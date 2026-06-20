from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SimulationRun, SimulationScenario

SIMULATION_RULE_VERSION = "1.0.0"

BASE_MINUTES = {
    "ACCIDENT": 6,
    "FLOOD": 10,
    "ROAD_CLOSURE": 8,
    "FIRE": 7,
    "TRAFFIC_JAM": 5,
    "MEDICAL_EMERGENCY": 5,
    "PUBLIC_HAZARD": 7,
    "AIR_QUALITY_ALERT": 7,
    "WEATHER_ALERT": 8,
}
TRAFFIC_MULTIPLIERS = {"LOW": 0.9, "MODERATE": 1.0, "HIGH": 1.3, "SEVERE": 1.65}
WEATHER_MULTIPLIERS = {"CLEAR": 1.0, "RAIN": 1.15, "HEAVY_RAIN": 1.35, "FOG": 1.25, "STORM": 1.55}


class SimulationRunRequest(BaseModel):
    scenario_name: str = Field(min_length=1)
    incident_type: str
    severity: int = Field(ge=1, le=5)
    latitude: float = Field(default=28.6139, ge=-90, le=90)
    longitude: float = Field(default=77.2090, ge=-180, le=180)
    number_of_vehicles: int = Field(default=2, ge=1, le=20)
    traffic_level: str = "MODERATE"
    weather_condition: str = "CLEAR"
    road_blocked: bool = False
    simulation_duration_minutes: int = Field(default=30, ge=5, le=240)


class CompareRequest(BaseModel):
    runIds: list[int] = Field(min_length=2, max_length=4)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["scenario_name"] = str(normalized["scenario_name"]).strip()
    normalized["incident_type"] = str(normalized["incident_type"]).upper()
    normalized["traffic_level"] = str(normalized.get("traffic_level", "MODERATE")).upper()
    normalized["weather_condition"] = str(normalized.get("weather_condition", "CLEAR")).upper()
    normalized["severity"] = int(normalized["severity"])
    normalized["number_of_vehicles"] = int(normalized.get("number_of_vehicles", 2))
    normalized["simulation_duration_minutes"] = int(normalized.get("simulation_duration_minutes", 30))
    normalized["latitude"] = round(float(normalized.get("latitude", 28.6139)), 6)
    normalized["longitude"] = round(float(normalized.get("longitude", 77.2090)), 6)
    normalized["road_blocked"] = bool(normalized.get("road_blocked", False))
    return normalized


def input_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(canonical_payload(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seed_from_hash(hash_value: str) -> int:
    return int(hash_value[:8], 16)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_result(payload: dict[str, Any], hash_value: str) -> dict[str, Any]:
    data = canonical_payload(payload)
    incident_type = data["incident_type"]
    traffic_level = data["traffic_level"]
    weather = data["weather_condition"]
    direct_distance = haversine_km(data["latitude"], data["longitude"], 28.6180, 77.2050)
    route_factor = 1.35 + (0.25 if data["road_blocked"] else 0)
    route_distance = round(max(0.1, direct_distance * route_factor), 2)
    speed = {"LOW": 38, "MODERATE": 30, "HIGH": 22, "SEVERE": 14}[traffic_level]
    route_minutes = max(2, round((route_distance / speed) * 60))
    vehicle_discount = min((data["number_of_vehicles"] - 1) * 0.75, 4.0)
    estimated_minutes = round(
        ((BASE_MINUTES[incident_type] + data["severity"] * 2 + route_minutes) * TRAFFIC_MULTIPLIERS[traffic_level] * WEATHER_MULTIPLIERS[weather])
        + (5 if data["road_blocked"] else 0)
        - vehicle_discount
    )
    estimated_minutes = max(4, estimated_minutes)
    base_radius = {
        "ACCIDENT": 120,
        "FIRE": 240,
        "FLOOD": 300,
        "ROAD_CLOSURE": 180,
        "TRAFFIC_JAM": 160,
        "MEDICAL_EMERGENCY": 90,
        "PUBLIC_HAZARD": 180,
        "AIR_QUALITY_ALERT": 220,
        "WEATHER_ALERT": 260,
    }[incident_type]
    weather_bonus = 80 if weather in {"HEAVY_RAIN", "STORM"} else 0
    radius = base_radius + data["severity"] * 75 + weather_bonus
    recommended = min(10, max(1, data["severity"] + (1 if incident_type in {"FIRE", "FLOOD"} else 0)))
    risk_score = min(100, round(data["severity"] * 13 + estimated_minutes * 1.4 + radius / 80))
    warnings: list[str] = []
    if traffic_level in {"HIGH", "SEVERE"}:
        warnings.append("Traffic level increases travel time.")
    if data["road_blocked"]:
        warnings.append("Road blocked flag added a rerouting penalty.")
    if incident_type in {"FIRE", "FLOOD"}:
        warnings.append("Incident type increases the affected area.")
    if data["number_of_vehicles"] < recommended:
        warnings.append("Entered vehicle count is below the deterministic recommendation.")
    return {
        "simulation_id": hash_value[:12],
        "scenario_name": data["scenario_name"],
        "incident_type": incident_type,
        "severity": data["severity"],
        "estimated_response_time_minutes": estimated_minutes,
        "estimated_affected_radius_meters": radius,
        "recommended_vehicle_count": recommended,
        "risk_score": risk_score,
        "route_distance_km": route_distance,
        "warnings": warnings,
        "status": "SIMULATION_COMPLETED",
        "simulation_version": SIMULATION_RULE_VERSION,
        "input_hash": hash_value,
        "seed": seed_from_hash(hash_value),
    }


def run_and_persist(db: Session, request: SimulationRunRequest, actor: str | None = None) -> dict[str, Any]:
    started = utcnow()
    start_perf = time.perf_counter()
    payload = canonical_payload(request.model_dump())
    hash_value = input_hash(payload)
    result = calculate_result(payload, hash_value)
    completed = utcnow()

    scenario = db.execute(select(SimulationScenario).where(SimulationScenario.input_hash == hash_value)).scalar_one_or_none()
    if scenario is None:
        scenario = SimulationScenario(
            name=payload["scenario_name"],
            description=None,
            input_json=json.dumps(payload, sort_keys=True),
            input_hash=hash_value,
            scenario_version=SIMULATION_RULE_VERSION,
            created_by=actor,
            created_at=started,
            updated_at=started,
        )
        db.add(scenario)
        db.flush()

    run = SimulationRun(
        scenario_id=scenario.id,
        simulation_version=SIMULATION_RULE_VERSION,
        input_json=json.dumps(payload, sort_keys=True),
        input_hash=hash_value,
        result_json=json.dumps(result, sort_keys=True),
        warnings_json=json.dumps(result["warnings"]),
        status="COMPLETED",
        seed=result["seed"],
        started_at=started,
        completed_at=completed,
        duration_ms=round((time.perf_counter() - start_perf) * 1000),
        created_by=actor,
    )
    db.add(run)
    db.flush()
    return run_to_dict(run)


def run_to_dict(run: SimulationRun) -> dict[str, Any]:
    result = json.loads(run.result_json or "{}")
    result.update(
        {
            "id": run.id,
            "runId": run.id,
            "scenarioId": run.scenario_id,
            "simulation_version": run.simulation_version,
            "input_hash": run.input_hash,
            "seed": run.seed,
            "status": "SIMULATION_COMPLETED" if run.status == "COMPLETED" else run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_ms": run.duration_ms,
        }
    )
    return result


def list_runs(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    runs = db.execute(select(SimulationRun).order_by(SimulationRun.id.desc()).limit(limit)).scalars().all()
    return [run_to_dict(run) for run in runs]


def get_run(db: Session, run_id: int) -> SimulationRun | None:
    return db.execute(select(SimulationRun).where(SimulationRun.id == run_id)).scalar_one_or_none()


def compare_runs(db: Session, run_ids: list[int]) -> dict[str, Any]:
    runs = [get_run(db, run_id) for run_id in run_ids]
    if any(run is None for run in runs):
        missing = [run_id for run_id, run in zip(run_ids, runs) if run is None]
        return {"missingRunIds": missing, "runs": [], "deltas": []}
    payloads = [run_to_dict(run) for run in runs if run is not None]
    baseline = payloads[0]
    deltas = []
    for item in payloads[1:]:
        deltas.append(
            {
                "runId": item["runId"],
                "responseTimeDelta": item["estimated_response_time_minutes"] - baseline["estimated_response_time_minutes"],
                "riskScoreDelta": item["risk_score"] - baseline["risk_score"],
                "affectedRadiusDelta": item["estimated_affected_radius_meters"] - baseline["estimated_affected_radius_meters"],
                "routeDistanceDelta": round(item["route_distance_km"] - baseline["route_distance_km"], 2),
            }
        )
    return {"baselineRunId": baseline["runId"], "runs": payloads, "deltas": deltas}


def export_run(run: SimulationRun, export_format: str) -> tuple[str, str]:
    payload = run_to_dict(run)
    if export_format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(payload.keys()))
        writer.writeheader()
        writer.writerow(payload)
        return "text/csv", output.getvalue()
    return "application/json", json.dumps(payload, indent=2)
