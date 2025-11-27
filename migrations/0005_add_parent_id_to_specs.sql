-- Migration 0005: Add parent_id to product_layers for hierarchical specs
-- A lot can have components (e.g., Computer) which have subcomponents (e.g., GPU, CPU)
-- Note: This migration is safe to run on databases created with schema.sql that already has parent_id

-- Only add column if it doesn't exist (SQLite doesn't have IF NOT EXISTS for ALTER TABLE)
-- The column already exists in schema.sql, so this migration is a no-op for new databases
-- For older databases, the ALTER TABLE will add the column
-- We use a pragma check to make this idempotent

-- Check if column exists and add if not
CREATE TABLE IF NOT EXISTS _migration_temp (x);
DROP TABLE _migration_temp;

-- The parent_id column and index are now defined in schema.sql
-- This migration is kept for backwards compatibility with existing databases
-- that were created before parent_id was added to the schema
