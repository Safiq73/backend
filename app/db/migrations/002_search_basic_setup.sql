-- Search Optimization Migration - Part 1: Basic Setup
-- Adds full-text search capabilities, indexes, and search vectors for unified search

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add search vector columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Add search vector columns to posts table  
ALTER TABLE posts ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Add search-related columns to representatives table
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS cached_name TEXT;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS cached_designation TEXT;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS cached_constituency TEXT;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS search_vector tsvector;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS contact_email TEXT;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS party TEXT;
ALTER TABLE representatives ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- Create search indexes for users
CREATE INDEX IF NOT EXISTS idx_users_search_vector ON users USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_users_username_trgm ON users USING GIN (username gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_users_display_name_trgm ON users USING GIN (display_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_users_bio_trgm ON users USING GIN (bio gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_users_followers_count ON users (followers_count DESC);
CREATE INDEX IF NOT EXISTS idx_users_verified ON users (is_verified, followers_count DESC);

-- Create search indexes for posts
CREATE INDEX IF NOT EXISTS idx_posts_search_vector ON posts USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_posts_title_trgm ON posts USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_posts_content_trgm ON posts USING GIN (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_posts_tags ON posts USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_posts_location_trgm ON posts USING GIN (location gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_posts_upvotes ON posts (upvotes DESC);
CREATE INDEX IF NOT EXISTS idx_posts_created_at_desc ON posts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_last_activity ON posts (last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_status_type ON posts (status, post_type);

-- Create search indexes for representatives
CREATE INDEX IF NOT EXISTS idx_representatives_search_vector ON representatives USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_representatives_cached_name_trgm ON representatives USING GIN (cached_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_representatives_cached_designation_trgm ON representatives USING GIN (cached_designation gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_representatives_cached_constituency_trgm ON representatives USING GIN (cached_constituency gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_representatives_party_trgm ON representatives USING GIN (party gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_representatives_verified ON representatives (is_verified);
CREATE INDEX IF NOT EXISTS idx_representatives_user_id_not_null ON representatives (user_id) WHERE user_id IS NOT NULL;

-- Create composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_posts_type_status_created ON posts (post_type, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_assignee_status ON posts (assignee, status) WHERE assignee IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_active_verified ON users (is_active, is_verified, followers_count DESC);
