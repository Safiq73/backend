#!/usr/bin/env python3
"""
Test script for representative linking functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from uuid import UUID, uuid4
from app.services.representative_service import RepresentativeService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_representative_service():
    """Test the representative service functionality"""
    rep_service = RepresentativeService()
    
    try:
        # Test 1: Get available representatives
        logger.info("Testing: Get available representatives")
        available_reps = await rep_service.get_available_representatives()
        logger.info(f"Found {len(available_reps)} available representatives")
        
        if available_reps:
            # Show first few representatives
            for i, rep in enumerate(available_reps[:3]):
                logger.info(f"Rep {i+1}: {rep['title_name']} - {rep['jurisdiction_name']}")
        
        # Test 2: Test getting representative by ID (if any exist)
        if available_reps:
            rep_id = available_reps[0]['id']  # Already a UUID object
            if isinstance(rep_id, str):
                rep_id = UUID(rep_id)
            logger.info(f"Testing: Get representative by ID: {rep_id}")
            rep_details = await rep_service.get_representative_by_id(rep_id)
            if rep_details:
                logger.info(f"Representative details: {rep_details['title_name']} in {rep_details['jurisdiction_name']}")
        
        # Test 3: Test getting linked representative for a fake user
        fake_user_id = uuid4()
        logger.info(f"Testing: Get linked representative for user: {fake_user_id}")
        linked_rep = await rep_service.get_user_linked_representative(fake_user_id)
        logger.info(f"Linked representative: {linked_rep}")
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_representative_service())
