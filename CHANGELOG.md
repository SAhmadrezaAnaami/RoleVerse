# Changelog

All notable changes to RoleVerse are documented in this file.

## [Unreleased]

### Added

- Initial product plan and delivery milestones.
- Versioned FastAPI health endpoint.
- Static client shell with chat, discovery, marketplace, and favorites views.
- English and Persian language switching with RTL and LTR layout support.
- Light and dark theme switching with local preference persistence.
- Responsive conversation workspace with character selection and a local preview response.
- Semantic design-system reference for the project.
- Development dependency manifest and API smoke tests.
- Development version marker and documented branch integration workflow.
- Development phone OTP authentication with console delivery, hashed challenges, and replay protection.
- Opaque HttpOnly session cookies with current-user, logout, and logout-all endpoints.
- Initial SQLAlchemy user/auth models and Alembic migration.
- Safe provider-test fixture example with ignored local configuration.
- Persistent bilingual character catalog with public discovery and detail APIs.
- Owner-scoped conversations with localized greetings and ordered idempotent messages.
- Development preview replies and API-backed client conversation restoration.
- Mock-first OpenAI-compatible provider boundary with explicit live-provider configuration and secret-safe URL validation.
- Persisted generation runs with queued, streaming, complete, failed, and cancelled states.
- Non-streaming and SSE streaming generation routes with ordered message persistence and safe error events.
- Generation usage and integer micro-cost snapshots, finish reasons, and owner-scoped status/cancel routes.
- Client SSE parsing, streaming message states, cancellation, and authenticated conversation recovery.
- In-memory global and per-user generation rate-limit primitives.
- Server-authorized administration APIs for masked users, bans, role elevation, provider/model metadata, usage, settings, and audit events.
- Separate responsive bilingual admin workspace at `/admin.html` and `/admin/` with safe provider metadata and no secret inputs.
- Ban operations revoke existing sessions and cancel active generations transactionally.
- Persisted generation rate-limit and maximum-output settings are read by the generation route.

### Changed

- Replaced the placeholder getting-started section with local development instructions.

### Known limitations

- Development OTP delivery uses the server console; production SMS delivery is not implemented.
- Sessions currently use a development role column; normalized permissions and god-user promotion workflows are deferred.
- Anonymous client conversations still use deterministic local preview data.
- Live provider calls, durable resumable event replay, and production provider administration require explicit operational configuration and are not enabled by default.
- The admin control plane is metadata-only; encrypted server-side provider secret management, live provider activation, distributed quotas, and full session-bound CSRF hardening are deferred.
- The marketplace publishing workflow is not implemented yet.
