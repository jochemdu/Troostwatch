"""Legacy debug utilities - deprecated.

This module re-exports from ``troostwatch.infrastructure.diagnostics.debug_tools``.
Import from the new location instead.
"""

import warnings

warnings.warn(
    "`troostwatch.debug_tools` is deprecated; import from "
    "`troostwatch.infrastructure.diagnostics.debug_tools` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from troostwatch.infrastructure.diagnostics.debug_tools import (
    db_integrity,
    db_stats,
    db_view,
)

__all__ = ["db_stats", "db_integrity", "db_view"]