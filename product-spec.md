# ArtMneme Product Specification (v1)

## Overview

ArtMneme is a personal artwork collection and relationship exploration platform.

Users collect artworks they have personally encountered, enrich them with metadata, document observations through notes and photos, and discover connections between artworks through explicit relationship exploration.

---

# Problem Statement

Art enthusiasts, museum visitors, travelers, and collectors regularly encounter artworks they want to remember and revisit.

Existing solutions such as:

- photo galleries
- note-taking applications
- spreadsheets
- bookmarking systems

allow storage but do not effectively support exploration and rediscovery.

ArtMneme solves this by combining:

```text
Collection

Documentation

Relationship Exploration

Watchlists
```

into a single workflow.

---

# Product Philosophy

```text
Collection First
→ Exploration Second
→ Community Third
```

ArtMneme is:

```text
Personal Collection Platform

Relationship Exploration Tool

Metadata Discovery Platform
```

ArtMneme is not:

```text
Social Network

Image Sharing Platform

Art Encyclopedia

AI Product
```

When tradeoffs occur, prioritize collection features over community features.

---

# Goals

Users should be able to:

```text
Collect artworks

Remember artworks

Explore artwork relationships

Manage future interests

Discover related artworks
```

without requiring social-network functionality.

---

# Platform

v1 targets desktop browsers.

A later version will target Android phones.

v1 screens must:

```text
Resize to narrow widths

Not rely on hover, right-click or drag
```

---

# Authentication

Authentication is required.

Supported in v1:

```text
Email + Password
```

Password rule:

```text
At least 8 characters

No other composition rules
```

Users stay logged in for 30 days. The 30 days restart each time they use the app.

Each user owns:

```text
Artworks

Artwork Photos

Detail Photos

Notes
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

There is no separate watchlist entity.

An artwork exists in one of two states:

```text
WATCHLIST
COLLECTION
```

---

## WATCHLIST

Represents an artwork not yet encountered.

Rules:

```text
Photo Optional
```

Examples:

```text
Artwork discovered via:

Book

Museum Website

Instagram

Recommendation

Relationship Exploration
```

---

## COLLECTION

Represents an artwork personally encountered by the user.

Rules:

```text
Artwork Photo Required
```

New artworks are created as COLLECTION by default. The user may choose WATCHLIST instead.

---

# Artwork Identity

Identity fields:

```text
Title
Artist
Date
```

Identity fields are used for duplicate detection and discoverability validation.

---

## Date Entry

The user enters:

```text
From year     (required for a date)

To year       (optional)

Circa         (checkbox)

BC            (checkbox)
```

The displayed date is generated from these.

Examples:

```text
1642

1600–1605

c. 1600

c. 450 BC
```

---

# Artwork Metadata

Metadata fields:

```text
Subject
Movement
Museum
Tags
Notes
Photos
```

Metadata enriches an artwork but does not define its identity.

---

# Artwork Structure

Each artwork contains:

```text
Title

Artist

Date

Subject

Movement

Museum

Tags

Notes

Artwork Photo

Detail Photos
```

---

# Artist

Artists are community-wide entities.

Workflow:

```text
Select Existing
OR
Create New
```

Examples:

```text
Caravaggio

Rembrandt

Rubens
```

Rules:

```text
Cannot be edited

Cannot be deleted
```

Aliases are deferred to v2.

---

# Movement

Movements are community-wide entities.

The application ships with seeded movements.

Examples:

```text
Baroque

Renaissance

Impressionism

Romanticism

Expressionism
```

Users may create additional movements.

Workflow:

```text
Select Existing
OR
Create New
```

Rules:

```text
Cannot be edited

Cannot be deleted
```

Aliases are deferred to v2.

---

# Subject

Subjects are community-wide entities.

Workflow:

```text
Select Existing
OR
Create New
```

Examples:

```text
Cat

Landscape

Ship

David and Goliath

Judgement of Paris
```

Rules:

```text
Cannot be edited

Cannot be deleted
```

Aliases are deferred to v2.

---

# Museum

Stored as free text.

Represents where the user encountered the artwork.

Examples:

```text
Louvre

Prado

Alte Nationalgalerie
```

Museum does NOT represent:

```text
Ownership

Provenance

Permanent Collection
```

---

# Tags

Tags are community-wide entities.

Workflow:

```text
Select Existing
OR
Create New
```

Tags are case-insensitive.

Example:

```text
Cat
cat
CAT
```

represent the same tag.

---

## Tag Validation

Length:

```text
2-50 characters
```

Allowed:

```text
Letters

Numbers

Spaces

Hyphens
```

---

## Tag Suggestions

Autocomplete prioritizes popular tags.

Tags used on fewer than 2 artworks are hidden from suggestions.

The tag remains valid even when hidden.

---

# Notes

Each artwork contains a single note field.

Rules:

```text
No note history

No note versioning

Not searchable
```

---

# Photos

Applies to artwork photos and detail photos.

```text
Original file:   up to 30 MB

Before upload:   shrunk in the browser to about 2,500 pixels on the longest side

File types:      any image the browser can open

Stored as:       JPEG
```

Files the browser cannot open are refused with a message saying the file type is not supported.

## Future: Local Photos

Not part of v1. In v1 every photo is uploaded.

A later version will remember, on the device where a photo was added, where the original file is stored. That device shows the original.

Other devices show the uploaded compressed copy.

An account-wide setting will let the user turn off uploading. Photos then stay only on the device where they were added, and other devices show the artwork without its photos.

How the device remembers the original file is not decided yet.

## Artwork Photo

Each artwork contains:

```text
Zero or One Artwork Photo
```

A COLLECTION artwork has exactly one artwork photo. A WATCHLIST artwork has zero or one.

Rules:

```text
May be replaced

Cannot be removed without a replacement; to drop it, delete the artwork

Shown as the main image

Never publicly shared
```

---

## Detail Photos

Each artwork may contain:

```text
Zero or More Detail Photos
```

Examples:

```text
Armor Detail

Brushstroke Detail

Signature Detail

Frame Detail
```

Rules:

```text
Private

Never Shared

Never Discoverable
```

---

# Artwork Page

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

---

# Watchlist Workflow

Users may discover artworks through:

```text
Museums

Books

Websites

Social Media

Relationship Exploration
```

These artworks are initially:

```text
WATCHLIST
```

When an artwork is later encountered:

```text
Upload Artwork Photo
```

and the artwork becomes:

```text
COLLECTION
```

If the watchlist artwork already has a photo, that photo is deleted and replaced by the collection photo.

A COLLECTION artwork cannot be moved back to WATCHLIST. The user creates a new watchlist artwork instead.

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

---

## Requirements

Discoverability requires:

```text
Title Set

Artist Set

Date Set
```

Artwork photos are not required.

---

# Notes Discoverability

Notes are controlled independently.

Options:

```text
Private Notes

Discoverable Notes
```

Default:

```text
Private Notes
```

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

Hidden:

```text
Artwork Photos

Detail Photos

Private Notes
```

---

# Community Discovery

Community discovery is relationship-driven.

Community content appears only through exploration.

---

## Allowed

```text
Same Artist

Same Subject

Same Movement

Same Museum

Shared Tags
```

---

## Not Allowed

```text
Global Community Search

Community Feed

Browse-All Catalog
```

---

# Relationship Exploration

Supported dimensions:

```text
Same Artist

Same Subject

Same Movement

Same Museum

Shared Tags
```

---

## Tag Exploration

Users may progressively narrow exploration.

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

Results must match all selected tags.

Use AND logic.

---

## Exploration Sources

Default:

```text
My Collection
```

Optional:

```text
Watchlist

Community
```

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

# Filtering

Supported filters:

```text
Artist

Movement

Museum

Tags

Date Range
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

Default sort:

```text
Recently Added
```

Artwork card displays:

```text
Artwork Photo

Title

Artist

Date
```

---

# Duplicate Handling

Duplicate detection uses:

```text
Title
Artist
Date
```

Matching:

```text
Title:   same, ignoring capital letters and extra spaces

Artist:  same artist

Date:    same years, same Circa and BC choices
```

The check runs only when title, artist and date are all set.

Compared against:

```text
The user's own artworks (collection and watchlist)
```

Behavior:

```text
Display Warning

Allow Creation
```

No uniqueness constraints.

---

# Deletion Rules

Artwork:

```text
Hard Delete
```

Metadata entities:

```text
Artist

Movement

Subject

Tag
```

cannot be deleted in v1.

---

# Pagination

Default:

```text
50 results per page
```

---

# Acceptance Criteria

## Create Artwork

Given an authenticated user

When they create an artwork with an artwork photo

Then it is created as COLLECTION by default.

The user may choose WATCHLIST instead.

---

Given an authenticated user

When they create an artwork without a photo

Then it can only be created as WATCHLIST.

---

Given a WATCHLIST artwork that has a photo

When the user uploads a collection photo

Then it becomes COLLECTION, and the old photo is deleted.

---

Given metadata is skipped

Then the artwork remains editable later.

---

Given detail photos are uploaded

Then they are attached to the artwork.

---

Given duplicate detection finds a match

Then a warning is displayed.

Artwork creation remains possible.

---

## Relationship Exploration

Given an artwork

When the user selects:

```text
Same Artist

Same Subject

Same Movement

Same Museum

Shared Tags
```

Then matching artworks are displayed.

---

Collection results appear by default.

---

Watchlist results appear only when enabled.

---

Community results appear only when enabled.

---

## Discoverability

Given an artwork is private

When the user enables discoverability

Then:

```text
Title is set

Artist is set

Date is set
```

Otherwise discoverability is denied.

---

# Observability

Dashboard metrics:

```text
Active Users

Artworks Created

Relationship Explorations

Discoverable Artworks

Watchlist Conversions
```

Primary alert:

```text
Artwork Creation Failure Rate
```

---

# Responder Agent

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

Responder agents are advisory only.

Automatic production changes are out of scope.

---

# Non-Goals

## AI

```text
Artwork Recognition

OCR

Semantic Search

AI Recommendations

AI Metadata Generation
```

---

## Social

```text
Following Users

Comments

Likes

Voting

Messaging
```

---

## Media Sharing

```text
Public Artwork Photos

Public Detail Photos
```

---

## Discovery

```text
Global Community Search

Community Homepage

Browse-All Community Catalog