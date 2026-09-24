# Provider test fixtures

`llm_openai_compatible.example.json` is the only provider configuration that belongs in Git.

For an opt-in local smoke test, create `llm_openai_compatible.local.json` beside it and provide the endpoint, model, and credential through a local secret source. The `*.local.json` file is ignored by Git.

Live provider tests must be explicitly enabled, use synthetic prompts, and never run against production data. The default test suite uses mocks and does not make external network requests.

If a credential is ever pasted into a tracked file, revoke it immediately and remove it from the working tree and repository history.
