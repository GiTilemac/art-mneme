# Shortcuts for running the backend and the frontend locally. See README.md for the setup they rely on.
# The database port defaults to 5433 (the local server); override it per call, e.g. `make run DB_PORT=5432`.

DB_PORT ?= 5433
DATABASE_URL ?= postgresql+psycopg://artmneme:artmneme@localhost:$(DB_PORT)/artmneme
TEST_DATABASE_URL ?= postgresql+psycopg://artmneme:artmneme@localhost:$(DB_PORT)/artmneme_test
PHOTO_DIR ?= $(CURDIR)/backend/photos
export DATABASE_URL TEST_DATABASE_URL PHOTO_DIR

.PHONY: run install migrate test frontend

# Install, bring the schema up to date, and start the API at http://localhost:8000/api
run: install migrate
	cd backend && uv run uvicorn main:app --port 8000

install:
	cd backend && uv sync

migrate:
	cd backend && uv run alembic upgrade head

test:
	cd backend && uv run pytest

# Start the frontend (in a second terminal, while `make run` is running); it passes /api calls to the backend.
frontend:
	cd frontend && npm install && npm run dev
