"""Initialise the Troostwatch project for first-time users.

This script creates the database, directories and placeholder configuration
for a fresh installation of Troostwatch.
"""

import json
from pathlib import Path


def main() -> None:
    """Create default database and configuration files."""
    root = Path(__file__).resolve().parent.parent
    config_path = root / "config.json"
    db_path = root / "troostwatch.db"

    # Create default config if it doesn't exist
    if not config_path.exists():
        config = {
            "config_format_version": "1.0",
            "paths": {
                "db_path": str(db_path),
                "snapshots_root": "snapshots",
                "lot_cards_dir": "snapshots/lot_cards",
                "lot_details_dir": "snapshots/lot_details",
            },
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    # Create the database if it doesn't exist
    if not db_path.exists():
        schema_path = root / "schema" / "schema.sql"
        if schema_path.exists():
            import sqlite3

            conn = sqlite3.connect(db_path)
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
            print(f"Created database at {db_path}")
        else:
            print("Schema file not found. Cannot create database.")

    # Create snapshot directories
    snapshots_root = root / "snapshots"
    (snapshots_root / "lot_cards").mkdir(parents=True, exist_ok=True)
    (snapshots_root / "lot_details").mkdir(parents=True, exist_ok=True)
    print("Initialized Troostwatch project.")


if __name__ == "__main__":
    main()
