from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth_service import get_current_user
from app.services.user_service import UserService
from app.services.post_service import PostService
from app.models.pydantic_models import APIResponse, UserUpdate, UserResponse
from typing import Dict, Any

router = APIRouter()
user_service = UserService()
post_service = PostService()

@router.get("/profile", response_model=APIResponse)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get full user data with role information
    user_data = await user_service.get_user_by_id(current_user["id"])
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove password_hash from response
    user_data.pop('password_hash', None)
    
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=UserResponse(**user_data)
    )

@router.get("/posts", response_model=APIResponse)
async def get_current_user_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get posts created by the current user"""
    from uuid import UUID
    
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    user_id = current_user["id"]
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID")
    
    # Ensure user_id is a UUID object
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # Get posts by the current user
    posts = await post_service.get_posts(
        skip=(page - 1) * size,
        limit=size,
        author_id=user_id,
        current_user_id=user_id
    )        

    return APIResponse(
        success=True,
        message="User posts retrieved successfully",
        data={
            "posts": posts,
            "page": page,
            "size": size,
            "total": len(posts)
        }
    )

@router.put("/profile", response_model=APIResponse)
async def update_user_profile(
    user_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile"""
    # Update user profile
    updated_user = await user_service.update_user(
        current_user['id'], 
        user_data.dict(exclude_unset=True),
        current_user['id']
    )
    
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data={"user": updated_user}
    )

@router.post("/avatar", response_model=APIResponse)
async def upload_avatar(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload avatar (placeholder implementation)"""
    # In a real implementation, this would handle file upload
    return APIResponse(
        success=True,
        message="Avatar upload endpoint ready",
        data={"avatar_url": "https://example.com/avatar.jpg"}
    )

@router.post("/cover-photo", response_model=APIResponse)
async def upload_cover_photo(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload cover photo (placeholder implementation)"""
    # In a real implementation, this would handle file upload
    return APIResponse(
        success=True,
        message="Cover photo upload endpoint ready",
        data={"cover_photo_url": "https://example.com/cover.jpg"}
    )

@router.put("/{user_id}/role", response_model=APIResponse)
async def assign_user_role(
    user_id: str,
    role_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Assign role to user (Admin only)"""
    from uuid import UUID
    
    # TODO: Add admin permission check
    # if current_user.get('title_info', {}).get('title_name') != 'Admin':
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate UUIDs
    try:
        user_uuid = UUID(user_id)
        role_uuid = UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Update user role
    updated_user = await user_service.update_user(
        user_uuid, 
        {"role": role_uuid},
        current_user['id']
    )
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return APIResponse(
        success=True,
        message="User role assigned successfully",
        data={"user": updated_user}
    )
