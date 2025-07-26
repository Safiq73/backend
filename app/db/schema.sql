-- CivicPulse Database Schema - Corrected for Implementation Alignment
-- This schema aligns with the actual implementation in db_service_new.py

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types for better data integrity
CREATE TYPE post_type AS ENUM ('issue', 'announcement', 'news', 'accomplishment', 'discussion');
CREATE TYPE post_status AS ENUM ('open', 'in_progress', 'resolved', 'closed');
CREATE TYPE notification_type AS ENUM ('issue_update', 'comment', 'vote', 'assignment', 'resolution', 'mention', 'follow');
CREATE TYPE vote_type AS ENUM ('upvote', 'downvote');

-- Roles table for user roles
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(100) NOT NULL UNIQUE,
    abbreviation VARCHAR(20) UNIQUE,
    level_rank INTEGER,
    role_type VARCHAR(50),
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
    role UUID REFERENCES roles(id) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Full-text search vector (will be updated via triggers)
    search_vector tsvector
);

-- Indexes for users table
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_active ON users (is_active);
CREATE INDEX idx_users_search ON users USING GIN (search_vector);
CREATE INDEX idx_users_created_at ON users (created_at DESC);

-- Posts table - aligned with implementation
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
