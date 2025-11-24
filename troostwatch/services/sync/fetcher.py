"""Facade for sync HTTP fetching services."""

import troostwatch.sync.fetcher as _legacy_fetcher
from troostwatch.sync.fetcher import *  # noqa: F401,F403

__all__ = getattr(_legacy_fetcher, "__all__", []) or [
    name
    for name in dir(_legacy_fetcher)
    if not name.startswith("_")
]
