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

The first usable slice is a character chat workspace backed by deterministic sample data. It proves the information architecture and interaction model before persistence and model integrations are added. The API boundary is designed so the sample data can be replaced by repository calls without changing the client interaction model.

## Non-goals for the first slice

- Real SMS delivery
- Payments or subscriptions
- Live OpenAI-compatible model responses
- Full marketplace publishing workflow
- Production-grade moderation and abuse prevention

## Acceptance criteria

- The client is usable at 375px, 768px, 1024px, and 1440px widths.
- The workspace supports English and Persian without layout breakage.
- The workspace supports light and dark mode with persistent local preference.
- All primary controls have visible keyboard focus and accessible names.
- The chat composer supports a character selection and a local message interaction.
- The FastAPI service exposes a versioned health endpoint and serves the client in local development.
- The repository has documented setup, branch, changelog, and testing conventions.
