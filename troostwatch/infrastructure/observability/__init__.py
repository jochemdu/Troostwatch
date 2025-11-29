"""Observability and logging facades."""

from .logging import (
    LogContext,
    configure_logging,
    get_logger,
    log_context,
    log_exception,
)
from .metrics import (
    Timer,
    format_prometheus,
    get_metrics_summary,
    increment_counter,
    observe_histogram,
    record_api_request,
    record_bid,
    record_sync_run,
)
from .tracing import (
    add_span_event,
    configure_tracing,
    get_trace_context,
    is_tracing_enabled,
    record_exception,
    set_span_attribute,
    trace_span,
    traced,
)

__all__ = [
    # Logging
    "LogContext",
    "configure_logging",
    "get_logger",
    "log_context",
    "log_exception",
    # Metrics
    "Timer",
    "format_prometheus",
    "get_metrics_summary",
    "increment_counter",
    "observe_histogram",
    "record_api_request",
    "record_bid",
    "record_sync_run",
    # Tracing
    "add_span_event",
    "configure_tracing",
    "get_trace_context",
    "is_tracing_enabled",
    "record_exception",
    "set_span_attribute",
    "trace_span",
    "traced",
]
