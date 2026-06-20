from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ALLOWED_ORIGINS = os.environ.get(
    "AI_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
).split(",")
AI_PROVIDER = os.environ.get("URBANSHIELD_AI_PROVIDER", "fallback")
ALLOW_REMOTE_AI = os.environ.get("URBANSHIELD_ALLOW_REMOTE_AI", "false").lower() in {"1", "true", "yes"}

app = FastAPI(title="UrbanShield AI Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvidenceItem(BaseModel):
    id: str
    kind: str
    summary: str


class AIRequest(BaseModel):
    incident: dict[str, Any] | None = None
    dispatches: list[dict[str, Any]] = Field(default_factory=list)
    simulation: dict[str, Any] | None = None
    notes: str | None = None


def evidence_id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def fallback_response(operation: str, payload: AIRequest) -> dict[str, Any]:
    incident = payload.incident or {}
    severity = int(incident.get("severity") or payload.simulation.get("severity", 1) if payload.simulation else incident.get("severity", 1) or 1)
    risk = int(payload.simulation.get("risk_score", severity * 15) if payload.simulation else severity * 15)
    recommended_priority = min(5, max(1, round((severity + (risk / 25)) / 2)))
    warnings: list[str] = []
    if severity >= 4:
        warnings.append("High-severity incident should stay visible to operators until resolved.")
    if not payload.dispatches:
        warnings.append("No dispatch evidence was provided; response uses deterministic fallback only.")
    evidence = [
        EvidenceItem(id=evidence_id("incident", incident), kind="incident", summary=f"Severity {severity} operational record."),
        EvidenceItem(id=evidence_id("operation", operation), kind="operation", summary=f"Fallback task {operation}."),
    ]
    return {
        "operation": operation,
        "provider": "fallback",
        "model": "deterministic-local",
        "fallbackUsed": True,
        "confidence": 0.58,
        "recommendedPriority": recommended_priority,
        "summary": f"{operation.replace('-', ' ').title()} generated from deterministic local rules.",
        "recommendations": [
            "Confirm incident location and current fleet availability.",
            "Prefer nearest available unit with compatible vehicle type.",
            "Record operator decision and keep audit trail attached to the incident.",
        ],
        "warnings": warnings,
        "evidence": [item.model_dump() for item in evidence],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/ai/health")
def health() -> dict[str, Any]:
    status = "DEGRADED" if AI_PROVIDER == "fallback" else "UP"
    return {
        "service": "ai-service",
        "status": status,
        "provider": AI_PROVIDER,
        "remoteProviderAllowed": ALLOW_REMOTE_AI,
        "fallbackAvailable": True,
    }


@app.get("/api/ai/models")
def models() -> dict[str, Any]:
    return {
        "provider": AI_PROVIDER,
        "models": [{"id": "deterministic-local", "status": "available", "fallback": True}],
        "remoteProviderAllowed": ALLOW_REMOTE_AI,
    }


@app.post("/api/ai/incident-priority")
def incident_priority(payload: AIRequest) -> dict[str, Any]:
    return fallback_response("incident-priority", payload)


@app.post("/api/ai/dispatch-brief")
def dispatch_brief(payload: AIRequest) -> dict[str, Any]:
    return fallback_response("dispatch-brief", payload)


@app.post("/api/ai/scenario-explanation")
def scenario_explanation(payload: AIRequest) -> dict[str, Any]:
    if not payload.simulation:
        raise HTTPException(status_code=422, detail="simulation evidence is required")
    return fallback_response("scenario-explanation", payload)
