# ArtMneme Backlog

Each task is meant to fit in one working session. Each one can be read on its own.
Sources of truth: `product-spec.md`, `openapi.yaml`, `docs/database-schema.md`, `docs/architecture.md`, `docs/observability.md`.
Every endpoint is already defined in `openapi.yaml`. Each task implements its endpoints exactly as defined there; if a task needs a change to an endpoint, `openapi.yaml` is changed first, with the project owner's approval.
This backlog covers the backend only. The frontend in `frontend/` is built in Lovable and talks to the backend through `frontend/src/services/`.

---

## 1. Empty backend with a passing test
Goal: An empty backend that builds, with one passing test.
Description: Create a `backend/` folder holding an empty Python + FastAPI application, as the repository structure in `README.md` describes. It gets one trivial test that passes. The README explains how to install, start and test it, using one command for each step where possible.

## 2. Database schema and seed data
Goal: An empty PostgreSQL database can be turned into the full v1 schema with one command.
Description: Create all tables, relationships and recommended indexes from `docs/database-schema.md`: User, Artwork, Artist, Movement, Subject, Tag, ArtworkTag and DetailPhoto. Seed the movements listed in `docs/database-schema.md`. Add a test proving the schema builds on an empty database and that the backend can connect to it.

## 3. Registration, login and logout API
Goal: A person can create an account, log in, stay logged in through a cookie session, and log out through the API.
Description: Implement `/auth/register`, `/auth/login`, `/auth/logout` and `/auth/me` as `openapi.yaml` defines them. Passwords are stored only as hashes, and sessions use cookies as `docs/architecture.md` states. Tests cover a wrong password, a duplicate email, and calling `/auth/me` while logged out.

## 4. Artist, Movement and Subject API
Goal: Users can search existing artists, movements and subjects, and create new ones.
Description: Implement the endpoints in `openapi.yaml` to search by name and create Artists, Movements and Subjects. Creating a name that already exists returns the existing one. These are community-wide, case-insensitively unique ("rembrandt" finds "Rembrandt" instead of creating a second one) and cannot be edited or deleted. Lists are paginated at 50 results per page.

## 5. Tag API with validation and suggestions
Goal: Users can create tags and get autocomplete suggestions ranked by popularity.
Description: Implement the endpoints in `openapi.yaml` to create tags and suggest tags from typed text. Tags are case-insensitive ("Cat", "cat" and "CAT" are one tag), 2 to 50 characters long, and may contain only letters, numbers, spaces and hyphens. Suggestions put frequently used tags first, using `Tag.usage_count`, and leave out tags used on fewer than 2 artworks.

## 6. Private photo storage
Goal: The backend can store, read and delete photos in Cloudflare R2, and only the owner can view them.
Description: Build the backend piece that uploads a photo file to Cloudflare R2, returns the stored path, and deletes it later, as `docs/architecture.md` decides. Photos are never publicly reachable. The backend hands a photo only to the user who owns the artwork. Tests must run without a real R2 account.

## 7. Create artwork API
Goal: A logged-in user can create a collection artwork (with photo) or a watchlist artwork (photo optional).
Description: Implement the create-artwork endpoint from `openapi.yaml`; details, state and photo arrive in one request. The user chooses the state: COLLECTION (the default) or WATCHLIST. A COLLECTION artwork needs an artwork photo; a WATCHLIST artwork may have one or not. Every metadata field may be left empty and filled in later. The artwork belongs to the user who created it.

## 8. View, edit and delete own artwork API
Goal: A user can fetch, edit and hard-delete their own artworks, and nobody else's.
Description: Implement the endpoints in `openapi.yaml` to fetch one artwork, update its metadata, notes and tags, and delete it. Deleting removes the artwork, its detail photos (including the stored files) and its tag links, as `docs/database-schema.md` describes. Another user's artwork behaves as if it does not exist.

## 9. Duplicate warning
Goal: Before saving, the app can ask whether the user already has an artwork with the same title, artist and date, and show a warning; saving is still allowed.
Description: Implement the duplicate-check endpoint from `openapi.yaml`, which the app calls before saving to find possible duplicates based on Title + Artist + Date, as `product-spec.md` describes under Duplicate Handling. The warning never blocks creation, and no uniqueness rule is added to the database.

## 10. Artwork photo upload and replace (watchlist to collection)
Goal: Uploading a photo to a watchlist artwork moves it into the collection; uploading to a collection artwork replaces its photo.
Description: Implement the endpoint in `openapi.yaml` to upload an artwork's main photo, and the one to get it. If the artwork is WATCHLIST, it becomes COLLECTION; if it already had a photo, that photo is deleted. If it is already COLLECTION, the old photo file is replaced and removed from storage. There is no way to remove the main photo without a replacement, and a COLLECTION artwork can never move back to WATCHLIST. A collection artwork can never end up without a photo.

## 11. Detail photos API
Goal: A user can add, list and delete any number of detail photos on their own artworks.
Description: Implement the detail-photo endpoints in `openapi.yaml`, using the `DetailPhoto` table from `docs/database-schema.md`. Detail photos are private: they are only ever shown to the artwork's owner and never appear in community results. Deleting a detail photo also deletes the stored file.

## 12. Artwork list API
Goal: A user can list their collection or their watchlist, newest first, 50 per page.
Description: Implement the endpoint in `openapi.yaml` that lists the logged-in user's own artworks, filtered by state (COLLECTION or WATCHLIST). The default sort is Recently Added. Each item carries what an artwork card shows: photo, title, artist and date.

## 13. Search and filter API
Goal: A user can search and filter their own artworks.
Description: Add search over Title, Artist, Subject, Tags and Museum, and filters for Artist, Movement, Museum, Tags and Date Range, to the artwork list endpoint as `openapi.yaml` defines them and `product-spec.md` lists. Notes are never searched. Search covers only the user's own artworks, because the spec excludes global community search.

## 14. Discoverability API
Goal: A user can make an artwork discoverable, and separately make its notes discoverable.
Description: Implement the endpoints in `openapi.yaml` to switch `is_discoverable` and `are_notes_discoverable` on and off. Making an artwork discoverable is refused unless its title, artist and date are all set; a photo is not required. Both settings start as private.

## 15. Relationship exploration API (artist, subject, movement, museum)
Goal: From one artwork, a user can list other artworks with the same artist, subject, movement or museum.
Description: Implement the exploration endpoint from `openapi.yaml`, using the mapping in `docs/database-schema.md` under Relationship Exploration Mapping. Results come from the user's collection by default; watchlist and community results are included only when asked for. Community results come only from discoverable artworks and show only the fields listed under Community Visibility, never photos or private notes.

## 16. Shared tags exploration API
Goal: A user can find artworks that carry all of a chosen set of tags.
Description: Extend relationship exploration with Shared Tags, where results must match every selected tag (battle + horse + armor). It uses the same sources (collection by default; watchlist and community on request) and the same community privacy rules as the other exploration modes.
