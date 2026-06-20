import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="UrbanShield Local Core Fallback", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Incident(BaseModel):
    id: int | None = None
    title: str = Field(min_length=1)
    description: str | None = None
    incidentType: str
    severity: int = Field(ge=1, le=5)
    status: str = "REPORTED"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    reportedAt: str | None = None
    updatedAt: str | None = None


INCIDENTS: list[Incident] = [
    Incident(id=1, title="Demo bridge lane collision", description="Local fallback demo incident.", incidentType="ACCIDENT", severity=3, status="VERIFIED", latitude=28.6139, longitude=77.2090),
    Incident(id=2, title="Demo market smoke report", description="Local fallback demo incident.", incidentType="FIRE", severity=4, status="IN_PROGRESS", latitude=28.6160, longitude=77.2150),
    Incident(id=3, title="Demo underpass waterlogging", description="Local fallback demo incident.", incidentType="FLOOD", severity=2, status="REPORTED", latitude=28.6075, longitude=77.2045),
    Incident(id=4, title="Demo arterial road closure", description="Local fallback demo incident.", incidentType="ROAD_CLOSURE", severity=3, status="VERIFIED", latitude=28.6210, longitude=77.1990),
    Incident(id=5, title="Demo medical assistance request", description="Local fallback demo incident.", incidentType="MEDICAL_EMERGENCY", severity=5, status="IN_PROGRESS", latitude=28.6195, longitude=77.2114),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def with_timestamps(incident: Incident) -> Incident:
    if incident.reportedAt is None:
        incident.reportedAt = now()
    incident.updatedAt = now()
    return incident


for seed in INCIDENTS:
    with_timestamps(seed)


@app.get("/api/core/health")
def health() -> dict[str, str]:
    return {"service": "core-service-local-fallback", "status": "UP"}


@app.get("/api/core/incidents")
def list_incidents(
    status: str | None = None,
    incidentType: str | None = None,
    minimumSeverity: int | None = Query(default=None, ge=1, le=5),
    maximumSeverity: int | None = Query(default=None, ge=1, le=5),
    page: int = 0,
    size: int = 100,
) -> dict[str, Any]:
    items = INCIDENTS
    if status:
        items = [item for item in items if item.status == status]
    if incidentType:
        items = [item for item in items if item.incidentType == incidentType]
    if minimumSeverity:
        items = [item for item in items if item.severity >= minimumSeverity]
    if maximumSeverity:
        items = [item for item in items if item.severity <= maximumSeverity]
    start = page * size
    content = items[start : start + size]
    return {"content": [item.model_dump() for item in content], "totalElements": len(items), "number": page, "size": size}


@app.get("/api/core/incidents/summary")
def summary() -> dict[str, Any]:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_severity: dict[int, int] = {}
    for item in INCIDENTS:
        by_type[item.incidentType] = by_type.get(item.incidentType, 0) + 1
        by_status[item.status] = by_status.get(item.status, 0) + 1
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    resolved = by_status.get("RESOLVED", 0)
    cancelled = by_status.get("CANCELLED", 0)
    average = round(sum(item.severity for item in INCIDENTS) / max(len(INCIDENTS), 1), 2)
    return {
        "totalIncidents": len(INCIDENTS),
        "activeIncidents": len(INCIDENTS) - resolved - cancelled,
        "resolvedIncidents": resolved,
        "byType": by_type,
        "byStatus": by_status,
        "bySeverity": by_severity,
        "averageSeverity": average,
    }


@app.get("/api/core/incidents/nearby")
def nearby(latitude: float, longitude: float, radiusMeters: float) -> list[dict[str, Any]]:
    return [item.model_dump() for item in INCIDENTS]


@app.get("/api/core/incidents/events")
async def incident_events() -> StreamingResponse:
    async def stream():
        yield ": connected\n\n"
        while True:
            await asyncio.sleep(25)
            yield ": heartbeat\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/core/incidents/{incident_id}")
def get_incident(incident_id: int) -> dict[str, Any]:
    for item in INCIDENTS:
        if item.id == incident_id:
            return item.model_dump()
    raise HTTPException(status_code=404, detail="Incident not found")


@app.post("/api/core/incidents", status_code=201)
def create_incident(incident: Incident) -> dict[str, Any]:
    next_id = max((item.id or 0 for item in INCIDENTS), default=0) + 1
    incident.id = next_id
    INCIDENTS.insert(0, with_timestamps(incident))
    return incident.model_dump()


@app.patch("/api/core/incidents/{incident_id}/status")
def update_status(incident_id: int, payload: dict[str, str]) -> dict[str, Any]:
    for item in INCIDENTS:
        if item.id == incident_id:
            item.status = payload["status"]
            item.updatedAt = now()
            return item.model_dump()
    raise HTTPException(status_code=404, detail="Incident not found")


@app.delete("/api/core/incidents/{incident_id}", status_code=204)
def delete_incident(incident_id: int) -> None:
    for index, item in enumerate(INCIDENTS):
        if item.id == incident_id:
            INCIDENTS.pop(index)
            return
    raise HTTPException(status_code=404, detail="Incident not found")
