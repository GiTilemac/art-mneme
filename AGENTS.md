# AGENTS.md

# ArtMneme

Personal artwork collection and relationship exploration platform.

---

# Product Philosophy

```text
Collection First
→ Exploration Second
→ Community Third
```

ArtMneme is:

- a personal collection application
- a relationship exploration tool
- an optional metadata-sharing community

ArtMneme is NOT:

- a social network
- an image-sharing platform
- an art encyclopedia
- an AI product

When implementation decisions are ambiguous, prefer:

```text
Collection First
```

over community features.

---

# Source Of Truth

Implementation must remain consistent with:

```text
product-spec.md
openapi.yaml
database-schema.md
```

When those files conflict:

```text
product-spec.md
    >
openapi.yaml
    >
database-schema.md
```

for business behavior.

---

# Core Domain Model

```text
User

Artwork

Artist

Movement

Subject

Tag

ArtworkTag

DetailPhoto