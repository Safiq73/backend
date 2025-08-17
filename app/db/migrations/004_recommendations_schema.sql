-- Recommendations System Schema Migration
-- Phase 1: Core tables for interactions, post quality, and user affinities

-- Create enum for interaction event types
CREATE TYPE interaction_event_type AS ENUM (
    'impression',
    'click',
    'like',
    'comment',
    'share',
    'save',
    'hide',
    'follow_author'
);

-- Interactions table: stores all user engagement events
CREATE TABLE IF NOT EXISTS interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    post_id UUID NOT NULL,
    event_type interaction_event_type NOT NULL,
    weight FLOAT DEFAULT 1.0,
    surface VARCHAR(50) DEFAULT 'main_feed', -- feed surface (main, explore, etc)
    session_id VARCHAR(100), -- optional session tracking
    device_type VARCHAR(20), -- mobile, desktop, tablet
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for interactions table
CREATE INDEX idx_interactions_user_created ON interactions(user_id, created_at DESC);
CREATE INDEX idx_interactions_post_created ON interactions(post_id, created_at DESC);
CREATE INDEX idx_interactions_event_created ON interactions(event_type, created_at DESC);
CREATE INDEX idx_interactions_user_post_event ON interactions(user_id, post_id, event_type);
-- Partial index for positive engagement events only
CREATE INDEX idx_interactions_positive_events ON interactions(user_id, post_id, created_at DESC) 
    WHERE event_type IN ('click', 'like', 'comment', 'share', 'save');

-- Post topics table: maps posts to topics/categories
CREATE TABLE IF NOT EXISTS post_topics (
    post_id UUID NOT NULL,
    topic_id INTEGER NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (post_id, topic_id)
);

-- Indexes for post_topics
CREATE INDEX idx_post_topics_topic_post ON post_topics(topic_id, post_id);
CREATE INDEX idx_post_topics_post ON post_topics(post_id);

-- Post quality metrics table: aggregated engagement metrics per post
CREATE TABLE IF NOT EXISTS post_quality (
    post_id UUID PRIMARY KEY,
    impressions_count INTEGER DEFAULT 0,
    clicks_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    saves_count INTEGER DEFAULT 0,
    hides_count INTEGER DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0.0,
    ctr_bayesian FLOAT DEFAULT 0.0, -- Bayesian CTR with priors
    recency_decay FLOAT DEFAULT 1.0,
    quality_score FLOAT DEFAULT 0.0,
    last_interaction_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for post_quality
CREATE INDEX idx_post_quality_score ON post_quality(quality_score DESC);
CREATE INDEX idx_post_quality_updated ON post_quality(updated_at);
CREATE INDEX idx_post_quality_last_interaction ON post_quality(last_interaction_at DESC);

-- User topic affinity table: user preferences for topics
CREATE TABLE IF NOT EXISTS user_topic_affinity (
    user_id UUID NOT NULL,
    topic_id INTEGER NOT NULL,
    score FLOAT DEFAULT 0.0,
    interaction_count INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, topic_id)
);

-- Indexes for user_topic_affinity
CREATE INDEX idx_user_topic_affinity_user_score ON user_topic_affinity(user_id, score DESC);
CREATE INDEX idx_user_topic_affinity_topic_score ON user_topic_affinity(topic_id, score DESC);

-- User author affinity table: user preferences for authors
CREATE TABLE IF NOT EXISTS user_author_affinity (
    user_id UUID NOT NULL,
    author_id UUID NOT NULL,
    score FLOAT DEFAULT 0.0,
    interaction_count INTEGER DEFAULT 0,
    is_following BOOLEAN DEFAULT FALSE,
    last_interaction_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, author_id)
);

-- Indexes for user_author_affinity
CREATE INDEX idx_user_author_affinity_user_score ON user_author_affinity(user_id, score DESC);
CREATE INDEX idx_user_author_affinity_following ON user_author_affinity(user_id, is_following, score DESC);

-- Topics table: define available topics/categories
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER REFERENCES topics(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert some default topics for civic engagement
INSERT INTO topics (name, slug, description) VALUES
('Local Government', 'local-government', 'City council, municipal issues, local policies'),
('State Politics', 'state-politics', 'State-level governance and legislation'),
('Federal Politics', 'federal-politics', 'National politics and federal government'),
('Community Events', 'community-events', 'Local events and community gatherings'),
('Public Safety', 'public-safety', 'Police, fire department, emergency services'),
('Infrastructure', 'infrastructure', 'Roads, public transport, utilities'),
('Education', 'education', 'Schools, education policy, academic issues'),
('Healthcare', 'healthcare', 'Public health, healthcare policy'),
('Environment', 'environment', 'Environmental issues, climate, sustainability'),
('Economy', 'economy', 'Economic policy, jobs, business')
ON CONFLICT (slug) DO NOTHING;

-- Function to update post quality metrics
CREATE OR REPLACE FUNCTION update_post_quality_metrics()
RETURNS VOID AS $$
DECLARE
    rec RECORD;
    alpha FLOAT := 3.0; -- Bayesian prior for CTR calculation
    beta FLOAT := 30.0; -- Bayesian prior for CTR calculation
    lambda FLOAT := 0.1; -- Decay rate for recency (per hour)
BEGIN
    -- Update post quality metrics for posts with recent interactions (last 7 days)
    FOR rec IN
        SELECT 
            post_id,
            COUNT(*) FILTER (WHERE event_type = 'impression') as impressions,
            COUNT(*) FILTER (WHERE event_type = 'click') as clicks,
            COUNT(*) FILTER (WHERE event_type = 'like') as likes,
            COUNT(*) FILTER (WHERE event_type = 'comment') as comments,
            COUNT(*) FILTER (WHERE event_type = 'share') as shares,
            COUNT(*) FILTER (WHERE event_type = 'save') as saves,
            COUNT(*) FILTER (WHERE event_type = 'hide') as hides,
            MAX(created_at) as last_interaction
        FROM interactions 
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY post_id
    LOOP
        -- Calculate engagement rate (weighted sum of positive interactions / impressions)
        DECLARE
            engagement_rate FLOAT := 0.0;
            ctr_bayesian FLOAT := 0.0;
            recency_decay FLOAT := 1.0;
            quality_score FLOAT := 0.0;
            age_hours FLOAT;
        BEGIN
            -- Engagement rate calculation
            IF rec.impressions > 0 THEN
                engagement_rate := (
                    0.6 * rec.clicks + 
                    0.2 * rec.likes + 
                    0.15 * rec.comments + 
                    0.05 * rec.shares + 
                    0.05 * rec.saves
                ) / GREATEST(rec.impressions, 1);
            END IF;
            
            -- Bayesian CTR calculation
            IF rec.impressions > 0 THEN
                ctr_bayesian := (rec.clicks + alpha) / (rec.impressions + alpha + beta);
            END IF;
            
            -- Recency decay calculation
            age_hours := EXTRACT(EPOCH FROM (NOW() - rec.last_interaction)) / 3600.0;
            recency_decay := EXP(-lambda * age_hours);
            
            -- Overall quality score
            quality_score := 0.4 * engagement_rate + 0.3 * ctr_bayesian + 0.3 * recency_decay;
            
            -- Upsert into post_quality table
            INSERT INTO post_quality (
                post_id, impressions_count, clicks_count, likes_count, 
                comments_count, shares_count, saves_count, hides_count,
                engagement_rate, ctr_bayesian, recency_decay, quality_score,
                last_interaction_at, updated_at
            ) VALUES (
                rec.post_id, rec.impressions, rec.clicks, rec.likes,
                rec.comments, rec.shares, rec.saves, rec.hides,
                engagement_rate, ctr_bayesian, recency_decay, quality_score,
                rec.last_interaction, NOW()
            )
            ON CONFLICT (post_id) DO UPDATE SET
                impressions_count = EXCLUDED.impressions_count,
                clicks_count = EXCLUDED.clicks_count,
                likes_count = EXCLUDED.likes_count,
                comments_count = EXCLUDED.comments_count,
                shares_count = EXCLUDED.shares_count,
                saves_count = EXCLUDED.saves_count,
                hides_count = EXCLUDED.hides_count,
                engagement_rate = EXCLUDED.engagement_rate,
                ctr_bayesian = EXCLUDED.ctr_bayesian,
                recency_decay = EXCLUDED.recency_decay,
                quality_score = EXCLUDED.quality_score,
                last_interaction_at = EXCLUDED.last_interaction_at,
                updated_at = NOW();
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to update user topic affinities
CREATE OR REPLACE FUNCTION update_user_topic_affinities()
RETURNS VOID AS $$
DECLARE
    rec RECORD;
    lambda FLOAT := 0.05; -- Decay rate for time-based scoring
BEGIN
    -- Update user topic affinities based on recent interactions
    FOR rec IN
        SELECT 
            i.user_id,
            pt.topic_id,
            SUM(
                CASE i.event_type
                    WHEN 'click' THEN 1.0
                    WHEN 'like' THEN 1.2
                    WHEN 'comment' THEN 1.5
                    WHEN 'share' THEN 1.8
                    WHEN 'save' THEN 1.6
                    WHEN 'hide' THEN -2.0
                    ELSE 0.5
                END * EXP(-lambda * EXTRACT(EPOCH FROM (NOW() - i.created_at)) / 3600.0)
            ) as weighted_score,
            COUNT(*) as interaction_count,
            MAX(i.created_at) as last_interaction
        FROM interactions i
        JOIN post_topics pt ON i.post_id = pt.post_id
        WHERE i.created_at >= NOW() - INTERVAL '30 days'
        AND i.event_type != 'impression'
        GROUP BY i.user_id, pt.topic_id
        HAVING SUM(
            CASE i.event_type
                WHEN 'click' THEN 1.0
                WHEN 'like' THEN 1.2
                WHEN 'comment' THEN 1.5
                WHEN 'share' THEN 1.8
                WHEN 'save' THEN 1.6
                WHEN 'hide' THEN -2.0
                ELSE 0.5
            END * EXP(-lambda * EXTRACT(EPOCH FROM (NOW() - i.created_at)) / 3600.0)
        ) > 0.1 -- Only keep meaningful affinities
    LOOP
        INSERT INTO user_topic_affinity (
            user_id, topic_id, score, interaction_count, last_interaction_at, updated_at
        ) VALUES (
            rec.user_id, rec.topic_id, rec.weighted_score, rec.interaction_count, 
            rec.last_interaction, NOW()
        )
        ON CONFLICT (user_id, topic_id) DO UPDATE SET
            score = EXCLUDED.score,
            interaction_count = EXCLUDED.interaction_count,
            last_interaction_at = EXCLUDED.last_interaction_at,
            updated_at = NOW();
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to update user author affinities
CREATE OR REPLACE FUNCTION update_user_author_affinities()
RETURNS VOID AS $$
DECLARE
    rec RECORD;
    lambda FLOAT := 0.05; -- Decay rate for time-based scoring
BEGIN
    -- Update user author affinities based on recent interactions
    FOR rec IN
        SELECT 
            i.user_id,
            p.author_id,
            SUM(
                CASE i.event_type
                    WHEN 'click' THEN 1.0
                    WHEN 'like' THEN 1.2
                    WHEN 'comment' THEN 1.5
                    WHEN 'share' THEN 1.8
                    WHEN 'save' THEN 1.6
                    WHEN 'follow_author' THEN 2.0
                    WHEN 'hide' THEN -2.0
                    ELSE 0.5
                END * EXP(-lambda * EXTRACT(EPOCH FROM (NOW() - i.created_at)) / 3600.0)
            ) as weighted_score,
            COUNT(*) as interaction_count,
            MAX(i.created_at) as last_interaction,
            BOOL_OR(i.event_type = 'follow_author') as is_following
        FROM interactions i
        JOIN posts p ON i.post_id = p.id
        WHERE i.created_at >= NOW() - INTERVAL '30 days'
        AND i.event_type != 'impression'
        GROUP BY i.user_id, p.author_id
        HAVING SUM(
            CASE i.event_type
                WHEN 'click' THEN 1.0
                WHEN 'like' THEN 1.2
                WHEN 'comment' THEN 1.5
                WHEN 'share' THEN 1.8
                WHEN 'save' THEN 1.6
                WHEN 'follow_author' THEN 2.0
                WHEN 'hide' THEN -2.0
                ELSE 0.5
            END * EXP(-lambda * EXTRACT(EPOCH FROM (NOW() - i.created_at)) / 3600.0)
        ) > 0.1 -- Only keep meaningful affinities
    LOOP
        INSERT INTO user_author_affinity (
            user_id, author_id, score, interaction_count, is_following,
            last_interaction_at, updated_at
        ) VALUES (
            rec.user_id, rec.author_id, rec.weighted_score, rec.interaction_count, 
            rec.is_following, rec.last_interaction, NOW()
        )
        ON CONFLICT (user_id, author_id) DO UPDATE SET
            score = EXCLUDED.score,
            interaction_count = EXCLUDED.interaction_count,
            is_following = EXCLUDED.is_following,
            last_interaction_at = EXCLUDED.last_interaction_at,
            updated_at = NOW();
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create a simple materialized view for trending posts (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS trending_posts AS
SELECT 
    pq.post_id,
    pq.quality_score,
    pq.engagement_rate,
    pq.recency_decay,
    p.created_at as post_created_at,
    p.author_id,
    p.title,
    p.content
FROM post_quality pq
JOIN posts p ON pq.post_id = p.id
WHERE pq.last_interaction_at >= NOW() - INTERVAL '48 hours'
AND pq.quality_score > 0.01
ORDER BY pq.quality_score DESC;

-- Index for trending posts view
CREATE UNIQUE INDEX idx_trending_posts_id ON trending_posts(post_id);
CREATE INDEX idx_trending_posts_score ON trending_posts(quality_score DESC);

-- Add comments explaining the schema
COMMENT ON TABLE interactions IS 'Stores all user engagement events for recommendations';
COMMENT ON TABLE post_quality IS 'Aggregated engagement metrics and quality scores per post';
COMMENT ON TABLE user_topic_affinity IS 'User preferences for topics based on interaction history';
COMMENT ON TABLE user_author_affinity IS 'User preferences for authors based on interaction history';
COMMENT ON TABLE topics IS 'Available topics/categories for content classification';
