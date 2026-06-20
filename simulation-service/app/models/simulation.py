from enum import StrEnum
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class IncidentType(StrEnum):
    ACCIDENT = "ACCIDENT"
    FLOOD = "FLOOD"
    ROAD_CLOSURE = "ROAD_CLOSURE"
    FIRE = "FIRE"
    TRAFFIC_JAM = "TRAFFIC_JAM"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    PUBLIC_HAZARD = "PUBLIC_HAZARD"


class TrafficLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class WeatherCondition(StrEnum):
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"
    FOG = "FOG"
    STORM = "STORM"


class SimulationStatus(StrEnum):
    COMPLETED = "SIMULATION_COMPLETED"
    FAILED = "FAILED"


class SimulationRequest(BaseModel):
    scenario_name: str = Field(min_length=1)
    incident_type: IncidentType
    severity: int = Field(ge=1, le=5)
    latitude: float = Field(default=28.6139, ge=-90, le=90)
    longitude: float = Field(default=77.2090, ge=-180, le=180)
    number_of_vehicles: int = Field(default=2, ge=1, le=20)
    traffic_level: TrafficLevel = TrafficLevel.MODERATE
    weather_condition: WeatherCondition = WeatherCondition.CLEAR
    road_blocked: bool = False
    simulation_duration_minutes: int = Field(default=30, ge=5, le=240)

    @field_validator("scenario_name")
    @classmethod
    def scenario_name_must_not_be_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be empty")
        return trimmed


class SimulationResponse(BaseModel):
    simulation_id: str = Field(default_factory=lambda: str(uuid4()))
    scenario_name: str
    incident_type: IncidentType
    severity: int
    estimated_response_time_minutes: int
    estimated_affected_radius_meters: int
    recommended_vehicle_count: int
    risk_score: int
    route_distance_km: float
    warnings: list[str]
    status: SimulationStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    traffic_level: TrafficLevel = TrafficLevel.MODERATE
    road_blocked: bool = False


class RouteResponse(BaseModel):
    origin: Coordinate
    destination: Coordinate
    distance_km: float
    estimated_travel_time_minutes: int
    route_coordinates: list[Coordinate]
    warnings: list[str]


class ImpactAreaRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    incident_type: IncidentType
    severity: int = Field(ge=1, le=5)
    weather_condition: WeatherCondition = WeatherCondition.CLEAR


class ImpactAreaResponse(BaseModel):
    center: Coordinate
    radius_meters: int
    polygon_coordinates: list[Coordinate]
    warnings: list[str]
