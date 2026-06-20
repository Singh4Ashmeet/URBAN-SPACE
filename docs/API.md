# UrbanShield API

## Gateway

- `GET /health`
- `GET /health/services`
- `GET /metrics`
- `/core/*` proxies to the persistent core API.
- `/simulation/*` proxies to the simulation service.

Gateway responses include `X-Correlation-ID` when a request is proxied or an error is generated.

## Core API

- `GET /core/api/core/health`
- `GET /core/api/core/incidents`
- `GET /core/api/core/incidents/{id}`
- `POST /core/api/core/incidents`
- `PUT /core/api/core/incidents/{id}`
- `PATCH /core/api/core/incidents/{id}/status`
- `DELETE /core/api/core/incidents/{id}`
- `GET /core/api/core/incidents/summary`
- `GET /core/api/core/incidents/nearby`
- `GET /core/api/core/incidents/{id}/history`
- `GET /core/api/core/incidents/{id}/events`

## Vehicles And Dispatch

- `GET /core/api/core/vehicles`
- `GET /core/api/core/vehicles/{id}`
- `POST /core/api/core/vehicles`
- `PATCH /core/api/core/vehicles/{id}/status`
- `PATCH /core/api/core/vehicles/{id}/location`
- `DELETE /core/api/core/vehicles/{id}`
- `GET /core/api/core/vehicles/nearby`
- `POST /core/api/core/dispatch`
- `GET /core/api/core/dispatches`
- `GET /core/api/core/dispatches/{id}`
- `PATCH /core/api/core/dispatches/{id}/status`

## Environment, Audit, And Outbox

- `GET /core/api/core/environment/current`
- `GET /core/api/core/environment/history`
- `POST /core/api/core/environment/refresh`
- `GET /core/api/core/environment/sources`
- `GET /core/api/core/audit`
- `GET /core/api/core/outbox`

Direct SSE endpoint:

- `GET http://localhost:8080/api/core/incidents/events`

## Simulation API

- `GET /simulation/api/simulation/health`
- `POST /simulation/api/simulation/run`

Direct WebSocket endpoint:

- `ws://localhost:8002/api/simulation/ws/progress`

## Phase 4 Planned APIs

Authentication, persisted scenarios, scenario comparison, Redis event publishing, and ML APIs are planned but not implemented in the current local foundation.
