"""Structured logs: JSON lines that share the trace ID of their request and hold no customer data."""

import io
import json
import logging

import pytest
from fastapi.testclient import TestClient
from test_artworks import JPEG, folder, post, user  # noqa: F401
from test_auth import login
from test_telemetry import spans  # noqa: F401

import photos
import telemetry
from main import app


@pytest.fixture
def logs():
    """The JSON lines the app logs during the test."""
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(telemetry.JsonFormatter())
    telemetry.log.addHandler(handler)
    yield lambda: [json.loads(line) for line in output.getvalue().splitlines()]
    telemetry.log.removeHandler(handler)


def test_a_request_is_logged_with_the_trace_id_of_its_request(spans, logs):
    TestClient(app).get("/api/health")

    entry = next(entry for entry in logs() if entry["message"] == "request")
    server_span = next(span for span in spans.get_finished_spans() if span.attributes.get("http.route") == "/api/health")
    assert entry["trace_id"] == format(server_span.context.trace_id, "032x")
    assert (entry["route"], entry["status"]) == ("/api/health", 200)


def test_a_failed_creation_is_logged_with_its_reason_and_the_error(user, logs, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(photos, "save", fail)
    client = TestClient(app, base_url="https://testserver", cookies=user.cookies, raise_server_exceptions=False)

    post(client, {}, photo=JPEG)

    entry = next(entry for entry in logs() if entry["message"] == "artwork creation failed")
    assert (entry["level"], entry["reason"]) == ("ERROR", "error")
    assert "disk on fire" in entry["exception"]
    assert entry["trace_id"]


def test_logs_hold_no_email_password_title_or_search_text(user, logs):
    login(user, "ana@example.com", "password1")
    post(user, {"title": "Secret Garden", "notes": "private note"}, photo=JPEG)
    user.get("/api/artworks", params={"q": "hidden search"})

    text = json.dumps(logs())
    for private in ("ana@example.com", "password1", "Secret Garden", "private note", "hidden search"):
        assert private not in text
    assert any(entry["message"] == "artwork created" for entry in logs())
