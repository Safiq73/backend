#!/usr/bin/env python3
"""
Test script for post status update API functionality
"""

import asyncio
import sys
import os
from uuid import uuid4

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.post_service import PostService
from app.services.db_service import DatabaseService
from app.services.representative_service import RepresentativeService
from app.core.logging_config import get_logger

logger = get_logger(__name__)

async def test_post_status_update():
    """Test the post status update functionality"""
    post_service = PostService()
    db_service = DatabaseService()
    rep_service = RepresentativeService()
    
    logger.info("=== Testing Post Status Update API ===")
    
    # Test 1: Get a sample post to test with
    logger.info("Test 1: Getting sample posts...")
    posts = await db_service.get_posts(skip=0, limit=5)
    
    if not posts:
        logger.warning("No posts found in database. Cannot test status update.")
        return
        
        test_post = posts[0]
        post_id = test_post['id']
        author_id = test_post['author']['id']
        
        logger.info(f"Using test post: {post_id}")
        logger.info(f"Post author: {author_id}")
        logger.info(f"Current status: {test_post.get('status', 'unknown')}")
        
        # Test 2: Check authorization logic
        logger.info("\nTest 2: Testing authorization logic...")
        
        # Get the post details for authorization testing
        post_details = await db_service.get_post_by_id(post_id)
        is_authorized_author = await post_service._check_post_status_authorization(post_details, author_id)
        logger.info(f"Author authorization check: {is_authorized_author}")
        
        # Test with a random user (should fail)
        random_user_id = uuid4()
        is_authorized_random = await post_service._check_post_status_authorization(post_details, random_user_id)
        logger.info(f"Random user authorization check: {is_authorized_random}")
        
        # Test 3: Check if post has assignee
        assignee_id = test_post.get('assignee')
        if assignee_id:
            logger.info(f"Post has assignee: {assignee_id}")
            
            # Get representative details
            rep_details = await rep_service.get_representative_by_id(assignee_id)
            if rep_details:
                logger.info(f"Assignee details: {rep_details.get('title_name', 'N/A')} - {rep_details.get('jurisdiction_name', 'N/A')}")
                
                # Check if assignee is linked to a user
                linked_user_id = rep_details.get('user_id')
                if linked_user_id:
                    logger.info(f"Assignee is linked to user: {linked_user_id}")
                    is_authorized_assignee = await post_service._check_post_status_authorization(post_details, linked_user_id)
                    logger.info(f"Assignee user authorization check: {is_authorized_assignee}")
                else:
                    logger.info("Assignee is not linked to any user")
            else:
                logger.warning("Could not get assignee details")
        else:
            logger.info("Post has no assignee")
        
        # Test 4: Test the database status update method
        logger.info("\nTest 4: Testing database status update...")
        original_status = test_post.get('status', 'open')
        new_status = 'in_progress' if original_status != 'in_progress' else 'resolved'
        
        updated_post = await db_service.update_post_status(post_id, new_status)
        if updated_post:
            logger.info(f"Successfully updated post status to: {new_status}")
            
            # Revert back to original status
            reverted_post = await db_service.update_post_status(post_id, original_status)
            if reverted_post:
                logger.info(f"Successfully reverted post status to: {original_status}")
            else:
                logger.error("Failed to revert post status")
        else:
            logger.error("Failed to update post status")
        
        logger.info("\n=== Test completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(test_post_status_update())
