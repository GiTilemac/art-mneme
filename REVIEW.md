# Review guide

A short path through ArtMneme for a reviewer: where each grading criterion is shown.

- **Live app (prod):** https://52-29-146-30.sslip.io (register any email and a password of 8+ characters)
- **Repository:** https://github.com/GiTilemac/art-mneme
- **Task tracker:** https://github.com/GiTilemac/art-mneme/issues

## Try it in 5 minutes

1. Open the live app, create an account, and add an artwork with a photo (Collection) and one without (Watchlist).
2. Open an artwork, then **Explore relationships**.
3. Locally: `docker compose up --build`, then open http://localhost:8000 (app, API and PostgreSQL in one command).
4. All tests in one command: `make test-all` (backend unit, frontend, integration and end-to-end tests).

## Criteria and evidence

| Criterion | Where to look |
|---|---|
| Problem description | `README.md` (top): the problem, the features and the expected behavior |
| Product specification and tracker | `product-spec.md` (behavior and acceptance criteria); `openapi.yaml`; GitHub issues: each task has acceptance criteria, and the PM, dev and QA agents commented on them (for example #7, #8, #11) |
| Agent team | `docs/process.md` (how the agents work together), `docs/team/` (orchestrator, PM, dev, QA, on-call engineer) |
| Context management | `AGENTS.md` (imported by `.claude/CLAUDE.md`) points to modular docs: process, team, testing, design system, architecture, external services, observability |
| Application | React frontend (`frontend/`), FastAPI backend (`backend/`), PostgreSQL; one command: `docker compose up --build` |
| Testing | 1099 backend tests (`backend/tests/`, real PostgreSQL), 66 frontend tests (Vitest + React Testing Library, including screen tests in `frontend/src/test/`), 6 integration tests (`backend/integration/`, over HTTP against the Docker stack), browser end-to-end test (`e2e/`, Playwright); all with `make test-all` |
| Containerization | `Dockerfile` (frontend and backend in one image), `docker-compose.yaml` (app and PostgreSQL), one command |
| Deployment | AWS, made with CloudFormation (`deploy/cloudformation.yaml`): EC2, Docker Compose, Caddy (HTTPS), S3 for photos, ECR for images; live at the address above |
| CI/CD | `.github/workflows/ci-cd.yml`: tests on every push and pull request, then the build stage pushes the image to ECR (tag `YYYYMMDD-HHMMSS-shortsha`, plus `dev`). `.github/workflows/deploy-prod.yml`: manual "Deploy to prod" with a health check; rollback = the same workflow with an older tag (drill done, see below). AWS access through GitHub OIDC, no stored keys |
| Observability | OpenTelemetry (`backend/telemetry.py`): traces and HTTP metrics for every request, application metrics (`docs/observability.md`), structured JSON logs with `trace_id` and `span_id` (no email, password, title, note or search text; tested in `backend/tests/test_logs.py`). Collected in Grafana Cloud (Prometheus, Tempo, Loki) with the dashboard `observability/grafana/dashboards/artmneme-app.json`; the same stack runs locally with `make observability` |
| Alerting on user impact | Rule "Artwork creations are failing" (`observability/grafana/provisioning/alerting/artwork-creation-failures.json`): one server-side artwork creation failure in 15 minutes, with service, environment, version, owner, runbook and dashboard link. Uploaded to Grafana Cloud with `make grafana-cloud`; sends an email. Trigger on purpose: `make fault-on` and `make trigger-alert` |
| On-call agent | `make on-call` (`on-call-engineer/on_call.py`) polls the Grafana alerts every minute and starts Claude Code headless for each new alert, in its own git worktree at the alerting version, with the role `docs/team/on-call-engineer.md`. It may commit a fix on a branch `oncall/<time>`; it may not push or deploy |

## Drills on prod (2026-10-26)

**Alert drill:**
1. `make fault-on`, then `make trigger-alert`: two creations failed (HTTP 500).
2. The alert fired in Grafana Cloud for `prod` and the email arrived.
3. `make on-call` started the agent. In about 2 minutes it found the likely cause: the fault switch (from the git history, the timing and the 4 failures). It ran the tests (all passed) and correctly committed nothing, because the code had no bug.
4. `make fault-off`.

**Rollback drill:**
1. "Deploy to prod" with the previous tag `20261026-171541-455f748` (run 40388771867): deployed and healthy in about 1 minute, and Grafana showed the old version.
2. "Deploy to prod" without a tag (run 40389060803): back to `20261026-175010-5db5c27`, healthy.

## Decisions and limits

- **Environments:** prod is the AWS stack. Dev runs on the developer's computer; its telemetry goes to the same Grafana Cloud stack as `dev`. A dev environment on the server, deployed by CI, is prepared on the branch `dev-environment` but not yet released.
- **Community features** (sharing, discoverability) are postponed to a later version (`product-spec.md`).
- **The on-call agent** runs on the developer's computer while `make on-call` runs. This is the least costly version, chosen by the project owner.
- **AI use** is recorded in `docs/ai-usage-report.md`.
