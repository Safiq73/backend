"""
Debug follow status response
"""
import requests
from uuid import uuid4

BASE_URL = "http://localhost:8000/api/v1"

# Create two test users
user1_data = {
    "email": f"debuguser1_{uuid4().hex[:8]}@example.com",
    "username": f"debuguser1_{uuid4().hex[:8]}",
    "password": "TestPassword123!",
    "display_name": "Debug User 1"
}

user2_data = {
    "email": f"debuguser2_{uuid4().hex[:8]}@example.com",
    "username": f"debuguser2_{uuid4().hex[:8]}",
    "password": "TestPassword123!",
    "display_name": "Debug User 2"
}

# Register users
response1 = requests.post(f"{BASE_URL}/auth/register", json=user1_data)
response2 = requests.post(f"{BASE_URL}/auth/register", json=user2_data)

user1 = response1.json()["data"]
user2 = response2.json()["data"]

headers1 = {"Authorization": f"Bearer {user1['tokens']['access_token']}"}

# Follow user2
follow_response = requests.post(f"{BASE_URL}/users/{user2['user']['id']}/follow", headers=headers1)
print(f"Follow response: {follow_response.json()}")

# Check follow status
status_response = requests.get(f"{BASE_URL}/users/{user2['user']['id']}/follow-status", headers=headers1)
print(f"Status code: {status_response.status_code}")
print(f"Status response: {status_response.json()}")

if status_response.status_code != 200:
    print(f"Error response text: {status_response.text}")
