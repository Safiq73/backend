"""
Comments API endpoints for CivicPulse
Provides comprehensive comment management with proper validation and error handling
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from uuid import UUID
import re

# Local imports
from app.schemas import APIResponse
from app.models.pydantic_models import (
    CommentCreate, CommentUpdate, CommentResponse, 
    VoteCreate, VoteType, PaginatedResponse
)
from app.services.comment_service import CommentService
from app.services.auth_service import get_current_user, get_current_user_optional
from app.core.logging_config import get_logger

# Initialize router and services
router = APIRouter(tags=["comments"])
comment_service = CommentService()
logger = get_logger('app.api.comments')


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new comment on a post
    
    - **post_id**: UUID of the post to comment on
    - **content**: Comment content (1-2000 characters)
    - **parent_id**: Optional UUID for reply to another comment
    """
    try:
        user_id = current_user['id']
        logger.info(f"Creating comment | Post: {comment_data.post_id} | User: {user_id} | Content: {comment_data.content[:50]}...")
        
        # Additional validation
        if not comment_data.post_id:
            raise ValueError("post_id is required")
        if not comment_data.content or not comment_data.content.strip():
            raise ValueError("content is required and cannot be empty")
        
        comment = await comment_service.create_comment(comment_data, user_id)
        
        logger.info(f"Comment created successfully | ID: {comment.id}")
        return comment
        
    except ValueError as e:
        logger.warning(f"Invalid comment data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to create comment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("", response_model=PaginatedResponse[CommentResponse])
async def get_comments_paginated(
    post_id: UUID = Query(..., description="UUID of the post"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Comments per page"),
    sort_by: str = Query("created_at", regex="^(created_at|upvotes|reply_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Get comments for a specific post with pagination and sorting (query parameter version)
    
    - **post_id**: UUID of the post (query parameter)
    - **page**: Page number (starts from 1)
    - **size**: Number of comments per page (1-100)
    - **sort_by**: Sort field (created_at, upvotes, reply_count)
    - **sort_order**: Sort order (asc, desc)
    """
    try:
        user_id = UUID(current_user['id']) if current_user else None
        logger.info(f"Fetching comments for post: {post_id} | Page: {page} | Size: {size}")
        
        comments = await comment_service.get_comments_by_post(
            post_id=post_id,
            current_user_id=user_id,
            page=page,
            size=size,
            sort_by=sort_by,
            order=sort_order
        )
        
        return comments
        
    except ValueError as e:
        logger.warning(f"Invalid request parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to fetch comments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch comments"
        )


@router.get("/post/{post_id}", response_model=PaginatedResponse[CommentResponse])
async def get_comments_by_post(
    post_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Comments per page"),
    sort_by: str = Query("created_at", regex="^(created_at|upvotes|reply_count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Get comments for a specific post with pagination and sorting
    
    - **post_id**: UUID of the post
    - **page**: Page number (starts from 1)
    - **size**: Number of comments per page (1-100)
    - **sort_by**: Sort field (created_at, upvotes, reply_count)
    - **order**: Sort order (asc, desc)
    """
    try:
        user_id = UUID(current_user['id']) if current_user else None
        logger.info(f"Fetching comments for post: {post_id} | Page: {page} | Size: {size}")
        
        comments = await comment_service.get_comments_by_post(
            post_id=post_id,
            current_user_id=user_id,
            page=page,
            size=size,
            sort_by=sort_by,
            order=order
        )
        
        return comments
        
    except ValueError as e:
        logger.warning(f"Invalid request parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to fetch comments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch comments"
        )


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: UUID,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Get a specific comment by ID
    
    - **comment_id**: UUID of the comment
    """
    try:
        user_id = UUID(current_user['id']) if current_user else None
        logger.info(f"Fetching comment: {comment_id}")
        
        comment = await comment_service.get_comment_by_id(comment_id, user_id)
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        return comment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch comment"
        )


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    comment_data: CommentUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a comment (only by the comment author)
    
    - **comment_id**: UUID of the comment to update
    - **content**: New comment content (1-2000 characters)
    """
    try:
        user_id = UUID(current_user['id'])
        logger.info(f"Updating comment: {comment_id} | User: {user_id}")
        
        comment = await comment_service.update_comment(comment_id, comment_data, user_id)
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or not authorized to update"
            )
        
        logger.info(f"Comment updated successfully | ID: {comment_id}")
        return comment
        
    except ValueError as e:
        logger.warning(f"Invalid comment update data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a comment (only by the comment author)
    
    - **comment_id**: UUID of the comment to delete
    """
    try:
        user_id = UUID(current_user['id'])
        logger.info(f"Deleting comment: {comment_id} | User: {user_id}")
        
        success = await comment_service.delete_comment(comment_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or not authorized to delete"
            )
        
        logger.info(f"Comment deleted successfully | ID: {comment_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )


@router.get("/{comment_id}/replies", response_model=PaginatedResponse[CommentResponse])
async def get_comment_replies(
    comment_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Get replies to a specific comment
    
    - **comment_id**: UUID of the parent comment
    - **page**: Page number (starts from 1)
    - **size**: Number of replies per page (1-50)
    """
    try:
        user_id = UUID(current_user['id']) if current_user else None
        logger.info(f"Fetching replies for comment: {comment_id}")
        
        replies = await comment_service.get_comment_replies(
            comment_id=comment_id,
            current_user_id=user_id,
            page=page,
            size=size
        )
        
        return replies
        
    except Exception as e:
        logger.error(f"Failed to fetch replies for comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch comment replies"
        )


@router.post("/{comment_id}/vote", response_model=APIResponse)
async def vote_on_comment(
    comment_id: UUID,
    vote_data: VoteCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Vote on a comment (upvote/downvote)
    
    - **comment_id**: UUID of the comment to vote on
    - **vote_type**: "upvote" or "downvote"
    """
    try:
        user_id = UUID(current_user['id'])
        logger.info(f"Voting on comment: {comment_id} | User: {user_id} | Vote: {vote_data.vote_type}")
        
        result = await comment_service.vote_on_comment(comment_id, vote_data.vote_type, user_id)
        
        return APIResponse(
            success=True,
            message=f"Successfully {vote_data.vote_type}d comment",
            data=result
        )
        
    except ValueError as e:
        logger.warning(f"Invalid vote data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to vote on comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to vote on comment"
        )


@router.delete("/{comment_id}/vote", response_model=APIResponse)
async def remove_vote_from_comment(
    comment_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Remove vote from a comment
    
    - **comment_id**: UUID of the comment to remove vote from
    """
    try:
        user_id = UUID(current_user['id'])
        logger.info(f"Removing vote from comment: {comment_id} | User: {user_id}")
        
        result = await comment_service.remove_vote_from_comment(comment_id, user_id)
        
        return APIResponse(
            success=True,
            message="Vote removed successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Failed to remove vote from comment {comment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove vote from comment"
        )
