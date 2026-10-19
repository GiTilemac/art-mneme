# ArtMneme Backlog

Each task is meant to fit in one working session. Each one can be read on its own.
Sources of truth: `product-spec.md`, `openapi.yaml`, `docs/database-schema.md`, `docs/architecture.md`, `docs/observability.md`.
Any task that adds an endpoint must first add it to `openapi.yaml`.

---

## 1. Empty project with a passing test
Goal: An empty backend and frontend that build, each with one passing test.
Description: Create a `backend/` folder holding an empty Python + FastAPI application and a `frontend/` folder holding an empty React + TypeScript application, as the repository structure in `README.md` describes. Each gets one trivial test that passes. The README explains how to install, start and test both, using one command for each step where possible.

## 2. Database schema and seed data
Goal: An empty PostgreSQL database can be turned into the full v1 schema with one command.
Description: Create all tables, relationships and recommended indexes from `docs/database-schema.md`: User, Artwork, Artist, Movement, Subject, Tag, ArtworkTag and DetailPhoto. Seed the movements listed in `docs/database-schema.md`. Add a test proving the schema builds on an empty database and that the backend can connect to it.

## 3. Registration, login and logout API
Goal: A person can create an account, log in, stay logged in through a cookie session, and log out through the API.
Description: Implement `/auth/register`, `/auth/login`, `/auth/logout` and `/auth/me` from `openapi.yaml`, and complete their request and response definitions there. Passwords are stored only as hashes, and sessions use cookies as `docs/architecture.md` states. Tests cover a wrong password, a duplicate email, and calling `/auth/me` while logged out.

## 4. Login and register screens
Goal: A person can register, log in and log out in the browser.
Description: Build the Login and Register screens listed in `docs/architecture.md` on top of the existing `/auth/*` endpoints. A logged-out user who opens any other screen is sent to Login. Error messages from the API, such as a wrong password, are shown to the user.

## 5. Artist, Movement and Subject API
Goal: Users can search existing artists, movements and subjects, and create new ones.
Description: Add endpoints to list, search by name and create Artists, Movements and Subjects, and document them in `openapi.yaml`. These are community-wide, case-insensitively unique ("rembrandt" finds "Rembrandt" instead of creating a second one) and cannot be edited or deleted. Lists are paginated at 50 results per page.

## 6. Tag API with validation and suggestions
Goal: Users can create tags and get autocomplete suggestions ranked by popularity.
Description: Add endpoints to create tags and suggest tags from typed text, and document them in `openapi.yaml`. Tags are case-insensitive ("Cat", "cat" and "CAT" are one tag), 2 to 50 characters long, and may contain only letters, numbers, spaces and hyphens. Suggestions put frequently used tags first, using `Tag.usage_count`, and leave out tags used on fewer than 2 artworks.

## 7. Private photo storage
Goal: The backend can store, read and delete photos in Cloudflare R2, and only the owner can view them.
Description: Build the backend piece that uploads a photo file to Cloudflare R2, returns the stored path, and deletes it later, as `docs/architecture.md` decides. Photos are never publicly reachable. The backend hands a photo only to the user who owns the artwork. Tests must run without a real R2 account.

## 8. Create artwork API
Goal: A logged-in user can create a collection artwork (with photo) or a watchlist artwork (photo optional).
Description: Add the create-artwork endpoint to `openapi.yaml` and implement it. An artwork with an artwork photo is created in the COLLECTION state; one without a photo is created in the WATCHLIST state. Every metadata field may be left empty and filled in later. The artwork belongs to the user who created it.

## 9. View, edit and delete own artwork API
Goal: A user can fetch, edit and hard-delete their own artworks, and nobody else's.
Description: Add endpoints to fetch one artwork, update its metadata, notes and tags, and delete it, and document them in `openapi.yaml`. Deleting removes the artwork, its detail photos (including the stored files) and its tag links, as `docs/database-schema.md` describes. Another user's artwork behaves as if it does not exist.

## 10. Duplicate warning
Goal: Creating an artwork whose title, artist and date match one the user already has returns a warning, and creation is still allowed.
Description: Extend the create-artwork endpoint so that it reports possible duplicates based on Title + Artist + Date, as `product-spec.md` describes under Duplicate Handling. The warning never blocks creation, and no uniqueness rule is added to the database. Document the warning in `openapi.yaml`.

## 11. Artwork photo upload and replace (watchlist to collection)
Goal: Uploading a photo to a watchlist artwork moves it into the collection; uploading to a collection artwork replaces its photo.
Description: Add an endpoint to upload an artwork's main photo and document it in `openapi.yaml`. If the artwork is WATCHLIST, it becomes COLLECTION; if it is already COLLECTION, the old photo file is replaced and removed from storage. A collection artwork can never end up without a photo.

## 12. Detail photos API
Goal: A user can add, list and delete any number of detail photos on their own artworks.
Description: Add endpoints for detail photos and document them in `openapi.yaml`, using the `DetailPhoto` table from `docs/database-schema.md`. Detail photos are private: they are only ever shown to the artwork's owner and never appear in community results. Deleting a detail photo also deletes the stored file.

## 13. Artwork list API
Goal: A user can list their collection or their watchlist, newest first, 50 per page.
Description: Add an endpoint that lists the logged-in user's own artworks, filtered by state (COLLECTION or WATCHLIST), and document it in `openapi.yaml`. The default sort is Recently Added. Each item carries what an artwork card shows: photo, title, artist and date.

## 14. Search and filter API
Goal: A user can search and filter their own artworks.
Description: Add search over Title, Artist, Subject, Tags and Museum, and filters for Artist, Movement, Museum, Tags and Date Range, as `product-spec.md` lists. Notes are never searched. Search covers only the user's own artworks, because the spec excludes global community search. Document it in `openapi.yaml`.

## 15. Discoverability API
Goal: A user can make an artwork discoverable, and separately make its notes discoverable.
Description: Add endpoints to switch `is_discoverable` and `are_notes_discoverable` on and off, and document them in `openapi.yaml`. Making an artwork discoverable is refused unless its title, artist and date are all set; a photo is not required. Both settings start as private.

## 16. Relationship exploration API (artist, subject, movement, museum)
Goal: From one artwork, a user can list other artworks with the same artist, subject, movement or museum.
Description: Add an exploration endpoint and document it in `openapi.yaml`, using the mapping in `docs/database-schema.md` under Relationship Exploration Mapping. Results come from the user's collection by default; watchlist and community results are included only when asked for. Community results come only from discoverable artworks and show only the fields listed under Community Visibility, never photos or private notes.

## 17. Shared tags exploration API
Goal: A user can find artworks that carry all of a chosen set of tags.
Description: Extend relationship exploration with Shared Tags, where results must match every selected tag (battle + horse + armor). It uses the same sources (collection by default; watchlist and community on request) and the same community privacy rules as the other exploration modes. Document it in `openapi.yaml`.

## 18. Photo preparation in the browser
Goal: Before any photo is uploaded, the browser shrinks it and converts it to JPEG.
Description: Build one shared frontend piece that every photo upload uses, following `product-spec.md` under Photos: originals up to 30 MB, any image the browser can open, shrunk to about 2,500 pixels on the longest side and saved as JPEG. The photo keeps the right orientation, and hidden location data is not kept. Files the browser cannot open are refused with a message saying the file type is not supported.

## 19. Collection screen
Goal: A logged-in user sees their collection as a grid of cards and can switch to a list.
Description: Build the Collection screen from `docs/architecture.md` using the artwork list API. Grid is the default, list is the alternative, items are sorted Recently Added and paginated at 50. Each card shows the artwork photo, title, artist and date and opens the Artwork page.

## 20. Create artwork form
Goal: A user can add an artwork to their collection or watchlist from the browser.
Description: Build a form with the fields from `product-spec.md` under Artwork Structure. Artist, Movement, Subject and Tags each offer "select existing or create new". With a photo the artwork goes to the collection; without one, to the watchlist. A duplicate warning from the API is shown, and the user can still save. Photos are prepared before upload as `product-spec.md` describes under Photos.

## 21. Artwork page
Goal: A user can view one of their artworks and use every action the spec lists for it.
Description: Build the Artwork page from `product-spec.md`. It shows the main photo, identity fields, metadata, tags, notes and detail photos. It offers replacing the artwork photo, adding, viewing and deleting detail photos, editing metadata and notes, and deleting the artwork after a confirmation. Photos are prepared before upload as `product-spec.md` describes under Photos.

## 22. Watchlist screen
Goal: A user can see their watchlist and move an artwork into the collection by uploading its photo.
Description: Build the Watchlist screen listed in `docs/architecture.md`, showing the user's WATCHLIST artworks. Each one offers an upload-photo action; after the upload, the artwork disappears from the watchlist and appears in the collection. Photos are prepared before upload as `product-spec.md` describes under Photos.

## 23. Search and filters screen
Goal: A user can search and filter their artworks from the browser.
Description: Build the Search Results screen listed in `docs/architecture.md` using the search and filter API. It provides a search box plus filters for Artist, Movement, Museum, Tags and Date Range. An empty result shows a clear "nothing found" message.

## 24. Discoverability controls
Goal: A user can switch an artwork's discoverability and its notes' discoverability from the Artwork page.
Description: Add two separate switches to the Artwork page, both starting as private. If the API refuses discoverability because title, artist or date is missing, the page says which fields are missing.

## 25. Relationship exploration screen
Goal: From an artwork, a user can explore related artworks by artist, subject, movement, museum or shared tags.
Description: Add an Explore Relationships action to the Artwork page that shows matching artworks for the chosen relationship. The user can narrow tag exploration one tag at a time (battle → battle + horse → battle + horse + armor) and switch watchlist and community results on or off. Community results show metadata only, never photos.

## 26. Integration tests for the main journeys
Goal: Automated tests prove the main user journeys work end to end against a real database.
Description: Write integration tests through the API for the journeys named in `docs/observability.md`: authentication, create artwork, watchlist-to-collection conversion, relationship exploration and enabling discoverability. They also check privacy: another user can never see photos, detail photos or private notes.

## 27. Single container
Goal: The whole application runs from one Docker container, with the frontend at `/` and the API at `/api`.
Description: Package the frontend and backend into one container image, as `docs/architecture.md` decides under Deployment Shape. Database address, photo storage keys and similar settings come from environment variables, never from the image. The README explains how to build and run it locally against a PostgreSQL database.

## 28. Continuous integration
Goal: Every push to GitHub runs all tests automatically and shows pass or fail.
Description: Set up an automated pipeline that installs the project, runs the backend, frontend and integration tests, and builds the container image on every push and pull request. A failing test marks the run as failed.

## 29. Deployment
Goal: The application is live on a public URL and updates when changes land on `main`.
Description: Deploy the container and a PostgreSQL database, connect them to Cloudflare R2, and make deployment run automatically after tests pass on `main`. The live site supports registering, logging in and creating an artwork. The README records the URL and how deployment works.

## 30. Telemetry (metrics, logs, traces)
Goal: The backend emits metrics, logs and traces through OpenTelemetry.
Description: Add OpenTelemetry to the backend so it emits request count, latency and errors, logs for the events listed in `docs/observability.md`, and traces for the listed workflows. Every signal carries environment and deployment version labels. Passwords, session cookies and other sensitive data are never logged.

## 31. User-impact metrics
Goal: The backend counts the five dashboard metrics from the spec.
Description: Emit Active Users, Artworks Created, Relationship Explorations, Discoverable Artworks and Watchlist Conversions, using the definitions in `docs/observability.md`. Artworks Created counts new collection artworks only, not edits. Tests check that each metric changes when its action happens.

## 32. Observability stack and dashboard
Goal: Operators can view the five user-impact metrics, logs and traces in Grafana.
Description: Run the stack from `docs/observability.md` (OpenTelemetry Collector, Prometheus, Loki, Tempo, Grafana) and connect the application to it. Build a Grafana dashboard showing the five user-impact metrics, request errors and latency. The setup is saved in the repository so it can be recreated.

## 33. Artwork creation failure alert
Goal: An alert fires when artwork creation starts failing.
Description: Define the primary alert, Artwork Creation Failure Rate, from `docs/observability.md` in the observability stack. The alert includes or links to the deployment version and the related logs and traces. Show it working by forcing creation failures in a test environment.

## 34. Responder agent
Goal: When the alert fires, an agent produces a read-only investigation report.
Description: Build the responder agent from `docs/observability.md`. It reads metrics, logs, traces and the deployment version, and writes an investigation summary, a root cause hypothesis and a recommended remediation. It is read-only: it cannot deploy, roll back, change infrastructure or change data.
