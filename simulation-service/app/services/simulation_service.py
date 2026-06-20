from datetime import datetime, timezone

from app.models.simulation import (
    Coordinate,
    ImpactAreaRequest,
    ImpactAreaResponse,
    IncidentType,
    RouteRequest,
    RouteResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationStatus,
    TrafficLevel,
    WeatherCondition,
)
from app.repositories.scenario_repository import scenario_repository
from app.utils.geo import approximate_circle, haversine_km

INCIDENT_BASE_MINUTES: dict[IncidentType, int] = {
    IncidentType.ACCIDENT: 6,
    IncidentType.FLOOD: 10,
    IncidentType.ROAD_CLOSURE: 8,
    IncidentType.FIRE: 7,
    IncidentType.TRAFFIC_JAM: 5,
    IncidentType.MEDICAL_EMERGENCY: 5,
    IncidentType.PUBLIC_HAZARD: 7,
}

TRAFFIC_MULTIPLIERS: dict[TrafficLevel, float] = {
    TrafficLevel.LOW: 0.9,
    TrafficLevel.MODERATE: 1.0,
    TrafficLevel.HIGH: 1.3,
    TrafficLevel.SEVERE: 1.65,
}

WEATHER_MULTIPLIERS: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 1.0,
    WeatherCondition.RAIN: 1.15,
    WeatherCondition.HEAVY_RAIN: 1.35,
    WeatherCondition.FOG: 1.25,
    WeatherCondition.STORM: 1.55,
}


def run_simulation(request: SimulationRequest) -> SimulationResponse:
    started_at = datetime.now(timezone.utc)
    base_minutes = INCIDENT_BASE_MINUTES[request.incident_type]
    route = calculate_route(
        RouteRequest(
            origin=Coordinate(latitude=request.latitude, longitude=request.longitude),
            destination=Coordinate(latitude=28.6180, longitude=77.2050),
            traffic_level=request.traffic_level,
            road_blocked=request.road_blocked,
        )
    )
    vehicle_discount = min((request.number_of_vehicles - 1) * 0.75, 4.0)
    estimated_minutes = round(
        ((base_minutes + request.severity * 2 + route.estimated_travel_time_minutes) * TRAFFIC_MULTIPLIERS[request.traffic_level]
        * WEATHER_MULTIPLIERS[request.weather_condition])
        + (5 if request.road_blocked else 0)
        - vehicle_discount
    )
    estimated_minutes = max(4, estimated_minutes)
    impact = calculate_impact_area(
        ImpactAreaRequest(
            latitude=request.latitude,
            longitude=request.longitude,
            incident_type=request.incident_type,
            severity=request.severity,
            weather_condition=request.weather_condition,
        )
    )
    recommended = min(10, max(1, request.severity + (1 if request.incident_type in {IncidentType.FIRE, IncidentType.FLOOD} else 0)))
    risk_score = min(100, round(request.severity * 13 + estimated_minutes * 1.4 + impact.radius_meters / 80))
    warnings = [*route.warnings, *impact.warnings]
    if request.number_of_vehicles < recommended:
        warnings.append("Entered vehicle count is below the deterministic recommendation.")
    result = SimulationResponse(
        scenario_name=request.scenario_name,
        incident_type=request.incident_type,
        severity=request.severity,
        estimated_response_time_minutes=estimated_minutes,
        estimated_affected_radius_meters=impact.radius_meters,
        recommended_vehicle_count=recommended,
        risk_score=risk_score,
        route_distance_km=route.distance_km,
        warnings=warnings,
        status=SimulationStatus.COMPLETED,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )
    return scenario_repository.save(result)


def list_scenarios() -> list[SimulationResponse]:
    return scenario_repository.list_recent()


def get_scenario(simulation_id: str) -> SimulationResponse | None:
    return scenario_repository.get(simulation_id)


def calculate_route(request: RouteRequest) -> RouteResponse:
    direct_distance = haversine_km(request.origin, request.destination)
    route_factor = 1.35 + (0.25 if request.road_blocked else 0)
    distance = round(max(0.1, direct_distance * route_factor), 2)
    average_speed_kmh = {
        TrafficLevel.LOW: 38,
        TrafficLevel.MODERATE: 30,
        TrafficLevel.HIGH: 22,
        TrafficLevel.SEVERE: 14,
    }[request.traffic_level]
    minutes = max(2, round((distance / average_speed_kmh) * 60))
    warnings: list[str] = []
    if request.traffic_level in {TrafficLevel.HIGH, TrafficLevel.SEVERE}:
        warnings.append("Traffic level increases travel time.")
    if request.road_blocked:
        warnings.append("Road blocked flag added a rerouting penalty.")
    mid = Coordinate(
        latitude=(request.origin.latitude + request.destination.latitude) / 2 + 0.002,
        longitude=(request.origin.longitude + request.destination.longitude) / 2 - 0.002,
    )
    return RouteResponse(
        origin=request.origin,
        destination=request.destination,
        distance_km=distance,
        estimated_travel_time_minutes=minutes,
        route_coordinates=[request.origin, mid, request.destination],
        warnings=warnings,
    )


def calculate_impact_area(request: ImpactAreaRequest) -> ImpactAreaResponse:
    base = {
        IncidentType.ACCIDENT: 120,
        IncidentType.FIRE: 240,
        IncidentType.FLOOD: 300,
        IncidentType.ROAD_CLOSURE: 180,
        IncidentType.TRAFFIC_JAM: 160,
        IncidentType.MEDICAL_EMERGENCY: 90,
        IncidentType.PUBLIC_HAZARD: 180,
    }[request.incident_type]
    weather_bonus = 80 if request.weather_condition in {WeatherCondition.HEAVY_RAIN, WeatherCondition.STORM} else 0
    radius = base + request.severity * 75 + weather_bonus
    center = Coordinate(latitude=request.latitude, longitude=request.longitude)
    warnings = []
    if request.incident_type in {IncidentType.FIRE, IncidentType.FLOOD}:
        warnings.append("Incident type increases the affected area.")
    return ImpactAreaResponse(
        center=center,
        radius_meters=radius,
        polygon_coordinates=approximate_circle(center, radius),
        warnings=warnings,
    )
