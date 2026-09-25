# Git Workflow

RoleVerse uses protected integration branches and small section branches.

## Branches

- `section/*` contains one bounded product section.
- `staging` receives tested section branches.
- `main` is the stable integration baseline.
- `release/*` contains release candidates.
- `hotfix/*` contains urgent fixes.

## Rules

- Agents do not commit or push directly to `main`.
- Every non-merge commit changes one file.
- Commits use Conventional Commit-style messages.
- Section branches are pushed explicitly and retained.
- Tested sections merge into `staging` with a merge commit.
- A maintainer promotes a green `staging` branch to `main` through a protected pull request.
- Force pushes and branch deletion are not used.
- Tags are created only after the tagged commit is tested and present in the approved integration branch.

## Section checklist

1. Fetch the latest remote branches.
2. Create a `section/*` branch from the agreed integration baseline.
3. Add one file per commit.
4. Run the relevant tests and browser checks.
5. Push the named section branch.
6. Merge through pull request into `staging`.
7. Run the full suite on `staging`.
8. Promote the tested commit through the protected `main` workflow.
9. Add a branch note, changelog entry, and release tag when appropriate.

The current active section is `section/05-security-hardening`. It must pass backend, migration, JavaScript syntax, and browser smoke checks before integration.
