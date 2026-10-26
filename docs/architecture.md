# ArtMneme Architecture

## Purpose

This document describes the high-level architecture of ArtMneme.

It defines the responsibilities of each layer and the interactions between them.

The architecture prioritizes:

- simplicity
- maintainability
- testability
- API-first development
- future observability support

---

# Architectural Principles

## Collection First

The primary purpose of ArtMneme is managing a personal artwork collection.

All architectural decisions should prioritize:

```text
Collection
```

before:

```text
Exploration
```

and:

```text
Community Discovery
```

---

## OpenAPI First

The API contract is defined before implementation.

The OpenAPI specification acts as the contract between:

```text
Frontend
Backend
```

The implementation must remain synchronized with:

```text
openapi.yaml
```

---

## Explicit Relationships

Relationship exploration is one of the core differentiators of the application.

Relationship logic must remain visible and explicit.

Avoid:

```text
Recommendations

AI scoring

Implicit ranking
```

Prefer:

```text
Same Artist

Same Subject

Same Movement

Same Museum

Shared Tags
```

Shared Tags comes in a later version.

---

## Metadata-First Community Layer

Not part of v1: community, including discoverability, comes in a later version. In v1 artworks stay private and exploration shows only the user's own artworks.

Community discovery is based on metadata.

Public image sharing is intentionally excluded from v1.

---

# High-Level System Architecture

```text
Browser
    ↓
Frontend Application
    ↓
REST API
    ↓
Backend Application
    ↓
PostgreSQL Database
```

---

# Technology Stack

## Decision

```text
Backend:   Python + FastAPI

Frontend:  React + TypeScript

Database:  PostgreSQL
```

Decided by the project owner.

---

## Rationale

Python was chosen for readability.

The project owner reviews all AI-generated code and must be able to read the business rules directly.

FastAPI was chosen because:

```text
OpenAPI support is built in

Request validation is built in

Interactive API documentation is generated automatically
```

The interactive documentation allows business rules to be checked without writing code.

Python also aligns with the Responder Agent work in Module 4.

---

## Alternatives Considered

```text
TypeScript backend (Fastify / NestJS)

Django + Django REST Framework

Next.js full-stack

Supabase (Backend-as-a-Service)
```

Next.js and Supabase were rejected because they weaken the separation between Frontend, REST API and Backend.

---

## Photo Storage

```text
Cloudflare R2, used from day one.
```

Production keeps photos in a private R2 bucket. Development and tests use a local folder chosen by `PHOTO_DIR`.

---

## Authentication Mechanism

```text
Cookie sessions.

Session lifetime: 30 days, renewed on each use.
```

---

## Deployment Shape

```text
One container.

Frontend:  served at /

API:       served at /api
```

---

## Test Tools

```text
Backend:   pytest

Frontend:  Vitest + React Testing Library
```

---

## UI Library

```text
MUI
```

See `docs/design-system.md`.

---

## Continuous Integration

```text
GitHub Actions
```

---

# Frontend Layer

## Responsibilities

The frontend is responsible for:

```text
Authentication

Artwork Management

Watchlist Management

Search

Filtering

Relationship Exploration

Discoverability Controls
```

---

## Screens

Planned screens:

```text
Login

Register

Collection

Artwork

Watchlist

Search Results
```

---

## Collection View

Default:

```text
Grid View
```

Alternative:

```text
List View
```

---

## Artwork Page

Displays:

```text
Main Artwork Photo

Title
Artist
Date

Subject
Movement
Museum

Tags

Notes

Detail Photos
```

Actions:

```text
Replace Artwork Photo

View Detail Photos

Add Detail Photo

Delete Detail Photo

Edit Metadata

Edit Notes

Explore Relationships
```

Detail Photos and their actions come in a later version.

---

# Backend Layer

## Responsibilities

The backend owns all business logic.

---

## Authentication

Responsible for:

```text
User Registration

User Login

Session Validation

Authorization
```

---

## Artwork Lifecycle

Responsible for:

```text
WATCHLIST

COLLECTION
```

state transitions.

---

## Duplicate Detection

Not part of v1.

Responsible for evaluating:

```text
Title
Artist
Date
```

similarity and returning warnings.

Duplicate creation must remain allowed.

---

## Relationship Exploration

Responsible for querying relationship matches using:

```text
Artist
Subject
Movement
Museum
Tags
```

---

## Discoverability

Not part of v1.

Responsible for enforcing:

```text
Title present

Artist present

Date present
```

before discoverability can be enabled.

---

## Privacy Enforcement

Responsible for ensuring:

```text
Artwork photos remain private

Detail photos remain private

Private notes remain private
```

---

# API Layer

The API exposes all functionality through REST endpoints.

The API contract is defined in:

```text
openapi.yaml
```

---

## Major API Areas

```text
Authentication

Artworks

Photos

Watchlist

Discoverability

Relationship Exploration

Search

Metadata Entities
```

---

# Database Layer

The database stores:

```text
Users

Artworks

Artists

Movements

Subjects

Tags

ArtworkTags

DetailPhotos
```

Schema details are defined in:

```text
docs/database-schema.md
```

---

# Ownership Model

## User-Owned Resources

Users own:

```text
Artworks

Artwork Photos

Detail Photos

Notes
```

---

## Community-Owned Resources

Platform-wide entities:

```text
Artists

Movements

Subjects

Tags
```

These entities are shared, reusable and immutable in v1.

---

# Community Discovery

Not part of v1.

Community participation occurs through discoverable metadata.

Visible:

```text
Title
Artist
Date

Subject
Movement
Museum
Tags

Shared Notes
```

Never visible:

```text
Artwork Photos

Detail Photos
```

---

# Request Flow Examples

## Create Artwork

```text
Frontend
    ↓
POST /artworks
    ↓
Backend Validation
    ↓
Database Write
    ↓
API Response
    ↓
Frontend Update
```

---

## Explore Relationships

```text
Artwork Page
    ↓
Relationship Selection
    ↓
API Request
    ↓
Relationship Query
    ↓
Result Set
    ↓
Display Results
```

---

## Enable Discoverability

Not part of v1.

```text
Artwork
    ↓
Discoverability Request
    ↓
Validation
    ↓
Database Update
    ↓
Response
```

---

# Testing Strategy

The architecture supports:

```text
Unit Tests

Frontend Tests

Integration Tests
```

Testing must validate:

```text
Business Rules

API Contracts

Relationship Queries

Discoverability Rules
```

Testing rules are defined in:

```text
docs/testing-guidelines.md
```

---

# Deployment Architecture

Module 3 introduces deployment.

Target structure:

```text
Frontend
    ↓
Backend API
    ↓
PostgreSQL
```

Containerized using Docker.

---

# Observability Integration

Module 4 introduces observability.

Planned telemetry flow:

```text
Application
    ↓
OpenTelemetry
    ↓
Collector
    ↓
Prometheus

Loki

Tempo
    ↓
Grafana
```

---

# Responder Agent Integration

The responder agent operates after alert creation.

Inputs:

```text
Metrics

Logs

Traces

Deployment Version
```

Outputs:

```text
Investigation Summary

Root Cause Hypothesis

Recommended Remediation
```

Agent actions remain advisory only.

---

# Explicit Non-Goals

The architecture intentionally excludes:

```text
Image Sharing

Community Galleries

Social Features

Comments

Likes

Following

Global Community Search

Collaborative Editing

AI Recommendations

Artwork Recognition

Graph Visualization
```

---

# Future Architectural Extensions

Potential V2 additions:

```text
Artist Aliases

Movement Aliases

Subject Aliases

Community Search

User Following

Image Sharing

Graph Exploration
```

These features should not influence v1 implementation.