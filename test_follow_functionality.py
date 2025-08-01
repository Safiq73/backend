"""
Test script for follow/unfollow functionality
"""
import asyncio
import aiohttp
import json
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL_1 = "test_user_1@example.com"
TEST_EMAIL_2 = "test_user_2@example.com"
TEST_USERNAME_1 = "test_user_1"
TEST_USERNAME_2 = "test_user_2"
TEST_PASSWORD = "testpassword123"

class FollowTestClient:
    def __init__(self):
        self.user1_token = None
        self.user2_token = None
        self.user1_id = None
        self.user2_id = None
    
    async def register_user(self, email: str, username: str, password: str):
        """Register a new user and return auth token"""
        async with aiohttp.ClientSession() as session:
            # Register user
            register_data = {
                "email": email,
                "username": username,
                "password": password,
                "display_name": f"Test User {username}"
            }
            
            async with session.post(f"{BASE_URL}/auth/register", json=register_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ User {username} registered successfully")
                    return result["data"]["access_token"], result["data"]["user"]["id"]
                else:
                    error = await response.text()
                    print(f"❌ Failed to register user {username}: {error}")
                    return None, None
    
    async def follow_user(self, token: str, user_id_to_follow: str):
        """Follow a user"""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/users/{user_id_to_follow}/follow", headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    print(f"✅ Follow successful: {result['message']}")
                    return result
                else:
                    print(f"❌ Follow failed: {result.get('detail', 'Unknown error')}")
                    return None
    
    async def unfollow_user(self, token: str, user_id_to_unfollow: str):
        """Unfollow a user"""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{BASE_URL}/users/{user_id_to_unfollow}/unfollow", headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    print(f"✅ Unfollow successful: {result['message']}")
                    return result
                else:
                    print(f"❌ Unfollow failed: {result.get('detail', 'Unknown error')}")
                    return None
    
    async def get_followers(self, token: str, user_id: str):
        """Get followers list"""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/users/{user_id}/followers", headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    followers_count = result['data']['total_count']
                    print(f"✅ Followers retrieved: {followers_count} total")
                    return result
                else:
                    print(f"❌ Get followers failed: {result.get('detail', 'Unknown error')}")
                    return None
    
    async def get_following(self, token: str, user_id: str):
        """Get following list"""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/users/{user_id}/following", headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    following_count = result['data']['total_count']
                    print(f"✅ Following retrieved: {following_count} total")
                    return result
                else:
                    print(f"❌ Get following failed: {result.get('detail', 'Unknown error')}")
                    return None
    
    async def get_follow_stats(self, token: str, user_id: str):
        """Get follow statistics"""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/users/{user_id}/follow-stats", headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    stats = result['data']
                    print(f"✅ Follow stats: Followers: {stats['followers_count']}, Following: {stats['following_count']}, Mutual: {stats['mutual_follows_count']}")
                    return result
                else:
                    print(f"❌ Get follow stats failed: {result.get('detail', 'Unknown error')}")
                    return None
    
    async def check_follow_status(self, token: str, user_id: str):
        """Check follow status with another user"""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/users/{user_id}/follow-status", headers=headers) as response:
                result = await response.json()
                if response.status == 200:
                    status = result['data']
                    print(f"✅ Follow status: Following: {status['is_following']}, Followed by: {status['is_followed_by']}, Mutual: {status['mutual']}")
                    return result
                else:
                    print(f"❌ Check follow status failed: {result.get('detail', 'Unknown error')}")
                    return None
    
    async def run_tests(self):
        """Run comprehensive follow/unfollow tests"""
        print("🚀 Starting follow/unfollow functionality tests...")
        print("=" * 60)
        
        # 1. Register two test users
        print("\n📝 Step 1: Registering test users...")
        self.user1_token, self.user1_id = await self.register_user(TEST_EMAIL_1, TEST_USERNAME_1, TEST_PASSWORD)
        self.user2_token, self.user2_id = await self.register_user(TEST_EMAIL_2, TEST_USERNAME_2, TEST_PASSWORD)
        
        if not all([self.user1_token, self.user2_token, self.user1_id, self.user2_id]):
            print("❌ Failed to register users. Exiting...")
            return
        
        # 2. Test initial follow stats (should be 0)
        print("\n📊 Step 2: Checking initial follow stats...")
        await self.get_follow_stats(self.user1_token, self.user1_id)
        await self.get_follow_stats(self.user2_token, self.user2_id)
        
        # 3. Test follow functionality
        print("\n👥 Step 3: Testing follow functionality...")
        print("User 1 follows User 2:")
        follow_result = await self.follow_user(self.user1_token, self.user2_id)
        
        # 4. Check follow status after first follow
        print("\n🔍 Step 4: Checking follow status after first follow...")
        await self.check_follow_status(self.user1_token, self.user2_id)
        await self.check_follow_status(self.user2_token, self.user1_id)
        
        # 5. Check followers/following lists
        print("\n📋 Step 5: Checking followers/following lists...")
        await self.get_followers(self.user2_token, self.user2_id)  # User 2's followers
        await self.get_following(self.user1_token, self.user1_id)  # User 1's following
        
        # 6. Test mutual follow
        print("\n💫 Step 6: Testing mutual follow...")
        print("User 2 follows User 1 back:")
        await self.follow_user(self.user2_token, self.user1_id)
        
        # 7. Check mutual status
        print("\n🤝 Step 7: Checking mutual follow status...")
        await self.check_follow_status(self.user1_token, self.user2_id)
        await self.get_follow_stats(self.user1_token, self.user1_id)
        await self.get_follow_stats(self.user2_token, self.user2_id)
        
        # 8. Test unfollow
        print("\n👋 Step 8: Testing unfollow functionality...")
        print("User 1 unfollows User 2:")
        await self.unfollow_user(self.user1_token, self.user2_id)
        
        # 9. Check status after unfollow
        print("\n📉 Step 9: Checking status after unfollow...")
        await self.check_follow_status(self.user1_token, self.user2_id)
        await self.get_follow_stats(self.user1_token, self.user1_id)
        await self.get_follow_stats(self.user2_token, self.user2_id)
        
        # 10. Test error cases
        print("\n⚠️ Step 10: Testing error cases...")
        print("Testing self-follow (should fail):")
        await self.follow_user(self.user1_token, self.user1_id)
        
        print("Testing double follow (should fail):")
        await self.follow_user(self.user2_token, self.user1_id)  # User 2 still follows User 1
        await self.follow_user(self.user2_token, self.user1_id)  # Try to follow again
        
        print("Testing unfollow non-followed user (should fail):")
        await self.unfollow_user(self.user1_token, self.user2_id)  # User 1 doesn't follow User 2
        
        print("\n✅ Follow/unfollow functionality tests completed!")
        print("=" * 60)

async def main():
    """Main test runner"""
    client = FollowTestClient()
    await client.run_tests()

if __name__ == "__main__":
    print("🧪 Follow/Unfollow API Test Suite")
    print("Make sure your server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Tests cancelled by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
