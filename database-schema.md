# ArtMneme Database Schema (v1)

## Overview

This document describes the persistent data model used by ArtMneme.

The schema is designed to support:

- personal artwork collections
- watchlists
- relationship exploration
- reusable community metadata
- discoverability
- future extensibility

The database intentionally prioritizes simplicity and explicit relationships over excessive normalization.

---

# Design Principles

## Collection First

Every artwork belongs to a user.

The primary use case is managing a personal artwork collection.

---

## Exploration Second

Relationships are a first-class feature.

Users should be able to explore artworks through:

- artist
- subject
- movement
- museum
- tags

---

## Community Metadata

The following entities are shared across all users:

```text
Artist
Movement
Subject
Tag
```

Users may create them.

Users may not modify or delete them in v1.

---

## Metadata-First Community Layer

Discoverability is based on metadata.

Artwork photos and detail photos remain private.

---

# Entity Relationship Diagram

```text
User
 │
 └──< Artwork
           │
           ├──── Artist
           ├──── Movement
           ├──── Subject
           ├──< ArtworkTag >── Tag
           └──< DetailPhoto
```

---

# User

Represents an authenticated user.

## Table

```text
User
----
id (PK)

email
password_hash

created_at
updated_at
```

## Relationships

```text
User
1 → N Artwork
```

---

# Artwork

Central domain entity.

Represents both:

```text
WATCHLIST
COLLECTION
```

states.

There is no separate watchlist table.

---

## Table

```text
Artwork
-------
id (PK)

user_id (FK)

collection_state

title

artist_id (FK)

date_display

year_start
year_end

subject_id (FK)

movement_id (FK)

museum

notes

is_discoverable

are_notes_discoverable

artwork_photo_path

created_at
updated_at
```

---

## collection_state

Allowed values:

```text
WATCHLIST
COLLECTION
```

---

### WATCHLIST

Artwork not yet encountered.

Photo optional.

---

### COLLECTION

Artwork encountered.

Artwork photo required.

---

## Artwork Identity

Identity fields:

```text
Title
Artist
Date
```

These identify the artwork conceptually.

---

## Artwork Metadata

Metadata fields:

```text
Subject
Movement
Museum
Tags
Notes
Photos
```

Metadata enriches the artwork but does not define identity.

---

## Duplicate Detection

Based on:

```text
Title
+
Artist
+
Date
```

Duplicates generate warnings only.

No uniqueness constraints are enforced.

---

# Artist

Community-wide reusable artist entity.

## Table

```text
Artist
------
id (PK)

name

created_at
```

---

## Rules

Case-insensitive uniqueness.

Examples:

```text
Caravaggio
Rembrandt
Rubens
```

---

## Ownership

Community-owned.

Cannot be modified or deleted in v1.

---

# Movement

Community-wide reusable movement entity.

## Table

```text
Movement
--------
id (PK)

name

created_at
```

---

## Seed Data

Examples:

```text
Baroque
Renaissance
Impressionism
Romanticism
Expressionism
```

Users may create additional movements.

---

## Rules

Case-insensitive uniqueness.

---

## Ownership

Community-owned.

Cannot be modified or deleted in v1.

---

# Subject

Community-wide reusable subject entity.

## Table

```text
Subject
-------
id (PK)

name

created_at
```

---

## Examples

```text
Cat
Landscape
Ship
David and Goliath
Judgement of Paris
```

---

## Rules

Case-insensitive uniqueness.

---

## Ownership

Community-owned.

Cannot be modified or deleted in v1.

---

# Tag

Community-wide reusable tag entity.

## Table

```text
Tag
---
id (PK)

name

usage_count

created_at
```

---

## Rules

Case-insensitive uniqueness.

Examples:

```text
Cat
cat
CAT
```

all refer to the same tag.

---

## Validation

Minimum length:

```text
2
```

Maximum length:

```text
50
```

Allowed characters:

```text
Letters
Numbers
Spaces
Hyphens
```

---

## Autocomplete Rules

Autocomplete prioritizes:

```text
Frequently-used tags
```

Very low-usage tags may be hidden from suggestions.

Hidden tags remain valid database records.

---

## Ownership

Community-owned.

Cannot be modified or deleted in v1.

---

# ArtworkTag

Many-to-many bridge table.

Connects artwork records and tags.

## Table

```text
ArtworkTag
----------
artwork_id (FK)

tag_id (FK)

source
```

---

## Source Values

```text
USER
SYSTEM
```

Reserved for future flexibility.

---

# DetailPhoto

Represents detail images attached to an artwork.

Examples:

```text
Brushstroke detail

Armor detail

Signature detail

Frame detail
```

---

## Table

```text
DetailPhoto
-----------
id (PK)

artwork_id (FK)

path

created_at
```

---

## Rules

Detail photos are:

```text
Private
Not discoverable
Never shared publicly
```

---

# Photo Model

## Artwork Photo

Stored directly on Artwork.

Field:

```text
artwork_photo_path
```

Rules:

```text
Exactly one artwork photo per artwork.

Photo may be replaced.

Photo is never publicly shared.
```

---

## Detail Photos

Stored separately.

Relationship:

```text
Artwork
1 → N DetailPhoto
```

---

# Ownership Matrix

| Resource | Owner |
|-----------|-----------|
| Artwork | User |
| Artwork Photo | User |
| Detail Photo | User |
| Notes | User |
| Artist | Community |
| Movement | Community |
| Subject | Community |
| Tag | Community |

---

# Discoverability Rules

Default:

```text
Private
```

Optional:

```text
Discoverable
```

An artwork may become discoverable only when:

```text
Title is set

Artist is set

Date is set
```

Artwork photo is not required.

---

# Community Visibility

Visible:

```text
Title
Artist
Date

Subject
Movement
Museum
Tags

Discoverable Notes
```

Not Visible:

```text
Artwork Photos

Detail Photos

Private Notes
```

---

# Search Model

Searchable fields:

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

# Relationship Exploration Mapping

| Exploration Mode | Database Source |
|------------------|----------------|
| Same Artist | artist_id |
| Same Subject | subject_id |
| Same Movement | movement_id |
| Same Museum | museum |
| Shared Tags | ArtworkTag |

---

# Indexing Strategy

The following indexes are recommended.

## Artwork

```text
user_id

collection_state

artist_id

subject_id

movement_id

is_discoverable
```

---

## Community Metadata

```text
Artist(name)

Movement(name)

Subject(name)

Tag(name)
```

---

## ArtworkTag

```text
artwork_id

tag_id
```

---

# Deletion Strategy

## Artwork

Hard delete.

Deleting an artwork removes:

```text
Artwork

Associated detail photos

Artwork-tag relationships
```

---

## Community Entities

The following are not deletable in v1:

```text
Artist

Movement

Subject

Tag
```

This avoids orphaned references and accidental data loss.

---

# Pagination

Default pagination:

```text
50 records per page
```

Applies to:

```text
Artworks

Artists

Movements

Subjects

Tags
```

---

# Explicit Non-Models

The following are intentionally not modeled as separate entities.

## Museum

Stored as:

```text
Artwork.museum
```

Reason:

```text
User-entered
Not canonical
Low business value
```

---

## Notes

Stored as:

```text
Artwork.notes
```

Reason:

```text
Single note field

No history

No versioning
```

---

# Future Schema Evolution (V2)

Potential future additions:

```text
ArtistAlias

MovementAlias

SubjectAlias

UserFollowing

CommunitySearch

SharedImages

Moderation
```

These features are intentionally excluded from v1.