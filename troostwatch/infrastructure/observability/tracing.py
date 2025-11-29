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
from contextlib import AbstractContextManager
from contextvars import ContextVar
from typing import Any, Callable, TypeVar
    
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


class trace_span(AbstractContextManager):
    def __init__(self, name: str, *, kind: str = "internal", **attributes: Any):
        self.name = name
        self.kind = kind
        self.attributes = attributes
        self.span = None
        self.ctx_token = None

    def __enter__(self):
        if not _tracing_enabled or _tracer is None:
            return None
        try:
            from opentelemetry.trace import SpanKind

            kind_map = {
                "internal": SpanKind.INTERNAL,
                "server": SpanKind.SERVER,
                "client": SpanKind.CLIENT,
                "producer": SpanKind.PRODUCER,
                "consumer": SpanKind.CONSUMER,
            }
            span_kind = kind_map.get(self.kind, SpanKind.INTERNAL)
            self.span_ctx = _tracer.start_as_current_span(self.name, kind=span_kind)
            self.span = self.span_ctx.__enter__()
            for key, value in self.attributes.items():
                if value is not None:
                    self.span.set_attribute(key, str(value))
            ctx = self.span.get_span_context()
            if ctx.is_valid:
                self.ctx_token = _trace_context.set({
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                })
            return self.span
        except Exception as e:
            logger.debug(f"Tracing error: {e}")
            return None

    def __exit__(self, exc_type, exc_value, traceback):
        if self.ctx_token is not None:
            _trace_context.reset(self.ctx_token)
        if hasattr(self, "span_ctx"):
            self.span_ctx.__exit__(exc_type, exc_value, traceback)
        return False


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
    
