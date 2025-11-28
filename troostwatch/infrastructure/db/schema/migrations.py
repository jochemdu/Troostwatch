from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ..connection import iso_utcnow
from .tables import SCHEMA_MIGRATIONS_SQL, SCHEMA_VERSION_SQL


# Current schema version - increment when making structural changes.
# This must match the version comment in schema/schema.sql.
CURRENT_SCHEMA_VERSION = 9


class SchemaMigrator:
    """Lightweight migration runner backed by ``schema_migrations``.

    Migration files are applied in lexical order and each filename is recorded
    in the ``schema_migrations`` table. The class can also register ad-hoc
    migrations triggered from code paths (e.g. adding columns conditionally).

    Schema versioning is tracked separately in the ``schema_version`` table
    which holds a single integer version number that must match
    ``CURRENT_SCHEMA_VERSION``.
    """

    def __init__(self, conn) -> None:
        self.conn = conn

    # -------------------------------------------------------------------------
    # Schema version tracking
    # -------------------------------------------------------------------------

    def ensure_version_table(self) -> None:
        """Create the schema_version table if it does not exist."""
        self.conn.executescript(SCHEMA_VERSION_SQL)

    def get_version(self) -> int | None:
        """Return the current schema version, or None if not set."""
        self.ensure_version_table()
        cur = self.conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None

    def set_version(self, version: int) -> None:
        """Set the schema version, replacing any existing value."""
        self.ensure_version_table()
        self.conn.execute("DELETE FROM schema_version")
        self.conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, iso_utcnow()),
        )

    def ensure_current_version(self) -> None:
        """Ensure the schema_version table reflects CURRENT_SCHEMA_VERSION."""
        current = self.get_version()
        if current is None or current < CURRENT_SCHEMA_VERSION:
            self.set_version(CURRENT_SCHEMA_VERSION)

    # -------------------------------------------------------------------------
    # Migration tracking (by name)
    # -------------------------------------------------------------------------

    def ensure_table(self) -> None:
        self.conn.executescript(SCHEMA_MIGRATIONS_SQL)

    def has_migration(self, name: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?", (name,)
        )
        return cur.fetchone() is not None

    def record(self, name: str, notes: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO schema_migrations (name, applied_at, notes) VALUES (?, ?, ?)",
            (name, iso_utcnow(), notes),
        )

    def apply_sql(self, name: str, sql: str, notes: str | None = None) -> None:
        self.ensure_table()
        if self.has_migration(name):
            return
        if not sql.strip():
            return
        self.conn.executescript(sql)
        self.record(name, notes)

    def apply_path(self, migrations_dir: str | Path | None = None) -> None:
        self.ensure_table()
        root = Path(__file__).resolve().parents[4]
        migrations_path = (
            Path(migrations_dir) if migrations_dir else (root / "migrations")
        )
        if not migrations_path.exists() or not migrations_path.is_dir():
            return

        for path in sorted(migrations_path.iterdir()):
            if not path.is_file() or not path.name.lower().endswith(".sql"):
                continue
            name = path.name
            if self.has_migration(name):
                continue
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            self.apply_sql(name, sql, notes=f"applied from {path.relative_to(root)}")

    def run_migrations(self, migrations: Iterable[str] | None = None) -> None:
        """Execute bundled schema and any additional migration scripts."""

        self.ensure_table()
        self.apply_path()
        if migrations:
            for script in migrations:
                self.apply_sql(f"inline-{hash(script)}", script)
