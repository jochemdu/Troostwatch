"""Simple in-process metrics collection for Troostwatch.

This module provides lightweight counters and histograms for tracking
application health without external dependencies. Metrics are stored in
memory and can be exported via a /metrics endpoint or logged periodically.

For production use with Prometheus/Grafana, this module can be extended
to use prometheus_client, but currently uses simple dictionaries.
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Metric storage
# ---------------------------------------------------------------------------


@dataclass
class Counter:
    """A monotonically increasing counter."""

    name: str
    help_text: str = ""
    _values: dict[tuple[tuple[str, str], ...], float] = field(
    _values: dict[tuple[tuple[str, str], ...], float] = field(
        default_factory=lambda: defaultdict(float)
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, value: float = 1.0, labels: dict[str, str | None] = None) -> None:
        """Increment the counter by the given value."""
        key = self._labels_to_key(labels)
        with self._lock:
            self._values[key] += value

    def get(self, labels: dict[str, str | None] = None) -> float:
        """Get the current counter value."""
        key = self._labels_to_key(labels)
        with self._lock:
            return self._values[key]

    def _labels_to_key(
        self, labels: dict[str, str | None]
    ) -> tuple[tuple[str, str], ...]:
        if labels is None:
            return ()
        return tuple(sorted(labels.items()))


@dataclass
class Histogram:
    """A histogram for recording distributions of values.

    Uses predefined buckets for simplicity. Values are accumulated into
    buckets and a sum/count is maintained for average calculation.
    """

    name: str
    help_text: str = ""
    buckets: tuple[float, ...] = (
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
    )
    _observations: dict[tuple[tuple[str, str], ...], list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def observe(self, value: float, labels: dict[str, str | None] = None) -> None:
        """Record an observation."""
        key = self._labels_to_key(labels)
        with self._lock:
            self._observations[key].append(value)

    def get_stats(self, labels: dict[str, str | None] = None) -> dict[str, float]:
        """Get summary statistics for the histogram."""
        key = self._labels_to_key(labels)
        with self._lock:
            values = self._observations[key]
            if not values:
                return {"count": 0, "sum": 0.0, "avg": 0.0}
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
            }

    def _labels_to_key(
        self, labels: dict[str, str | None]
    ) -> tuple[tuple[str, str], ...]:
        if labels is None:
            return ()
        return tuple(sorted(labels.items()))


# ---------------------------------------------------------------------------
# Global metric registry
# ---------------------------------------------------------------------------


class MetricRegistry:
    """Global registry for all metrics."""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, help_text: str = "") -> Counter:
        """Get or create a counter."""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name, help_text=help_text)
            return self._counters[name]

    def histogram(
        self,
        name: str,
        help_text: str = "",
        buckets: tuple[float, ... | None] = None,
    ) -> Histogram:
        """Get or create a histogram."""
        with self._lock:
            if name not in self._histograms:
                kwargs: dict[str, object] = {"name": name, "help_text": help_text}
                kwargs: dict[str, object] = {"name": name, "help_text": help_text}
                if buckets is not None:
                    kwargs["buckets"] = buckets
                self._histograms[name] = Histogram(**kwargs)  # type: ignore[arg-type]
            return self._histograms[name]

    def all_counters(self) -> dict[str, Counter]:
    def all_counters(self) -> dict[str, Counter]:
        """Return all registered counters."""
        with self._lock:
            return dict(self._counters)

    def all_histograms(self) -> dict[str, Histogram]:
    def all_histograms(self) -> dict[str, Histogram]:
        """Return all registered histograms."""
        with self._lock:
            return dict(self._histograms)


# Default global registry
_registry = MetricRegistry()


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def increment_counter(
    name: str,
    value: float = 1.0,
    labels: dict[str, str | None] = None,
    help_text: str = "",
) -> None:
    """Increment a counter by name.

    Creates the counter if it doesn't exist.
    """
    _registry.counter(name, help_text).inc(value, labels)


def observe_histogram(
    name: str,
    value: float,
    labels: dict[str, str | None] = None,
    help_text: str = "",
) -> None:
    """Record an observation in a histogram.

    Creates the histogram if it doesn't exist.
    """
    _registry.histogram(name, help_text).observe(value, labels)


class Timer:
    """Context manager for timing operations and recording to a histogram."""

    def __init__(
        self,
        histogram_name: str,
        labels: dict[str, str | None] = None,
        help_text: str = "",
    ) -> None:
        self.histogram_name = histogram_name
        self.labels = labels
        self.help_text = help_text
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        duration = time.perf_counter() - self._start
        observe_histogram(self.histogram_name, duration, self.labels, self.help_text)


# ---------------------------------------------------------------------------
# Predefined metrics for Troostwatch
# ---------------------------------------------------------------------------

# API metrics
API_REQUESTS = "api_requests_total"
API_REQUEST_DURATION = "api_request_duration_seconds"

# Sync metrics
SYNC_RUNS = "sync_runs_total"
SYNC_RUN_DURATION = "sync_run_duration_seconds"
SYNC_LOTS_PROCESSED = "sync_lots_processed_total"

# Bidding metrics
BIDS = "bids_total"


def record_api_request(
    endpoint: str, method: str, status_code: int, duration: float
) -> None:
    """Record an API request with its outcome and duration."""
    labels = {"endpoint": endpoint, "method": method, "status": str(status_code)}
    increment_counter(API_REQUESTS, labels=labels, help_text="Total API requests")
    observe_histogram(
        API_REQUEST_DURATION,
        duration,
        labels={"endpoint": endpoint, "method": method},
        help_text="API request duration in seconds",
    )


def record_sync_run(
    auction_code: str, status: str, duration: float, lots_processed: int
) -> None:
    """Record a completed sync run."""
    increment_counter(
        SYNC_RUNS,
        labels={"auction_code": auction_code, "status": status},
        help_text="Total sync runs",
    )
    observe_histogram(
        SYNC_RUN_DURATION,
        duration,
        labels={"auction_code": auction_code},
        help_text="Sync run duration in seconds",
    )
    increment_counter(
        SYNC_LOTS_PROCESSED,
        value=float(lots_processed),
        labels={"auction_code": auction_code},
        help_text="Total lots processed by sync",
    )


def record_bid(outcome: str, auction_code: str, lot_code: str) -> None:
    """Record a bid attempt with its outcome."""
    increment_counter(
        BIDS,
        labels={"outcome": outcome, "auction_code": auction_code},
        help_text="Total bid attempts",
    )


# ---------------------------------------------------------------------------
# Export utilities
# ---------------------------------------------------------------------------


def get_metrics_summary() -> dict[str, object]:
def get_metrics_summary() -> dict[str, object]:
    """Return a summary of all metrics for logging or API response."""
    result: dict[str, object] = {"counters": {}, "histograms": {}}
    result: dict[str, object] = {"counters": {}, "histograms": {}}

    for name, counter in _registry.all_counters().items():
        values = {}
        for key, value in counter._values.items():
            label_str = ",".join(f"{k}={v}" for k, v in key) if key else "default"
            values[label_str] = value
        result["counters"][name] = values  # type: ignore[index]

    for name, histogram in _registry.all_histograms().items():
        stats = {}
        for key in histogram._observations:
            label_str = ",".join(f"{k}={v}" for k, v in key) if key else "default"
            stats[label_str] = histogram.get_stats(dict(key) if key else None)
        result["histograms"][name] = stats  # type: ignore[index]

    return result


def format_prometheus() -> str:
    """Format metrics in Prometheus text exposition format."""
    lines: list[str] = []
    lines: list[str] = []

    for name, counter in _registry.all_counters().items():
        if counter.help_text:
            lines.append(f"# HELP {name} {counter.help_text}")
        lines.append(f"# TYPE {name} counter")
        for key, value in counter._values.items():
            if key:
                label_str = ",".join(f'{k}="{v}"' for k, v in key)
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

    for name, histogram in _registry.all_histograms().items():
        if histogram.help_text:
            lines.append(f"# HELP {name} {histogram.help_text}")
        lines.append(f"# TYPE {name} histogram")
        for key in histogram._observations:
            stats = histogram.get_stats(dict(key) if key else None)
            if key:
                label_str = ",".join(f'{k}="{v}"' for k, v in key)
                lines.append(f"{name}_count{{{label_str}}} {stats['count']}")
                lines.append(f"{name}_sum{{{label_str}}} {stats['sum']}")
            else:
                lines.append(f"{name}_count {stats['count']}")
                lines.append(f"{name}_sum {stats['sum']}")

    return "\n".join(lines)
