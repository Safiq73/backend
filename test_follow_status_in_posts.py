#!/usr/bin/env python3
"""
Test script for the follow status in posts API enhancement
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000/api/v1"

async def test_posts_with_follow_status():
    """Test the posts API with follow status parameter"""
    print("🚀 Testing Posts API with Follow Status Enhancement")
    print("=" * 60)
    
    # Test data - you'll need to replace these with actual values from your database
    test_user_token = "YOUR_TEST_USER_TOKEN"  # Replace with actual token
    
    headers = {
        "Authorization": f"Bearer {test_user_token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Get posts without follow status (original behavior)
        print("\n1. Testing GET /posts without follow status...")
        try:
            async with session.get(
                f"{API_BASE_URL}/posts?page=1&size=5",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Received {len(data.get('items', []))} posts")
                    
                    # Check that follow_status is not in the response
                    for item in data.get('items', []):
                        if 'follow_status' in item:
                            print(f"⚠️  Warning: follow_status found when not requested")
                        else:
                            print(f"✅ Correct: No follow_status field in post {item.get('id', 'unknown')}")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Get posts with follow status enabled
        print("\n2. Testing GET /posts with include_follow_status=true...")
        try:
            async with session.get(
                f"{API_BASE_URL}/posts?page=1&size=5&include_follow_status=true",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Received {len(data.get('items', []))} posts")
                    
                    # Check that follow_status is in the response
                    for item in data.get('items', []):
                        if 'follow_status' in item:
                            follow_status = item['follow_status']
                            author_id = item.get('author', {}).get('id', 'unknown')
                            print(f"✅ Follow status for author {author_id}: {follow_status}")
                        else:
                            print(f"⚠️  Warning: follow_status missing when requested")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Get posts-only with follow status enabled
        print("\n3. Testing GET /posts/posts-only with include_follow_status=true...")
        try:
            async with session.get(
                f"{API_BASE_URL}/posts/posts-only?page=1&size=5&include_follow_status=true",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Received {len(data.get('items', []))} posts-only")
                    
                    # Check that follow_status is in the response
                    for item in data.get('items', []):
                        if 'follow_status' in item:
                            follow_status = item['follow_status']
                            author_id = item.get('author', {}).get('id', 'unknown')
                            print(f"✅ Follow status for author {author_id}: {follow_status}")
                        else:
                            print(f"⚠️  Warning: follow_status missing when requested")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 4: Test without authentication (should work but no follow status)
        print("\n4. Testing GET /posts without authentication...")
        try:
            async with session.get(
                f"{API_BASE_URL}/posts?page=1&size=5&include_follow_status=true"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Received {len(data.get('items', []))} posts without auth")
                    
                    # Check that follow_status is null/None when not authenticated
                    for item in data.get('items', []):
                        if 'follow_status' in item:
                            follow_status = item['follow_status']
                            if follow_status is None:
                                print(f"✅ Correct: follow_status is null for unauthenticated user")
                            else:
                                print(f"⚠️  Warning: follow_status should be null for unauthenticated user")
                        else:
                            print(f"⚠️  follow_status field missing")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("🏁 Test completed!")
    print("\nTo use this feature in your frontend:")
    print("1. Add ?include_follow_status=true to your API calls")
    print("2. Check the 'follow_status' field in each post object")
    print("3. follow_status will be:")
    print("   - true: Current user follows the post author")
    print("   - false: Current user does not follow the post author") 
    print("   - null: Current user is the author OR user not authenticated")


if __name__ == "__main__":
    print("📝 Follow Status in Posts API Test")
    print("Please update the test_user_token variable with a valid JWT token")
    print("Then run the server and execute this test script")
    print("\nNote: This test requires the backend server to be running on localhost:8000")
    
    # Uncomment the line below to run the actual test
    # asyncio.run(test_posts_with_follow_status())
