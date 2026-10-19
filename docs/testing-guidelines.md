# Testing Guidelines

## Tools

```text
Backend:   pytest

Frontend:  Vitest + React Testing Library

CI:        GitHub Actions
```

## Rules

1. Every task tests its own acceptance criteria: at least one test per criterion, including the awkward cases.
2. Test names read as plain sentences, for example `test_discoverability_is_refused_when_date_is_missing`.
3. Backend tests use a real PostgreSQL database: a separate, empty database used only for tests.
4. Photo storage is simulated in tests. Tests never use the real Cloudflare R2 account.
5. Frontend tests check what the user sees, such as messages, buttons and their state, not how the code is built inside.
6. All tests must pass before a task is closed. GitHub Actions runs them on every push.
