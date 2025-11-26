"""Legacy HTTP client - deprecated.

This module re-exports from ``troostwatch.infrastructure.http``.
Import from the new location instead.
"""

import warnings

warnings.warn(
    "`troostwatch.http_client` is deprecated; import from "
    "`troostwatch.infrastructure.http` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from troostwatch.infrastructure.http import (
    AuthenticationError,
    LoginCredentials,
    SessionExpiredError,
    StoredSession,
    TroostwatchHttpClient,
)

__all__ = [
    "AuthenticationError",
    "LoginCredentials",
    "SessionExpiredError",
    "StoredSession",
    "TroostwatchHttpClient",
]
