# UrbanShield Project Plan

## 1. Problem Statement

Cities need faster, more reliable ways to monitor civic incidents, understand operational risk, and simulate emergency response decisions before those decisions affect real people. Many city dashboards only show static reports, while many simulation tools are too heavy, cloud-dependent, or expensive for local prototyping.

UrbanShield addresses this gap by providing a local-first smart city digital twin prototype. It lets users view incidents, manage response data, run deterministic emergency scenarios, and inspect service health through a practical development stack that works without Docker by default.

## 2. Proposed Solution

UrbanShield is a multi-service application that combines:

- A map-first Next.js dashboard for monitoring incidents and simulations.
- A lightweight Python gateway that routes API traffic and adds operational safeguards.
- A persistent local core API for incidents, vehicles, dispatches, environment readings, audit records, and outbox events.
- A FastAPI simulation service for deterministic emergency scenario modeling.
- An optional Spring Boot/PostGIS/Docker Compose stack for containerized and geospatial expansion.

The project is designed for local development first, with Docker kept optional. This keeps the system easy to run, inspect, and extend while still preserving a path toward more production-like infrastructure.

## 3. Project Goals

- Provide a working smart city monitoring dashboard.
- Support incident creation, filtering, updates, deletion, history, and realtime events.
- Support emergency vehicle and dispatch workflows.
- Run deterministic simulations using incident type, severity, location, traffic, weather, vehicles, road blocks, and duration.
- Keep development accessible with `python start.py` as the default entry point.
- Preserve optional Docker, Spring Boot, PostgreSQL/PostGIS, and Kong paths for future expansion.
- Add tests for meaningful behavior changes across services.

## 4. Current Architecture

Default local mode:

```text
Browser / Next.js frontend :3000
        |
        v
Local Python gateway :8000
   |                 |
   v                 v
Core API :8080       FastAPI simulation service :8002
   |
   v
Local SQLite-backed data store
```

Realtime channels currently connect directly:

- Incident Server-Sent Events: `http://localhost:8080/api/core/incidents/events`
- Simulation WebSocket progress: `ws://localhost:8002/api/simulation/ws/progress`

Optional Docker mode keeps the earlier containerized architecture available with Kong, Spring Boot, and PostgreSQL/PostGIS.

## 5. Repository Structure

```text
UrbanShield/
  core-api/              Local Python core API
  core-service/          Optional Spring Boot core service
  database/init/         Database bootstrap SQL
  docs/                  Architecture, API, security, data, and model docs
  frontend/              Next.js dashboard, components, hooks, assets, tests
  gateway/               Optional Kong gateway configuration
  local-runtime/         Local Python gateway and fallback runtime helpers
  simulation-service/    FastAPI deterministic simulation service
  tests/integration/     Cross-service integration tests
  start.py               Main local orchestration script
  docker-compose.yml     Optional Docker Compose stack
```

## 6. Main Features

### Incident Management

UrbanShield supports incident CRUD workflows with status updates, severity levels, filters, summaries, nearby lookup, history, and realtime event streaming. Incidents include title, description, incident type, severity, status, latitude, longitude, reported time, and update time.

### Emergency Operations

The local core API includes emergency vehicles, dispatches, synthetic environmental readings, audit records, and outbox records. Vehicle data includes call sign, vehicle type, status, location, capacity, speed, assigned incident, and version.

### Scenario Simulation

The simulation service models emergency response scenarios using deterministic rules. Inputs include incident type, severity, coordinates, number of vehicles, traffic level, weather condition, road block state, and simulation duration. Outputs can be used to inspect response estimates, operational warnings, and generated incident data.

### Frontend Dashboard

The frontend provides a map-first interface using Next.js, React, Tailwind CSS, MapLibre, and reusable components. It includes incident lists, filters, summary cards, charts, scenario builder views, offline support, and PWA assets.

### Gateway And Observability

The local Python gateway handles request routing, correlation IDs, rate limits, request body limits, upstream timeouts, CORS, security headers, health checks, and Prometheus-style metrics.

## 7. API Overview

Important local URLs:

- Frontend: `http://localhost:3000`
- Gateway: `http://localhost:8000`
- Gateway health: `http://localhost:8000/health`
- Service health: `http://localhost:8000/health/services`
- Metrics: `http://localhost:8000/metrics`
- Core health: `http://localhost:8000/core/api/core/health`
- Incidents: `http://localhost:8000/core/api/core/incidents`
- Vehicles: `http://localhost:8000/core/api/core/vehicles`
- Dispatches: `http://localhost:8000/core/api/core/dispatches`
- Environment: `http://localhost:8000/core/api/core/environment/current`
- Simulation: `http://localhost:8000/simulation/api/simulation/run`

## 8. Development Workflow

Recommended local workflow:

```powershell
python start.py
python start.py --health-report
python start.py --test
```

Useful commands:

```powershell
python start.py --build
python start.py --restart
python start.py --status
python start.py --stop
python start.py --migrate
python start.py --seed
python start.py --reset-db
```

Frontend workflow:

```powershell
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
npm test
```

Python service workflow:

```powershell
cd core-api
..\.venv\Scripts\python.exe -m pytest
```

```powershell
cd simulation-service
pytest
```

Optional Java service workflow:

```powershell
cd core-service
mvn test
```

Optional Docker workflow:

```powershell
docker compose up --build
docker compose down
```

## 9. Testing Strategy

Testing should focus on behavior, not implementation details.

- Use `pytest` for Python API and simulation-service tests.
- Use Maven/Spring tests for the optional Java core service.
- Use frontend tests in `frontend/tests/*.test.tsx` for dashboard behavior.
- Use `tests/integration/` for gateway and cross-service flows.
- Run `python start.py --test` before submitting broad changes.

Every change that affects API behavior, simulation results, persistence, gateway behavior, or UI workflows should include or update tests.

## 10. Security And Configuration

- Do not commit real secrets.
- Use `.env.example` files as templates for local `.env` files.
- Keep Docker optional and preserve the no-Docker local workflow.
- Avoid paid services or API-key-only dependencies unless explicitly approved.
- Preserve gateway safeguards such as correlation IDs, timeouts, CORS, security headers, body limits, and rate limits.

## 11. Current Limitations

- Simulations are deterministic rule-based models, not machine learning predictions.
- Scenario history in the simulation service is not fully persisted.
- Authentication and role-based authorization are not implemented.
- PostgreSQL/PostGIS remains optional and is not the default local data path.
- Redis, event broker integration, full observability, and advanced ML services are planned but not implemented.
- Full browser end-to-end testing is not yet included.

## 12. Roadmap

### Phase 1: Local Stability

- Keep `python start.py` reliable.
- Maintain health checks and test orchestration.
- Improve local data seeding and reset workflows.

### Phase 2: Operational Workflows

- Expand vehicle dispatch features.
- Add richer incident history and audit views.
- Improve scenario result comparison and export.
- Add better offline handling for queued user actions.

### Phase 3: Persistence And Auth

- Add persisted scenario versions and simulation runs.
- Introduce users, roles, and authentication.
- Add role-aware access to incident, dispatch, and audit workflows.

### Phase 4: Production Foundation

- Add PostgreSQL/PostGIS-backed local or Docker mode.
- Add Redis or another event broker for scalable realtime workflows.
- Add observability dashboards with metrics, logs, and traces.
- Add deployment documentation for a production-like environment.

### Phase 5: Intelligence Layer

- Introduce ML-assisted risk scoring or incident prioritization.
- Compare deterministic and ML-generated recommendations.
- Document model behavior, limitations, evaluation data, and safety boundaries.

## 13. Success Criteria

UrbanShield is successful when a contributor can:

- Start the full local stack with one command.
- View, create, update, and resolve incidents from the dashboard.
- Run a simulation and understand its operational output.
- Inspect service health and metrics.
- Run tests locally.
- Extend one service without breaking the no-Docker workflow.
- Understand the architecture from the docs without needing tribal knowledge.

## 14. Contributor Notes

Keep changes scoped and practical. Prefer existing patterns over new abstractions. Update documentation when commands, URLs, environment variables, APIs, or architecture change. Add tests for behavior changes, especially around incident workflows, gateway routing, persistence, and simulation outputs.
