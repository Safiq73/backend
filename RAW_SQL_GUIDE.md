# CivicPulse Raw SQL Implementation Guide

## Overview
This guide provides a complete raw SQL implementation for CivicPulse using PostgreSQL with PostGIS for spatial operations. The system supports civic issue reporting, geo-tagged posts, representative assignment based on spatial boundaries, full-text search, and comprehensive analytics.

## Database Schema

### Core Tables Structure

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types for data integrity
CREATE TYPE user_role AS ENUM ('citizen', 'representative', 'admin', 'moderator');
CREATE TYPE issue_type AS ENUM ('infrastructure', 'safety', 'environment', 'transportation', 'community', 'planning', 'utilities');
CREATE TYPE issue_status AS ENUM ('open', 'in_progress', 'resolved', 'closed', 'duplicate');
CREATE TYPE notification_type AS ENUM ('issue_update', 'comment', 'vote', 'assignment', 'resolution', 'mention', 'follow');
CREATE TYPE media_type AS ENUM ('image', 'video', 'document', 'audio');
CREATE TYPE vote_type AS ENUM ('upvote', 'downvote');
```

### 1. Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    cover_photo_url TEXT,
    role user_role NOT NULL DEFAULT 'citizen',
    phone VARCHAR(20),
    address TEXT,
    bio TEXT,
    verified BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    -- Full-text search vector
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', name || ' ' || COALESCE(email, '') || ' ' || COALESCE(bio, ''))
    ) STORED
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_active ON users (active);
CREATE INDEX idx_users_search ON users USING GIN (search_vector);
```

### 2. Issues Table (Geo-tagged Posts)
```sql
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location GEOMETRY(Point, 4326) NOT NULL, -- PostGIS point (longitude, latitude)
    address TEXT,
    issue_type issue_type NOT NULL,
    status issue_status DEFAULT 'open',
    priority_score FLOAT DEFAULT 0.0,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_representative_id UUID REFERENCES representatives(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_note TEXT,
    -- Full-text search vector
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', title || ' ' || description || ' ' || COALESCE(address, ''))
    ) STORED
);

-- Spatial and performance indexes
CREATE INDEX idx_issues_location ON issues USING GIST (location);
CREATE INDEX idx_issues_user_id ON issues (user_id);
CREATE INDEX idx_issues_status ON issues (status);
CREATE INDEX idx_issues_type ON issues (issue_type);
CREATE INDEX idx_issues_created_at ON issues (created_at);
CREATE INDEX idx_issues_representative ON issues (assigned_representative_id);
CREATE INDEX idx_issues_search ON issues USING GIN (search_vector);
```

### 3. Representatives Table (Spatial Boundaries)
```sql
CREATE TABLE representatives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL, -- e.g., "City Council Member", "Mayor", "State Senator"
    office VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    website TEXT,
    photo_url TEXT,
    bio TEXT,
    political_party VARCHAR(100),
    jurisdiction_name VARCHAR(255) NOT NULL, -- e.g., "District 5", "San Francisco"
    jurisdiction_type VARCHAR(50) NOT NULL, -- 'city', 'county', 'state', 'federal'
    jurisdiction_boundary GEOMETRY(MultiPolygon, 4326), -- PostGIS boundary
    term_start_date DATE,
    term_end_date DATE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Spatial index for boundary queries
CREATE INDEX idx_representatives_boundary ON representatives USING GIST (jurisdiction_boundary);
CREATE INDEX idx_representatives_active ON representatives (active);
CREATE INDEX idx_representatives_type ON representatives (jurisdiction_type);
```

### 4. Comments Table (Threaded)
```sql
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES comments(id),
    thread_level INTEGER DEFAULT 0,
    thread_path TEXT, -- Materialized path for efficient threading
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_comments_issue_id ON comments (issue_id);
CREATE INDEX idx_comments_user_id ON comments (user_id);
CREATE INDEX idx_comments_parent ON comments (parent_comment_id);
CREATE INDEX idx_comments_thread_path ON comments (thread_path);
```

### 5. Votes Table
```sql
CREATE TABLE votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    issue_id UUID REFERENCES issues(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    vote_type vote_type NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one vote per user per item
    CONSTRAINT unique_issue_vote UNIQUE (user_id, issue_id),
    CONSTRAINT unique_comment_vote UNIQUE (user_id, comment_id),
    -- Ensure vote is for either issue or comment, not both
    CONSTRAINT vote_target_check CHECK (
        (issue_id IS NOT NULL AND comment_id IS NULL) OR 
        (issue_id IS NULL AND comment_id IS NOT NULL)
    )
);

CREATE INDEX idx_votes_user_id ON votes (user_id);
CREATE INDEX idx_votes_issue_id ON votes (issue_id);
CREATE INDEX idx_votes_comment_id ON votes (comment_id);
```

### 6. Media Table (External Storage)
```sql
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    media_type media_type NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    url TEXT NOT NULL, -- S3 or external storage URL
    thumbnail_url TEXT,
    issue_id UUID REFERENCES issues(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure media belongs to either issue or comment
    CONSTRAINT media_parent_check CHECK (
        (issue_id IS NOT NULL AND comment_id IS NULL) OR 
        (issue_id IS NULL AND comment_id IS NOT NULL)
    )
);

CREATE INDEX idx_media_issue_id ON media (issue_id);
CREATE INDEX idx_media_comment_id ON media (comment_id);
CREATE INDEX idx_media_user_id ON media (uploaded_by_user_id);
CREATE INDEX idx_media_type ON media (media_type);
```

### 7. Notifications Table
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type notification_type NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    issue_id UUID REFERENCES issues(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(id), -- Who triggered the notification
    metadata JSONB, -- Additional data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications (user_id);
CREATE INDEX idx_notifications_read ON notifications (user_id, is_read);
CREATE INDEX idx_notifications_created_at ON notifications (created_at);
```

### 8. Analytics Tables
```sql
-- Daily analytics aggregation
CREATE TABLE daily_analytics (
    date DATE PRIMARY KEY,
    total_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,
    new_issues INTEGER DEFAULT 0,
    resolved_issues INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    new_comments INTEGER DEFAULT 0,
    total_votes INTEGER DEFAULT 0,
    new_votes INTEGER DEFAULT 0,
    avg_resolution_time_hours FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Issue activity tracking
CREATE TABLE issue_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    activity_type VARCHAR(50) NOT NULL, -- 'created', 'updated', 'commented', 'voted', 'assigned', 'resolved'
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_issue_activities_issue_id ON issue_activities (issue_id);
CREATE INDEX idx_issue_activities_user_id ON issue_activities (user_id);
CREATE INDEX idx_issue_activities_type ON issue_activities (activity_type);
```

## Essential Raw SQL Queries

### 1. Insert Issue with Location
```sql
-- Insert a new geo-tagged issue
INSERT INTO issues (
    title, description, user_id, location, address, issue_type
) VALUES (
    $1, $2, $3, ST_Point($4, $5), $6, $7
) RETURNING id, created_at;

-- Example parameters: title, description, user_id, longitude, latitude, address, issue_type
```

### 2. Find Representative for a Location
```sql
-- Find which representative covers a specific point
SELECT r.id, r.name, r.title, r.office, r.jurisdiction_name
FROM representatives r
WHERE r.active = true
  AND ST_Contains(r.jurisdiction_boundary, ST_Point($1, $2))
ORDER BY r.jurisdiction_type DESC; -- Prioritize more local representatives

-- Parameters: longitude, latitude
```

### 3. Spatial Query - Issues Near Location
```sql
-- Find issues within a radius (meters) of a location
SELECT 
    i.id, i.title, i.description, i.status, i.issue_type,
    ST_Y(i.location) as latitude,
    ST_X(i.location) as longitude,
    ST_Distance(i.location::geography, ST_Point($1, $2)::geography) as distance_meters,
    u.name as author_name,
    i.upvotes, i.downvotes, i.comment_count,
    i.created_at
FROM issues i
JOIN users u ON i.user_id = u.id
WHERE ST_DWithin(
    i.location::geography, 
    ST_Point($1, $2)::geography, 
    $3
)
AND i.status != 'closed'
ORDER BY distance_meters, i.created_at DESC
LIMIT $4 OFFSET $5;

-- Parameters: longitude, latitude, radius_meters, limit, offset
```

### 4. Full-Text Search
```sql
-- Search issues by text with ranking
SELECT 
    i.id, i.title, i.description, i.address, i.issue_type, i.status,
    ts_rank(i.search_vector, query) as rank,
    u.name as author_name,
    i.upvotes, i.downvotes, i.comment_count,
    i.created_at
FROM issues i
JOIN users u ON i.user_id = u.id,
     to_tsquery('english', $1) query
WHERE i.search_vector @@ query
ORDER BY rank DESC, i.created_at DESC
LIMIT $2 OFFSET $3;

-- Parameters: search_query (e.g., 'pothole & street'), limit, offset
```

### 5. Vote on Issue
```sql
-- Upsert vote (insert or update existing vote)
INSERT INTO votes (user_id, issue_id, vote_type)
VALUES ($1, $2, $3)
ON CONFLICT (user_id, issue_id) 
DO UPDATE SET vote_type = $3, updated_at = NOW()
RETURNING id;

-- Parameters: user_id, issue_id, vote_type ('upvote' or 'downvote')
```

### 6. Paginated Issue Feed
```sql
-- Get paginated issues with user interaction status
SELECT 
    i.id, i.title, i.description, i.status, i.issue_type,
    ST_Y(i.location) as latitude,
    ST_X(i.location) as longitude,
    u.name as author_name, u.avatar_url,
    i.upvotes, i.downvotes, i.comment_count, i.view_count,
    i.created_at, i.last_activity_at,
    -- User interaction status
    CASE WHEN uv.vote_type = 'upvote' THEN true ELSE false END as is_upvoted,
    CASE WHEN uv.vote_type = 'downvote' THEN true ELSE false END as is_downvoted,
    CASE WHEN si.user_id IS NOT NULL THEN true ELSE false END as is_saved
FROM issues i
JOIN users u ON i.user_id = u.id
LEFT JOIN votes uv ON uv.issue_id = i.id AND uv.user_id = $1
LEFT JOIN saved_issues si ON si.issue_id = i.id AND si.user_id = $1
WHERE ($2::issue_status IS NULL OR i.status = $2)
  AND ($3::issue_type IS NULL OR i.issue_type = $3)
ORDER BY 
    CASE WHEN $4 = 'recent' THEN i.created_at END DESC,
    CASE WHEN $4 = 'popular' THEN (i.upvotes - i.downvotes) END DESC,
    CASE WHEN $4 = 'active' THEN i.last_activity_at END DESC
LIMIT $5 OFFSET $6;

-- Parameters: current_user_id, status_filter, type_filter, sort_by, limit, offset
```

### 7. Threaded Comments
```sql
-- Get threaded comments for an issue
SELECT 
    c.id, c.content, c.thread_level, c.thread_path,
    c.upvotes, c.downvotes, c.reply_count,
    u.name as author_name, u.avatar_url,
    c.created_at, c.is_edited,
    CASE WHEN cv.vote_type = 'upvote' THEN true ELSE false END as is_upvoted,
    CASE WHEN cv.vote_type = 'downvote' THEN true ELSE false END as is_downvoted
FROM comments c
JOIN users u ON c.user_id = u.id
LEFT JOIN votes cv ON cv.comment_id = c.id AND cv.user_id = $2
WHERE c.issue_id = $1
ORDER BY c.thread_path
LIMIT $3 OFFSET $4;

-- Parameters: issue_id, current_user_id, limit, offset
```

### 8. Mark Notifications as Read
```sql
-- Mark specific notifications as read
UPDATE notifications 
SET is_read = true, updated_at = NOW()
WHERE user_id = $1 AND id = ANY($2::UUID[])
RETURNING id;

-- Mark all notifications as read for user
UPDATE notifications 
SET is_read = true, updated_at = NOW()
WHERE user_id = $1 AND is_read = false
RETURNING COUNT(*);

-- Parameters: user_id, notification_ids_array
```

### 9. Analytics Queries
```sql
-- Get daily analytics
SELECT * FROM daily_analytics 
WHERE date >= $1 AND date <= $2
ORDER BY date;

-- Issues by representative
SELECT 
    r.name, r.title, r.jurisdiction_name,
    COUNT(i.id) as total_issues,
    COUNT(CASE WHEN i.status = 'resolved' THEN 1 END) as resolved_issues,
    AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.created_at))/3600) as avg_resolution_hours
FROM representatives r
LEFT JOIN issues i ON i.assigned_representative_id = r.id
WHERE r.active = true
GROUP BY r.id, r.name, r.title, r.jurisdiction_name
ORDER BY total_issues DESC;

-- Popular issue types by area
SELECT 
    issue_type,
    COUNT(*) as count,
    AVG(upvotes - downvotes) as avg_score
FROM issues
WHERE created_at >= $1
GROUP BY issue_type
ORDER BY count DESC;
```

### 10. Representative Assignment
```sql
-- Auto-assign representative to issue based on location
UPDATE issues 
SET assigned_representative_id = (
    SELECT r.id
    FROM representatives r
    WHERE r.active = true
      AND ST_Contains(r.jurisdiction_boundary, issues.location)
    ORDER BY 
        CASE r.jurisdiction_type
            WHEN 'city' THEN 1
            WHEN 'county' THEN 2
            WHEN 'state' THEN 3
            WHEN 'federal' THEN 4
        END
    LIMIT 1
)
WHERE id = $1 AND assigned_representative_id IS NULL
RETURNING assigned_representative_id;

-- Parameters: issue_id
```

## Performance Optimization Tips

### 1. Connection Pooling
```python
# Use asyncpg connection pool
pool = await asyncpg.create_pool(
    database_url,
    min_size=5,
    max_size=20,
    command_timeout=60
)
```

### 2. Prepared Statements
```python
# Prepare frequently used queries
async def prepare_statements(connection):
    await connection.prepare("""
        SELECT * FROM issues WHERE ST_DWithin(location::geography, $1::geography, $2)
    """)
```

### 3. Batch Operations
```python
# Use executemany for bulk inserts
await connection.executemany("""
    INSERT INTO notifications (user_id, title, message, notification_type)
    VALUES ($1, $2, $3, $4)
""", notification_data)
```

This raw SQL implementation gives you complete control over performance while leveraging PostgreSQL's advanced spatial and full-text search capabilities.
