"""
Comprehensive test script for follow/unfollow functionality
"""
import asyncio
import json
import aiohttp
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test user credentials
TEST_USERS = [
    {
        "username": f"testuser1_{uuid4().hex[:8]}",
        "email": f"testuser1_{uuid4().hex[:8]}@example.com",
        "password": "TestPass123!",
        "display_name": "Test User 1"
    },
    {
        "username": f"testuser2_{uuid4().hex[:8]}",
        "email": f"testuser2_{uuid4().hex[:8]}@example.com",
        "password": "TestPass123!",
        "display_name": "Test User 2"
    },
    {
        "username": f"testuser3_{uuid4().hex[:8]}",
        "email": f"testuser3_{uuid4().hex[:8]}@example.com",
        "password": "TestPass123!",
        "display_name": "Test User 3"
    }
]

async def create_user(session, user_data):
    """Create a new user"""
    async with session.post(f"{API_BASE}/auth/register", json=user_data) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✅ Created user: {user_data['username']}")
            return result
        else:
            error = await response.text()
            print(f"❌ Failed to create user {user_data['username']}: {error}")
            return None

async def login_user(session, username, password):
    """Login user and return token"""
    login_data = {"username": username, "password": password}
    async with session.post(f"{API_BASE}/auth/login", json=login_data) as response:
        if response.status == 200:
            result = await response.json()
            token = result["data"]["access_token"]
            user_id = result["data"]["user"]["id"]
            print(f"✅ Logged in user: {username}")
            return token, user_id
        else:
            error = await response.text()
            print(f"❌ Failed to login user {username}: {error}")
            return None, None

async def follow_user(session, token, user_id_to_follow):
    """Follow a user"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(f"{API_BASE}/users/{user_id_to_follow}/follow", headers=headers) as response:
        result = await response.json()
        if response.status == 200:
            mutual = result["data"]["mutual"]
            print(f"✅ Follow successful - Mutual: {mutual}")
            return result
        else:
            print(f"❌ Follow failed: {result}")
            return None

async def unfollow_user(session, token, user_id_to_unfollow):
    """Unfollow a user"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.delete(f"{API_BASE}/users/{user_id_to_unfollow}/unfollow", headers=headers) as response:
        result = await response.json()
        if response.status == 200:
            print(f"✅ Unfollow successful")
            return result
        else:
            print(f"❌ Unfollow failed: {result}")
            return None

async def get_followers(session, token, user_id, page=1, size=10):
    """Get user followers"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{API_BASE}/users/{user_id}/followers?page={page}&size={size}", headers=headers) as response:
        result = await response.json()
        if response.status == 200:
            followers = result["data"]["followers"]
            total = result["data"]["total_count"]
            print(f"✅ Got {len(followers)} followers (total: {total})")
            return result
        else:
            print(f"❌ Get followers failed: {result}")
            return None

async def get_following(session, token, user_id, page=1, size=10):
    """Get user following"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{API_BASE}/users/{user_id}/following?page={page}&size={size}", headers=headers) as response:
        result = await response.json()
        if response.status == 200:
            following = result["data"]["following"]
            total = result["data"]["total_count"]
            print(f"✅ Got {len(following)} following (total: {total})")
            return result
        else:
            print(f"❌ Get following failed: {result}")
            return None

async def get_follow_stats(session, token, user_id):
    """Get user follow stats"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{API_BASE}/users/{user_id}/follow-stats", headers=headers) as response:
        result = await response.json()
        if response.status == 200:
            stats = result["data"]
            print(f"✅ Follow stats - Followers: {stats['followers_count']}, Following: {stats['following_count']}, Mutual: {stats['mutual_follows_count']}")
            return result
        else:
            print(f"❌ Get follow stats failed: {result}")
            return None

async def check_follow_status(session, token, user_id):
    """Check follow status with another user"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{API_BASE}/users/{user_id}/follow-status", headers=headers) as response:
        result = await response.json()
        if response.status == 200:
            status = result["data"]
            print(f"✅ Follow status - Following: {status['is_following']}, Followed by: {status['is_followed_by']}, Mutual: {status['mutual']}")
            return result
        else:
            print(f"❌ Check follow status failed: {result}")
            return None

async def test_self_follow_prevention(session, token, user_id):
    """Test that users cannot follow themselves"""
    print("\n🧪 Testing self-follow prevention...")
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(f"{API_BASE}/users/{user_id}/follow", headers=headers) as response:
        result = await response.json()
        if response.status == 400 and "cannot follow themselves" in result.get("detail", ""):
            print("✅ Self-follow prevention works correctly")
            return True
        else:
            print(f"❌ Self-follow prevention failed: {result}")
            return False

async def main():
    """Main test function"""
    print("🚀 Starting comprehensive follow/unfollow functionality tests...\n")
    
    async with aiohttp.ClientSession() as session:
        # Create test users
        print("📝 Creating test users...")
        users = []
        for user_data in TEST_USERS:
            result = await create_user(session, user_data)
            if result:
                users.append({
                    "data": user_data,
                    "response": result
                })
        
        if len(users) < 3:
            print("❌ Failed to create enough test users")
            return
        
        print(f"\n✅ Created {len(users)} test users")
        
        # Login users
        print("\n🔐 Logging in users...")
        tokens = []
        user_ids = []
        for user in users:
            token, user_id = await login_user(session, user["data"]["username"], user["data"]["password"])
            if token and user_id:
                tokens.append(token)
                user_ids.append(user_id)
        
        if len(tokens) < 3:
            print("❌ Failed to login enough users")
            return
        
        print(f"\n✅ Logged in {len(tokens)} users")
        
        # Test self-follow prevention
        await test_self_follow_prevention(session, tokens[0], user_ids[0])
        
        # Test basic follow functionality
        print("\n🔗 Testing basic follow functionality...")
        
        # User 1 follows User 2
        print(f"\n👤 User 1 follows User 2...")
        await follow_user(session, tokens[0], user_ids[1])
        
        # Check follow stats for User 1
        print(f"\n📊 Checking User 1 follow stats...")
        await get_follow_stats(session, tokens[0], user_ids[0])
        
        # Check follow stats for User 2
        print(f"\n📊 Checking User 2 follow stats...")
        await get_follow_stats(session, tokens[1], user_ids[1])
        
        # Test mutual follow
        print(f"\n🤝 Testing mutual follow...")
        print(f"👤 User 2 follows User 1...")
        await follow_user(session, tokens[1], user_ids[0])
        
        # Check follow status between User 1 and User 2
        print(f"\n🔍 Checking follow status between User 1 and User 2...")
        await check_follow_status(session, tokens[0], user_ids[1])
        
        # Test followers/following lists
        print(f"\n📋 Getting User 1's followers...")
        await get_followers(session, tokens[0], user_ids[0])
        
        print(f"\n📋 Getting User 1's following...")
        await get_following(session, tokens[0], user_ids[0])
        
        # Test unfollow
        print(f"\n💔 Testing unfollow functionality...")
        print(f"👤 User 1 unfollows User 2...")
        await unfollow_user(session, tokens[0], user_ids[1])
        
        # Check updated stats
        print(f"\n📊 Checking updated follow stats after unfollow...")
        await get_follow_stats(session, tokens[0], user_ids[0])
        await get_follow_stats(session, tokens[1], user_ids[1])
        
        # Test complex scenario: User 3 follows both User 1 and User 2
        print(f"\n🕸️ Testing complex follow scenario...")
        print(f"👤 User 3 follows User 1...")
        await follow_user(session, tokens[2], user_ids[0])
        
        print(f"👤 User 3 follows User 2...")
        await follow_user(session, tokens[2], user_ids[1])
        
        # Final stats check
        print(f"\n📊 Final follow stats check...")
        for i, (token, user_id) in enumerate(zip(tokens, user_ids), 1):
            print(f"\nUser {i} stats:")
            await get_follow_stats(session, token, user_id)
    
    print("\n🎉 Follow/unfollow functionality tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
