#!/usr/bin/env python3
"""
Search Optimization Migration Runner

This script applies the search optimization migration to enable full-text search
capabilities across users, posts, and representatives.
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

async def run_search_migration():
    """Run the search optimization migration"""
    
    # List of migration files to run in order
    migration_files = [
        "002_search_basic_setup.sql",
        "002_search_functions.sql", 
        "002_search_data.sql",
        "002_search_helpers.sql"
    ]
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = await asyncpg.connect(settings.database_url)
        
        # Run each migration file
        for migration_file in migration_files:
            migration_path = backend_dir / "app" / "db" / "migrations" / migration_file
            logger.info(f"Reading migration file: {migration_path}")
            
            if not migration_path.exists():
                raise FileNotFoundError(f"Migration file not found: {migration_path}")
            
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            logger.info(f"Executing {migration_file}...")
            await conn.execute(migration_sql)
            logger.info(f"✅ {migration_file} completed successfully!")
        
        logger.info("🎉 All search optimization migrations completed successfully!")
        
        # Verify the migration
        logger.info("Verifying migration...")
        
        # Check if search vectors were added
        users_has_search = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'search_vector'
            )
        """)
        
        posts_has_search = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'posts' AND column_name = 'search_vector'
            )
        """)
        
        reps_has_search = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'representatives' AND column_name = 'search_vector'
            )
        """)
        
        # Check if search tables were created
        search_analytics_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'search_analytics'
            )
        """)
        
        search_suggestions_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'search_suggestions'
            )
        """)
        
        # Verify search indexes
        search_indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE indexname LIKE '%search%' OR indexname LIKE '%trgm%'
            ORDER BY indexname
        """)
        
        # Print verification results
        logger.info("Migration verification results:")
        logger.info(f"  ✅ Users search vector: {'✓' if users_has_search else '✗'}")
        logger.info(f"  ✅ Posts search vector: {'✓' if posts_has_search else '✗'}")
        logger.info(f"  ✅ Representatives search vector: {'✓' if reps_has_search else '✗'}")
        logger.info(f"  ✅ Search analytics table: {'✓' if search_analytics_exists else '✗'}")
        logger.info(f"  ✅ Search suggestions table: {'✓' if search_suggestions_exists else '✗'}")
        logger.info(f"  ✅ Search indexes created: {len(search_indexes)} indexes")
        
        if search_indexes:
            logger.info("Search indexes:")
            for idx in search_indexes:
                logger.info(f"    - {idx['indexname']}")
        
        # Test search functionality
        logger.info("Testing search functionality...")
        
        # Test search suggestions
        suggestions = await conn.fetch("""
            SELECT suggestion, category, search_count 
            FROM search_suggestions 
            ORDER BY search_count DESC 
            LIMIT 3
        """)
        
        logger.info(f"Search suggestions loaded: {len(suggestions)}")
        for suggestion in suggestions:
            logger.info(f"  - {suggestion['suggestion']} ({suggestion['category']}, {suggestion['search_count']} searches)")
        
        # Test if trigram extension is available
        trgm_available = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
            )
        """)
        logger.info(f"  ✅ pg_trgm extension: {'✓' if trgm_available else '✗'}")
        
        # Test search functions
        try:
            test_suggestions = await conn.fetch("""
                SELECT * FROM get_search_suggestions('road', 2)
            """)
            logger.info(f"  ✅ Search suggestions function: ✓ (returned {len(test_suggestions)} results)")
        except Exception as e:
            logger.error(f"  ✗ Search suggestions function failed: {e}")
        
        logger.info("🎉 Search optimization migration verification completed!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()

def main():
    """Main entry point"""
    logger.info("🚀 Starting search optimization migration...")
    
    try:
        asyncio.run(run_search_migration())
        logger.info("✅ Search migration completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run the search service implementation")
        logger.info("2. Create the search API endpoint")
        logger.info("3. Update the frontend SearchModal component")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
