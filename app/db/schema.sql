-- CivicPulse Database Schema - Corrected for Implementation Alignment
-- This schema aligns with the actual implementation in db_service_new.py

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For fuzzy text search

-- Create full-text search configuration for better Indian context
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS indian_search (COPY = english);

-- Create ENUM types for better data integrity
CREATE TYPE post_type AS ENUM ('issue', 'announcement', 'news', 'accomplishment', 'discussion');
CREATE TYPE post_status AS ENUM ('open', 'in_progress', 'resolved', 'closed');
CREATE TYPE notification_type AS ENUM ('issue_update', 'comment', 'vote', 'assignment', 'resolution', 'mention', 'follow');
CREATE TYPE vote_type AS ENUM ('upvote', 'downvote');

-- Titles table for user titles (previously roles - renamed to avoid confusion with permission roles)
CREATE TABLE titles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title_name VARCHAR(100) NOT NULL UNIQUE,
    abbreviation VARCHAR(20) UNIQUE,
    level_rank INTEGER,
    title_type VARCHAR(50),
    description TEXT,
    level VARCHAR(50),
    is_elected BOOLEAN DEFAULT FALSE,
    term_length INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table - aligned with implementation
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    rep_accounts UUID[] DEFAULT NULL, -- Array of representative IDs this user can manage
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Full-text search vector (will be updated via triggers)
    search_vector tsvector
);

-- Indexes for users table
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_active ON users (is_active);
CREATE INDEX idx_users_search ON users USING GIN (search_vector);
CREATE INDEX idx_users_created_at ON users (created_at DESC);
CREATE INDEX idx_users_rep_accounts ON users USING GIN (rep_accounts);

-- Enhanced search indexes for users
CREATE INDEX idx_users_search_vector ON users USING GIN (search_vector);
CREATE INDEX idx_users_username_trgm ON users USING GIN (username gin_trgm_ops);
CREATE INDEX idx_users_display_name_trgm ON users USING GIN (display_name gin_trgm_ops);
CREATE INDEX idx_users_bio_trgm ON users USING GIN (bio gin_trgm_ops);
CREATE INDEX idx_users_followers_count ON users (followers_count DESC);
CREATE INDEX idx_users_verified ON users (is_verified, followers_count DESC);
CREATE INDEX idx_users_active_verified ON users (is_active, is_verified, followers_count DESC);

-- Posts table - aligned with implementation
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignee UUID REFERENCES representatives(id) ON DELETE SET NULL, -- Representative assigned to handle this post
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    post_type post_type NOT NULL DEFAULT 'discussion',
    status post_status DEFAULT 'open',
    area VARCHAR(100), -- Geographic area/location
    category VARCHAR(100), -- Category for filtering
    location VARCHAR(255), -- Location description
    latitude DECIMAL(10, 8), -- Geographic latitude (India: 6.5° to 37.5° N)
    longitude DECIMAL(11, 8), -- Geographic longitude (India: 68° to 97.5° E)
    tags TEXT[], -- Array of tags
    media_urls TEXT[], -- Array of media URLs (standardized name)
    -- Vote counts (updated via triggers)
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    priority_score INTEGER DEFAULT 0,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Full-text search vector (will be updated via triggers)
    search_vector tsvector,
    -- Constraints for India geographic bounds
    CONSTRAINT check_latitude_india_bounds 
        CHECK (latitude IS NULL OR (latitude >= 6.5 AND latitude <= 37.5)),
    CONSTRAINT check_longitude_india_bounds 
        CHECK (longitude IS NULL OR (longitude >= 68.0 AND longitude <= 97.5))
);

-- Indexes for posts table
CREATE INDEX idx_posts_user_id ON posts (user_id);
CREATE INDEX idx_posts_assignee ON posts (assignee);
CREATE INDEX idx_posts_status ON posts (status);
CREATE INDEX idx_posts_type ON posts (post_type);
CREATE INDEX idx_posts_area ON posts (area);
CREATE INDEX idx_posts_category ON posts (category);
CREATE INDEX idx_posts_created_at ON posts (created_at DESC);
CREATE INDEX idx_posts_updated_at ON posts (updated_at DESC);
CREATE INDEX idx_posts_last_activity ON posts (last_activity_at DESC);
CREATE INDEX idx_posts_search ON posts USING GIN (search_vector);
CREATE INDEX idx_posts_priority ON posts (priority_score DESC);
CREATE INDEX idx_posts_tags ON posts USING GIN (tags);
-- Spatial indexes for location-based queries
CREATE INDEX idx_posts_coordinates ON posts (latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
CREATE INDEX idx_posts_latitude ON posts (latitude) WHERE latitude IS NOT NULL;
CREATE INDEX idx_posts_longitude ON posts (longitude) WHERE longitude IS NOT NULL;

-- Enhanced search indexes for posts
CREATE INDEX idx_posts_search_vector ON posts USING GIN (search_vector);
CREATE INDEX idx_posts_title_trgm ON posts USING GIN (title gin_trgm_ops);
CREATE INDEX idx_posts_content_trgm ON posts USING GIN (content gin_trgm_ops);
CREATE INDEX idx_posts_location_trgm ON posts USING GIN (location gin_trgm_ops);
CREATE INDEX idx_posts_upvotes ON posts (upvotes DESC);
CREATE INDEX idx_posts_created_at_desc ON posts (created_at DESC);
CREATE INDEX idx_posts_status_type ON posts (status, post_type);
CREATE INDEX idx_posts_type_status_created ON posts (post_type, status, created_at DESC);
CREATE INDEX idx_posts_assignee_status ON posts (assignee, status) WHERE assignee IS NOT NULL;

-- Comments table with threading support
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP WITH TIME ZONE,
    -- Vote counts (updated via triggers)
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    -- Comment threading support
    thread_level INTEGER DEFAULT 0,
    thread_path TEXT, -- e.g., '1.2.5' for nested comments
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Full-text search vector (will be updated via triggers)
    search_vector tsvector
);

CREATE INDEX idx_comments_post_id ON comments (post_id);
CREATE INDEX idx_comments_user_id ON comments (user_id);
CREATE INDEX idx_comments_parent ON comments (parent_id);
CREATE INDEX idx_comments_created_at ON comments (created_at DESC);
CREATE INDEX idx_comments_thread_path ON comments (thread_path);
CREATE INDEX idx_comments_search ON comments USING GIN (search_vector);

-- Votes table for posts and comments
CREATE TABLE votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    vote_type vote_type NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Ensure user can only vote once per item
    CONSTRAINT unique_post_vote UNIQUE (user_id, post_id),
    CONSTRAINT unique_comment_vote UNIQUE (user_id, comment_id),
    -- Ensure vote is for either post or comment, not both
    CONSTRAINT vote_target_check CHECK (
        (post_id IS NOT NULL AND comment_id IS NULL) OR 
        (post_id IS NULL AND comment_id IS NOT NULL)
    )
);

CREATE INDEX idx_votes_user_id ON votes (user_id);
CREATE INDEX idx_votes_post_id ON votes (post_id);
CREATE INDEX idx_votes_comment_id ON votes (comment_id);
CREATE INDEX idx_votes_type ON votes (vote_type);

-- Notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    triggered_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notification_type notification_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    action_url TEXT,
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications (user_id);
CREATE INDEX idx_notifications_read ON notifications (user_id, read, created_at DESC);
CREATE INDEX idx_notifications_type ON notifications (notification_type);
CREATE INDEX idx_notifications_created_at ON notifications (created_at DESC);

-- Saved posts
CREATE TABLE saved_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, post_id)
);

CREATE INDEX idx_saved_posts_user_id ON saved_posts (user_id);
CREATE INDEX idx_saved_posts_created_at ON saved_posts (created_at DESC);

-- User sessions for JWT token tracking
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_agent TEXT,
    ip_address INET,
    is_mobile BOOLEAN DEFAULT FALSE,
    revoked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_sessions_user_id ON user_sessions (user_id);
CREATE INDEX idx_sessions_token_hash ON user_sessions (refresh_token_hash);
CREATE INDEX idx_sessions_expires ON user_sessions (expires_at);
CREATE INDEX idx_sessions_active ON user_sessions (user_id, revoked, expires_at);

-- Performance optimization: Partial indexes for common queries
CREATE INDEX idx_posts_open_recent ON posts (created_at DESC) WHERE status = 'open';
CREATE INDEX idx_posts_user_open ON posts (user_id, created_at DESC) WHERE status = 'open';
CREATE INDEX idx_notifications_unread ON notifications (user_id, created_at DESC) WHERE read = FALSE;

-- Follows table for user follow/unfollow functionality
CREATE TABLE follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mutual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Primary key is the combination of follower_id and followed_id
    PRIMARY KEY (follower_id, followed_id),
    
    -- Prevent self-following
    CONSTRAINT no_self_follow CHECK (follower_id != followed_id)
);

-- Create indexes for follows table performance
CREATE INDEX idx_follows_follower_id ON follows (follower_id);
CREATE INDEX idx_follows_followed_id ON follows (followed_id);
CREATE INDEX idx_follows_mutual ON follows (mutual);
CREATE INDEX idx_follows_created_at ON follows (created_at DESC);

-- Create compound indexes for common queries
CREATE INDEX idx_follows_follower_mutual ON follows (follower_id, mutual);
CREATE INDEX idx_follows_followed_mutual ON follows (followed_id, mutual);

-- Update existing data with search vectors when schema is applied
-- This should be run after the schema is created

-- Update users search vectors for existing data
UPDATE users SET search_vector = 
    setweight(to_tsvector('indian_search', COALESCE(username, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(display_name, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(bio, '')), 'B')
WHERE search_vector IS NULL;

-- Update posts search vectors for existing data
UPDATE posts SET search_vector = 
    setweight(to_tsvector('indian_search', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('indian_search', COALESCE(content, '')), 'B') ||
    setweight(to_tsvector('indian_search', COALESCE(location, '')), 'C') ||
    setweight(to_tsvector('indian_search', COALESCE(array_to_string(tags, ' '), '')), 'C')
WHERE search_vector IS NULL;

-- Update comments search vectors for existing data
UPDATE comments SET search_vector = 
    setweight(to_tsvector('indian_search', COALESCE(content, '')), 'A')
WHERE search_vector IS NULL;

-- Refresh the materialized view
REFRESH MATERIALIZED VIEW search_stats;

-- Analyze tables for better query planning
ANALYZE users;
ANALYZE posts;
ANALYZE comments;
ANALYZE search_analytics;
ANALYZE search_suggestions;

-- Functions and triggers for follow functionality
-- Create function to update mutual status
CREATE OR REPLACE FUNCTION update_mutual_status()
RETURNS TRIGGER AS $$
BEGIN
    -- If this is an INSERT operation
    IF TG_OP = 'INSERT' THEN
        -- Check if the reverse relationship exists and update mutual status
        IF EXISTS (
            SELECT 1 FROM follows 
            WHERE follower_id = NEW.followed_id AND followed_id = NEW.follower_id
        ) THEN
            -- Update both relationships to mutual = true
            UPDATE follows 
            SET mutual = TRUE 
            WHERE (follower_id = NEW.follower_id AND followed_id = NEW.followed_id)
               OR (follower_id = NEW.followed_id AND followed_id = NEW.follower_id);
        END IF;
        RETURN NEW;
    END IF;
    
    -- If this is a DELETE operation
    IF TG_OP = 'DELETE' THEN
        -- Update the reverse relationship to mutual = false if it exists
        UPDATE follows 
        SET mutual = FALSE 
        WHERE follower_id = OLD.followed_id AND followed_id = OLD.follower_id;
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update mutual status
CREATE TRIGGER follows_mutual_trigger
    AFTER INSERT OR DELETE ON follows
    FOR EACH ROW
    EXECUTE FUNCTION update_mutual_status();

-- Create function to update user follow counts
CREATE OR REPLACE FUNCTION update_user_follow_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- If this is an INSERT operation
    IF TG_OP = 'INSERT' THEN
        -- Increment following count for follower
        UPDATE users 
        SET following_count = following_count + 1 
        WHERE id = NEW.follower_id;
        
        -- Increment followers count for followed user
        UPDATE users 
        SET followers_count = followers_count + 1 
        WHERE id = NEW.followed_id;
        
        RETURN NEW;
    END IF;
    
    -- If this is a DELETE operation
    IF TG_OP = 'DELETE' THEN
        -- Decrement following count for follower
        UPDATE users 
        SET following_count = GREATEST(following_count - 1, 0)
        WHERE id = OLD.follower_id;
        
        -- Decrement followers count for followed user
        UPDATE users 
        SET followers_count = GREATEST(followers_count - 1, 0)
        WHERE id = OLD.followed_id;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update user follow counts
CREATE TRIGGER follows_count_trigger
    AFTER INSERT OR DELETE ON follows
    FOR EACH ROW
    EXECUTE FUNCTION update_user_follow_counts();

-- Search analytics table for tracking popular searches
CREATE TABLE search_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT NOT NULL,
    search_type TEXT, -- 'all', 'people', 'posts', 'representatives'
    result_count INTEGER DEFAULT 0,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    search_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_search_analytics_query ON search_analytics (query);
CREATE INDEX idx_search_analytics_created_at ON search_analytics (created_at DESC);
CREATE INDEX idx_search_analytics_user_id ON search_analytics (user_id);
CREATE INDEX idx_search_analytics_type ON search_analytics (search_type);

-- Search suggestions table for popular search terms
CREATE TABLE search_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suggestion TEXT UNIQUE NOT NULL,
    category TEXT, -- 'popular', 'trending', 'recent'
    search_count INTEGER DEFAULT 0,
    last_searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_search_suggestions_category ON search_suggestions (category, search_count DESC);
CREATE INDEX idx_search_suggestions_count ON search_suggestions (search_count DESC);

-- Insert default search suggestions
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

-- Search Functions and Triggers

-- Function to update user search vector
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

-- Function to update post search vector
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

-- Function to update comment search vector
CREATE OR REPLACE FUNCTION update_comment_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('indian_search', COALESCE(NEW.content, '')), 'A');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function for relevance scoring
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

-- Function to get trending searches
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

-- Create triggers to automatically update search vectors
CREATE TRIGGER trigger_update_user_search_vector
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_search_vector();

CREATE TRIGGER trigger_update_post_search_vector
    BEFORE INSERT OR UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_post_search_vector();

CREATE TRIGGER trigger_update_comment_search_vector
    BEFORE INSERT OR UPDATE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_comment_search_vector();

-- Materialized view for fast search statistics
CREATE MATERIALIZED VIEW search_stats AS
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
FROM posts;

CREATE UNIQUE INDEX idx_search_stats_type ON search_stats (content_type);

-- Function to refresh search stats (can be called periodically)
CREATE OR REPLACE FUNCTION refresh_search_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW search_stats;
END;
$$ LANGUAGE plpgsql;
CREATE INDEX idx_follows_followed_mutual ON follows (followed_id, mutual);
