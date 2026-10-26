"""OpenTelemetry for the backend: a trace and HTTP metrics for every request, plus the application metrics
below, and structured logs, sent with OTLP over HTTP.

Logs: the logger "artmneme" writes one JSON object per line to stdout, with the trace_id and span_id of the
current request, and sends the same records to the OTLP endpoint (where they carry the trace context too).
Log records hold no customer data: no email, password, title, note or search text; only IDs, states and codes.

Every span and metric carries service.name, service.version (APP_VERSION: the image tag, set at build time)
and deployment.environment.name (DEPLOYMENT_ENVIRONMENT; "dev" when not set, i.e. on a developer's computer). Nothing is sent unless
OTEL_EXPORTER_OTLP_ENDPOINT is set, e.g. http://localhost:4318 for a local OpenTelemetry Collector.
"""

import json
import logging
import os
import sys
from collections.abc import Iterable

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = "artmneme-backend"
ACTIVE_MINUTES = 15

log = logging.getLogger("artmneme")
# Attributes every LogRecord has; anything else on a record came from `extra=` and goes into the JSON line.
STANDARD_ATTRIBUTES = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the trace and span of the current request (null outside a request)."""

    def format(self, record: logging.LogRecord) -> str:
        context = trace.get_current_span().get_span_context()
        entry = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": format(context.trace_id, "032x") if context.is_valid else None,
            "span_id": format(context.span_id, "016x") if context.is_valid else None,
            **{key: value for key, value in vars(record).items() if key not in STANDARD_ATTRIBUTES},
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)

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
            "deployment.environment.name": os.environ.get("DEPLOYMENT_ENVIRONMENT", "dev"),
        }
    )


def instrument(app: FastAPI, extra_readers: Iterable[MetricReader] = ()) -> TracerProvider:
    """Traces, metrics and logs for every request to `app`; returns the tracer provider (tests read spans from it).
    `extra_readers` lets tests read the metrics."""
    global artworks_created, artwork_creation_failures, photos_uploaded, relationship_explorations
    tracer_provider = TracerProvider(resource=resource())
    readers = list(extra_readers)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(JsonFormatter())
    log.handlers = [stdout]
    log.setLevel(logging.INFO)
    log.propagate = False
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
        logger_provider = LoggerProvider(resource=resource())
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        log.addHandler(LoggingHandler(logger_provider=logger_provider))
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
    # Report every label value as 0 at start: Prometheus' increase() cannot see a first sample that is already 1.
    for counter, label, values in (
        (artworks_created, "state", ("COLLECTION", "WATCHLIST")),
        (artwork_creation_failures, "reason", ("invalid", "storage", "error")),
        (photos_uploaded, "kind", ("create", "replace", "watchlist_conversion")),
        (relationship_explorations, "by", ("artist", "subject", "movement", "museum")),
    ):
        for value in values:
            counter.add(0, {label: value})
    meter.create_observable_gauge(
        "artmneme.users.active", callbacks=[active_users], description=f"Users active in the last {ACTIVE_MINUTES} minutes"
    )
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider)
    return tracer_provider
