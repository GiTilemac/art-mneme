# AGENTS.md

Instructions for AI coding agents working on ArtMneme. `.claude/CLAUDE.md` imports this file.

---

## Documents

- `docs/process.md` - how work is organized
- Before writing tests, read `docs/testing-guidelines.md`
- For anything touching the UI, read `docs/design-system.md`
- `docs/external-services.md` - every online service and account (AWS, ...): resources, secrets, costs. Update it when a service is added or changed.

## Sources of Truth

Read the relevant document before implementing. When they conflict, this order wins:

1. `product-spec.md`: business behavior and acceptance criteria
2. `openapi.yaml`: API contract
3. `docs/database-schema.md`: data model
4. `docs/architecture.md`: layers, technology stack, deployment

Also: `docs/observability.md` covers metrics, alerts and the responder agent.

## Decision Authority

- AI tools may recommend but never decide.
- Proposals are discussed in chat only.
- Project files contain only what the project owner has explicitly decided.
- A stated priority or preference is not a decision.
- If something needed for a task is undecided, stop and ask.

## Agent Rules

- Reproduce a reported problem before you explain it. If reproducing costs a lot of time or credits, give a possible explanation, mark it as unconfirmed, and ask the project owner before the expensive reproduction.
- Do not introduce undocumented endpoints. Keep `openapi.yaml` and the implementation in sync.
- Record AI contributions in `docs/ai-usage-report.md`.
- Stop and ask the project owner before:
  - deleting important data
  - force-pushing
  - modifying external systems
  - performing destructive operations
  - making a decision that requires the owner's approval

## Guidelines
- Don't assume. Don't hide confusion. Surface tradeoffs.
Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask

- No features beyond what was asked
- No abstractions for single-use code
- No error handling for impossible scenarios.
- If you write e.g. 200 lines and it could be e.g. 50, rewrite it.
- Ask yourself, "Would a senior engineer say this is overcomplicated? If yes, simplify.
- Touch only what you must. Clean up your own mess.
- Don't refactor things that aren't broken.
- If you notice unrelated dead code, mention it. Don't delete it.
- When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

Every changed line should trace directly to the user's request.
Transform tasks into verifiable goals.
"Add validation" includes writing tests for invalid inputs and making them pass.
"Fix the bug" includes writing a test that reproduces it, then making it pass.
"Refactor X" includes tests pass before and after

## Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file

for backend, use uv for dependency management. a few useful commands:

  uv sync
  uv add <PACKAGE-NAME>
  uv run python <PYTHON-FILE>

  regularly commit code to git 

## Rules

- Dependencies are added in `pyproject.toml`. Do not add one without
  asking