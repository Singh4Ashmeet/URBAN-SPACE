from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_up() -> None:
    response = client.get("/api/simulation/health")

    assert response.status_code == 200
    assert response.json() == {"service": "simulation-service", "status": "UP"}


def test_successful_simulation_request() -> None:
    response = client.post(
        "/api/simulation/run",
        json={
            "scenario_name": "Demo Traffic Incident",
            "incident_type": "ACCIDENT",
            "severity": 3,
            "latitude": 28.6139,
            "longitude": 77.209,
            "number_of_vehicles": 2,
            "traffic_level": "MODERATE",
            "weather_condition": "CLEAR",
            "road_blocked": False,
            "simulation_duration_minutes": 30,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_name"] == "Demo Traffic Incident"
    assert body["incident_type"] == "ACCIDENT"
    assert body["severity"] == 3
    assert body["status"] == "SIMULATION_COMPLETED"
    assert body["estimated_response_time_minutes"] >= 4
    assert body["estimated_affected_radius_meters"] > 0
    assert body["simulation_id"]


def test_invalid_input_returns_validation_error() -> None:
    response = client.post(
        "/api/simulation/run",
        json={"scenario_name": " ", "incident_type": "ALIEN", "severity": 7},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "ValidationError"


def test_route_calculation() -> None:
    response = client.post(
        "/api/simulation/route",
        json={
            "origin": {"latitude": 28.6139, "longitude": 77.209},
            "destination": {"latitude": 28.618, "longitude": 77.205},
            "traffic_level": "HIGH",
            "road_blocked": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["distance_km"] > 0
    assert len(body["route_coordinates"]) == 3
    assert body["warnings"]


def test_impact_area_calculation() -> None:
    response = client.post(
        "/api/simulation/impact-area",
        json={
            "latitude": 28.6139,
            "longitude": 77.209,
            "incident_type": "FIRE",
            "severity": 4,
            "weather_condition": "STORM",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["radius_meters"] > 500
    assert len(body["polygon_coordinates"]) >= 16


def test_scenario_retrieval() -> None:
    created = client.post(
        "/api/simulation/run",
        json={"scenario_name": "Lookup scenario", "incident_type": "FLOOD", "severity": 2},
    ).json()

    response = client.get(f"/api/simulation/scenarios/{created['simulation_id']}")

    assert response.status_code == 200
    assert response.json()["scenario_name"] == "Lookup scenario"
