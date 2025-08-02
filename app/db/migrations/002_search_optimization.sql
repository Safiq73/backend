-- Search Optimization Migration
-- Adds full-text search capabilities, indexes, and search vectors for unified search

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create full-text search configuration for better Indian context
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS indian_search (COPY = english);

-- Add search vector columns if they don't exist
DO $$
BEGIN
    -- Add search_vector to users table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE users ADD COLUMN search_vector tsvector;
    END IF;

    -- Add search_vector to posts table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'posts' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE posts ADD COLUMN search_vector tsvector;
    END IF;
END $$;

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

-- Create comprehensive indexes for representatives search
-- First, let's add search optimization columns to representatives
DO $$
BEGIN
    -- Add cached name field for faster search
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'cached_name'
    ) THEN
        ALTER TABLE representatives ADD COLUMN cached_name TEXT;
    END IF;

    -- Add cached designation field
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'cached_designation'
    ) THEN
        ALTER TABLE representatives ADD COLUMN cached_designation TEXT;
    END IF;

    -- Add cached constituency field
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'cached_constituency'
    ) THEN
        ALTER TABLE representatives ADD COLUMN cached_constituency TEXT;
    END IF;

    -- Add search vector for representatives
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE representatives ADD COLUMN search_vector tsvector;
    END IF;

    -- Add verified status (based on whether they have a user_id)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'is_verified'
    ) THEN
        ALTER TABLE representatives ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
    END IF;

    -- Add contact information
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'contact_email'
    ) THEN
        ALTER TABLE representatives ADD COLUMN contact_email TEXT;
    END IF;

    -- Add party information
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'party'
    ) THEN
        ALTER TABLE representatives ADD COLUMN party TEXT;
    END IF;

    -- Add avatar URL
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'representatives' AND column_name = 'avatar_url'
    ) THEN
        ALTER TABLE representatives ADD COLUMN avatar_url TEXT;
    END IF;
END $$;

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

-- Create function to update user search vector
CREATE OR REPLACE FUNCTION update_user_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('indian_search', COALESCE(NEW.username, '')), 'A') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.display_name, '')), 'A') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.bio, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create function to update post search vector
CREATE OR REPLACE FUNCTION update_post_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('indian_search', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.location, '')), 'C') ||
        setweight(to_tsvector('indian_search', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create function to update representative search vector and cached fields
CREATE OR REPLACE FUNCTION update_representative_search_vector()
RETURNS TRIGGER AS $$
DECLARE
    title_name TEXT;
    jurisdiction_name TEXT;
    user_display_name TEXT;
BEGIN
    -- Get title name
    SELECT t.title_name INTO title_name
    FROM titles t
    WHERE t.id = NEW.title_id;

    -- Get jurisdiction name
    SELECT j.name INTO jurisdiction_name
    FROM jurisdictions j
    WHERE j.id = NEW.jurisdiction_id;

    -- Get user display name if linked
    SELECT u.display_name INTO user_display_name
    FROM users u
    WHERE u.id = NEW.user_id;

    -- Update cached fields for faster queries
    NEW.cached_name := COALESCE(user_display_name, 'Unknown Representative');
    NEW.cached_designation := COALESCE(title_name, 'Representative');
    NEW.cached_constituency := COALESCE(jurisdiction_name, 'Unknown Constituency');
    NEW.is_verified := (NEW.user_id IS NOT NULL);

    -- Update search vector
    NEW.search_vector := 
        setweight(to_tsvector('indian_search', COALESCE(NEW.cached_name, '')), 'A') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.cached_designation, '')), 'A') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.cached_constituency, '')), 'B') ||
        setweight(to_tsvector('indian_search', COALESCE(NEW.party, '')), 'C');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update search vectors
DROP TRIGGER IF EXISTS trigger_update_user_search_vector ON users;
CREATE TRIGGER trigger_update_user_search_vector
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_search_vector();

DROP TRIGGER IF EXISTS trigger_update_post_search_vector ON posts;
CREATE TRIGGER trigger_update_post_search_vector
    BEFORE INSERT OR UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_post_search_vector();

DROP TRIGGER IF EXISTS trigger_update_representative_search_vector ON representatives;
CREATE TRIGGER trigger_update_representative_search_vector
    BEFORE INSERT OR UPDATE ON representatives
    FOR EACH ROW
    EXECUTE FUNCTION update_representative_search_vector();

-- Create search analytics table for tracking popular searches
CREATE TABLE IF NOT EXISTS search_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT NOT NULL,
    search_type TEXT, -- 'all', 'people', 'posts', 'representatives'
    result_count INTEGER DEFAULT 0,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    search_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_analytics_query ON search_analytics (query);
CREATE INDEX IF NOT EXISTS idx_search_analytics_created_at ON search_analytics (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_analytics_user_id ON search_analytics (user_id);
CREATE INDEX IF NOT EXISTS idx_search_analytics_type ON search_analytics (search_type);

-- Create table for popular search suggestions
CREATE TABLE IF NOT EXISTS search_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suggestion TEXT UNIQUE NOT NULL,
    category TEXT, -- 'popular', 'trending', 'recent'
    search_count INTEGER DEFAULT 0,
    last_searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_suggestions_category ON search_suggestions (category, search_count DESC);
CREATE INDEX IF NOT EXISTS idx_search_suggestions_count ON search_suggestions (search_count DESC);

-- Insert some default search suggestions
INSERT INTO search_suggestions (suggestion, category, search_count) VALUES
('road maintenance', 'popular', 150),
('water supply issues', 'trending', 120),
('waste management', 'popular', 100),
('public transport', 'recent', 80),
('street lighting', 'popular', 70),
('traffic problems', 'trending', 60),
('healthcare services', 'popular', 50),
('education facilities', 'recent', 40)
ON CONFLICT (suggestion) DO NOTHING;

-- Update existing data with search vectors
-- This might take a while for large datasets, so we'll do it in batches

-- Update users search vectors
UPDATE users SET search_vector = 
    setweight(to_tsvector('indian_search', COALESCE(username, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(display_name, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(bio, '')), 'B')
WHERE search_vector IS NULL;

-- Update posts search vectors
UPDATE posts SET search_vector = 
    setweight(to_tsvector('indian_search', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(content, '')), 'B') ||
    setweight(to_tsvector('indian_search', COALESCE(location, '')), 'C') ||
    setweight(to_tsvector('indian_search', COALESCE(array_to_string(tags, ' '), '')), 'C')
WHERE search_vector IS NULL;

-- Update representatives with cached data and search vectors
UPDATE representatives SET 
    cached_name = COALESCE(u.display_name, 'Unknown Representative'),
    cached_designation = COALESCE(t.title_name, 'Representative'),
    cached_constituency = COALESCE(j.name, 'Unknown Constituency'),
    is_verified = (representatives.user_id IS NOT NULL)
FROM users u, titles t, jurisdictions j
WHERE representatives.user_id = u.id 
    AND representatives.title_id = t.id 
    AND representatives.jurisdiction_id = j.id
    AND representatives.cached_name IS NULL;

-- Update representatives without users
UPDATE representatives SET 
    cached_name = 'Unknown Representative',
    cached_designation = COALESCE(t.title_name, 'Representative'),
    cached_constituency = COALESCE(j.name, 'Unknown Constituency'),
    is_verified = FALSE
FROM titles t, jurisdictions j
WHERE representatives.title_id = t.id 
    AND representatives.jurisdiction_id = j.id
    AND representatives.user_id IS NULL
    AND representatives.cached_name IS NULL;

-- Update representatives search vectors
UPDATE representatives SET search_vector = 
    setweight(to_tsvector('indian_search', COALESCE(cached_name, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(cached_designation, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(cached_constituency, '')), 'B') ||
    setweight(to_tsvector('indian_search', COALESCE(party, '')), 'C')
WHERE search_vector IS NULL;

-- Create function for relevance scoring
CREATE OR REPLACE FUNCTION calculate_search_relevance(
    search_query TEXT,
    content_vector tsvector,
    content_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    upvotes INTEGER DEFAULT 0,
    follower_count INTEGER DEFAULT 0
) RETURNS FLOAT AS $$
DECLARE
    base_score FLOAT;
    time_score FLOAT;
    engagement_score FLOAT;
    type_multiplier FLOAT;
BEGIN
    -- Base relevance from full-text search
    base_score := ts_rank_cd(content_vector, plainto_tsquery('indian_search', search_query));
    
    -- Time decay (newer content gets higher score)
    IF created_at IS NOT NULL THEN
        time_score := EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0; -- days ago
        time_score := 1.0 / (1.0 + time_score * 0.1); -- decay factor
    ELSE
        time_score := 1.0;
    END IF;
    
    -- Engagement score (upvotes, followers, etc.)
    engagement_score := 1.0 + (COALESCE(upvotes, 0) * 0.01) + (COALESCE(follower_count, 0) * 0.001);
    
    -- Content type multiplier
    CASE content_type
        WHEN 'user' THEN type_multiplier := 1.0;
        WHEN 'post' THEN type_multiplier := 1.0;
        WHEN 'representative' THEN type_multiplier := 1.2; -- Boost official accounts
        ELSE type_multiplier := 1.0;
    END CASE;
    
    RETURN base_score * time_score * engagement_score * type_multiplier;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for fast search statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS search_stats AS
SELECT 
    'users' as content_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_verified = true) as verified_count,
    AVG(followers_count) as avg_followers
FROM users WHERE is_active = true
UNION ALL
SELECT 
    'posts' as content_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE status = 'open') as verified_count,
    AVG(upvotes) as avg_followers
FROM posts
UNION ALL
SELECT 
    'representatives' as content_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_verified = true) as verified_count,
    0 as avg_followers
FROM representatives;

CREATE UNIQUE INDEX IF NOT EXISTS idx_search_stats_type ON search_stats (content_type);

-- Refresh the materialized view
REFRESH MATERIALIZED VIEW search_stats;

-- Create function to refresh search stats (can be called periodically)
CREATE OR REPLACE FUNCTION refresh_search_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW search_stats;
END;
$$ LANGUAGE plpgsql;

-- Enable pg_trgm extension for fuzzy text search if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create additional helper functions for search

-- Function to get search suggestions based on query
CREATE OR REPLACE FUNCTION get_search_suggestions(query_text TEXT, limit_count INTEGER DEFAULT 5)
RETURNS TABLE(suggestion TEXT, category TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT s.suggestion, s.category
    FROM search_suggestions s
    WHERE s.suggestion ILIKE '%' || query_text || '%'
    ORDER BY s.search_count DESC, s.last_searched_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to log search queries
CREATE OR REPLACE FUNCTION log_search_query(
    query_text TEXT,
    search_type_val TEXT,
    result_count_val INTEGER,
    user_id_val UUID DEFAULT NULL,
    ip_address_val INET DEFAULT NULL,
    search_time_ms_val INTEGER DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO search_analytics (query, search_type, result_count, user_id, ip_address, search_time_ms)
    VALUES (query_text, search_type_val, result_count_val, user_id_val, ip_address_val, search_time_ms_val);
    
    -- Update or insert search suggestion
    INSERT INTO search_suggestions (suggestion, category, search_count, last_searched_at)
    VALUES (query_text, 'recent', 1, NOW())
    ON CONFLICT (suggestion) 
    DO UPDATE SET 
        search_count = search_suggestions.search_count + 1,
        last_searched_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Create function to get trending searches
CREATE OR REPLACE FUNCTION get_trending_searches(limit_count INTEGER DEFAULT 10)
RETURNS TABLE(query TEXT, search_count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT sa.query, COUNT(*) as search_count
    FROM search_analytics sa
    WHERE sa.created_at >= NOW() - INTERVAL '7 days'
    GROUP BY sa.query
    ORDER BY search_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Ensure all search optimizations are applied
ANALYZE users;
ANALYZE posts;
ANALYZE representatives;
ANALYZE search_analytics;
ANALYZE search_suggestions;
