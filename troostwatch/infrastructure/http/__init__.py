"""HTTP adapters for Troostwatch.

This package provides authenticated HTTP client functionality for interacting
with the Troostwijk website.
"""

from .client import (
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
