"""OpenTelemetry: every request is traced, with service name, environment and deployed version."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import telemetry
from main import app, tracer_provider


@pytest.fixture
def spans():
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter
    exporter.clear()


def test_a_request_is_traced_with_service_environment_and_version(spans):
    assert TestClient(app).get("/api/health").status_code == 200

    server_span = next(span for span in spans.get_finished_spans() if span.attributes.get("http.route") == "/api/health")
    assert server_span.resource.attributes["service.name"] == "artmneme-backend"
    assert {"deployment.environment.name", "service.version"} <= set(server_span.resource.attributes)


def test_environment_and_version_come_from_the_deployment(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "20261026-155049-1ae1c7e")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")

    attributes = telemetry.resource().attributes

    assert (attributes["service.version"], attributes["deployment.environment.name"]) == ("20261026-155049-1ae1c7e", "prod")


def test_without_settings_the_version_is_unknown_and_the_environment_local(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("DEPLOYMENT_ENVIRONMENT", raising=False)

    attributes = telemetry.resource().attributes

    assert (attributes["service.version"], attributes["deployment.environment.name"]) == ("unknown", "local")


def test_nothing_is_sent_without_an_otlp_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    provider = telemetry.instrument(FastAPI())

    assert provider._active_span_processor._span_processors == ()
