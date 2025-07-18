from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import get_current_user
from app.services.user_service import UserService
from app.schemas import APIResponse, UserUpdate
from typing import Dict, Any

router = APIRouter()
user_service = UserService()

@router.get("/profile", response_model=Dict[str, Any])
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "id": current_user["id"],
        "email": current_user["email"], 
        "username": current_user.get("username", current_user.get("name")),  # Support both fields
        "display_name": current_user.get("display_name", current_user.get("name")),  # Support both fields
        "role": current_user["role"],
        "bio": current_user.get("bio", current_user.get("area")),  # Support both fields
        "avatar_url": current_user.get("avatar_url", current_user.get("avatar")),  # Support both fields
        "cover_photo": current_user.get("cover_photo"),
        "created_at": current_user.get("created_at"),
        "updated_at": current_user.get("updated_at")
    }

@router.put("/profile", response_model=APIResponse)
async def update_user_profile(
    user_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile"""
    try:
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update profile: {str(e)}"
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
