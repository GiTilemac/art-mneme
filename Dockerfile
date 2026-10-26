# One container: the backend serves the API at /api and the built frontend at /.
# Run with DATABASE_URL set, and PHOTO_DIR or the four R2 variables (see README.md).

# 1. Build the frontend as static files.
FROM node:22-slim AS frontend
RUN npm install -g bun@1.3.0
WORKDIR /frontend
COPY frontend/package.json frontend/bun.lock frontend/bunfig.toml ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
RUN npm run build

# 2. The backend, with the frontend's files.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY --from=frontend /frontend/.output/public /app/frontend
ENV FRONTEND_DIR=/app/frontend
# The deployed version for telemetry: deploy/build.sh passes the image tag. Last, so it does not undo the build cache.
ARG APP_VERSION=unknown
ENV APP_VERSION=$APP_VERSION
EXPOSE 8000
# Bring the database schema up to date, then start the server.
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn main:app --host 0.0.0.0 --port 8000"]
