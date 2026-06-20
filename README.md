# UrbanShield

UrbanShield is a local, open-source smart city digital twin prototype built around a working no-Docker development stack: a persistent Python core API, FastAPI simulation service, lightweight Python gateway, and Next.js frontend. The Spring Boot/PostGIS/Docker Compose stack remains available as an optional containerized path.

Phase 2 turns the Phase 1 health dashboard into a functional monitoring and deterministic simulation application: seeded incidents, CRUD APIs, a map-first frontend, scenario execution, realtime update channels, PWA basics, and a root startup helper.

## Start

Recommended no-Docker local runner:

```powershell
python start.py
```

Supported `start.py` commands:

```powershell
python start.py
python start.py --build      # build and run the production frontend
python start.py --logs
python start.py --stop
python start.py --restart
python start.py --status
python start.py --clean
python start.py --mode local
python start.py --mode docker
python start.py --profile minimal
python start.py --health-report
python start.py --test
python start.py --migrate
python start.py --seed
python start.py --reset-db
python start.py --train-models
python start.py --docker
```

By default, `start.py` runs the project without Docker:

- Local persistent core API: `http://localhost:8080`
- FastAPI simulation service: `http://localhost:8002`
- Local Python gateway: `http://localhost:8000`
- Next.js frontend: `http://localhost:3000`

Use `python start.py --docker` only when you specifically want the optional Docker Compose stack and Docker Desktop is running.

Manual Docker Compose:

```powershell
docker compose up --build
docker compose down
```

## Documentation

Root documentation is kept to this README. Supporting docs live in `docs/`:

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Security](docs/SECURITY.md)
- [Data Dictionary](docs/DATA_DICTIONARY.md)
- [ML Model Card](docs/ML_MODEL_CARD.md)
- [Contributing](docs/CONTRIBUTING.md)

## Important URLs

- Frontend: `http://localhost:3000`
- Local gateway: `http://localhost:8000`
- Gateway health: `http://localhost:8000/health`
- Gateway service health: `http://localhost:8000/health/services`
- Gateway metrics: `http://localhost:8000/metrics`
- Optional Kong admin in Docker mode: `http://localhost:8001`
- Core health through gateway: `http://localhost:8000/core/api/core/health`
- Simulation health through gateway: `http://localhost:8000/simulation/api/simulation/health`
- Incidents API: `http://localhost:8000/core/api/core/incidents`
- Vehicles API: `http://localhost:8000/core/api/core/vehicles`
- Dispatch API: `http://localhost:8000/core/api/core/dispatch`
- Environment API: `http://localhost:8000/core/api/core/environment/current`
- Audit API: `http://localhost:8000/core/api/core/audit`
- Outbox API: `http://localhost:8000/core/api/core/outbox`
- Simulation API: `http://localhost:8000/simulation/api/simulation/run`
- Direct incident SSE events: `http://localhost:8080/api/core/incidents/events`
- Direct simulation WebSocket: `ws://localhost:8002/api/simulation/ws/progress`

## Architecture

The browser opens the Next.js dashboard on port `3000`. In the default local runner, API calls go through the lightweight Python gateway on port `8000`, using `/core` and `/simulation` prefixes. The gateway forwards core requests to the persistent SQLite-backed core API on `8080` and simulation requests to FastAPI on `8002`.

Realtime updates are intentionally simple for Phase 2: core incidents use Server-Sent Events from the core API, and simulation progress uses a FastAPI WebSocket. The frontend uses direct local development URLs for these realtime channels because the gateway stays intentionally minimal.

Docker mode is optional. In Docker mode, Kong forwards to the Spring Boot core service and FastAPI service inside the Docker network, and PostgreSQL/PostGIS runs as `db:5432`.

## Folder Tree

```text
UrbanShield/
  core-service/
    src/main/java/com/urbanshield/core/
    src/main/resources/db/migration/
    src/test/java/
    Dockerfile
    pom.xml
  core-api/
    app/
    tests/
    requirements.txt
  database/init/
  frontend/
    app/
    components/
    hooks/
    lib/
    public/
    tests/
    types/
    Dockerfile
    package.json
  gateway/kong.yml
  simulation-service/
    app/
    tests/
    Dockerfile
    requirements.txt
  start.py
  docker-compose.yml
  .env.example
```

## Phase 2 Features

- Incident CRUD APIs with DTOs, validation, filters, sorting, pagination, summary analytics, and nearby PostGIS search.
- Flyway migrations for PostGIS, incident schema, indexes, and fictional demo incidents.
- FastAPI deterministic scenario simulation with traffic, weather, vehicle, road-block, route, and impact-area rules.
- Recent simulation lookup stored in memory for local Phase 2 use.
- Interactive MapLibre map with incident severity markers and a 2D/3D pitch toggle.
- Accessible incident list alternative, filters, resolve/delete actions, and summary charts.
- Scenario builder with map placement, deterministic results, warnings, JSON export, draft saving, and incident creation from results.
- PWA manifest, service worker, offline fallback, cached incidents, cached scenarios, and queued draft scenarios.
- Root `start.py` launcher for cross-platform local startup and health polling.

## API Examples

Create an incident:

```powershell
$body = @{
  title = "Demo public hazard"
  description = "Fictional local test incident."
  incidentType = "PUBLIC_HAZARD"
  severity = 2
  status = "REPORTED"
  latitude = 28.6139
  longitude = 77.2090
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/core/api/core/incidents" -ContentType "application/json" -Body $body
```

Run a scenario:

```powershell
$scenario = @{
  scenario_name = "Demo fire response"
  incident_type = "FIRE"
  severity = 4
  latitude = 28.616
  longitude = 77.215
  number_of_vehicles = 3
  traffic_level = "HIGH"
  weather_condition = "RAIN"
  road_blocked = $false
  simulation_duration_minutes = 30
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/simulation/api/simulation/run" -ContentType "application/json" -Body $scenario
```

Nearby incidents:

```powershell
Invoke-RestMethod "http://localhost:8000/core/api/core/incidents/nearby?latitude=28.6139&longitude=77.209&radiusMeters=1500"
```

## Tests

All available local validation:

```powershell
python start.py --test
```

Core API:

```powershell
cd core-api
..\.venv\Scripts\python.exe -m pytest
```

Optional Java core service:

```powershell
cd core-service
mvn test
```

Python:

```powershell
cd simulation-service
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

Frontend:

```powershell
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
npm test
npm audit --omit=dev
```

Optional Docker validation:

```powershell
docker compose config --quiet
docker compose up --build
```

## PWA And Offline Mode

The frontend registers `/sw.js`, provides `/manifest.webmanifest`, and caches the application shell. The app caches the most recently loaded incidents and completed scenarios in IndexedDB. If offline, scenario drafts can be queued locally, but incident submissions are not represented as successful unless the server actually accepts them.

## Known Limitations

- Phase 2 uses deterministic rules, not machine learning.
- Phase 4 now includes a persistent SQLite-backed local core API. PostgreSQL/PostGIS, authentication, ML service, Redis event broker, and full observability stack are not implemented yet.
- The map uses OpenStreetMap raster tiles and a simple marker overlay; it is not a photorealistic city model.
- Realtime channels are direct local service URLs for reliability in this minimal gateway setup.
- Scenario history is in memory in the simulation service and resets when that container restarts.
- End-to-end Playwright tests and full axe browser scans are not yet included.
- Docker runtime validation requires Docker Desktop or a Docker daemon to be running.
- The default local runner uses the Python core API instead of the Spring Boot service, so Maven and Docker are not required for normal development.

## Troubleshooting

- If Docker is not running, use the default `python start.py` path. Only `python start.py --docker` needs Docker.
- If ports `3000`, `8000`, `8002`, or `8080` are busy, stop the conflicting process or run `python start.py --restart`.
- If Flyway appears not to run in Docker mode on an existing Phase 1 database, restart with `python start.py --docker --restart`; avoid deleting volumes unless you intentionally want fresh demo data.
- If PWA assets appear stale, unregister the service worker in browser developer tools and reload.
- If realtime status shows reconnecting, check direct URLs `http://localhost:8080/api/core/incidents/events` and `ws://localhost:8002/api/simulation/ws/progress`.

## Reserved For Phase 3

Advanced machine learning, real sensor feeds, Kafka, Redis, OAuth, GraphQL, Kubernetes, cloud deployment, event sourcing, CQRS, data lakes, Spark/Flink, and multi-user collaboration remain out of scope.

## Phase 2 Checklist

- [x] Incident management API
- [x] Flyway migrations and demo incidents
- [x] Deterministic scenario simulation
- [x] Route and impact-area endpoints
- [x] Realtime SSE/WebSocket channels
- [x] Map-first dashboard
- [x] Scenario builder and result panel
- [x] PWA manifest/service worker/offline fallback
- [x] `start.py` launcher
- [x] Python and frontend validation
- [ ] Java tests require Maven or Docker runtime
- [ ] Full Docker runtime verification requires Docker daemon

## Phase 4 Foundation Checklist

- [x] Preserve no-Docker local startup
- [x] Production frontend build path
- [x] Gateway correlation IDs
- [x] Gateway rate limiting
- [x] Gateway request body limits
- [x] Gateway upstream timeouts
- [x] Gateway security headers
- [x] Gateway `/health`, `/health/services`, and `/metrics`
- [x] Frontend security headers
- [x] `start.py --mode`, `--profile`, `--health-report`, and `--test`
- [x] Phase 4 architecture, API, security, model-card, data dictionary, and contribution docs
- [x] SQLite-backed persistent local core API
- [x] Incident history
- [x] Emergency vehicles
- [x] Dispatch persistence
- [x] Synthetic environmental readings
- [x] Audit records
- [x] Event outbox records
- [x] `start.py --migrate`, `--seed`, and `--reset-db`
- [ ] PostgreSQL/PostGIS core API mode
- [ ] Authentication and role authorization
- [ ] Scenario versioning and comparison persistence
- [ ] Environmental data service
- [ ] ML service
- [ ] Event broker and transactional outbox
- [ ] Docker full profile
- [ ] Prometheus/Grafana stack
