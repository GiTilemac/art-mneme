# ArtMneme v1 — Build Plan

## Phase 1 (this build): the personal collection app
1. **Accounts** — email + password sign-up/sign-in (min 8 chars), stay signed in with a rolling session.
2. **Add artwork** — title, artist, date (from/to year, circa, BC → "c. 450 BC"), subject, movement, museum, tags, note. Photo optional → saved as Watchlist; with photo → Collection.
   - Artist / Movement / Subject / Tag: pick existing or create new (shared across everyone, never editable/deletable). Movements pre-seeded.
   - Tags: case-insensitive, 2–50 chars, letters/numbers/spaces/hyphens; suggestions show only tags used on 2+ artworks, most popular first.
   - Duplicate warning (own artworks, same title ignoring case/spaces, same artist, same date) — creation still allowed.
3. **Photos** — any browser-readable image up to 30 MB, shrunk in browser to ~2,500 px, stored as JPEG, private storage only. One main photo (replaceable), any number of detail photos (add/delete).
4. **Artwork page** — all fields, edit metadata/notes, replace photo (Watchlist → Collection), hard delete.
5. **Collection & Watchlist views** — grid (default) / list, recently added, 50 per page, search (title, artist, subject, tags, museum — not notes), filters (artist, movement, museum, tags, date range).
6. **Discoverability** — private by default; can only be enabled when title, artist and date are set. Notes shared separately (off by default). Photos never shared.
7. **Explore relationships** — from an artwork: same artist / subject / movement / museum / shared tags (progressive AND narrowing). Sources: My Collection (default), toggle Watchlist, toggle Community (shows only shared fields, no photos). No global community search or feed.
8. **Usage events** recorded (sign-ins, artworks created, explorations, discoverable toggles, watchlist conversions, creation failures) to feed a later dashboard.

## Phase 2 (later, separate request)
- Observability dashboard + creation-failure alert.
- Advisory responder agent.

## Design direction
Quiet museum aesthetic: warm off-white paper, deep ink text, oxblood accent, serif display headings (Cormorant) with a clean sans body. Image-first grid, no hover-dependent controls, works at narrow widths.

## Technical details
- Lovable Cloud: auth, Postgres with RLS (artworks/detail photos owned per user; community reads via a security-definer function returning only discoverable public fields), private storage bucket with per-user folder policies.
- Tables: artists, movements, subjects, tags (unique lower(name)), artworks, artwork_tags, detail_photos, usage_events.
- TanStack routes: /, /auth, /_authenticated/{collection, watchlist, artworks/new, artworks/$id, artworks/$id/explore}.
- Tests for date formatting, tag validation, duplicate matching, discoverability rule.
