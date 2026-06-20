# UrbanShield Data Dictionary

## Current Local Core Incident

| Field | Meaning |
| --- | --- |
| `id` | Numeric incident identifier |
| `title` | Short incident title |
| `description` | Incident details |
| `incidentType` | Incident category |
| `severity` | Severity from 1 to 5 |
| `status` | Incident lifecycle status |
| `latitude` | Latitude |
| `longitude` | Longitude |
| `reportedAt` | Creation timestamp |
| `updatedAt` | Last update timestamp |

## Planned Phase 4 Entities

- Persisted scenarios
- Scenario versions
- Simulation runs
- Users and roles

## Current Emergency Vehicle

| Field | Meaning |
| --- | --- |
| `id` | Numeric vehicle identifier |
| `callSign` | Public operational identifier |
| `vehicleType` | Vehicle category |
| `status` | Fleet lifecycle status |
| `latitude` | Last known latitude |
| `longitude` | Last known longitude |
| `capacity` | Crew/resource capacity |
| `maximumSpeedKph` | Planning speed |
| `assignedIncidentId` | Current incident assignment |
| `version` | Optimistic concurrency version |

## Current Dispatch

| Field | Meaning |
| --- | --- |
| `id` | Numeric dispatch identifier |
| `incident_id` | Assigned incident |
| `vehicle_id` | Assigned vehicle |
| `status` | Dispatch lifecycle status |
| `distance_km` | Estimated distance |
| `estimated_arrival_minutes` | Estimated arrival time |
| `assignment_reason` | Human-readable explanation |
