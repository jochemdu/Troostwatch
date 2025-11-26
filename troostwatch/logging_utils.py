"""Legacy logging utilities - deprecated.

This module re-exports from ``troostwatch.infrastructure.observability.logging``.
Import from the new location instead.
"""

import warnings

warnings.warn(
    "`troostwatch.logging_utils` is deprecated; import from "
    "`troostwatch.infrastructure.observability.logging` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from troostwatch.infrastructure.observability.logging import get_logger

__all__ = ["get_logger"]
