"""
Debug pagination issue
"""
import requests
from uuid import uuid4

BASE_URL = "http://localhost:8000/api/v1"

# Create test users
users = []
for i in range(3):
    user_data = {
        "email": f"pagintest{i}_{uuid4().hex[:8]}@example.com",
        "username": f"pagintest{i}_{uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "display_name": f"Pagination Test User {i+1}"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code == 200:
        data = response.json()["data"]
        users.append({
            "id": data["user"]["id"],
            "token": data["tokens"]["access_token"],
            "username": data["user"]["username"]
        })

print(f"Created {len(users)} users")

# User 0 and User 2 both follow User 1
headers0 = {"Authorization": f"Bearer {users[0]['token']}"}
headers1 = {"Authorization": f"Bearer {users[1]['token']}"}
headers2 = {"Authorization": f"Bearer {users[2]['token']}"}

# Follow operations
follow1 = requests.post(f"{BASE_URL}/users/{users[1]['id']}/follow", headers=headers0)
follow2 = requests.post(f"{BASE_URL}/users/{users[1]['id']}/follow", headers=headers2)

print(f"Follow 1 status: {follow1.status_code}")
print(f"Follow 2 status: {follow2.status_code}")

# Check followers of user 1
followers_response = requests.get(f"{BASE_URL}/users/{users[1]['id']}/followers", headers=headers1)
print(f"Followers response: {followers_response.json()}")

# Test pagination with size=1
paginated_followers = requests.get(f"{BASE_URL}/users/{users[1]['id']}/followers?page=1&size=1", headers=headers1)
print(f"Paginated followers response: {paginated_followers.json()}")
