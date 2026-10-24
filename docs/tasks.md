# ArtMneme Backlog

Each task is meant to fit in one working session. Each one can be read on its own.
Sources of truth: `product-spec.md`, `openapi.yaml`, `docs/database-schema.md`, `docs/architecture.md`, `docs/observability.md`.
Any task that adds an endpoint must first add it to `openapi.yaml`.
This backlog covers the backend only. The frontend in `frontend/` is built in Lovable and talks to the backend through `frontend/src/lib/api.ts`.

---

## 1. Empty backend with a passing test
Goal: An empty backend that builds, with one passing test.
Description: Create a `backend/` folder holding an empty Python + FastAPI application, as the repository structure in `README.md` describes. It gets one trivial test that passes. The README explains how to install, start and test it, using one command for each step where possible.

## 2. Database schema and seed data
Goal: An empty PostgreSQL database can be turned into the full v1 schema with one command.
Description: Create all tables, relationships and recommended indexes from `docs/database-schema.md`: User, Artwork, Artist, Movement, Subject, Tag, ArtworkTag and DetailPhoto. Seed the movements listed in `docs/database-schema.md`. Add a test proving the schema builds on an empty database and that the backend can connect to it.

## 3. Registration, login and logout API
Goal: A person can create an account, log in, stay logged in through a cookie session, and log out through the API.
Description: Implement `/auth/register`, `/auth/login`, `/auth/logout` and `/auth/me` from `openapi.yaml`, and complete their request and response definitions there. Passwords are stored only as hashes, and sessions use cookies as `docs/architecture.md` states. Tests cover a wrong password, a duplicate email, and calling `/auth/me` while logged out.

## 4. Artist, Movement and Subject API
Goal: Users can search existing artists, movements and subjects, and create new ones.
Description: Add endpoints to list, search by name and create Artists, Movements and Subjects, and document them in `openapi.yaml`. These are community-wide, case-insensitively unique ("rembrandt" finds "Rembrandt" instead of creating a second one) and cannot be edited or deleted. Lists are paginated at 50 results per page.

## 5. Tag API with validation and suggestions
Goal: Users can create tags and get autocomplete suggestions ranked by popularity.
Description: Add endpoints to create tags and suggest tags from typed text, and document them in `openapi.yaml`. Tags are case-insensitive ("Cat", "cat" and "CAT" are one tag), 2 to 50 characters long, and may contain only letters, numbers, spaces and hyphens. Suggestions put frequently used tags first, using `Tag.usage_count`, and leave out tags used on fewer than 2 artworks.

## 6. Private photo storage
Goal: The backend can store, read and delete photos in Cloudflare R2, and only the owner can view them.
Description: Build the backend piece that uploads a photo file to Cloudflare R2, returns the stored path, and deletes it later, as `docs/architecture.md` decides. Photos are never publicly reachable. The backend hands a photo only to the user who owns the artwork. Tests must run without a real R2 account.

## 7. Create artwork API
Goal: A logged-in user can create a collection artwork (with photo) or a watchlist artwork (photo optional).
Description: Add the create-artwork endpoint to `openapi.yaml` and implement it. The user chooses the state: COLLECTION (the default) or WATCHLIST. A COLLECTION artwork needs an artwork photo; a WATCHLIST artwork may have one or not. Every metadata field may be left empty and filled in later. The artwork belongs to the user who created it.

## 8. View, edit and delete own artwork API
Goal: A user can fetch, edit and hard-delete their own artworks, and nobody else's.
Description: Add endpoints to fetch one artwork, update its metadata, notes and tags, and delete it, and document them in `openapi.yaml`. Deleting removes the artwork, its detail photos (including the stored files) and its tag links, as `docs/database-schema.md` describes. Another user's artwork behaves as if it does not exist.

## 9. Duplicate warning
Goal: Creating an artwork whose title, artist and date match one the user already has returns a warning, and creation is still allowed.
Description: Extend the create-artwork endpoint so that it reports possible duplicates based on Title + Artist + Date, as `product-spec.md` describes under Duplicate Handling. The warning never blocks creation, and no uniqueness rule is added to the database. Document the warning in `openapi.yaml`.

## 10. Artwork photo upload and replace (watchlist to collection)
Goal: Uploading a photo to a watchlist artwork moves it into the collection; uploading to a collection artwork replaces its photo.
Description: Add an endpoint to upload an artwork's main photo and document it in `openapi.yaml`. If the artwork is WATCHLIST, it becomes COLLECTION; if it already had a photo, that photo is deleted. If it is already COLLECTION, the old photo file is replaced and removed from storage. There is no way to remove the main photo without a replacement, and a COLLECTION artwork can never move back to WATCHLIST. A collection artwork can never end up without a photo.

## 11. Detail photos API
Goal: A user can add, list and delete any number of detail photos on their own artworks.
Description: Add endpoints for detail photos and document them in `openapi.yaml`, using the `DetailPhoto` table from `docs/database-schema.md`. Detail photos are private: they are only ever shown to the artwork's owner and never appear in community results. Deleting a detail photo also deletes the stored file.

## 12. Artwork list API
Goal: A user can list their collection or their watchlist, newest first, 50 per page.
Description: Add an endpoint that lists the logged-in user's own artworks, filtered by state (COLLECTION or WATCHLIST), and document it in `openapi.yaml`. The default sort is Recently Added. Each item carries what an artwork card shows: photo, title, artist and date.

## 13. Search and filter API
Goal: A user can search and filter their own artworks.
Description: Add search over Title, Artist, Subject, Tags and Museum, and filters for Artist, Movement, Museum, Tags and Date Range, as `product-spec.md` lists. Notes are never searched. Search covers only the user's own artworks, because the spec excludes global community search. Document it in `openapi.yaml`.

## 14. Discoverability API
Goal: A user can make an artwork discoverable, and separately make its notes discoverable.
Description: Add endpoints to switch `is_discoverable` and `are_notes_discoverable` on and off, and document them in `openapi.yaml`. Making an artwork discoverable is refused unless its title, artist and date are all set; a photo is not required. Both settings start as private.

## 15. Relationship exploration API (artist, subject, movement, museum)
Goal: From one artwork, a user can list other artworks with the same artist, subject, movement or museum.
Description: Add an exploration endpoint and document it in `openapi.yaml`, using the mapping in `docs/database-schema.md` under Relationship Exploration Mapping. Results come from the user's collection by default; watchlist and community results are included only when asked for. Community results come only from discoverable artworks and show only the fields listed under Community Visibility, never photos or private notes.

## 16. Shared tags exploration API
Goal: A user can find artworks that carry all of a chosen set of tags.
Description: Extend relationship exploration with Shared Tags, where results must match every selected tag (battle + horse + armor). It uses the same sources (collection by default; watchlist and community on request) and the same community privacy rules as the other exploration modes. Document it in `openapi.yaml`.
