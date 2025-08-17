-- Search Optimization Migration - Part 2: Functions and Triggers

-- Create function to update user search vector
CREATE OR REPLACE FUNCTION update_user_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.username, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.display_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.bio, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create function to update post search vector
CREATE OR REPLACE FUNCTION update_post_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
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
        setweight(to_tsvector('english', COALESCE(NEW.cached_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.cached_designation, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.cached_constituency, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.party, '')), 'C');

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
