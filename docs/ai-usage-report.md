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
