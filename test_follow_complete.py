"""
Comprehensive test for follow/unfollow API endpoints
"""
import requests
import json
from uuid import uuid4
from config.api_config import API_BASE_URL

BASE_URL = API_BASE_URL

def test_comprehensive_follow_functionality():
    """Test comprehensive follow/unfollow scenarios"""
    print("🧪 Comprehensive Follow/Unfollow API Test")
    print("=" * 50)
    
    # Create test users
    users = []
    for i in range(3):
        user_data = {
            "email": f"testuser{i}_{uuid4().hex[:8]}@example.com",
            "username": f"testuser{i}_{uuid4().hex[:8]}",
            "password": "TestPassword123!",
            "display_name": f"Test User {i+1}"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        if response.status_code == 200:
            data = response.json()["data"]
            users.append({
                "id": data["user"]["id"],
                "token": data["tokens"]["access_token"],
                "username": data["user"]["username"]
            })
            print(f"✅ Registered {user_data['username']}")
        else:
            print(f"❌ Failed to register user {i+1}: {response.text}")
            return False
    
    if len(users) < 3:
        print("❌ Failed to register required users")
        return False
    
    # Test scenarios
    try:
        # 1. Test basic follow
        print("\n1. Testing basic follow...")
        headers1 = {"Authorization": f"Bearer {users[0]['token']}"}
        follow_response = requests.post(f"{BASE_URL}/users/{users[1]['id']}/follow", headers=headers1)
        assert follow_response.status_code == 200
        result = follow_response.json()
        assert result["data"]["mutual"] == False
        print("✅ Basic follow works")
        
        # 2. Test follow status
        print("\n2. Testing follow status...")
        status_response = requests.get(f"{BASE_URL}/users/{users[1]['id']}/follow-status", headers=headers1)
        assert status_response.status_code == 200
        status = status_response.json()["data"]
        assert status["is_following"] == True
        assert status["is_followed_by"] == False
        assert status["mutual"] == False
        print("✅ Follow status correct")
        
        # 3. Test mutual follow
        print("\n3. Testing mutual follow...")
        headers2 = {"Authorization": f"Bearer {users[1]['token']}"}
        mutual_follow = requests.post(f"{BASE_URL}/users/{users[0]['id']}/follow", headers=headers2)
        assert mutual_follow.status_code == 200
        mutual_result = mutual_follow.json()
        assert mutual_result["data"]["mutual"] == True
        print("✅ Mutual follow detected")
        
        # 4. Test followers/following lists
        print("\n4. Testing followers/following lists...")
        followers_response = requests.get(f"{BASE_URL}/users/{users[0]['id']}/followers", headers=headers1)
        assert followers_response.status_code == 200
        followers_data = followers_response.json()["data"]
        assert followers_data["total_count"] == 1
        assert followers_data["followers"][0]["mutual"] == True
        
        following_response = requests.get(f"{BASE_URL}/users/{users[0]['id']}/following", headers=headers1)
        assert following_response.status_code == 200
        following_data = following_response.json()["data"]
        assert following_data["total_count"] == 1
        assert following_data["following"][0]["mutual"] == True
        print("✅ Followers/following lists correct")
        
        # 5. Test follow stats
        print("\n5. Testing follow statistics...")
        stats_response = requests.get(f"{BASE_URL}/users/{users[0]['id']}/follow-stats", headers=headers1)
        assert stats_response.status_code == 200
        stats = stats_response.json()["data"]
        assert stats["followers_count"] == 1
        assert stats["following_count"] == 1
        assert stats["mutual_follows_count"] == 1
        print("✅ Follow statistics correct")
        
        # 6. Test unfollow breaks mutual
        print("\n6. Testing unfollow breaks mutual relationship...")
        unfollow_response = requests.delete(f"{BASE_URL}/users/{users[1]['id']}/unfollow", headers=headers1)
        assert unfollow_response.status_code == 200
        
        # Check that user2 still follows user1 but it's no longer mutual
        user2_following = requests.get(f"{BASE_URL}/users/{users[1]['id']}/following", headers=headers2)
        assert user2_following.status_code == 200
        user2_following_data = user2_following.json()["data"]
        assert user2_following_data["total_count"] == 1
        assert user2_following_data["following"][0]["mutual"] == False
        print("✅ Unfollow correctly breaks mutual relationship")
        
        # 7. Test pagination
        print("\n7. Testing pagination...")
        # Make user3 follow user1
        headers3 = {"Authorization": f"Bearer {users[2]['token']}"}
        requests.post(f"{BASE_URL}/users/{users[1]['id']}/follow", headers=headers3)
        
        # Test pagination with size=1
        paginated_followers = requests.get(f"{BASE_URL}/users/{users[1]['id']}/followers?page=1&size=1", headers=headers2)
        assert paginated_followers.status_code == 200
        paginated_data = paginated_followers.json()["data"]
        assert len(paginated_data["followers"]) == 1
        assert paginated_data["total_count"] == 2
        assert paginated_data["has_next"] == True
        print("✅ Pagination works correctly")
        
        # 8. Test error cases
        print("\n8. Testing error cases...")
        
        # Invalid user ID
        invalid_follow = requests.post(f"{BASE_URL}/users/invalid-uuid/follow", headers=headers1)
        assert invalid_follow.status_code == 422  # Validation error
        
        # Non-existent user
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        nonexistent_follow = requests.post(f"{BASE_URL}/users/{fake_uuid}/follow", headers=headers1)
        assert nonexistent_follow.status_code == 404 or nonexistent_follow.status_code == 400
        
        # Unfollow non-followed user
        unfollow_nonexistent = requests.delete(f"{BASE_URL}/users/{users[0]['id']}/unfollow", headers=headers3)
        assert unfollow_nonexistent.status_code == 400
        
        print("✅ Error cases handled correctly")
        
        print("\n🎉 All comprehensive tests passed!")
        return True
        
    except AssertionError as e:
        print(f"❌ Test assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_comprehensive_follow_functionality()
    if success:
        print("\n✅ All tests PASSED - Follow/Unfollow functionality is working correctly!")
    else:
        print("\n❌ Some tests FAILED - Please check the implementation")
