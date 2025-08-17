from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.schemas import APIResponse
from app.services.db_service import DatabaseService
from app.services.auth_service import get_current_user
from app.core.logging_config import get_logger
from uuid import UUID
import re

router = APIRouter()
db_service = DatabaseService()
logger = get_logger('app.comments')

@router.post("", response_model=APIResponse)
async def create_comment(
    comment_data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new comment on a post"""
    try:
        logger.info(f"Creating comment | Post: {comment_data.get('post_id')} | User: {current_user['id']}")
        
        # Validate required fields
        if not comment_data.get('post_id') or not comment_data.get('content'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post ID and content are required"
            )
        
        # Create comment
        new_comment = await db_service.create_comment(comment_data, UUID(current_user['id']))
        
        # Get post details for notification
        post = await db_service.get_post_by_id(UUID(comment_data['post_id']))
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Send real-time notification
        try:
            from app.services.notification_service import notification_service
            
            commenter_name = current_user.get('display_name') or current_user.get('username', 'Someone')
            
            # Extract mentioned users from comment content (@username)
            mentioned_users = []
            mentions = re.findall(r'@(\w+)', comment_data['content'])
            if mentions:
                # Get mentioned user IDs from usernames
                for username in mentions:
                    mentioned_user = await db_service.get_user_by_username(username)
                    if mentioned_user:
                        mentioned_users.append(UUID(mentioned_user['id']))
            
            # Don't notify if user commented on their own post
            if post.get('user_id') != current_user['id']:
                await notification_service.notify_new_comment(
                    post_id=UUID(comment_data['post_id']),
                    post_title=post.get('title', 'Unknown Post'),
                    comment_id=UUID(new_comment['id']),
                    commenter_name=commenter_name,
                    post_author_id=UUID(post['user_id']),
                    mentioned_users=mentioned_users
                )
            elif mentioned_users:
                # If user commented on their own post but mentioned others, still notify mentions
                await notification_service.notify_new_comment(
                    post_id=UUID(comment_data['post_id']),
                    post_title=post.get('title', 'Unknown Post'),
                    comment_id=UUID(new_comment['id']),
                    commenter_name=commenter_name,
                    post_author_id=UUID(post['user_id']),
                    mentioned_users=mentioned_users
                )
                
        except Exception as e:
            logger.error(f"Failed to send comment notification: {e}")
            # Don't fail the comment creation if notification fails
        
        logger.info(f"Comment created successfully | ID: {new_comment['id']}")
        
        return APIResponse(
            success=True,
            message="Comment created successfully",
            data=new_comment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

@router.get("/{post_id}")
async def get_comments(post_id: str):
    """Get all comments for a post"""
    try:
        logger.info(f"Fetching comments for post: {post_id}")
        
        comments = await db_service.get_comments_by_post(UUID(post_id))
        
        return APIResponse(
            success=True,
            message="Comments fetched successfully",
            data=comments
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch comments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch comments"
        )
