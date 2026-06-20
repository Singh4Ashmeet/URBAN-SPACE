"""Pydantic request/response schemas for UrbanShield Core API.

Implements the canonical error envelope, pagination wrapper, and typed
request/response models for all public endpoints.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IncidentType(str, enum.Enum):
    ACCIDENT = "ACCIDENT"
    FIRE = "FIRE"
    FLOOD = "FLOOD"
    ROAD_CLOSURE = "ROAD_CLOSURE"
    TRAFFIC_JAM = "TRAFFIC_JAM"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    PUBLIC_HAZARD = "PUBLIC_HAZARD"
    AIR_QUALITY_ALERT = "AIR_QUALITY_ALERT"
    WEATHER_ALERT = "WEATHER_ALERT"


class IncidentStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    DISPATCHED = "DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class VehicleType(str, enum.Enum):
    AMBULANCE = "AMBULANCE"
    FIRE_ENGINE = "FIRE_ENGINE"
    POLICE_CAR = "POLICE_CAR"
    RESCUE_VEHICLE = "RESCUE_VEHICLE"
    MOBILE_COMMAND_UNIT = "MOBILE_COMMAND_UNIT"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RETURNING = "RETURNING"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class DispatchStatus(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACCEPTED = "ACCEPTED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    DISPATCHER = "dispatcher"
    ADMIN = "admin"


# ---------------------------------------------------------------------------
# Shared error envelope
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated response wrapper."""
    items: list[T]
    page: int = 1
    page_size: int = 20
    total: int = 0
    has_next: bool = False


class LegacyPaginatedResponse(BaseModel, Generic[T]):
    """Legacy paginated response for backward compatibility."""
    content: list[T]
    totalElements: int = 0
    number: int = 0
    size: int = 100


# ---------------------------------------------------------------------------
# Incident schemas
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    incidentType: str
    severity: int = Field(ge=1, le=5)
    status: str = "REPORTED"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: Optional[str] = None
    assignedTeam: Optional[str] = None
    version: Optional[int] = None


class IncidentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    incidentType: str
    severity: int = Field(ge=1, le=5)
    status: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: Optional[str] = None
    assignedTeam: Optional[str] = None
    version: Optional[int] = None


class StatusUpdateRequest(BaseModel):
    status: str
    version: Optional[int] = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    incidentType: str
    severity: int
    status: str
    latitude: float
    longitude: float
    district: Optional[str] = None
    assignedTeam: Optional[str] = None
    reportedAt: str
    updatedAt: str
    resolvedAt: Optional[str] = None
    version: int


class IncidentHistoryResponse(BaseModel):
    id: int
    incidentId: int
    action: str
    snapshot: dict[str, Any] | IncidentResponse
    createdAt: str


class IncidentSummaryResponse(BaseModel):
    totalIncidents: int
    activeIncidents: int
    resolvedIncidents: int
    byType: dict[str, int]
    byStatus: dict[str, int]
    bySeverity: dict[str, int]
    averageSeverity: float


# ---------------------------------------------------------------------------
# Vehicle schemas
# ---------------------------------------------------------------------------

class VehicleCreate(BaseModel):
    callSign: str = Field(min_length=1, max_length=50)
    vehicleType: str
    status: str = "AVAILABLE"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity: int = Field(default=2, ge=1, le=50)
    maximumSpeedKph: float = Field(default=60, gt=0, le=200)
    homeStation: Optional[str] = None
    version: Optional[int] = None


class VehicleStatusUpdateRequest(BaseModel):
    status: str
    version: Optional[int] = None


class VehicleLocationUpdateRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    version: Optional[int] = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    callSign: str
    vehicleType: str
    status: str
    latitude: float
    longitude: float
    capacity: int
    maximumSpeedKph: float
    assignedIncidentId: Optional[int] = None
    homeStation: Optional[str] = None
    lastSeenAt: str
    createdAt: str
    updatedAt: str
    version: int


# ---------------------------------------------------------------------------
# Dispatch schemas
# ---------------------------------------------------------------------------

class DispatchCreate(BaseModel):
    incidentId: int
    requestedVehicleCount: int = Field(default=1, ge=1, le=10)
    priority: int = Field(default=3, ge=1, le=5)
    vehicleType: Optional[str] = None


class DispatchStatusUpdateRequest(BaseModel):
    status: str


class DispatchAssignment(BaseModel):
    dispatchId: int
    vehicle: VehicleResponse
    distanceKm: float
    estimatedArrivalMinutes: int


class DispatchCreateResponse(BaseModel):
    incidentId: int
    assignments: list[DispatchAssignment]
    warnings: list[str]


class DispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    vehicle_id: int
    status: str
    priority: int
    distance_km: float
    estimated_arrival_minutes: int
    assignment_reason: str
    dispatched_at: str
    acknowledged_at: Optional[str] = None
    arrived_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Environment schemas
# ---------------------------------------------------------------------------

class EnvironmentReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    latitude: float
    longitude: float
    temperature_c: float
    humidity_percent: float
    air_quality_index: int
    visibility_km: float
    weather_condition: str
    rainfall_mm: float
    wind_speed_kph: float
    pm25: float
    pm10: float
    observed_at: str
    source: str
    quality: str
    is_synthetic: int
    created_at: str


# ---------------------------------------------------------------------------
# Health schemas
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    service: str
    status: str
    storage: str = "sqlite"
    database: Optional[str] = None
    incidentCount: int = 0
