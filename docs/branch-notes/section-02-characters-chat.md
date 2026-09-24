# Section 02 Characters and Chat

## Branch

`section/02-characters-chat`

## Base

`cc43ff0` (merge of the data and development auth section into `main`)

## Scope

- Add persistent curated characters with published visibility, bilingual display data, discovery metadata, and development seed data.
- Add owner-scoped conversations with a fixed conversation language and persisted character greeting.
- Add ordered, idempotent user/assistant preview messages.
- Expose public character catalog/detail endpoints and authenticated conversation/message endpoints.
- Connect the static client to character discovery, remote conversations, and persisted preview messages.
- Add migration `0002_characters_chats` and an explicit `scripts.seed_dev` command.

## API

- `GET /api/v1/characters`
- `GET /api/v1/characters/{slug}`
- `GET /api/v1/conversations`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{id}`
- `GET /api/v1/conversations/{id}/messages`
- `POST /api/v1/conversations/{id}/messages`

## Validation

- `python -m pytest -q` — 26 passed.
- Python compilation — passed.
- Client JavaScript syntax checks — passed.
- Alembic upgrade/downgrade/upgrade — passed.
- Browser API catalog and authentication smoke tests — passed.

## Database impact

Migration `0002_characters_chats` creates `characters`, `conversations`, and `messages` with foreign keys, indexes, check constraints, unique message request keys, and deterministic message positions. Character data is seeded explicitly, not during application startup.

## Security and privacy impact

Conversation ownership is enforced in repository queries. Clients cannot submit owner IDs, roles, positions, or assistant status. Message content is bounded by the API schema. Public character responses omit internal persona, soul, backstory, and preview-reply fields. Local provider credentials remain ignored and uncommitted.

## Known limitations

- Assistant messages are deterministic preview replies until the OpenAI-compatible generation service is implemented.
- Character administration and moderation are not exposed yet.
- Message pagination currently uses a bounded initial page; cursor pagination and branching are deferred.
- Provider streaming, generation runs, usage costs, and rate-limit persistence are deferred.
- CSRF/Origin enforcement and production identity binding remain release-hardening work.

## Rollback

Revert the section branch commits or close its pull request. The migration can be rolled back to `0001_data_auth` only after backing up and explicitly accepting loss of character, conversation, and message data.
