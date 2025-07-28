-- Migration to remove category and area fields from posts table
-- These fields are being removed as they're no longer needed in the simplified post structure

-- Drop the columns and their indexes
DROP INDEX IF EXISTS idx_posts_area;
DROP INDEX IF EXISTS idx_posts_category;

ALTER TABLE posts DROP COLUMN IF EXISTS area;
ALTER TABLE posts DROP COLUMN IF EXISTS category;
