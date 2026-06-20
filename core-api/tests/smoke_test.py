"""Quick smoke test for the refactored Core API."""
import json
import urllib.request

BASE = "http://127.0.0.1:8080"

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())

# Health
health = get("/api/core/health")
assert health["status"] == "UP", f"Health not UP: {health}"
print(f"Health: {health['status']} - Incidents: {health.get('incidentCount')}")

# Incidents
data = get("/api/core/incidents")
assert "content" in data, "No content key in incidents response"
assert "totalElements" in data, "No totalElements key"
print(f"Incidents: {data['totalElements']} total, {len(data['content'])} in page")
if data["content"]:
    inc = data["content"][0]
    assert "version" in inc, "No version field on incident"
    print(f"  First: {inc['title']} (type={inc['incidentType']}, severity={inc['severity']}, version={inc['version']})")

# Summary
summary = get("/api/core/incidents/summary")
print(f"Summary: total={summary['totalIncidents']}, active={summary['activeIncidents']}")

# Vehicles
vehicles = get("/api/core/vehicles")
print(f"Vehicles: {vehicles['totalElements']} total")
if vehicles["content"]:
    v = vehicles["content"][0]
    assert "version" in v, "No version field on vehicle"
    print(f"  First: {v['callSign']} ({v['vehicleType']}, version={v['version']})")

# Audit
audit = get("/api/core/audit")
print(f"Audit logs: {audit['totalElements']}")

# Environment
env_data = get("/api/core/environment/current")
print(f"Environment: {env_data['weather_condition']}, temp={env_data['temperature_c']}C")

# Dispatches
dispatches = get("/api/core/dispatches")
print(f"Dispatches: {dispatches['totalElements']}")

# Outbox
outbox = get("/api/core/outbox")
print(f"Outbox status counts: {outbox['statusCounts']}")

# Nearby vehicles
nearby = get("/api/core/vehicles/nearby?latitude=28.6139&longitude=77.209&radiusMeters=5000")
print(f"Nearby vehicles: {len(nearby)}")

# Test incident history endpoint
if data["content"]:
    inc_id = data["content"][0]["id"]
    history = get(f"/api/core/incidents/{inc_id}/history")
    print(f"Incident {inc_id} history entries: {len(history)}")

print()
print("ALL API SMOKE TESTS PASSED")
