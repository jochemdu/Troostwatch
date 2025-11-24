"""Domain analytics facade.

This wrapper re-exports the legacy :mod:`troostwatch.analytics` package so
imports can move to ``troostwatch.domain.analytics`` during the layered
migration without changing behaviour.
"""

import troostwatch.analytics as _legacy_analytics
from troostwatch.analytics import *  # noqa: F401,F403

__all__ = getattr(_legacy_analytics, "__all__", []) or [
    name
    for name in dir(_legacy_analytics)
    if not name.startswith("_")
]
