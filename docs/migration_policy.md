# Database Migration Policy

This document describes how Troostwatch manages SQLite schema changes.

## Overview

Troostwatch uses a **hybrid migration strategy**:

1. **Snapshot schema** (`schema/schema.sql`) – the canonical source of truth for
   new databases.
2. **Programmatic migrations** – Python code in
   `troostwatch/infrastructure/db/schema/manager.py` handles incremental
   changes (adding columns, creating indexes, etc.).
3. **SQL migration files** (`migrations/*.sql`) – optional; applied in lexical
   order by `SchemaMigrator.apply_path()`.

The `schema_version` table stores a single integer version that must match
`CURRENT_SCHEMA_VERSION` in the codebase. The `schema_migrations` table tracks
individual migration scripts (by name) to prevent re-application.

## Files & Locations

| Path | Purpose |
|------|---------|
| `schema/schema.sql` | Full DDL snapshot; used when creating new databases. |
| `migrations/` | Optional SQL migration scripts applied by `SchemaMigrator`. |
| `troostwatch/infrastructure/db/schema/migrations.py` | `SchemaMigrator` class and `CURRENT_SCHEMA_VERSION`. |
| `troostwatch/infrastructure/db/schema/manager.py` | `ensure_schema()` and programmatic column additions. |
| `troostwatch/infrastructure/db/schema/tables.py` | SQL fragments for ancillary tables. |

## Workflow: Adding a New Column

1. **Add the column to `schema/schema.sql`** so that fresh databases include it
   from the start.
2. **Increment `CURRENT_SCHEMA_VERSION`** in `migrations.py` (e.g., `1 → 2`).
3. **Update the version comment** at the top of `schema/schema.sql` to match.
4. **Add a programmatic migration** in `manager.py` (using `_ensure_*_columns`
   patterns) or create a numbered SQL file in `migrations/`.
5. **Run the test suite** (`pytest -q`) to verify no regressions.
6. **Commit atomically** with a message like `feat: add <column> to <table>`.

## Workflow: Creating a New Table

1. Add the `CREATE TABLE` statement to `schema/schema.sql`.
2. If the table needs runtime creation for existing databases, add a
   `CREATE TABLE IF NOT EXISTS` snippet to `tables.py` and execute it in
   `ensure_schema()`.
3. Increment `CURRENT_SCHEMA_VERSION` and update the header comment.
4. Run tests and commit.

## Version Tracking

- **`schema_version`** – single-row table holding the current integer version.
- **`schema_migrations`** – records each migration script (by `name`) with an
  `applied_at` timestamp and optional `notes`.

`SchemaMigrator.ensure_current_version()` is called during `ensure_schema()` to
update the version number automatically.

## Querying Current State

Use `scripts/check_schema.py` to inspect the database:

```bash
python scripts/check_schema.py
```

This prints the current schema version, lists applied migrations, and flags any
version mismatch.

## Forbidden Patterns

- ❌ **Hand-editing production databases** – always use migrations.
- ❌ **Dropping columns without a migration** – data loss is irreversible.
- ❌ **Changing column types in-place** – SQLite has limited `ALTER TABLE`
  support; prefer adding a new column and backfilling.
- ❌ **Skipping `schema/schema.sql` updates** – new databases must reflect the
  current schema.

## Rollback Strategy

SQLite does not support transactional DDL for all statements. For non-trivial
rollbacks:

1. **Take a backup** before applying risky migrations.
2. Write a corresponding "down" SQL file if needed (not auto-applied).
3. Test rollback scripts in a development environment before production use.

## Agent Reference

The `migration-agent.md` file under `.github/agents/` provides role-specific
instructions for agents performing migration work. It references this policy
and does **not** use Alembic (Alembic is not part of Troostwatch).
