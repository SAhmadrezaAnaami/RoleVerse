# Section 05: Security Hardening

## Scope

This section hardens the persisted session, admin control plane, provider boundary, generation finalization, and static client.

- Session-bound synchronizer CSRF tokens are issued after OTP verification.
- Unsafe browser requests require a trusted `Origin` and `X-CSRF-Token` where a session is authenticated.
- The session token remains `HttpOnly`; only the separate `roleverse_csrf` cookie is readable by the client.
- User and session auth epochs invalidate old sessions after bans, role changes, logout-all, and administrative session revocation.
- Legacy sessions without a usable CSRF hash fail closed and require reauthentication after migration `0005_security_hardening`.
- Generation terminal transitions use compare-and-set updates so a late provider completion cannot overwrite cancellation.
- The static client no longer loads executable Tailwind CDN JavaScript and serves a restrictive CSP.
- Live provider configuration requires a production host allowlist, uses bounded output, disables redirects, and does not inherit proxy environment settings.
- Provider metadata is redacted for admin responses and cannot activate a runtime provider.

## Validation

- Full backend test suite
- Auth, admin, generation, provider, and migration regression coverage
- Alembic upgrade, downgrade, re-upgrade, and `alembic check`
- Python compilation and JavaScript syntax checks
- Browser smoke test for CSRF login, protected admin mutation, CSP, and no external executable scripts

## Deliberate rollout policy

Sessions created before migration `0005_security_hardening` are intentionally invalidated. Users must complete OTP authentication again. Live provider calls remain disabled by default; encrypted secret management, distributed quotas, DNS-pinned egress, and full production observability remain follow-up work.
