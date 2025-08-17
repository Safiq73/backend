"""
Raw SQL queries for CivicPulse application
All queries use parameterized statements to prevent SQL injection
"""

class UserQueries:
    """SQL queries for user management"""
    
    CREATE_USER = """
        INSERT INTO users (email, password_hash, name, role, address, bio)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, email, name, role, created_at;
    """
    
    GET_USER_BY_EMAIL = """
        SELECT id, email, password_hash, name, role, avatar_url, cover_photo_url,
               phone, address, bio, verified, email_verified, active, created_at, updated_at
        FROM users 
        WHERE email = $1 AND active = TRUE;
    """
    
    GET_USER_BY_ID = """
        SELECT id, email, name, role, avatar_url, cover_photo_url,
               phone, address, bio, verified, email_verified, active, created_at, updated_at
        FROM users 
        WHERE id = $1 AND active = TRUE;
    """
    
    UPDATE_USER_PROFILE = """
        UPDATE users 
        SET name = COALESCE($2, name),
            avatar_url = COALESCE($3, avatar_url),
            cover_photo_url = COALESCE($4, cover_photo_url),
            phone = COALESCE($5, phone),
            address = COALESCE($6, address),
            bio = COALESCE($7, bio),
            updated_at = NOW()
        WHERE id = $1
        RETURNING id, name, avatar_url, cover_photo_url, phone, address, bio, updated_at;
    """
    
    UPDATE_LAST_LOGIN = """
        UPDATE users 
        SET last_login = NOW(), login_count = login_count + 1
        WHERE id = $1;
    """
    
    SEARCH_USERS = """
        SELECT id, name, email, role, avatar_url, verified
        FROM users
        WHERE search_vector @@ plainto_tsquery('english', $1)
           AND active = TRUE
        ORDER BY ts_rank(search_vector, plainto_tsquery('english', $1)) DESC
        LIMIT $2 OFFSET $3;
    """


class IssueQueries:
    """SQL queries for issue management with spatial operations"""
    
    CREATE_ISSUE = """
        INSERT INTO issues (
            user_id, title, description, issue_type, location, address, 
            landmark_description, urgency_level
        ) 
        VALUES ($1, $2, $3, $4, ST_SetSRID(ST_MakePoint($5, $6), 4326), $7, $8, $9)
        RETURNING id, created_at;
    """
    
    FIND_REPRESENTATIVE_FOR_LOCATION = """
        SELECT r.id, r.user_id, r.title, r.office_name, r.jurisdiction_name,
               r.jurisdiction_level, r.contact_email, r.contact_phone,
               u.name as representative_name, u.email, u.avatar_url
        FROM representatives r
        JOIN users u ON r.user_id = u.id
        WHERE ST_Contains(r.jurisdiction_boundary, ST_SetSRID(ST_MakePoint($1, $2), 4326))
          AND r.active = TRUE
        ORDER BY r.priority_order ASC, r.jurisdiction_level ASC;
    """
    
    ASSIGN_REPRESENTATIVE_TO_ISSUE = """
        UPDATE issues 
        SET assigned_representative_id = $2, updated_at = NOW()
        WHERE id = $1
        RETURNING id, assigned_representative_id;
    """
    
    GET_ISSUES_PAGINATED = """
        SELECT i.id, i.title, i.description, i.issue_type, i.status, i.priority_score,
               i.urgency_level, i.upvotes, i.downvotes, i.comment_count, i.view_count,
               ST_X(i.location) as longitude, ST_Y(i.location) as latitude,
               i.address, i.landmark_description, i.created_at, i.updated_at,
               u.name as author_name, u.avatar_url as author_avatar,
               r.title as representative_title, r.office_name,
               ru.name as representative_name
        FROM issues i
        JOIN users u ON i.user_id = u.id
        LEFT JOIN representatives r ON i.assigned_representative_id = r.id
        LEFT JOIN users ru ON r.user_id = ru.id
        WHERE ($1::issue_status IS NULL OR i.status = $1)
          AND ($2::issue_type IS NULL OR i.issue_type = $2)
          AND ($3::uuid IS NULL OR i.assigned_representative_id = $3)
        ORDER BY 
            CASE WHEN $4 = 'recent' THEN i.created_at END DESC,
            CASE WHEN $4 = 'popular' THEN (i.upvotes - i.downvotes) END DESC,
            CASE WHEN $4 = 'urgent' THEN i.urgency_level END DESC,
            i.created_at DESC
        LIMIT $5 OFFSET $6;
    """
    
    GET_ISSUES_NEAR_LOCATION = """
        SELECT i.id, i.title, i.description, i.issue_type, i.status,
               i.upvotes, i.downvotes, i.comment_count,
               ST_X(i.location) as longitude, ST_Y(i.location) as latitude,
               i.address, i.created_at,
               u.name as author_name, u.avatar_url as author_avatar,
               ST_Distance(
                   ST_Transform(i.location, 3857),
                   ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3857)
               ) as distance_meters
        FROM issues i
        JOIN users u ON i.user_id = u.id
        WHERE ST_DWithin(
            ST_Transform(i.location, 3857),
            ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3857),
            $3  -- radius in meters
        )
        ORDER BY distance_meters ASC
        LIMIT $4 OFFSET $5;
    """
    
    UPDATE_ISSUE_STATUS = """
        UPDATE issues 
        SET status = $2, 
            resolution_notes = COALESCE($3, resolution_notes),
            resolution_cost = COALESCE($4, resolution_cost),
            resolved_by_user_id = CASE WHEN $2 = 'resolved' THEN $5 ELSE NULL END,
            resolved_at = CASE WHEN $2 = 'resolved' THEN NOW() ELSE NULL END,
            updated_at = NOW(),
            last_activity_at = NOW()
        WHERE id = $1
        RETURNING id, status, resolution_notes, resolved_at;
    """
    
    SEARCH_ISSUES = """
        SELECT i.id, i.title, i.description, i.issue_type, i.status,
               i.upvotes, i.downvotes, i.comment_count,
               ST_X(i.location) as longitude, ST_Y(i.location) as latitude,
               i.address, i.created_at,
               u.name as author_name,
               ts_rank(i.search_vector, plainto_tsquery('english', $1)) as rank
        FROM issues i
        JOIN users u ON i.user_id = u.id
        WHERE i.search_vector @@ plainto_tsquery('english', $1)
        ORDER BY rank DESC, i.created_at DESC
        LIMIT $2 OFFSET $3;
    """
    
    INCREMENT_VIEW_COUNT = """
        UPDATE issues 
        SET view_count = view_count + 1
        WHERE id = $1;
    """


class CommentQueries:
    """SQL queries for comment management"""
    
    CREATE_COMMENT = """
        INSERT INTO comments (issue_id, user_id, parent_comment_id, content, thread_level, thread_path)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at;
    """
    
    GET_COMMENTS_FOR_ISSUE = """
        SELECT c.id, c.content, c.parent_comment_id, c.thread_level, c.thread_path,
               c.upvotes, c.downvotes, c.reply_count, c.edited, c.edited_at,
               c.created_at, c.updated_at,
               u.id as author_id, u.name as author_name, u.avatar_url as author_avatar,
               u.role as author_role
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.issue_id = $1
        ORDER BY c.thread_path ASC, c.created_at ASC
        LIMIT $2 OFFSET $3;
    """
    
    UPDATE_COMMENT = """
        UPDATE comments 
        SET content = $2, edited = TRUE, edited_at = NOW(), updated_at = NOW()
        WHERE id = $1 AND user_id = $3
        RETURNING id, content, edited, edited_at;
    """
    
    DELETE_COMMENT = """
        DELETE FROM comments 
        WHERE id = $1 AND user_id = $2
        RETURNING id;
    """
    
    GET_COMMENT_THREAD_PATH = """
        SELECT COALESCE(parent.thread_path || '.' || parent.id::text, '1') as new_path,
               COALESCE(parent.thread_level + 1, 0) as new_level
        FROM comments parent 
        WHERE parent.id = $1;
    """


class VoteQueries:
    """SQL queries for voting system"""
    
    CAST_VOTE_ISSUE = """
        INSERT INTO votes (user_id, issue_id, vote_type)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, issue_id) 
        DO UPDATE SET vote_type = $3, updated_at = NOW()
        RETURNING id, vote_type;
    """
    
    CAST_VOTE_COMMENT = """
        INSERT INTO votes (user_id, comment_id, vote_type)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, comment_id) 
        DO UPDATE SET vote_type = $3, updated_at = NOW()
        RETURNING id, vote_type;
    """
    
    REMOVE_VOTE_ISSUE = """
        DELETE FROM votes 
        WHERE user_id = $1 AND issue_id = $2
        RETURNING id;
    """
    
    REMOVE_VOTE_COMMENT = """
        DELETE FROM votes 
        WHERE user_id = $1 AND comment_id = $2
        RETURNING id;
    """
    
    GET_USER_VOTE_FOR_ISSUE = """
        SELECT vote_type 
        FROM votes 
        WHERE user_id = $1 AND issue_id = $2;
    """
    
    GET_VOTE_COUNTS_FOR_ISSUE = """
        SELECT 
            COUNT(CASE WHEN vote_type = 'upvote' THEN 1 END) as upvotes,
            COUNT(CASE WHEN vote_type = 'downvote' THEN 1 END) as downvotes
        FROM votes 
        WHERE issue_id = $1;
    """
    
    GET_VOTE_COUNTS_FOR_COMMENT = """
        SELECT 
            COUNT(CASE WHEN vote_type = 'upvote' THEN 1 END) as upvotes,
            COUNT(CASE WHEN vote_type = 'downvote' THEN 1 END) as downvotes
        FROM votes 
        WHERE comment_id = $1;
    """


class NotificationQueries:
    """SQL queries for notification management"""
    
    CREATE_NOTIFICATION = """
        INSERT INTO notifications (
            user_id, issue_id, comment_id, triggered_by_user_id, 
            notification_type, title, message, action_url
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, created_at;
    """
    
    GET_USER_NOTIFICATIONS = """
        SELECT n.id, n.notification_type, n.title, n.message, n.action_url,
               n.read, n.read_at, n.created_at,
               u.name as triggered_by_name, u.avatar_url as triggered_by_avatar,
               i.title as issue_title
        FROM notifications n
        LEFT JOIN users u ON n.triggered_by_user_id = u.id
        LEFT JOIN issues i ON n.issue_id = i.id
        WHERE n.user_id = $1
        ORDER BY n.created_at DESC
        LIMIT $2 OFFSET $3;
    """
    
    MARK_NOTIFICATION_READ = """
        UPDATE notifications 
        SET read = TRUE, read_at = NOW()
        WHERE id = $1 AND user_id = $2
        RETURNING id;
    """
    
    MARK_ALL_NOTIFICATIONS_READ = """
        UPDATE notifications 
        SET read = TRUE, read_at = NOW()
        WHERE user_id = $1 AND read = FALSE
        RETURNING COUNT(*);
    """
    
    GET_UNREAD_COUNT = """
        SELECT COUNT(*) 
        FROM notifications 
        WHERE user_id = $1 AND read = FALSE;
    """
    
    DELETE_OLD_NOTIFICATIONS = """
        DELETE FROM notifications 
        WHERE created_at < NOW() - INTERVAL '90 days'
        RETURNING COUNT(*);
    """


class RepresentativeQueries:
    """SQL queries for representative management"""
    
    CREATE_REPRESENTATIVE = """
        INSERT INTO representatives (
            user_id, title, office_name, jurisdiction_name, jurisdiction_level,
            jurisdiction_boundary, office_address, term_start, term_end,
            contact_email, contact_phone, website_url, party_affiliation, bio
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        RETURNING id, created_at;
    """
    
    GET_REPRESENTATIVES_FOR_LOCATION = """
        SELECT r.id, r.title, r.office_name, r.jurisdiction_name, r.jurisdiction_level,
               r.contact_email, r.contact_phone, r.website_url, r.party_affiliation,
               u.name, u.email, u.avatar_url, u.bio
        FROM representatives r
        JOIN users u ON r.user_id = u.id
        WHERE ST_Contains(r.jurisdiction_boundary, ST_SetSRID(ST_MakePoint($1, $2), 4326))
          AND r.active = TRUE
        ORDER BY r.priority_order ASC;
    """
    
    GET_REPRESENTATIVE_BY_ID = """
        SELECT r.id, r.title, r.office_name, r.jurisdiction_name, r.jurisdiction_level,
               r.office_address, r.term_start, r.term_end, r.contact_email, r.contact_phone,
               r.website_url, r.party_affiliation, r.bio, r.created_at,
               u.name, u.email, u.avatar_url, u.cover_photo_url
        FROM representatives r
        JOIN users u ON r.user_id = u.id
        WHERE r.id = $1 AND r.active = TRUE;
    """
    
    GET_ISSUES_FOR_REPRESENTATIVE = """
        SELECT i.id, i.title, i.description, i.issue_type, i.status, i.priority_score,
               i.upvotes, i.downvotes, i.comment_count,
               ST_X(i.location) as longitude, ST_Y(i.location) as latitude,
               i.address, i.created_at, i.updated_at,
               u.name as author_name, u.avatar_url as author_avatar
        FROM issues i
        JOIN users u ON i.user_id = u.id
        WHERE i.assigned_representative_id = $1
          AND ($2::issue_status IS NULL OR i.status = $2)
        ORDER BY 
            CASE WHEN i.status = 'open' THEN 1
                 WHEN i.status = 'in_progress' THEN 2
                 ELSE 3 END,
            i.urgency_level DESC,
            i.created_at DESC
        LIMIT $3 OFFSET $4;
    """


class AnalyticsQueries:
    """SQL queries for analytics and performance tracking"""
    
    GET_DASHBOARD_STATS = """
        SELECT 
            (SELECT COUNT(*) FROM users WHERE active = TRUE) as total_users,
            (SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as new_users_month,
            (SELECT COUNT(*) FROM issues) as total_issues,
            (SELECT COUNT(*) FROM issues WHERE status = 'open') as open_issues,
            (SELECT COUNT(*) FROM issues WHERE status = 'resolved') as resolved_issues,
            (SELECT COUNT(*) FROM issues WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as new_issues_month,
            (SELECT COUNT(*) FROM comments WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as new_comments_month,
            (SELECT ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/3600), 2) 
             FROM issues WHERE status = 'resolved' AND resolved_at IS NOT NULL) as avg_resolution_time_hours;
    """
    
    GET_ISSUES_BY_TYPE = """
        SELECT issue_type, COUNT(*) as count
        FROM issues
        GROUP BY issue_type
        ORDER BY count DESC;
    """
    
    GET_ISSUES_BY_STATUS = """
        SELECT status, COUNT(*) as count
        FROM issues
        GROUP BY status
        ORDER BY count DESC;
    """
    
    GET_TOP_CONTRIBUTORS = """
        SELECT u.id, u.name, u.avatar_url,
               COUNT(i.id) as issues_created,
               COUNT(c.id) as comments_made,
               COUNT(v.id) as votes_cast
        FROM users u
        LEFT JOIN issues i ON u.id = i.user_id
        LEFT JOIN comments c ON u.id = c.user_id
        LEFT JOIN votes v ON u.id = v.user_id
        WHERE u.active = TRUE
        GROUP BY u.id, u.name, u.avatar_url
        HAVING COUNT(i.id) + COUNT(c.id) + COUNT(v.id) > 0
        ORDER BY (COUNT(i.id) * 3 + COUNT(c.id) * 2 + COUNT(v.id)) DESC
        LIMIT $1;
    """
    
    GET_ACTIVITY_HEATMAP = """
        SELECT 
            DATE_TRUNC('day', created_at) as date,
            COUNT(*) as activity_count
        FROM (
            SELECT created_at FROM issues WHERE created_at >= $1
            UNION ALL
            SELECT created_at FROM comments WHERE created_at >= $1
            UNION ALL
            SELECT created_at FROM votes WHERE created_at >= $1
        ) activities
        GROUP BY DATE_TRUNC('day', created_at)
        ORDER BY date;
    """


class MediaQueries:
    """SQL queries for media management"""
    
    CREATE_MEDIA = """
        INSERT INTO media (
            issue_id, comment_id, uploaded_by_user_id, media_type, url, 
            thumbnail_url, filename, file_size, mime_type, width, height, 
            duration, alt_text, caption, upload_order
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING id, created_at;
    """
    
    GET_MEDIA_FOR_ISSUE = """
        SELECT id, media_type, url, thumbnail_url, filename, file_size,
               mime_type, width, height, duration, alt_text, caption, upload_order
        FROM media
        WHERE issue_id = $1
        ORDER BY upload_order ASC, created_at ASC;
    """
    
    GET_MEDIA_FOR_COMMENT = """
        SELECT id, media_type, url, thumbnail_url, filename, file_size,
               mime_type, width, height, duration, alt_text, caption
        FROM media
        WHERE comment_id = $1
        ORDER BY upload_order ASC, created_at ASC;
    """
    
    DELETE_MEDIA = """
        DELETE FROM media 
        WHERE id = $1 AND uploaded_by_user_id = $2
        RETURNING url, thumbnail_url;
    """


class SavedIssueQueries:
    """SQL queries for saved/bookmarked issues"""
    
    SAVE_ISSUE = """
        INSERT INTO saved_issues (user_id, issue_id)
        VALUES ($1, $2)
        ON CONFLICT (user_id, issue_id) DO NOTHING
        RETURNING id;
    """
    
    UNSAVE_ISSUE = """
        DELETE FROM saved_issues 
        WHERE user_id = $1 AND issue_id = $2
        RETURNING id;
    """
    
    GET_SAVED_ISSUES = """
        SELECT i.id, i.title, i.description, i.issue_type, i.status,
               i.upvotes, i.downvotes, i.comment_count,
               ST_X(i.location) as longitude, ST_Y(i.location) as latitude,
               i.address, i.created_at,
               u.name as author_name, u.avatar_url as author_avatar,
               si.created_at as saved_at
        FROM saved_issues si
        JOIN issues i ON si.issue_id = i.id
        JOIN users u ON i.user_id = u.id
        WHERE si.user_id = $1
        ORDER BY si.created_at DESC
        LIMIT $2 OFFSET $3;
    """
    
    CHECK_IF_SAVED = """
        SELECT EXISTS(
            SELECT 1 FROM saved_issues 
            WHERE user_id = $1 AND issue_id = $2
        );
    """


class SessionQueries:
    """SQL queries for session management"""
    
    CREATE_SESSION = """
        INSERT INTO user_sessions (
            user_id, refresh_token_hash, expires_at, user_agent, ip_address, is_mobile
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id;
    """
    
    GET_VALID_SESSION = """
        SELECT id, user_id, expires_at
        FROM user_sessions
        WHERE refresh_token_hash = $1 
          AND expires_at > NOW() 
          AND revoked = FALSE;
    """
    
    REVOKE_SESSION = """
        UPDATE user_sessions 
        SET revoked = TRUE
        WHERE refresh_token_hash = $1
        RETURNING id;
    """
    
    REVOKE_ALL_USER_SESSIONS = """
        UPDATE user_sessions 
        SET revoked = TRUE
        WHERE user_id = $1 AND revoked = FALSE
        RETURNING COUNT(*);
    """
    
    CLEANUP_EXPIRED_SESSIONS = """
        DELETE FROM user_sessions 
        WHERE expires_at < NOW() OR revoked = TRUE
        RETURNING COUNT(*);
    """
