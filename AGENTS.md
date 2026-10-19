# AGENTS.md

# ArtMneme

Personal artwork collection and relationship exploration platform.

---

# Purpose

This document provides context and implementation guidance for AI coding agents working on ArtMneme.

Agents should use this file together with:

```text
product-spec.md

openapi.yaml

docs/database-schema.md

docs/architecture.md
```

Product requirements always take precedence over implementation convenience.

---

# Product Philosophy

```text
Collection First
→ Exploration Second
→ Community Third
```

ArtMneme is:

```text
Personal Collection App

Relationship Exploration Tool

Metadata Discovery Platform
```

ArtMneme is NOT:

```text
Social Network

Image Sharing Platform

Art Encyclopedia

AI Product
```

When uncertain, prioritize:

```text
Collection Features
```

over:

```text
Community Features
```

---

# Source of Truth

Priority order:

```text
1. product-spec.md

2. openapi.yaml

3. database-schema.md

4. architecture.md
```

Business requirements always override implementation assumptions.

---

# Decision Authority

AI tools may recommend but never decide.

Proposals are discussed in chat only.

Project files contain only what the project owner has explicitly decided.

A stated priority or preference is not a decision.

---

# Technology Stack

```text
Backend:   Python + FastAPI

Frontend:  React + TypeScript

Database:  PostgreSQL
```

Details and rationale:

```text
docs/architecture.md → Technology Stack
```

Do not introduce a different language or framework without the project owner's approval.

```text
Photo Storage:   Cloudflare R2, from day one.

Authentication:  Cookie sessions.

Deployment:      One container. Frontend at /, API at /api.
```

---

# Core Domain Model

Primary entities:

```text
User

Artwork

Artist

Movement

Subject

Tag

ArtworkTag

DetailPhoto
```

---

# Artwork

Artwork is the central domain entity.

Use a single Artwork model.

Do NOT create a separate watchlist entity.

Artwork state:

```text
WATCHLIST

COLLECTION
```

Workflow:

```text
WATCHLIST
→ upload artwork photo
→ COLLECTION
```

---

# Artwork Identity

Identity fields:

```text
Title

Artist

Date
```

Metadata fields:

```text
Subject

Movement

Museum

Tags

Notes

Photos
```

Identity fields drive duplicate detection.

Duplicate detection:

```text
Title + Artist + Date
```

Must produce warnings only.

Do not enforce uniqueness.

---

# Photos

## Artwork Photo

Rules:

```text
Exactly one artwork photo.
```

The artwork photo:

```text
May be replaced.

Never shared publicly.

Never discoverable.
```

Do not create support for multiple artwork photos in v1.

---

## Detail Photos

Rules:

```text
Zero or more detail photos.
```

Detail photos are:

```text
Private

Never discoverable

Never shared
```

---

# Community Metadata

Community-wide entities:

```text
Artist

Movement

Subject

Tag
```

Users may:

```text
Create

Reuse
```

Users may not:

```text
Rename

Delete

Modify
```

in v1.

---

# Artists

Workflow:

```text
Select Existing
OR
Create New
```

No aliases in v1.

---

# Movements

Starts with seeded data.

Users may create additional movements.

Workflow:

```text
Select Existing
OR
Create New
```

No aliases in v1.

---

# Subjects

Workflow:

```text
Select Existing
OR
Create New
```

Subjects are community-wide.

Examples:

```text
Cat

Landscape

David and Goliath
```

No aliases in v1.

---

# Tags

Workflow:

```text
Select Existing
OR
Create New
```

Tags are:

```text
Community-wide

Case-insensitive
```

Examples:

```text
Cat
cat
CAT
```

refer to the same tag.

Validation:

```text
2-50 characters

Letters

Numbers

Spaces

Hyphens
```

Autocomplete should prioritize popular tags.

Low-usage tags may be hidden from suggestions.

Do not introduce moderation workflows.

---

# Notes

Artworks have:

```text
One note field.
```

Do not implement:

```text
Note entities

Note history

Note versioning
```

Notes are not searchable.

---

# Discoverability

Default:

```text
Private
```

Optional:

```text
Discoverable
```

Requirements:

```text
Title set

Artist set

Date set
```

Artwork photos are not required.

---

# Visibility Rules

Community-visible:

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

Private Notes
```

Treat these as privacy requirements.

---

# Relationship Exploration

Supported:

```text
Same Artist

Same Subject

Same Movement

Same Museum

Shared Tags
```

Default scope:

```text
My Collection
```

Optional scopes:

```text
Watchlist

Community
```

Community discovery must remain:

```text
Relationship-based
```

Do not introduce:

```text
Global community search

Community feed

Browse-all catalog
```

---

# Tag Exploration

Tag exploration is cumulative.

Example:

```text
battle
```

↓

```text
battle + horse
```

↓

```text
battle + horse + armor
```

Results must match ALL selected tags.

Implement as AND logic.

---

# Search

Searchable:

```text
Title

Artist

Subject

Tags

Museum
```

Not searchable:

```text
Notes
```

---

# Collection View

Default:

```text
Grid
```

Alternative:

```text
List
```

Default sorting:

```text
Recently Added
```

Artwork card:

```text
Artwork Photo

Title

Artist

Date
```

---

# Authentication

v1 authentication:

```text
Email + Password
```

No social login requirements.

---

# Pagination

Default:

```text
50 records per page
```

---

# Testing Requirements

Every feature should be covered by appropriate tests.

Minimum categories:

```text
Unit Tests

Frontend Tests

Integration Tests
```

Critical coverage:

```text
Artwork Creation

Watchlist Conversion

Discoverability Rules

Relationship Exploration

Authentication
```

---

# OpenAPI Requirements

All API changes must be reflected in:

```text
openapi.yaml
```

Keep implementation and contract synchronized.

Do not introduce undocumented endpoints.

---

# Observability Requirements

Important metrics:

```text
Active Users

Artworks Created

Watchlist Conversions

Relationship Explorations

Discoverable Artworks
```

Primary alert:

```text
Artwork Creation Failure Rate
```

---

# Responder Agent

Responder agents:

```text
Investigate

Summarize

Recommend
```

They must never:

```text
Deploy

Rollback

Modify Production Data
```

without explicit human action.

---

# Non-Goals

Do not implement without explicit approval.

## AI

```text
Artwork Recognition

OCR

Semantic Search

AI Recommendations

AI Metadata Generation
```

## Social

```text
Following Users

Comments

Likes

Voting

Messaging
```

## Media Sharing

```text
Public Artwork Photos

Public Detail Photos
```

## Discovery

```text
Global Community Search

Community Homepage

Browse-All Artworks
```

## Visualization

```text
Graph Views

Node-Link Diagrams
```

---

# V2 Backlog

Future candidates:

```text
Artist Aliases

Movement Aliases

Subject Aliases

User Following

Community Search

Image Sharing

Graph Exploration
```

Do not partially implement V2 features in V1.

---

# Success Criteria

A successful implementation allows users to:

```text
Collect Artworks

Maintain Watchlists

Upload Photos

Record Notes

Explore Relationships

Discover Related Artworks

Without Introducing Social-Network Complexity
```