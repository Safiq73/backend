#!/usr/bin/env python3
"""
Test script to verify follow_status is now in author object
"""
import asyncio
import json
from uuid import UUID
from app.services.post_service import PostService

async def test_follow_status_in_author():
    """Test that follow_status is included in author object"""
    print("🧪 Testing follow_status in author object...")
    
    post_service = PostService()
    
    # Test with a sample post (you may need to adjust the post_id)
    try:
        # Get posts with follow status
        posts = await post_service.get_posts(
            skip=0,
            limit=1,
            current_user_id=UUID("12345678-1234-5678-9012-123456789abc"),  # Replace with real user ID
            include_follow_status=True
        )
        
        if posts:
            post = posts[0]
            print(f"📝 Post ID: {post['id']}")
            print(f"👤 Author: {post['author']['display_name']} ({post['author']['id']})")
            
            # Check if follow_status is in author object
            if 'follow_status' in post['author']:
                follow_status = post['author']['follow_status']
                print(f"✅ follow_status found in author: {follow_status}")
                print(f"📋 Author object keys: {list(post['author'].keys())}")
            else:
                print("❌ follow_status NOT found in author object")
                print(f"📋 Author object keys: {list(post['author'].keys())}")
            
            # Check if follow_status is NOT at root level
            if 'follow_status' in post:
                print("⚠️  WARNING: follow_status found at root level (should be removed)")
            else:
                print("✅ follow_status correctly NOT at root level")
            
            # Pretty print the author object
            print("\n🔍 Author object structure:")
            print(json.dumps(post['author'], indent=2, default=str))
            
        else:
            print("📭 No posts found for testing")
            
    except Exception as e:
        print(f"❌ Error testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_follow_status_in_author())
