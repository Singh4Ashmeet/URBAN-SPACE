# UrbanShield Security

## Current Security Foundation

The Phase 4 foundation adds local production-style safety controls without breaking the verified no-Docker workflow:

- Gateway CORS allow-list for `http://localhost:3000`.
- Gateway request body limit.
- Gateway rate limiting with stricter limits for simulation execution.
- Gateway upstream timeout.
- Gateway correlation ID propagation through `X-Correlation-ID`.
- Gateway security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy`
- Frontend security headers and a local-development Content Security Policy.

## Authorization Matrix

Full authentication and authorization are planned for the database-backed Phase 4 core API.

| Role | Planned Access |
| --- | --- |
| ADMIN | Manage users and configuration |
| CITY_OPERATOR | Create and update incidents |
| INCIDENT_COMMANDER | Dispatch vehicles and run high-severity scenarios |
| EMERGENCY_RESPONDER | Update assigned incidents and vehicle status |
| DATA_ANALYST | View analytics and environmental data |
| AUDITOR | View audit logs |
| VIEWER | Read public dashboard data |

## Current Limitations

- JWT authentication is not implemented yet.
- Password hashing and refresh-token rotation are not implemented yet.
- Audit logging is not implemented yet.
- The local in-memory rate limiter is suitable for the single-process development gateway, not a multi-process deployment.
- The current SQLite-backed core API is suitable for local development persistence, not production multi-user deployment.

## Reporting

Do not commit real secrets. Use `.env.example` for development-only placeholders and keep local `.env` files private.
