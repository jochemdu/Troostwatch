-- This migration originally used "ALTER TABLE ... ADD COLUMN IF NOT EXISTS" to
-- add a batch of columns to the ``lots`` table. Older SQLite versions (before
-- 3.35) do not support the ``IF NOT EXISTS`` clause on ADD COLUMN, which caused
-- a "near \"EXISTS\": syntax error" during ``executescript``. The core schema
-- already ships with these columns, and :func:`troostwatch.db._ensure_lots_columns`
-- adds any missing ones for legacy databases, so the DDL can safely be removed.

-- Keeping this file (with comments only) preserves the migration record in
-- ``schema_migrations`` without executing incompatible statements.
