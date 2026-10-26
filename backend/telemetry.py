"""OpenTelemetry for the backend: a trace and HTTP metrics for every request, sent with OTLP over HTTP.

Every span and metric carries service.name, service.version (APP_VERSION: the image tag, set at build time)
and deployment.environment.name (DEPLOYMENT_ENVIRONMENT; "local" when not set). Nothing is sent unless
OTEL_EXPORTER_OTLP_ENDPOINT is set, e.g. http://localhost:4318 for a local OpenTelemetry Collector.
"""

import os

from fastapi import FastAPI
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = "artmneme-backend"


def resource() -> Resource:
    return Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": os.environ.get("APP_VERSION", "unknown"),
            "deployment.environment.name": os.environ.get("DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )


def instrument(app: FastAPI) -> TracerProvider:
    """Traces and metrics for every request to `app`; returns the tracer provider (tests read spans from it)."""
    tracer_provider = TracerProvider(resource=resource())
    readers = []
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
    meter_provider = MeterProvider(resource=resource(), metric_readers=readers)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider)
    return tracer_provider
