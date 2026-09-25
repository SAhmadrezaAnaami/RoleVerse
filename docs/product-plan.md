# RoleVerse Product Plan

## Product promise

RoleVerse is a bilingual role-play chat platform where people can create relationships with curated characters that have a defined identity, soul, persona, history, and extra context. The product should feel as familiar and calm as a modern AI chat workspace while remaining colorful, alive, and emotionally engaging.

## Users

- Visitors discover the product and available characters.
- Members sign in with a phone number and development OTP, then chat with characters.
- Creators and community members browse or submit characters through the marketplace.
- Admins manage characters, users, conversations, providers, models, usage, costs, bans, settings, and rate limits.
- The god user configured in the environment can promote trusted users to administrators.

## Core product rules

- Membership and conversations are free; there is no payment flow in the initial product scope.
- Authentication uses phone-number verification. Development OTPs are printed to the server console until a production SMS provider is selected.
- Character identity, persona, history, and additional context are separate data concerns.
- Provider and model configuration stays behind an OpenAI-compatible boundary.
- Every request passes through global and per-user rate limits.
- The interface supports English and Persian, LTR and RTL, and light and dark themes.

## Delivery milestones

### Milestone 1: Foundation and first vertical slice

- Establish backend and client folder boundaries.
- Provide a healthy FastAPI service with versioned API routing.
- Provide a responsive chat workspace shell with character navigation, conversation view, composer, theme toggle, language toggle, and mobile navigation.
- Establish semantic design tokens and accessibility baselines.
- Add a changelog and repeatable local development commands.

### Milestone 2: Identity and persistence

- Add users, sessions, roles, phone OTP challenges, bans, and god-user promotion.
- Add SQLAlchemy models, repositories, schema validation, and Alembic migrations.
- Add login, signup, verification, logout, and protected API middleware.

### Milestone 3: Character library and marketplace

- Add character CRUD for administrators.
- Add avatar, category, tags, greeting, persona, soul, backstory, and visibility fields.
- Add discovery, search, filters, favorites, and submission workflow.

### Milestone 4: Conversations and providers

- Add chats, messages, branches, and history.
- Add OpenAI-compatible provider, model, streaming, usage, and cost tracking.
- Add global and per-user rate-limit configuration.

### Milestone 5: Administration and operations

- Build the admin workspace for users, characters, chats, providers, models, usage, costs, bans, settings, and rate limits.
- Add audit events, operational metrics, and safe configuration changes.

## Current vertical slice

The current usable slice now includes a persistent character catalog, owner-scoped conversations, persisted localized greetings, ordered preview messages, and a mock-first provider generation boundary. Authenticated clients can persist a user turn, stream a normalized assistant response, cancel an active run, and restore the completed conversation after reload. Session-bound CSRF protection, auth epochs, strict origin checks, CSP-protected static pages, generation terminal compare-and-set updates, and provider output/redirect safeguards are included. Authorized administrators can use the separate control plane to review users, bans, safe provider/model metadata, usage and cost, settings, rate limits, session revocation, and audit events. Live OpenAI-compatible calls and live provider activation remain disabled by default.

## Non-goals for the first slice

- Real SMS delivery
- Payments or subscriptions
- Production-grade live OpenAI-compatible operations and provider administration
- Full marketplace publishing workflow
- Production-grade moderation and abuse prevention
- Encrypted provider secret management, distributed rate limiting, DNS-pinned provider egress, and live provider activation

## Acceptance criteria

- The client is usable at 375px, 768px, 1024px, and 1440px widths.
- The workspace supports English and Persian without layout breakage.
- The workspace supports light and dark mode with persistent local preference.
- All primary controls have visible keyboard focus and accessible names.
- The chat composer supports a character selection and a local message interaction.
- The FastAPI service exposes a versioned health endpoint and serves the client in local development.
- Published characters are publicly discoverable and hidden characters are not exposed.
- Authenticated users can create, reload, and append to only their own conversations.
- Message history has deterministic ordering and idempotent client request keys.
- The repository has documented setup, branch, changelog, and testing conventions.
