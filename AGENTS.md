# AGENTS.md

Instructions for AI coding agents working on ArtMneme. `CLAUDE.md` imports this file.

---

## Documents

- `docs/process.md` - how work is organized
- Before writing tests, read `docs/testing-guidelines.md`
- For anything touching the UI, read `docs/design-system.md`

## Sources of Truth

Read the relevant document before implementing. When they conflict, this order wins:

1. `product-spec.md`: business behavior and acceptance criteria
2. `openapi.yml`: API contract
3. `database-schema.md`: data model
4. `docs/architecture.md`: layers, technology stack, deployment

Also: `docs/observability.md` covers metrics, alerts and the responder agent.

## Decision Authority

- AI tools may recommend but never decide.
- Proposals are discussed in chat only.
- Project files contain only what the project owner has explicitly decided.
- A stated priority or preference is not a decision.
- If something needed for a task is undecided, stop and ask.

## Agent Rules

- Do not introduce undocumented endpoints. Keep `openapi.yml` and the implementation in sync.
- Record AI contributions in `ai-usage-report.md`.
