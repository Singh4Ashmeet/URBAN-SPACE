"""UrbanShield Core API — refactored to use SQLAlchemy ORM with layered architecture.

Preserves all existing route paths and response shapes for backward compatibility.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from starlette.responses import Response, StreamingResponse

from app.db import Base, SessionLocal, engine, get_db
from app.models import (
    AuditLog,
    Dispatch,
    EnvironmentReading,
    Incident,
    IncidentHistory,
    OutboxEvent,
    RefreshToken,
    SimulationRun,
    User,
    Vehicle,
)
from app.repositories import (
    RECENT_EVENTS,
    create_dispatch_assignment,
    create_incident,
    create_synthetic_reading,
    create_vehicle,
    get_audit_logs,
    get_dispatch,
    get_environment_history,
    get_incident,
    get_incident_history,
    get_incident_summary,
    get_incidents_nearby,
    get_latest_reading,
    get_outbox_status,
    get_vehicle,
    get_vehicles_nearby,
    incident_to_dict,
    list_dispatches,
    list_incidents,
    list_vehicles,
    _dispatch_to_dict,
    _reading_to_dict,
    _write_audit,
    _write_outbox,
    soft_delete_incident,
    soft_delete_vehicle,
    update_dispatch_status,
    update_incident_full,
    update_incident_status,
    update_vehicle_location,
    update_vehicle_status,
    vehicle_to_dict,
    rank_vehicles_for_incident,
)
from app.security import (
    AUDIT_ROLES,
    AUTH_ENABLED,
    MUTATION_ROLES,
    LoginRequest,
    RefreshRequest,
    actor_name,
    authenticate_user,
    decode_access_token,
    get_current_user,
    issue_tokens,
    refresh_token_hash,
    require_roles,
    seed_users,
    utcnow,
)
from app.simulation_persistence import (
    CompareRequest,
    SimulationRunRequest,
    compare_runs,
    export_run,
    get_run,
    list_runs,
    run_and_persist,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("URBANSHIELD_DATA_DIR", ROOT / ".data"))
DB_PATH = Path(os.environ.get("URBANSHIELD_CORE_DB", DATA_DIR / "urbanshield-core.sqlite3"))
ALLOWED_ORIGINS = os.environ.get(
    "APP_CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
).split(",")

# ---------------------------------------------------------------------------
# Enums (kept for validation, same as legacy)
# ---------------------------------------------------------------------------
INCIDENT_TYPES = {
    "ACCIDENT", "FIRE", "FLOOD", "ROAD_CLOSURE", "TRAFFIC_JAM",
    "MEDICAL_EMERGENCY", "PUBLIC_HAZARD", "AIR_QUALITY_ALERT", "WEATHER_ALERT",
}
INCIDENT_STATUSES = {"REPORTED", "VERIFIED", "DISPATCHED", "IN_PROGRESS", "RESOLVED", "CANCELLED"}
VEHICLE_TYPES = {"AMBULANCE", "FIRE_ENGINE", "POLICE_CAR", "RESCUE_VEHICLE", "MOBILE_COMMAND_UNIT"}
VEHICLE_STATUSES = {"AVAILABLE", "RESERVED", "DISPATCHED", "EN_ROUTE", "ON_SCENE", "RETURNING", "OUT_OF_SERVICE"}
DISPATCH_STATUSES = {"ASSIGNED", "ACCEPTED", "ACKNOWLEDGED", "EN_ROUTE", "ARRIVED", "COMPLETED", "CANCELLED", "FAILED"}

# ---------------------------------------------------------------------------
# Request models (backward-compatible names)
# ---------------------------------------------------------------------------

class IncidentIn(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    incidentType: str
    severity: int = Field(ge=1, le=5)
    status: str = "REPORTED"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: str | None = None
    assignedTeam: str | None = None
    version: int | None = None


class StatusUpdate(BaseModel):
    status: str
    version: int | None = None


class VehicleIn(BaseModel):
    callSign: str = Field(min_length=1)
    vehicleType: str
    status: str = "AVAILABLE"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity: int = Field(default=2, ge=1, le=50)
    maximumSpeedKph: float = Field(default=60, gt=0, le=200)
    homeStation: str | None = None
    version: int | None = None


class VehicleStatusUpdate(BaseModel):
    status: str
    version: int | None = None


class VehicleLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    version: int | None = None


class DispatchRequest(BaseModel):
    incidentId: int
    requestedVehicleCount: int = Field(default=1, ge=1, le=10)
    priority: int = Field(default=3, ge=1, le=5)
    vehicleType: str | None = None


class DispatchStatusUpdate(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# App & middleware
# ---------------------------------------------------------------------------

app = FastAPI(title="UrbanShield Core API", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_choice(value: str, allowed: set[str], label: str) -> None:
    if value not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported {label}: {value}")


# ---------------------------------------------------------------------------
# Startup — create tables (for non-Alembic path) and seed
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup() -> None:
    from app.cli import migrate_database
    migrate_database()
    _seed_if_empty()


def _seed_if_empty() -> None:
    """Seed demo data if the database is empty."""
    db = SessionLocal()
    try:
        seed_users(db)
        count = db.query(Incident).filter(Incident.deleted_at.is_(None)).count()
        if count > 0:
            db.commit()
            db.close()
            return

        seed_incidents = [
            ("Demo bridge lane collision", "Persistent demo incident.", "ACCIDENT", 3, "VERIFIED", 28.6139, 77.2090),
            ("Demo market smoke report", "Persistent demo incident.", "FIRE", 4, "IN_PROGRESS", 28.6160, 77.2150),
            ("Demo underpass waterlogging", "Persistent demo incident.", "FLOOD", 2, "REPORTED", 28.6075, 77.2045),
            ("Demo arterial road closure", "Persistent demo incident.", "ROAD_CLOSURE", 3, "VERIFIED", 28.6210, 77.1990),
            ("Demo medical assistance request", "Persistent demo incident.", "MEDICAL_EMERGENCY", 5, "IN_PROGRESS", 28.6195, 77.2114),
        ]
        for item in seed_incidents:
            create_incident(
                db,
                title=item[0], description=item[1], incident_type=item[2],
                severity=item[3], status=item[4], latitude=item[5], longitude=item[6],
                actor="SEED",
            )

        seed_vehicles = [
            ("AMB-12", "AMBULANCE", "AVAILABLE", 28.6145, 77.2085, 4, 70, "Central Medical Station"),
            ("FIRE-04", "FIRE_ENGINE", "AVAILABLE", 28.6170, 77.2130, 6, 60, "North Fire Station"),
            ("POL-22", "POLICE_CAR", "AVAILABLE", 28.6100, 77.2050, 2, 90, "Central Police Station"),
            ("RES-08", "RESCUE_VEHICLE", "AVAILABLE", 28.6220, 77.2000, 5, 65, "Rescue Depot"),
        ]
        for v in seed_vehicles:
            create_vehicle(
                db,
                call_sign=v[0], vehicle_type=v[1], status=v[2],
                latitude=v[3], longitude=v[4], capacity=v[5],
                maximum_speed_kph=v[6], home_station=v[7],
                actor="SEED",
            )

        create_synthetic_reading(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/core/auth/login")
@app.post("/api/v1/auth/login")
def api_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    result = issue_tokens(db, user, request)
    _write_audit(db, "AUTH_LOGIN", "User", str(user.id), "SUCCESS", {"username": user.username, "role": user.role}, user.username, None, utcnow())
    db.commit()
    return result.model_dump()


@app.get("/api/core/auth/me")
@app.get("/api/v1/auth/me")
def api_me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"id": user.id, "username": user.username, "displayName": user.display_name, "role": user.role}


@app.post("/api/core/auth/refresh")
@app.post("/api/v1/auth/refresh")
def api_refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    token_hash = refresh_token_hash(payload.refreshToken)
    token = db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).scalar_one_or_none()
    if not token or token.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    user = db.execute(select(User).where(User.id == token.user_id)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    token.revoked_at = utcnow()
    result = issue_tokens(db, user, request)
    _write_audit(db, "AUTH_REFRESH", "User", str(user.id), "SUCCESS", {"username": user.username}, user.username, None, utcnow())
    db.commit()
    return result.model_dump()


@app.post("/api/core/auth/logout")
@app.post("/api/v1/auth/logout")
def api_logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)).update({"revoked_at": utcnow()})
    _write_audit(db, "AUTH_LOGOUT", "User", str(user.id), "SUCCESS", {"username": user.username}, user.username, None, utcnow())
    db.commit()
    return {"status": "logged_out"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/core/health")
@app.get("/api/v1/system/core-health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    count = db.query(Incident).filter(Incident.deleted_at.is_(None)).count()
    return {
        "service": "core-api",
        "status": "UP",
        "storage": "sqlite",
        "database": str(DB_PATH),
        "incidentCount": count,
    }


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@app.get("/api/core/incidents")
def api_list_incidents(
    status: str | None = None,
    incidentType: str | None = None,
    minimumSeverity: int | None = Query(default=None, ge=1, le=5),
    maximumSeverity: int | None = Query(default=None, ge=1, le=5),
    search: str | None = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=100, ge=1, le=500),
    sortBy: str = "reportedAt",
    direction: str = "desc",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    incidents, total = list_incidents(
        db,
        status=status,
        incident_type=incidentType,
        min_severity=minimumSeverity,
        max_severity=maximumSeverity,
        search=search,
        sort_by=sortBy,
        direction=direction,
        page=page,
        size=size,
    )
    return {
        "content": [incident_to_dict(inc) for inc in incidents],
        "totalElements": total,
        "number": page,
        "size": size,
    }


@app.get("/api/core/incidents/summary")
def api_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    return get_incident_summary(db)


@app.get("/api/core/incidents/nearby")
def api_nearby(
    latitude: float,
    longitude: float,
    radiusMeters: float,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return get_incidents_nearby(db, latitude, longitude, radiusMeters)


@app.get("/api/core/incidents/events")
async def api_incident_events(
    request: Request,
    access_token: str | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    if AUTH_ENABLED:
        token = access_token
        header = request.headers.get("authorization")
        if not token and header and header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        payload = decode_access_token(token)
        user = db.execute(select(User).where(User.id == int(payload["uid"]))).scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

    async def stream():
        last_index = 0
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            while last_index < len(RECENT_EVENTS):
                event = RECENT_EVENTS[last_index]
                last_index += 1
                yield f"id: {event['event_id']}\nevent: incident\ndata: {json.dumps(event)}\n\n"
            await asyncio.sleep(10)
            yield ": heartbeat\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/core/incidents/{incident_id}")
def api_get_incident(incident_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    inc = get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident_to_dict(inc)


@app.post("/api/core/incidents", status_code=201)
def api_create_incident(
    payload: IncidentIn,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_choice(payload.incidentType, INCIDENT_TYPES, "incident type")
    require_choice(payload.status, INCIDENT_STATUSES, "incident status")
    result = create_incident(
        db,
        title=payload.title,
        description=payload.description,
        incident_type=payload.incidentType,
        severity=payload.severity,
        status=payload.status,
        latitude=payload.latitude,
        longitude=payload.longitude,
        district=payload.district,
        assigned_team=payload.assignedTeam,
        actor=actor_name(user),
    )
    db.commit()
    return result


@app.put("/api/core/incidents/{incident_id}")
def api_update_incident(
    incident_id: int,
    payload: IncidentIn,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_choice(payload.incidentType, INCIDENT_TYPES, "incident type")
    require_choice(payload.status, INCIDENT_STATUSES, "incident status")
    inc = get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if payload.version is not None and payload.version != inc.version:
        raise HTTPException(status_code=409, detail="Incident version conflict")
    result = update_incident_full(
        db, inc,
        title=payload.title,
        description=payload.description,
        incident_type=payload.incidentType,
        severity=payload.severity,
        status=payload.status,
        latitude=payload.latitude,
        longitude=payload.longitude,
        district=payload.district,
        assigned_team=payload.assignedTeam,
        actor=actor_name(user),
    )
    db.commit()
    return result


@app.patch("/api/core/incidents/{incident_id}/status")
def api_update_status(
    incident_id: int,
    payload: StatusUpdate,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_choice(payload.status, INCIDENT_STATUSES, "incident status")
    inc = get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if payload.version is not None and payload.version != inc.version:
        raise HTTPException(status_code=409, detail="Incident version conflict")
    result = update_incident_status(db, inc, new_status=payload.status, actor=actor_name(user))
    db.commit()
    return result


@app.delete("/api/core/incidents/{incident_id}", status_code=204, response_class=Response)
def api_delete_incident(
    incident_id: int,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    inc = get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    soft_delete_incident(db, inc, actor=actor_name(user))
    db.commit()
    return Response(status_code=204)


@app.get("/api/core/incidents/{incident_id}/history")
def api_incident_history(incident_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = get_incident_history(db, incident_id)
    return [
        {
            "id": row.id,
            "incidentId": row.incident_id,
            "action": row.action,
            "snapshot": json.loads(row.after_json),
            "createdAt": row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
        }
        for row in rows
    ]


@app.get("/api/core/incidents/{incident_id}/events")
def api_incident_event_list(incident_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    events = db.query(OutboxEvent).filter(
        OutboxEvent.aggregate_type == "Incident",
        OutboxEvent.aggregate_id == str(incident_id),
    ).order_by(OutboxEvent.created_at.desc()).all()
    return [json.loads(e.payload_json) for e in events]


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

@app.get("/api/core/vehicles")
def api_list_vehicles(
    status: str | None = None,
    vehicleType: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    vehicles = list_vehicles(db, status=status, vehicle_type=vehicleType)
    return {
        "content": [vehicle_to_dict(v) for v in vehicles],
        "totalElements": len(vehicles),
    }


@app.get("/api/core/vehicles/nearby")
def api_nearby_vehicles(
    latitude: float,
    longitude: float,
    radiusMeters: float,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return get_vehicles_nearby(db, latitude, longitude, radiusMeters)


@app.post("/api/core/vehicles", status_code=201)
def api_create_vehicle(
    payload: VehicleIn,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_choice(payload.vehicleType, VEHICLE_TYPES, "vehicle type")
    require_choice(payload.status, VEHICLE_STATUSES, "vehicle status")
    from sqlalchemy.exc import IntegrityError
    try:
        result = create_vehicle(
            db,
            call_sign=payload.callSign,
            vehicle_type=payload.vehicleType,
            status=payload.status,
            latitude=payload.latitude,
            longitude=payload.longitude,
            capacity=payload.capacity,
            maximum_speed_kph=payload.maximumSpeedKph,
            home_station=payload.homeStation,
            actor=actor_name(user),
        )
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Vehicle call sign already exists")


@app.get("/api/core/vehicles/{vehicle_id}")
def api_get_vehicle(vehicle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    veh = get_vehicle(db, vehicle_id)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle_to_dict(veh)


@app.patch("/api/core/vehicles/{vehicle_id}/status")
def api_update_vehicle_status(
    vehicle_id: int,
    payload: VehicleStatusUpdate,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_choice(payload.status, VEHICLE_STATUSES, "vehicle status")
    veh = get_vehicle(db, vehicle_id)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if payload.version is not None and payload.version != veh.version:
        raise HTTPException(status_code=409, detail="Vehicle version conflict")
    result = update_vehicle_status(db, veh, new_status=payload.status, actor=actor_name(user))
    db.commit()
    return result


@app.patch("/api/core/vehicles/{vehicle_id}/location")
def api_update_vehicle_location(
    vehicle_id: int,
    payload: VehicleLocationUpdate,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    veh = get_vehicle(db, vehicle_id)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if payload.version is not None and payload.version != veh.version:
        raise HTTPException(status_code=409, detail="Vehicle version conflict")
    result = update_vehicle_location(db, veh, latitude=payload.latitude, longitude=payload.longitude, actor=actor_name(user))
    db.commit()
    return result


@app.delete("/api/core/vehicles/{vehicle_id}", status_code=204, response_class=Response)
def api_delete_vehicle(
    vehicle_id: int,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> Response:
    veh = get_vehicle(db, vehicle_id)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    soft_delete_vehicle(db, veh, actor=actor_name(user))
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Dispatches
# ---------------------------------------------------------------------------

@app.post("/api/core/dispatch")
def api_create_dispatch(
    payload: DispatchRequest,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    inc = get_incident(db, payload.incidentId)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    if payload.vehicleType:
        require_choice(payload.vehicleType, VEHICLE_TYPES, "vehicle type")

    # Use deterministic ranking
    ranked_recs = rank_vehicles_for_incident(db, inc, payload.vehicleType)
    ranked_available = [rec for rec in ranked_recs if rec["vehicle"]["status"] == "AVAILABLE"]

    assignments = []
    warnings = []

    for rec in ranked_available[:payload.requestedVehicleCount]:
        vehicle = get_vehicle(db, rec["vehicle"]["id"])
        if not vehicle:
            continue
        assignment = create_dispatch_assignment(
            db,
            incident=inc,
            vehicle=vehicle,
            priority=payload.priority,
            actor=actor_name(user),
        )
        # Include scoring breakdown in the response
        assignment["score"] = rec["score"]
        assignment["reasons"] = rec["reasons"]
        assignments.append(assignment)

    if len(assignments) < payload.requestedVehicleCount:
        warnings.append("Insufficient available vehicles for full dispatch request.")

    if assignments:
        inc.status = "DISPATCHED"
        inc.updated_at = datetime.now(timezone.utc)
        inc.version += 1
        db.flush()

        # History for dispatch
        ts = datetime.now(timezone.utc)
        db.add(IncidentHistory(
            incident_id=inc.id,
            action="DISPATCHED",
            before_json=None,
            after_json=json.dumps(incident_to_dict(inc)),
            created_at=ts,
        ))

    result = {"incidentId": payload.incidentId, "assignments": assignments, "warnings": warnings}
    ts = datetime.now(timezone.utc)
    _write_outbox(db, "VEHICLE_DISPATCHED", "Dispatch", str(payload.incidentId), result, ts)
    _write_audit(db, "DISPATCH_CREATED", "Dispatch", str(payload.incidentId), "SUCCESS", result, None, None, ts)
    db.commit()
    return result


@app.get("/api/core/dispatch/recommend")
def api_recommend_vehicles(
    incidentId: int,
    vehicleType: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    inc = get_incident(db, incidentId)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if vehicleType:
        require_choice(vehicleType, VEHICLE_TYPES, "vehicle type")
    return rank_vehicles_for_incident(db, inc, vehicleType)


@app.get("/api/core/dispatches")
def api_list_dispatches(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    dispatches = list_dispatches(db)
    return {
        "content": [_dispatch_to_dict(d) for d in dispatches],
        "totalElements": len(dispatches),
    }


@app.get("/api/core/dispatches/{dispatch_id}")
def api_get_dispatch(dispatch_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    d = get_dispatch(db, dispatch_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return _dispatch_to_dict(d)


@app.patch("/api/core/dispatches/{dispatch_id}/status")
def api_update_dispatch_status(
    dispatch_id: int,
    payload: DispatchStatusUpdate,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    target_status = payload.status.upper().replace(" ", "_")
    mapping = {
        "CREATED": "ASSIGNED",
    }
    target_status = mapping.get(target_status, target_status)
    
    require_choice(target_status, DISPATCH_STATUSES, "dispatch status")
    
    d = get_dispatch(db, dispatch_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dispatch not found")
        
    try:
        result = update_dispatch_status(db, d, new_status=target_status, actor=actor_name(user))
        db.commit()
        return result
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@app.get("/api/core/environment/current")
def api_environment_current(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    reading = get_latest_reading(db)
    if not reading:
        result = create_synthetic_reading(db)
        db.commit()
        return result
    return _reading_to_dict(reading)


@app.get("/api/core/environment/history")
def api_environment_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    readings = get_environment_history(db)
    return {
        "content": [_reading_to_dict(r) for r in readings],
        "totalElements": len(readings),
    }


@app.post("/api/core/environment/refresh")
def api_environment_refresh(user: User = Depends(require_roles(*MUTATION_ROLES)), db: Session = Depends(get_db)) -> dict[str, Any]:
    result = create_synthetic_reading(db)
    ts = datetime.now(timezone.utc)
    _write_outbox(db, "ENVIRONMENT_UPDATED", "EnvironmentalReading", result.get("timestamp", ""), result, ts)
    _write_audit(db, "ENVIRONMENT_REFRESHED", "EnvironmentalReading", result.get("timestamp", ""), "SUCCESS", result, actor_name(user), None, ts)
    db.commit()
    return result


@app.get("/api/core/environment/sources")
def api_environment_sources(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"sources": [{"name": "synthetic-local", "quality": "SYNTHETIC", "requiresApiKey": False}]}


# ---------------------------------------------------------------------------
# Persisted simulations
# ---------------------------------------------------------------------------

@app.post("/api/core/simulations/run")
@app.post("/api/v1/simulations/run")
def api_run_persisted_simulation(
    payload: SimulationRunRequest,
    user: User = Depends(require_roles(*MUTATION_ROLES)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = run_and_persist(db, payload, actor=actor_name(user))
    ts = utcnow()
    _write_outbox(db, "SIMULATION_RUN_COMPLETED", "SimulationRun", str(result["runId"]), result, ts)
    _write_audit(db, "SIMULATION_RUN_COMPLETED", "SimulationRun", str(result["runId"]), "SUCCESS", result, actor_name(user), None, ts)
    db.commit()
    return result


@app.get("/api/core/simulations/runs")
@app.get("/api/v1/simulations/runs")
def api_list_simulation_runs(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    runs = list_runs(db, limit=limit)
    return {"content": runs, "totalElements": len(runs)}


@app.get("/api/core/simulations/runs/{run_id}")
@app.get("/api/v1/simulations/runs/{run_id}")
def api_get_simulation_run(
    run_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    from app.simulation_persistence import run_to_dict
    return run_to_dict(run)


@app.post("/api/core/simulations/compare")
@app.post("/api/v1/simulations/compare")
def api_compare_simulation_runs(
    payload: CompareRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = compare_runs(db, payload.runIds)
    if result.get("missingRunIds"):
        raise HTTPException(status_code=404, detail=result)
    return result


@app.get("/api/core/simulations/runs/{run_id}/export")
@app.get("/api/v1/simulations/runs/{run_id}/export")
def api_export_simulation_run(
    run_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    media_type, payload = export_run(run, format)
    extension = "csv" if format == "csv" else "json"
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="urbanshield-simulation-{run_id}.{extension}"'},
    )


# ---------------------------------------------------------------------------
# Audit & Outbox
# ---------------------------------------------------------------------------

@app.get("/api/core/audit")
def api_audit_log(user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)) -> dict[str, Any]:
    logs = get_audit_logs(db)
    return {
        "content": [
            {
                "id": log.id,
                "timestamp": log.created_at.isoformat() if isinstance(log.created_at, datetime) else str(log.created_at),
                "action": log.action,
                "resource_type": log.entity_type,
                "resource_id": log.entity_id,
                "result": log.result,
                "correlation_id": log.correlation_id,
                "details": log.metadata_json or "{}",
            }
            for log in logs
        ],
        "totalElements": len(logs),
    }


@app.get("/api/core/outbox")
def api_outbox_status(user: User = Depends(require_roles(*AUDIT_ROLES)), db: Session = Depends(get_db)) -> dict[str, Any]:
    return get_outbox_status(db)


@app.get("/api/core/metrics")
@app.get("/api/v1/system/metrics")
def api_core_metrics(db: Session = Depends(get_db)) -> Response:
    incident_count = db.query(Incident).filter(Incident.deleted_at.is_(None)).count()
    vehicle_count = db.query(Vehicle).filter(Vehicle.deleted_at.is_(None)).count()
    dispatch_count = db.query(Dispatch).count()
    simulation_count = db.query(SimulationRun).count()
    outbox_pending = db.query(OutboxEvent).filter(OutboxEvent.status == "PENDING").count()
    lines = [
        "# HELP urbanshield_core_incidents_total Current non-deleted incidents.",
        "# TYPE urbanshield_core_incidents_total gauge",
        f"urbanshield_core_incidents_total {incident_count}",
        "# HELP urbanshield_core_vehicles_total Current non-deleted emergency vehicles.",
        "# TYPE urbanshield_core_vehicles_total gauge",
        f"urbanshield_core_vehicles_total {vehicle_count}",
        "# HELP urbanshield_core_dispatches_total Dispatch records.",
        "# TYPE urbanshield_core_dispatches_total gauge",
        f"urbanshield_core_dispatches_total {dispatch_count}",
        "# HELP urbanshield_core_simulation_runs_total Persisted simulation runs.",
        "# TYPE urbanshield_core_simulation_runs_total gauge",
        f"urbanshield_core_simulation_runs_total {simulation_count}",
        "# HELP urbanshield_core_outbox_pending_total Pending outbox events.",
        "# TYPE urbanshield_core_outbox_pending_total gauge",
        f"urbanshield_core_outbox_pending_total {outbox_pending}",
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
