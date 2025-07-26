-- Migration: Add latitude and longitude columns to posts table
-- Date: $(date +%Y-%m-%d)
-- Description: Add coordinate fields for precise location tracking

BEGIN;

-- Add latitude and longitude columns
ALTER TABLE posts 
ADD COLUMN latitude DECIMAL(10, 8),
ADD COLUMN longitude DECIMAL(11, 8);

-- Add check constraints to ensure coordinates are within India bounds
ALTER TABLE posts 
ADD CONSTRAINT check_latitude_india_bounds 
CHECK (latitude IS NULL OR (latitude >= 6.5 AND latitude <= 37.5));

ALTER TABLE posts 
ADD CONSTRAINT check_longitude_india_bounds 
CHECK (longitude IS NULL OR (longitude >= 68.0 AND longitude <= 97.5));

-- Add indexes for spatial queries
CREATE INDEX idx_posts_coordinates ON posts (latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Add a computed geography point column for PostGIS spatial queries (if needed later)
-- ALTER TABLE posts ADD COLUMN location_point GEOGRAPHY(POINT, 4326);
-- CREATE INDEX idx_posts_location_point ON posts USING GIST (location_point);

-- Update existing posts that might have location data
-- (This is safe to run even if no existing data)
UPDATE posts 
SET latitude = NULL, longitude = NULL 
WHERE latitude IS NULL AND longitude IS NULL;

COMMIT;
