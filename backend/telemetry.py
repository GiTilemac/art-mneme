"""OpenTelemetry for the backend: a trace and HTTP metrics for every request, plus the application metrics
below, sent with OTLP over HTTP.

Every span and metric carries service.name, service.version (APP_VERSION: the image tag, set at build time)
and deployment.environment.name (DEPLOYMENT_ENVIRONMENT; "local" when not set). Nothing is sent unless
OTEL_EXPORTER_OTLP_ENDPOINT is set, e.g. http://localhost:4318 for a local OpenTelemetry Collector.
"""

import os
from collections.abc import Iterable

from fastapi import FastAPI
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = "artmneme-backend"
ACTIVE_MINUTES = 15

# Application metrics (docs/observability.md), set by instrument(). Labels: see where they are counted in main.py.
artworks_created = None  # label state: COLLECTION or WATCHLIST
artwork_creation_failures = None  # label reason: invalid (422), storage (503) or error
photos_uploaded = None  # label kind: create, replace or watchlist_conversion
relationship_explorations = None  # label by: artist, subject, movement or museum


def count_active_users(connection) -> int:
    """Users with a request in the last 15 minutes: every request renews the session to end 30 days later."""
    from sqlalchemy import text

    return connection.execute(
        text(
            "SELECT count(DISTINCT user_id) FROM sessions "
            "WHERE expires_at > now() + interval '30 days' - make_interval(mins => :minutes)"
        ),
        {"minutes": ACTIVE_MINUTES},
    ).scalar()


def active_users(options: CallbackOptions) -> Iterable[Observation]:
    from db import get_engine

    try:
        with get_engine().connect() as connection:
            return [Observation(count_active_users(connection))]
    except (Exception, SystemExit):  # No database: no value this time, and the app keeps running.
        return []


def resource() -> Resource:
    return Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": os.environ.get("APP_VERSION", "unknown"),
            "deployment.environment.name": os.environ.get("DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )


def instrument(app: FastAPI, extra_readers: Iterable[MetricReader] = ()) -> TracerProvider:
    """Traces and metrics for every request to `app`; returns the tracer provider (tests read spans from it).
    `extra_readers` lets tests read the metrics."""
    global artworks_created, artwork_creation_failures, photos_uploaded, relationship_explorations
    tracer_provider = TracerProvider(resource=resource())
    readers = list(extra_readers)
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
    meter_provider = MeterProvider(resource=resource(), metric_readers=readers)
    meter = meter_provider.get_meter("artmneme")
    artworks_created = meter.create_counter("artmneme.artworks.created", description="Artworks created")
    artwork_creation_failures = meter.create_counter(
        "artmneme.artworks.creation_failures", description="Failed artwork creations"
    )
    photos_uploaded = meter.create_counter("artmneme.photos.uploaded", description="Artwork photos stored")
    relationship_explorations = meter.create_counter(
        "artmneme.relationship.explorations", description="Relationship explorations"
    )
    meter.create_observable_gauge(
        "artmneme.users.active", callbacks=[active_users], description=f"Users active in the last {ACTIVE_MINUTES} minutes"
    )
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider)
    return tracer_provider
