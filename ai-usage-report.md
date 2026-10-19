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

Recorded in:

```text
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

