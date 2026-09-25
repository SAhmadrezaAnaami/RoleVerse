# RoleVerse Architecture

## Runtime shape

RoleVerse is split into a static client and a FastAPI backend. The backend owns the API boundary and serves the static client during local development.

```text
browser
  -> static client
  -> /api/v1 endpoints
  -> route dependencies
  -> services
  -> repositories
  -> SQLAlchemy session
  -> SQLite
  -> OpenAI-compatible provider adapter
```

Routes should not contain SQLAlchemy queries. Services own use cases and authorization decisions. Repositories own persistence queries and return typed values. SQLAlchemy models are never returned directly by API routes.

## Repository layout

```text
client/
  index.html
  assets/
    css/
      tokens.css
      layout.css
      components.css
      responsive.css
    js/
      data.js
      i18n.js
      api.js
      app.js

backend/
  pyproject.toml
  .env.example
  app/
    main.py
    core/
      config.py
    api/
      router.py
      routes/
        health.py
    db/
      base.py
      session.py
    schemas/
      health.py
  tests/
    test_health.py
```

The first slice uses deterministic client data so the interaction model can be reviewed before authentication and persistence are connected.

## Backend boundaries

- `core` contains process configuration and cross-cutting utilities.
- `api` contains versioned routers, request dependencies, and response schemas.
- `services` will contain authentication, characters, conversations, generation, rate limits, and admin use cases.
- `db/models` will contain SQLAlchemy entities.
- `db/repositories` will contain typed persistence operations.
- `providers` will contain OpenAI-compatible adapters and a registry.
- `schemas` will contain input, output, pagination, and persistence-facing contracts.

The planned dependency direction is:

```text
API routes -> services -> repositories -> SQLAlchemy
Services -> provider adapter
```

## Data model direction

The next database milestone will introduce UUID string identifiers, UTC timestamps, foreign keys, and migrations for:

- users and roles
- OTP challenges and sessions
- characters and marketplace metadata
- conversations and messages
- providers and provider models
- generation runs and usage costs
- system settings, rate-limit counters, and audit logs

The god user is an environment-controlled privilege and is not a client-controlled role. Provider keys and OTP codes must never be returned in API responses or written to normal logs.

## Client boundaries

The current client uses classic scripts so it remains directly static and does not require Node.js or a bundler. `app.js` owns presentation state, while `api.js` is the replacement point for real API calls. Later API methods can be added without changing the page interaction model.

The client stores only UI preferences and preview conversation state. OTPs, sessions, provider credentials, and production secrets remain server-side.

## API naming

All endpoints use the `/api/v1` prefix. The first route is:

```text
GET /api/v1/health
```

The static client is mounted at `/` after the API routes so the same local server can serve both layers.

## Operational defaults

- SQLite is the first development database.
- SQLAlchemy sessions are short-lived and provided through FastAPI dependencies.
- Schema changes must use Alembic migrations; application startup must not call `create_all()`.
- CORS origins are environment-configurable.
- The default environment is development and must not be used for production secrets.
- Provider calls will eventually use a bounded, model-aware history budget and idempotent request identifiers.

## Current development auth section

The first persisted vertical slice now includes:

- `users` for phone identity, role, status, and language preference
- `otp_challenges` for short-lived development verification codes
- `auth_sessions` for opaque server-side session tokens
- `/api/v1/auth/otp/request`, `/api/v1/auth/otp/verify`, `/api/v1/auth/me`, `/api/v1/auth/logout`, and `/api/v1/auth/logout-all`
- Alembic migration `0001_data_auth`
- HMAC-SHA-256 hashes for OTP codes and session tokens using a server-side pepper

The role column is an initial development boundary. A normalized role/permission model and explicit god-user promotion workflow will be added with the administration section. The configured god phone is never accepted from the client and is normalized at startup.

The development OTP sender writes only a masked phone and generated code to the server console. It is rejected when the service is configured for production until a real delivery adapter is supplied. Browser storage contains only theme and language preferences; sessions use an HttpOnly cookie. Unsafe authenticated requests additionally use a separate synchronizer CSRF cookie and `X-CSRF-Token` header.

## Current security hardening section

Migration `0005_security_hardening` adds session CSRF hashes and user/session auth epochs. New OTP sessions receive a random CSRF token whose HMAC digest is stored server-side. Authenticated unsafe requests require both a trusted `Origin` and the matching CSRF header. Logout-all, bans, role changes, and administrative session revocation increment the user epoch and invalidate older sessions atomically.

Legacy sessions with an empty CSRF hash fail closed after migration and require a fresh OTP login. Production and staging settings require an explicit high-entropy auth pepper, secure cookies, and HTTPS for authentication. The static client no longer loads executable third-party JavaScript and receives a restrictive CSP.

Generation terminal updates use conditional status transitions. A completion, failure, or cancellation that races with an administrative cancellation cannot overwrite the terminal state. Live provider adapters disable redirects and proxy environment inheritance, enforce production host allowlists, and cap provider output characters; database provider rows remain metadata-only and are not runtime activation sources.

## Current character and conversation section

The persisted slice now includes:

- `characters` for curated bilingual character identity and public discovery metadata
- `conversations` for user-owned chat sessions with a fixed `en`/`fa` locale
- `messages` for ordered persisted turns with client request idempotency
- Alembic migration `0002_characters_chats`
- Explicit development seeding through `python -m scripts.seed_dev`
- Public character list/detail routes and authenticated conversation/message routes

Conversation creation persists the localized character greeting before returning the conversation. Message sending uses a server-owned role and position. The current assistant response is explicitly a deterministic preview; the future provider generation service will replace that step without changing the client message contract.

The current implementation keeps route dependencies thin: routes validate transport data and map domain errors, services enforce ownership and transactions, and repositories scope every query to the authenticated user where private data is involved.

## Current provider and generation section

The provider boundary is server-owned and mock-first. `MockProvider` is selected whenever `LIVE_PROVIDER_ENABLED=false`, even if provider environment variables are present. An explicit live configuration can use environment variables or an explicitly named ignored fixture; the application never discovers local credential files automatically.

Generation uses two authenticated routes after a user-only message is persisted:

```text
POST /api/v1/conversations/{conversation_id}/messages/{message_id}/response
POST /api/v1/conversations/{conversation_id}/messages/{message_id}/responses
```

The first returns the existing message-pair JSON shape. The second emits normalized SSE `start`, `delta`, and `done` or `error` events. Provider output is accumulated in memory and finalized in a short database transaction, so a network stream does not hold a SQLite transaction open. The client uses a UTF-8-aware SSE parser, renders provisional assistant text, and can cancel the active run.

`generation_runs` stores provider/model snapshots, prompt version, lifecycle state, token usage availability, pricing availability, finish reason, and integer micro-cost values. Failed and cancelled assistant messages remain auditable but are excluded from future prompt history. Owner-scoped status and cancellation routes are available at:

```text
GET  /api/v1/conversations/{conversation_id}/generations/{run_id}
POST /api/v1/conversations/{conversation_id}/generations/{run_id}/cancel
```

The in-memory limiter is a development primitive for global and per-user generation quotas. A distributed limiter and durable event replay belong in the operations layer before production scale-out.

## Current administration and operations section

The admin control plane is a separate static surface at `/admin.html` and `/admin/`, while authorization remains server-side. `get_admin_user` requires an active administrator session. Role changes require the configured god user. Ban and unban commands revoke sessions, cancel active generations for the target, and write an audit event in the same transaction.

Admin API routes are under `/api/v1/admin` and return masked user phone numbers. Provider and model records are safe metadata only: no API key, authorization header, fixture path, prompt, or message content is stored or returned. Provider records do not activate the runtime registry; the existing environment/fixture provider boundary remains authoritative.

The admin workspace exposes overview metrics, users and access, provider/model metadata, usage and estimated provider cost, typed settings, rate-limit values, and an append-only audit feed. Admin responses use `no-store`, and unsafe admin mutations require both an allowed same-origin request and a session-bound CSRF token. Provider endpoints are redacted in responses. The current limiter remains process-local; distributed quotas, encrypted secret management, provider health probes, and DNS-pinned egress remain deferred operational work.

Phone numbers, chat content, provider credentials, and audit events are sensitive. The implementation roadmap includes session hashing, OTP expiry and replay protection, bans, rate limits, secret-safe errors, audit records, retention controls, and provider-key encryption before production deployment.
