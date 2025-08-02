"""
Test script for the new file upload functionality in CivicPulse post creation API
This script demonstrates how to test the updated POST /posts endpoint with file uploads
"""
import requests
import json
import tempfile
import os
from pathlib import Path

# Configuration
from config.api_config import API_BASE_URL

BASE_URL = API_BASE_URL

def create_test_image(filename: str, size: tuple = (800, 600)) -> str:
    """Create a test image file for upload testing"""
    # Create a minimal JPEG file header + data (fake but valid structure)
    temp_dir = Path(tempfile.gettempdir())
    filepath = temp_dir / filename
    
    # Create a minimal fake JPEG file for testing
    # This creates a small file that will be detected as image/jpeg
    jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00'
    fake_data = b'\x00' * 1000  # Minimal fake image data
    jpeg_footer = b'\xff\xd9'
    
    with open(filepath, 'wb') as f:
        f.write(jpeg_header + fake_data + jpeg_footer)
    
    return str(filepath)

def create_test_video(filename: str) -> str:
    """Create a minimal test video file (placeholder)"""
    # For a real test, you'd create a small MP4 file
    # For now, we'll create a dummy file
    temp_dir = Path(tempfile.gettempdir())
    filepath = temp_dir / filename
    
    # Create a small dummy file (not a real video)
    with open(filepath, 'wb') as f:
        f.write(b'fake video content for testing')
    
    return str(filepath)

def test_upload_info():
    """Test the upload configuration endpoint"""
    print("🔍 Testing upload configuration endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/posts/upload-info")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload info retrieved successfully:")
            print(f"   S3 Available: {data['data']['s3_available']}")
            print(f"   Max files per post: {data['data']['max_files_per_post']}")
            print(f"   Max file size: {data['data']['max_file_size']} bytes")
            print(f"   Allowed image types: {data['data']['allowed_image_types']}")
            print(f"   Allowed video types: {data['data']['allowed_video_types']}")
            return data['data']
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_create_post_with_files():
    """Test creating a post with file uploads"""
    print("\n📝 Testing post creation with file uploads...")
    
    # Create test files
    test_image = create_test_image("test_upload.jpg")
    # test_video = create_test_video("test_upload.mp4")  # Uncomment for video testing
    
    try:
        # Prepare form data
        form_data = {
            "title": "Test Post with File Upload",
            "content": "This is a test post created with the new file upload functionality. It demonstrates uploading media files to S3.",
            "post_type": "issue",
            "assignee": "11111111-1111-1111-1111-111111111111",  # Use a valid UUID format
            "location": "Test Location, New Delhi",
            "latitude": 28.6139,  # New Delhi coordinates
            "longitude": 77.2090,
        }
        
        # Prepare files for upload
        files = []
        
        # Add test image
        if os.path.exists(test_image):
            files.append(('files', ('test_image.jpg', open(test_image, 'rb'), 'image/jpeg')))
        
        # Add test video (uncomment for video testing)
        # if os.path.exists(test_video):
        #     files.append(('files', ('test_video.mp4', open(test_video, 'rb'), 'video/mp4')))
        
        # Make the request
        response = requests.post(
            f"{BASE_URL}/posts",
            data=form_data,
            files=files
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Post created successfully!")
            print(f"   Post ID: {data['data']['post']['id']}")
            print(f"   Title: {data['data']['post']['title']}")
            print(f"   Uploaded files: {data['data']['uploaded_files']}")
            print(f"   Media URLs: {data['data']['media_urls']}")
            return data['data']
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    finally:
        # Clean up test files
        for filepath in [test_image]:  # Add test_video when testing videos
            if os.path.exists(filepath):
                os.remove(filepath)

def test_create_post_without_files():
    """Test creating a post without file uploads (should still work)"""
    print("\n📝 Testing post creation without files...")
    
    try:
        # Prepare form data
        form_data = {
            "title": "Test Post without Files",
            "content": "This is a test post created without any file uploads.",
            "post_type": "discussion",
            "assignee": "11111111-1111-1111-1111-111111111111",
            "location": "Test Location",
            "latitude": 28.6139,
            "longitude": 77.2090,
        }
        
        # Make the request without files
        response = requests.post(
            f"{BASE_URL}/posts",
            data=form_data
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Post created successfully without files!")
            print(f"   Post ID: {data['data']['post']['id']}")
            print(f"   Title: {data['data']['post']['title']}")
            print(f"   Media URLs: {data['data']['post'].get('media_urls', [])}")
            return data['data']
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_file_validation():
    """Test file validation (large files, invalid types)"""
    print("\n🛡️ Testing file validation...")
    
    # Create a large test file (exceeding limits)
    temp_dir = Path(tempfile.gettempdir())
    large_file = temp_dir / "large_file.txt"
    
    try:
        # Create a file larger than the typical limit
        with open(large_file, 'wb') as f:
            f.write(b'x' * (15 * 1024 * 1024))  # 15MB file
        
        form_data = {
            "title": "Test Post with Large File",
            "content": "This should fail due to file size limits.",
            "post_type": "issue",
            "assignee": "11111111-1111-1111-1111-111111111111",
        }
        
        files = [('files', ('large_file.txt', open(large_file, 'rb'), 'text/plain'))]
        
        response = requests.post(
            f"{BASE_URL}/posts",
            data=form_data,
            files=files
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 400:
            print("✅ File validation working - large/invalid file rejected")
            print(f"   Error: {response.json().get('detail', 'No detail')}")
        else:
            print(f"⚠️ Unexpected result: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Clean up
        if os.path.exists(large_file):
            os.remove(large_file)

def main():
    """Run all tests"""
    print("🚀 Testing CivicPulse File Upload API")
    print("=" * 50)
    
    # Test 1: Get upload configuration
    upload_info = test_upload_info()
    
    # Test 2: Create post with files
    if upload_info and upload_info['s3_available']:
        test_create_post_with_files()
    else:
        print("\n⚠️ S3 not available, skipping file upload test")
    
    # Test 3: Create post without files
    test_create_post_without_files()
    
    # Test 4: Test file validation
    test_file_validation()
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main()
