# ArtMneme Observability

## Purpose

Observability exists to detect user impact quickly, investigate incidents efficiently, and support operational decision-making.

ArtMneme focuses on user-centric observability rather than infrastructure-only monitoring.

The goal is to answer:

```text
Are users successfully using the application?
```

rather than:

```text
Is CPU utilization high?
```

Infrastructure metrics remain useful but are not sufficient on their own.

---

# Observability Goals

ArtMneme should enable operators to:

```text
Observe
Detect
Investigate
Respond
```

to production issues.

The observability stack must provide:

```text
Metrics
Logs
Traces
```

for all critical user journeys.

---

# User Impact Monitoring

ArtMneme prioritizes monitoring actions that directly affect users.

Critical user journeys include:

```text
Create Artwork

Convert Watchlist → Collection

Explore Relationships

Authentication
```

---

# Dashboard Metrics

The following application-level metrics should be displayed in Grafana.

---

## Active Users

Definition:

```text
Authenticated users actively interacting with ArtMneme.
```

Purpose:

```text
Understand platform usage.
```

---

## Artworks Created

Definition:

```text
Number of artworks created.
```

Includes:

```text
Collection artworks.
```

Excludes:

```text
Metadata edits.
```

Purpose:

```text
Primary collection growth metric.
```

---

## Watchlist Conversions

Definition:

```text
Number of WATCHLIST artworks converted into COLLECTION artworks.
```

Purpose:

```text
Measure successful real-world encounters.
```

---

## Relationship Explorations

Definition:

```text
Relationship exploration requests.
```

Includes:

```text
Same Artist
Same Subject
Same Movement
Same Museum
Shared Tags
```

Shared Tags comes in a later version.

Purpose:

```text
Measure engagement with the application's core differentiator.
```

---

## Discoverable Artworks

Not part of v1: added with community in a later version.

Definition:

```text
Number of artworks marked discoverable.
```

Purpose:

```text
Measure participation in the community metadata layer.
```

---

# Infrastructure Metrics

System metrics remain valuable.

Examples:

```text
CPU Usage

Memory Usage

Request Volume

Database Connections
```

These help explain incidents but are not considered user-impact metrics.

---

# Telemetry

ArtMneme collects:

```text
Metrics
Logs
Traces
```

using OpenTelemetry.

Implemented (2026-10-26): `backend/telemetry.py` traces every request and records the HTTP metrics (request count, duration, errors) through the FastAPI instrumentation, sent with OTLP over HTTP to `OTEL_EXPORTER_OTLP_ENDPOINT`. Every span and metric carries:

```text
service.name                  artmneme-backend
deployment.environment.name   prod (AWS) or local
service.version               the image tag, e.g. 20261026-155049-1ae1c7e
```

Not yet: logs through OpenTelemetry, and the business metrics (Artworks Created, Relationship Explorations, Watchlist Conversions).

---

# Metrics

Collected examples:

```text
Request Count

Request Latency

Request Errors

Artworks Created

Relationship Explorations

Watchlist Conversions
```

Metrics should include labels such as:

```text
Environment

Deployment Version
```

whenever possible.

---

# Logs

Logs capture discrete events.

Examples:

```text
Authentication Failure

Authorization Failure

Artwork Creation Failure

Database Exception

Unexpected Application Error
```

Logs must contain sufficient context for incident investigation.

Sensitive data must not be logged.

---

# Traces

Traces capture complete request lifecycles.

Important traced workflows:

```text
Create Artwork

Update Artwork

Convert Watchlist → Collection

Explore Relationships
```

Enable Discoverability is added with community in a later version.

Each workflow should be traceable end-to-end.

---

# Alerting

Alerts should represent real user impact.

---

## Primary Alert

```text
Artwork Creation Failure Rate
```

Reason:

```text
Creating artworks is the most critical user workflow.
```

If artwork creation breaks:

```text
Users cannot use the primary functionality of the application.
```

Fires when:

```text
Any artwork creation fails within the last 15 minutes.
```

Only the application's own failures count, such as a server error, an unavailable database or unreachable photo storage.

User input errors, such as a missing required photo or an invalid tag, do not count.

---

## Alert Inputs

Alert investigation should have immediate access to:

```text
Metrics

Logs

Traces

Deployment Version
```

to reduce diagnosis time.

---

# Responder Agent

## Purpose

Assist investigation after alerts fire.

The responder agent is:

```text
Read-only
```

and advisory.

---

## Inputs

```text
Metrics

Logs

Traces

Deployment Metadata
```

---

## Responsibilities

The responder agent may:

```text
Summarize incidents

Identify likely root causes

Highlight suspicious patterns

Recommend remediation steps
```

---

## Restrictions

The responder agent must not:

```text
Deploy code

Rollback deployments

Modify infrastructure

Change production data
```

Human approval is always required.

---

# Observability Stack

Planned stack:

```text
Application
    ↓
OpenTelemetry
    ↓
OpenTelemetry Collector
    ↓
Prometheus
Loki
Tempo
    ↓
Grafana
```

---

# Metrics Storage

```text
Prometheus
```

Stores:

```text
Application Metrics
Infrastructure Metrics
```

---

# Log Storage

```text
Loki
```

Stores:

```text
Application Logs
```

---

# Trace Storage

```text
Tempo
```

Stores:

```text
Distributed Traces
```

---

# Visualization

```text
Grafana
```

Provides:

```text
Dashboards

Operational Views

Alert Visibility
```

---

# Future Enhancements

Potential future additions:

```text
Additional User-Journey Alerts

Anomaly Detection

Responder-Agent Improvements

Automated Incident Classification
```

These enhancements are out of scope for v1.