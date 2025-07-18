"""
Database migration script to align current implementation with corrected schema
This script handles the schema changes needed to make the database consistent
"""

import asyncio
import asyncpg
from typing import List, Dict, Any
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigration:
    def __init__(self, database_url: str):
        self.database_url = database_url
    
    async def connect(self):
        """Connect to the database"""
        self.conn = await asyncpg.connect(self.database_url)
        logger.info("Connected to database")
    
    async def disconnect(self):
        """Disconnect from the database"""
        await self.conn.close()
        logger.info("Disconnected from database")
    
    async def execute_migration(self, migration_sql: str, description: str):
        """Execute a migration step"""
        try:
            await self.conn.execute(migration_sql)
            logger.info(f"✓ {description}")
        except Exception as e:
            logger.error(f"✗ {description}: {e}")
            raise
    
    async def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        result = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
        """, table_name)
        return result
    
    async def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        result = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = $1 AND column_name = $2
            )
        """, table_name, column_name)
        return result
    
    async def migrate_user_schema(self):
        """Migrate user table schema"""
        logger.info("Migrating user table schema...")
        
        # Check if users table exists
        if not await self.check_table_exists('users'):
            logger.info("Creating users table...")
            await self.execute_migration("""
                CREATE TABLE users (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(100),
                    bio TEXT,
                    avatar_url TEXT,
                    role VARCHAR(20) NOT NULL DEFAULT 'citizen',
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """, "Create users table")
        
        # Add missing columns if they don't exist
        columns_to_add = [
            ("username", "VARCHAR(50)"),
            ("display_name", "VARCHAR(100)"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("is_verified", "BOOLEAN DEFAULT FALSE"),
        ]
        
        for column_name, column_type in columns_to_add:
            if not await self.check_column_exists('users', column_name):
                await self.execute_migration(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_type}",
                    f"Add {column_name} column to users table"
                )
        
        # Create indexes
        await self.execute_migration("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
            CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
            CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active);
            CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);
        """, "Create user table indexes")
    
    async def migrate_post_schema(self):
        """Migrate post table schema"""
        logger.info("Migrating post table schema...")
        
        # Check if posts table exists
        if not await self.check_table_exists('posts'):
            logger.info("Creating posts table...")
            await self.execute_migration("""
                CREATE TABLE posts (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    post_type VARCHAR(20) NOT NULL DEFAULT 'discussion',
                    status VARCHAR(20) DEFAULT 'open',
                    area VARCHAR(100),
                    category VARCHAR(100),
                    location VARCHAR(255),
                    tags TEXT[],
                    media_urls TEXT[],
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    share_count INTEGER DEFAULT 0,
                    priority_score INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """, "Create posts table")
        
        # Add missing columns if they don't exist
        columns_to_add = [
            ("area", "VARCHAR(100)"),
            ("category", "VARCHAR(100)"),
            ("status", "VARCHAR(20) DEFAULT 'open'"),
            ("tags", "TEXT[]"),
            ("media_urls", "TEXT[]"),
            ("upvotes", "INTEGER DEFAULT 0"),
            ("downvotes", "INTEGER DEFAULT 0"),
            ("comment_count", "INTEGER DEFAULT 0"),
            ("view_count", "INTEGER DEFAULT 0"),
            ("share_count", "INTEGER DEFAULT 0"),
            ("priority_score", "INTEGER DEFAULT 0"),
            ("last_activity_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
        ]
        
        for column_name, column_type in columns_to_add:
            if not await self.check_column_exists('posts', column_name):
                await self.execute_migration(
                    f"ALTER TABLE posts ADD COLUMN {column_name} {column_type}",
                    f"Add {column_name} column to posts table"
                )
        
        # Rename images column to media_urls if it exists
        if await self.check_column_exists('posts', 'images'):
            await self.execute_migration(
                "ALTER TABLE posts RENAME COLUMN images TO media_urls",
                "Rename images column to media_urls"
            )
        
        # Create indexes
        await self.execute_migration("""
            CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts (user_id);
            CREATE INDEX IF NOT EXISTS idx_posts_status ON posts (status);
            CREATE INDEX IF NOT EXISTS idx_posts_type ON posts (post_type);
            CREATE INDEX IF NOT EXISTS idx_posts_area ON posts (area);
            CREATE INDEX IF NOT EXISTS idx_posts_category ON posts (category);
            CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_updated_at ON posts (updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_last_activity ON posts (last_activity_at DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_priority ON posts (priority_score DESC);
        """, "Create post table indexes")
    
    async def migrate_comment_schema(self):
        """Migrate comment table schema"""
        logger.info("Migrating comment table schema...")
        
        # Check if comments table exists
        if not await self.check_table_exists('comments'):
            logger.info("Creating comments table...")
            await self.execute_migration("""
                CREATE TABLE comments (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    edited BOOLEAN DEFAULT FALSE,
                    edited_at TIMESTAMP WITH TIME ZONE,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    reply_count INTEGER DEFAULT 0,
                    thread_level INTEGER DEFAULT 0,
                    thread_path TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """, "Create comments table")
        
        # Add missing columns if they don't exist
        columns_to_add = [
            ("edited", "BOOLEAN DEFAULT FALSE"),
            ("edited_at", "TIMESTAMP WITH TIME ZONE"),
            ("upvotes", "INTEGER DEFAULT 0"),
            ("downvotes", "INTEGER DEFAULT 0"),
            ("reply_count", "INTEGER DEFAULT 0"),
            ("thread_level", "INTEGER DEFAULT 0"),
            ("thread_path", "TEXT"),
        ]
        
        for column_name, column_type in columns_to_add:
            if not await self.check_column_exists('comments', column_name):
                await self.execute_migration(
                    f"ALTER TABLE comments ADD COLUMN {column_name} {column_type}",
                    f"Add {column_name} column to comments table"
                )
        
        # Create indexes
        await self.execute_migration("""
            CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments (post_id);
            CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments (user_id);
            CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments (parent_id);
            CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_comments_thread_path ON comments (thread_path);
        """, "Create comment table indexes")
    
    async def migrate_vote_schema(self):
        """Migrate vote table schema"""
        logger.info("Migrating vote table schema...")
        
        # Check if votes table exists
        if not await self.check_table_exists('votes'):
            logger.info("Creating votes table...")
            await self.execute_migration("""
                CREATE TABLE votes (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
                    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
                    vote_type VARCHAR(10) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT unique_post_vote UNIQUE (user_id, post_id),
                    CONSTRAINT unique_comment_vote UNIQUE (user_id, comment_id),
                    CONSTRAINT vote_target_check CHECK (
                        (post_id IS NOT NULL AND comment_id IS NULL) OR 
                        (post_id IS NULL AND comment_id IS NOT NULL)
                    )
                )
            """, "Create votes table")
        
        # Create indexes
        await self.execute_migration("""
            CREATE INDEX IF NOT EXISTS idx_votes_user_id ON votes (user_id);
            CREATE INDEX IF NOT EXISTS idx_votes_post_id ON votes (post_id);
            CREATE INDEX IF NOT EXISTS idx_votes_comment_id ON votes (comment_id);
            CREATE INDEX IF NOT EXISTS idx_votes_type ON votes (vote_type);
        """, "Create vote table indexes")
    
    async def migrate_supporting_tables(self):
        """Migrate supporting tables"""
        logger.info("Migrating supporting tables...")
        
        # Saved posts table
        if not await self.check_table_exists('saved_posts'):
            await self.execute_migration("""
                CREATE TABLE saved_posts (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, post_id)
                )
            """, "Create saved_posts table")
        
        # Notifications table
        if not await self.check_table_exists('notifications'):
            await self.execute_migration("""
                CREATE TABLE notifications (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
                    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
                    triggered_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    notification_type VARCHAR(20) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    action_url TEXT,
                    read BOOLEAN DEFAULT FALSE,
                    read_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """, "Create notifications table")
        
        # User sessions table
        if not await self.check_table_exists('user_sessions'):
            await self.execute_migration("""
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
                )
            """, "Create user_sessions table")
    
    async def run_full_migration(self):
        """Run the complete migration"""
        logger.info("Starting database migration...")
        
        try:
            await self.connect()
            
            # Enable UUID extension if not already enabled
            await self.execute_migration(
                'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
                "Enable UUID extension"
            )
            
            # Run migrations in order
            await self.migrate_user_schema()
            await self.migrate_post_schema()
            await self.migrate_comment_schema()
            await self.migrate_vote_schema()
            await self.migrate_supporting_tables()
            
            logger.info("✓ Database migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            await self.disconnect()

# Example usage
async def main():
    # Update with your database URL
    database_url = "postgresql://user:password@localhost/civicpulse"
    
    migration = DatabaseMigration(database_url)
    await migration.run_full_migration()

if __name__ == "__main__":
    asyncio.run(main())
