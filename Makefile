# Shortcuts for running the backend and the frontend locally. See README.md for the setup they rely on.
# The database port defaults to 5433 (the local server); override it per call, e.g. `make run DB_PORT=5432`.

DB_PORT ?= 5433
DATABASE_URL ?= postgresql+psycopg://artmneme:artmneme@localhost:$(DB_PORT)/artmneme
TEST_DATABASE_URL ?= postgresql+psycopg://artmneme:artmneme@localhost:$(DB_PORT)/artmneme_test
PHOTO_DIR ?= $(CURDIR)/backend/photos
export DATABASE_URL TEST_DATABASE_URL PHOTO_DIR

.PHONY: run install migrate test frontend integration deploy-stack build deploy e2e deploy-ci-role observability observability-down

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
	cd frontend && npm run dev

# Start docker-compose.yaml under its own name, port and empty volumes, run the integration tests, then remove it all.
integration: export COMPOSE_PROJECT_NAME = artmneme-integration
integration: export APP_PORT = 8092
integration: export INTEGRATION_URL = http://localhost:8092
integration:
	docker compose down -v
	docker compose up -d --build
	cd backend && uv run pytest integration; status=$$?; cd .. && docker compose down -v; exit $$status

# The same, with a browser: run the end-to-end tests in e2e/ against the stack on port 8093.
e2e: export COMPOSE_PROJECT_NAME = artmneme-e2e
e2e: export APP_PORT = 8093
e2e: export E2E_URL = http://localhost:8093
e2e:
	docker compose down -v
	docker compose up -d --build
	cd backend && uv run pytest ../e2e; status=$$?; cd .. && docker compose down -v; exit $$status

# Create or update the AWS stack (deploy/cloudformation.yaml). Needs the AWS CLI configured; see README.md.
deploy-stack:
	aws cloudformation deploy --template-file deploy/cloudformation.yaml --stack-name artmneme --capabilities CAPABILITY_IAM
	aws cloudformation describe-stacks --stack-name artmneme --query "Stacks[0].Outputs" --output table

# Build stage: build the committed version, push it to ECR (YYYYMMDD-HHMMSS-shortsha) and tag it dev.
build:
	deploy/build.sh

# Deploy stage: start the image tagged dev on the server, or a given one: `make deploy TAG=20261026-163457-452bc20`.
deploy:
	deploy/deploy.sh $(TAG)

# Create or update the AWS role that GitHub Actions deploys with (deploy/github-oidc.yaml), for the production environment.
deploy-ci-role:
	aws cloudformation deploy --template-file deploy/github-oidc.yaml --stack-name artmneme-github-production --capabilities CAPABILITY_IAM
	aws cloudformation describe-stacks --stack-name artmneme-github-production --query "Stacks[0].Outputs" --output table

# Local observability stack (observability/): Collector, Prometheus, Loki, Tempo, Grafana at http://localhost:3000.
observability:
	docker compose -f observability/docker-compose.yaml up -d

observability-down:
	docker compose -f observability/docker-compose.yaml down
