# Provider test fixtures

`llm_openai_compatible.example.json` is the only provider configuration that belongs in Git.

For an opt-in local smoke test, create `llm_openai_compatible.local.json` beside it and provide the endpoint, model, and credential through a local secret source. The `*.local.json` file is ignored by Git.

Live provider tests must be explicitly enabled, use synthetic prompts, and never run against production data. The default test suite uses mocks and does not make external network requests.

The application does not discover or read local fixture files automatically. For a deliberate local run, set `LIVE_PROVIDER_ENABLED=true` and either provide `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`, or set `PROVIDER_FIXTURE_PATH` to the ignored local file. Fixture loading is rejected when `ENVIRONMENT=production`. Production deployments should also set `PROVIDER_ALLOWED_HOSTS` to an explicit comma-separated host allowlist. Use a revoked or dedicated low-quota credential, a small output budget, and synthetic prompts.

If a credential is ever pasted into a tracked file, revoke it immediately and remove it from the working tree and repository history.
