# Repository Guidelines

## Project Structure & Module Organization

UrbanShield is a multi-service smart city prototype. The default local stack is orchestrated by `start.py` and uses a Python core API, FastAPI simulation service, lightweight gateway, and Next.js frontend.

- `core-api/app/` contains the local Python core API; tests live in `core-api/tests/`.
- `simulation-service/app/` contains the FastAPI simulation engine; tests live in `simulation-service/tests/`.
- `frontend/app/`, `frontend/components/`, `frontend/hooks/`, `frontend/lib/`, and `frontend/types/` contain the Next.js UI; static assets live in `frontend/public/`.
- `core-service/src/` contains the optional Spring Boot/PostGIS service, with Flyway migrations in `src/main/resources/db/migration/`.
- `database/init/`, `gateway/kong.yml`, `docs/`, and `tests/integration/` hold database bootstrap, optional Kong config, documentation, and integration tests.

## Build, Test, and Development Commands

- `python start.py` starts the recommended no-Docker local stack.
- `python start.py --build` builds and runs the production frontend path.
- `python start.py --test` runs available local validation across services.
- `python start.py --health-report` checks service health endpoints.
- `docker compose up --build` runs the optional Docker stack when Docker Desktop is available.
- In `frontend/`: `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`, and `npm test`.
- In `core-service/`: `mvn test` runs optional Java service tests.

## Coding Style & Naming Conventions

Use 4-space indentation for Python and Java, and 2-space indentation for TypeScript/React. Keep Python modules and functions `snake_case`; Java classes `PascalCase`; Java methods and fields `camelCase`; React components `PascalCase`; hooks `useCamelCase`. Keep DTOs, models, services, repositories, and controllers in their existing package folders. Run frontend linting and type checks before changing UI code.

## Testing Guidelines

Add tests for behavior changes. Use `pytest` for Python services, Maven/Spring tests for `core-service`, and the Node test runner plus Testing Library for frontend tests in `frontend/tests/*.test.tsx`. Prefer focused unit tests near the changed service and integration coverage in `tests/integration/` for gateway behavior.

## Commit & Pull Request Guidelines

This checkout has no local commit history, so follow concise imperative commits such as `feat: add incident filters` or `fix: handle gateway timeout`. Pull requests should include a short summary, validation commands run, linked issues when applicable, screenshots for UI changes, and notes for configuration or migration changes.

## Security & Configuration Tips

Do not commit real secrets. Copy from `.env.example` files and keep local overrides in `.env`. Preserve the no-Docker workflow, keep Docker optional, and avoid paid or API-key-only dependencies unless explicitly approved.
