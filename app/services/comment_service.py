"""
Comment service layer - handles all comment-related business logic
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException
from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class CommentService:
    """Service for comment-related operations"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def create_comment(self, comment_data: Dict[str, Any], user_id: UUID) -> Dict[str, Any]:
        """Create a new comment"""
        try:
            # Validate required fields
            if not comment_data.get('content'):
                raise HTTPException(status_code=400, detail="Content is required")
            if not comment_data.get('post_id'):
                raise HTTPException(status_code=400, detail="Post ID is required")
            
            # Create comment in database
            comment = await self.db_service.create_comment(comment_data, user_id)
            
            # Get the full comment with author info
            full_comment = await self._get_comment_with_details(comment['id'], user_id)
            
            logger.info(f"Created comment {comment['id']} by user {user_id}")
            return full_comment
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to create comment")
    
    async def get_comments_by_post(self, post_id: UUID, current_user_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Get all comments for a post with user voting info"""
        try:
            # Get comments from database
            comments = await self.db_service.get_comments_by_post(post_id)
            
            # If user is authenticated, get their vote status for each comment
            if current_user_id:
                for comment in comments:
                    user_vote = await self.db_service.get_user_vote_on_comment(comment['id'], current_user_id)
                    comment['user_vote'] = user_vote['vote_type'] if user_vote else None
                    comment['is_upvoted'] = user_vote and user_vote['vote_type'] == 'upvote'
                    comment['is_downvoted'] = user_vote and user_vote['vote_type'] == 'downvote'
            else:
                for comment in comments:
                    comment['user_vote'] = None
                    comment['is_upvoted'] = False
                    comment['is_downvoted'] = False
            
            # Add vote counts (they should already be in the database via triggers)
            for comment in comments:
                vote_counts = await self.db_service.get_comment_vote_counts(comment['id'])
                comment.update(vote_counts)
            
            return comments
            
        except Exception as e:
            logger.error(f"Error retrieving comments for post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve comments")
    
    async def get_comment_by_id(self, comment_id: UUID, current_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get a comment by ID with user voting info"""
        try:
            comment = await self._get_comment_with_details(comment_id, current_user_id)
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            return comment
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving comment {comment_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve comment")
    
    async def update_comment(self, comment_id: UUID, comment_data: Dict[str, Any], current_user_id: UUID) -> Dict[str, Any]:
        """Update a comment (only by the author)"""
        try:
            # Get the comment first to check ownership
            comment = await self.db_service.get_comment_by_id(comment_id)
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            # Check if user is the author
            if comment['user_id'] != current_user_id:
                raise HTTPException(status_code=403, detail="Not authorized to update this comment")
            
            # Validate content
            if not comment_data.get('content'):
                raise HTTPException(status_code=400, detail="Content is required")
            
            # Update the comment
            updated_comment = await self.db_service.update_comment(comment_id, comment_data)
            if not updated_comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            # Get full comment with details
            full_comment = await self._get_comment_with_details(comment_id, current_user_id)
            
            logger.info(f"Updated comment {comment_id} by user {current_user_id}")
            return full_comment
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating comment {comment_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update comment")
    
    async def delete_comment(self, comment_id: UUID, current_user_id: UUID) -> bool:
        """Delete a comment (only by the author)"""
        try:
            # Get the comment first to check ownership
            comment = await self.db_service.get_comment_by_id(comment_id)
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            # Check if user is the author
            if comment['user_id'] != current_user_id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
            
            # Delete the comment
            success = await self.db_service.delete_comment(comment_id)
            if not success:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            logger.info(f"Deleted comment {comment_id} by user {current_user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting comment {comment_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete comment")
    
    async def vote_on_comment(self, comment_id: UUID, vote_type: str, user_id: UUID) -> Dict[str, Any]:
        """Vote on a comment (upvote/downvote)"""
        try:
            # Validate vote type
            if vote_type.lower() not in ['upvote', 'downvote']:
                raise HTTPException(status_code=400, detail="Invalid vote type")
            
            # Create or update vote
            vote = await self.db_service.create_or_update_comment_vote(comment_id, user_id, vote_type.lower())
            
            # Get updated vote counts
            vote_counts = await self.db_service.get_comment_vote_counts(comment_id)
            
            # Get user's current vote status
            user_vote = await self.db_service.get_user_vote_on_comment(comment_id, user_id)
            is_upvoted = user_vote and user_vote['vote_type'] == 'upvote'
            is_downvoted = user_vote and user_vote['vote_type'] == 'downvote'
            
            result = {
                'success': True,
                'upvotes': vote_counts['upvotes'],
                'downvotes': vote_counts['downvotes'],
                'user_vote': user_vote['vote_type'] if user_vote else None,
                'is_upvoted': is_upvoted,
                'is_downvoted': is_downvoted
            }
            
            logger.info(f"User {user_id} voted {vote_type} on comment {comment_id}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error voting on comment {comment_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to vote on comment")
    
    async def _get_comment_with_details(self, comment_id: UUID, current_user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get a comment with full details including vote counts and user vote status"""
        comment = await self.db_service.get_comment_by_id(comment_id)
        if not comment:
            return None
        
        # Get vote counts
        vote_counts = await self.db_service.get_comment_vote_counts(comment_id)
        comment.update(vote_counts)
        
        # Get user vote status if authenticated
        if current_user_id:
            user_vote = await self.db_service.get_user_vote_on_comment(comment_id, current_user_id)
            comment['user_vote'] = user_vote['vote_type'] if user_vote else None
            comment['is_upvoted'] = user_vote and user_vote['vote_type'] == 'upvote'
            comment['is_downvoted'] = user_vote and user_vote['vote_type'] == 'downvote'
        else:
            comment['user_vote'] = None
            comment['is_upvoted'] = False
            comment['is_downvoted'] = False
        
        return comment
