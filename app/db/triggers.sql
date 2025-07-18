-- Database triggers for maintaining counts and activity tracking
-- These triggers automatically update vote counts, comment counts, and track activities

-- Function to update issue vote counts
CREATE OR REPLACE FUNCTION update_issue_vote_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE issues SET
            upvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE issue_id = NEW.issue_id AND vote_type = 'upvote'
            ),
            downvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE issue_id = NEW.issue_id AND vote_type = 'downvote'
            ),
            last_activity_at = NOW()
        WHERE id = NEW.issue_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE issues SET
            upvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE issue_id = OLD.issue_id AND vote_type = 'upvote'
            ),
            downvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE issue_id = OLD.issue_id AND vote_type = 'downvote'
            ),
            last_activity_at = NOW()
        WHERE id = OLD.issue_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for issue vote counts
DROP TRIGGER IF EXISTS trigger_update_issue_vote_counts ON votes;
CREATE TRIGGER trigger_update_issue_vote_counts
    AFTER INSERT OR UPDATE OR DELETE ON votes
    FOR EACH ROW
    EXECUTE FUNCTION update_issue_vote_counts();

-- Function to update comment vote counts
CREATE OR REPLACE FUNCTION update_comment_vote_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE comments SET
            upvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE comment_id = NEW.comment_id AND vote_type = 'upvote'
            ),
            downvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE comment_id = NEW.comment_id AND vote_type = 'downvote'
            )
        WHERE id = NEW.comment_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE comments SET
            upvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE comment_id = OLD.comment_id AND vote_type = 'upvote'
            ),
            downvotes = (
                SELECT COUNT(*) FROM votes 
                WHERE comment_id = OLD.comment_id AND vote_type = 'downvote'
            )
        WHERE id = OLD.comment_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for comment vote counts
DROP TRIGGER IF EXISTS trigger_update_comment_vote_counts ON votes;
CREATE TRIGGER trigger_update_comment_vote_counts
    AFTER INSERT OR UPDATE OR DELETE ON votes
    FOR EACH ROW
    EXECUTE FUNCTION update_comment_vote_counts();

-- Function to update issue comment counts
CREATE OR REPLACE FUNCTION update_issue_comment_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE issues SET
            comment_count = comment_count + 1,
            last_activity_at = NOW()
        WHERE id = NEW.issue_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE issues SET
            comment_count = GREATEST(comment_count - 1, 0),
            last_activity_at = NOW()
        WHERE id = OLD.issue_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for issue comment counts
DROP TRIGGER IF EXISTS trigger_update_issue_comment_count ON comments;
CREATE TRIGGER trigger_update_issue_comment_count
    AFTER INSERT OR DELETE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_issue_comment_count();

-- Function to update comment reply counts
CREATE OR REPLACE FUNCTION update_comment_reply_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.parent_comment_id IS NOT NULL THEN
        UPDATE comments SET
            reply_count = reply_count + 1
        WHERE id = NEW.parent_comment_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' AND OLD.parent_comment_id IS NOT NULL THEN
        UPDATE comments SET
            reply_count = GREATEST(reply_count - 1, 0)
        WHERE id = OLD.parent_comment_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for comment reply counts
DROP TRIGGER IF EXISTS trigger_update_comment_reply_count ON comments;
CREATE TRIGGER trigger_update_comment_reply_count
    AFTER INSERT OR DELETE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_comment_reply_count();

-- Function to track issue activities
CREATE OR REPLACE FUNCTION track_issue_activity()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO issue_activities (issue_id, user_id, activity_type, description, metadata)
        VALUES (
            NEW.id, 
            NEW.user_id, 
            'created', 
            'Issue created',
            jsonb_build_object(
                'issue_type', NEW.issue_type,
                'status', NEW.status,
                'location', jsonb_build_object(
                    'latitude', ST_Y(NEW.location),
                    'longitude', ST_X(NEW.location)
                )
            )
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Track status changes
        IF OLD.status != NEW.status THEN
            INSERT INTO issue_activities (issue_id, user_id, activity_type, description, metadata)
            VALUES (
                NEW.id, 
                NULL, -- System update
                'status_changed', 
                format('Status changed from %s to %s', OLD.status, NEW.status),
                jsonb_build_object(
                    'old_status', OLD.status,
                    'new_status', NEW.status,
                    'resolved_at', NEW.resolved_at,
                    'resolved_by', NEW.resolved_by_user_id
                )
            );
        END IF;
        
        -- Track representative assignment
        IF OLD.assigned_representative_id != NEW.assigned_representative_id THEN
            INSERT INTO issue_activities (issue_id, user_id, activity_type, description, metadata)
            VALUES (
                NEW.id, 
                NULL,
                'assigned', 
                'Representative assigned',
                jsonb_build_object(
                    'old_representative_id', OLD.assigned_representative_id,
                    'new_representative_id', NEW.assigned_representative_id
                )
            );
        END IF;
        
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for issue activity tracking
DROP TRIGGER IF EXISTS trigger_track_issue_activity ON issues;
CREATE TRIGGER trigger_track_issue_activity
    AFTER INSERT OR UPDATE ON issues
    FOR EACH ROW
    EXECUTE FUNCTION track_issue_activity();

-- Function to track comment activities
CREATE OR REPLACE FUNCTION track_comment_activity()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO issue_activities (issue_id, user_id, activity_type, description, metadata)
        VALUES (
            NEW.issue_id, 
            NEW.user_id, 
            'commented', 
            'Comment added',
            jsonb_build_object(
                'comment_id', NEW.id,
                'parent_comment_id', NEW.parent_comment_id,
                'thread_level', NEW.thread_level
            )
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for comment activity tracking
DROP TRIGGER IF EXISTS trigger_track_comment_activity ON comments;
CREATE TRIGGER trigger_track_comment_activity
    AFTER INSERT ON comments
    FOR EACH ROW
    EXECUTE FUNCTION track_comment_activity();

-- Function to track vote activities
CREATE OR REPLACE FUNCTION track_vote_activity()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.issue_id IS NOT NULL THEN
        INSERT INTO issue_activities (issue_id, user_id, activity_type, description, metadata)
        VALUES (
            NEW.issue_id, 
            NEW.user_id, 
            'voted', 
            format('Vote cast: %s', NEW.vote_type),
            jsonb_build_object(
                'vote_type', NEW.vote_type,
                'vote_id', NEW.id
            )
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for vote activity tracking (only for issues, not comments to avoid spam)
DROP TRIGGER IF EXISTS trigger_track_vote_activity ON votes;
CREATE TRIGGER trigger_track_vote_activity
    AFTER INSERT ON votes
    FOR EACH ROW
    WHEN (NEW.issue_id IS NOT NULL)
    EXECUTE FUNCTION track_vote_activity();

-- Function to update user timestamps
CREATE OR REPLACE FUNCTION update_user_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for user timestamp updates
DROP TRIGGER IF EXISTS trigger_update_user_timestamp ON users;
CREATE TRIGGER trigger_update_user_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_timestamp();

-- Function to update issue timestamps
CREATE OR REPLACE FUNCTION update_issue_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for issue timestamp updates
DROP TRIGGER IF EXISTS trigger_update_issue_timestamp ON issues;
CREATE TRIGGER trigger_update_issue_timestamp
    BEFORE UPDATE ON issues
    FOR EACH ROW
    EXECUTE FUNCTION update_issue_timestamp();

-- Function to automatically assign representatives to new issues
CREATE OR REPLACE FUNCTION auto_assign_representative()
RETURNS TRIGGER AS $$
DECLARE
    rep_id UUID;
BEGIN
    -- Find the most appropriate representative for this location
    SELECT r.id INTO rep_id
    FROM representatives r
    WHERE ST_Contains(r.jurisdiction_boundary, NEW.location)
      AND r.active = TRUE
    ORDER BY r.priority_order ASC, r.jurisdiction_level ASC
    LIMIT 1;
    
    -- Assign the representative if found
    IF rep_id IS NOT NULL THEN
        NEW.assigned_representative_id = rep_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic representative assignment
DROP TRIGGER IF EXISTS trigger_auto_assign_representative ON issues;
CREATE TRIGGER trigger_auto_assign_representative
    BEFORE INSERT ON issues
    FOR EACH ROW
    EXECUTE FUNCTION auto_assign_representative();

-- Function to clean up old data periodically (called by scheduled job)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Delete old notifications (older than 90 days)
    DELETE FROM notifications 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Delete expired sessions
    DELETE FROM user_sessions 
    WHERE expires_at < NOW() OR revoked = TRUE;
    
    -- Delete old issue activities (older than 1 year, keep only important ones)
    DELETE FROM issue_activities 
    WHERE created_at < NOW() - INTERVAL '1 year'
      AND activity_type NOT IN ('created', 'status_changed', 'assigned');
    
    -- Update analytics table if needed
    INSERT INTO daily_analytics (date) 
    VALUES (CURRENT_DATE) 
    ON CONFLICT (date) DO NOTHING;
    
END;
$$ LANGUAGE plpgsql;

-- Function to calculate thread path for comments
CREATE OR REPLACE FUNCTION calculate_comment_thread_path()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_comment_id IS NULL THEN
        -- Root comment
        NEW.thread_level = 0;
        NEW.thread_path = NEW.id::text;
    ELSE
        -- Reply comment
        SELECT 
            thread_level + 1,
            thread_path || '.' || NEW.id::text
        INTO NEW.thread_level, NEW.thread_path
        FROM comments 
        WHERE id = NEW.parent_comment_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for comment thread path calculation
DROP TRIGGER IF EXISTS trigger_calculate_comment_thread_path ON comments;
CREATE TRIGGER trigger_calculate_comment_thread_path
    BEFORE INSERT ON comments
    FOR EACH ROW
    EXECUTE FUNCTION calculate_comment_thread_path();
