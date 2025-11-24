"""Domain models facade.

Provides a stable path ``troostwatch.domain.models`` that forwards to the
existing :mod:`troostwatch.models` package while the codebase transitions to
the layered layout.
"""

import troostwatch.models as _legacy_models
from troostwatch.models import *  # noqa: F401,F403

__all__ = getattr(_legacy_models, "__all__", []) or [
    name
    for name in dir(_legacy_models)
    if not name.startswith("_")
]
