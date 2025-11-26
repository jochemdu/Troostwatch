"""Legacy analytics namespace - deprecated.

This package is deprecated. Import from ``troostwatch.domain.analytics``
instead.
"""

import warnings

warnings.warn(
    "`troostwatch.analytics` is deprecated; import from "
    "`troostwatch.domain.analytics` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from troostwatch.domain.analytics import BuyerSummary, TrackedLotSummary

__all__ = ["BuyerSummary", "TrackedLotSummary"]