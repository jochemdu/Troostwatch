#!/usr/bin/env python3
"""Inspect the database schema version and applied migrations.

Usage:
    python scripts/check_schema.py [--db PATH]

Prints:
    - Current schema version (from schema_version table).
    - Expected version (CURRENT_SCHEMA_VERSION from code).
    - List of applied migrations (from schema_migrations table).
    - Warning if versions mismatch.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Ensure package is importable when run as script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from troostwatch.infrastructure.db.schema import \
    CURRENT_SCHEMA_VERSION  # noqa: E402


def get_db_path() -> Path:
    """Return the default database path from config or fallback."""
    config_path = Path(__file__).resolve().parents[1] / "config.json"
    if config_path.exists():
        import json

        with open(config_path) as f:
            cfg = json.load(f)
            return Path(cfg.get("database", "troostwatch.db"))
    return Path("troostwatch.db")


def check_schema(db_path: Path) -> int:
    """Inspect and report on database schema state. Returns exit code."""
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        # Check schema_version table
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        has_version_table = cur.fetchone() is not None

        db_version: int | None = None
        if has_version_table:
            cur = conn.execute("SELECT version, applied_at FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if row:
                db_version = row[0]
                print(f"📦 Database schema version: {db_version} (applied at {row[1]})")
            else:
                print("📦 Database schema version: (not set)")
        else:
            print("📦 Database schema version: (table missing)")

        print(f"📋 Expected schema version: {CURRENT_SCHEMA_VERSION}")

        # Version mismatch warning
        if db_version is None:
            print("⚠️  No version recorded – run the application to apply migrations.")
        elif db_version < CURRENT_SCHEMA_VERSION:
            print(
                f"⚠️  Database is behind – expected {CURRENT_SCHEMA_VERSION}, "
                f"found {db_version}."
            )
        elif db_version > CURRENT_SCHEMA_VERSION:
            print(
                f"⚠️  Database is ahead – expected {CURRENT_SCHEMA_VERSION}, "
                f"found {db_version}. Code may be outdated."
            )
        else:
            print("✅ Schema version is current.")

        # List applied migrations
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        if cur.fetchone():
            cur = conn.execute(
                "SELECT name, applied_at, notes FROM schema_migrations ORDER BY applied_at"
            )
            rows = cur.fetchall()
            if rows:
                print(f"\n📜 Applied migrations ({len(rows)}):")
                for name, applied_at, notes in rows:
                    note_str = f" – {notes}" if notes else ""
                    print(f"   • {name} @ {applied_at}{note_str}")
            else:
                print("\n📜 No migrations recorded.")
        else:
            print("\n📜 schema_migrations table not found.")

        return 0
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect database schema version.")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database (default: from config.json or troostwatch.db)",
    )
    args = parser.parse_args()
    db_path = args.db if args.db else get_db_path()
    sys.exit(check_schema(db_path))


if __name__ == "__main__":
    main()
