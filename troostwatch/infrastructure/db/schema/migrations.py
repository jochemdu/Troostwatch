from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..connection import iso_utcnow
from .tables import SCHEMA_MIGRATIONS_SQL


class SchemaMigrator:
    """Lightweight migration runner backed by ``schema_migrations``.

    Migration files are applied in lexical order and each filename is recorded
    in the ``schema_migrations`` table. The class can also register ad-hoc
    migrations triggered from code paths (e.g. adding columns conditionally).
    """

    def __init__(self, conn) -> None:
        self.conn = conn

    def ensure_table(self) -> None:
        self.conn.executescript(SCHEMA_MIGRATIONS_SQL)

    def has_migration(self, name: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM schema_migrations WHERE name = ?", (name,))
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
        migrations_path = Path(migrations_dir) if migrations_dir else (root / "migrations")
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
