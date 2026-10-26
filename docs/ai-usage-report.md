# AI Usage Report

## Project

ArtMneme

Personal artwork collection and relationship exploration platform.

---

# Purpose

This document records the use of AI tools throughout the design and development of ArtMneme.

The goals are:

- transparency
- accountability
- reproducibility
- clear separation between AI assistance and human decision-making

---

# Development Approach

ArtMneme uses an AI-assisted development workflow.

AI tools are used as:

```text
Design Assistants

Implementation Assistants

Architecture Assistants

Documentation Assistants
```

AI does not act autonomously.

All final decisions remain the responsibility of the project owner.

---

# AI Tools Used

## Microsoft 365 Copilot (GPT-5)

Primary AI assistant.

Used extensively for:

```text
Product Design

Requirements Engineering

Database Design

API Design

Architecture Design

Observability Design

Documentation Generation
```

---

## Additional AI Tools

This section should be updated as development progresses.

Examples:

```text
GitHub Copilot

Claude

Cursor

ChatGPT
```

---

## Claude Code (Claude Opus 5.5)

Used for:

```text
Specification Consistency Review

Technology Stack Options Analysis
```

Technology stack:

- Claude proposed four options and explained the tradeoffs of each.
- The project owner selected Python + FastAPI.

Architecture choices:

- Claude explained the options for photo storage, login and deployment shape.
- The project owner chose Cloudflare R2 from day one, cookie sessions and one container.

Decision recorded in:

```text
docs/architecture.md
```

Backlog:

- At the project owner's request, Claude drafted a task backlog from the existing documents.
- Claude listed the open questions the backlog depended on and explained the options for each.
- The project owner decided test tools, CI, seeded movements, password and session rules, duplicate matching, date entry and storage, tag hiding, photo handling and the alert rule.
- Claude explained the tradeoffs of using Lovable for the frontend, of doing CI and deployment early or late, and of ways to bring the Lovable repo into this one.
- The project owner decided the backlog covers backend development only, imported the Lovable frontend into `frontend/` with git subtree, and kept operations and observability work outside the backlog.

Recorded in:

```text
docs/tasks.md
```

Agent rules:

- The project owner set a rule that AI agents must stop and ask before deleting important data, force-pushing, modifying external systems, performing destructive operations, or making a decision that requires the owner's approval.
- At the project owner's request, Claude added the rule to `AGENTS.md`.

Recorded in:

```text
AGENTS.md
```

Photos and collection state:

- The project owner asked how keeping photos on their own device would change the plan, including a later Android version.
- Claude explained the ways to store photos locally, how Android affects each, and which documents and tasks depend on the photo rules.
- The project owner decided: a COLLECTION artwork needs a photo; new artworks default to COLLECTION; a collection artwork can never move back to WATCHLIST (the user creates a new watchlist artwork instead); the main photo cannot be removed without a replacement; when a watchlist artwork with a photo is collected, that photo is deleted.
- The project owner decided on a future feature: the device where a photo was added remembers the original, other devices show the uploaded compressed copy, and an account-wide setting can turn uploading off. In v1 every photo is uploaded.
- At the project owner's request, Claude updated the documents and backlog to match.

Recorded in:

```text
product-spec.md
docs/database-schema.md
docs/tasks.md
```

Frontend photo rules:

- At the project owner's request, Claude changed the Lovable frontend in `frontend/` to follow the new photo rules: the artwork state is stored instead of derived from the photo, new artworks choose Collection (default) or Watchlist, and collecting a watchlist artwork replaces its old photo.
- Claude added tests for the rule that a collection artwork needs a photo.

Recorded in:

```text
frontend/src
```

API contract:

- At the project owner's request, Claude read the frontend's API client and proposed the endpoints the backend needs, explaining the choices in plain terms.
- The project owner decided: extend the existing `openapi.yaml` and keep its auth paths; define every endpoint now, so backlog tasks implement them; search with pages for artists, movements and subjects; the duplicate check runs before saving only; discoverability has its own endpoints; usage metrics are recorded by the backend; creating an existing name returns the existing entry; an artwork is created with its photo in one request; photos are served through the backend in v1 (loaded from the device in the future local-photos feature); exploration is one endpoint with a `by` option.
- Claude wrote the full contract in `openapi.yaml` and updated the backlog wording to match.

Recorded in:

```text
openapi.yaml
docs/tasks.md
```

Frontend services layer:

- At the project owner's request, Claude checked whether the frontend kept every backend call in one services layer with a mock behind it. All calls were in one file, but that file was itself the mock, it had no tests, and it no longer matched `openapi.yaml`.
- The project owner decided to reshape the layer to match `openapi.yaml` and approved `fake-indexeddb` as a test-only dependency.
- Claude split the layer into `frontend/src/services/` (the list of actions, the browser mock, and the switch between them), updated the screens to use it, and added 30 tests for the mock.

Recorded in:

```text
frontend/src/services
frontend/package.json
```

Empty backend (backlog task 1, GitHub issue #1):

- The project owner groomed the task and approved its acceptance criteria, including the dependencies (`fastapi`, `uvicorn`, and `pytest` and `httpx` for tests) and keeping FastAPI's documentation pages under `/api`.
- Claude added `GET /health` to `openapi.yaml`, set up the Python 3.13 project in `backend/` with `uv`, wrote the FastAPI application with `GET /api/health` and 5 tests, and added the backend's install, start and test commands to `README.md`.
- Claude checked the behaviour by running the tests and by starting the server and calling it with `curl`.

Recorded in:

```text
openapi.yaml
backend/
README.md
docs/tasks.md
```

Database schema and seed data (backlog task 2, GitHub issue #2):

- The project owner groomed the task and approved its acceptance criteria, including the dependencies (`sqlalchemy`, `alembic`, `psycopg[binary]`), the rules the database enforces, and the change to "Zero or One Artwork Photo" in `product-spec.md`.
- Claude wrote the backend's database connection module, one Alembic migration that creates the v1 schema and seeds the 16 movements (`uv run alembic upgrade head`), and tests that run against a separate test database; added the PostgreSQL set-up, the environment variables and the schema command to `README.md`; and recorded the decided rules in `docs/database-schema.md`.
- Claude checked the behaviour by running the full test suite against the local test database (105 passed, also when run in reverse order and file by file), running the schema command twice against the development database (16 movements, the second run changed nothing), starting the backend without `DATABASE_URL`, and checking that the schema command and the tests stop with a message naming the missing variable. The first test run found a bug in a test helper, which Claude fixed.
- QA found that the tests did not notice when `DATABASE_URL` named the test database with another host spelling (`127.0.0.1` instead of `localhost`). Claude changed the check to compare what the server reports about the two databases, added tests for it, and the suite then passed with 108 tests.

Recorded in:

```text
backend/
README.md
docs/database-schema.md
product-spec.md
```

Registration, login and logout (backlog task 3, GitHub issue #3):

- The project owner groomed the task and approved its acceptance criteria, including the `openapi.yaml` changes (a `422` on `/auth/login`, the cookie renewed on every logged-in response), sessions kept in a database table, and `argon2-cffi` for password hashing.
- Claude made the approved `openapi.yaml` changes, added the `Session` section to `docs/database-schema.md`, and wrote the `sessions` migration, the four `/api/auth` endpoints, one login check that later endpoints reuse, and one handler that answers every request validation error in the `Error` shape.
- Claude wrote tests for every acceptance criterion: register, login, logout and `/auth/me`; the cookie's flags and 30 days; renewal and expiry (by setting `expires_at` directly); two devices; email and password rules; password hashes; and the `sessions` table and migration.
- Claude ran the full test suite against the local test database. The first run found that the new migration test read the `sessions` table before the migration had created it; Claude fixed the test, and the suite then passed with 180 tests.
- QA found that a JSON body that is not valid UTF-8 was answered `400` with FastAPI's own message instead of `422` in the `Error` shape. Claude added a test that reproduced it, made the whole app answer such a body `422` with one sentence, and the suite then passed with 182 tests.

Recorded in:

```text
backend/
openapi.yaml
docs/database-schema.md
```

Artist, movement and subject API (backlog task 4, GitHub issue #4):

- The project owner groomed the task and approved its acceptance criteria, including the two `openapi.yaml` changes (`maxLength: 200` on `NewEntity`, the `EntityExisting` description), how names are cleaned and compared, the three error messages, and the order and paging of search results.
- Claude made the approved `openapi.yaml` changes and wrote one implementation of `GET` and `POST` shared by `/api/artists`, `/api/movements` and `/api/subjects`, with one function that cleans names and search text (ends trimmed, inner spaces reduced to one, Unicode NFC), reusing the login check and error handlers from #3.
- Claude wrote tests for every acceptance criterion, each shared rule on all three lists, including two threads that create the same new name at the same moment, and ran the full test suite against the local test database: 448 passed.
- Claude found two cases the acceptance criteria do not cover that answer `500`: a name containing a lone UTF-16 surrogate (such as `"\ud800"` in the JSON body), and a NUL character in the search text `q`. They were reported on the issue for the project owner to decide, not changed.
- The project owner then decided both cases, and that the rarer characters `str.split()` treats as whitespace stay spaces. Claude first wrote tests that reproduced the two `500`s, then refused control characters in `q`, and lone surrogates in names and `q`, with the same `422` message, and added tests documenting the rarer whitespace. The suite then passed with 503 tests.

Recorded in:

```text
backend/
openapi.yaml
```

Tag API with validation and suggestions (backlog task 5, GitHub issue #5):

- The project owner groomed the task and decided every rule in its acceptance criteria, including that a tag's popularity is the number of different users who have it, the tag rules and error messages, and the wording of the changes to `product-spec.md`, `docs/database-schema.md`, `docs/tasks.md` and `openapi.yaml`.
- Claude made those approved document and contract changes first, each in its own commit, keeping the line endings of each file.
- Claude wrote migration `0003`, a PL/pgSQL trigger on `artwork_tags` that locks the tag row and keeps `usage_count` equal to the number of different users, with a backfill for existing links, and `POST /api/tags` and `GET /api/tags/suggestions` in `backend/main.py`, reusing the login check and `cleaned()`.
- Claude wrote tests for every acceptance criterion, including two threads creating the same tag and two threads linking the same tag, and ran the full test suite against the local test database.

Recorded in:

```text
backend/
```

Private photo storage (backlog task 6, GitHub issue #6):

- The project owner groomed the task and decided, on 2026-10-25: photos are kept in a local folder chosen by `PHOTO_DIR` in development and tests and in a private Cloudflare R2 bucket in production; the stored path is a flat 32-character hexadecimal name plus `.jpg`; the 10 MB limit and the two refusal messages; a 10-second timeout and a `503` answer with its message when R2 cannot be reached; R2 is tested with botocore's `Stubber`; the `StorageUnavailable` response in `openapi.yaml`; `boto3` as a dependency; and that photos are served through the backend in v1.
- Claude made the approved `openapi.yaml` change first, in its own commit, keeping the line endings, and added `boto3` with `uv add`.
- Claude wrote `backend/photos.py` (save, read and delete, with the local folder and R2 behind them) and the `503` handler in `backend/main.py`, and the README, `.gitignore` and `docs/architecture.md` lines.
- Claude wrote tests for every acceptance criterion against a temporary folder and simulated R2 answers (no network), and ran the full test suite against the local test database.

Recorded in:

```text
backend/
openapi.yaml
README.md
```

Create artwork API (backlog task 7, GitHub issue #7):

- The project owner groomed the task and decided, on 2026-10-25: the text limits (title 300, museum 200, notes 10,000 characters); a BC choice for each year (`from_bc`, `to_bc`) and the year limits (an AD year not later than the current year, a BC year up to 100,000); `photo_version` and the `?v=` parameter of the photo request; the cleaning of title, museum and notes; `422` (not `404`) for an id that does not exist; the order of checks, photo before database and the photo deleted again when the database step fails; `python-multipart` as a dependency; and the `product-spec.md` Date Entry wording.
- Claude made the approved `openapi.yaml` and `product-spec.md` changes first, each in its own commit, keeping the line endings, and added `python-multipart` with `uv add`.
- Claude wrote `POST /api/artworks` in `backend/main.py` (reusing the login check, the `Error`-shaped `422` handler, the cleaning and control-character check of #4, the tag trigger of #5 and `backend/photos.py` of #6), with the date display function and the shared `Artwork` builder (with `photo_version`) for later tasks. In `backend/photos.py` the JPEG and size check became its own function, `check`, so it runs before anything is stored.
- Claude wrote tests for the acceptance criteria (rare characters tested once, in a shared place) and ran the full test suite against the local test database.

Recorded in:

```text
backend/
openapi.yaml
product-spec.md
```

View, edit and delete own artwork API (backlog task 8, GitHub issue #8):

- The project owner groomed the task and decided, on 2026-10-25: `404` "Artwork not found." for odd ids (`0`, `-1`, `abc`, `1.5`, `99999999999`) on all three operations, without an `openapi.yaml` change; that a discoverable artwork may not lose its title, artist or date; the delete order (database rows first in one open transaction, stored files deleted through the #6 module, commit only when every file is gone, `503` and nothing deleted when storage is unreachable, a repeated delete finishing the job); and the `product-spec.md` change adding Delete Artwork to the Artwork Page actions.
- Claude made the approved `product-spec.md` change first, in its own commit, and wrote `GET`, `PATCH` and `DELETE /api/artworks/{artwork_id}` in `backend/main.py`, reusing the login check, the text cleaning and control-character check of #4, the date check, the shared `Artwork` builder of #7 and the photo module of #6.
- Claude wrote tests for the acceptance criteria. On 2026-10-26, before committing them, Claude ran the full suite, found 32 failures caused by mistakes in the tests (not in the endpoint code), fixed them, and confirmed the full suite passes (920 tests).

Recorded in:

```text
backend/
product-spec.md
```

Artwork photo upload and replace (backlog task 10, GitHub issue #12):

- The project owner groomed the task and decided, on 2026-10-25: the replace order (new photo saved first, then the row, then the old file deleted), an upload that still succeeds when the old file cannot be deleted, `404` "Photo not found." for an artwork without a photo, "Choose a photo to upload." when no photo file is sent, reading the whole photo before answering so a storage failure gives a clean `503`, and the caching rule (`immutable` only with the current `?v=`, otherwise `no-store`).
- Claude wrote `PUT` and `GET /api/artworks/{artwork_id}/photo` in `backend/main.py`, reusing the ownership check of #8, the photo module of #6 and the `Artwork` builder of #7, and wrote one test per rule in `backend/tests/test_artwork_photo.py`. The full suite passes (968 tests).

Recorded in:

```text
backend/
```

Artwork list API (backlog task 12, GitHub issue #14):

- The project owner groomed the task and decided, on 2026-10-25: the `422` on `GET /artworks` in `openapi.yaml`, "Choose Collection or Watchlist." for a missing or wrong state, artworks created at the same moment ordered highest id first, search and filter parameters ignored until task 13, no new index, and `photo_version` on the `Artwork`.
- Claude made the approved `openapi.yaml` change first, in its own commit, and wrote `GET /api/artworks` in `backend/main.py`. The shared `Artwork` builder now builds many artworks with three queries, so a page of 50 costs no more queries than a page of 5; the single-artwork version uses it too. Claude wrote one test per rule in `backend/tests/test_artwork_list.py`. The full suite passes (996 tests).

Recorded in:

```text
backend/
openapi.yaml
```

Search and filter API (backlog task 13, GitHub issue #15):

- The project owner groomed the task and decided, on 2026-10-25: the date filter as a year plus a BC box (`from_bc`, `to_bc` in `openapi.yaml`), partial search where every word must be found, search only within the requested state, museum matched ignoring capitals and extra spaces, all tags required, an unknown id giving an empty page, the messages "Filter values are not valid." and "Search must be at most 200 characters.", search and filters combined with AND, and no new index or extension.
- Claude made the approved `openapi.yaml` change first, in its own commit, and added search and filters to `GET /api/artworks` in `backend/main.py`, inside the same database query as the owner and state conditions. It reuses the text check of #4/#7 and the date check of #7; the `%`/`_`/`\` escaping of #4 became a small shared function. The endpoint now reads `page` itself so the checks run in the decided order (login, state, page, filters). Claude wrote one test per rule in `backend/tests/test_artwork_search.py` and removed the #14 test that expected filters to be ignored. The full suite passes (1045 tests).

Recorded in:

```text
backend/
openapi.yaml
```

Relationship exploration API (backlog task 15, GitHub issue #19):

- The project owner groomed the task and decided, on 2026-10-25: at most 50 artworks per source, newest first (highest id first on ties), added to `openapi.yaml`; two empty lists when the starting artwork has no value for the chosen field or both sources are off; the starting artwork never in its own results; `by=tags` refused with "Exploring by tags is not available yet."; museum matched ignoring capitals and extra spaces. On 2026-10-26 the owner postponed community results and shared-tags exploration, so this task covers only the user's own artworks.
- Claude made the approved `openapi.yaml` change first, in its own commit, and wrote `GET /api/artworks/{artwork_id}/related` in `backend/main.py`, reusing the ownership check of #8 and the `Artwork` builder of #14. Claude wrote one test per rule in `backend/tests/test_related.py`. The full suite passes (1073 tests).

Recorded in:

```text
backend/
openapi.yaml
```

Frontend brief for Lovable (GitHub issue #11, 2026-10-26):

- The project owner decided on 2026-10-26 that the frontend keeps its 30 MB check on the original photo, and that #11 is done in Lovable from a brief that stands on its own, because Lovable may not see the rest of the repository.
- Claude rewrote GitHub issue #11 as that brief: how the frontend talks to the backend, every endpoint it uses with its data and messages, the screens to connect, and what stays hidden in v1.

Community postponed to a later version (backlog rework, 2026-10-26):

- To save credits, the project owner asked which backlog work could wait. Claude recommended postponing community; the project owner decided on 2026-10-26 to postpone community, including discoverability, to keep the database columns, the two `Artwork` fields (always false in v1) and the finished #8 code as they are, and to hide the frontend controls as part of #11.
- Claude removed the discoverability endpoints and the community parts of the exploration endpoint from `openapi.yaml`, marked the community sections of `product-spec.md`, `docs/database-schema.md`, `docs/architecture.md`, `docs/observability.md` and `README.md` as not part of v1, and moved task 14 and community exploration to a Later version section in `docs/tasks.md`.
- Claude updated GitHub issues #18 (postponed), #19 (own artworks only) and #11 (hide the controls).

Recorded in:

```text
openapi.yaml
product-spec.md
docs/
README.md
```

Duplicate warnings, detail photos and shared-tags exploration postponed (backlog rework, 2026-10-26):

- The project owner decided on 2026-10-26 to postpone every whole issue Claude had listed as postponable: #9 duplicate warning, #13 detail photos and task 16 shared-tags exploration, and to keep #15 search and filter whole. Built parts (the `detail_photos` table, `Artwork.detail_photo_ids`, the #8 delete of detail photos) stay as they are.
- Claude removed the duplicate-check and detail-photo endpoints and `by=tags`/`tag_ids` from `openapi.yaml`, marked those parts of `product-spec.md`, `docs/database-schema.md`, `docs/architecture.md`, `docs/observability.md` and `README.md` as not part of v1, and moved tasks 9, 11 and 16 to the Later version section of `docs/tasks.md`.
- Claude updated GitHub issues #9 and #13 (postponed), #19 (no shared tags), #11 (hide the duplicate warning and detail photos) and #14 (a note about the removed detail-photo operations).

Recorded in:

```text
openapi.yaml
product-spec.md
docs/
README.md
```

---

# AI Contributions

## Product Design

AI assisted with:

```text
Problem Definition

Product Scope

User Workflows

Community Model

Watchlist Model

Relationship Exploration Design

Discoverability Design

Non-Goals Definition
```

Primary artifact:

```text
product-spec.md
```

---

## Requirements Engineering

AI assisted with:

```text
Acceptance Criteria

Feature Refinement

Constraint Identification

Edge Case Analysis
```

Outputs incorporated into:

```text
product-spec.md
```

---

## Domain Modeling

AI assisted with:

```text
Artwork Model

Artist Model

Movement Model

Subject Model

Tag Model

Discoverability Rules
```

Final decisions remained human-owned.

---

## Database Design

AI assisted with:

```text
Entity Discovery

Relationship Mapping

Ownership Rules

Schema Refinement

Indexing Recommendations
```

Primary artifact:

```text
docs/database-schema.md
```

---

## API Design

AI assisted with:

```text
REST Resource Design

Endpoint Modeling

Contract Design

OpenAPI Specification Generation
```

Primary artifact:

```text
openapi.yaml
```

---

## Architecture Design

AI assisted with:

```text
System Architecture

Frontend / Backend Separation

OpenAPI-First Workflow

Deployment Preparation

Observability Planning
```

Primary artifact:

```text
docs/architecture.md
```

---

## Observability Design

AI assisted with:

```text
Metrics Selection

Alert Design

Responder-Agent Planning

Telemetry Strategy
```

Primary artifact:

```text
docs/observability.md
```

---

## Documentation

AI assisted with creation of:

```text
README.md

AGENTS.md

database-schema.md

architecture.md

observability.md

ai-usage-report.md
```

---

# Human Responsibilities

The project owner remains responsible for all final outcomes.

---

## Product Decisions

The project owner selected:

```text
Feature Set

Scope

Acceptance Criteria

Roadmap
```

---

## Technical Decisions

The project owner remains responsible for:

```text
Technology Stack

Dependencies

Security Decisions

Infrastructure Decisions
```

---

## Validation

The project owner must validate:

```text
Correctness

Performance

Security

Compliance
```

of all generated artifacts.

---

## Code Review

All AI-generated code must be:

```text
Reviewed

Verified

Modified when necessary
```

before inclusion in the project.

---

## Testing

The project owner remains responsible for:

```text
Unit Tests

Frontend Tests

Integration Tests

Acceptance Testing
```

regardless of AI assistance.

---

# Development Timeline

## Phase 1 — Product Definition

AI assisted with:

```text
Project Ideation

Problem Analysis

Requirements Discovery

Workflow Design
```

Artifacts:

```text
product-spec.md
```

---

## Phase 2 — Domain Design

AI assisted with:

```text
Entity Modeling

Ownership Modeling

Discoverability Rules

Community Rules
```

Artifacts:

```text
product-spec.md
docs/database-schema.md
```

---

## Phase 3 — Database Design

AI assisted with:

```text
Schema Design

Relationship Mapping

Constraint Identification

Index Planning
```

Artifacts:

```text
docs/database-schema.md
```

---

## Phase 4 — API Design

AI assisted with:

```text
REST Design

Endpoint Design

OpenAPI Generation
```

Artifacts:

```text
openapi.yaml
```

---

## Phase 5 — Architecture Design

AI assisted with:

```text
Architecture Planning

Component Responsibilities

Deployment Preparation
```

Artifacts:

```text
docs/architecture.md
```

---

## Phase 6 — Observability Planning

AI assisted with:

```text
Metrics Strategy

```
