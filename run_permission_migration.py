"""
Permission System Database Migration Runner

This script handles the complete setup and migration of the permission system,
including database schema updates and initial data population.
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from typing import Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PermissionMigrationRunner:
    """Handles permission system database migrations"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:postgres@localhost:5432/civicpulse"
        )
        self.migration_dir = Path(__file__).parent / "app" / "db"
    
    async def run_migration(self):
        """Run the complete permission system migration"""
        logger.info("Starting permission system migration...")
        
        try:
            # Connect to database
            conn = await asyncpg.connect(self.database_url)
            logger.info("Connected to database successfully")
            
            # Check if main schema exists
            await self._ensure_main_schema(conn)
            
            # Run permission system migration
            await self._run_permission_migration(conn)
            
            # Verify migration
            await self._verify_migration(conn)
            
            logger.info("Permission system migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            await conn.close()
    
    async def _ensure_main_schema(self, conn):
        """Ensure main database schema exists"""
        logger.info("Checking main database schema...")
        
        schema_file = self.migration_dir / "schema.sql"
        if not schema_file.exists():
            raise FileNotFoundError(f"Main schema file not found: {schema_file}")
        
        # Check if users table exists (indicator of main schema)
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """)
        
        if not result:
            logger.info("Main schema not found, applying main schema...")
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            await conn.execute(schema_sql)
            logger.info("Main schema applied successfully")
        else:
            logger.info("Main schema already exists")
    
    async def _run_permission_migration(self, conn):
        """Run the permission system migration"""
        logger.info("Applying permission system migration...")
        
        migration_file = self.migration_dir / "permissions_migration.sql"
        if not migration_file.exists():
            raise FileNotFoundError(f"Permission migration file not found: {migration_file}")
        
        # Check if permission tables already exist
        tables_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name IN ('system_roles', 'api_permissions', 'user_roles', 'role_api_permissions')
            )
        """)
        
        if tables_exist:
            logger.info("Permission tables already exist, checking for updates...")
            # In production, you might want more sophisticated migration tracking
        
        # Read and execute migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        try:
            # Split the SQL file into individual statements
            # Remove empty lines and comments
            statements = []
            current_statement = ""
            in_transaction = False
            
            for line in migration_sql.split('\n'):
                line = line.strip()
                
                # Skip empty lines and pure comment lines
                if not line or line.startswith('--'):
                    continue
                
                # Track transaction boundaries
                if line.upper().startswith('BEGIN'):
                    in_transaction = True
                    current_statement += line + '\n'
                    continue
                
                if line.upper().startswith('COMMIT'):
                    current_statement += line + '\n'
                    statements.append(current_statement.strip())
                    current_statement = ""
                    in_transaction = False
                    continue
                
                # Add line to current statement
                current_statement += line + '\n'
                
                # If not in transaction and line ends with semicolon, it's a complete statement
                if not in_transaction and line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # Add any remaining statement
            if current_statement.strip():
                statements.append(current_statement.strip())
            
            # Execute each statement
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        logger.info(f"Executing statement {i+1}/{len(statements)}")
                        await conn.execute(statement)
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                            logger.info(f"Skipping statement {i+1} (already exists): {str(e)[:100]}...")
                        else:
                            logger.error(f"Error in statement {i+1}: {e}")
                            logger.error(f"Statement: {statement[:200]}...")
                            raise
            
            logger.info("Permission migration applied successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Permission tables already exist, skipping creation")
            else:
                logger.error(f"Migration error: {e}")
                raise
    
    async def _verify_migration(self, conn):
        """Verify that the migration was successful"""
        logger.info("Verifying migration...")
        
        # Check that all required tables exist
        required_tables = [
            'system_roles', 
            'api_permissions', 
            'user_roles', 
            'role_api_permissions'
        ]
        
        for table in required_tables:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            
            if not exists:
                raise Exception(f"Required table '{table}' was not created")
            
            logger.info(f"✓ Table '{table}' exists")
        
        # Check that default roles were created
        role_count = await conn.fetchval("SELECT COUNT(*) FROM system_roles")
        if role_count == 0:
            raise Exception("No system roles were created")
        
        logger.info(f"✓ {role_count} system roles created")
        
        # Check that API permissions were created
        permission_count = await conn.fetchval("SELECT COUNT(*) FROM api_permissions")
        if permission_count == 0:
            raise Exception("No API permissions were created")
        
        logger.info(f"✓ {permission_count} API permissions created")
        
        # Check that role-permission mappings exist
        mapping_count = await conn.fetchval("SELECT COUNT(*) FROM role_api_permissions")
        if mapping_count == 0:
            raise Exception("No role-permission mappings were created")
        
        logger.info(f"✓ {mapping_count} role-permission mappings created")
        
        logger.info("Migration verification completed successfully")
    
    async def assign_default_role_to_existing_users(self, default_role: str = "citizen"):
        """Assign default role to existing users who don't have roles"""
        logger.info(f"Assigning default role '{default_role}' to existing users...")
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Get the citizen role ID
            role_id = await conn.fetchval(
                "SELECT id FROM system_roles WHERE name = $1", default_role
            )
            
            if not role_id:
                raise Exception(f"Role '{default_role}' not found")
            
            # Find users without roles
            users_without_roles = await conn.fetch("""
                SELECT u.id FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                WHERE ur.user_id IS NULL
            """)
            
            # Assign default role to users without roles
            assigned_count = 0
            for user in users_without_roles:
                await conn.execute("""
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                """, user['id'], role_id)
                assigned_count += 1
            
            logger.info(f"Assigned default role to {assigned_count} existing users")
            
        except Exception as e:
            logger.error(f"Error assigning default roles: {e}")
            raise
        finally:
            await conn.close()
    
    async def create_admin_user(
        self, 
        username: str, 
        email: str, 
        password: str,
        role: str = "admin"
    ):
        """Create an admin user with specified role"""
        logger.info(f"Creating admin user '{username}' with role '{role}'...")
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Hash the password (you'll need to import your password hashing function)
            from app.core.security import get_password_hash
            hashed_password = get_password_hash(password)
            
            # Create user
            user_id = await conn.fetchval("""
                INSERT INTO users (username, email, password_hash, is_active, is_verified)
                VALUES ($1, $2, $3, true, true)
                RETURNING id
                ON CONFLICT (email) DO UPDATE SET 
                    username = EXCLUDED.username,
                    password_hash = EXCLUDED.password_hash
                RETURNING id
            """, username, email, hashed_password)
            
            # Get role ID
            role_id = await conn.fetchval(
                "SELECT id FROM system_roles WHERE name = $1", role
            )
            
            if not role_id:
                raise Exception(f"Role '{role}' not found")
            
            # Assign role
            await conn.execute("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, role_id) DO NOTHING
            """, user_id, role_id)
            
            logger.info(f"Admin user '{username}' created successfully with role '{role}'")
            
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            raise
        finally:
            await conn.close()

async def main():
    """Main migration runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run CivicPulse permission system migration')
    parser.add_argument('--database-url', help='Database URL')
    parser.add_argument('--assign-default-roles', action='store_true', 
                       help='Assign default roles to existing users')
    parser.add_argument('--create-admin', action='store_true',
                       help='Create admin user')
    parser.add_argument('--admin-username', default='admin',
                       help='Admin username')
    parser.add_argument('--admin-email', default='admin@civicpulse.local',
                       help='Admin email')
    parser.add_argument('--admin-password', default='admin123',
                       help='Admin password')
    
    args = parser.parse_args()
    
    runner = PermissionMigrationRunner(args.database_url)
    
    try:
        # Run main migration
        await runner.run_migration()
        
        # Assign default roles if requested
        if args.assign_default_roles:
            await runner.assign_default_role_to_existing_users()
        
        # Create admin user if requested
        if args.create_admin:
            await runner.create_admin_user(
                args.admin_username,
                args.admin_email,
                args.admin_password
            )
        
        print("\n✅ Permission system setup completed successfully!")
        print("\nNext steps:")
        print("1. Update your FastAPI app to use the new permission middleware")
        print("2. Test the permission system with different user roles")
        print("3. Review and adjust role permissions as needed")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
