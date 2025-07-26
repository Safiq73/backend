-- Migration: Rename roles table and columns to titles
-- This migration aligns the database schema with the Python code changes
-- Date: 2025-07-26

-- Start transaction
BEGIN;

-- Step 1: Rename the roles table to titles
ALTER TABLE roles RENAME TO titles;

-- Step 2: Rename columns in titles table to match title terminology
ALTER TABLE titles RENAME COLUMN role_name TO title_name;
ALTER TABLE titles RENAME COLUMN role_type TO title_type;

-- Step 3: Rename the role column in users table to title
ALTER TABLE users RENAME COLUMN role TO title;

-- Step 4: Update index names to match new table and column names
DROP INDEX IF EXISTS idx_users_role;
CREATE INDEX idx_users_title ON users (title);

-- Step 5: Update any existing data references if needed
-- (No data changes needed for this rename operation)

-- Commit transaction
COMMIT;

-- Verify the changes
SELECT 'Migration completed successfully: roles table renamed to titles, role columns renamed to title' as status;
