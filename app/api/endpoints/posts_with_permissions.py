"""
Updated Posts API endpoints with dynamic permission system

This file demonstrates how to integrate the permission system with FastAPI endpoints.
The permission checking can be done either through middleware or dependency injection.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional, List, Dict, Any
from uuid import UUID

# Import new auth dependencies
from app.core.auth import (
    get_current_user, 
    get_current_user_optional, 
    require_permissions,
    require_roles,
    get_user_permissions
)
from app.middleware.permission_middleware import check_permission_dependency
from app.models.user import User

# Existing imports (would be adjusted based on actual structure)
from app.schemas import PostCreate, PostUpdate, PostResponse, PaginatedResponse
from app.services.post_service import PostService

router = APIRouter()
post_service = PostService()

# Method 1: Using middleware dependency for automatic permission checking
@router.get("", response_model=PaginatedResponse, dependencies=[Depends(check_permission_dependency)])
async def get_posts(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    post_type: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get posts with automatic permission checking through middleware
    
    Permission: posts.get (automatically checked by middleware)
    Public: Yes (read-only access)
    """
    try:
        user_id = current_user.id if current_user else None
        
        posts = await post_service.get_posts(
            skip=(page - 1) * size,
            limit=size,
            post_type=post_type,
            user_id=user_id
        )
        
        return posts
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch posts"
        )

# Method 2: Using explicit permission dependency
@router.post("", response_model=PostResponse, dependencies=[Depends(require_permissions("posts.post"))])
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new post
    
    Permission: posts.post (explicitly required)
    Roles: citizen, verified_citizen, representative, moderator, admin
    """
    try:
        # Add user information to post data
        post_dict = post_data.dict()
        post_dict['author_id'] = current_user.id
        
        post = await post_service.create_post(post_dict)
        return post
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )

# Method 3: Using role-based access control
@router.get("/{post_id}", response_model=PostResponse, dependencies=[Depends(check_permission_dependency)])
async def get_post(
    post_id: UUID,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get a specific post by ID
    
    Permission: posts.detail.get (automatically checked)
    Public: Yes (read-only access)
    """
    try:
        post = await post_service.get_post(
            post_id=post_id,
            user_id=current_user.id if current_user else None
        )
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return post
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post"
        )

# Method 4: Manual permission checking with custom logic
@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a post with custom permission logic
    
    Permission: posts.detail.put OR ownership check
    """
    try:
        # Get the existing post
        existing_post = await post_service.get_post(post_id)
        if not existing_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check if user owns the post or has permission to edit any post
        user_permissions = await get_user_permissions(current_user)
        
        can_edit_own = existing_post['author_id'] == current_user.id
        can_edit_any = "posts.detail.put" in user_permissions
        
        if not (can_edit_own or can_edit_any):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own posts"
            )
        
        # Update the post
        updated_post = await post_service.update_post(post_id, post_data.dict())
        return updated_post
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post"
        )

# Method 5: Role-based endpoint access
@router.delete("/{post_id}", dependencies=[Depends(require_roles("moderator", "admin"))])
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a post (moderator/admin only)
    
    Roles: moderator, admin
    """
    try:
        # Check if post exists
        existing_post = await post_service.get_post(post_id)
        if not existing_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Delete the post
        await post_service.delete_post(post_id)
        
        return {"message": "Post deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post"
        )

# Method 6: Admin-only endpoints with explicit permission checks
@router.post("/{post_id}/moderate", dependencies=[Depends(require_permissions("admin.posts.moderate.post"))])
async def moderate_post(
    post_id: UUID,
    action: str = Query(..., regex="^(approve|reject|flag)$"),
    reason: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Moderate a post (admin/moderator only)
    
    Permission: admin.posts.moderate.post
    """
    try:
        result = await post_service.moderate_post(
            post_id=post_id,
            action=action,
            reason=reason,
            moderator_id=current_user.id
        )
        
        return {
            "message": f"Post {action}ed successfully",
            "moderation_result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to moderate post"
        )

# Method 7: Endpoint that shows user's current permissions (for debugging/UI)
@router.get("/my-permissions", response_model=Dict[str, Any])
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    user_permissions: List[str] = Depends(get_user_permissions)
):
    """
    Get current user's permissions and roles (for debugging/UI)
    """
    try:
        from app.services.permission_service import PermissionService
        permission_service = PermissionService()
        
        user_roles = await permission_service.get_user_roles(current_user.id)
        
        return {
            "user_id": current_user.id,
            "username": current_user.username,
            "roles": [{"name": role.name, "display_name": role.display_name, "level": role.level} for role in user_roles],
            "permissions": user_permissions,
            "permission_count": len(user_permissions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user permissions"
        )

# Example of using conditional permissions based on content
@router.post("/{post_id}/assign")
async def assign_post_to_representative(
    post_id: UUID,
    representative_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Assign a post to a representative
    
    Conditional permissions:
    - If user is the post author: no special permission needed
    - If user is moderator/admin: requires posts.assign permission
    """
    try:
        # Get the post
        post = await post_service.get_post(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check permissions
        user_permissions = await get_user_permissions(current_user)
        is_author = post['author_id'] == current_user.id
        can_assign = "posts.assign" in user_permissions
        
        if not (is_author or can_assign):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only assign your own posts or need assign permission"
            )
        
        # Assign the post
        result = await post_service.assign_post(post_id, representative_id, current_user.id)
        
        return {
            "message": "Post assigned successfully",
            "assignment": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign post"
        )
