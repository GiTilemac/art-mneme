"""Application metrics: artworks created, creation failures, photos uploaded, explorations, active users."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from sqlalchemy import text
from test_artworks import JPEG, folder, post, user, watch  # noqa: F401
from test_auth import device

import photos
import telemetry
from main import app

COUNTERS = ("artworks_created", "artwork_creation_failures", "photos_uploaded", "relationship_explorations")


class Recorder:
    def __init__(self):
        self.calls = []

    def add(self, amount, attributes=None):
        self.calls.append((amount, attributes))


@pytest.fixture
def recorded(monkeypatch):
    """Each counter replaced by a recorder, so a test sees exactly what was counted."""
    recorders = {name: Recorder() for name in COUNTERS}
    for name, recorder in recorders.items():
        monkeypatch.setattr(telemetry, name, recorder)
    return recorders


def test_a_created_artwork_and_its_photo_are_counted(user, recorded):
    post(user, {}, photo=JPEG)
    watch(user, {})

    assert recorded["artworks_created"].calls == [(1, {"state": "COLLECTION"}), (1, {"state": "WATCHLIST"})]
    assert recorded["photos_uploaded"].calls == [(1, {"kind": "create"})]
    assert recorded["artwork_creation_failures"].calls == []


@pytest.mark.parametrize("reason", ["invalid", "storage", "error"])
def test_a_failed_creation_is_counted_with_its_reason(user, recorded, monkeypatch, reason):
    def fail(*args, **kwargs):
        raise {"storage": photos.StorageUnavailable, "error": RuntimeError}[reason]

    if reason != "invalid":
        monkeypatch.setattr(photos, "save", fail)
    client = TestClient(app, base_url="https://testserver", cookies=user.cookies, raise_server_exceptions=False)

    response = post(client, {}, state="DONE" if reason == "invalid" else None, photo=JPEG)

    assert response.status_code == {"invalid": 422, "storage": 503, "error": 500}[reason]
    assert recorded["artwork_creation_failures"].calls == [(1, {"reason": reason})]
    assert recorded["artworks_created"].calls == []


def test_a_request_without_login_is_not_a_creation_attempt(client, recorded):
    assert post(device(), {}, photo=JPEG).status_code == 401
    assert recorded["artwork_creation_failures"].calls == []


def test_a_photo_upload_is_counted_as_conversion_or_replacement(user, recorded):
    artwork = watch(user, {}).json()
    upload = {"photo": ("p.jpg", JPEG, "image/jpeg")}

    user.put(f"/api/artworks/{artwork['id']}/photo", files=upload)
    user.put(f"/api/artworks/{artwork['id']}/photo", files=upload)

    assert recorded["photos_uploaded"].calls == [(1, {"kind": "watchlist_conversion"}), (1, {"kind": "replace"})]


def test_an_exploration_is_counted_with_its_dimension(user, recorded):
    artwork = watch(user, {}).json()

    user.get(f"/api/artworks/{artwork['id']}/related", params={"by": "museum"})
    user.get(f"/api/artworks/{artwork['id']}/related", params={"by": "nonsense"})

    assert recorded["relationship_explorations"].calls == [(1, {"by": "museum"})]


def test_active_users_are_those_with_a_request_in_the_last_15_minutes(client, user, conn):
    def session(user_id, minutes_ago):
        conn.execute(
            text(
                "INSERT INTO sessions (user_id, token_hash, expires_at) "
                "VALUES (:u, md5(random()::text), now() + interval '30 days' - make_interval(mins => :m))"
            ),
            {"u": user_id, "m": minutes_ago},
        )

    me = user.get("/api/auth/me").json()["id"]  # this request makes the user active now
    other = conn.execute(text("INSERT INTO users (email, password_hash) VALUES ('b@example.com', 'x') RETURNING id")).scalar()
    away = conn.execute(text("INSERT INTO users (email, password_hash) VALUES ('c@example.com', 'x') RETURNING id")).scalar()
    session(me, 1)  # a second session of the same user counts once
    session(other, 14)
    session(away, 16)

    assert telemetry.count_active_users(conn) == 2


def test_metrics_are_exported_with_their_names_and_the_deployment_attributes(monkeypatch):
    for name in COUNTERS:  # instrument() replaces the counters; put the app's back afterwards
        monkeypatch.setattr(telemetry, name, getattr(telemetry, name))
    monkeypatch.setenv("APP_VERSION", "20261026-155049-1ae1c7e")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(telemetry, "active_users", lambda options: [Observation(3)])  # no database here
    reader = InMemoryMetricReader()
    telemetry.instrument(FastAPI(), extra_readers=[reader])

    telemetry.artworks_created.add(1, {"state": "COLLECTION"})
    telemetry.artwork_creation_failures.add(1, {"reason": "invalid"})
    telemetry.photos_uploaded.add(1, {"kind": "create"})
    telemetry.relationship_explorations.add(1, {"by": "artist"})

    resource_metrics = reader.get_metrics_data().resource_metrics[0]
    names = {metric.name for scope in resource_metrics.scope_metrics for metric in scope.metrics}
    assert {
        "artmneme.artworks.created",
        "artmneme.artworks.creation_failures",
        "artmneme.photos.uploaded",
        "artmneme.relationship.explorations",
        "artmneme.users.active",
    } <= names
    attributes = resource_metrics.resource.attributes
    assert (attributes["service.version"], attributes["deployment.environment.name"]) == ("20261026-155049-1ae1c7e", "prod")


def test_the_fault_switch_makes_creation_fail_as_a_server_error(user, recorded, monkeypatch):
    monkeypatch.setenv("ARTMNEME_FAULT", "artwork-creation")
    client = TestClient(app, base_url="https://testserver", cookies=user.cookies, raise_server_exceptions=False)

    assert post(client, {}, photo=JPEG).status_code == 500
    assert recorded["artwork_creation_failures"].calls == [(1, {"reason": "error"})]

    monkeypatch.delenv("ARTMNEME_FAULT")
    assert post(client, {}, photo=JPEG).status_code == 201
