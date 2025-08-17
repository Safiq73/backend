#!/usr/bin/env python3
"""
Permission System Migration Script

This script applies the permission system schema and data migrations to the database.
It should be run after the main schema.sql has been applied.

Usage:
    python apply_permissions_migration.py [--dry-run]
"""

import asyncio
import asyncpg
import sys
import argparse
from pathlib import Path
from typing import Optional

# Add the backend app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class PermissionsMigrationManager:
    """Manages the permission system database migration"""
    
    def __init__(self):
        self.connection: Optional[asyncpg.Connection] = None
        
    async def connect(self):
        """Connect to the database"""
        try:
            self.connection = await asyncpg.connect(settings.database_url)
            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from the database"""
        if self.connection:
            await self.connection.close()
            logger.info("✅ Disconnected from database")
            
    async def check_existing_permissions_tables(self) -> bool:
        """Check if permission tables already exist"""
        try:
            result = await self.connection.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('system_roles', 'permissions', 'user_roles', 'role_permissions')
            """)
            return result > 0
        except Exception as e:
            logger.error(f"❌ Error checking existing tables: {e}")
            return False
            
    async def apply_schema_migration(self, dry_run: bool = False) -> bool:
        """Apply the permission system schema"""
        try:
            # Read the migration SQL
            migration_file = Path(__file__).parent / "permissions_migration.sql"
            
            if not migration_file.exists():
                logger.error(f"❌ Migration file not found: {migration_file}")
                return False
                
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
                
            if dry_run:
                logger.info("🔍 DRY RUN - Would execute the following migration:")
                logger.info(f"Migration SQL length: {len(migration_sql)} characters")
                return True
                
            # Execute the migration
            logger.info("🚀 Applying permission system migration...")
            await self.connection.execute(migration_sql)
            logger.info("✅ Permission system migration applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration: {e}")
            return False
            
    async def verify_migration(self) -> bool:
        """Verify that the migration was applied correctly"""
        try:
            # Check that all required tables exist
            required_tables = [
                'system_roles', 'permissions', 'role_permissions', 
                'user_roles', 'user_permission_overrides', 'permission_audit_log',
                'permission_cache', 'token_blacklist'
            ]
            
            for table in required_tables:
                exists = await self.connection.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table)
                
                if not exists:
                    logger.error(f"❌ Required table '{table}' not found")
                    return False
                    
            # Check that default roles were created
            role_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM system_roles WHERE is_system_role = true
            """)
            
            if role_count < 7:  # We expect 7 default roles
                logger.error(f"❌ Expected 7 default roles, found {role_count}")
                return False
                
            # Check that permissions were created
            permission_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM permissions WHERE is_system_permission = true
            """)
            
            if permission_count < 30:  # We expect at least 30 permissions
                logger.error(f"❌ Expected at least 30 permissions, found {permission_count}")
                return False
                
            # Check that role-permission mappings exist
            mapping_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM role_permissions
            """)
            
            if mapping_count < 50:  # We expect at least 50 mappings
                logger.error(f"❌ Expected at least 50 role-permission mappings, found {mapping_count}")
                return False
                
            # Check that user roles were assigned
            user_role_count = await self.connection.fetchval("""
                SELECT COUNT(*) FROM user_roles
            """)
            
            logger.info(f"✅ Migration verification successful:")
            logger.info(f"   - Tables created: {len(required_tables)}")
            logger.info(f"   - Default roles: {role_count}")
            logger.info(f"   - Permissions: {permission_count}")
            logger.info(f"   - Role mappings: {mapping_count}")
            logger.info(f"   - User roles assigned: {user_role_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            return False
            
    async def show_migration_summary(self):
        """Show a summary of the current permission system state"""
        try:
            # Get role summary
            roles = await self.connection.fetch("""
                SELECT name, display_name, level, 
                       (SELECT COUNT(*) FROM user_roles ur WHERE ur.role_id = sr.id AND ur.is_active = true) as user_count
                FROM system_roles sr 
                ORDER BY level DESC
            """)
            
            logger.info("\n📊 Permission System Summary:")
            logger.info("=" * 50)
            logger.info("ROLES:")
            for role in roles:
                logger.info(f"  {role['display_name']} ({role['name']}) - Level {role['level']} - {role['user_count']} users")
                
            # Get permission summary by resource
            resources = await self.connection.fetch("""
                SELECT resource, COUNT(*) as permission_count
                FROM permissions 
                GROUP BY resource 
                ORDER BY permission_count DESC
            """)
            
            logger.info("\nPERMISSIONS BY RESOURCE:")
            for resource in resources:
                logger.info(f"  {resource['resource']}: {resource['permission_count']} permissions")
                
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"❌ Failed to show summary: {e}")


async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="Apply CivicPulse permission system migration")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without applying changes")
    parser.add_argument("--force", action="store_true", help="Force migration even if tables exist")
    parser.add_argument("--summary", action="store_true", help="Show migration summary only")
    
    args = parser.parse_args()
    
    manager = PermissionsMigrationManager()
    
    try:
        await manager.connect()
        
        if args.summary:
            await manager.show_migration_summary()
            return
            
        # Check if migration is needed
        tables_exist = await manager.check_existing_permissions_tables()
        
        if tables_exist and not args.force:
            logger.warning("⚠️ Permission tables already exist. Use --force to override or --summary to view current state.")
            await manager.show_migration_summary()
            return
            
        if tables_exist and args.force:
            logger.warning("🔄 Force mode enabled - proceeding with migration despite existing tables")
            
        # Apply migration
        success = await manager.apply_schema_migration(dry_run=args.dry_run)
        
        if not success:
            logger.error("❌ Migration failed")
            sys.exit(1)
            
        if not args.dry_run:
            # Verify migration
            if await manager.verify_migration():
                logger.info("🎉 Permission system migration completed successfully!")
                await manager.show_migration_summary()
            else:
                logger.error("❌ Migration verification failed")
                sys.exit(1)
        else:
            logger.info("🔍 Dry run completed - no changes made")
            
    except Exception as e:
        logger.error(f"❌ Migration failed with error: {e}")
        sys.exit(1)
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
