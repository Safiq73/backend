"""
Comment Service for CivicPulse
Handles all comment-related business logic and database operations
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
import re

from app.models.pydantic_models import (
    CommentCreate, CommentUpdate, CommentResponse, 
    VoteType, PaginatedResponse, AuthorInfo
)
from app.services.db_service import DatabaseService
from app.core.logging_config import get_logger

logger = get_logger('app.services.comment')


class CommentService:
    """Service for comment-related operations"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def create_comment(self, comment_data: CommentCreate, user_id: UUID) -> CommentResponse:
        """
        Create a new comment on a post
        
        Args:
            comment_data: Comment creation data
            user_id: UUID of the user creating the comment
            
        Returns:
            CommentResponse: Created comment with author info
            
        Raises:
            ValueError: If post doesn't exist or comment data is invalid
        """
        try:
            # Validate post exists
            post = await self.db_service.get_post_by_id(comment_data.post_id)
            if not post:
                raise ValueError("Post not found")
            
            # Validate parent comment if replying
            if comment_data.parent_id:
                parent_comment = await self.db_service.get_comment_by_id(comment_data.parent_id)
                if not parent_comment:
                    raise ValueError("Parent comment not found")
                if parent_comment['post_id'] != comment_data.post_id:
                    raise ValueError("Parent comment must be on the same post")
            
            # Create comment in database
            comment_dict = {
                'post_id': comment_data.post_id,  # Don't convert to string
                'content': comment_data.content,
                'parent_id': comment_data.parent_id if comment_data.parent_id else None
            }
            
            new_comment = await self.db_service.create_comment(comment_dict, user_id)
            
            # Get full comment with author info
            full_comment = await self.get_comment_by_id(new_comment['id'], user_id)
            
            # Handle notifications
            await self._handle_comment_notifications(
                comment=full_comment,
                post=post,
                commenter_id=user_id
            )
            
            logger.info(f"Comment created successfully | ID: {new_comment['id']} | User: {user_id}")
            return full_comment
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create comment: {e}")
            raise Exception(f"Failed to create comment: {str(e)}")
    
    async def get_comments_by_post(
        self, 
        post_id: UUID, 
        current_user_id: Optional[UUID] = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        order: str = "desc"
    ) -> PaginatedResponse[CommentResponse]:
        """
        Get paginated comments for a post
        
        Args:
            post_id: UUID of the post
            current_user_id: Optional UUID of current user for vote status
            page: Page number (1-based)
            size: Number of comments per page
            sort_by: Field to sort by
            order: Sort order (asc/desc)
            
        Returns:
            PaginatedResponse[CommentResponse]: Paginated comments
        """
        try:
            # Validate post exists
            post = await self.db_service.get_post_by_id(post_id)
            if not post:
                raise ValueError("Post not found")
            
            # Calculate offset
            offset = (page - 1) * size
            
            # Get comments from database
            comments_data = await self.db_service.get_comments_by_post_paginated(
                post_id=post_id,
                limit=size,
                offset=offset,
                sort_by=sort_by,
                order=order
            )
            
            # Get total count
            total_count = await self.db_service.get_comments_count_by_post(post_id)
            
            # Format comments
            comments = []
            for comment_data in comments_data:
                comment = await self._format_comment_response(comment_data, current_user_id)
                comments.append(comment)
            
            # Calculate pagination info
            has_more = (offset + len(comments)) < total_count
            
            return PaginatedResponse[CommentResponse](
                items=comments,
                total=total_count,
                page=page,
                size=size,
                has_more=has_more
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get comments for post {post_id}: {e}")
            raise Exception(f"Failed to get comments: {str(e)}")
    
    async def get_comment_by_id(
        self, 
        comment_id: UUID, 
        current_user_id: Optional[UUID] = None
    ) -> Optional[CommentResponse]:
        """
        Get a specific comment by ID
        
        Args:
            comment_id: UUID of the comment
            current_user_id: Optional UUID of current user for vote status
            
        Returns:
            Optional[CommentResponse]: Comment if found, None otherwise
        """
        try:
            comment_data = await self.db_service.get_comment_by_id(comment_id)
            if not comment_data:
                return None
            
            return await self._format_comment_response(comment_data, current_user_id)
            
        except Exception as e:
            logger.error(f"Failed to get comment {comment_id}: {e}")
            raise Exception(f"Failed to get comment: {str(e)}")
    
    async def update_comment(
        self, 
        comment_id: UUID, 
        comment_data: CommentUpdate, 
        user_id: UUID
    ) -> Optional[CommentResponse]:
        """
        Update a comment (only by the comment author)
        
        Args:
            comment_id: UUID of the comment to update
            comment_data: Updated comment data
            user_id: UUID of the user requesting the update
            
        Returns:
            Optional[CommentResponse]: Updated comment if successful, None if not found/unauthorized
        """
        try:
            # Check if comment exists and user is authorized
            existing_comment = await self.db_service.get_comment_by_id(comment_id)
            if not existing_comment:
                return None
            
            if UUID(existing_comment['user_id']) != user_id:
                logger.warning(f"Unauthorized comment update attempt | Comment: {comment_id} | User: {user_id}")
                return None
            
            # Update comment in database
            update_dict = {'content': comment_data.content}
            updated_comment = await self.db_service.update_comment(comment_id, update_dict, user_id)
            
            if not updated_comment:
                return None
            
            # Get full comment with author info
            full_comment = await self.get_comment_by_id(comment_id, user_id)
            
            logger.info(f"Comment updated successfully | ID: {comment_id} | User: {user_id}")
            return full_comment
            
        except Exception as e:
            logger.error(f"Failed to update comment {comment_id}: {e}")
            raise Exception(f"Failed to update comment: {str(e)}")
    
    async def delete_comment(self, comment_id: UUID, user_id: UUID) -> bool:
        """
        Delete a comment (only by the comment author)
        
        Args:
            comment_id: UUID of the comment to delete
            user_id: UUID of the user requesting the deletion
            
        Returns:
            bool: True if deleted successfully, False if not found/unauthorized
        """
        try:
            # Check if comment exists and user is authorized
            existing_comment = await self.db_service.get_comment_by_id(comment_id)
            if not existing_comment:
                return False
            
            if UUID(existing_comment['user_id']) != user_id:
                logger.warning(f"Unauthorized comment deletion attempt | Comment: {comment_id} | User: {user_id}")
                return False
            
            # Delete comment from database
            success = await self.db_service.delete_comment(comment_id, user_id)
            
            if success:
                logger.info(f"Comment deleted successfully | ID: {comment_id} | User: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete comment {comment_id}: {e}")
            raise Exception(f"Failed to delete comment: {str(e)}")
    
    async def get_comment_replies(
        self,
        comment_id: UUID,
        current_user_id: Optional[UUID] = None,
        page: int = 1,
        size: int = 10
    ) -> PaginatedResponse[CommentResponse]:
        """
        Get replies to a specific comment
        
        Args:
            comment_id: UUID of the parent comment
            current_user_id: Optional UUID of current user for vote status
            page: Page number (1-based)
            size: Number of replies per page
            
        Returns:
            PaginatedResponse[CommentResponse]: Paginated replies
        """
        try:
            # Validate parent comment exists
            parent_comment = await self.db_service.get_comment_by_id(comment_id)
            if not parent_comment:
                raise ValueError("Parent comment not found")
            
            # Calculate offset
            offset = (page - 1) * size
            
            # Get replies from database
            replies_data = await self.db_service.get_comment_replies(
                parent_id=comment_id,
                limit=size,
                offset=offset
            )
            
            # Get total replies count
            total_count = await self.db_service.get_comment_replies_count(comment_id)
            
            # Format replies
            replies = []
            for reply_data in replies_data:
                reply = await self._format_comment_response(reply_data, current_user_id)
                replies.append(reply)
            
            # Calculate pagination info
            has_more = (offset + len(replies)) < total_count
            
            return PaginatedResponse[CommentResponse](
                items=replies,
                total=total_count,
                page=page,
                size=size,
                has_more=has_more
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get replies for comment {comment_id}: {e}")
            raise Exception(f"Failed to get comment replies: {str(e)}")
    
    async def vote_on_comment(
        self, 
        comment_id: UUID, 
        vote_type: VoteType, 
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Vote on a comment
        
        Args:
            comment_id: UUID of the comment to vote on
            vote_type: Type of vote (upvote/downvote)
            user_id: UUID of the user voting
            
        Returns:
            Dict with vote counts and user vote status
        """
        try:
            # Validate comment exists
            comment = await self.db_service.get_comment_by_id(comment_id)
            if not comment:
                raise ValueError("Comment not found")
            
            # Create or update vote
            await self.db_service.create_or_update_comment_vote(comment_id, user_id, vote_type.value)
            
            # Get updated vote counts and user's vote status
            vote_counts = await self.db_service.get_comment_vote_counts(comment_id)
            user_vote = await self.db_service.get_user_vote_on_comment(comment_id, user_id)
            
            result = {
                "upvotes": vote_counts.get("upvotes", 0),
                "downvotes": vote_counts.get("downvotes", 0),
                "is_upvoted": user_vote and user_vote['vote_type'] == 'upvote',
                "is_downvoted": user_vote and user_vote['vote_type'] == 'downvote'
            }
            
            logger.info(f"User {user_id} voted {vote_type.value} on comment {comment_id}")
            return result
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to vote on comment {comment_id}: {e}")
            raise Exception(f"Failed to vote on comment: {str(e)}")
    
    async def remove_vote_from_comment(self, comment_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Remove vote from a comment
        
        Args:
            comment_id: UUID of the comment
            user_id: UUID of the user removing vote
            
        Returns:
            Dict with updated vote counts and user vote status
        """
        try:
            # Validate comment exists
            comment = await self.db_service.get_comment_by_id(comment_id)
            if not comment:
                raise ValueError("Comment not found")
            
            # Remove vote
            await self.db_service.remove_comment_vote(comment_id, user_id)
            
            # Get updated vote counts
            vote_counts = await self.db_service.get_comment_vote_counts(comment_id)
            
            result = {
                "upvotes": vote_counts.get("upvotes", 0),
                "downvotes": vote_counts.get("downvotes", 0),
                "is_upvoted": False,
                "is_downvoted": False
            }
            
            logger.info(f"User {user_id} removed vote from comment {comment_id}")
            return result
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to remove vote from comment {comment_id}: {e}")
            raise Exception(f"Failed to remove vote from comment: {str(e)}")
    
    async def _format_comment_response(
        self, 
        comment_data: Dict[str, Any], 
        current_user_id: Optional[UUID] = None
    ) -> CommentResponse:
        """
        Format comment data into CommentResponse model
        
        Args:
            comment_data: Raw comment data from database
            current_user_id: Optional current user ID for vote status
            
        Returns:
            CommentResponse: Formatted comment
        """
        comment_id = UUID(comment_data['id']) if isinstance(comment_data['id'], str) else comment_data['id']
        
        # Get vote counts
        vote_counts = await self.db_service.get_comment_vote_counts(comment_id)
        
        # Get user's vote status if logged in
        user_vote = None
        if current_user_id:
            user_vote_data = await self.db_service.get_user_vote_on_comment(comment_id, current_user_id)
            if user_vote_data:
                user_vote = VoteType(user_vote_data['vote_type'])
        
        # Get reply count
        reply_count = await self.db_service.get_comment_replies_count(comment_id)
        
        # Format author info
        author = AuthorInfo(
            id=UUID(comment_data['author']['id']) if isinstance(comment_data['author']['id'], str) else comment_data['author']['id'],
            username=comment_data['author']['username'],
            display_name=comment_data['author'].get('display_name'),
            avatar_url=comment_data['author'].get('avatar_url'),
            rep_accounts=[]  # Simplified for now to avoid validation issues
        )
        
        return CommentResponse(
            id=comment_id,
            post_id=UUID(comment_data['post_id']) if isinstance(comment_data['post_id'], str) else comment_data['post_id'],
            user_id=UUID(comment_data['author']['id']) if isinstance(comment_data['author']['id'], str) else comment_data['author']['id'],
            content=comment_data['content'],
            parent_id=UUID(comment_data['parent_id']) if comment_data.get('parent_id') and isinstance(comment_data['parent_id'], str) else comment_data.get('parent_id'),
            author=author,
            edited=comment_data.get('edited', False),
            edited_at=comment_data.get('edited_at'),
            upvotes=vote_counts.get("upvotes", 0),
            downvotes=vote_counts.get("downvotes", 0),
            reply_count=reply_count,
            thread_level=comment_data.get('thread_level', 0),
            thread_path=comment_data.get('thread_path'),
            created_at=comment_data['created_at'],
            updated_at=comment_data['updated_at'],
            user_vote=user_vote
        )
    
    async def _handle_comment_notifications(
        self, 
        comment: CommentResponse, 
        post: Dict[str, Any], 
        commenter_id: UUID
    ):
        """
        Handle notifications for new comments
        
        Args:
            comment: The created comment
            post: The post being commented on
            commenter_id: UUID of the comment author
        """
        try:
            from app.services.notification_service import notification_service
            
            # Get commenter info
            commenter = await self.db_service.get_user_by_id(commenter_id)
            commenter_name = commenter.get('display_name') or commenter.get('username', 'Someone')
            
            # Extract mentioned users from comment content (@username)
            mentioned_users = []
            mentions = re.findall(r'@(\w+)', comment.content)
            if mentions:
                for username in mentions:
                    mentioned_user = await self.db_service.get_user_by_username(username)
                    if mentioned_user:
                        mentioned_users.append(UUID(mentioned_user['id']))
            
            # Notify post author (if not self-comment) or mentioned users
            if post.get('user_id') != str(commenter_id):
                await notification_service.notify_new_comment(
                    post_id=comment.post_id,
                    post_title=post.get('title', 'Unknown Post'),
                    comment_id=comment.id,
                    commenter_name=commenter_name,
                    post_author_id=UUID(post['user_id']),
                    mentioned_users=mentioned_users
                )
            elif mentioned_users:
                # If user commented on their own post but mentioned others, still notify mentions
                await notification_service.notify_new_comment(
                    post_id=comment.post_id,
                    post_title=post.get('title', 'Unknown Post'),
                    comment_id=comment.id,
                    commenter_name=commenter_name,
                    post_author_id=UUID(post['user_id']),
                    mentioned_users=mentioned_users
                )
                
        except Exception as e:
            logger.error(f"Failed to send comment notification: {e}")
            # Don't fail the comment creation if notification fails
