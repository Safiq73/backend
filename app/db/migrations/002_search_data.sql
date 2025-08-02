-- Search Optimization Migration - Part 3: Analytics and Data

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
-- Update users search vectors
UPDATE users SET search_vector = 
    setweight(to_tsvector('english', COALESCE(username, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(display_name, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(bio, '')), 'B')
WHERE search_vector IS NULL;

-- Update posts search vectors
UPDATE posts SET search_vector = 
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(content, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(location, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(array_to_string(tags, ' '), '')), 'C')
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
    setweight(to_tsvector('english', COALESCE(cached_name, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(cached_designation, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(cached_constituency, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(party, '')), 'C')
WHERE search_vector IS NULL;
