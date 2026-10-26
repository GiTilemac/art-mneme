# ArtMneme

ArtMneme is a personal artwork collection and relationship exploration platform.

Users collect artworks they have encountered, enrich them with metadata, record observations, and explore relationships between artworks across their collection and watchlist. Community discovery comes in a later version.

---

# Philosophy

```text
Collection First
→ Exploration Second
→ Community Third
```

ArtMneme is intentionally designed as a collection and discovery tool rather than a social network.

Users own their collections.

Community features exist to support discovery, not social engagement.

---

# Core Features

## Collection Management

Users can:

```text
Create artworks

Edit artworks

Delete artworks

Upload artwork photos
```

Detail photos come in a later version.

---

## Watchlists

Users can maintain a list of artworks they would like to encounter in the future.

Artwork states:

```text
WATCHLIST

COLLECTION
```

When an artwork is encountered:

```text
WATCHLIST
→ COLLECTION
```

---

## Relationship Exploration

Users can explore artworks through:

```text
Same Artist

Same Subject

Same Movement

Same Museum

Shared Tags
```

Shared Tags and tag exploration come in a later version. Tag exploration supports progressive filtering:

```text
battle

battle + horse

battle + horse + armor
```

---

## Community Discovery

Not part of v1: it comes in a later version.

Community discovery is metadata-driven.

Visible:

```text
Title

Artist

Date

Subject

Movement

Museum

Tags
```

Optional:

```text
Shared Notes
```

Never visible:

```text
Artwork Photos

Detail Photos
```

Community discovery occurs exclusively through relationship exploration.

Global community search is intentionally excluded from v1.

---

# Documentation

## Product

```text
product-spec.md
```

Source of truth for product behavior.

---

## API

```text
openapi.yaml
```

Source of truth for API contracts.

---

## Database

```text
docs/database-schema.md
```

Source of truth for persistence design.

---

## Agent Instructions

```text
AGENTS.md
```

Instructions for AI-assisted development.

---

# Repository Structure

```text
.
├── product-spec.md
├── openapi.yaml
├── AGENTS.md
├── README.md
│
├── frontend/
├── backend/
│   └── tests/
│
├── .claude/
│   └── CLAUDE.md
│
└── docs/
    ├── database-schema.md
    ├── architecture.md
    ├── observability.md
    ├── design-system.md
    ├── testing-guidelines.md
    ├── process.md
    ├── tasks.md
    ├── task-template.md
    ├── ai-usage-report.md
    └── team/
        ├── pm.md
        └── dev.md
```

---

# Running the Backend

Run all commands from the `backend/` folder.

## Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 14 or newer, installed and running

Create the database user `artmneme` and its two databases, `artmneme` (development) and `artmneme_test` (tests only):

```bash
sudo -u postgres psql -c "CREATE ROLE artmneme LOGIN PASSWORD 'artmneme'"
sudo -u postgres createdb -O artmneme artmneme
sudo -u postgres createdb -O artmneme artmneme_test
```

If your PostgreSQL server does not listen on the default port 5432, add `-p <port>` to these commands.

The backend and the tests find these databases through two environment variables:

| Variable | Used by | Local value |
|----------|---------|-------------|
| `DATABASE_URL` | the backend and the schema command | `postgresql+psycopg://artmneme:artmneme@localhost:5432/artmneme` |
| `TEST_DATABASE_URL` | the tests | `postgresql+psycopg://artmneme:artmneme@localhost:5432/artmneme_test` |

The port in these values must match your local server (for example 5433). These are local development values only; no `.env` file is read.

## Photo storage

Photos are stored by `backend/photos.py`, in one of two places:

| Variable | Used by | Value |
|----------|---------|-------|
| `PHOTO_DIR` | the backend (development) | a folder, created if missing. Local value: `$PWD/photos` (ignored by git) |
| `S3_BUCKET` | the backend (production) | the name of the private AWS S3 bucket |

If `PHOTO_DIR` is set, photos are files in that folder and `S3_BUCKET` is not used. If it is not set, `S3_BUCKET` is needed; it is only checked when photo storage is first used. The AWS credentials and region come from the usual AWS environment (on the server: its AWS role, so no keys are stored). For local development:

```bash
export PHOTO_DIR=$PWD/photos
```

In production the bucket is created by `deploy/cloudformation.yaml`, with all public access blocked. The tests use a temporary folder and simulated S3 answers; they never contact AWS.

## Install

No variables needed.

```bash
uv sync
```

## Create the schema

Needs `DATABASE_URL`. Creates all tables and the seeded movements. Running it again does nothing.

```bash
export DATABASE_URL=postgresql+psycopg://artmneme:artmneme@localhost:5432/artmneme
uv run alembic upgrade head
```

## Start

Needs `DATABASE_URL` for endpoints that use the database; `GET /api/health` works without it.

```bash
uv run uvicorn main:app --port 8000
```

The API is served at `http://localhost:8000/api`, for example `http://localhost:8000/api/health`.

## Test

Needs `TEST_DATABASE_URL`. The tests empty the test database and rebuild it at every run, so it must never be the development database.

```bash
export TEST_DATABASE_URL=postgresql+psycopg://artmneme:artmneme@localhost:5432/artmneme_test
uv run pytest
```


## Docker

One image holds the backend and the built frontend. The backend serves the API at `/api` and the frontend at `/`.

```bash
docker build -t artmneme .
docker run -p 8000:8000 -e DATABASE_URL=... -e PHOTO_DIR=/photos artmneme
```

`DATABASE_URL` must reach the database from inside the container. Use `S3_BUCKET` instead of `PHOTO_DIR` in production. At start the container brings the database schema up to date.

To run the app together with its own PostgreSQL, use Docker Compose:

```bash
docker compose up --build
```

Then open http://localhost:8000. The database and the photos are kept in Docker volumes. `APP_PORT=8001 docker compose up --build` uses another port on your computer.

## Integration tests

`make integration` starts `docker-compose.yaml` with empty volumes on port 8092 and runs the tests in `backend/integration/` against it over HTTP. Afterwards it removes the containers and their volumes. It needs Docker; `make test` does not run these tests.

## End-to-end tests

`make e2e` does the same on port 8093, but drives a real browser (Chromium, through pytest-playwright) against the running stack: it registers a user, adds two artworks through the forms and explores relationships, then checks that everything is still there after a reload and in a new session. The tests are in `e2e/`. It needs Docker and Chromium (`cd backend && uv run playwright install chromium`).

## Deploy to AWS

One EC2 server runs `deploy/docker-compose.prod.yaml`: the app, PostgreSQL and Caddy, which gives HTTPS with a free Let's Encrypt certificate. `deploy/cloudformation.yaml` creates everything: the server with a fixed public address, an ECR repository for the image, the server's permissions, a firewall that opens only ports 80 and 443, a private S3 bucket for the photos, and a daily disk snapshot kept for 7 days. The cost is about $13 a month.

One-time steps:

1. Configure the AWS CLI (`aws configure`) for a user that may manage CloudFormation, EC2, IAM roles, ECR, SSM and Data Lifecycle Manager. On a personal account, the simplest choice is the `AdministratorAccess` policy. Set an AWS Budgets alarm, for example at $15 a month.
2. Store the database password in SSM Parameter Store (letters and digits only, because it is part of the database address):

```bash
aws ssm put-parameter --type SecureString --name /artmneme/postgres-password --value "$(openssl rand -hex 24)"
```

Then, from the repository root:

```bash
make deploy-stack   # create or update the AWS resources; prints the app address
make deploy         # build this version, push it and start it on the server
```

The app is at the `AppUrl` that `make deploy-stack` prints (`https://<address>.sslip.io`). To open a shell on the server, use `aws ssm start-session --target <InstanceId>`; no SSH key is needed.

### Deploy a new version

Run these steps from the repository root, in a terminal where `aws sts get-caller-identity` shows the ArtMneme account (for example after `export AWS_PROFILE=artmneme-deploy`).

1. Run the tests: `make test`, `make integration` and `make e2e`. All must pass.
2. Commit the changes. The image is named after the commit (for example `7ab31e2`); uncommitted changes give a name that ends in `-dirty`, so you cannot tell later what runs.
3. If the version changes the database (a new file in `backend/migrations/versions/`), take a snapshot of the server disk first. The app updates the database schema when it starts, and a rollback does not undo that.
4. Run `make deploy`. It builds the image, uploads it, copies `deploy/docker-compose.prod.yaml` and `deploy/Caddyfile` to the server and restarts the changed containers. The app is unavailable for a few seconds. At the end it prints `Deployed <commit> to <address>`.
5. Check the result: `curl https://<address>/api/health` gives `{"status":"ok"}`. Then sign in in a browser and open an artwork.
6. Push the commit to GitHub, so the repository shows what runs.

If the new version does not work, go back to the previous one:

1. Run `git checkout <previous commit>`, then `make deploy`. ECR keeps the last 5 images, but `make deploy` builds the image again from that commit.
2. Run `git checkout main` again.
3. If the new version changed the database, restore the snapshot from step 3 instead (create a volume from it and attach it in place of the server's disk), or ask for help first.

Changes to `deploy/cloudformation.yaml` are deployed with `make deploy-stack`, not `make deploy`. Be careful: the template asks for the latest Amazon Linux image, so after Amazon publishes a new one, `make deploy-stack` replaces the server, and the database on its disk starts empty. A change to `UserData` stops and starts the server, and the start script does not run again. Take a disk snapshot before every `make deploy-stack` on a running stack.

---

# Technology Goals

The project is designed to satisfy the requirements of the AI Dev Tools Zoomcamp.

These include:

```text
Frontend

Backend

Database

OpenAPI

Unit Tests

Frontend Tests

Integration Tests

Containerization

CI/CD

Deployment

Observability

Alerting

Responder Agent
```

---

# Technology Stack

```text
Backend:   Python + FastAPI

Frontend:  React + TypeScript

Database:  PostgreSQL
```

See `docs/architecture.md` for rationale.

---

# Observability

ArtMneme monitors real user impact.

Example metrics:

```text
Active Users

Artworks Created

Relationship Explorations

Watchlist Conversions
```

Primary alert:

```text
Artwork Creation Failure Rate
```

---

# Non-Goals

ArtMneme v1 intentionally excludes:

```text
Artwork Recognition

OCR

AI Recommendations

Public Image Sharing

Collaborative Editing

Following Users

Comments

Likes

Global Community Search

Graph Visualization
```

---

# License

Copyright © Tilemachos Doganis.

All rights reserved unless explicitly stated otherwise.