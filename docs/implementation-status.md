# UrbanShield Implementation Status

This file tracks progress against `UrbanShield_Execution_Plan.md` and `UrbanShield_Agent_Superprompt.md`. UrbanShield remains a local-first prototype; production infrastructure is deferred unless explicitly requested.

## Current Checkpoint

Status: Phase 0 complete; Phase 1 partially complete.

Latest focus:
- Stabilized Windows local startup and status reporting.
- Repaired frontend test execution in environments where `tsx --test` cannot spawn.
- Verified the running app through local browser tooling.
- Identified a Windows/OneDrive ACL blocker for Next production builds during `python start.py --test`.

## Phase 0 - Repository Audit and Baseline

Status: Completed

Files changed:
- `docs/implementation-status.md`
- `docs/baseline-report.md`

Behavior implemented:
- Created implementation status tracking before feature work.
- Recorded current architecture, service ports, routes, storage model, baseline commands, test counts, hardcoded URLs, and compatibility risks.

Commands run:
- Required project file discovery and reads
- `python start.py --status`
- `python start.py --health-report`
- Frontend typecheck, lint, tests, and build
- Core API and simulation service pytest suites
- Gateway integration test discovery

Tests passed:
- Core API: 3 passed
- Simulation service: 6 passed
- Frontend typecheck: passed
- Frontend lint: passed after generated build folders were ignored
- Frontend unit tests: 2 passed after test runner repair
- Gateway integration: 4 passed after startup repairs

Tests failed or blocked:
- Initial `python start.py`, `--stop`, and integration tests failed because `.urbanshield/pids.json` could not be removed.
- Initial frontend tests failed with `spawn EPERM`.
- `npm ci` remains blocked by Windows `EPERM` while replacing `node_modules/@deck.gl`.
- `mvn test` remains blocked because Maven is not installed.

Known limitations:
- Canonical `/api/v1/*` routes, auth, role enforcement, AI service, and simulation persistence remain future phases.

Deferred items:
- Phase 2+ architecture and feature work.

## Phase 1 - Stabilize Local Runtime

Status: In progress

Files changed:
- `start.py`
- `frontend/package.json`
- `frontend/tests/run-tests.cjs`
- `frontend/eslint.config.mjs`
- `frontend/next.config.mjs`
- `.gitignore`
- `docs/implementation-status.md`
- `docs/baseline-report.md`

Behavior implemented:
- `python start.py` now uses the production frontend server on Windows to avoid `next dev` spawn failures.
- PID cleanup now tolerates `.urbanshield/pids.json` deletion denial by clearing the file contents.
- Stop/status/health logic detects all listener PIDs on managed ports instead of only recorded PIDs.
- Process shutdown now falls back from `taskkill` to PowerShell `Stop-Process`.
- Health reporting now reflects actual service state before printing the summary.
- Frontend tests now run through `tests/run-tests.cjs`, avoiding the blocked `tsx --test` spawn path.
- Generated `.next-*` build/probe folders are ignored by git; validation folders are ignored by ESLint.
- `NEXT_DIST_DIR` can redirect Next build output for validation attempts.
- Windows validation builds now try to copy the frontend to a temporary directory and link existing `node_modules`, so Next can build outside OneDrive-protected generated folders when a writable temp path exists.
- `URBANSHIELD_VALIDATION_TEMP` can point validation builds at an explicit writable scratch directory outside OneDrive.
- Core API, simulation service, fallback core, and gateway CORS defaults now allow both `localhost:3000` and `127.0.0.1:3000`.
- Simulation service `.env` and `.env.example` now include `127.0.0.1` origins, matching the default URL printed by `start.py`.
- Core API SQLite connections use persistent journaling and memory temp storage to avoid deleting journal files in OneDrive-protected folders.

Commands run:
- `python start.py --status`
- `python start.py --health-report`
- `python start.py`
- `python start.py --test`
- `cd frontend; npm run typecheck`
- `cd frontend; npm run lint`
- `cd frontend; npm test`
- `cd frontend; npm run build`
- `cd core-api; python -m pytest`
- `cd simulation-service; python -m pytest`
- `python -m unittest discover -s tests/integration`

Tests passed:
- `python start.py` starts core API, simulation service, gateway, and frontend.
- `python start.py --health-report` reports all services UP when the stack is running.
- `frontend`: typecheck passed, lint passed, 2 tests passed.
- `core-api`: 3 passed, 2 FastAPI deprecation warnings.
- `simulation-service`: 6 passed.
- `tests/integration`: 4 passed.
- Browser smoke checks loaded `http://127.0.0.1:3000` and found the UrbanShield dashboard without console errors.
- Browser verification after CORS fixes passed: page content loaded, no framework overlay, no console errors, incidents loaded, events connected, allocation ready, services showed `2/2`, and simulation completed with result metrics.
- Browser dispatch verification passed: after a simulation, `Dispatch Recommended Vehicles` handled the no-available-vehicles case and displayed dispatch history without console errors.
- Gateway preflight from `http://127.0.0.1:3000` now returns `Access-Control-Allow-Origin: http://127.0.0.1:3000`.

Tests failed or blocked:
- `python start.py --test` reaches the frontend production build step, then fails because the default Windows temp directory in this session also denies child directory creation: `[WinError 5] Access is denied: ... AppData\\Local\\Temp\\urbanshield-frontend-build-*\\frontend`.
- Direct in-place `next build` attempts in the OneDrive workspace fail because Next/Turbopack cannot rename generated files under inherited `Everyone:(DENY)(DC)` folders.
- `next build --webpack` also fails with `spawn EPERM`.
- Attempts to remove the inherited deny ACL from generated frontend build folders are denied by Windows.
- Computer Use plugin bootstrap failed because the bundled package does not export the requested Windows internal client subpath.
- Vercel `agent-browser` CLI is not installed on PATH in this session; equivalent browser verification was run through the available in-app browser client.
- Browser plugin cache is missing `browser/scripts/browser-client.mjs`; browser automation was reached through the available bundled browser client exposing the in-app browser.
- The `Create incident from result` browser interaction remained inconclusive through automation. The UI rendered the control and core API accepted CORS preflight, but the automated click did not produce a confirmed UI-created incident during the final pass.

Known limitations:
- The local stack can still leave stale listener processes if Windows denies `taskkill`; direct `Stop-Process` fallback usually clears them, but the final process state should be checked after interrupted validation runs.
- Production build validation is blocked by local filesystem policy, not by TypeScript, lint, or unit-test failures.
- AI, auth, canonical gateway routes, SSE/WebSocket gateway proxying, and persisted simulation runs are not implemented yet.

Deferred items:
- Resolve the OneDrive/temp ACL issue by moving the repo to a normal writable development directory, changing folder permissions outside the app, or setting `URBANSHIELD_VALIDATION_TEMP` to a writable scratch folder.
- Continue Phase 1 until `python start.py --test` can complete in an environment that allows Next build file renames.

## Phase 2 - Contracts and Persistence

Status: Completed

Behavior implemented:
- Refactored core API to use SQLAlchemy 2.x ORM models and Alembic migrations.
- Extracted code into app/db, app/models, app/schemas, and app/repositories.
- Implemented shared error envelope and standardized pagination.
- Added version fields on mutable entities (incidents, vehicles, dispatches) for optimistic concurrency.
- Created programmatically executable Alembic migrations in app/cli.py and uvicorn startup.
- Tested and verified CLI command database migration, seeding, and resets.

## Phase 3 - Operational Workflows

Status: Pending

Known limitations:
- Incident, vehicle, dispatch, audit, and outbox workflows exist in the current prototype but still need formal state-machine, authorization, and UI acceptance coverage.

## Phase 4 - Simulation Persistence and Comparison

Status: Pending

Known limitations:
- Simulation scenario history is still in-memory and capped; persisted runs, input hashes, seeds, comparison, and export are pending.

## Phase 5 - Authentication and Roles

Status: Pending

Known limitations:
- Local users, Argon2 password hashes, sessions/tokens, and backend role enforcement are not implemented.

## Phase 6 - Gateway and Realtime

Status: Pending

Known limitations:
- Frontend and docs still include direct service port references for some realtime paths.
- Canonical `/api/v1` routes, gateway SSE proxying, and gateway WebSocket proxying are pending.

## Phase 7 - Optional Local AI Service

Status: Pending

Known limitations:
- `ai-service/`, local model discovery, AI flags, guardrails, and deterministic AI fallbacks are not implemented.

## Phase 8 - Offline, PWA, and UX Polish

Status: Pending

Known limitations:
- Offline writes, conflict handling, accessibility pass, and print/export polish remain future work.

## Phase 9 - Observability, E2E, and Documentation

Status: Pending

Known limitations:
- Playwright E2E, expanded architecture/API/security/testing docs, and final demo script are pending.
