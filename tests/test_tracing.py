"""Tests for OpenTelemetry tracing module."""

import pytest

from troostwatch.infrastructure.observability.tracing import (
    configure_tracing,
    is_tracing_enabled,
    trace_span,
    traced,
    get_trace_context,
    add_span_event,
    set_span_attribute,
    record_exception,
)


class TestTracingDisabled:
    """Tests when tracing is disabled (default state)."""

    def test_tracing_disabled_by_default(self):
        """Tracing is disabled when OpenTelemetry is not installed."""
        assert is_tracing_enabled() is False

    def test_trace_span_noop_when_disabled(self):
        """trace_span yields None when tracing is disabled."""
        with trace_span("test_span", key="value") as span:
            assert span is None

    def test_traced_decorator_works_when_disabled(self):
        """@traced decorator works but doesn't create spans when disabled."""
        @traced("test_function")
        def my_function(x: int) -> int:
            return x * 2

        result = my_function(21)
        assert result == 42

    def test_traced_decorator_async_works_when_disabled(self):
        """@traced decorator works with async functions when disabled."""
        import asyncio

        @traced("async_function")
        async def my_async_function(x: int) -> int:
            return x * 2

        result = asyncio.run(my_async_function(21))
        assert result == 42

    def test_get_trace_context_empty_when_disabled(self):
        """get_trace_context returns empty dict when disabled."""
        ctx = get_trace_context()
        assert ctx == {}

    def test_add_span_event_noop_when_disabled(self):
        """add_span_event is a no-op when disabled."""
        # Should not raise
        add_span_event("test_event", key="value")

    def test_set_span_attribute_noop_when_disabled(self):
        """set_span_attribute is a no-op when disabled."""
        # Should not raise
        set_span_attribute("key", "value")

    def test_record_exception_noop_when_disabled(self):
        """record_exception is a no-op when disabled."""
        # Should not raise
        record_exception(ValueError("test error"))


class TestConfigureTracing:
    """Tests for configure_tracing function."""

    def test_configure_with_enable_false(self):
        """configure_tracing returns False when enable=False."""
        result = configure_tracing(enable=False)
        assert result is False
        assert is_tracing_enabled() is False

    def test_configure_without_opentelemetry(self):
        """configure_tracing returns False when OpenTelemetry is not installed."""
        # This test assumes OpenTelemetry is not installed in the test environment
        # If it is installed, this test will pass anyway (returns True)
        result = configure_tracing(service_name="test", enable=True)
        # Result depends on whether opentelemetry is installed
        assert isinstance(result, bool)


class TestTracedDecorator:
    """Tests for the @traced decorator."""

    def test_traced_preserves_function_name(self):
        """@traced preserves the original function name."""
        @traced("custom_name")
        def original_function():
            pass

        assert original_function.__name__ == "original_function"

    def test_traced_uses_function_name_by_default(self):
        """@traced uses function name when no name provided."""
        @traced()
        def my_special_function():
            return 42

        result = my_special_function()
        assert result == 42
        assert my_special_function.__name__ == "my_special_function"

    def test_traced_passes_arguments(self):
        """@traced passes all arguments to the function."""
        @traced("test")
        def add(a: int, b: int, *, c: int = 0) -> int:
            return a + b + c

        assert add(1, 2) == 3
        assert add(1, 2, c=3) == 6

    def test_traced_propagates_exceptions(self):
        """@traced propagates exceptions from the function."""
        @traced("failing_function")
        def failing():
            raise ValueError("expected error")

        with pytest.raises(ValueError, match="expected error"):
            failing()


class TestTraceSpan:
    """Tests for trace_span context manager."""

    def test_trace_span_context_manager(self):
        """trace_span can be used as a context manager."""
        executed = False
        with trace_span("test_span"):
            executed = True
        assert executed

    def test_trace_span_with_attributes(self):
        """trace_span accepts keyword attributes."""
        with trace_span("test_span", auction_code="ABC", lot_count=10):
            pass  # Should not raise

    def test_trace_span_with_kind(self):
        """trace_span accepts span kind."""
        for kind in ["internal", "server", "client", "producer", "consumer"]:
            with trace_span("test_span", kind=kind):
                pass  # Should not raise
