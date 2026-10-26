# Shortcuts for running the backend locally. See README.md for the setup they rely on.
# The database port defaults to 5432; override it once with `export DB_PORT=5433` or per call: `make run DB_PORT=5433`.

DB_PORT ?= 5432
DATABASE_URL ?= postgresql+psycopg://artmneme:artmneme@localhost:$(DB_PORT)/artmneme
TEST_DATABASE_URL ?= postgresql+psycopg://artmneme:artmneme@localhost:$(DB_PORT)/artmneme_test
PHOTO_DIR ?= $(CURDIR)/backend/photos
export DATABASE_URL TEST_DATABASE_URL PHOTO_DIR

.PHONY: run install migrate test

# Install, bring the schema up to date, and start the API at http://localhost:8000/api
run: install migrate
	cd backend && uv run uvicorn main:app --port 8000

install:
	cd backend && uv sync

migrate:
	cd backend && uv run alembic upgrade head

test:
	cd backend && uv run pytest
