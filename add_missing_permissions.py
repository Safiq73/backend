"""
Add Missing Permissions Script

This script adds the permissions we're using in our protected endpoints
that aren't yet in the database.
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

async def add_missing_permissions():
    """Add the missing permissions to the database"""
    
    print("🔧 Adding Missing Permissions")
    print("=" * 40)
    
    try:
        from app.db.database import db_manager
        
        # Define the missing permissions
        missing_permissions = [
            {
                'name': 'analytics.clear_cache',
                'description': 'Clear analytics cache - system administration function',
                'resource': 'analytics',
                'action': 'clear_cache'
            },
            {
                'name': 'users.role.put',
                'description': 'Assign roles to users - user management function',
                'resource': 'users', 
                'action': 'role_put'
            }
        ]
        
        async with db_manager.get_connection() as conn:
            for perm in missing_permissions:
                # Check if permission already exists
                existing = await conn.fetchrow(
                    "SELECT id FROM api_permissions WHERE permission_name = $1",
                    perm['name']
                )
                
                if existing:
                    print(f"✅ {perm['name']} already exists")
                    continue
                
                # Add the permission
                await conn.execute("""
                    INSERT INTO api_permissions (permission_name, description, resource_name, action_name)
                    VALUES ($1, $2, $3, $4)
                """, perm['name'], perm['description'], perm['resource'], perm['action'])
                
                print(f"➕ Added permission: {perm['name']}")
            
            # Now assign these permissions to appropriate roles
            print("\n🎯 Assigning permissions to roles:")
            
            # Get role IDs
            roles = await conn.fetch("SELECT id, name FROM system_roles")
            role_map = {role['name']: role['id'] for role in roles}
            
            # Get permission IDs
            permissions = await conn.fetch("SELECT id, permission_name FROM api_permissions")
            perm_map = {perm['permission_name']: perm['id'] for perm in permissions}
            
            # Define role-permission assignments
            assignments = [
                # analytics.clear_cache - only super_admin
                ('super_admin', 'analytics.clear_cache'),
                
                # users.role.put - admin and super_admin
                ('admin', 'users.role.put'),
                ('super_admin', 'users.role.put'),
            ]
            
            for role_name, perm_name in assignments:
                if role_name not in role_map or perm_name not in perm_map:
                    print(f"⚠️  Skipping {role_name} -> {perm_name} (not found)")
                    continue
                
                # Check if assignment already exists
                existing = await conn.fetchrow("""
                    SELECT id FROM role_api_permissions 
                    WHERE role_id = $1 AND permission_id = $2
                """, role_map[role_name], perm_map[perm_name])
                
                if existing:
                    print(f"✅ {role_name} already has {perm_name}")
                    continue
                
                # Create the assignment
                await conn.execute("""
                    INSERT INTO role_api_permissions (role_id, permission_id)
                    VALUES ($1, $2)
                """, role_map[role_name], perm_map[perm_name])
                
                print(f"🔗 {role_name} → {perm_name}")
            
            print("\n✅ All missing permissions added and assigned!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def verify_permissions():
    """Verify that our permissions are now working"""
    
    print("\n" + "=" * 50)
    print("🧪 VERIFYING PERMISSION ASSIGNMENTS")
    print("=" * 50)
    
    try:
        from app.services.simple_permission_service import permission_service
        from app.db.database import db_manager
        
        # Get a super admin user to test
        async with db_manager.get_connection() as conn:
            super_admin_user = await conn.fetchrow("""
                SELECT u.id, u.username
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN system_roles sr ON ur.role_id = sr.id
                WHERE sr.name = 'super_admin'
                LIMIT 1
            """)
            
            if not super_admin_user:
                print("⚠️  No super admin user found for testing")
                return
            
            print(f"🧪 Testing permissions for super admin: {super_admin_user['username']}")
            
            test_permissions = [
                "analytics.get",
                "analytics.clear_cache", 
                "users.role.put",
                "posts.post"
            ]
            
            for perm in test_permissions:
                has_perm = await permission_service.user_has_permission(
                    super_admin_user['id'], perm
                )
                status = "✅ ALLOWED" if has_perm else "❌ DENIED"
                print(f"   - {perm}: {status}")
                
            print("\n🎉 Permission verification complete!")
                
    except Exception as e:
        print(f"❌ Verification error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_missing_permissions())
    asyncio.run(verify_permissions())
