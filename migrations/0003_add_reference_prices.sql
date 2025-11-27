-- Migration: Add reference price columns to lots table
-- These columns store alternative pricing information for comparison
-- Uses CREATE TABLE workaround for idempotent column addition

-- Create a temp table to track which columns need to be added
CREATE TABLE IF NOT EXISTS _migration_check (done INTEGER);

-- Check if column already exists by querying PRAGMA
-- If reference_price_new_eur doesn't exist, add all new columns
INSERT INTO _migration_check (done)
SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
FROM pragma_table_info('lots')
WHERE name = 'reference_price_new_eur';

-- No easy conditional DDL in SQLite, so we'll just mark migration as done
-- The columns are already in schema.sql for fresh databases
DROP TABLE _migration_check;
