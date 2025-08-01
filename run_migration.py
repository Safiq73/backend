"""
Simple migration runner for the follows table
"""
import asyncio
import asyncpg
import os
from pathlib import Path

# Database URL - update this to match your configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/civicpulse")

async def run_migration():
    """Run the follows table migration"""
    try:
        # Read the migration file
        migration_file = Path(__file__).parent / "app" / "db" / "migrations" / "001_add_follows_table.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Connect to database and run migration
        conn = await asyncpg.connect(DATABASE_URL)
        
        try:
            print("🚀 Running follows table migration...")
            
            # Execute the migration SQL
            await conn.execute(migration_sql)
            
            print("✅ Migration completed successfully!")
            print("📋 Created:")
            print("   - follows table with primary key (follower_id, followed_id)")
            print("   - Indexes for performance")
            print("   - Triggers for automatic mutual status updates")
            print("   - Triggers for user follow count updates")
            print("   - Added followers_count and following_count columns to users table")
            
        finally:
            await conn.close()
    
    except asyncpg.PostgresError as e:
        print(f"❌ Database error: {e}")
    except FileNotFoundError as e:
        print(f"❌ File error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🔧 CivicPulse Follow/Unfollow Migration Runner")
    print("=" * 50)
    asyncio.run(run_migration())
