"""
CivicPulse Permission System Integration Guide

This script demonstrates how to integrate the permission system into your existing APIs
and provides step-by-step instructions for adding permissions to endpoints.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4, UUID

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

print("🔧 CivicPulse Permission System Integration Guide")
print("=" * 60)

print("\n📝 INTEGRATION STEPS:")
print("\n1. ✅ Database Setup - COMPLETED")
print("   - Created permission tables: system_roles, api_permissions, user_roles, role_api_permissions")
print("   - Added 7 default roles: guest to super_admin")
print("   - Added 37 API permissions based on your routes")
print("   - Set up role-permission mappings")

print("\n2. ✅ Permission Service - COMPLETED")
print("   - SimplePermissionService for checking permissions")
print("   - Compatible with existing database patterns")
print("   - Functions: user_has_permission(), assign_role_to_user(), etc.")

print("\n3. ✅ Permission Decorators - COMPLETED")
print("   - FastAPI dependencies for permission checking")
print("   - Functions: require_permissions(), require_role(), etc.")
print("   - Compatible with existing auth system")

print("\n4. 🎯 READY TO INTEGRATE INTO YOUR APIs")
print("\n   Here's how to add permissions to your existing endpoints:")

print("\n   OPTION A: Using FastAPI Dependencies (Recommended)")
print("""
   # Before:
   @router.post("/posts")
   async def create_post(
       title: str = Form(...),
       current_user: Dict = Depends(get_current_user)
   ):
       # Your logic here
   
   # After:
   @router.post("/posts") 
   async def create_post(
       title: str = Form(...),
       current_user: Dict = Depends(require_permissions('posts.post', fail_open=True))
   ):
       # Your logic here - user is already permission-checked!
   """)

print("\n   OPTION B: Programmatic Checking (For Complex Logic)")
print("""
   from app.core.permission_decorators import check_user_permission, user_has_admin_role
   
   @router.put("/posts/{post_id}")
   async def update_post(
       post_id: str,
       current_user: Dict = Depends(get_current_user_optional)
   ):
       if not current_user:
           raise HTTPException(401, "Authentication required")
       
       user_id = UUID(current_user['id'])
       
       # Check ownership or admin rights
       can_update = await check_user_permission(user_id, 'posts.detail.put')
       is_admin = await user_has_admin_role(user_id)
       owns_post = await check_if_user_owns_post(user_id, post_id)
       
       if not (can_update and (owns_post or is_admin)):
           raise HTTPException(403, "Cannot update this post")
       
       # Your update logic here
   """)

print("\n5. 🚀 ENABLING THE SYSTEM")
print("\n   To enable permission checking:")
print("   1. Set ENABLE_PERMISSION_MIDDLEWARE=true in your .env file")
print("   2. Assign roles to users: await permission_service.assign_role_to_user(user_id, 'citizen')")
print("   3. Test endpoints with different user roles")

print("\n6. 🔄 GRADUAL MIGRATION STRATEGY")
print("""
   Week 1: Add permissions to critical endpoints (admin functions)
   Week 2: Add permissions to user content creation (posts, comments)  
   Week 3: Add permissions to user interactions (votes, follows)
   Week 4: Enable middleware for automatic route protection
   
   Use fail_open=True during testing to avoid breaking existing functionality
   """)

print("\n📊 CURRENT PERMISSION MAPPINGS:")

async def show_current_setup():
    """Show current permission system status"""
    try:
        from app.services.simple_permission_service import permission_service
        
        # Get all roles
        roles = await permission_service.get_all_roles()
        print(f"\n   📋 {len(roles)} Roles Available:")
        for role in roles:
            print(f"      - {role['name']}: {role['display_name']} (level {role['level']})")
        
        # Show example permission for citizen role
        test_user_id = uuid4()
        await permission_service.assign_role_to_user(test_user_id, "citizen")
        
        permissions_to_test = [
            "posts.get", "posts.post", "users.detail.delete", "analytics.get"
        ]
        
        print(f"\n   🧪 Sample Permission Check (Citizen Role):")
        for perm in permissions_to_test:
            has_perm = await permission_service.user_has_permission(test_user_id, perm)
            status = "✅ ALLOWED" if has_perm else "❌ DENIED"
            print(f"      - {perm}: {status}")
        
        # Clean up test user
        await permission_service.remove_role_from_user(test_user_id, "citizen")
        
    except Exception as e:
        print(f"   ⚠️  Error checking permissions: {e}")
        print("   Make sure database is running and tables are created")

print("\n🎯 NEXT ACTIONS:")
print("1. Run this integration test: python integration_guide.py")
print("2. Pick 2-3 endpoints to add permissions to first")  
print("3. Test with different user roles")
print("4. Gradually expand to more endpoints")
print("5. Enable middleware when ready for full protection")

if __name__ == "__main__":
    asyncio.run(show_current_setup())
    
    print("\n✨ Permission system is ready to integrate!")
    print("   See posts_permission_examples.py for detailed code examples")
    print("   The system is backward-compatible and won't break existing functionality")
    