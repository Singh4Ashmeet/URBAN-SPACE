"""Repository layer for UrbanShield Core API.

Handles all database queries through SQLAlchemy sessions. Each function
receives a Session and performs reads/writes without committing — the caller
(service or route) is responsible for committing the transaction.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Dispatch,
    EnvironmentReading,
    Incident,
    IncidentHistory,
    OutboxEvent,
    Vehicle,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometres."""
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Incident helpers
# ---------------------------------------------------------------------------

def incident_to_dict(row: Incident) -> dict[str, Any]:
    """Convert an Incident ORM object to the camelCase API response dict."""
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "incidentType": row.incident_type,
        "severity": row.severity,
        "status": row.status,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "district": row.district,
        "assignedTeam": row.assigned_team,
        "reportedAt": row.reported_at.isoformat() if isinstance(row.reported_at, datetime) else str(row.reported_at),
        "updatedAt": row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else str(row.updated_at),
        "resolvedAt": row.resolved_at.isoformat() if isinstance(row.resolved_at, datetime) and row.resolved_at else row.resolved_at,
        "version": row.version,
    }


def vehicle_to_dict(row: Vehicle) -> dict[str, Any]:
    """Convert a Vehicle ORM object to the camelCase API response dict."""
    return {
        "id": row.id,
        "callSign": row.call_sign,
        "vehicleType": row.vehicle_type,
        "status": row.status,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "capacity": row.capacity,
        "maximumSpeedKph": row.maximum_speed_kph,
        "assignedIncidentId": row.assigned_incident_id,
        "homeStation": row.home_station,
        "lastSeenAt": row.last_seen_at.isoformat() if isinstance(row.last_seen_at, datetime) else str(row.last_seen_at),
        "createdAt": row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
        "updatedAt": row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else str(row.updated_at),
        "version": row.version,
    }


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

def create_incident(
    db: Session,
    *,
    title: str,
    description: str | None,
    incident_type: str,
    severity: int,
    status: str,
    latitude: float,
    longitude: float,
    district: str | None = None,
    assigned_team: str | None = None,
    actor: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    resolved_at = ts if status == "RESOLVED" else None
    incident = Incident(
        title=title,
        description=description,
        incident_type=incident_type,
        severity=severity,
        status=status,
        latitude=latitude,
        longitude=longitude,
        district=district,
        assigned_team=assigned_team,
        reported_at=ts,
        updated_at=ts,
        resolved_at=resolved_at,
        created_by=actor,
    )
    db.add(incident)
    db.flush()

    result = incident_to_dict(incident)

    # History
    db.add(IncidentHistory(
        incident_id=incident.id,
        action="CREATED",
        before_json=None,
        after_json=json.dumps(result),
        actor_id=actor,
        correlation_id=correlation_id,
        created_at=ts,
    ))

    # Outbox
    _write_outbox(db, "INCIDENT_CREATED", "Incident", str(incident.id), result, ts)

    # Audit
    _write_audit(db, "INCIDENT_CREATED", "Incident", str(incident.id), "SUCCESS", result, actor, correlation_id, ts)

    return result


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.execute(
        select(Incident).where(Incident.id == incident_id, Incident.deleted_at.is_(None))
    ).scalar_one_or_none()


def list_incidents(
    db: Session,
    *,
    status: str | None = None,
    incident_type: str | None = None,
    min_severity: int | None = None,
    max_severity: int | None = None,
    search: str | None = None,
    sort_by: str = "reported_at",
    direction: str = "desc",
    page: int = 0,
    size: int = 100,
) -> tuple[list[Incident], int]:
    """Return (incidents, total_count)."""
    query = select(Incident).where(Incident.deleted_at.is_(None))

    if status:
        query = query.where(Incident.status == status)
    if incident_type:
        query = query.where(Incident.incident_type == incident_type)
    if min_severity is not None:
        query = query.where(Incident.severity >= min_severity)
    if max_severity is not None:
        query = query.where(Incident.severity <= max_severity)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            (func.lower(Incident.title).like(pattern))
            | (func.lower(func.coalesce(Incident.description, "")).like(pattern))
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Sort
    sort_map = {
        "reportedAt": Incident.reported_at,
        "reported_at": Incident.reported_at,
        "updatedAt": Incident.updated_at,
        "updated_at": Incident.updated_at,
        "severity": Incident.severity,
        "title": Incident.title,
    }
    sort_col = sort_map.get(sort_by, Incident.reported_at)
    if direction.lower() == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    query = query.limit(size).offset(page * size)
    incidents = list(db.execute(query).scalars().all())
    return incidents, total


def update_incident_full(
    db: Session,
    incident: Incident,
    *,
    title: str,
    description: str | None,
    incident_type: str,
    severity: int,
    status: str,
    latitude: float,
    longitude: float,
    district: str | None = None,
    assigned_team: str | None = None,
    actor: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    before = incident_to_dict(incident)

    incident.title = title
    incident.description = description
    incident.incident_type = incident_type
    incident.severity = severity
    incident.status = status
    incident.latitude = latitude
    incident.longitude = longitude
    incident.district = district
    incident.assigned_team = assigned_team
    incident.updated_at = ts
    incident.updated_by = actor
    if status == "RESOLVED" and incident.resolved_at is None:
        incident.resolved_at = ts
    incident.version += 1
    db.flush()

    after = incident_to_dict(incident)
    db.add(IncidentHistory(
        incident_id=incident.id,
        action="UPDATED",
        before_json=json.dumps(before),
        after_json=json.dumps(after),
        actor_id=actor,
        correlation_id=correlation_id,
        created_at=ts,
    ))
    _write_outbox(db, "INCIDENT_UPDATED", "Incident", str(incident.id), after, ts)
    _write_audit(db, "INCIDENT_UPDATED", "Incident", str(incident.id), "SUCCESS", after, actor, correlation_id, ts)
    return after


def update_incident_status(
    db: Session,
    incident: Incident,
    *,
    new_status: str,
    actor: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    before = incident_to_dict(incident)

    incident.status = new_status
    incident.updated_at = ts
    incident.updated_by = actor
    if new_status == "RESOLVED" and incident.resolved_at is None:
        incident.resolved_at = ts
    incident.version += 1
    db.flush()

    after = incident_to_dict(incident)
    db.add(IncidentHistory(
        incident_id=incident.id,
        action="STATUS_CHANGED",
        before_json=json.dumps(before),
        after_json=json.dumps(after),
        actor_id=actor,
        correlation_id=correlation_id,
        created_at=ts,
    ))
    _write_outbox(db, "INCIDENT_STATUS_CHANGED", "Incident", str(incident.id), after, ts)
    _write_audit(db, "INCIDENT_STATUS_CHANGED", "Incident", str(incident.id), "SUCCESS", after, actor, correlation_id, ts)
    return after


def soft_delete_incident(
    db: Session,
    incident: Incident,
    *,
    actor: str | None = None,
    correlation_id: str | None = None,
) -> None:
    ts = _now()
    before = incident_to_dict(incident)
    incident.deleted_at = ts
    incident.updated_at = ts
    incident.version += 1
    db.flush()

    db.add(IncidentHistory(
        incident_id=incident.id,
        action="DELETED",
        before_json=json.dumps(before),
        after_json=json.dumps(incident_to_dict(incident)),
        actor_id=actor,
        correlation_id=correlation_id,
        created_at=ts,
    ))
    _write_outbox(db, "INCIDENT_DELETED", "Incident", str(incident.id), before, ts)
    _write_audit(db, "INCIDENT_DELETED", "Incident", str(incident.id), "SUCCESS", before, actor, correlation_id, ts)


def get_incident_history(db: Session, incident_id: int) -> list[IncidentHistory]:
    return list(
        db.execute(
            select(IncidentHistory)
            .where(IncidentHistory.incident_id == incident_id)
            .order_by(IncidentHistory.created_at.desc())
        ).scalars().all()
    )


def get_incidents_nearby(
    db: Session,
    latitude: float,
    longitude: float,
    radius_meters: float,
) -> list[dict[str, Any]]:
    all_incidents = list(
        db.execute(
            select(Incident).where(Incident.deleted_at.is_(None))
        ).scalars().all()
    )
    results = []
    for inc in all_incidents:
        dist = _haversine_km(latitude, longitude, inc.latitude, inc.longitude)
        if dist * 1000 <= radius_meters:
            results.append(incident_to_dict(inc) | {"distanceKm": round(dist, 3)})
    return results


def get_incident_summary(db: Session) -> dict[str, Any]:
    incidents = list(
        db.execute(select(Incident).where(Incident.deleted_at.is_(None))).scalars().all()
    )
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for inc in incidents:
        by_type[inc.incident_type] = by_type.get(inc.incident_type, 0) + 1
        by_status[inc.status] = by_status.get(inc.status, 0) + 1
        by_severity[str(inc.severity)] = by_severity.get(str(inc.severity), 0) + 1
    resolved = by_status.get("RESOLVED", 0)
    cancelled = by_status.get("CANCELLED", 0)
    avg = round(sum(inc.severity for inc in incidents) / max(len(incidents), 1), 2)
    return {
        "totalIncidents": len(incidents),
        "activeIncidents": len(incidents) - resolved - cancelled,
        "resolvedIncidents": resolved,
        "byType": by_type,
        "byStatus": by_status,
        "bySeverity": by_severity,
        "averageSeverity": avg,
    }


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

def create_vehicle(
    db: Session,
    *,
    call_sign: str,
    vehicle_type: str,
    status: str,
    latitude: float,
    longitude: float,
    capacity: int,
    maximum_speed_kph: float,
    home_station: str | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    vehicle = Vehicle(
        call_sign=call_sign,
        vehicle_type=vehicle_type,
        status=status,
        latitude=latitude,
        longitude=longitude,
        capacity=capacity,
        maximum_speed_kph=maximum_speed_kph,
        home_station=home_station,
        last_seen_at=ts,
        created_at=ts,
        updated_at=ts,
    )
    db.add(vehicle)
    db.flush()
    result = vehicle_to_dict(vehicle)
    _write_outbox(db, "VEHICLE_CREATED", "EmergencyVehicle", str(vehicle.id), result, ts)
    _write_audit(db, "VEHICLE_CREATED", "EmergencyVehicle", str(vehicle.id), "SUCCESS", result, actor, None, ts)
    return result


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle | None:
    return db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
    ).scalar_one_or_none()


def list_vehicles(
    db: Session,
    *,
    status: str | None = None,
    vehicle_type: str | None = None,
) -> list[Vehicle]:
    query = select(Vehicle).where(Vehicle.deleted_at.is_(None))
    if status:
        query = query.where(Vehicle.status == status)
    if vehicle_type:
        query = query.where(Vehicle.vehicle_type == vehicle_type)
    query = query.order_by(Vehicle.call_sign)
    return list(db.execute(query).scalars().all())


def update_vehicle_status(
    db: Session,
    vehicle: Vehicle,
    *,
    new_status: str,
    actor: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    vehicle.status = new_status
    vehicle.updated_at = ts
    vehicle.version += 1
    db.flush()
    result = vehicle_to_dict(vehicle)
    _write_outbox(db, "VEHICLE_STATUS_CHANGED", "EmergencyVehicle", str(vehicle.id), result, ts)
    _write_audit(db, "VEHICLE_STATUS_CHANGED", "EmergencyVehicle", str(vehicle.id), "SUCCESS", result, actor, None, ts)
    return result


def update_vehicle_location(
    db: Session,
    vehicle: Vehicle,
    *,
    latitude: float,
    longitude: float,
    actor: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    vehicle.latitude = latitude
    vehicle.longitude = longitude
    vehicle.last_seen_at = ts
    vehicle.updated_at = ts
    vehicle.version += 1
    db.flush()
    result = vehicle_to_dict(vehicle)
    _write_outbox(db, "VEHICLE_LOCATION_UPDATED", "EmergencyVehicle", str(vehicle.id), result, ts)
    _write_audit(db, "VEHICLE_LOCATION_UPDATED", "EmergencyVehicle", str(vehicle.id), "SUCCESS", result, actor, None, ts)
    return result


def soft_delete_vehicle(db: Session, vehicle: Vehicle, *, actor: str | None = None) -> None:
    ts = _now()
    vehicle.deleted_at = ts
    vehicle.updated_at = ts
    db.flush()
    _write_audit(db, "VEHICLE_DELETED", "EmergencyVehicle", str(vehicle.id), "SUCCESS", vehicle_to_dict(vehicle), actor, None, ts)


def get_vehicles_nearby(
    db: Session,
    latitude: float,
    longitude: float,
    radius_meters: float,
) -> list[dict[str, Any]]:
    all_vehicles = list(
        db.execute(select(Vehicle).where(Vehicle.deleted_at.is_(None))).scalars().all()
    )
    results = []
    for veh in all_vehicles:
        dist = _haversine_km(latitude, longitude, veh.latitude, veh.longitude)
        if dist * 1000 <= radius_meters:
            results.append(vehicle_to_dict(veh) | {"distanceKm": round(dist, 3)})
    return results


# ---------------------------------------------------------------------------
# Dispatches
# ---------------------------------------------------------------------------

def create_dispatch_assignment(
    db: Session,
    *,
    incident: Incident,
    vehicle: Vehicle,
    priority: int,
    actor: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    distance = _haversine_km(incident.latitude, incident.longitude, vehicle.latitude, vehicle.longitude)
    eta = max(1, round((distance / max(vehicle.maximum_speed_kph, 1)) * 60))

    dispatch = Dispatch(
        incident_id=incident.id,
        vehicle_id=vehicle.id,
        status="ASSIGNED",
        priority=priority,
        distance_km=round(distance, 3),
        estimated_arrival_minutes=eta,
        assignment_reason=f"Nearest available {vehicle.vehicle_type} at {round(distance, 2)} km.",
        dispatched_at=ts,
        created_at=ts,
        updated_at=ts,
        created_by=actor,
    )
    db.add(dispatch)
    db.flush()

    # Mark vehicle as dispatched
    vehicle.status = "DISPATCHED"
    vehicle.assigned_incident_id = incident.id
    vehicle.updated_at = ts
    vehicle.version += 1
    db.flush()

    return {
        "dispatchId": dispatch.id,
        "vehicle": vehicle_to_dict(vehicle),
        "distanceKm": round(distance, 3),
        "estimatedArrivalMinutes": eta,
    }


def list_dispatches(db: Session) -> list[Dispatch]:
    return list(
        db.execute(select(Dispatch).order_by(Dispatch.created_at.desc())).scalars().all()
    )


def get_dispatch(db: Session, dispatch_id: int) -> Dispatch | None:
    return db.execute(
        select(Dispatch).where(Dispatch.id == dispatch_id)
    ).scalar_one_or_none()


def update_dispatch_status(
    db: Session,
    dispatch: Dispatch,
    *,
    new_status: str,
    actor: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    ts = _now()
    
    current = dispatch.status.upper()
    target = new_status.upper().replace(" ", "_")
    
    # Normalize inputs like "created", "en_route", etc.
    mapping = {
        "CREATED": "ASSIGNED",
    }
    target = mapping.get(target, target)
    
    # Validate transition
    VALID_TRANSITIONS = {
        "ASSIGNED": {"ACKNOWLEDGED", "ACCEPTED", "CANCELLED", "FAILED"},
        "ACCEPTED": {"ACKNOWLEDGED", "EN_ROUTE", "CANCELLED", "FAILED"},
        "ACKNOWLEDGED": {"EN_ROUTE", "CANCELLED", "FAILED"},
        "EN_ROUTE": {"ARRIVED", "CANCELLED", "FAILED"},
        "ARRIVED": {"COMPLETED", "CANCELLED", "FAILED"},
        "COMPLETED": set(),
        "CANCELLED": set(),
        "FAILED": set(),
    }
    
    if target != current:
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"Invalid dispatch transition from {current} to {target}")
            
    dispatch.status = target
    new_status = target
    dispatch.updated_at = ts
    if new_status == "ARRIVED":
        dispatch.arrived_at = ts
    if new_status in {"COMPLETED", "CANCELLED", "FAILED"}:
        dispatch.completed_at = ts
        # Release the vehicle
        vehicle = db.execute(
            select(Vehicle).where(Vehicle.id == dispatch.vehicle_id)
        ).scalar_one_or_none()
        if vehicle and new_status in {"COMPLETED", "CANCELLED"}:
            vehicle.status = "AVAILABLE"
            vehicle.assigned_incident_id = None
            vehicle.updated_at = ts
            vehicle.version += 1
    if new_status == "ACKNOWLEDGED":
        dispatch.acknowledged_at = ts
    dispatch.version += 1
    db.flush()

    result = _dispatch_to_dict(dispatch)
    _write_outbox(db, "DISPATCH_STATUS_CHANGED", "Dispatch", str(dispatch.id), result, ts)
    _write_audit(db, "DISPATCH_STATUS_CHANGED", "Dispatch", str(dispatch.id), "SUCCESS", result, actor, correlation_id, ts)
    return result


def _dispatch_to_dict(d: Dispatch) -> dict[str, Any]:
    def _fmt(val):
        if isinstance(val, datetime):
            return val.isoformat()
        return val

    return {
        "id": d.id,
        "incident_id": d.incident_id,
        "vehicle_id": d.vehicle_id,
        "status": d.status,
        "priority": d.priority,
        "distance_km": d.distance_km,
        "estimated_arrival_minutes": d.estimated_arrival_minutes,
        "assignment_reason": d.assignment_reason,
        "dispatched_at": _fmt(d.dispatched_at),
        "acknowledged_at": _fmt(d.acknowledged_at),
        "arrived_at": _fmt(d.arrived_at),
        "completed_at": _fmt(d.completed_at),
        "created_at": _fmt(d.created_at),
        "updated_at": _fmt(d.updated_at),
    }


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def get_latest_reading(db: Session) -> EnvironmentReading | None:
    return db.execute(
        select(EnvironmentReading).order_by(EnvironmentReading.observed_at.desc()).limit(1)
    ).scalar_one_or_none()


def create_synthetic_reading(db: Session) -> dict[str, Any]:
    ts = _now()
    reading = EnvironmentReading(
        latitude=28.6139,
        longitude=77.2090,
        temperature_c=31.4,
        humidity_percent=58,
        rainfall_mm=0.0,
        wind_speed_kph=9.5,
        visibility_km=5.0,
        weather_condition="CLEAR",
        pm25=42.0,
        pm10=86.0,
        air_quality_index=128,
        source="synthetic-local",
        quality="SYNTHETIC",
        is_synthetic=1,
        observed_at=ts,
        created_at=ts,
    )
    db.add(reading)
    db.flush()
    return _reading_to_dict(reading)


def get_environment_history(db: Session, limit: int = 100) -> list[EnvironmentReading]:
    return list(
        db.execute(
            select(EnvironmentReading).order_by(EnvironmentReading.observed_at.desc()).limit(limit)
        ).scalars().all()
    )


def _reading_to_dict(r: EnvironmentReading) -> dict[str, Any]:
    def _fmt(val):
        if isinstance(val, datetime):
            return val.isoformat()
        return val
    return {
        "id": r.id,
        "timestamp": _fmt(r.observed_at),
        "latitude": r.latitude,
        "longitude": r.longitude,
        "temperature_c": r.temperature_c,
        "humidity_percent": r.humidity_percent,
        "rainfall_mm": r.rainfall_mm,
        "wind_speed_kph": r.wind_speed_kph,
        "visibility_meters": r.visibility_km * 1000 if r.visibility_km else 0,
        "weather_condition": r.weather_condition,
        "pm25": r.pm25,
        "pm10": r.pm10,
        "air_quality_index": r.air_quality_index,
        "source": r.source,
        "quality": r.quality,
        "is_synthetic": r.is_synthetic,
        "created_at": _fmt(r.created_at),
    }


# ---------------------------------------------------------------------------
# Audit & Outbox
# ---------------------------------------------------------------------------

def get_audit_logs(db: Session, limit: int = 200) -> list[AuditLog]:
    return list(
        db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        ).scalars().all()
    )


def get_outbox_status(db: Session) -> dict[str, Any]:
    rows = db.execute(
        select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status)
    ).all()
    status_counts = {row[0]: row[1] for row in rows}
    recent = list(
        db.execute(
            select(OutboxEvent).order_by(OutboxEvent.created_at.desc()).limit(20)
        ).scalars().all()
    )
    return {
        "statusCounts": status_counts,
        "recentEvents": [json.loads(e.payload_json) for e in recent],
    }


# Shared in-memory event buffer for SSE
RECENT_EVENTS: list[dict[str, Any]] = []
MAX_RECENT_EVENTS = 200


def _write_outbox(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    ts: datetime,
) -> dict[str, Any]:
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "timestamp": ts.isoformat(),
        "version": 1,
        "source": "core-api",
        "payload": payload,
    }
    db.add(OutboxEvent(
        event_id=event["event_id"],
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload_json=json.dumps(event),
        status="PENDING",
        created_at=ts,
    ))
    RECENT_EVENTS.append(event)
    del RECENT_EVENTS[:-MAX_RECENT_EVENTS]
    return event


def _write_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str | None,
    result: str,
    details: dict[str, Any],
    actor: str | None,
    correlation_id: str | None,
    ts: datetime,
) -> None:
    db.add(AuditLog(
        actor_id=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=f"{action} on {entity_type} {entity_id}",
        metadata_json=json.dumps(details),
        correlation_id=correlation_id,
        result=result,
        created_at=ts,
    ))


def rank_vehicles_for_incident(
    db: Session,
    incident: Incident,
    vehicle_type: str | None = None,
) -> list[dict[str, Any]]:
    """Determine a list of emergency vehicles ranked by suitability for the given incident.
    
    Returns score, reasons, and distance.
    """
    query = select(Vehicle).where(Vehicle.deleted_at.is_(None))
    if vehicle_type:
        query = query.where(Vehicle.vehicle_type == vehicle_type)
    vehicles = db.execute(query).scalars().all()
    
    # Matching rules
    type_matches = {
        "ACCIDENT": {"AMBULANCE", "POLICE_CAR"},
        "FIRE": {"FIRE_ENGINE", "RESCUE_VEHICLE"},
        "FLOOD": {"RESCUE_VEHICLE", "MOBILE_COMMAND_UNIT"},
        "MEDICAL_EMERGENCY": {"AMBULANCE"},
        "PUBLIC_HAZARD": {"POLICE_CAR", "RESCUE_VEHICLE"},
        "ROAD_CLOSURE": {"POLICE_CAR"},
        "TRAFFIC_JAM": {"POLICE_CAR"},
        "WEATHER_ALERT": {"MOBILE_COMMAND_UNIT", "RESCUE_VEHICLE"},
        "AIR_QUALITY_ALERT": {"MOBILE_COMMAND_UNIT"},
    }
    
    results = []
    for v in vehicles:
        score = 100.0
        reasons = []
        
        # 1. Geographic distance
        dist = _haversine_km(incident.latitude, incident.longitude, v.latitude, v.longitude)
        dist_penalty = round(dist * 5.0, 2)
        score -= dist_penalty
        reasons.append(f"Geographic distance is {round(dist, 2)} km (-{dist_penalty} pts)")
        
        # 2. Status
        status_upper = v.status.upper()
        if status_upper == "AVAILABLE":
            reasons.append("Status is AVAILABLE (no penalty)")
        elif status_upper in {"RESERVED", "RETURNING"}:
            score -= 20.0
            reasons.append(f"Status is {status_upper} (-20.0 pts)")
        elif status_upper in {"DISPATCHED", "EN_ROUTE", "ON_SCENE"}:
            score -= 50.0
            reasons.append(f"Status is {status_upper} (-50.0 pts)")
        else:  # OUT_OF_SERVICE etc
            score -= 100.0
            reasons.append(f"Status is {status_upper} (-100.0 pts)")
            
        # 3. Type eligibility
        eligible_types = type_matches.get(incident.incident_type.upper(), set())
        if v.vehicle_type.upper() in eligible_types:
            score += 30.0
            reasons.append(f"Vehicle type {v.vehicle_type} is highly eligible for {incident.incident_type} (+30.0 pts)")
        else:
            reasons.append(f"Vehicle type {v.vehicle_type} is neutral for {incident.incident_type}")
            
        # 4. Capacity
        if v.capacity >= incident.severity:
            score += 10.0
            reasons.append(f"Capacity {v.capacity} matches or exceeds incident severity {incident.severity} (+10.0 pts)")
        else:
            reasons.append(f"Capacity {v.capacity} is less than incident severity {incident.severity}")
            
        # 5. Existing assignment
        if v.assigned_incident_id is not None:
            score -= 15.0
            reasons.append(f"Vehicle has an existing assignment to incident #{v.assigned_incident_id} (-15.0 pts)")
            
        # Cap score between 0 and 150
        score = max(0.0, min(150.0, score))
        score = round(score, 2)
        
        results.append({
            "vehicle": vehicle_to_dict(v),
            "score": score,
            "reasons": reasons,
            "distanceKm": round(dist, 3),
        })
        
    # Sort by score desc, then by distance asc
    results.sort(key=lambda x: (-x["score"], x["distanceKm"]))
    return results
