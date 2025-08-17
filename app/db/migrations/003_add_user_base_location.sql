-- Migration: Add base location columns to users table
-- This allows users to set their base/home location during registration

-- Add base location columns to users table
ALTER TABLE users 
ADD COLUMN base_latitude DECIMAL(10, 8), 
ADD COLUMN base_longitude DECIMAL(11, 8);

-- Add constraints to ensure coordinates are within India bounds
ALTER TABLE users 
ADD CONSTRAINT check_base_latitude_india_bounds 
    CHECK (base_latitude IS NULL OR (base_latitude >= 6.5 AND base_latitude <= 37.5));

ALTER TABLE users 
ADD CONSTRAINT check_base_longitude_india_bounds 
    CHECK (base_longitude IS NULL OR (base_longitude >= 68.0 AND base_longitude <= 97.5));

-- Add indexes for location-based queries
CREATE INDEX idx_users_base_coordinates ON users (base_latitude, base_longitude) 
WHERE base_latitude IS NOT NULL AND base_longitude IS NOT NULL;

CREATE INDEX idx_users_base_latitude ON users (base_latitude) 
WHERE base_latitude IS NOT NULL;

CREATE INDEX idx_users_base_longitude ON users (base_longitude) 
WHERE base_longitude IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN users.base_latitude IS 'User''s base/home location latitude (India bounds: 6.5° to 37.5° N)';
COMMENT ON COLUMN users.base_longitude IS 'User''s base/home location longitude (India bounds: 68° to 97.5° E)';
