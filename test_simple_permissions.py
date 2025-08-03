"""
Test the Simple Permission Service

This script tests the basic functionality of the permission system
using the existing CivicPulse database patterns.
"""

import asyncio
import sys
import logging
from pathlib import Path
import uuid

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.services.simple_permission_service import permission_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_permission_system():
    """Test the permission system functionality"""
    
    print("\n🧪 Testing Simple Permission System")
    print("=" * 50)
    
    try:
        # Test 1: Get all available roles
        print("\n1. Testing role retrieval...")
        roles = await permission_service.get_all_roles()
        print(f"✓ Found {len(roles)} system roles:")
        for role in roles:
            print(f"  - {role['name']}: {role['display_name']} (level {role['level']})")
        
        # Test 2: Use an existing user from the database
        print("\n2. Getting an existing user for testing...")
        
        # Get an existing user UUID
        from app.db.database import db_manager
        async with db_manager.get_connection() as conn:
            user_result = await conn.fetchrow("SELECT id, username FROM users LIMIT 1")
            if not user_result:
                print("❌ No users found in database. Please create a user first.")
                return
            
            test_user_id = user_result['id']
            test_username = user_result['username']
            print(f"✓ Using existing user: {test_username} ({test_user_id})")
        
        print("\n3. Testing role assignment...")
        success = await permission_service.assign_role_to_user(test_user_id, "citizen")
        if success:
            print(f"✓ Successfully assigned 'citizen' role to user {test_username}")
        else:
            print(f"❌ Failed to assign role to user")
            return
        
        # Test 3: Check user roles
        print("\n4. Testing user role retrieval...")
        user_roles = await permission_service.get_user_roles(test_user_id)
        print(f"✓ User has {len(user_roles)} roles:")
        for role in user_roles:
            print(f"  - {role['name']}: {role['display_name']}")
        
        # Test 4: Test permission checking
        print("\n5. Testing permission checking...")
        
        # First, need to assign some permissions to the citizen role
        # For now, let's just test the permission checking mechanism
        has_posts_get = await permission_service.user_has_permission(test_user_id, "posts.get")
        has_admin_delete = await permission_service.user_has_permission(test_user_id, "users.detail.delete")
        
        print(f"✓ User can view posts: {has_posts_get}")
        print(f"✓ User can delete users (admin): {has_admin_delete}")
        
        # Test 5: Test route permission name lookup
        print("\n6. Testing route permission lookup...")
        permission_name = await permission_service.get_route_permission_name("/api/v1/posts", "GET")
        print(f"✓ Permission for GET /api/v1/posts: {permission_name}")
        
        # Test 6: Remove role
        print("\n7. Testing role removal...")
        removed = await permission_service.remove_role_from_user(test_user_id, "citizen")
        if removed:
            print(f"✓ Successfully removed 'citizen' role from user {test_username}")
        else:
            print(f"❌ Failed to remove role from user")
        
        # Verify removal
        user_roles_after = await permission_service.get_user_roles(test_user_id)
        print(f"✓ User now has {len(user_roles_after)} roles")
        
        print("\n🎉 Permission system test completed successfully!")
        print("\nNext steps:")
        print("1. Set up role-permission mappings")
        print("2. Integrate with authentication middleware")
        print("3. Add permission decorators to API endpoints")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error(f"Permission system test error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_permission_system())
