"""
Test script for S3 upload functionality in CivicPulse post creation API
This script demonstrates how to use the updated /posts endpoint with file uploads
"""
import requests
import json
from pathlib import Path

# Configuration
from config.api_config import API_BASE_URL

BASE_URL = API_BASE_URL
TEST_FILES_DIR = Path(__file__).parent / "test_files"

def test_create_post_with_media():
    """Test creating a post with media uploads"""
    
    # First, login to get authentication token (adjust based on your auth setup)
    login_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    
    # If authentication is enabled, login first
    # auth_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    # token = auth_response.json()["data"]["tokens"]["access_token"]
    # headers = {"Authorization": f"Bearer {token}"}
    
    # For testing without auth (when enable_authentication: false)
    headers = {}
    
    # Prepare form data
    form_data = {
        "title": "Test Post with Media Upload",
        "content": "This is a test post created with the new media upload functionality. It demonstrates uploading images and videos to S3.",
        "post_type": "issue",
        "assignee": "some-representative-uuid",  # Replace with actual representative UUID
        "location": "Test Location",
        "latitude": 28.6139,  # New Delhi coordinates
        "longitude": 77.2090,
        "tags": json.dumps(["test", "media", "s3"])  # JSON string of tags array
    }
    
    # Prepare files for upload
    files = []
    
    # Test with sample files (create these for testing)
    test_image_path = TEST_FILES_DIR / "test_image.jpg"
    test_video_path = TEST_FILES_DIR / "test_video.mp4"
    
    # Only add files if they exist
    if test_image_path.exists():
        files.append(("files", ("test_image.jpg", open(test_image_path, "rb"), "image/jpeg")))
    
    if test_video_path.exists():
        files.append(("files", ("test_video.mp4", open(test_video_path, "rb"), "video/mp4")))
    
    try:
        # Make the request
        response = requests.post(
            f"{BASE_URL}/posts",
            data=form_data,
            files=files,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Post created successfully with media!")
            response_data = response.json()
            if "uploaded_media_urls" in response_data["data"]:
                print(f"📎 Uploaded {len(response_data['data']['uploaded_media_urls'])} media files:")
                for url in response_data["data"]["uploaded_media_urls"]:
                    print(f"   - {url}")
        else:
            print("❌ Failed to create post")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Close file handles
        for _, file_tuple in files:
            if len(file_tuple) > 1 and hasattr(file_tuple[1], 'close'):
                file_tuple[1].close()

def test_create_post_without_media():
    """Test creating a post without media (using original endpoint)"""
    
    headers = {"Content-Type": "application/json"}
    
    post_data = {
        "title": "Test Post without Media",
        "content": "This is a test post created without media using the original endpoint.",
        "post_type": "discussion",
        "assignee": "some-representative-uuid",
        "location": "Test Location",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "tags": ["test", "no-media"],
        "media_urls": []
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/posts",
            json=post_data,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Post created successfully without media!")
        else:
            print("❌ Failed to create post")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing CivicPulse Post Creation with Media Upload")
    print("=" * 60)
    
    print("\n1. Testing post creation WITH media upload:")
    test_create_post_with_media()
    
    print("\n2. Testing post creation WITHOUT media:")
    test_create_post_without_media()
    
    print("\n✨ Test completed!")
