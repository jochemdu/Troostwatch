"""Database facade for the infrastructure layer.

Re-exports the legacy :mod:`troostwatch.db` helpers so call sites can migrate to
``troostwatch.infrastructure.persistence.db`` while retaining behaviour.
"""

import troostwatch.db as _legacy_db
from troostwatch.db import *  # noqa: F401,F403

__all__ = getattr(_legacy_db, "__all__", []) or [
    name
    for name in dir(_legacy_db)
    if not name.startswith("_")
]
