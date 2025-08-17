"""
Follow service layer for user follow/unfollow functionality
"""
import logging
from typing import Dict, Any
from uuid import UUID
from fastapi import HTTPException
from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class FollowService:
    """Service for follow-related operations"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def follow_user(self, follower_id: UUID, followed_id: UUID) -> Dict[str, Any]:
        """Follow a user"""
        # Prevent self-following
        if follower_id == followed_id:
            raise HTTPException(status_code=400, detail="Users cannot follow themselves")
        
        try:
            result = await self.db_service.follow_user(follower_id, followed_id)
            
            message = "User followed successfully"
            if result['mutual']:
                message = "User followed successfully - You now follow each other!"
            
            return {
                'success': True,
                'message': message,
                'mutual': result['mutual']
            }
            
        except ValueError as e:
            error_msg = str(e)
            if "already being followed" in error_msg:
                raise HTTPException(status_code=400, detail="User is already being followed")
            elif "does not exist" in error_msg:
                raise HTTPException(status_code=404, detail="User not found")
            else:
                raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            logger.error(f"Error following user {followed_id} by {follower_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def unfollow_user(self, follower_id: UUID, followed_id: UUID) -> Dict[str, Any]:
        """Unfollow a user"""
        # Prevent self-unfollowing
        if follower_id == followed_id:
            raise HTTPException(status_code=400, detail="Users cannot unfollow themselves")
        
        try:
            result = await self.db_service.unfollow_user(follower_id, followed_id)
            
            return {
                'success': True,
                'message': "User unfollowed successfully"
            }
            
        except ValueError as e:
            error_msg = str(e)
            if "not being followed" in error_msg:
                raise HTTPException(status_code=400, detail="User is not being followed")
            else:
                raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            logger.error(f"Error unfollowing user {followed_id} by {follower_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_followers(self, user_id: UUID, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get list of followers for a user"""
        try:
            result = await self.db_service.get_user_followers(user_id, page, size)
            return result
        except Exception as e:
            logger.error(f"Error getting followers for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_following(self, user_id: UUID, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get list of users that the specified user is following"""
        try:
            result = await self.db_service.get_user_following(user_id, page, size)
            return result
        except Exception as e:
            logger.error(f"Error getting following for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_follow_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get follow statistics for a user"""
        try:
            result = await self.db_service.get_follow_stats(user_id)
            return result
        except Exception as e:
            logger.error(f"Error getting follow stats for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_follow_status(self, follower_id: UUID, followed_id: UUID) -> Dict[str, Any]:
        """Check follow status between two users"""
        try:
            result = await self.db_service.check_follow_status(follower_id, followed_id)
            return result
        except Exception as e:
            logger.error(f"Error checking follow status between {follower_id} and {followed_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
