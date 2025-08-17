"""
Add Missing Permissions - Fixed Version

This script adds the missing permissions using the correct table structure.
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

async def add_missing_permissions_fixed():
    """Add the missing permissions using correct column names"""
    
    print("🔧 Adding Missing Permissions (Fixed)")
    print("=" * 45)
    
    try:
        from app.db.database import db_manager
        
        # Define the missing permissions with correct structure
        missing_permissions = [
            {
                'route_path': '/api/v1/analytics/clear-cache',
                'method': 'POST',
                'permission_name': 'analytics.clear_cache',
                'description': 'Clear analytics cache - system administration function',
                'category': 'analytics'
            },
            {
                'route_path': '/api/v1/users/{user_id}/role',
                'method': 'PUT', 
                'permission_name': 'users.role.put',
                'description': 'Assign roles to users - user management function',
                'category': 'user_management'
            }
        ]
        
        async with db_manager.get_connection() as conn:
            for perm in missing_permissions:
                # Check if permission already exists
                existing = await conn.fetchrow(
                    "SELECT id FROM api_permissions WHERE permission_name = $1",
                    perm['permission_name']
                )
                
                if existing:
                    print(f"✅ {perm['permission_name']} already exists")
                    continue
                
                # Add the permission with correct columns
                await conn.execute("""
                    INSERT INTO api_permissions (route_path, method, permission_name, description, category)
                    VALUES ($1, $2, $3, $4, $5)
                """, perm['route_path'], perm['method'], perm['permission_name'], 
                     perm['description'], perm['category'])
                
                print(f"➕ Added permission: {perm['permission_name']}")
            
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

if __name__ == "__main__":
    asyncio.run(add_missing_permissions_fixed())
