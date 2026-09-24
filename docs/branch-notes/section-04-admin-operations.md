# Section 04: Administration and Operations

## Scope

This section adds a server-authorized administration control plane for the existing RoleVerse data model.

- Admin and god-user dependencies protect privileged routes.
- User profile, role, ban, and unban operations are explicit and audited.
- Bans revoke existing sessions and cancel queued or streaming generations.
- Provider and model records contain safe metadata only; API keys and secret values are not stored or returned.
- Admin overview, user, provider, model, usage/cost, settings, and audit endpoints are available under `/api/v1/admin`.
- Generation rate limits and maximum output tokens can be persisted as typed settings and are read by the generation route.
- The separate static admin workspace is available at `/admin.html` and `/admin/`.

## Security boundary

Admin responses use `Cache-Control: no-store`. Admin mutations require an allowed same-origin request. Provider secrets, message content, OTP values, session tokens, and raw phone numbers are not part of admin response schemas. Provider records are metadata/inventory only; the existing mock-first runtime registry remains environment/fixture owned.

## Validation

- Backend admin and regression tests
- Fresh and downgrade/re-upgrade migration checks
- `alembic check`
- Python compilation
- JavaScript syntax checks
- Authenticated browser smoke tests in English and Persian/RTL

## Deferred hardening

- Encrypted/server-side secret management and live provider activation
- Distributed rate limiting and durable event replay
- Full CSRF token/session-epoch hardening across every mutation route
- Fine-grained permissions beyond `user`, `admin`, and god-user checks
- Provider health probes and external egress controls
