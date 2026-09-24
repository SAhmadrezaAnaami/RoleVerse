# Section 00 Foundation

## Branch

`section/00-foundation`

## Base

`2812093` (`Initialize RoleVerse repository`)

## Scope

- Establish the product plan and first vertical slice.
- Add backend/client separation.
- Add a versioned FastAPI health endpoint.
- Add a static chat workspace with sample character data.
- Add English/Persian, RTL/LTR, light/dark, and responsive foundations.
- Establish dependency, ignore, changelog, and testing conventions.

## Validation

- `python -m pytest` from `backend/` — 2 passed.
- `python -m compileall -q app tests` from `backend/` — passed.
- `node --check` for all client JavaScript files — passed.
- Browser smoke test — chat, discovery, character selection, language, theme, composer, and account dialog verified.

## Database impact

No schema migration is included in this section. The SQLAlchemy base and session primitives are present for the next data section. Runtime schema creation is not used.

## Security and privacy impact

The current client stores only theme and language preferences. The account dialog is a visual shell and does not transmit or persist OTPs. No provider credentials are present. A local untracked provider-testing file was excluded from version control; any credential in that file should be rotated before it is used again.

## Known limitations

- Real phone OTP, sessions, persistence, providers, streaming, and administration are deferred.
- The browser uses local deterministic replies for review.

## Rollback

Revert the section branch commits or close the corresponding pull request. No database or remote data migration is required.
