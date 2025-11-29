"""Database facade for the infrastructure layer.

Re-exports the database helpers from ``troostwatch.infrastructure.db``
so call sites can use ``troostwatch.infrastructure.persistence.db``.
"""

from troostwatch.infrastructure.db import (
    ensure_schema,
    get_connection,
    get_path_config,
    iso_utcnow,
)

__all__ = [
    "ensure_schema",
    "get_connection",
    "get_path_config",
    "iso_utcnow",
]
