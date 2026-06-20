from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_ai_health_degraded_with_fallback() -> None:
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    assert response.json()["fallbackAvailable"] is True


def test_ai_fallback_incident_priority_has_evidence() -> None:
    response = client.post("/api/ai/incident-priority", json={"incident": {"id": 1, "severity": 4}})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "fallback"
    assert body["fallbackUsed"] is True
    assert body["evidence"]
