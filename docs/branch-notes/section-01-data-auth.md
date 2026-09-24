# Section 01 Data and Development Auth

## Branch

`section/01-data-auth`

## Base

`0dc8940` (`merge: foundation section` on `staging`)

## Scope

- Add SQLAlchemy user, OTP challenge, and auth session models.
- Add the initial Alembic migration and migration round-trip coverage.
- Add phone normalization, development OTP delivery, HMAC-backed code and session hashing, expiry, attempt limits, resend invalidation, and atomic challenge consumption.
- Add opaque HttpOnly session cookies with current-user, logout, and logout-all endpoints.
- Add environment-controlled god-user elevation during successful verification.
- Connect the static sign-in dialog to the FastAPI auth API.
- Add a credential-free provider fixture example and ignore local provider configuration.

## API

- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-all`

## Validation

- `python -m pytest -q` — 17 passed.
- `python -m compileall -q app tests` — passed.
- Client JavaScript syntax checks — passed.
- Alembic upgrade, downgrade, and upgrade round trip — passed.
- Browser smoke test — OTP request, OTP step transition, and invalid-code error verified.

## Database impact

Migration `0001_data_auth` creates `users`, `otp_challenges`, and `auth_sessions` with foreign keys, uniqueness constraints, and indexes. Application startup does not create tables.

## Security and privacy impact

OTP codes and session tokens are not returned in JSON. Values are stored as HMAC-SHA-256 digests, sessions are revocable, auth responses are marked `no-store`, and the development console sender masks phone numbers. The local provider credential file is ignored and was not committed. Any exposed credential must be revoked or rotated before reuse.

## Known limitations

- The role field is a development boundary; normalized permissions and explicit god-user promotion are deferred to the admin section.
- The console OTP sender is not a production SMS provider.
- Character, conversation, provider, streaming, and admin persistence are not part of this section.
- CSRF/Origin enforcement and production identity binding need to be completed before deployment.

## Rollback

Revert the section branch commits or close its pull request. The migration can be rolled back with `alembic downgrade base`; do not run it against production data without a backup.
