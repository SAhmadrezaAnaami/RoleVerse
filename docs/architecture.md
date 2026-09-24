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

## Security and privacy boundaries

Phone numbers, chat content, provider credentials, and audit events are sensitive. The implementation roadmap includes session hashing, OTP expiry and replay protection, bans, rate limits, secret-safe errors, audit records, retention controls, and provider-key encryption before production deployment.
