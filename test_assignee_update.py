#!/usr/bin/env python3
"""
Test script to verify the new assignee update API works correctly
"""
import asyncio
import json
import logging
from datetime import datetime
from app.services.post_service import PostService
from app.services.db_service import DatabaseService
from app.schemas import PostCreate
from uuid import UUID, uuid4

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_assignee_update_api():
    """Test the new assignee update functionality"""
    post_service = PostService()
    db_service = DatabaseService()
    
    try:
        logger.info("🧪 Testing assignee update API...")
        
        # First, let's check if we have any existing posts to work with
        logger.info("📋 Getting existing posts...")
        posts = await post_service.get_posts(skip=0, limit=5)
        
        if not posts:
            logger.info("❌ No posts found to test with")
            return
        
        test_post = posts[0]
        post_id = test_post['id']
        original_assignee = test_post.get('assignee')
        
        logger.info(f"📝 Testing with post ID: {post_id}")
        logger.info(f"📝 Original assignee: {original_assignee}")
        
        # Test the new database method directly
        logger.info("🔄 Testing update_post_assignee database method...")
        
        # Test setting assignee to None (unassigning)
        result = await db_service.update_post_assignee(post_id, None)
        if result:
            logger.info("✅ Successfully updated assignee to None")
            logger.info(f"   New assignee: {result.get('assignee')}")
        else:
            logger.error("❌ Failed to update assignee to None")
            return
        
        # Test setting assignee back to original value
        if original_assignee:
            result = await db_service.update_post_assignee(post_id, str(original_assignee))
            if result:
                logger.info(f"✅ Successfully restored original assignee: {original_assignee}")
            else:
                logger.error("❌ Failed to restore original assignee")
                return
        
        logger.info("🎉 All assignee update tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_assignee_update_api())
