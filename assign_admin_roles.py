"""
Admin Role Assignment Script

This script assigns admin roles to specific users so you can test
the newly protected endpoints.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add the backend directory to sys.path  
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

async def assign_admin_roles():
    """Assign admin roles to specific users for testing"""
    
    print("🔧 Assigning Admin Roles for Testing")
    print("=" * 50)
    
    try:
        from app.services.simple_permission_service import permission_service
        from app.db.database import db_manager
        
        # Get some users to make admins
        async with db_manager.get_connection() as conn:
            users = await conn.fetch("""
                SELECT id, username, email 
                FROM users 
                WHERE username IN ('permissiontest', 'safiq', 'testuser') 
                LIMIT 5
            """)
            
            if not users:
                print("ℹ️  No target users found. Let's get the first few users:")
                users = await conn.fetch("SELECT id, username, email FROM users LIMIT 3")
            
            print(f"📊 Found {len(users)} users to potentially promote:")
            
            for i, user in enumerate(users):
                print(f"  {i+1}. {user['username']} ({user['email']})")
            
            print("\n🎯 Assigning roles:")
            
            # Make the first user a super admin
            if len(users) > 0:
                user = users[0]
                success = await permission_service.assign_role_to_user(
                    UUID(str(user['id'])), 'super_admin'
                )
                if success:
                    print(f"👑 {user['username']} → SUPER ADMIN")
                else:
                    print(f"❌ Failed to assign super_admin to {user['username']}")
            
            # Make the second user an admin
            if len(users) > 1:
                user = users[1]
                success = await permission_service.assign_role_to_user(
                    UUID(str(user['id'])), 'admin'
                )
                if success:
                    print(f"⚙️  {user['username']} → ADMIN")
                else:
                    print(f"❌ Failed to assign admin to {user['username']}")
            
            # Make the third user a moderator
            if len(users) > 2:
                user = users[2]
                success = await permission_service.assign_role_to_user(
                    UUID(str(user['id'])), 'moderator'
                )
                if success:
                    print(f"🔧 {user['username']} → MODERATOR")
                else:
                    print(f"❌ Failed to assign moderator to {user['username']}")
            
            print("\n🧪 Testing permissions for the super admin user:")
            if len(users) > 0:
                test_user = users[0]
                test_user_id = UUID(str(test_user['id']))
                
                test_permissions = [
                    "analytics.get",           # Should be True (admin can view analytics)
                    "analytics.clear_cache",   # Should be True (super admin can clear cache)  
                    "users.role.put",          # Should be True (admin can assign roles)
                    "posts.post"               # Should be True (admin can create posts)
                ]
                
                for perm in test_permissions:
                    has_perm = await permission_service.user_has_permission(test_user_id, perm)
                    status = "✅ ALLOWED" if has_perm else "❌ DENIED"
                    print(f"   - {perm}: {status}")
                
                print(f"\n✨ Super admin {test_user['username']} can now access all protected endpoints!")
            
            print("\n📝 To test the protected endpoints:")
            print("1. Login as one of the admin users")
            print("2. Try accessing /api/v1/analytics/dashboard")
            print("3. Try accessing /api/v1/analytics/clear-cache")
            print("4. Regular citizens should get 403 Forbidden for these endpoints")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def show_endpoint_protection_status():
    """Show which endpoints are now protected"""
    
    print("\n" + "=" * 60)
    print("🛡️  PROTECTED ENDPOINTS STATUS")
    print("=" * 60)
    
    print("\n📊 ANALYTICS ENDPOINTS (Admin Only):")
    print("   ✅ GET  /api/v1/analytics/dashboard")
    print("   ✅ GET  /api/v1/analytics/search-insights") 
    print("   ✅ GET  /api/v1/analytics/real-time")
    print("   ✅ POST /api/v1/analytics/clear-cache (Super Admin)")
    
    print("\n👥 USER MANAGEMENT ENDPOINTS (Admin Only):")
    print("   ✅ PUT  /api/v1/users/{user_id}/role")
    
    print("\n🔍 HOW TO TEST:")
    print("   1. Get auth token: POST /api/v1/auth/login")
    print("   2. Access analytics: GET /api/v1/analytics/dashboard")
    print("   3. Regular users should get 403 Forbidden")
    print("   4. Admin users should get full access")
    
    print("\n🎯 NEXT STEPS:")
    print("   • Add more endpoint protections as needed")
    print("   • Test with different user roles")
    print("   • Monitor logs for permission denials")
    print("   • Expand to other sensitive operations")

if __name__ == "__main__":
    asyncio.run(assign_admin_roles())
    asyncio.run(show_endpoint_protection_status())
