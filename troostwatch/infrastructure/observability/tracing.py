"""OpenTelemetry tracing support for Troostwatch.

This module provides optional distributed tracing via OpenTelemetry.
Tracing is disabled by default and requires the opentelemetry packages
to be installed. When disabled, all tracing functions are no-ops.

Usage:
    from troostwatch.infrastructure.observability import configure_tracing, trace_span

    # At startup (e.g., FastAPI lifespan or CLI main)
    configure_tracing(service_name="troostwatch-api", endpoint="http://localhost:4317")

    # In code
    with trace_span("sync_auction", auction_code=code):
        # ... operation ...

    # Or as a decorator
    @traced("fetch_lot_details")
    async def fetch_lot_details(lot_id: int) -> LotDetail:
        ...
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterator, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Tracing state
# ---------------------------------------------------------------------------

_tracer: Any = None
_tracing_enabled: bool = False

# Context variable for trace/span IDs (used for log correlation)
_trace_context: ContextVar[dict[str, str]] = ContextVar(
    "trace_context", default={}
)


def is_tracing_enabled() -> bool:
    """Check if tracing is currently enabled."""
    return _tracing_enabled


def get_trace_context() -> dict[str, str]:
    """Get current trace context for log correlation."""
    return _trace_context.get()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def configure_tracing(
    *,
    service_name: str = "troostwatch",
    endpoint: str | None = None,
    enable: bool = True,
    sample_rate: float = 1.0,
) -> bool:
    """Configure OpenTelemetry tracing.

    Args:
        service_name: Name of this service in traces.
        endpoint: OTLP endpoint URL (e.g., "http://localhost:4317").
                  If None, uses OTEL_EXPORTER_OTLP_ENDPOINT env var or disables export.
        enable: Whether to enable tracing. If False, all trace calls are no-ops.
        sample_rate: Fraction of traces to sample (0.0 to 1.0).

    Returns:
        True if tracing was successfully configured, False otherwise.

    Note:
        Requires opentelemetry-api, opentelemetry-sdk, and
        opentelemetry-exporter-otlp to be installed. If not available,
        tracing is silently disabled.
    """
    global _tracer, _tracing_enabled

    if not enable:
        _tracing_enabled = False
        logger.info("Tracing disabled by configuration")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        # Create resource with service name
        resource = Resource.create({SERVICE_NAME: service_name})

        # Create sampler
        sampler = TraceIdRatioBased(sample_rate)

        # Create and set tracer provider
        provider = TracerProvider(resource=resource, sampler=sampler)

        # Configure exporter if endpoint provided
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"Tracing exporter configured for {endpoint}")
            except ImportError:
                logger.warning(
                    "opentelemetry-exporter-otlp not installed; traces won't be exported"
                )
        else:
            # Check for console exporter for debugging
            try:
                from opentelemetry.sdk.trace.export import (
                    ConsoleSpanExporter,
                    SimpleSpanProcessor,
                )
                import os

                if os.environ.get("OTEL_TRACES_CONSOLE", "").lower() == "true":
                    provider.add_span_processor(
                        SimpleSpanProcessor(ConsoleSpanExporter())
                    )
                    logger.info("Console trace exporter enabled")
            except ImportError:
                pass

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        _tracing_enabled = True
        logger.info(f"Tracing enabled for service '{service_name}'")
        return True

    except ImportError as e:
        logger.debug(f"OpenTelemetry not available: {e}")
        _tracing_enabled = False
        return False
    except Exception as e:
        logger.warning(f"Failed to configure tracing: {e}")
        _tracing_enabled = False
        return False


# ---------------------------------------------------------------------------
# Tracing helpers
# ---------------------------------------------------------------------------


@contextmanager
def trace_span(
    name: str,
    *,
    kind: str = "internal",
    **attributes: Any,
) -> Iterator[Any]:
    """Create a trace span for the enclosed code block.

    Args:
        name: Name of the span (e.g., "sync_auction", "fetch_page").
        kind: Span kind - "internal", "server", "client", "producer", "consumer".
        **attributes: Additional attributes to attach to the span.

    Yields:
        The span object (or None if tracing is disabled).

    Example:
        with trace_span("process_lot", lot_code="LOT123", auction_code="A1"):
            # ... processing ...
    """
    if not _tracing_enabled or _tracer is None:
        yield None
        return

    try:
        from opentelemetry.trace import SpanKind

        kind_map = {
            "internal": SpanKind.INTERNAL,
            "server": SpanKind.SERVER,
            "client": SpanKind.CLIENT,
            "producer": SpanKind.PRODUCER,
            "consumer": SpanKind.CONSUMER,
        }
        span_kind = kind_map.get(kind, SpanKind.INTERNAL)

        with _tracer.start_as_current_span(name, kind=span_kind) as span:
            # Set attributes
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, str(value))

            # Update trace context for log correlation
            ctx = span.get_span_context()
            if ctx.is_valid:
                token = _trace_context.set({
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                })
                try:
                    yield span
                finally:
                    _trace_context.reset(token)
            else:
                yield span

    except Exception as e:
        logger.debug(f"Tracing error: {e}")
        yield None


def traced(
    name: str | None = None,
    *,
    kind: str = "internal",
) -> Callable[[F], F]:
    """Decorator to trace a function.

    Args:
        name: Span name (defaults to function name).
        kind: Span kind.

    Example:
        @traced("sync_auction")
        async def sync_auction(code: str) -> SyncResult:
            ...

        @traced()  # Uses function name as span name
        def process_lot(lot: Lot) -> None:
            ...
    """
    def decorator(func: F) -> F:
        span_name = name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(span_name, kind=kind):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace_span(span_name, kind=kind):
                return await func(*args, **kwargs)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def add_span_event(name: str, **attributes: Any) -> None:
    """Add an event to the current span.

    Events are timestamped annotations that can be attached to spans
    to mark significant moments during execution.

    Args:
        name: Event name.
        **attributes: Event attributes.
    """
    if not _tracing_enabled:
        return

    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.add_event(name, attributes=attributes)
    except Exception:
        pass


def set_span_attribute(key: str, value: Any) -> None:
    """Set an attribute on the current span.

    Args:
        key: Attribute key.
        value: Attribute value (will be converted to string).
    """
    if not _tracing_enabled:
        return

    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute(key, str(value))
    except Exception:
        pass


def record_exception(exception: BaseException) -> None:
    """Record an exception on the current span.

    Args:
        exception: The exception to record.
    """
    if not _tracing_enabled:
        return

    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.record_exception(exception)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
    except Exception:
        pass
