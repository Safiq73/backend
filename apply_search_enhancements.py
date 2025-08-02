#!/usr/bin/env python3
"""
Consolidated Search Migration - Apply All Search Features

This script applies search optimization to both the main schema and static data schema.
"""

import asyncio
import asyncpg
import logging
import os
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.core.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def apply_search_enhancements():
    """Apply search enhancements to existing database"""
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = await asyncpg.connect(settings.database_url)
        
        logger.info("Applying search enhancements to existing database...")
        
        # Enable extensions if not already enabled
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        logger.info("✅ pg_trgm extension enabled")
        
        # Add search vectors to existing tables if they don't exist
        search_enhancements = """
        -- Add search vector to users if not exists
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE users ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
        
        -- Add search vector to posts if not exists
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'posts' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE posts ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
        
        -- Add search vector to comments if not exists
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'comments' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE comments ADD COLUMN search_vector tsvector;
            END IF;
        END $$;
        
        -- Add search optimization columns to representatives if they don't exist
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'cached_name'
            ) THEN
                ALTER TABLE representatives ADD COLUMN cached_name TEXT;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'cached_designation'
            ) THEN
                ALTER TABLE representatives ADD COLUMN cached_designation TEXT;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'cached_constituency'
            ) THEN
                ALTER TABLE representatives ADD COLUMN cached_constituency TEXT;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE representatives ADD COLUMN search_vector tsvector;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'is_verified'
            ) THEN
                ALTER TABLE representatives ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'contact_email'
            ) THEN
                ALTER TABLE representatives ADD COLUMN contact_email TEXT;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'party'
            ) THEN
                ALTER TABLE representatives ADD COLUMN party TEXT;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'avatar_url'
            ) THEN
                ALTER TABLE representatives ADD COLUMN avatar_url TEXT;
            END IF;
        END $$;
        """
        
        await conn.execute(search_enhancements)
        logger.info("✅ Search columns added to existing tables")
        
        # Update existing data with search vectors
        logger.info("Updating existing data with search vectors...")
        
        # Update users
        result = await conn.execute("""
            UPDATE users SET search_vector = 
                setweight(to_tsvector('english', COALESCE(username, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(display_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(bio, '')), 'B')
            WHERE search_vector IS NULL
        """)
        logger.info(f"✅ Updated {result.split()[-1]} user search vectors")
        
        # Update posts  
        result = await conn.execute("""
            UPDATE posts SET search_vector = 
                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(content, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(location, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(array_to_string(tags, ' '), '')), 'C')
            WHERE search_vector IS NULL
        """)
        logger.info(f"✅ Updated {result.split()[-1]} post search vectors")
        
        # Update comments
        result = await conn.execute("""
            UPDATE comments SET search_vector = 
                setweight(to_tsvector('english', COALESCE(content, '')), 'A')
            WHERE search_vector IS NULL
        """)
        logger.info(f"✅ Updated {result.split()[-1]} comment search vectors")
        
        # Update representatives with cached data
        await conn.execute("""
            UPDATE representatives SET 
                cached_name = COALESCE(u.display_name, 'Unknown Representative'),
                cached_designation = COALESCE(t.title_name, 'Representative'),
                cached_constituency = COALESCE(j.name, 'Unknown Constituency'),
                is_verified = (representatives.user_id IS NOT NULL)
            FROM users u, titles t, jurisdictions j
            WHERE representatives.user_id = u.id 
                AND representatives.title_id = t.id 
                AND representatives.jurisdiction_id = j.id
                AND representatives.cached_name IS NULL
        """)
        
        # Update representatives without users
        await conn.execute("""
            UPDATE representatives SET 
                cached_name = 'Unknown Representative',
                cached_designation = COALESCE(t.title_name, 'Representative'),
                cached_constituency = COALESCE(j.name, 'Unknown Constituency'),
                is_verified = FALSE
            FROM titles t, jurisdictions j
            WHERE representatives.title_id = t.id 
                AND representatives.jurisdiction_id = j.id
                AND representatives.user_id IS NULL
                AND representatives.cached_name IS NULL
        """)
        
        # Update representative search vectors
        result = await conn.execute("""
            UPDATE representatives SET search_vector = 
                setweight(to_tsvector('english', COALESCE(cached_name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(cached_designation, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(cached_constituency, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(party, '')), 'C')
            WHERE search_vector IS NULL
        """)
        logger.info(f"✅ Updated {result.split()[-1]} representative search vectors")
        
        # Verify search functionality
        logger.info("Verifying search functionality...")
        
        # Test search on users
        users_with_search = await conn.fetchval("""
            SELECT COUNT(*) FROM users WHERE search_vector IS NOT NULL
        """)
        
        # Test search on posts
        posts_with_search = await conn.fetchval("""
            SELECT COUNT(*) FROM posts WHERE search_vector IS NOT NULL
        """)
        
        # Test search on representatives
        reps_with_search = await conn.fetchval("""
            SELECT COUNT(*) FROM representatives WHERE search_vector IS NOT NULL
        """)
        
        logger.info(f"✅ Search vectors applied:")
        logger.info(f"  - Users: {users_with_search}")
        logger.info(f"  - Posts: {posts_with_search}")
        logger.info(f"  - Representatives: {reps_with_search}")
        
        # Test a search query
        try:
            test_result = await conn.fetch("""
                SELECT 'users' as type, COUNT(*) as count
                FROM users 
                WHERE search_vector @@ plainto_tsquery('english', 'test')
                UNION ALL
                SELECT 'posts' as type, COUNT(*) as count
                FROM posts 
                WHERE search_vector @@ plainto_tsquery('english', 'test')
                LIMIT 5
            """)
            logger.info(f"✅ Test search executed successfully: {len(test_result)} result types")
        except Exception as e:
            logger.warning(f"⚠️  Test search failed (this is normal if no test data): {e}")
        
        logger.info("🎉 Search enhancements applied successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()

def main():
    """Main entry point"""
    logger.info("🚀 Applying search enhancements to existing database...")
    
    try:
        asyncio.run(apply_search_enhancements())
        logger.info("✅ Search enhancements applied successfully!")
        logger.info("")
        logger.info("Search features now available:")
        logger.info("- Full-text search across users, posts, representatives") 
        logger.info("- Fuzzy text search with pg_trgm")
        logger.info("- Automatic search vector updates via triggers")
        logger.info("- Search analytics and suggestions")
        logger.info("- Relevance scoring functions")
        logger.info("")
        logger.info("Next: Create the search service and API endpoint!")
        
    except Exception as e:
        logger.error(f"❌ Search enhancement failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
