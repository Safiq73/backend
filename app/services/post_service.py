"""
Post service layer - Production implementation using raw SQL
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException
from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class PostService:
    """Service for post-related operations using raw SQL"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def create_post(self, post_data: Dict[str, Any], author_id: UUID) -> Dict[str, Any]:
        """Create a new post"""
        # Create the post in database

        post = await self.db_service.create_post(post_data, author_id)
        
        # Get full post with author info
        full_post = await self.db_service.get_post_by_id(post['id'])
        
        # Format response with engagement data
        response = await self._format_post_response(full_post, author_id)
        
        logger.info(f"Created post {post['id']} by user {author_id}")
        return response
        
    
    async def get_posts(
        self,
        skip: int = 0,
        limit: int = 20,
        post_type: Optional[str] = None,
        location: Optional[str] = None,
        author_id: Optional[UUID] = None,
        assignee: Optional[List[str]] = None,
        current_user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get posts with filters and pagination"""
        # Get posts from database
        posts = await self.db_service.get_posts(
            skip=skip,
            limit=limit,
            post_type=post_type,
            user_id=author_id,
            location=location,
            assignee=assignee
        )

        # Convert to response format
        responses = []
        for post in posts:
            response = await self._format_post_response(post, current_user_id)
            responses.append(response)
        
        logger.info(f"Retrieved {len(responses)} posts with filters: type={post_type}, location={location}, assignee={assignee}")
        return responses
            
    
    async def get_post_by_id(self, post_id: UUID, current_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get a specific post by ID"""
        try:
            post = await self.db_service.get_post_by_id(post_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            
            response = await self._format_post_response(post, current_user_id)
            
            logger.info(f"Retrieved post {post_id}")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve post")
    
    async def update_post(self, post_id: UUID, post_data: Dict[str, Any], current_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Update a post"""
        try:
            # Get the post first to check ownership if current_user_id is provided
            if current_user_id is not None:
                post = await self.db_service.get_post_by_id(post_id)
                if not post:
                    raise HTTPException(status_code=404, detail="Post not found")
                
                post_author_id = post['author']['id']
                if isinstance(post_author_id, str):
                    post_author_id = UUID(post_author_id)
                if post_author_id != current_user_id:
                    raise HTTPException(status_code=403, detail="Not authorized to update this post")
            
            # Update the post
            updated_post = await self.db_service.update_post(post_id, post_data)
            if not updated_post:
                raise HTTPException(status_code=404, detail="Post not found")
            
            response = await self._format_post_response(updated_post, current_user_id)
            
            logger.info(f"Updated post {post_id} by user {current_user_id or 'system'}")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update post")

    async def update_post_status(self, post_id: UUID, status: str, current_user_id: UUID) -> Dict[str, Any]:
        """Update post status with authorization checks"""
        # Get the post first to check authorization
        post = await self.db_service.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Check if user is authorized to update status
        is_authorized = await self._check_post_status_authorization(post, current_user_id)
        if not is_authorized:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to update post status. Only post author or assigned representatives can update status."
            )
        
        # Update the post status
        updated_post = await self.db_service.update_post_status(post_id, status)
        if not updated_post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        response = await self._format_post_response(updated_post, current_user_id)
        
        logger.info(f"Updated post {post_id} status to {status} by user {current_user_id}")
        return response

    async def update_post_assignee(self, post_id: UUID, assignee_id: Optional[str], current_user_id: UUID) -> Dict[str, Any]:
        """Update post assignee with authorization checks"""
        # Get the post first to check authorization
        post = await self.db_service.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Check if user is authorized to update assignee
        is_authorized = await self._check_post_assignee_authorization(post, current_user_id)
        if not is_authorized:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to update post assignee. Only post author or current assignee can update assignee."
            )
        
        # If assigning to someone, validate the representative exists
        if assignee_id:
            from app.services.representative_service import RepresentativeService
            rep_service = RepresentativeService()
            representative = await rep_service.get_representative_by_id(assignee_id)
            if not representative:
                raise HTTPException(status_code=400, detail="Invalid representative ID")
        
        # Update the post assignee
        updated_post = await self.db_service.update_post_assignee(post_id, assignee_id)
        if not updated_post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        response = await self._format_post_response(updated_post, current_user_id)
        
        action = "assigned" if assignee_id else "unassigned"
        logger.info(f"Updated post {post_id} assignee ({action}) by user {current_user_id}")
        return response

    async def _check_post_assignee_authorization(self, post: Dict[str, Any], user_id: UUID) -> bool:
        """Check if user is authorized to update post assignee"""
        # Check if user is the post author
        post_author_id = post['author']['id']
        if isinstance(post_author_id, str):
            post_author_id = UUID(post_author_id)
        if post_author_id == user_id:
            return True
        
        # Check if user is the current assignee
        assignee_id = post.get('assignee')
        if assignee_id:
            # Get user's linked representative accounts
            from app.services.representative_service import RepresentativeService
            rep_service = RepresentativeService()
            user_rep_accounts = await rep_service.get_user_rep_accounts(user_id)
            
            # Check if any of user's representative accounts match the current assignee
            for rep_account in user_rep_accounts:
                if str(rep_account['id']) == str(assignee_id):
                    return True
        
        return False

    async def _check_post_status_authorization(self, post: Dict[str, Any], user_id: UUID) -> bool:
        """Check if user is authorized to update post status"""
        # Check if user is the post author
        post_author_id = post['author']['id']
        if isinstance(post_author_id, str):
            post_author_id = UUID(post_author_id)
        if post_author_id == user_id:
            return True
        
        # Check if post has an assignee and user is linked to that representative
        assignee_id = post.get('assignee')
        if assignee_id:
            # Get user's linked representative accounts
            from app.services.representative_service import RepresentativeService
            rep_service = RepresentativeService()
            user_rep_accounts = await rep_service.get_user_rep_accounts(user_id)
            
            # Check if any of user's representative accounts match the assignee
            for rep_account in user_rep_accounts:
                if str(rep_account['id']) == str(assignee_id):
                    return True
        
        return False
    
    async def delete_post(self, post_id: UUID, current_user_id: UUID) -> bool:
        """Delete a post"""
        try:
            # Get the post first to check ownership
            post = await self.db_service.get_post_by_id(post_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
            
            post_author_id = post['author']['id']
            if isinstance(post_author_id, str):
                post_author_id = UUID(post_author_id)
            if post_author_id != current_user_id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this post")
            
            # Delete the post
            success = await self.db_service.delete_post(post_id)
            if not success:
                raise HTTPException(status_code=404, detail="Post not found")
            
            logger.info(f"Deleted post {post_id} by user {current_user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete post")
    
    async def vote_on_post(self, post_id: UUID, vote_type: str, user_id: UUID) -> Dict[str, Any]:
        """Vote on a post (upvote/downvote)"""
        try:
            # Validate vote type
            if vote_type.lower() not in ['upvote', 'downvote']:
                raise HTTPException(status_code=400, detail="Invalid vote type")
            
            # Create or update vote
            vote = await self.db_service.create_or_update_vote(post_id, user_id, vote_type.lower())
            
            # Get updated vote counts
            vote_counts = await self.db_service.get_post_vote_counts(post_id)
            
            # Get user's current vote status
            user_vote = await self.db_service.get_user_vote_on_post(post_id, user_id)
            is_upvoted = user_vote and user_vote['vote_type'] == 'upvote'
            is_downvoted = user_vote and user_vote['vote_type'] == 'downvote'
            
            result = {
                "upvotes": vote_counts["upvotes"],
                "downvotes": vote_counts["downvotes"],
                "is_upvoted": is_upvoted,
                "is_downvoted": is_downvoted
            }
            
            logger.info(f"User {user_id} voted {vote_type} on post {post_id}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error voting on post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to vote on post")
    
    async def save_post(self, post_id: UUID, user_id: UUID) -> Dict[str, bool]:
        """Toggle save status for a post by a user"""
        try:
            # Check if post is already saved
            is_currently_saved = await self.db_service.is_post_saved(post_id, user_id)
            
            if is_currently_saved:
                # Unsave the post
                await self.db_service.unsave_post(post_id, user_id)
                logger.info(f"User {user_id} unsaved post {post_id}")
                return {"is_saved": False}
            else:
                # Save the post
                await self.db_service.save_post(post_id, user_id)
                logger.info(f"User {user_id} saved post {post_id}")
                return {"is_saved": True}
            
        except Exception as e:
            logger.error(f"Error toggling save status for post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to save/unsave post")
    
    async def unsave_post(self, post_id: UUID, user_id: UUID) -> Dict[str, bool]:
        """Remove a saved post for a user"""
        try:
            success = await self.db_service.unsave_post(post_id, user_id)
            
            if success:
                logger.info(f"User {user_id} unsaved post {post_id}")
            
            return {"is_saved": False}
            
        except Exception as e:
            logger.error(f"Error unsaving post {post_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to unsave post")
    
    async def get_saved_posts(self, user_id: UUID, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Get saved posts for a user"""
        try:
            # TODO: Implement get_saved_posts in DatabaseService
            # For now, return empty list
            logger.info(f"Retrieved 0 saved posts for user {user_id} (not implemented)")
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving saved posts for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve saved posts")
    
    async def get_trending_posts(self, hours: int = 24, limit: int = 10, current_user_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Get trending posts"""
        try:
            posts = await self.db_service.get_trending_posts(hours, limit)
            
            responses = []
            for post in posts:
                response = await self._format_post_response(post, current_user_id)
                responses.append(response)
            
            logger.info(f"Retrieved {len(responses)} trending posts")
            return responses
            
        except Exception as e:
            logger.error(f"Error retrieving trending posts: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve trending posts")
    
    async def _format_post_response(self, post: Dict[str, Any], current_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Convert database post to API response format"""
        # Handle UUID - post['id'] is already a UUID object from asyncpg
        post_id = post['id'] if isinstance(post['id'], UUID) else UUID(post['id'])
        
        # Get vote counts
        vote_counts = await self.db_service.get_post_vote_counts(post_id)
        
        # Get user's vote status if logged in
        is_upvoted = False
        is_downvoted = False
        is_saved = False
        
        if current_user_id:
            user_vote = await self.db_service.get_user_vote_on_post(post_id, current_user_id)
            if user_vote:
                is_upvoted = user_vote['vote_type'] == 'upvote'
                is_downvoted = user_vote['vote_type'] == 'downvote'
            
            is_saved = await self.db_service.is_post_saved(post_id, current_user_id)
        
        # Get comments count
        comments = await self.db_service.get_comments_by_post(post_id)
        comment_count = len(comments)
        
        # Get assignee details if post has an assignee
        assignee_info = None
        if post.get('assignee'):
            try:
                from app.services.representative_service import RepresentativeService
                rep_service = RepresentativeService()
                # Handle the case where assignee might already be a UUID object
                assignee_id = post['assignee']
                if not isinstance(assignee_id, UUID):
                    assignee_id = UUID(assignee_id)
                assignee_details = await rep_service.get_representative_with_user_details(assignee_id)
                if assignee_details:
                    assignee_info = assignee_details
            except Exception as e:
                logger.error(f"Error fetching assignee details for post {post_id}: {e}")
                # Don't fail the whole request if assignee details can't be fetched
                assignee_info = None
        
        return {
            "id": post['id'],
            "title": post['title'],
            "content": post['content'],
            "post_type": post['post_type'],
            "status": post.get('status'),  # Include status field
            "assignee": post.get('assignee'),  # Include assignee field
            "assignee_info": assignee_info,  # Include assignee details
            "media_urls": post.get('media_urls', []),  # Map media_urls to images for API response
            "latitude": post.get('latitude'),
            "longitude": post.get('longitude'),
            "author": post['author'],
            "created_at": post['created_at'],
            "updated_at": post['updated_at'],
            "upvotes": vote_counts["upvotes"],
            "downvotes": vote_counts["downvotes"],
            "comment_count": comment_count,
            "is_upvoted": is_upvoted,
            "is_downvoted": is_downvoted,
            "is_saved": is_saved
        }
        
