"""
Database service layer using raw SQL with asyncpg for production-ready operations
"""
import logging
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import asyncpg
from app.db.database import db_manager
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations using raw SQL with asyncpg"""
    
    def __init__(self):
        self.retry_attempts = 3
        self.retry_delay = 1.0
    
    @asynccontextmanager
    async def get_connection_with_retry(self):
        """Get database connection with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                async with db_manager.get_connection() as conn:
                    yield conn
                    return
            except asyncpg.ConnectionDoesNotExistError:
                if attempt == self.retry_attempts - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                logger.warning(f"Database connection retry {attempt + 1}/{self.retry_attempts}")
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with transaction support"""
        async with self.get_connection_with_retry() as conn:
            async with conn.transaction():
                user_id = uuid4()
                
                # Check if username or email already exists
                check_query = """
                    SELECT username, email FROM users 
                    WHERE username = $1 OR email = $2
                """
                existing = await conn.fetchrow(
                    check_query,
                    user_data.get('username'),
                    user_data.get('email')
                )
                
                if existing:
                    if existing['username'] == user_data.get('username'):
                        raise ValueError("Username already exists")
                    if existing['email'] == user_data.get('email'):
                        raise ValueError("Email already exists")
                
                # Create user
                query = """
                    INSERT INTO users (id, username, email, password_hash, display_name, bio, avatar_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, username, email, display_name, bio, avatar_url, is_active, is_verified, created_at, updated_at
                """
                row = await conn.fetchrow(
                    query,
                    user_id,
                    user_data.get('username'),
                    user_data.get('email'),
                    user_data.get('password_hash'),
                    user_data.get('display_name'),
                    user_data.get('bio'),
                    user_data.get('avatar_url')
                )
                
                logger.info(f"User created successfully | ID: {user_id} | Username: {user_data.get('username')}")
                return dict(row)
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT id, username, email, password_hash, display_name, role, bio, avatar_url,
                       is_active, is_verified, created_at, updated_at
                FROM users WHERE id = $1
            """
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else None
        
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT id, username, email, password_hash, display_name, bio, avatar_url,
                       is_active, is_verified, created_at, updated_at
                FROM users WHERE email = $1
            """
            row = await conn.fetchrow(query, email)
            return dict(row) if row else None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT id, username, email, password_hash, display_name, bio, avatar_url,
                       is_active, is_verified, created_at, updated_at
                FROM users WHERE username = $1
            """
            row = await conn.fetchrow(query, username)
            return dict(row) if row else None
    
    async def update_user(self, user_id: UUID, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user information"""
        async with db_manager.get_connection() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in user_data.items():
                if value is not None and field not in ['id', 'created_at']:
                    set_clauses.append(f"{field} = ${param_num}")
                    values.append(value)
                    param_num += 1
            
            if not set_clauses:
                return await self.get_user_by_id(user_id)
            
            set_clauses.append(f"updated_at = NOW()")
            values.append(user_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_num}
                RETURNING id, username, email, display_name, bio, avatar_url,
                         is_active, is_verified, created_at, updated_at
            """
            
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user by ID"""
        async with db_manager.get_connection() as conn:
            query = "DELETE FROM users WHERE id = $1"
            result = await conn.execute(query, user_id)
            return result == "DELETE 1"
    
    # Post operations
    async def create_post(self, post_data: Dict[str, Any], user_id: UUID) -> Dict[str, Any]:
        """Create a new post"""
        async with db_manager.get_connection() as conn:
            post_id = uuid4()
            query = """
                INSERT INTO posts (id, user_id, title, content, post_type, area, category, location, tags, media_urls)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id, user_id, title, content, post_type, area, category, location, tags, media_urls, created_at, updated_at
            """
            row = await conn.fetchrow(
                query,
                post_id,
                user_id,
                post_data.get('title'),
                post_data.get('content'),
                post_data.get('post_type', 'discussion'),
                post_data.get('area'),
                post_data.get('category'),
                post_data.get('location'),
                post_data.get('tags', []),
                post_data.get('media_urls', [])
            )
            return dict(row)
    
    async def get_post_by_id(self, post_id: UUID) -> Optional[Dict[str, Any]]:
        """Get post by ID with author information"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT p.id, p.title, p.content, p.post_type, p.images, p.location, p.tags,
                       p.created_at, p.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = $1
            """
            row = await conn.fetchrow(query, post_id)
            if not row:
                return None
            
            # Format the response
            post = dict(row)
            post['author'] = {
                'id': post.pop('user_id'),
                'username': post.pop('author_username'),
                'display_name': post.pop('author_display_name'),
                'avatar_url': post.pop('author_avatar_url')
            }
            return post
    
    async def get_posts(
        self,
        skip: int = 0,
        limit: int = 20,
        post_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
        location: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get posts with filters and pagination"""
        async with db_manager.get_connection() as conn:
            # Build the base query
            query = """
                SELECT p.id, p.title, p.content, p.post_type, p.area, p.category, p.status,
                       p.media_urls, p.location, p.upvotes, p.downvotes, p.comment_count,
                       p.created_at, p.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url
                FROM posts p
                JOIN users u ON p.user_id = u.id
            """
            
            conditions = []
            values = []
            param_num = 1
            
            # Apply filters
            if post_type:
                conditions.append(f"p.post_type = ${param_num}")
                values.append(post_type)
                param_num += 1
            
            if user_id:
                conditions.append(f"p.user_id = ${param_num}")
                values.append(user_id)
                param_num += 1
            
            if location:
                conditions.append(f"p.area ILIKE ${param_num}")
                values.append(f"%{location}%")
                param_num += 1
            
            if tags:
                conditions.append(f"p.tags && ${param_num}")
                values.append(tags)
                param_num += 1
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Order and pagination
            query += f" ORDER BY p.created_at DESC OFFSET ${param_num} LIMIT ${param_num + 1}"
            values.extend([skip, limit])
            
            rows = await conn.fetch(query, *values)
            
            # Format the response
            posts = []
            for row in rows:
                post = dict(row)
                post['author'] = {
                    'id': post.pop('user_id'),
                    'username': post.pop('author_username'),
                    'display_name': post.pop('author_display_name'),
                    'avatar_url': post.pop('author_avatar_url')
                }
                posts.append(post)
            
            return posts
    
    async def update_post(self, post_id: UUID, post_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update post information"""
        async with db_manager.get_connection() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in post_data.items():
                if value is not None and field not in ['id', 'user_id', 'created_at']:
                    set_clauses.append(f"{field} = ${param_num}")
                    values.append(value)
                    param_num += 1
            
            if not set_clauses:
                return await self.get_post_by_id(post_id)
            
            set_clauses.append(f"updated_at = NOW()")
            values.append(post_id)
            
            query = f"""
                UPDATE posts 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_num}
                RETURNING id, user_id, title, content, post_type, area, category, location, tags, media_urls, created_at, updated_at
            """
            
            row = await conn.fetchrow(query, *values)
            if not row:
                return None
            
            # Get the full post with author info
            return await self.get_post_by_id(post_id)
    
    async def delete_post(self, post_id: UUID) -> bool:
        """Delete post by ID"""
        async with db_manager.get_connection() as conn:
            query = "DELETE FROM posts WHERE id = $1"
            result = await conn.execute(query, post_id)
            return result == "DELETE 1"
    
    # Vote operations
    async def create_or_update_vote(self, post_id: UUID, user_id: UUID, vote_type: str) -> Optional[Dict[str, Any]]:
        """Create or update a vote on a post"""
        async with db_manager.get_connection() as conn:
            # Check if vote already exists
            existing_query = "SELECT id, vote_type FROM votes WHERE post_id = $1 AND user_id = $2"
            existing_vote = await conn.fetchrow(existing_query, post_id, user_id)
            
            if existing_vote:
                if existing_vote['vote_type'] == vote_type:
                    # Same vote - remove it (toggle off)
                    delete_query = "DELETE FROM votes WHERE id = $1"
                    await conn.execute(delete_query, existing_vote['id'])
                    return None
                else:
                    # Different vote - update it
                    update_query = """
                        UPDATE votes SET vote_type = $1, updated_at = NOW()
                        WHERE id = $2
                        RETURNING id, post_id, user_id, vote_type, created_at, updated_at
                    """
                    row = await conn.fetchrow(update_query, vote_type, existing_vote['id'])
                    return dict(row)
            else:
                # New vote
                vote_id = uuid4()
                insert_query = """
                    INSERT INTO votes (id, post_id, user_id, vote_type)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, post_id, user_id, vote_type, created_at, updated_at
                """
                row = await conn.fetchrow(insert_query, vote_id, post_id, user_id, vote_type)
                return dict(row)
    
    async def get_post_vote_counts(self, post_id: UUID) -> Dict[str, int]:
        """Get vote counts for a post"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT vote_type, COUNT(*) as count
                FROM votes 
                WHERE post_id = $1 
                GROUP BY vote_type
            """
            rows = await conn.fetch(query, post_id)
            
            vote_counts = {"upvotes": 0, "downvotes": 0}
            for row in rows:
                if row['vote_type'] == 'upvote':
                    vote_counts["upvotes"] = row['count']
                elif row['vote_type'] == 'downvote':
                    vote_counts["downvotes"] = row['count']
            
            return vote_counts
    
    async def get_user_vote_on_post(self, post_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user's vote on a specific post"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT id, post_id, user_id, vote_type, created_at, updated_at
                FROM votes 
                WHERE post_id = $1 AND user_id = $2
            """
            row = await conn.fetchrow(query, post_id, user_id)
            return dict(row) if row else None
    
    # Comment operations
    async def create_comment(self, comment_data: Dict[str, Any], user_id: UUID) -> Dict[str, Any]:
        """Create a new comment"""
        async with db_manager.get_connection() as conn:
            comment_id = uuid4()
            query = """
                INSERT INTO comments (id, post_id, user_id, content, parent_id)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, post_id, user_id, content, parent_id, created_at, updated_at
            """
            row = await conn.fetchrow(
                query,
                comment_id,
                comment_data.get('post_id'),
                user_id,
                comment_data.get('content'),
                comment_data.get('parent_id')
            )
            return dict(row)
    
    async def get_comments_by_post(self, post_id: UUID) -> List[Dict[str, Any]]:
        """Get all comments for a post"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT c.id, c.post_id, c.content, c.parent_id, c.created_at, c.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = $1
                ORDER BY c.created_at ASC
            """
            rows = await conn.fetch(query, post_id)
            
            comments = []
            for row in rows:
                comment = dict(row)
                comment['author'] = {
                    'id': comment.pop('user_id'),
                    'username': comment.pop('author_username'),
                    'display_name': comment.pop('author_display_name'),
                    'avatar_url': comment.pop('author_avatar_url')
                }
                comments.append(comment)
            
            return comments
    
    # Saved posts operations
    async def save_post(self, post_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Save a post for a user"""
        async with db_manager.get_connection() as conn:
            # Check if already saved
            existing_query = "SELECT id FROM saved_posts WHERE post_id = $1 AND user_id = $2"
            existing = await conn.fetchrow(existing_query, post_id, user_id)
            
            if existing:
                return dict(existing)
            
            saved_id = uuid4()
            query = """
                INSERT INTO saved_posts (id, user_id, post_id)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, post_id, created_at
            """
            row = await conn.fetchrow(query, saved_id, user_id, post_id)
            return dict(row)
    
    async def unsave_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Remove a saved post for a user"""
        async with db_manager.get_connection() as conn:
            query = "DELETE FROM saved_posts WHERE post_id = $1 AND user_id = $2"
            result = await conn.execute(query, post_id, user_id)
            return result == "DELETE 1"
    
    async def is_post_saved(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if a post is saved by a user"""
        async with db_manager.get_connection() as conn:
            query = "SELECT 1 FROM saved_posts WHERE post_id = $1 AND user_id = $2"
            row = await conn.fetchrow(query, post_id, user_id)
            return row is not None
    
    # Analytics and aggregations
    async def get_user_stats(self, user_id: UUID) -> Dict[str, int]:
        """Get user statistics"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT 
                    (SELECT COUNT(*) FROM posts WHERE user_id = $1) as posts_count,
                    (SELECT COUNT(*) FROM comments WHERE user_id = $1) as comments_count,
                    (SELECT COUNT(*) FROM votes v 
                     JOIN posts p ON v.post_id = p.id 
                     WHERE p.user_id = $1 AND v.vote_type = 'upvote') as upvotes_received
            """
            row = await conn.fetchrow(query, user_id)
            return dict(row)
    
    async def get_trending_posts(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending posts based on engagement in the last N hours"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT p.id, p.title, p.content, p.post_type, p.images, p.location, p.tags,
                       p.created_at, p.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url,
                       (COALESCE(vote_count, 0) + COALESCE(comment_count, 0)) as engagement_score
                FROM posts p
                JOIN users u ON p.user_id = u.id
                LEFT JOIN (
                    SELECT post_id, COUNT(*) as vote_count
                    FROM votes 
                    WHERE created_at >= NOW() - INTERVAL '%s hours'
                    GROUP BY post_id
                ) v ON p.id = v.post_id
                LEFT JOIN (
                    SELECT post_id, COUNT(*) as comment_count
                    FROM comments 
                    WHERE created_at >= NOW() - INTERVAL '%s hours'
                    GROUP BY post_id
                ) c ON p.id = c.post_id
                WHERE p.created_at >= NOW() - INTERVAL '%s hours'
                ORDER BY engagement_score DESC, p.created_at DESC
                LIMIT $1
            """ % (hours, hours, hours)
            
            rows = await conn.fetch(query, limit)
            
            posts = []
            for row in rows:
                post = dict(row)
                post['author'] = {
                    'id': post.pop('user_id'),
                    'username': post.pop('author_username'),
                    'display_name': post.pop('author_display_name'),
                    'avatar_url': post.pop('author_avatar_url')
                }
                post.pop('engagement_score', None)  # Remove internal scoring field
                posts.append(post)
            
            return posts
