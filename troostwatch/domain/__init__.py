"""Domain layer facade for Troostwatch.

This package groups the pure business logic and shared models that do not
concern infrastructure or interface details. It currently bridges to the
existing ``troostwatch.analytics`` and ``troostwatch.models`` modules so new
imports can target ``troostwatch.domain`` without breaking legacy callers.
"""

from . import analytics, models

__all__ = ["analytics", "models"]
