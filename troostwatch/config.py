"""Legacy config utilities - deprecated.

This module re-exports from ``troostwatch.app.config``.
Import from the new location instead.
"""

import warnings

warnings.warn(
    "`troostwatch.config` is deprecated; import from "
    "`troostwatch.app.config` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from troostwatch.app.config import load_config

__all__ = ["load_config"]