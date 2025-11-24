"""Application configuration facade."""

import troostwatch.config as _legacy_config
from troostwatch.config import *  # noqa: F401,F403

__all__ = getattr(_legacy_config, "__all__", []) or [
    name
    for name in dir(_legacy_config)
    if not name.startswith("_")
]
