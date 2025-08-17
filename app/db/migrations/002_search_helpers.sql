-- Search Optimization Migration - Part 4: Helper Functions

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
    base_score := ts_rank_cd(content_vector, plainto_tsquery('english', search_query));
    
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

-- Analyze tables for better query planning
ANALYZE users;
ANALYZE posts;
ANALYZE representatives;
ANALYZE search_analytics;
ANALYZE search_suggestions;
