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
| `R2_ACCOUNT_ID` | the backend (production) | the Cloudflare account id |
| `R2_BUCKET` | the backend (production) | the name of the private R2 bucket |
| `R2_ACCESS_KEY_ID` | the backend (production) | the API token's access key id |
| `R2_SECRET_ACCESS_KEY` | the backend (production) | the API token's secret |

If `PHOTO_DIR` is set, photos are files in that folder and the R2 variables are not used. If it is not set, all four R2 variables are needed. They are only checked when photo storage is first used. For local development:

```bash
export PHOTO_DIR=$PWD/photos
```

The R2 account, the bucket and its API token are created by the project owner, not by the developer. The bucket must keep public access turned off (no `r2.dev` address, no custom domain), and its API token needs only object read and write rights on that one bucket. Never commit these values. The tests use a temporary folder and simulated R2 answers; they never contact R2.

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