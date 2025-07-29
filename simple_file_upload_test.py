#!/usr/bin/env python3
"""
Simple test for file upload functionality
Run this script to test the new file upload endpoints
"""

import requests
import tempfile
import os
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

def create_test_file(filename: str, content: bytes, content_type: str = "image/jpeg") -> str:
    """Create a test file for upload"""
    temp_dir = Path(tempfile.gettempdir())
    filepath = temp_dir / filename
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    return str(filepath)

def test_upload_info():
    """Test upload configuration"""
    print("Testing upload info...")
    try:
        response = requests.get(f"{BASE_URL}/posts/upload-info")
        if response.status_code == 200:
            data = response.json()['data']
            print(f"✅ S3 Available: {data['s3_available']}")
            print(f"✅ Max files: {data['max_files_per_post']}")
            return data['s3_available']
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_post_creation():
    """Test creating a post with a file"""
    print("\nTesting post creation with file...")
    
    # Create a small test file
    test_content = b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'  # Minimal JPEG
    test_file = create_test_file("test.jpg", test_content)
    
    try:
        form_data = {
            "title": "Test Post with File Upload",
            "content": "Testing the new file upload functionality.",
            "post_type": "issue", 
            "assignee": "12345678-1234-1234-1234-123456789012",
            "location": "Test Location",
        }
        
        with open(test_file, 'rb') as f:
            files = [('files', ('test.jpg', f, 'image/jpeg'))]
            
            response = requests.post(
                f"{BASE_URL}/posts",
                data=form_data,
                files=files
            )
        
        if response.status_code == 200:
            data = response.json()['data']
            print(f"✅ Post created successfully!")
            print(f"✅ Post ID: {data['post']['id']}")
            print(f"✅ Uploaded files: {data['uploaded_files']}")
            print(f"✅ Media URLs: {len(data['media_urls'])}")
            return data['post']['id']
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def test_post_without_files():
    """Test creating a post without files"""
    print("\nTesting post creation without files...")
    
    try:
        form_data = {
            "title": "Test Post without Files",
            "content": "Testing post creation without any files.",
            "post_type": "discussion",
            "assignee": "12345678-1234-1234-1234-123456789012",
        }
        
        response = requests.post(f"{BASE_URL}/posts", data=form_data)
        
        if response.status_code == 200:
            data = response.json()['data']
            print(f"✅ Post created successfully without files!")
            print(f"✅ Post ID: {data['post']['id']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 Testing CivicPulse File Upload API")
    print("=" * 40)
    
    # Test upload configuration
    s3_available = test_upload_info()
    
    # Test post creation with files (if S3 is available)
    if s3_available:
        test_post_creation()
    else:
        print("\n⚠️ S3 not available, skipping file upload test")
    
    # Test post creation without files
    test_post_without_files()
    
    print("\n" + "=" * 40)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main()
