"""HTTP adapter facade.

Exposes the legacy :class:`troostwatch.http_client.TroostwatchHttpClient` and
related errors under the infrastructure layer namespace.
"""

import troostwatch.http_client as _legacy_http
from troostwatch.http_client import *  # noqa: F401,F403

__all__ = getattr(_legacy_http, "__all__", []) or [
    name
    for name in dir(_legacy_http)
    if not name.startswith("_")
]
