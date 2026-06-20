# UrbanShield Agent Superprompt

You are the lead software engineer responsible for upgrading the existing UrbanShield repository into a reliable, free, local-first, fully demonstrable prototype.

You must inspect and modify the actual repository. Do not stop after producing another plan. Implement, test, repair, document, and report the working result.

Read these repository files before changing code:

```text
AGENTS.md
plan.md
README.md
start.py
docker-compose.yml
all .env.example files
all package manifests and requirements files
all existing tests
```

Also read:

```text
UrbanShield_Execution_Plan.md
```

The execution plan is the target specification. Existing working behavior must be preserved unless it conflicts with an explicit requirement below.

---

# 1. Primary Outcome

Deliver a polished UrbanShield prototype that:

1. starts through `python start.py` on Windows;
2. does not require Docker;
3. does not require a paid API, cloud account, or API key;
4. uses the Python `core-api` as the authoritative backend;
5. supports incident, vehicle, dispatch, environment, audit, and deterministic simulation workflows;
6. persists simulation scenarios and runs;
7. supports local authentication and role-based authorization;
8. routes HTTP, SSE, and WebSocket traffic through the local gateway;
9. optionally uses local open-weight language models through Ollama or another OpenAI-compatible local server;
10. remains fully usable when the AI runtime is absent;
11. has tests, documentation, seed data, and a repeatable demonstration path.

Do not claim production readiness. Build a strong prototype with production-aware boundaries.

---

# 2. Non-Negotiable Rules

## 2.1 Preserve current functionality

- Make minimal, targeted changes.
- Do not rewrite working modules without need.
- Do not change frameworks merely for preference.
- Do not remove the no-Docker path.
- Do not make Docker mandatory.
- Do not break existing routes, response fields, startup flags, tests, or frontend flows.
- Add compatibility aliases before deprecating routes.
- Do not delete the optional Spring Boot/PostGIS code.

## 2.2 Backend ownership

Use `core-api/` for all default backend features.

Do not duplicate work into `core-service/` unless the task explicitly requires the Java service.

Add a clear note to architecture documentation that `core-service/` is optional.

## 2.3 Free by default

Do not introduce a mandatory dependency on:

- OpenAI, Anthropic, Google, Azure, AWS, or another paid model API;
- hosted auth;
- hosted database;
- paid map tiles;
- paid geocoding;
- Redis;
- Kafka;
- Kubernetes;
- proprietary monitoring;
- a GPU.

Optional adapters are allowed only when disabled by default.

## 2.4 No fake completion

Do not:

- add placeholder handlers;
- return hardcoded success objects for unfinished features;
- skip tests and claim they passed;
- hide exceptions to force a green status;
- fake metrics;
- label deterministic templates as AI;
- leave critical TODOs in delivered flows;
- seed real personal or emergency data.

## 2.5 No uncontrolled AI writes

The AI layer is advisory.

It must not directly create, update, delete, dispatch, resolve, or close anything. It may create a preview. A human must confirm the preview, after which the normal validated API performs the write with normal role checks and audit logging.

## 2.6 Security

- Never commit secrets.
- Never log passwords, tokens, cookies, or API keys.
- Never store plain-text passwords.
- Validate all user and model input.
- Enforce authorization on the backend.
- Block remote AI endpoints unless explicitly enabled.
- Treat imported and incident text as untrusted model context.
- Do not expose hidden model reasoning.

---

# 3. Working Method

Proceed without asking the user to choose routine implementation details.

Use this sequence:

1. audit;
2. baseline;
3. implement one phase;
4. run focused tests;
5. repair failures;
6. run broader validation;
7. update documentation and implementation status;
8. continue to the next phase.

When the repository differs from this prompt:

- prefer preserving working behavior;
- document the discrepancy;
- choose the smallest compatible implementation;
- do not silently change scope.

Create `docs/implementation-status.md` immediately and update it after every phase.

For each phase record:

```text
Status
Files changed
Behavior implemented
Commands run
Tests passed
Tests failed
Known limitations
Deferred items
```

---

# 4. Phase 0 — Audit and Baseline

Before editing features:

## 4.1 Inspect

Inspect:

- complete repository tree;
- Python entry points;
- Next.js routes and components;
- gateway routing;
- database initialization;
- SQLite models and queries;
- simulation schemas and formulas;
- SSE and WebSocket code;
- `start.py` process management;
- health endpoints;
- all tests;
- all hardcoded URLs and ports;
- existing security headers and CORS;
- offline/PWA behavior;
- existing documentation.

## 4.2 Run baseline commands

Run every command that exists and is safe:

```powershell
python start.py --status
python start.py --health-report
python start.py --test
```

In the frontend:

```powershell
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

Run Python tests directly where useful.

Do not treat pre-existing failure as a reason to stop. Record it, then fix it if it blocks the target prototype.

## 4.3 Produce baseline report

Create:

```text
docs/baseline-report.md
```

Include:

- current architecture;
- current working commands;
- current failing commands;
- routes by service;
- data storage;
- test counts;
- known hardcoded dependencies;
- compatibility risks;
- exact issues to fix.

Do not implement architecture changes before this report exists.

---

# 5. Phase 1 — Stabilize the Local Runtime

Make `start.py` the dependable root command.

## 5.1 Preserve and support

Preserve existing flags and add missing behavior for:

```powershell
python start.py
python start.py --build
python start.py --test
python start.py --health-report
python start.py --status
python start.py --restart
python start.py --stop
python start.py --migrate
python start.py --seed
python start.py --reset-db
```

Later add:

```powershell
python start.py --with-ai
python start.py --without-ai
python start.py --ai-check
python start.py --setup-ai --model qwen3:4b
python start.py --e2e
```

## 5.2 Runtime behavior

Implement:

- root-relative path handling;
- Windows-safe subprocess creation;
- PID tracking;
- port-conflict detection;
- actionable missing-dependency messages;
- clean shutdown;
- no orphan processes;
- per-service log prefixes;
- startup health polling;
- startup timeout with diagnostics;
- graceful AI degradation;
- no global software installation during normal startup.

Do not silently run `npm install -g`, install Ollama, or download models during `python start.py`.

## 5.3 Setup

If dependencies are missing, print exact commands.

An explicit setup flag may install project-local Python and Node dependencies, but must not install global desktop applications.

## 5.4 Acceptance

From the repository root:

```powershell
python start.py
python start.py --health-report
python start.py --test
python start.py --stop
```

must behave predictably and exit with truthful status codes.

---

# 6. Phase 2 — Formal Contracts and SQLite Persistence

## 6.1 Core structure

Refactor only as needed into clear layers:

```text
core-api/app/
  api/
  models/
  schemas/
  repositories/
  services/
  security/
  db/
  events/
```

Reuse existing patterns where already present.

## 6.2 SQLAlchemy and migrations

Use SQLAlchemy 2-style models and Alembic.

Create versioned migrations for:

- users;
- incidents;
- incident_history;
- vehicles;
- dispatches;
- environment_readings;
- audit_logs;
- outbox_events;
- simulation scenario references if owned by core;
- AI run metadata if owned by core.

Never mutate an applied migration.

Implement:

```powershell
python start.py --migrate
python start.py --seed
python start.py --reset-db
```

Back up the SQLite database before reset.

## 6.3 Canonical errors

Add one shared error model:

```json
{
  "error": {
    "code": "CODE",
    "message": "Human-readable message",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

Map validation, not-found, conflict, authorization, rate-limit, timeout, and upstream errors consistently.

## 6.4 Pagination and filtering

Add consistent pagination and filter contracts to list endpoints without breaking legacy callers.

## 6.5 Optimistic concurrency

Add `version` fields to mutable entities.

Reject stale updates using `409 Conflict`.

## 6.6 API contracts

Use Pydantic request and response models for all public endpoints.

Do not return ORM objects directly.

Keep OpenAPI schemas accurate.

Create or update frontend TypeScript types from these contracts.

## 6.7 Acceptance

- migrations apply to an empty database;
- seed is repeatable;
- reset is safe and explicit;
- CRUD tests pass;
- legacy route tests pass;
- frontend typecheck passes.

---

# 7. Phase 3 — Incident, Vehicle, and Dispatch Workflows

## 7.1 Incidents

Complete:

- create;
- read;
- update;
- status transition;
- severity change;
- soft or authorized hard delete according to current design;
- filters;
- pagination;
- nearby lookup;
- summary;
- history;
- realtime events.

Every write creates:

- incident history;
- audit log;
- outbox event;
- correlation ID.

## 7.2 Vehicles

Complete:

- create and edit;
- list and filter;
- availability state;
- location;
- capacity;
- assignment;
- release;
- version conflict handling.

## 7.3 Dispatches

Implement a validated state machine. Use existing states if present; otherwise use:

```text
created
acknowledged
en_route
arrived
completed
cancelled
```

Reject invalid transitions.

Creating a dispatch must atomically:

- validate incident;
- validate vehicle;
- validate vehicle eligibility;
- create dispatch;
- mark vehicle assigned;
- create audit and outbox records.

Completing or cancelling must release the vehicle when appropriate.

## 7.4 Deterministic ranking

Add a transparent deterministic vehicle ranking using:

- vehicle status;
- vehicle type eligibility;
- approximate geographic distance;
- capacity;
- existing assignment;
- scenario constraints.

Return reasons for every score.

Do not call this machine learning.

## 7.5 Frontend

Add or complete:

```text
/incidents
/incidents/[id]
/vehicles
/dispatches
/operations
```

Handle loading, empty, error, conflict, offline, unauthorized, and success states.

## 7.6 Acceptance scenario

Through the UI:

1. create an incident;
2. view it on the map;
3. assign a vehicle;
4. progress dispatch state;
5. resolve the incident;
6. inspect history and audit entries.

Add integration and frontend tests for this exact path.

---

# 8. Phase 4 — Deterministic Simulation Persistence

## 8.1 Keep calculations deterministic

Do not move simulation calculations into the LLM.

Normalize inputs and version formulas.

## 8.2 Persist

Add:

```text
simulation_scenarios
simulation_runs
```

Each run stores:

- normalized input;
- input hash;
- simulation version;
- deterministic seed;
- output;
- warnings;
- status;
- start/end;
- duration.

## 8.3 Reproducibility tests

Assert that identical:

```text
normalized input + seed + simulation version
```

produces identical output.

## 8.4 Progress

Preserve or improve WebSocket progress.

Every progress message should include:

```json
{
  "run_id": "uuid",
  "stage": "routing",
  "progress": 50,
  "message": "Estimating response delay",
  "correlation_id": "uuid"
}
```

## 8.5 UI

Complete:

```text
/simulations
/simulations/[id]
```

Support:

- create;
- run;
- progress;
- history;
- comparison;
- JSON export;
- CSV export;
- print-friendly report;
- create-incident preview from result.

## 8.6 Acceptance

- run history survives restart;
- identical runs reproduce;
- two runs compare correctly;
- WebSocket progress works;
- incident creation from simulation requires confirmation.

---

# 9. Phase 5 — Local Authentication and Roles

## 9.1 Users

Store local users in SQLite.

Use Argon2 password hashing.

Do not commit passwords.

Create seed/setup logic for viewer, operator, dispatcher, and admin users.

## 9.2 Sessions or tokens

Use a secure, simple local strategy compatible with the current gateway and frontend.

Requirements:

- short expiry;
- signature validation;
- logout/revocation strategy;
- no token logging;
- backend role enforcement;
- unauthorized responses use the shared error envelope.

Prefer secure HTTP-only cookies when compatible. If bearer tokens are used, do not persist long-lived tokens in localStorage.

## 9.3 Permissions

Implement the permission matrix in `UrbanShield_Execution_Plan.md`.

Never rely only on hiding UI elements.

## 9.4 Frontend

Add:

```text
/login
/settings
```

Protect routes.

Show current role and user.

## 9.5 Acceptance

Direct API tests must prove that viewer/operator/dispatcher roles cannot perform forbidden admin operations.

---

# 10. Phase 6 — Gateway-Only Networking

## 10.1 Canonical routes

Add:

```text
/api/v1/auth/*
/api/v1/incidents/*
/api/v1/vehicles/*
/api/v1/dispatches/*
/api/v1/environment/*
/api/v1/audit/*
/api/v1/simulations/*
/api/v1/ai/*
/api/v1/system/*
```

Keep legacy aliases.

## 10.2 SSE

Proxy incident SSE through:

```text
GET /api/v1/events/incidents
```

Support:

- authentication;
- heartbeat;
- event IDs;
- reconnection;
- disconnect cleanup;
- correlation IDs.

## 10.3 WebSocket

Proxy simulation progress through:

```text
WS /api/v1/ws/simulations
```

Support:

- token validation;
- close code forwarding;
- correlation IDs;
- message-size limits;
- disconnect cleanup.

## 10.4 Frontend configuration

Use one public base URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Remove direct frontend dependencies on `8080`, `8002`, or `8003`.

## 10.5 Acceptance

Browser network inspection for application traffic should show gateway port `8000`, apart from frontend assets and permitted map tiles.

---

# 11. Phase 7 — Optional Local AI Service

Create a new optional FastAPI service:

```text
ai-service/
```

Use port `8003`.

The service must start even when no model runtime is available and report a degraded provider state.

## 11.1 Dependencies

Prefer small, maintained, free dependencies:

```text
fastapi
uvicorn
pydantic
httpx
```

Do not add a heavy agent framework unless existing code already requires it.

## 11.2 Provider abstraction

Implement:

```text
AIProvider
OllamaProvider
OpenAICompatibleProvider
DisabledProvider
```

The generic provider should support local OpenAI-compatible servers.

Ollama should be the default.

## 11.3 Configuration

Add:

```env
AI_ENABLED=auto
AI_PROVIDER=ollama
AI_BASE_URL=http://localhost:11434
AI_OPENAI_BASE_URL=http://localhost:11434/v1
AI_MODEL=qwen3:4b
AI_API_KEY=
AI_ALLOW_REMOTE=false
AI_TIMEOUT_SECONDS=120
AI_MAX_INPUT_CHARS=24000
AI_MAX_CONCURRENT_REQUESTS=2
AI_STORE_RUN_METADATA=true
AI_STORE_RAW_INPUT=false
AI_ALLOW_WRITE_ACTIONS=false
```

Default behavior:

- localhost endpoint allowed;
- remote endpoint blocked;
- missing Ollama does not break platform startup;
- missing model returns actionable status;
- no model download during normal start.

## 11.4 Model discovery

For Ollama, list installed models dynamically.

Expose:

```text
GET /api/v1/ai/models
```

The frontend selector must display only discovered models plus disabled state.

Recommended labels:

```text
Light: qwen3:1.7b
Balanced: qwen3:4b
Quality: qwen3:8b
```

Do not assume any is installed.

## 11.5 Setup command

Implement:

```powershell
python start.py --ai-check
python start.py --setup-ai --model qwen3:4b
```

`--ai-check` should:

- detect Ollama;
- query its health/version;
- list models;
- test configured model;
- report memory-independent setup guidance;
- never fail the non-AI platform.

`--setup-ai` may run `ollama pull` only because the user explicitly requested it.

If Ollama executable is absent, print official installation guidance and exit truthfully. Do not silently download or install an executable.

## 11.6 Endpoints

Implement:

```text
GET  /api/v1/ai/health
GET  /api/v1/ai/models
POST /api/v1/ai/incidents/draft
POST /api/v1/ai/incidents/summarize
POST /api/v1/ai/simulations/explain
POST /api/v1/ai/dispatch/recommend
POST /api/v1/ai/chat
GET  /api/v1/ai/chat/stream
```

## 11.7 Structured models

Define Pydantic output schemas for every task.

Use schema-constrained output and temperature `0`.

Validate model output.

On invalid output:

1. retry once with a repair request;
2. validate again;
3. return deterministic fallback or a clear error.

Never pass invalid model JSON to the frontend.

## 11.8 Grounded tools

The assistant may call read-only application tools:

```text
get_incident
list_incidents
get_vehicle
list_available_vehicles
get_dispatch
get_simulation_run
get_service_health
get_summary_metrics
```

Implement tools as trusted server functions.

Do not let the model invent function names or arbitrary URLs.

Any proposed mutation must return a preview structure.

## 11.9 Guardrails

Implement:

- role-specific system prompts;
- untrusted-data delimiters;
- tool allow-list;
- schema validation;
- input length limits;
- timeout;
- concurrency limit;
- local-host enforcement;
- secret redaction;
- safe logging;
- no hidden reasoning storage;
- advisory warning;
- evidence IDs;
- model/provider metadata;
- prompt-template version.

## 11.10 AI run metadata

Persist safe metadata:

```text
operation
provider
model
template version
input hash
result
warnings
latency
status
fallback flag
actor
timestamp
```

Do not store raw input by default.

## 11.11 Fallbacks

When AI is unavailable:

- incident summary uses counts and deterministic templates;
- simulation explanation uses calculated fields and warnings;
- dispatch recommendation uses deterministic ranking;
- assistant page shows setup guidance;
- no core workflow fails.

Clearly label fallback output as deterministic.

## 11.12 Acceptance

Run all tests with Ollama stopped.

Then, when a local Ollama instance is available, verify:

```text
health
model listing
structured incident draft
incident summary
simulation explanation
dispatch advisory
streaming chat
```

The code must not require changes when switching between supported local models.

---

# 12. Phase 8 — Map, Offline, and PWA

## 12.1 Map

Keep MapLibre.

Use configurable style/tile URLs.

Preserve required attribution.

Do not add tile scraping, city prefetch, or offline download from public OpenStreetMap tile servers.

Add a local offline fallback:

- neutral grid;
- locally stored GeoJSON boundaries if already licensed and available;
- incident and vehicle points;
- clear “base map unavailable” state.

## 12.2 PWA

Use Next.js App Router PWA conventions.

Cache:

- app shell;
- icons;
- static assets;
- bounded safe GET responses;
- local drafts.

Do not cache:

- tokens;
- passwords;
- destructive responses;
- unrestricted audit data.

## 12.3 Offline writes

Use:

- client-generated idempotency keys;
- visible queued state;
- retry after reconnection;
- conflict handling;
- no silent overwrite.

## 12.4 Accessibility

Audit:

- keyboard navigation;
- focus;
- labels;
- contrast;
- map alternatives;
- error announcements;
- reduced motion;
- mobile layout.

---

# 13. Phase 9 — Observability and E2E

## 13.1 Logs

Use structured JSON logs.

Include correlation IDs.

Redact secrets.

## 13.2 Metrics

Expose local Prometheus-style metrics without requiring a monitoring server.

Include:

- request totals;
- latency;
- errors;
- rate limits;
- SSE connections;
- WebSocket connections;
- simulation duration;
- AI health, status, and latency.

## 13.3 E2E

Add a minimal Playwright suite.

It must not require a real model.

Test:

1. login;
2. create incident;
3. edit incident;
4. dispatch vehicle;
5. run simulation;
6. inspect persisted result;
7. verify realtime update;
8. use deterministic AI fallback;
9. logout.

Add an optional test marker for real Ollama integration.

---

# 14. UI Requirements

Preserve existing visual identity where it works. Improve consistency rather than replacing the whole frontend.

Required routes:

```text
/login
/dashboard
/incidents
/incidents/[id]
/operations
/vehicles
/dispatches
/simulations
/simulations/[id]
/assistant
/audit
/system
/settings
```

Every page must handle:

```text
loading
empty
error
offline
unauthorized
success
```

Use existing component patterns.

Do not add a second large UI framework without need.

Required product details:

- map-first dashboard;
- responsive sidebar/navigation;
- role-aware actions;
- service-health indicator;
- model/provider status;
- visible AI advisory labels;
- explicit confirmation modals;
- simulation comparison;
- audit timeline;
- realistic synthetic seed data;
- no lorem ipsum in final demo.

---

# 15. Test Commands

After focused tests, run the broad validation available in the repository.

At minimum:

```powershell
python start.py --test
python start.py --health-report
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

Python:

```powershell
cd core-api
python -m pytest
```

```powershell
cd simulation-service
python -m pytest
```

```powershell
cd ai-service
python -m pytest
```

Run gateway and integration tests.

Run E2E when implemented.

If a command fails:

- inspect the real cause;
- fix it;
- rerun it;
- do not simply remove the test or suppress the error.

---

# 16. Required Documentation

Update or create:

```text
README.md
AGENTS.md
.env.example
docs/baseline-report.md
docs/implementation-status.md
docs/architecture.md
docs/api.md
docs/data-model.md
docs/simulation.md
docs/ai-local-models.md
docs/security.md
docs/testing.md
docs/demo-script.md
docs/troubleshooting-windows.md
```

README must contain a first-run path that does not require Docker.

`docs/ai-local-models.md` must explain:

- AI is optional;
- Ollama setup;
- model discovery;
- light/balanced/quality presets;
- `--ai-check`;
- `--setup-ai`;
- generic OpenAI-compatible local endpoint;
- remote endpoint opt-in;
- data handling;
- troubleshooting;
- how deterministic fallback works.

---

# 17. Demo Data

Use fictional Delhi-region-style data but do not use real emergency incidents or private information.

Seed:

- multiple incident types and severities;
- active, resolved, and closed incidents;
- ambulances, fire vehicles, patrol vehicles, and utility vehicles;
- available, assigned, maintenance, and offline statuses;
- environmental readings;
- simulation scenarios;
- a complete dispatch history;
- audit records.

Make relationships internally consistent.

---

# 18. Performance and Reliability Targets

Use practical prototype targets and measure where possible:

- health response should be fast and bounded;
- common local CRUD should feel immediate;
- standard deterministic simulation should complete quickly;
- AI requests must have a timeout and cancellation path;
- no unbounded in-memory event list;
- no unbounded frontend polling;
- no repeated model pull;
- no startup deadlock;
- no orphan processes after stop;
- SQLite writes should use transactions;
- dispatch assignment must be atomic.

Do not fake benchmark numbers. Record measured values only.

---

# 19. Final Verification Checklist

Before declaring completion, verify:

## Runtime

- [ ] one-command no-Docker startup;
- [ ] clean stop;
- [ ] restart;
- [ ] status;
- [ ] health report;
- [ ] migration;
- [ ] seed;
- [ ] reset;
- [ ] production frontend build.

## Core

- [ ] incident CRUD;
- [ ] history;
- [ ] vehicle CRUD;
- [ ] dispatch state machine;
- [ ] atomic assignment and release;
- [ ] environment readings;
- [ ] audit;
- [ ] outbox;
- [ ] pagination;
- [ ] conflicts;
- [ ] role authorization.

## Simulation

- [ ] deterministic result;
- [ ] version;
- [ ] seed;
- [ ] input hash;
- [ ] persisted run;
- [ ] progress;
- [ ] comparison;
- [ ] export.

## Gateway

- [ ] canonical routes;
- [ ] legacy aliases;
- [ ] correlation IDs;
- [ ] limits;
- [ ] SSE proxy;
- [ ] WebSocket proxy;
- [ ] auth forwarding;
- [ ] metrics.

## AI

- [ ] starts without Ollama;
- [ ] reports degraded status;
- [ ] core stays usable;
- [ ] model discovery;
- [ ] provider abstraction;
- [ ] structured validation;
- [ ] fallback;
- [ ] no direct writes;
- [ ] evidence IDs;
- [ ] remote host blocked by default;
- [ ] optional real local-model test.

## Frontend

- [ ] login and roles;
- [ ] dashboard;
- [ ] map;
- [ ] incidents;
- [ ] operations;
- [ ] simulations;
- [ ] assistant;
- [ ] audit;
- [ ] system page;
- [ ] loading/empty/error/offline states;
- [ ] responsive and keyboard usable.

## Quality

- [ ] Python tests pass;
- [ ] integration tests pass;
- [ ] typecheck passes;
- [ ] lint passes;
- [ ] frontend tests pass;
- [ ] build passes;
- [ ] E2E smoke passes or exact blocker documented;
- [ ] no real secrets;
- [ ] no critical placeholders;
- [ ] docs match implementation.

---

# 20. Completion Report Format

When the implementation is complete, respond with:

## Implemented

A concise summary of working product capabilities.

## Architecture

Services, ports, database, gateway routes, and AI provider behavior.

## Files changed

Group by service.

## Commands run

List exact commands.

## Validation results

Give exact pass/fail counts when available.

## How to run

Provide the shortest Windows-first setup and startup path.

## Demo credentials

Explain how to obtain seeded credentials without exposing committed passwords.

## Local AI setup

Show the optional commands for model detection and explicit model pull.

## Known limitations

Be honest and specific.

## Deferred production work

List only genuinely deferred infrastructure.

Do not say “everything works” unless every required validation has actually passed.

---

# 21. Final Engineering Principle

Prefer a smaller system that is fully integrated, tested, understandable, and free to run over a large collection of half-connected “enterprise” technologies.

UrbanShield must work as a complete local prototype before any optional production-scale infrastructure is added.
