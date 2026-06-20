# UrbanShield — Free, Local-First Prototype Execution Plan

## 0. Purpose

This plan converts the current UrbanShield prototype into a reliable, demonstrable, local-first smart-city operations platform that:

- starts on Windows with one command;
- works without Docker, cloud accounts, paid APIs, or API keys;
- keeps the current Python core API as the authoritative backend;
- supports incident, vehicle, dispatch, environment, audit, and simulation workflows;
- routes normal, SSE, and WebSocket traffic through one gateway;
- persists simulation runs and operational history;
- includes local authentication and role-based access;
- optionally uses locally hosted open-weight language models;
- remains fully usable when no AI runtime or model is installed;
- preserves the optional Spring Boot/PostGIS/Docker path without making it a requirement.

The target is a polished prototype, not a claim of production readiness or a full city-scale digital twin.

---

# 1. Non-Negotiable Architecture Decisions

## 1.1 Authoritative backend

`core-api/` is the authoritative backend for the default local workflow.

Do not duplicate new features in `core-service/`. Treat `core-service/` as an optional, frozen expansion path unless a task explicitly asks for Java, Spring Boot, or PostGIS work.

## 1.2 Default runtime

The supported default is:

```text
Browser / Next.js frontend :3000
              |
              v
Local Python gateway :8000
      |              |              |
      v              v              v
Core API :8080  Simulation :8002  AI service :8003
      |
      v
SQLite + versioned migrations
```

The AI service is optional at the capability level. It may start in a healthy-but-degraded state when no local model runtime is available. Core product workflows must not depend on it.

## 1.3 Single public entry point

The frontend must call the gateway for:

- HTTP API requests;
- Server-Sent Events;
- WebSocket connections;
- authentication;
- AI requests;
- health information.

The frontend must not hardcode internal ports such as `8080`, `8002`, or `8003`.

## 1.4 Backward compatibility

Existing routes and response fields must continue working while new canonical routes are introduced.

Add aliases and deprecation notes rather than breaking the current frontend or tests.

## 1.5 Free and local-first

The default implementation must require:

- no paid API;
- no mandatory account;
- no cloud database;
- no mandatory Docker;
- no mandatory GPU;
- no external authentication provider;
- no mandatory Redis, Kafka, or hosted observability platform.

External integrations may exist only behind optional adapters and must be disabled by default.

## 1.6 AI is advisory

AI must never:

- silently create or update incidents;
- automatically dispatch vehicles;
- override deterministic simulation calculations;
- invent incident, vehicle, or environmental records;
- claim certainty where the underlying data is absent;
- send local data to a remote endpoint unless explicitly enabled.

All write actions originating from AI suggestions require explicit user confirmation and normal backend validation.

---

# 2. Product Scope

## 2.1 Prototype name and positioning

Use this accurate positioning in the UI and documentation:

> UrbanShield is a local-first operational digital twin prototype for incident monitoring, emergency-response simulation, resource coordination, and decision support.

Do not present it as a deployed emergency system or a replacement for official emergency services.

## 2.2 Primary users

### Viewer

- view dashboard, map, incidents, simulations, and public metrics;
- cannot modify operational records.

### Operator

- create and update incidents;
- run simulations;
- inspect history;
- use AI explanations and drafts.

### Dispatcher

- manage vehicles and dispatches;
- assign and release vehicles;
- update dispatch status;
- inspect response recommendations.

### Administrator

- manage local users and roles;
- access system diagnostics and audit records;
- control AI and runtime configuration.

## 2.3 Core workflows

### Incident workflow

```text
Create incident
→ validate and persist
→ create history and audit record
→ publish realtime event
→ show on dashboard and map
→ update status/severity/details
→ resolve or close
```

### Dispatch workflow

```text
Select active incident
→ inspect available vehicles
→ create dispatch
→ mark vehicle assigned
→ update dispatch state
→ release vehicle
→ resolve incident
→ preserve full audit history
```

### Simulation workflow

```text
Create scenario
→ validate inputs
→ run deterministic simulation
→ store scenario version and run
→ stream progress
→ display result and warnings
→ compare runs
→ optionally create an incident draft
```

### AI-assisted workflow

```text
Select trusted application data
→ send bounded structured context to local AI service
→ validate structured model output
→ show evidence, model, warnings, and confidence limits
→ require confirmation before any write action
```

---

# 3. Canonical API Design

## 3.1 Gateway routes

Introduce these canonical gateway routes:

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
/api/v1/events/incidents
/api/v1/ws/simulations
```

Keep legacy aliases such as:

```text
/core/api/core/*
/simulation/api/simulation/*
```

## 3.2 Error envelope

All new API errors should use:

```json
{
  "error": {
    "code": "INCIDENT_NOT_FOUND",
    "message": "Incident was not found.",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

Never leak stack traces, secrets, raw SQL, or internal filesystem paths through public responses.

## 3.3 Pagination

List endpoints should support:

```text
page
page_size
sort
order
query
status
severity
type
from
to
```

Responses should include:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_next": false
}
```

## 3.4 Concurrency protection

Mutable operational entities should include a `version` integer.

Update requests should reject stale versions with `409 Conflict`.

## 3.5 API documentation

FastAPI OpenAPI documents are the source of truth for Python services.

Generate or maintain frontend TypeScript contract types from the OpenAPI schemas, or create a checked shared contract package if generation is not practical.

---

# 4. Data Model

Use SQLAlchemy 2-style models and Alembic migrations for the Python core API.

## 4.1 Required entities

### users

- id
- username
- display_name
- password_hash
- role
- is_active
- created_at
- updated_at
- last_login_at

### incidents

- id
- title
- description
- incident_type
- severity
- status
- latitude
- longitude
- reported_at
- created_at
- updated_at
- version
- created_by
- updated_by

### incident_history

- id
- incident_id
- action
- before_json
- after_json
- actor_id
- correlation_id
- created_at

### vehicles

- id
- call_sign
- vehicle_type
- status
- latitude
- longitude
- capacity
- speed
- assigned_incident_id
- version
- created_at
- updated_at

### dispatches

- id
- incident_id
- vehicle_id
- status
- priority
- dispatched_at
- acknowledged_at
- arrived_at
- completed_at
- notes
- version
- created_by
- created_at
- updated_at

### environment_readings

- id
- latitude
- longitude
- temperature_c
- humidity_percent
- air_quality_index
- visibility_km
- weather_condition
- observed_at
- source

### audit_logs

- id
- actor_id
- action
- entity_type
- entity_id
- summary
- metadata_json
- correlation_id
- created_at

### outbox_events

- id
- event_type
- aggregate_type
- aggregate_id
- payload_json
- status
- attempts
- created_at
- processed_at

### simulation_scenarios

- id
- name
- description
- input_json
- input_hash
- scenario_version
- created_by
- created_at
- updated_at

### simulation_runs

- id
- scenario_id
- simulation_version
- input_json
- input_hash
- result_json
- warnings_json
- status
- seed
- started_at
- completed_at
- duration_ms
- created_by

### ai_runs

- id
- operation
- provider
- model
- prompt_template_version
- input_hash
- result_json
- warnings_json
- latency_ms
- status
- fallback_used
- created_by
- created_at

Do not store passwords, bearer tokens, raw secrets, or unrestricted chain-of-thought content.

## 4.2 Migration rules

- Never modify a migration that may already have run.
- Create forward-only versioned migrations.
- Make migration and seed commands idempotent.
- Back up the SQLite database before destructive reset operations.
- Add tests that create a database from zero and apply all migrations.
- Keep repository boundaries clean enough to support a later PostgreSQL/PostGIS adapter.

---

# 5. Deterministic Simulation Contract

## 5.1 Inputs

At minimum:

- incident type;
- severity;
- latitude and longitude;
- available vehicle count;
- selected vehicles;
- traffic level;
- weather condition;
- road-block state;
- simulation duration;
- deterministic seed;
- optional environmental snapshot.

## 5.2 Outputs

At minimum:

- risk score;
- estimated response time;
- affected radius;
- recommended vehicle count;
- operational warnings;
- response stages;
- selected assumptions;
- simulation version;
- input hash;
- reproducibility metadata.

## 5.3 Reproducibility

Identical normalized inputs, seed, and simulation version must produce identical results.

Store:

```text
simulation_version
seed
normalized_input
input_hash
result
started_at
completed_at
duration_ms
```

## 5.4 Validation

Reject:

- coordinates outside valid ranges;
- negative counts or durations;
- unknown enum values;
- selected vehicles that do not exist;
- unavailable vehicles where availability is required;
- malformed scenario objects.

## 5.5 AI boundary

The deterministic engine computes all operational values.

The AI layer may explain a result in plain language but must receive the already calculated result and must not replace it.

---

# 6. Local AI Architecture

## 6.1 Service

Add:

```text
ai-service/
  app/
    main.py
    config.py
    schemas.py
    service.py
    prompts.py
    guardrails.py
    providers/
      base.py
      openai_compatible.py
      ollama.py
      disabled.py
    tests/
```

Use FastAPI, Pydantic, and `httpx`.

## 6.2 Provider interface

Define a stable interface:

```python
class AIProvider(Protocol):
    async def health(self) -> ProviderHealth: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def generate_structured(
        self,
        messages: list[Message],
        output_schema: dict,
        *,
        model: str,
        temperature: float = 0.0,
    ) -> dict: ...
    async def stream_chat(...): ...
```

## 6.3 Supported runtimes

### Default: Ollama

Default local base URL:

```text
http://localhost:11434
```

Use its native model-list endpoint for discovery and its OpenAI-compatible API for generation where practical.

### Alternative: llama.cpp server

Support any OpenAI-compatible local endpoint, including `llama-server`.

### Generic adapter

Allow another OpenAI-compatible endpoint through environment variables, but block non-local hosts unless `AI_ALLOW_REMOTE=true`.

## 6.4 Suggested model profiles

Do not hardcode a single mandatory model.

Provide presets:

```text
Light:    qwen3:1.7b
Balanced: qwen3:4b
Quality:  qwen3:8b
```

The actual model selector must list locally installed models. The service should not assume the preset is installed.

Normal startup must not silently download a multi-gigabyte model.

Add an explicit command such as:

```powershell
python start.py --setup-ai --model qwen3:4b
```

This command may call `ollama pull` only after the user explicitly invokes it.

## 6.5 Environment variables

Add to `.env.example`:

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

## 6.6 AI endpoints

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

## 6.7 Structured outputs

Every task-specific AI endpoint must:

- define a Pydantic output model;
- request schema-constrained JSON;
- use temperature `0` by default;
- validate the returned JSON;
- retry once with a repair prompt if validation fails;
- return a safe deterministic fallback or a clear `AI_UNAVAILABLE` error;
- include provider, model, latency, template version, warnings, and evidence IDs.

Example dispatch advisory response:

```json
{
  "summary": "Two vehicles are suitable based on availability and distance.",
  "recommended_vehicle_ids": ["veh-1", "veh-4"],
  "reasons": [
    {
      "vehicle_id": "veh-1",
      "reason": "Available and closest among eligible ambulances."
    }
  ],
  "warnings": [
    "Recommendation is advisory and must be confirmed by a dispatcher."
  ],
  "evidence_ids": ["incident-12", "veh-1", "veh-4"],
  "model": "qwen3:4b",
  "provider": "ollama",
  "fallback_used": false
}
```

## 6.8 Guardrails

- Treat incident descriptions and imported text as untrusted data.
- Delimit application data from system instructions.
- Do not let data redefine the model’s role or tools.
- Allow-list tools and fields.
- Limit input size.
- Add request timeouts and a concurrency semaphore.
- Redact secrets and authorization headers from logs.
- Do not log raw prompts by default.
- Do not expose hidden reasoning.
- Require normal role permissions for any confirmed write.
- Label AI output as advisory.
- Show the active model and provider in the UI.

## 6.9 AI-free fallback

When Ollama or the selected model is unavailable:

- dashboard, incidents, vehicles, dispatch, simulations, auth, and exports still work;
- AI health reports `degraded`;
- UI shows a non-blocking setup card;
- simulation explanations use deterministic templates;
- dispatch ranking uses deterministic distance, status, type, and capacity rules;
- no fake “AI generated” label is shown.

---

# 7. Authentication and Authorization

## 7.1 Local authentication

Implement local users in SQLite.

Use:

- Argon2 password hashes;
- short-lived signed access tokens or secure local sessions;
- role checks on the backend;
- disabled-by-default public registration;
- a seed command for demo accounts.

Never store plain-text passwords.

## 7.2 Demo accounts

Create demo users only during explicit seed/setup:

```text
viewer
operator
dispatcher
admin
```

Generate secure random initial passwords and print them once, or require values through environment variables.

Do not commit real default passwords.

## 7.3 Authorization matrix

| Resource | Viewer | Operator | Dispatcher | Admin |
|---|---:|---:|---:|---:|
| Read dashboard/incidents | Yes | Yes | Yes | Yes |
| Create/update incidents | No | Yes | Limited | Yes |
| Delete incidents | No | No | No | Yes |
| Run simulations | No | Yes | Yes | Yes |
| Manage vehicles | No | No | Yes | Yes |
| Manage dispatches | No | No | Yes | Yes |
| View audit logs | No | Limited | Limited | Yes |
| Manage users/settings | No | No | No | Yes |
| Use AI explanations | Yes | Yes | Yes | Yes |
| Confirm AI-generated writes | No | Yes | Role-limited | Yes |

Enforce this in backend dependencies, not only by hiding buttons.

---

# 8. Gateway and Realtime Unification

## 8.1 HTTP proxy

Preserve:

- correlation IDs;
- body-size limits;
- upstream timeouts;
- CORS;
- security headers;
- rate limiting;
- clear upstream error translation.

## 8.2 SSE proxy

Expose incident events through:

```text
GET /api/v1/events/incidents
```

Requirements:

- preserve streaming;
- send heartbeat comments;
- handle disconnects;
- include event IDs;
- support reconnection using `Last-Event-ID`;
- authenticate before opening the stream;
- test with a real streaming client.

## 8.3 WebSocket proxy

Expose simulation progress through:

```text
WS /api/v1/ws/simulations
```

Requirements:

- validate the token during handshake;
- pass correlation/run IDs;
- relay close codes correctly;
- enforce message-size limits;
- clean up disconnected clients;
- test gateway-to-service forwarding.

## 8.4 Health

`/health/services` should report:

```json
{
  "gateway": "healthy",
  "core_api": "healthy",
  "simulation_service": "healthy",
  "ai_service": "degraded",
  "frontend": "healthy"
}
```

AI degradation must not mark the complete platform unhealthy.

---

# 9. Frontend Experience

## 9.1 Required pages

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

Hide or disable pages according to role.

## 9.2 Dashboard

Include:

- active incident count;
- severity distribution;
- incident status distribution;
- available/assigned vehicle counts;
- average deterministic response estimate;
- service-health summary;
- recent activity;
- map with incident and vehicle layers.

## 9.3 Map

Keep MapLibre.

Requirements:

- visible map attribution;
- configurable tile/style URL;
- normal interactive tile usage only;
- no background tile scraping or region prefetch;
- offline fallback that displays a local grid/GeoJSON canvas without claiming full offline map coverage;
- incident and vehicle markers;
- clustering where useful;
- filters synchronized with list views;
- accessible non-map list alternative.

## 9.4 Incident detail

Show:

- current fields;
- status and severity controls;
- map location;
- history timeline;
- related dispatches;
- audit entries allowed for the role;
- “Explain” or “Summarize” AI action;
- explicit confirmation before applying an AI-generated draft.

## 9.5 Operations

Support:

- available vehicle list;
- distance and eligibility indicators;
- manual assignment;
- dispatch state transitions;
- deterministic recommendation;
- optional AI explanation;
- conflict and stale-version handling.

## 9.6 Simulations

Support:

- scenario creation;
- validation errors;
- live progress;
- persisted run history;
- side-by-side run comparison;
- warnings and assumptions;
- export to JSON and CSV;
- print-friendly report;
- optional local-AI explanation.

## 9.7 Assistant

The assistant should be grounded by application tools, not by dumping the entire database into a prompt.

Supported read-only tools:

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

Any proposed write should become a preview object and require confirmation through the normal API.

## 9.8 States and accessibility

Every data view must handle:

- loading;
- empty;
- error;
- stale/offline;
- unauthorized;
- success.

Maintain:

- keyboard navigation;
- visible focus;
- labelled controls;
- sufficient contrast;
- reduced-motion support;
- responsive layouts;
- list alternatives for map-only information.

---

# 10. Offline and PWA Behavior

Use Next.js App Router PWA conventions already compatible with the project.

Cache only:

- application shell;
- icons and static assets;
- safe read-only API responses with bounded lifetime;
- locally created drafts.

Do not cache:

- authentication tokens;
- secrets;
- unrestricted audit data;
- destructive responses.

Queued writes must:

- have a client-generated idempotency key;
- show pending status;
- be replayed only after reconnection;
- handle `409 Conflict`;
- never silently overwrite newer server state.

Do not prefetch OpenStreetMap tiles for offline use.

---

# 11. Observability

Keep observability lightweight and free.

## 11.1 Logs

Use structured JSON logs with:

- timestamp;
- level;
- service;
- correlation ID;
- route;
- status;
- duration;
- safe error code.

Redact:

- passwords;
- tokens;
- cookies;
- API keys;
- raw AI prompts by default.

## 11.2 Metrics

Expose Prometheus-style metrics for:

- request counts;
- latency;
- error counts;
- rate-limit rejections;
- active SSE connections;
- active WebSocket connections;
- simulation duration;
- AI request status and latency;
- provider health.

Do not require Prometheus or Grafana to run the prototype.

## 11.3 Audit

Audit operational writes, authentication events, role changes, dispatch decisions, and confirmed AI-assisted actions.

---

# 12. Testing Strategy

## 12.1 Core API tests

Cover:

- migration from empty database;
- CRUD success and validation failures;
- filters and pagination;
- stale version conflicts;
- history and audit creation;
- dispatch state transitions;
- role authorization;
- outbox event creation;
- idempotency.

## 12.2 Simulation tests

Cover:

- deterministic reproducibility;
- input normalization;
- invalid coordinates and enum values;
- progress events;
- run persistence;
- version metadata;
- comparison output.

## 12.3 AI service tests

Use fake HTTP providers; do not require a downloaded model in normal CI.

Cover:

- provider unavailable;
- model missing;
- valid structured output;
- invalid JSON and repair retry;
- timeout;
- remote endpoint blocked by default;
- prompt-injection text treated as data;
- fallback behavior;
- no-write policy.

Add an optional manual/integration marker for a real local Ollama instance.

## 12.4 Gateway tests

Cover:

- HTTP routing;
- legacy aliases;
- correlation IDs;
- CORS and security headers;
- body limits;
- timeout translation;
- rate limiting;
- SSE proxy;
- WebSocket proxy;
- authentication forwarding.

## 12.5 Frontend tests

Cover:

- dashboard states;
- incident forms;
- role-based controls;
- dispatch workflow;
- simulation builder and comparison;
- AI unavailable state;
- AI preview and confirmation;
- offline queue conflict;
- accessible labels.

## 12.6 End-to-end smoke tests

Add a small Playwright suite for:

```text
login
create incident
edit incident
dispatch vehicle
run simulation
inspect result
open realtime connection
use AI fallback or local provider
logout
```

Do not make model installation mandatory for E2E.

---

# 13. Start Script Requirements

Preserve all existing commands.

Add or standardize:

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
python start.py --with-ai
python start.py --without-ai
python start.py --ai-check
python start.py --setup-ai --model qwen3:4b
python start.py --e2e
```

Requirements:

- work from the repository root;
- work on Windows PowerShell;
- use clear process logs;
- detect port conflicts;
- shut down child processes cleanly;
- avoid orphan processes;
- avoid silently installing global software;
- fail with actionable messages;
- keep the platform usable when AI is unavailable.

---

# 14. Delivery Phases and Gates

## Phase 0 — Repository audit and baseline

### Work

- inspect every service, route, test, config, and startup command;
- run current tests and builds;
- record existing failures separately from newly introduced failures;
- document current ports, routes, schemas, and database behavior;
- identify hardcoded internal URLs;
- create `docs/implementation-status.md`.

### Gate

No architecture changes before the baseline is recorded.

---

## Phase 1 — Stabilize local runtime

### Work

- fix `start.py` lifecycle;
- make setup, migrate, seed, reset, status, restart, and stop reliable;
- validate environment variables;
- improve service health checks;
- ensure clean Windows startup and shutdown;
- preserve production frontend build path.

### Gate

The following succeed from a clean local setup:

```powershell
python start.py
python start.py --health-report
python start.py --test
python start.py --stop
```

---

## Phase 2 — Contracts and persistence

### Work

- formalize Pydantic schemas;
- add standard error envelope;
- add pagination and validation;
- add Alembic migrations;
- add repository/service boundaries;
- introduce version fields and conflict handling;
- preserve legacy routes.

### Gate

- all migrations apply from zero;
- existing data is preserved or migrated;
- API tests pass;
- frontend typecheck passes;
- legacy route tests pass.

---

## Phase 3 — Complete operational workflows

### Work

- complete incident history;
- complete vehicles and dispatch lifecycle;
- add audit records;
- add outbox events;
- implement role-aware validation;
- add UI pages and state handling.

### Gate

A seeded user can complete the full incident-to-dispatch-to-resolution workflow through the UI.

---

## Phase 4 — Simulation persistence and comparison

### Work

- version simulation rules;
- normalize inputs;
- persist scenarios and runs;
- add input hashes and seeds;
- add progress tracking;
- add comparison and export.

### Gate

Two identical runs produce identical results and persisted metadata. Different runs can be compared in the UI.

---

## Phase 5 — Authentication and roles

### Work

- add local users;
- hash passwords with Argon2;
- issue and validate sessions/tokens;
- enforce backend permissions;
- add login/logout;
- hide unauthorized UI;
- audit auth and role changes.

### Gate

Authorization tests prove that forbidden operations cannot be performed by lower roles even through direct API calls.

---

## Phase 6 — Gateway and realtime

### Work

- add canonical `/api/v1` routes;
- proxy SSE through gateway;
- proxy WebSocket through gateway;
- move frontend configuration to gateway-only URLs;
- preserve legacy endpoints.

### Gate

Browser network traffic for app functionality uses port `8000`, except normal frontend assets on `3000` and optional external map tiles.

---

## Phase 7 — Local AI service

### Work

- add optional AI service;
- add Ollama and generic OpenAI-compatible adapters;
- add model discovery;
- add structured task endpoints;
- add deterministic fallback;
- add guardrails and UI;
- add `start.py` AI commands.

### Gate

The platform passes all tests with no model runtime installed. When Ollama and a supported model are installed, all AI demos work without code changes.

---

## Phase 8 — Offline, PWA, and UX polish

### Work

- complete manifest and service-worker behavior;
- add safe offline drafts;
- add idempotency and conflict UI;
- improve responsive layout;
- improve accessibility;
- add print-friendly reports;
- add realistic seed data.

### Gate

Core read views and draft creation remain understandable offline, and queued actions do not overwrite newer server state.

---

## Phase 9 — Observability, E2E, and documentation

### Work

- add structured logs and metrics;
- add Playwright smoke tests;
- update README and architecture docs;
- add demo script and troubleshooting;
- remove dead code and placeholders;
- complete validation matrix.

### Gate

A new contributor can clone, set up, run, test, demo, and understand the system using repository documentation alone.

---

# 15. Definition of Done

A feature is complete only when:

- implementation is real, not a placeholder;
- errors and empty states are handled;
- tests cover the changed behavior;
- relevant tests actually pass;
- frontend typecheck and lint pass;
- API contracts are documented;
- environment variables are added to `.env.example`;
- Windows no-Docker startup still works;
- existing public behavior remains compatible;
- security and authorization are enforced server-side;
- logs do not expose secrets;
- AI remains optional and advisory;
- changed commands and architecture are documented;
- the completion report states exactly what was and was not validated.

Never claim a command passed unless it was executed successfully.

---

# 16. Demonstration Scenario

Seed a complete Delhi-style fictional scenario using clearly synthetic data:

1. Operator logs in.
2. Dashboard shows incidents, vehicles, and environment readings.
3. Operator creates a high-severity road accident.
4. Incident appears on map and realtime feed.
5. Dispatcher sees eligible vehicles and deterministic ranking.
6. Dispatcher assigns an ambulance and response vehicle.
7. Dispatch states progress through acknowledged, en route, arrived, and completed.
8. Operator runs a traffic-and-weather simulation.
9. Progress arrives through the gateway WebSocket.
10. Run is persisted and compared with a less-congested scenario.
11. Local AI explains the difference, or deterministic fallback explains it when no model exists.
12. Incident is resolved.
13. Audit timeline shows the complete sequence.
14. System page shows health, metrics, provider status, and active model.

All names, locations, numbers, and events used in the demo must be synthetic.

---

# 17. Cost-Control Checklist

The default prototype must use:

- SQLite;
- local Python processes;
- local Node.js frontend;
- MapLibre;
- user-viewed OSM tiles with attribution and policy compliance, or a configured alternative;
- deterministic local simulation;
- Ollama or llama.cpp only when the user enables AI;
- locally installed open-weight models;
- local JSON logs and built-in metrics;
- no mandatory cloud deployment.

Optional integrations must be clearly marked and disabled by default.

---

# 18. Required Documentation

Create or update:

```text
README.md
AGENTS.md
.env.example
docs/architecture.md
docs/api.md
docs/data-model.md
docs/simulation.md
docs/ai-local-models.md
docs/security.md
docs/testing.md
docs/demo-script.md
docs/troubleshooting-windows.md
docs/implementation-status.md
```

`docs/implementation-status.md` should contain a checklist for every phase with:

- status;
- files changed;
- validation commands;
- known limitations;
- deferred work.

---

# 19. Explicitly Deferred Work

Do not add these to the default prototype unless the repository already needs them:

- Kubernetes;
- Helm;
- Kafka;
- Spark;
- Flink;
- a mandatory Redis instance;
- a mandatory PostgreSQL/PostGIS server;
- a hosted vector database;
- a paid LLM API;
- a paid map provider;
- live emergency-service integration;
- automatic real-world dispatch;
- biometric identification;
- large-scale city sensor ingestion.

Keep extension interfaces clean so these can be added later without rewriting the prototype.

---

# 20. Official Technical References

- Ollama API and OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- Ollama model listing: https://docs.ollama.com/api/tags
- Ollama Qwen3 model family: https://ollama.com/library/qwen3
- llama.cpp local OpenAI-compatible server: https://github.com/ggml-org/llama.cpp
- Qwen3 model card: https://huggingface.co/Qwen/Qwen3-4B
- FastAPI: https://fastapi.tiangolo.com/
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- FastAPI security tutorial: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- MapLibre GL JS: https://maplibre.org/
- OpenStreetMap tile policy: https://operations.osmfoundation.org/policies/tiles/
- Next.js PWA guide: https://nextjs.org/docs/app/guides/progressive-web-apps
