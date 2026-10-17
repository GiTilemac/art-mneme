# ArtMneme - Database Schema (v1)

## Overview

ArtMneme uses a relational database.

The schema prioritizes:

- personal ownership
- relationship exploration
- community-wide metadata reuse
- minimal moderation requirements

The database model follows:

```text
User
│
└── Artwork
      │
      ├── Artist
      ├── Movement
      ├── Subject
      ├── Tags
      └── Detail Photos
```

---

# Entity Relationship Diagram

```text
User
 │
 └──< Artwork >──────── Artist
          │
          ├──────────── Movement
          │
          ├──────────── Subject
          │
          ├──< ArtworkTag >── Tag
          │
          └──< DetailPhoto
```

---

# User

Represents an