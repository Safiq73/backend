"""
Example: Integrating Permissions into CivicPulse Posts API

This file demonstrates how to add permission checks to existing API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File
from typing import Optional, List, Dict, Any
from uuid import UUID

# Import permission decorators
from app.core.permission_decorators import (
    require_permissions, 
    require_role,
    check_user_permission,
    user_has_admin_role,
    get_current_user_for_permissions,
    get_current_user_required_for_permissions
)

# Create router for examples
router = APIRouter()

# Example 1: Using dependency injection for permission checks
@router.get("/example-posts", response_model=Dict[str, Any])
async def get_posts_with_permission_check(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    # This will check if user has 'posts.get' permission before allowing access
    current_user: Dict[str, Any] = Depends(require_permissions('posts.get', fail_open=True))
):
    """
    Example endpoint that requires 'posts.get' permission
    
    If user doesn't have permission, returns 403 Forbidden
    If permission system fails, allows access (fail_open=True)
    """
    user_id = current_user['id'] if current_user else None
    
    # Your existing posts logic here
    return {
        "message": "Posts retrieved successfully",
        "user_id": str(user_id) if user_id else None,
        "has_permission": True
    }

# Example 2: Creating posts with permission check
@router.post("/example-posts", response_model=Dict[str, Any])
async def create_post_with_permission_check(
    title: str = Form(..., min_length=1, max_length=500),
    content: str = Form(..., min_length=1, max_length=10000),
    post_type: str = Form(...),
    # Require 'posts.post' permission to create posts
    current_user: Dict[str, Any] = Depends(require_permissions('posts.post', fail_open=True))
):
    """
    Example endpoint that requires 'posts.post' permission to create posts
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create posts"
        )
    
    user_id = UUID(str(current_user['id']))
    
    # Your existing post creation logic here
    return {
        "message": "Post created successfully",
        "user_id": str(user_id),
        "title": title,
        "post_type": post_type
    }

# Example 3: Admin-only endpoint
@router.delete("/example-posts/{post_id}")
async def delete_post_admin_only(
    post_id: str,
    # Only admins can delete posts
    current_user: Dict[str, Any] = Depends(require_role('admin', fail_open=False))
):
    """
    Example endpoint that requires admin role to delete posts
    fail_open=False means if permission system fails, deny access
    """
    return {
        "message": f"Post {post_id} deleted by admin",
        "admin_user": current_user['username']
    }

# Example 4: Programmatic permission checking within endpoint
@router.put("/example-posts/{post_id}")
async def update_post_with_ownership_check(
    post_id: str,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_for_permissions)
):
    """
    Example showing programmatic permission checking
    Users can update their own posts, or admins can update any post
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user_id = UUID(str(current_user['id']))
    
    # Check if user can update this specific post
    can_update_any = await check_user_permission(user_id, 'posts.detail.put')
    is_admin = await user_has_admin_role(user_id)
    
    # Here you would check if user owns the post
    # post_owner_id = await get_post_owner(post_id)
    # user_owns_post = (post_owner_id == user_id)
    
    if not (can_update_any or is_admin):  # or user_owns_post
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own posts"
        )
    
    return {
        "message": f"Post {post_id} updated successfully",
        "updated_by": current_user['username'],
        "can_update_any": can_update_any,
        "is_admin": is_admin
    }

# Example 5: Multiple permission checks
@router.get("/example-analytics")
async def get_analytics_data(
    # Requires both analytics viewing AND posts viewing permissions
    current_user: Dict[str, Any] = Depends(require_permissions('analytics.get', 'posts.get', fail_open=True))
):
    """
    Example endpoint requiring multiple permissions
    """
    if not current_user:
        return {"message": "Public analytics data only"}
    
    return {
        "message": "Full analytics data",
        "user": current_user['username'],
        "permissions": ["analytics.get", "posts.get"]
    }

# Example 6: Moderator-level access
@router.post("/example-posts/{post_id}/moderate")
async def moderate_post(
    post_id: str,
    action: str = Form(...),  # 'approve', 'reject', 'flag'
    reason: Optional[str] = Form(None),
    # Moderators, admins, and super_admins can moderate
    current_user: Dict[str, Any] = Depends(require_role('moderator', fail_open=False))
):
    """
    Example moderator action requiring moderator role or higher
    """
    return {
        "message": f"Post {post_id} moderated with action: {action}",
        "moderator": current_user['username'],
        "reason": reason
    }
