# Observability Guide

This document describes Troostwatch's observability strategy: logging, metrics,
and (optionally) tracing.

## Goals

Troostwatch observability aims to:

1. **Debug failures quickly** – Identify issues in sync runs, bidding operations,
   and API requests with contextual logs.
2. **Monitor health** – Track whether the live runner is active, how long sync
   runs take, and API latency/error rates.
3. **Support both local and production** – Provide useful output during
   development while enabling integration with external monitoring in
   semi-production scenarios.

## Critical Flows

The following flows are instrumented with logging and (where applicable) metrics:

| Flow | Description | Key Context Fields |
|------|-------------|-------------------|
| **Sync run** | Auction ingest → lots/buyers in DB | `auction_code`, `sync_run_id` |
| **Bidding** | Place bid + confirmation | `lot_id`, `buyer_id`, `amount` |
| **API requests** | HTTP endpoints for lots, buyers, filters | `request_id`, `endpoint`, `method` |
| **Live runner** | Long-running sync with WebSocket updates | `auction_code`, `interval` |
| **CLI commands** | User-initiated operations | `command`, `args` |

## Logging

### Configuration

Logging is configured centrally in `troostwatch/infrastructure/observability/`.
Call `configure_logging()` at application startup (CLI or API) to apply
consistent settings.

```python
from troostwatch.infrastructure.observability import configure_logging

configure_logging()  # INFO for app loggers, WARNING for third-party
```

### Log Levels

| Level | Use Case |
|-------|----------|
| `DEBUG` | Detailed diagnostics (disabled by default) |
| `INFO` | Normal operation events (sync started, request received) |
| `WARNING` | Recoverable issues (retry, missing optional field) |
| `ERROR` | Failures requiring attention (sync failed, bid rejected) |

### Contextual Logging

Use `LogContext` to attach domain-specific fields to log messages:

```python
from troostwatch.infrastructure.observability import get_logger, LogContext

logger = get_logger(__name__)

with LogContext(auction_code="ABC123", sync_run_id=42):
    logger.info("Starting sync")  # Includes auction_code and sync_run_id
```

### Logging Guidelines by Layer

**Services layer** (`troostwatch/services/`):
- Log start and end of significant operations with context IDs
- Log errors with exception details
- Avoid logging in tight loops

**Infrastructure layer** (`troostwatch/infrastructure/`):
- Log HTTP errors and retries with target URL
- Log database errors with operation context
- Keep logs concise; avoid verbose payloads

**API/CLI layer** (`troostwatch/app/`, `troostwatch/interfaces/cli/`):
- Log request/command receipt at INFO level
- Log completion with status/exit code
- Use shared observability helpers

## Metrics

### Current Metrics

Metrics are collected via simple in-process counters in
`troostwatch/infrastructure/observability/metrics.py`. No external dependencies
are required for basic operation.

| Metric | Type | Description |
|--------|------|-------------|
| `api_requests_total` | Counter | Requests by endpoint and status code |
| `api_request_duration_seconds` | Histogram | Request latency by endpoint |
| `sync_runs_total` | Counter | Sync runs by status (success/failed) |
| `sync_run_duration_seconds` | Histogram | Duration of sync runs |
| `sync_lots_processed` | Counter | Lots synced per run |
| `bids_total` | Counter | Bid attempts by outcome |
| `image_downloads_total` | Counter | Image downloads by status |
| `image_download_duration_seconds` | Histogram | Download latency |
| `image_downloads_bytes_total` | Counter | Total bytes downloaded |
| `image_analysis_total` | Counter | Analyses by backend and status |
| `image_analysis_duration_seconds` | Histogram | Analysis latency by backend |
| `extracted_codes_total` | Counter | Codes extracted by backend |
| `code_approvals_total` | Counter | Approvals by type and code type |

### Accessing Metrics

For local debugging, metrics can be logged or printed. If a `/metrics` endpoint
is enabled in the API, it exposes Prometheus-compatible text format.

### Adding New Metrics

Use the helpers in the metrics module:

```python
from troostwatch.infrastructure.observability.metrics import (
    increment_counter,
    observe_histogram,
)

increment_counter("bids_total", labels={"outcome": "success"})
observe_histogram("sync_run_duration_seconds", duration, labels={"auction": code})
```

### Image Pipeline Metrics

The image analysis pipeline has dedicated metrics for monitoring OCR operations:

```python
from troostwatch.infrastructure.observability.metrics import (
    record_image_download,
    record_image_analysis,
    record_code_approval,
    get_image_pipeline_stats,
)

# Record a download (automatically called by ImageAnalysisService)
record_image_download("success", duration_seconds, bytes_downloaded)

# Record an analysis operation
record_image_analysis("local", "success", duration_seconds, codes_extracted=3)

# Record code approval events
record_code_approval("auto", "ean")
record_code_approval("manual", "serial_number")

# Get summary statistics for dashboards
stats = get_image_pipeline_stats()
# {
#     "downloads": {"success": 150, "failed": 5},
#     "analysis": {"local_success": 120, "local_review": 25, "local_failed": 5},
#     "codes_extracted": {"local": 280, "openai": 15},
#     "approvals": {"auto": 240, "manual": 30, "rejected": 10}
# }
```

## Tracing

Distributed tracing is available via OpenTelemetry. Tracing is **optional** and
disabled by default. Install the tracing extras to enable:

```bash
pip install troostwatch[tracing]
```

### Configuration

Configure tracing at application startup:

```python
from troostwatch.infrastructure.observability import configure_tracing

# Enable tracing with OTLP exporter
configure_tracing(
    service_name="troostwatch-api",
    endpoint="http://localhost:4317",  # Jaeger/Tempo OTLP endpoint
    sample_rate=1.0,  # Sample all traces (reduce in production)
)
```

Environment variables:
- `OTEL_EXPORTER_OTLP_ENDPOINT`: Default OTLP endpoint
- `OTEL_TRACES_CONSOLE=true`: Print traces to console (debugging)

### Using Traces

```python
from troostwatch.infrastructure.observability import trace_span, traced

# Context manager for spans
with trace_span("sync_auction", auction_code="ABC123"):
    # ... operation ...

# Decorator for functions
@traced("fetch_lot_details")
async def fetch_lot_details(lot_id: int) -> LotDetail:
    ...

# Add events and attributes to current span
from troostwatch.infrastructure.observability import add_span_event, set_span_attribute

add_span_event("page_fetched", page=1, lots=25)
set_span_attribute("total_lots", 150)
```

### Log Correlation

When tracing is enabled, trace and span IDs are available for log correlation:

```python
from troostwatch.infrastructure.observability import get_trace_context

ctx = get_trace_context()
# {"trace_id": "abc123...", "span_id": "def456..."}
```

### Viewing Traces

Export traces to:
- **Jaeger**: `http://localhost:16686` (default UI)
- **Grafana Tempo**: Via Grafana datasource
- **Console**: Set `OTEL_TRACES_CONSOLE=true` for debugging

## Dashboards

When metrics are exported to Prometheus/Grafana, use the reference dashboard
in `docs/grafana_dashboard.md`. The dashboard includes:

| Row | Panels |
|-----|--------|
| **API Health** | Requests/sec, error rate (%), p95 latency, latency distribution |
| **Sync Operations** | Success/failure counts, success rate gauge, avg duration, lots/hour |
| **Bidding Activity** | Bids/hour by outcome, success rate gauge, daily volume, by-auction breakdown |

### Recommended Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighAPIErrorRate | 5xx rate > 5% for 5m | Critical |
| SyncFailures | >3 failures in 1h | Warning |
| HighAPILatency | p95 > 2s for 10m | Warning |
| NoSyncActivity | No syncs in 2h | Warning |

See `docs/grafana_dashboard.md` for the full dashboard JSON and Prometheus
scrape configuration.

## Integration with Agents

| Agent | Responsibility |
|-------|---------------|
| `observability_agent` | Owns logging config, context helpers, metrics module |
| `services_agent` | Calls observability hooks at operation boundaries |
| `api_agent` / `cli_agent` | Uses shared helpers for request/command logging |
| `test_agent` | May add tests verifying important paths emit logs/metrics |

## Periodic Review

Quarterly, review:

- Are logs still useful or too verbose?
- Which metrics are actively used?
- Are there new flows needing instrumentation?

Adjust configuration and remove unused metrics to keep observability lean.
