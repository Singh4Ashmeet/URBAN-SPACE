# UrbanShield Baseline Report

Generated during Phase 0 against `UrbanShield_Execution_Plan.md` and `UrbanShield_Agent_Superprompt.md`.

## Current Architecture

Default local mode is a no-Docker stack:

- Next.js frontend on `3000`
- Local Python gateway on `8000`
- Python `core-api` on `8080`
- FastAPI `simulation-service` on `8002`
- SQLite data under `.data/urbanshield-core.sqlite3`

The optional Docker path keeps PostgreSQL/PostGIS, Kong, Spring Boot `core-service`, simulation service, and frontend.

## Current Routes By Service

Gateway:
- `GET /health`
- `GET /health/services`
- `GET /metrics`
- `/core/*` proxy to `core-api`
- `/simulation/*` proxy to `simulation-service`

Core API:
- `GET /api/core/health`
- `GET /api/core/incidents`
- `GET /api/core/incidents/summary`
- `GET /api/core/incidents/nearby`
- `GET /api/core/incidents/events`
- `GET/PUT/DELETE /api/core/incidents/{id}`
- `PATCH /api/core/incidents/{id}/status`
- `GET /api/core/incidents/{id}/history`
- `GET /api/core/incidents/{id}/events`
- `GET/POST /api/core/vehicles`
- `GET /api/core/vehicles/nearby`
- `GET/DELETE /api/core/vehicles/{id}`
- `PATCH /api/core/vehicles/{id}/status`
- `PATCH /api/core/vehicles/{id}/location`
- `POST /api/core/dispatch`
- `GET /api/core/dispatches`
- `GET /api/core/dispatches/{id}`
- `PATCH /api/core/dispatches/{id}/status`
- `GET /api/core/environment/current`
- `GET /api/core/environment/history`
- `POST /api/core/environment/refresh`
- `GET /api/core/environment/sources`
- `GET /api/core/audit`
- `GET /api/core/outbox`

Simulation service:
- `GET /api/simulation/health`
- `POST /api/simulation/run`
- `GET /api/simulation/scenarios`
- `GET /api/simulation/scenarios/{simulation_id}`
- `POST /api/simulation/route`
- `POST /api/simulation/impact-area`
- `WS /api/simulation/ws/progress`

## Data Storage

`core-api` uses direct `sqlite3` calls with `CREATE TABLE IF NOT EXISTS` in `core-api/app/main.py`. It stores incidents, incident history, emergency vehicles, dispatches, environmental readings, audit logs, and event outbox rows. It does not use SQLAlchemy or Alembic yet.

`simulation-service` stores scenarios in an in-memory `OrderedDict` capped at 50 items. Run history does not survive restart.

## Baseline Command Results

Working:
- `python start.py --status`: exited `0`; reported recorded services stopped.
- `python start.py --health-report`: exited `0`; reported all services down.
- `python start.py --migrate`: exited `0`.
- `python start.py --seed`: exited `0`.
- `npm run typecheck`: passed.
- `npm run lint`: passed.
- `npm run build`: passed.
- `python -m pytest` in `core-api`: 3 passed, 2 warnings.
- `python -m pytest` in `simulation-service`: 6 passed.
- `.venv` pytest in `core-api`: 3 passed, 2 warnings.
- `.venv` pytest in `simulation-service`: 6 passed.

Failing or blocked:
- `python start.py`: fails before launch with `PermissionError: [WinError 5] Access is denied: .urbanshield/pids.json`.
- `python start.py --stop`: same `pids.json` deletion failure.
- `python start.py --test`: fails at frontend tests after typecheck/lint.
- `npm test`: fails with Node test runner `spawn EPERM`.
- `npm ci`: fails with Windows `EPERM` while removing `frontend/node_modules/@deck.gl`.
- `python -m unittest discover -s tests/integration`: fails in `setUpClass` because `python start.py` exits `1`.
- `mvn test`: blocked because `mvn` is not installed on PATH.

## Test Counts

- Core API: 3 tests passing.
- Simulation service: 6 tests passing.
- Frontend test command: 1 file discovered, runner fails before assertions.
- Gateway integration: 0 tests executed due startup failure.
- Java service: not executed because Maven is unavailable.

## Hardcoded URLs And Ports

Current frontend and docs still reference internal ports:

- `frontend/lib/api.ts` defaults core to `http://127.0.0.1:8080`.
- `frontend/lib/api.ts` defaults simulation to `http://127.0.0.1:8002`.
- `frontend/hooks/useIncidentEvents.ts` uses direct core SSE URL.
- `frontend/hooks/useSimulationProgress.ts` uses direct simulation WebSocket URL.
- `frontend/next.config.mjs` allows direct `8080` and `8002` connections.
- `.env.example`, `frontend/.env.example`, `docker-compose.yml`, `README.md`, and `docs/API.md` document direct realtime URLs.

This conflicts with the target gateway-only networking phase.

## Compatibility Risks

- `start.py --health-report` prints "UrbanShield is running" even when all services are down.
- `.urbanshield/pids.json` can be a OneDrive reparse point and currently blocks startup and stop cleanup.
- The gateway is HTTP-only and does not proxy SSE or WebSocket routes yet.
- Canonical `/api/v1/*` routes are not implemented.
- Core API errors use mixed legacy shapes, not the target shared error envelope.
- Dispatch status transitions are not validated as a strict state machine.
- Authentication, roles, and local users are not implemented.
- AI service and AI runtime flags are not implemented.
- Simulation persistence, input hashing, version metadata, comparison, and export are not implemented.
- Documentation contains a mismatch: `docs/SECURITY.md` says audit logging is not implemented, while `core-api` currently writes audit rows.

## Exact Issues To Fix First

1. Make `start.py` stop/start resilient when `.urbanshield/pids.json` cannot be unlinked.
2. Make health reporting truthful when services are down.
3. Fix frontend test runner invocation so `npm test` executes assertions instead of failing with `spawn EPERM`.
4. Re-run `python start.py --test` and gateway integration tests after startup is repaired.
5. Only then proceed to API contracts, persistence, auth, gateway realtime, and AI phases.

## Phase 1 Validation Update

Completed fixes:
- `start.py` now clears `.urbanshield/pids.json` when Windows denies deletion.
- `start.py --status` and `--health-report` now inspect actual listener PIDs on managed ports.
- `start.py` now uses `npm run start` on Windows after a production frontend build, avoiding the blocked `next dev` spawn path.
- Frontend tests now run through `frontend/tests/run-tests.cjs` instead of `tsx --test`.
- Git now ignores generated `.next-*` build/probe folders; ESLint ignores `.next-validation-*` validation folders.
- Windows validation builds now try a temporary frontend source copy and support `URBANSHIELD_VALIDATION_TEMP` for an explicit writable scratch directory.
- Core, simulation, fallback, and gateway CORS defaults now allow both `localhost:3000` and `127.0.0.1:3000`.
- Simulation service local `.env` now matches the `127.0.0.1` frontend URL used by `start.py`.
- Core API now uses persistent SQLite journaling and memory temp storage to reduce OneDrive journal-file failures.

Current passing checks:
- `python start.py` starts the local no-Docker stack.
- `python start.py --health-report` reports core API, simulation service, frontend, gateway, and gateway service health as UP when running.
- `cd frontend; npm run typecheck` passed.
- `cd frontend; npm run lint` passed.
- `cd frontend; npm test` passed with 2 tests.
- `cd core-api; python -m pytest` passed with 3 tests and 2 FastAPI deprecation warnings.
- `cd simulation-service; python -m pytest` passed with 6 tests.
- `python -m unittest discover -s tests/integration` passed with 4 tests.
- Browser smoke checks opened `http://127.0.0.1:3000` and verified the UrbanShield dashboard without console errors.
- Browser verification after fixes confirmed content, no error overlay, no console errors, incidents loaded, events connected, allocation ready, services `2/2`, and successful simulation result metrics.
- Browser dispatch verification confirmed the allocation workflow handles the no-available-vehicles case and renders dispatch history without console errors.
- Gateway CORS preflight for `http://127.0.0.1:3000` now succeeds.

Current blockers:
- `python start.py --test` still fails at the frontend production build step in this managed session because the default Windows temp folder denies child directory creation for the temporary validation copy.
- Direct in-place Next builds remain blocked by the OneDrive workspace ACL; generated folders inherit `Everyone:(DENY)(DC)`, and Next/Turbopack needs rename/delete access.
- `next build --webpack` also fails with `spawn EPERM`.
- Windows denies attempts to remove the inherited deny ACL from generated build directories.
- `npm ci` remains blocked by `EPERM` while replacing existing `node_modules`.
- `mvn test` remains blocked because Maven is not installed.
- Vercel `agent-browser` is not installed on PATH, so the Vercel verification checklist was executed through the available in-app browser automation surface.
- Computer Use remains blocked by a bundled Windows client export error.

Recommended next environment action:
- Move the repository to a normal development folder outside OneDrive-controlled permissions, adjust the folder ACLs in Windows Explorer/PowerShell with elevated permissions, or set `URBANSHIELD_VALIDATION_TEMP` to a writable scratch folder. Then rerun `python start.py --test`.
