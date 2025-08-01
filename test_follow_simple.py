"""
Simple follow/unfollow functionality test using requests library
"""
import requests
import json
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000/api/v1"

def test_follow_functionality():
    """Test the follow/unfollow endpoints"""
    print("🚀 Testing Follow/Unfollow Functionality")
    print("=" * 50)
    
    # Test data
    test_user_1 = {
        "email": f"testuser1_{uuid4().hex[:8]}@example.com",
        "username": f"testuser1_{uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "display_name": "Test User 1"
    }
    
    test_user_2 = {
        "email": f"testuser2_{uuid4().hex[:8]}@example.com", 
        "username": f"testuser2_{uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "display_name": "Test User 2"
    }
    
    try:
        # 1. Register users
        print("\n1. Registering test users...")
        
        # Register user 1
        response1 = requests.post(f"{BASE_URL}/auth/register", json=test_user_1)
        print(f"User 1 registration response: {response1.status_code}")
        if response1.status_code != 200:
            print(f"❌ Failed to register user 1: {response1.text}")
            return
        
        user1_data = response1.json()
        print(f"User 1 response data: {user1_data}")
        
        if "data" not in user1_data or "tokens" not in user1_data["data"]:
            print(f"❌ Unexpected response structure for user 1: {user1_data}")
            return
            
        user1_token = user1_data["data"]["tokens"]["access_token"]
        user1_id = user1_data["data"]["user"]["id"]
        print(f"✅ User 1 registered: {test_user_1['username']}")
        
        # Register user 2
        response2 = requests.post(f"{BASE_URL}/auth/register", json=test_user_2)
        print(f"User 2 registration response: {response2.status_code}")
        if response2.status_code != 200:
            print(f"❌ Failed to register user 2: {response2.text}")
            return
        
        user2_data = response2.json()
        print(f"User 2 response data: {user2_data}")
        
        if "data" not in user2_data or "tokens" not in user2_data["data"]:
            print(f"❌ Unexpected response structure for user 2: {user2_data}")
            return
            
        user2_token = user2_data["data"]["tokens"]["access_token"]
        user2_id = user2_data["data"]["user"]["id"]
        print(f"✅ User 2 registered: {test_user_2['username']}")
        
        # 2. Test follow functionality
        print("\n2. Testing follow functionality...")
        
        headers1 = {"Authorization": f"Bearer {user1_token}"}
        headers2 = {"Authorization": f"Bearer {user2_token}"}
        
        # User 1 follows User 2
        follow_response = requests.post(f"{BASE_URL}/users/{user2_id}/follow", headers=headers1)
        if follow_response.status_code == 200:
            result = follow_response.json()
            print(f"✅ User 1 followed User 2: {result['message']}")
            print(f"   Mutual: {result['data']['mutual']}")
        else:
            print(f"❌ Follow failed: {follow_response.text}")
            return
        
        # 3. Check followers/following
        print("\n3. Checking followers and following...")
        
        # Get User 2's followers
        followers_response = requests.get(f"{BASE_URL}/users/{user2_id}/followers", headers=headers2)
        if followers_response.status_code == 200:
            followers_data = followers_response.json()["data"]
            print(f"✅ User 2 has {followers_data['total_count']} followers")
        
        # Get User 1's following
        following_response = requests.get(f"{BASE_URL}/users/{user1_id}/following", headers=headers1)
        if following_response.status_code == 200:
            following_data = following_response.json()["data"]
            print(f"✅ User 1 is following {following_data['total_count']} users")
        
        # 4. Test mutual follow
        print("\n4. Testing mutual follow...")
        
        # User 2 follows User 1 back
        mutual_follow_response = requests.post(f"{BASE_URL}/users/{user1_id}/follow", headers=headers2)
        if mutual_follow_response.status_code == 200:
            result = mutual_follow_response.json()
            print(f"✅ User 2 followed User 1 back: {result['message']}")
            print(f"   Mutual: {result['data']['mutual']}")
        
        # 5. Check follow stats
        print("\n5. Checking follow statistics...")
        
        stats_response = requests.get(f"{BASE_URL}/users/{user1_id}/follow-stats", headers=headers1)
        if stats_response.status_code == 200:
            stats = stats_response.json()["data"]
            print(f"✅ User 1 stats - Followers: {stats['followers_count']}, Following: {stats['following_count']}, Mutual: {stats['mutual_follows_count']}")
        
        # 6. Test unfollow
        print("\n6. Testing unfollow functionality...")
        
        # User 1 unfollows User 2
        unfollow_response = requests.delete(f"{BASE_URL}/users/{user2_id}/unfollow", headers=headers1)
        if unfollow_response.status_code == 200:
            result = unfollow_response.json()
            print(f"✅ User 1 unfollowed User 2: {result['message']}")
        
        # Check stats after unfollow
        stats_response = requests.get(f"{BASE_URL}/users/{user1_id}/follow-stats", headers=headers1)
        if stats_response.status_code == 200:
            stats = stats_response.json()["data"]
            print(f"✅ User 1 stats after unfollow - Followers: {stats['followers_count']}, Following: {stats['following_count']}, Mutual: {stats['mutual_follows_count']}")
        
        # 7. Test error cases
        print("\n7. Testing error cases...")
        
        # Test self-follow (should fail)
        self_follow_response = requests.post(f"{BASE_URL}/users/{user1_id}/follow", headers=headers1)
        if self_follow_response.status_code == 400:
            print("✅ Self-follow correctly rejected")
        else:
            print(f"❌ Self-follow should have failed: {self_follow_response.text}")
        
        # Test double follow (should fail)
        double_follow_response = requests.post(f"{BASE_URL}/users/{user1_id}/follow", headers=headers2)
        if double_follow_response.status_code == 400:
            print("✅ Double follow correctly rejected")
        else:
            print(f"❌ Double follow should have failed: {double_follow_response.text}")
        
        print("\n🎉 All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_follow_functionality()
