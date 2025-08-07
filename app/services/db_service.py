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
        """Get user by ID with detailed representative account information"""
        async with db_manager.get_connection() as conn:
            # Get basic user information including follow counts
            user_query = """
                SELECT u.id, u.username, u.email, u.password_hash, u.display_name, u.bio, u.avatar_url,
                       u.rep_accounts, u.is_active, u.is_verified, u.created_at, u.updated_at,
                       u.followers_count, u.following_count
                FROM users u
                WHERE u.id = $1
            """

            user_row = await conn.fetchrow(user_query, user_id)
            if not user_row:
                return None
            
            user_data = dict(user_row)

            # Get detailed representative account information if rep_accounts exist
            if user_data.get('rep_accounts'):
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.id = ANY($1) AND r.user_id = $2
                    ORDER BY t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, user_data['rep_accounts'], user_id)
                
                # Format representative accounts with nested structure
                rep_accounts = []
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    rep_accounts.append(formatted_rep)
                
                user_data['rep_accounts'] = rep_accounts
            else:
                user_data['rep_accounts'] = []

            return user_data
        
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email with detailed representative account information"""
        async with db_manager.get_connection() as conn:
            # Get basic user information
            user_query = """
                SELECT u.id, u.username, u.email, u.password_hash, u.display_name, u.bio, u.avatar_url,
                       u.rep_accounts, u.is_active, u.is_verified, u.created_at, u.updated_at
                FROM users u
                WHERE u.email = $1
            """
            user_row = await conn.fetchrow(user_query, email)
            if not user_row:
                return None
            
            user_data = dict(user_row)
            
            # Get detailed representative account information if rep_accounts exist
            if user_data.get('rep_accounts'):
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.id = ANY($1) AND r.user_id = $2
                    ORDER BY t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, user_data['rep_accounts'], user_data['id'])
                
                # Format representative accounts with nested structure
                rep_accounts = []
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    rep_accounts.append(formatted_rep)
                
                user_data['rep_accounts'] = rep_accounts
            else:
                user_data['rep_accounts'] = []
            
            return user_data
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username with detailed representative account information"""
        async with db_manager.get_connection() as conn:
            # Get basic user information
            user_query = """
                SELECT u.id, u.username, u.email, u.password_hash, u.display_name, u.bio, u.avatar_url,
                       u.rep_accounts, u.is_active, u.is_verified, u.created_at, u.updated_at
                FROM users u
                WHERE u.username = $1
            """
            user_row = await conn.fetchrow(user_query, username)
            if not user_row:
                return None
            
            user_data = dict(user_row)
            
            # Get detailed representative account information if rep_accounts exist
            if user_data.get('rep_accounts'):
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.id = ANY($1) AND r.user_id = $2
                    ORDER BY t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, user_data['rep_accounts'], user_data['id'])
                
                # Format representative accounts with nested structure
                rep_accounts = []
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    rep_accounts.append(formatted_rep)
                
                user_data['rep_accounts'] = rep_accounts
            else:
                user_data['rep_accounts'] = []
            
            return user_data
    
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
    
    # Title operations (previously role operations)
    async def create_title(self, title_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new title"""
        async with db_manager.get_connection() as conn:
            title_id = uuid4()
            query = """
                INSERT INTO titles (id, title_name, abbreviation, level_rank, title_type, description, 
                                level, is_elected, term_length, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id, title_name, abbreviation, level_rank, title_type, description, 
                         level, is_elected, term_length, status, created_at, updated_at
            """
            row = await conn.fetchrow(
                query,
                title_id,
                title_data.get('title_name'),
                title_data.get('abbreviation'),
                title_data.get('level_rank'),
                title_data.get('title_type'),
                title_data.get('description'),
                title_data.get('level'),
                title_data.get('is_elected', False),
                title_data.get('term_length'),
                title_data.get('status', 'active')
            )
            return dict(row)
    
    async def get_title_by_id(self, title_id: UUID) -> Optional[Dict[str, Any]]:
        """Get title by ID"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT id, title_name, abbreviation, level_rank, title_type, description, 
                       level, is_elected, term_length, status, created_at, updated_at
                FROM titles WHERE id = $1
            """
            row = await conn.fetchrow(query, title_id)
            return dict(row) if row else None
    
    async def get_all_titles(self) -> List[Dict[str, Any]]:
        """Get all titles"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT id, title_name, abbreviation, level_rank, title_type, description, 
                       level, is_elected, term_length, status, created_at, updated_at
                FROM titles WHERE status = 'active' ORDER BY level_rank ASC, title_name ASC
            """
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def update_title(self, title_id: UUID, title_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update title information"""
        async with db_manager.get_connection() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in title_data.items():
                if value is not None and field not in ['id', 'created_at']:
                    set_clauses.append(f"{field} = ${param_num}")
                    values.append(value)
                    param_num += 1
            
            if not set_clauses:
                return await self.get_title_by_id(title_id)
            
            set_clauses.append(f"updated_at = NOW()")
            values.append(title_id)
            
            query = f"""
                UPDATE titles 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_num}
                RETURNING id, title_name, abbreviation, level_rank, title_type, description, 
                         level, is_elected, term_length, status, created_at, updated_at
            """
            
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
    
    async def delete_title(self, title_id: UUID) -> bool:
        """Delete title by ID"""
        async with db_manager.get_connection() as conn:
            query = "DELETE FROM titles WHERE id = $1"
            result = await conn.execute(query, title_id)
            return result == "DELETE 1"
    
    # Post operations
    async def create_post(self, post_data: Dict[str, Any], user_id: UUID) -> Dict[str, Any]:
        """Create a new post"""
        async with db_manager.get_connection() as conn:
            post_id = uuid4()
            query = """
                INSERT INTO posts (id, user_id, assignee, title, content, post_type, location, latitude, longitude, tags, media_urls)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id, user_id, assignee, title, content, post_type, location, latitude, longitude, tags, media_urls, created_at, updated_at
            """
            row = await conn.fetchrow(
                query,
                post_id,
                user_id,
                post_data.get('assignee'),
                post_data.get('title'),
                post_data.get('content'),
                post_data.get('post_type', 'discussion'),
                post_data.get('location'),
                post_data.get('latitude'),
                post_data.get('longitude'),
                post_data.get('tags', []),
                post_data.get('media_urls', [])
            )
            return dict(row)
    
    async def get_post_by_id(self, post_id: UUID) -> Optional[Dict[str, Any]]:
        """Get post by ID with author information including rep_accounts"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT p.id, p.title, p.content, p.post_type, p.status, p.assignee, p.media_urls, p.location, p.latitude, p.longitude, p.tags,
                       p.upvotes, p.downvotes, p.comment_count, p.view_count, p.share_count, p.priority_score,
                       p.created_at, p.updated_at, p.last_activity_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url,
                       u.rep_accounts
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = $1
            """
            row = await conn.fetchrow(query, post_id)
            if not row:
                return None
            
            # Format the response
            post = dict(row)
            user_id = post.pop('user_id')
            rep_accounts_ids = post.pop('rep_accounts')
            
            # Get detailed representative account information if rep_accounts exist
            rep_accounts = []
            if rep_accounts_ids:
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.id = ANY($1) AND r.user_id = $2
                    ORDER BY t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, rep_accounts_ids, user_id)
                
                # Format representative accounts with nested structure
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    rep_accounts.append(formatted_rep)
            
            post['author'] = {
                'id': user_id,
                'username': post.pop('author_username'),
                'display_name': post.pop('author_display_name'),
                'avatar_url': post.pop('author_avatar_url'),
                'rep_accounts': rep_accounts
            }
            
            return post
    
    async def get_posts(
        self,
        skip: int = 0,
        limit: int = 20,
        post_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
        location: Optional[str] = None,
        assignee: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get posts with filters and pagination including author rep_accounts"""
        async with db_manager.get_connection() as conn:
            # Build the base query
            query = """
                SELECT p.id, p.title, p.content, p.post_type, p.status, p.assignee,
                       p.media_urls, p.location, p.latitude, p.longitude, p.tags, p.upvotes, p.downvotes, p.comment_count,
                       p.created_at, p.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url,
                       u.rep_accounts
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
                conditions.append(f"p.location ILIKE ${param_num}")
                values.append(f"%{location}%")
                param_num += 1
            
            if assignee and len(assignee) > 0:
                # Convert list of strings to list of UUIDs if needed
                assignee_uuids = []
                for a in assignee:
                    if isinstance(a, str):
                        assignee_uuids.append(UUID(a))
                    else:
                        assignee_uuids.append(a)
                
                # Use IN clause for multiple assignees
                placeholders = [f"${param_num + i}" for i in range(len(assignee_uuids))]
                conditions.append(f"p.assignee IN ({', '.join(placeholders)})")
                values.extend(assignee_uuids)
                param_num += len(assignee_uuids)
            
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
            
            # Get unique user IDs to fetch rep_accounts for all authors
            user_ids = list(set([row['user_id'] for row in rows]))
            
            # Fetch all rep_accounts data for these users
            user_rep_accounts = {}
            if user_ids:
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.user_id = ANY($1)
                    ORDER BY r.user_id, t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, user_ids)
                
                # Group rep accounts by user_id
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    user_id_key = rep_data['user_id']
                    
                    if user_id_key not in user_rep_accounts:
                        user_rep_accounts[user_id_key] = []
                    
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    user_rep_accounts[user_id_key].append(formatted_rep)
                
                # Ensure each user's rep_accounts are sorted by level_rank ASC (lowest rank number = highest position first)
                for user_id_key in user_rep_accounts:
                    user_rep_accounts[user_id_key].sort(key=lambda x: x['title']['level_rank'], reverse=False)
            
            # Format the response
            posts = []
            for row in rows:
                post = dict(row)
                author_user_id = post.pop('user_id')
                post['author'] = {
                    'id': author_user_id,
                    'username': post.pop('author_username'),
                    'display_name': post.pop('author_display_name'),
                    'avatar_url': post.pop('author_avatar_url'),
                    'rep_accounts': user_rep_accounts.get(author_user_id, [])
                }
                # Remove the rep_accounts field from the post level since we don't need it
                post.pop('rep_accounts', None)
                
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
                RETURNING id, user_id, title, content, post_type, location, tags, media_urls, created_at, updated_at
            """
            
            row = await conn.fetchrow(query, *values)
            if not row:
                return None
            
            # Get the full post with author info
            return await self.get_post_by_id(post_id)

    async def update_post_status(self, post_id: UUID, status: str) -> Optional[Dict[str, Any]]:
        """Update post status specifically"""
        async with db_manager.get_connection() as conn:
            query = """
                UPDATE posts 
                SET status = $1, updated_at = NOW(), last_activity_at = NOW()
                WHERE id = $2
                RETURNING id, user_id, assignee
            """
            
            row = await conn.fetchrow(query, status, post_id)
            if not row:
                return None
            
            # Get the full post with author info
            return await self.get_post_by_id(post_id)

    async def update_post_assignee(self, post_id: UUID, assignee_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Update post assignee specifically"""
        async with db_manager.get_connection() as conn:
            query = """
                UPDATE posts 
                SET assignee = $1, updated_at = NOW(), last_activity_at = NOW()
                WHERE id = $2
                RETURNING id, user_id, assignee
            """
            
            # Convert assignee_id to UUID if provided, otherwise set to None
            assignee_uuid = UUID(assignee_id) if assignee_id else None
            
            row = await conn.fetchrow(query, assignee_uuid, post_id)
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
        """Get all comments for a post with author rep_accounts"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT c.id, c.post_id, c.content, c.parent_id, c.created_at, c.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url,
                       u.rep_accounts
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = $1
                ORDER BY c.created_at ASC
            """
            rows = await conn.fetch(query, post_id)
            
            # Get unique user IDs to fetch rep_accounts for all comment authors
            user_ids = list(set([row['user_id'] for row in rows]))
            
            # Fetch all rep_accounts data for these users
            user_rep_accounts = {}
            if user_ids:
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.user_id = ANY($1)
                    ORDER BY r.user_id, t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, user_ids)
                
                # Group rep accounts by user_id
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    user_id_key = rep_data['user_id']
                    
                    if user_id_key not in user_rep_accounts:
                        user_rep_accounts[user_id_key] = []
                    
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    user_rep_accounts[user_id_key].append(formatted_rep)
                
                # Ensure each user's rep_accounts are sorted by level_rank ASC (lowest rank number = highest position first)
                for user_id_key in user_rep_accounts:
                    user_rep_accounts[user_id_key].sort(key=lambda x: x['title']['level_rank'], reverse=False)
            
            comments = []
            for row in rows:
                comment = dict(row)
                author_user_id = comment.pop('user_id')
                comment['author'] = {
                    'id': author_user_id,
                    'username': comment.pop('author_username'),
                    'display_name': comment.pop('author_display_name'),
                    'avatar_url': comment.pop('author_avatar_url'),
                    'rep_accounts': user_rep_accounts.get(author_user_id, [])
                }
                # Remove the rep_accounts field from the comment level since we don't need it
                comment.pop('rep_accounts', None)
                comments.append(comment)
            
            return comments
    
    async def get_comment_by_id(self, comment_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a comment by ID with author info"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT c.id, c.post_id, c.user_id, c.content, c.parent_id, c.edited, c.edited_at,
                       c.upvotes, c.downvotes, c.reply_count, c.thread_level, c.thread_path,
                       c.created_at, c.updated_at,
                       u.username as author_username, u.display_name as author_display_name, 
                       u.avatar_url as author_avatar_url
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.id = $1
            """
            row = await conn.fetchrow(query, comment_id)
            if not row:
                return None
            
            comment = dict(row)
            # Format author info
            comment['author'] = {
                'id': comment['user_id'],
                'username': comment.pop('author_username'),
                'display_name': comment.pop('author_display_name'),
                'avatar_url': comment.pop('author_avatar_url'),
                'rep_accounts': []  # TODO: Add rep_accounts if needed
            }
            return comment
    
    async def update_comment(self, comment_id: UUID, comment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a comment"""
        async with db_manager.get_connection() as conn:
            query = """
                UPDATE comments 
                SET content = $2, edited = TRUE, edited_at = NOW(), updated_at = NOW()
                WHERE id = $1
                RETURNING id, post_id, user_id, content, parent_id, edited, edited_at,
                         upvotes, downvotes, reply_count, thread_level, thread_path,
                         created_at, updated_at
            """
            row = await conn.fetchrow(query, comment_id, comment_data.get('content'))
            return dict(row) if row else None
    
    async def delete_comment(self, comment_id: UUID) -> bool:
        """Delete a comment"""
        async with db_manager.get_connection() as conn:
            query = "DELETE FROM comments WHERE id = $1"
            result = await conn.execute(query, comment_id)
            return result == "DELETE 1"
    
    async def create_or_update_comment_vote(self, comment_id: UUID, user_id: UUID, vote_type: str) -> Optional[Dict[str, Any]]:
        """Create or update a vote on a comment"""
        async with db_manager.get_connection() as conn:
            # Check if vote already exists
            existing_query = "SELECT id, vote_type FROM votes WHERE comment_id = $1 AND user_id = $2"
            existing_vote = await conn.fetchrow(existing_query, comment_id, user_id)
            
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
                        RETURNING id, comment_id, user_id, vote_type, created_at, updated_at
                    """
                    row = await conn.fetchrow(update_query, vote_type, existing_vote['id'])
                    return dict(row)
            else:
                # New vote
                vote_id = uuid4()
                insert_query = """
                    INSERT INTO votes (id, comment_id, user_id, vote_type)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, comment_id, user_id, vote_type, created_at, updated_at
                """
                row = await conn.fetchrow(insert_query, vote_id, comment_id, user_id, vote_type)
                return dict(row)
    
    async def get_comment_vote_counts(self, comment_id: UUID) -> Dict[str, int]:
        """Get vote counts for a comment"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT 
                    COUNT(CASE WHEN vote_type = 'upvote' THEN 1 END) as upvotes,
                    COUNT(CASE WHEN vote_type = 'downvote' THEN 1 END) as downvotes
                FROM votes
                WHERE comment_id = $1
            """
            row = await conn.fetchrow(query, comment_id)
            return {
                'upvotes': row['upvotes'] or 0,
                'downvotes': row['downvotes'] or 0
            }
    
    async def get_user_vote_on_comment(self, comment_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a user's vote on a comment"""
        async with db_manager.get_connection() as conn:
            query = "SELECT id, vote_type, created_at FROM votes WHERE comment_id = $1 AND user_id = $2"
            row = await conn.fetchrow(query, comment_id, user_id)
            return dict(row) if row else None

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
        """Get trending posts based on engagement in the last N hours including author rep_accounts"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT p.id, p.title, p.content, p.post_type, p.media_urls, p.location, p.tags,
                       p.created_at, p.updated_at,
                       u.id as user_id, u.username as author_username, 
                       u.display_name as author_display_name, u.avatar_url as author_avatar_url,
                       u.rep_accounts,
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
            
            # Get unique user IDs to fetch rep_accounts for all authors
            user_ids = list(set([row['user_id'] for row in rows]))
            
            # Fetch all rep_accounts data for these users
            user_rep_accounts = {}
            if user_ids:
                rep_query = """
                    SELECT r.id, r.user_id, r.created_at as linked_at,
                           t.id as title_id, t.title_name, t.abbreviation, t.level_rank, t.description,
                           j.id as jurisdiction_id, j.name as jurisdiction_name, j.level_name as jurisdiction_level
                    FROM representatives r
                    JOIN titles t ON r.title_id = t.id
                    JOIN jurisdictions j ON r.jurisdiction_id = j.id
                    WHERE r.user_id = ANY($1)
                    ORDER BY r.user_id, t.level_rank DESC
                """
                rep_rows = await conn.fetch(rep_query, user_ids)
                
                # Group rep accounts by user_id
                for rep_row in rep_rows:
                    rep_data = dict(rep_row)
                    user_id_key = rep_data['user_id']
                    
                    if user_id_key not in user_rep_accounts:
                        user_rep_accounts[user_id_key] = []
                    
                    formatted_rep = {
                        'id': rep_data['id'],
                        'title': {
                            'id': rep_data['title_id'],
                            'title_name': rep_data['title_name'],
                            'abbreviation': rep_data['abbreviation'],
                            'level_rank': rep_data['level_rank'],
                            'description': rep_data['description']
                        },
                        'jurisdiction': {
                            'id': rep_data['jurisdiction_id'],
                            'name': rep_data['jurisdiction_name'],
                            'level_name': rep_data['jurisdiction_level']
                        },
                        'linked_at': rep_data['linked_at']
                    }
                    user_rep_accounts[user_id_key].append(formatted_rep)
                
                # Ensure each user's rep_accounts are sorted by level_rank ASC (lowest rank number = highest position first)
                for user_id_key in user_rep_accounts:
                    user_rep_accounts[user_id_key].sort(key=lambda x: x['title']['level_rank'], reverse=False)
            
            posts = []
            for row in rows:
                post = dict(row)
                author_user_id = post.pop('user_id')
                post['author'] = {
                    'id': author_user_id,
                    'username': post.pop('author_username'),
                    'display_name': post.pop('author_display_name'),
                    'avatar_url': post.pop('author_avatar_url'),
                    'rep_accounts': user_rep_accounts.get(author_user_id, [])
                }
                
                # Remove internal scoring field and rep_accounts field at post level
                post.pop('engagement_score', None)
                post.pop('rep_accounts', None)
                
                posts.append(post)
            
            return posts

    async def get_representatives_by_location(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Get representatives and judiciary for a specific location based on coordinates"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT DISTINCT 
                    r.id as representative_id,
                    t.id as title_id,
                    t.title_name,
                    t.abbreviation,
                    t.level_rank,
                    t.description as title_description,
                    t.title_type,
                    t.level,
                    t.is_elected,
                    t.term_length,
                    t.status,
                    t.created_at as title_created_at,
                    t.updated_at as title_updated_at,
                    j.id as jurisdiction_id,
                    j.name as jurisdiction_name,
                    j.level_name as jurisdiction_level,
                    j.level_rank as jurisdiction_rank,
                    j.parent_id as parent_jurisdiction_id,
                    j.created_at as jurisdiction_created_at,
                    j.updated_at as jurisdiction_updated_at
                FROM jurisdictions j
                JOIN representatives r ON r.jurisdiction_id = j.id
                JOIN titles t ON r.title_id = t.id
                WHERE ST_Contains(j.boundary, ST_SetSRID(ST_Point($1, $2), 4326))
                ORDER BY t.level_rank DESC, j.level_rank DESC
            """
            
            rows = await conn.fetch(query, longitude, latitude)
            
            representatives = []
            for row in rows:
                rep_data = dict(row)
                representative = {
                    'representative_id': str(rep_data['representative_id']),
                    'title': {
                        'id': str(rep_data['title_id']),
                        'title_name': rep_data['title_name'],
                        'abbreviation': rep_data['abbreviation'],
                        'level_rank': rep_data['level_rank'],
                        'description': rep_data['title_description'],
                        'title_type': rep_data['title_type'],
                        'level': rep_data['level'],
                        'is_elected': rep_data['is_elected'],
                        'term_length': rep_data['term_length'],
                        'status': rep_data['status'],
                        'created_at': rep_data['title_created_at'].isoformat() if rep_data['title_created_at'] else None,
                        'updated_at': rep_data['title_updated_at'].isoformat() if rep_data['title_updated_at'] else None
                    },
                    'jurisdiction': {
                        'id': str(rep_data['jurisdiction_id']),
                        'name': rep_data['jurisdiction_name'],
                        'level_name': rep_data['jurisdiction_level'],
                        'level_rank': rep_data['jurisdiction_rank'],
                        'parent_jurisdiction_id': str(rep_data['parent_jurisdiction_id']) if rep_data['parent_jurisdiction_id'] else None,
                        'created_at': rep_data['jurisdiction_created_at'].isoformat() if rep_data['jurisdiction_created_at'] else None,
                        'updated_at': rep_data['jurisdiction_updated_at'].isoformat() if rep_data['jurisdiction_updated_at'] else None
                    },
                    'display_name': f"{rep_data['abbreviation']} - {rep_data['jurisdiction_name']}" if rep_data['abbreviation'] else f"{rep_data['title_name']} - {rep_data['jurisdiction_name']}"
                }
                representatives.append(representative)
            
            return representatives

    # Follow/Unfollow operations
    async def follow_user(self, follower_id: UUID, followed_id: UUID) -> Dict[str, Any]:
        """Follow a user and update mutual status"""
        async with self.get_connection_with_retry() as conn:
            async with conn.transaction():
                # Check if already following
                check_query = """
                    SELECT 1 FROM follows 
                    WHERE follower_id = $1 AND followed_id = $2
                """
                existing = await conn.fetchrow(check_query, follower_id, followed_id)
                
                if existing:
                    raise ValueError("User is already being followed")
                
                # Check if users exist
                user_check_query = """
                    SELECT 
                        (SELECT COUNT(*) FROM users WHERE id = $1) as follower_exists,
                        (SELECT COUNT(*) FROM users WHERE id = $2) as followed_exists
                """
                user_check = await conn.fetchrow(user_check_query, follower_id, followed_id)
                
                if user_check['follower_exists'] == 0:
                    raise ValueError("Follower user does not exist")
                if user_check['followed_exists'] == 0:
                    raise ValueError("User to follow does not exist")
                
                # Insert follow relationship
                insert_query = """
                    INSERT INTO follows (follower_id, followed_id, created_at)
                    VALUES ($1, $2, NOW())
                    RETURNING created_at
                """
                result = await conn.fetchrow(insert_query, follower_id, followed_id)
                
                # Check if mutual relationship exists
                mutual_query = """
                    SELECT mutual FROM follows 
                    WHERE follower_id = $1 AND followed_id = $2
                """
                mutual_result = await conn.fetchrow(mutual_query, follower_id, followed_id)
                is_mutual = mutual_result['mutual'] if mutual_result else False
                
                logger.info(f"User {follower_id} followed user {followed_id} | Mutual: {is_mutual}")
                
                return {
                    'success': True,
                    'mutual': is_mutual,
                    'followed_at': result['created_at']
                }

    async def unfollow_user(self, follower_id: UUID, followed_id: UUID) -> Dict[str, Any]:
        """Unfollow a user and update mutual status"""
        async with self.get_connection_with_retry() as conn:
            async with conn.transaction():
                # Check if following relationship exists
                check_query = """
                    SELECT 1 FROM follows 
                    WHERE follower_id = $1 AND followed_id = $2
                """
                existing = await conn.fetchrow(check_query, follower_id, followed_id)
                
                if not existing:
                    raise ValueError("User is not being followed")
                
                # Delete follow relationship
                delete_query = """
                    DELETE FROM follows 
                    WHERE follower_id = $1 AND followed_id = $2
                """
                await conn.execute(delete_query, follower_id, followed_id)
                
                logger.info(f"User {follower_id} unfollowed user {followed_id}")
                
                return {'success': True}

    async def get_user_followers(self, user_id: UUID, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get list of users following the specified user"""
        async with db_manager.get_connection() as conn:
            offset = (page - 1) * size
            
            # Get followers with user details
            query = """
                SELECT 
                    u.id,
                    u.username,
                    u.display_name,
                    u.avatar_url,
                    u.is_verified,
                    f.mutual,
                    f.created_at as followed_at
                FROM follows f
                JOIN users u ON f.follower_id = u.id
                WHERE f.followed_id = $1
                ORDER BY f.created_at DESC
                LIMIT $2 OFFSET $3
            """
            
            followers_rows = await conn.fetch(query, user_id, size, offset)
            
            # Get total count
            count_query = """
                SELECT COUNT(*) as total
                FROM follows f
                WHERE f.followed_id = $1
            """
            count_result = await conn.fetchrow(count_query, user_id)
            total_count = count_result['total']
            
            followers = [dict(row) for row in followers_rows]
            
            return {
                'followers': followers,
                'total_count': total_count,
                'page': page,
                'size': size,
                'has_next': total_count > page * size
            }

    async def get_user_following(self, user_id: UUID, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get list of users that the specified user is following"""
        async with db_manager.get_connection() as conn:
            offset = (page - 1) * size
            
            # Get following with user details
            query = """
                SELECT 
                    u.id,
                    u.username,
                    u.display_name,
                    u.avatar_url,
                    u.is_verified,
                    f.mutual,
                    f.created_at as followed_at
                FROM follows f
                JOIN users u ON f.followed_id = u.id
                WHERE f.follower_id = $1
                ORDER BY f.created_at DESC
                LIMIT $2 OFFSET $3
            """
            
            following_rows = await conn.fetch(query, user_id, size, offset)
            
            # Get total count
            count_query = """
                SELECT COUNT(*) as total
                FROM follows f
                WHERE f.follower_id = $1
            """
            count_result = await conn.fetchrow(count_query, user_id)
            total_count = count_result['total']
            
            following = [dict(row) for row in following_rows]
            
            return {
                'following': following,
                'total_count': total_count,
                'page': page,
                'size': size,
                'has_next': total_count > page * size
            }

    async def get_follow_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get follow statistics for a user"""
        async with db_manager.get_connection() as conn:
            query = """
                SELECT 
                    u.followers_count,
                    u.following_count,
                    (
                        SELECT COUNT(*) 
                        FROM follows f 
                        WHERE f.follower_id = $1 AND f.mutual = true
                    ) as mutual_follows_count
                FROM users u
                WHERE u.id = $1
            """
            
            result = await conn.fetchrow(query, user_id)
            
            if not result:
                return {
                    'followers_count': 0,
                    'following_count': 0,
                    'mutual_follows_count': 0
                }
            
            return dict(result)

    async def check_follow_status(self, follower_id: UUID, followed_id: UUID) -> Dict[str, Any]:
        """Check if one user follows another and get mutual status"""
        async with db_manager.get_connection() as conn:
            # Check if follower follows followed
            follow_query = """
                SELECT mutual FROM follows 
                WHERE follower_id = $1 AND followed_id = $2
            """
            follow_result = await conn.fetchrow(follow_query, follower_id, followed_id)
            
            # Check if followed follows follower back  
            follow_back_query = """
                SELECT 1 FROM follows 
                WHERE follower_id = $1 AND followed_id = $2
            """
            follow_back_result = await conn.fetchrow(follow_back_query, followed_id, follower_id)
            
            is_following = follow_result is not None
            is_followed_by = follow_back_result is not None
            mutual = follow_result['mutual'] if follow_result else False
            
            return {
                'is_following': is_following,
                'is_followed_by': is_followed_by,
                'mutual': mutual
            }
