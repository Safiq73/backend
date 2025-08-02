"""
Follow API endpoints for user follow/unfollow functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from app.services.auth_service import get_current_user
from app.services.follow_service import FollowService
from app.models.pydantic_models import (
    APIResponse, 
    FollowResponse, 
    UnfollowResponse,
    FollowersListResponse, 
    FollowingListResponse,
    FollowStatsResponse
)
from typing import Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
follow_service = FollowService()

def get_user_uuid(user_id) -> UUID:
    """Helper function to convert user ID to UUID if needed"""
    if isinstance(user_id, str):
        return UUID(user_id)
    return user_id

@router.post("/users/{user_id}/follow", response_model=APIResponse)
async def follow_user(
    user_id: UUID = Path(..., description="ID of the user to follow"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Follow a user"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Handle both string and UUID types for current_user["id"]
    follower_id = get_user_uuid(current_user["id"])
    
    # Follow the user
    result = await follow_service.follow_user(follower_id, user_id)
    
    return APIResponse(
        success=True,
        message=result['message'],
        data=FollowResponse(
            success=result['success'],
            message=result['message'],
            mutual=result['mutual']
        )
    )

@router.delete("/users/{user_id}/unfollow", response_model=APIResponse)
async def unfollow_user(
    user_id: UUID = Path(..., description="ID of the user to unfollow"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Unfollow a user"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Handle both string and UUID types for current_user["id"]
    follower_id = current_user["id"]
    if isinstance(follower_id, str):
        follower_id = UUID(follower_id)
    
    # Unfollow the user
    result = await follow_service.unfollow_user(follower_id, user_id)
    
    return APIResponse(
        success=True,
        message=result['message'],
        data=UnfollowResponse(
            success=result['success'],
            message=result['message']
        )
    )

@router.get("/users/{user_id}/followers", response_model=APIResponse)
async def get_user_followers(
    user_id: UUID = Path(..., description="ID of the user to get followers for"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Number of followers per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get list of users following the specified user"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get followers
    result = await follow_service.get_followers(user_id, page, size)
    
    return APIResponse(
        success=True,
        message=f"Followers retrieved successfully",
        data=FollowersListResponse(**result)
    )

@router.get("/users/{user_id}/following", response_model=APIResponse)
async def get_user_following(
    user_id: UUID = Path(..., description="ID of the user to get following list for"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Number of following per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get list of users that the specified user is following"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get following
    result = await follow_service.get_following(user_id, page, size)
    
    return APIResponse(
        success=True,
        message=f"Following list retrieved successfully",
        data=FollowingListResponse(**result)
    )

@router.get("/users/{user_id}/follow-stats", response_model=APIResponse)
async def get_user_follow_stats(
    user_id: UUID = Path(..., description="ID of the user to get follow stats for"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get follow statistics for a user"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get follow stats
    result = await follow_service.get_follow_stats(user_id)
    
    return APIResponse(
        success=True,
        message="Follow statistics retrieved successfully",
        data=FollowStatsResponse(**result)
    )

@router.get("/users/{user_id}/follow-status", response_model=APIResponse)
async def check_follow_status(
    user_id: UUID = Path(..., description="ID of the user to check follow status with"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Check follow status between current user and specified user"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Handle both string and UUID types for current_user["id"]
    current_user_id = current_user["id"]
    if isinstance(current_user_id, str):
        current_user_id = UUID(current_user_id)
    
    # Check follow status
    result = await follow_service.check_follow_status(current_user_id, user_id)
    
    return APIResponse(
        success=True,
        message="Follow status retrieved successfully",
        data=result
    )
