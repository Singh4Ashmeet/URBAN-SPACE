from __future__ import annotations

import os
import tempfile

os.environ["URBANSHIELD_CORE_DB"] = os.path.join(tempfile.gettempdir(), "urbanshield-core-test.sqlite3")

from fastapi.testclient import TestClient

from app.main import app
from app.cli import migrate_database, seed_database


client = TestClient(app)


def setup_function() -> None:
    from app.db import DB_PATH
    import os
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass
    migrate_database()
    seed_database(force=True)


def auth_headers(username: str = "operator") -> dict[str, str]:
    response = client.post("/api/core/auth/login", json={"username": username, "password": "UrbanShield123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def test_health_and_incidents_are_persistent() -> None:
    health = client.get("/api/core/health")
    assert health.status_code == 200
    assert health.json()["storage"] == "sqlite"
    response = client.get("/api/core/incidents", headers=auth_headers("viewer"))
    assert response.status_code == 200
    assert response.json()["totalElements"] >= 5


def test_incident_history_and_conflict() -> None:
    created = client.post(
        "/api/core/incidents",
        json={"title": "Test", "incidentType": "PUBLIC_HAZARD", "severity": 2, "latitude": 28.61, "longitude": 77.2},
        headers=auth_headers(),
    )
    assert created.status_code == 201
    incident = created.json()
    stale = {**incident, "title": "Conflict", "version": 0}
    conflict = client.put(f"/api/core/incidents/{incident['id']}", json=stale, headers=auth_headers())
    assert conflict.status_code == 409
    status = client.patch(f"/api/core/incidents/{incident['id']}/status", json={"status": "RESOLVED", "version": incident["version"]}, headers=auth_headers())
    assert status.status_code == 200
    history = client.get(f"/api/core/incidents/{incident['id']}/history", headers=auth_headers("viewer"))
    assert history.status_code == 200
    assert len(history.json()) >= 2


def test_vehicle_dispatch_and_environment() -> None:
    vehicles = client.get("/api/core/vehicles", headers=auth_headers("viewer"))
    assert vehicles.status_code == 200
    assert vehicles.json()["totalElements"] >= 1
    dispatch = client.post("/api/core/dispatch", json={"incidentId": 1, "requestedVehicleCount": 1}, headers=auth_headers())
    assert dispatch.status_code == 200
    assert len(dispatch.json()["assignments"]) == 1
    # Check that score and reasons are returned in the assignment
    assert "score" in dispatch.json()["assignments"][0]
    assert "reasons" in dispatch.json()["assignments"][0]
    
    environment = client.get("/api/core/environment/current", headers=auth_headers("viewer"))
    assert environment.status_code == 200
    assert environment.json()["quality"] == "SYNTHETIC"


def test_deterministic_vehicle_ranking() -> None:
    # Test GET recommend vehicles
    rec = client.get("/api/core/dispatch/recommend?incidentId=1", headers=auth_headers("viewer"))
    assert rec.status_code == 200
    results = rec.json()
    assert len(results) >= 1
    for item in results:
        assert "score" in item
        assert "reasons" in item
        assert isinstance(item["reasons"], list)
        assert "vehicle" in item


def test_dispatch_state_machine_validation() -> None:
    # 1. Create a dispatch
    dispatch = client.post("/api/core/dispatch", json={"incidentId": 1, "requestedVehicleCount": 1}, headers=auth_headers())
    assert dispatch.status_code == 200
    dispatch_id = dispatch.json()["assignments"][0]["dispatchId"]
    
    # 2. ASSIGNED -> ACKNOWLEDGED (valid)
    patch1 = client.patch(f"/api/core/dispatches/{dispatch_id}/status", json={"status": "ACKNOWLEDGED"}, headers=auth_headers())
    assert patch1.status_code == 200
    assert patch1.json()["status"] == "ACKNOWLEDGED"
    
    # 3. ACKNOWLEDGED -> COMPLETED (invalid transition according to VALID_TRANSITIONS)
    patch2 = client.patch(f"/api/core/dispatches/{dispatch_id}/status", json={"status": "COMPLETED"}, headers=auth_headers())
    assert patch2.status_code == 400
    assert "Invalid dispatch transition" in patch2.json()["detail"]
    
    # 4. ACKNOWLEDGED -> EN_ROUTE (valid)
    patch3 = client.patch(f"/api/core/dispatches/{dispatch_id}/status", json={"status": "EN_ROUTE"}, headers=auth_headers())
    assert patch3.status_code == 200
    assert patch3.json()["status"] == "EN_ROUTE"
    
    # 5. EN_ROUTE -> ARRIVED (valid)
    patch4 = client.patch(f"/api/core/dispatches/{dispatch_id}/status", json={"status": "ARRIVED"}, headers=auth_headers())
    assert patch4.status_code == 200
    assert patch4.json()["status"] == "ARRIVED"
    
    # 6. ARRIVED -> COMPLETED (valid)
    patch5 = client.patch(f"/api/core/dispatches/{dispatch_id}/status", json={"status": "COMPLETED"}, headers=auth_headers())
    assert patch5.status_code == 200
    assert patch5.json()["status"] == "COMPLETED"


def test_roles_block_viewer_mutation_and_allow_audit() -> None:
    viewer = auth_headers("viewer")
    forbidden = client.post(
        "/api/core/incidents",
        json={"title": "Denied", "incidentType": "PUBLIC_HAZARD", "severity": 2, "latitude": 28.61, "longitude": 77.2},
        headers=viewer,
    )
    assert forbidden.status_code == 403

    audit = client.get("/api/core/audit", headers=auth_headers("auditor"))
    assert audit.status_code == 200
    outbox_forbidden = client.get("/api/core/outbox", headers=viewer)
    assert outbox_forbidden.status_code == 403


def test_persisted_simulations_are_deterministic_and_exportable() -> None:
    headers = auth_headers()
    payload = {
        "scenario_name": "Deterministic check",
        "incident_type": "ACCIDENT",
        "severity": 3,
        "latitude": 28.6139,
        "longitude": 77.209,
        "number_of_vehicles": 2,
        "traffic_level": "MODERATE",
        "weather_condition": "CLEAR",
        "road_blocked": False,
        "simulation_duration_minutes": 30,
    }
    first = client.post("/api/core/simulations/run", json=payload, headers=headers)
    second = client.post("/api/core/simulations/run", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["input_hash"] == second.json()["input_hash"]
    assert first.json()["risk_score"] == second.json()["risk_score"]

    compare = client.post(
        "/api/core/simulations/compare",
        json={"runIds": [first.json()["runId"], second.json()["runId"]]},
        headers=auth_headers("viewer"),
    )
    assert compare.status_code == 200
    assert compare.json()["deltas"][0]["riskScoreDelta"] == 0

    exported = client.get(f"/api/core/simulations/runs/{first.json()['runId']}/export?format=csv", headers=auth_headers("viewer"))
    assert exported.status_code == 200
    assert "risk_score" in exported.text
