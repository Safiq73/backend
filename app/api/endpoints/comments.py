from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.services.auth_service import get_current_user_optional, get_current_user
from app.services.comment_service import CommentService

router = APIRouter()
comment_service = CommentService()

class CreateCommentRequest(BaseModel):
    content: str
    post_id: str
    parent_id: Optional[str] = None

class UpdateCommentRequest(BaseModel):
    content: str

class CommentResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
    error: Optional[str] = None

@router.post("")
async def create_comment(
    comment_data: CreateCommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new comment"""
    try:
        # Handle case where user_id might already be a UUID object
        user_id = current_user['id']
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        comment_dict = {
            'content': comment_data.content,
            'post_id': UUID(comment_data.post_id),
            'parent_id': UUID(comment_data.parent_id) if comment_data.parent_id else None
        }
        
        comment = await comment_service.create_comment(comment_dict, user_id)
        return comment
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{comment_id}")
async def get_comment(
    comment_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get a specific comment by ID"""
    try:
        comment_uuid = UUID(comment_id)
        user_id = None
        if current_user:
            user_id = current_user['id']
            if isinstance(user_id, str):
                user_id = UUID(user_id)
        
        comment = await comment_service.get_comment_by_id(comment_uuid, user_id)
        return comment
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comment ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{comment_id}")
async def update_comment(
    comment_id: str,
    comment_data: UpdateCommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a comment (only by the author)"""
    try:
        comment_uuid = UUID(comment_id)
        user_id = current_user['id']
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        comment_dict = {'content': comment_data.content}
        comment = await comment_service.update_comment(comment_uuid, comment_dict, user_id)
        return comment
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comment ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a comment (only by the author)"""
    try:
        comment_uuid = UUID(comment_id)
        user_id = current_user['id']
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        success = await comment_service.delete_comment(comment_uuid, user_id)
        return CommentResponse(
            success=success,
            message="Comment deleted successfully" if success else "Failed to delete comment"
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comment ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{comment_id}/vote")
async def vote_on_comment(
    comment_id: str,
    vote_type: str = Query(..., description="Vote type: 'up' or 'down'"),
    current_user: dict = Depends(get_current_user)
):
    """Vote on a comment (upvote/downvote)"""
    try:
        comment_uuid = UUID(comment_id)
        user_id = current_user['id']
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        # Convert 'up'/'down' to 'upvote'/'downvote' like posts
        if vote_type == 'up':
            vote_type = 'upvote'
        elif vote_type == 'down':
            vote_type = 'downvote'
        else:
            raise HTTPException(status_code=400, detail="Vote type must be 'up' or 'down'")
        
        result = await comment_service.vote_on_comment(comment_uuid, vote_type, user_id)
        return CommentResponse(
            success=result['success'],
            data=result,
            message=f"Successfully voted {vote_type} on comment"
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comment ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoint for upvoting (to match frontend expectations)
@router.post("/{comment_id}/upvote")
async def upvote_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Upvote a comment (legacy endpoint)"""
    return await vote_on_comment(comment_id, "up", current_user)
