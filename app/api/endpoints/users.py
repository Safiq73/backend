from fastapi import APIRouter, Depends, HTTPException, Query, Path
from app.services.auth_service import get_current_user, get_current_user_optional
from app.services.user_service import UserService
from app.services.post_service import PostService
from app.services.representative_service import RepresentativeService
from app.models.pydantic_models import APIResponse, UserUpdate, UserResponse, UserWithRepresentativeResponse, PublicUserWithRepresentativeResponse
from typing import Dict, Any, Optional
from uuid import UUID

router = APIRouter()
user_service = UserService()
post_service = PostService()
representative_service = RepresentativeService()

@router.get("/profile", response_model=APIResponse)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile with representative information"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get full user data with role information
    user_data = await user_service.get_user_by_id(current_user["id"])
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove password_hash from response
    user_data.pop('password_hash', None)
    
    # Get all representative accounts linked to the user
    rep_accounts = await representative_service.get_user_rep_accounts(current_user["id"])
    user_data['rep_accounts'] = rep_accounts
    
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=UserWithRepresentativeResponse(**user_data)
    )


@router.get("/{user_id}", response_model=APIResponse)
async def get_user_by_id(
    user_id: UUID = Path(..., description="ID of the user to get"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get public user profile by ID"""
    # Get user data
    user_data = await user_service.get_user_by_id(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove sensitive information for public access
    user_data.pop('password_hash', None)
    user_data.pop('email', None)  # Don't expose email to other users
    
    # Get representative accounts linked to the user
    rep_accounts = await representative_service.get_user_rep_accounts(user_id)
    user_data['rep_accounts'] = rep_accounts
    
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=PublicUserWithRepresentativeResponse(**user_data)
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

@router.get("/settings/representative", response_model=APIResponse)
async def get_user_representative_settings(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user's representative account settings"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get linked representative information
    linked_rep = await representative_service.get_user_linked_representative(current_user["id"])
    
    # Get available representatives for selection
    available_reps = await representative_service.get_available_representatives()
    
    return APIResponse(
        success=True,
        message="Representative settings retrieved successfully",
        data={
            "linked_representative": linked_rep,
            "available_representatives": available_reps,
            "can_change": True  # User can always change/update their representative link
        }
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

@router.get("/settings/representative/titles", response_model=APIResponse)
async def get_available_titles(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available titles for representative linking"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        titles = await representative_service.get_available_titles()
        
        return APIResponse(
            success=True,
            message="Available titles retrieved successfully",
            data={"titles": titles}
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.get("/settings/representative/jurisdictions", response_model=APIResponse)
async def get_jurisdiction_suggestions(
    title_id: str = Query(..., description="Title ID to filter jurisdictions"),
    query: str = Query(..., min_length=1, description="Search query for jurisdiction name"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get jurisdiction suggestions based on title and search query"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        suggestions = await representative_service.get_jurisdiction_suggestions(
            title_id=title_id,
            query=query,
            limit=limit
        )
        
        return APIResponse(
            success=True,
            message="Jurisdiction suggestions retrieved successfully",
            data={"jurisdictions": suggestions}
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.get("/settings/representative/by-selection", response_model=APIResponse)
async def get_representatives_by_selection(
    title_id: str = Query(..., description="Title ID"),
    jurisdiction_id: str = Query(..., description="Jurisdiction ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available representatives for specific title and jurisdiction selection"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        representatives = await representative_service.get_representatives_by_title_and_jurisdiction(
            title_id=title_id,
            jurisdiction_id=jurisdiction_id
        )
        
        return APIResponse(
            success=True,
            message="Representatives retrieved successfully",
            data={"representatives": representatives}
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.get("/settings/representative", response_model=APIResponse)
async def get_representatives_for_settings(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
    search_query: str = Query(None, description="Search in title name, jurisdiction name, or abbreviation"),
    title_filter: str = Query(None, description="Filter by exact title name"),
    jurisdiction_name: str = Query(None, description="Filter by exact jurisdiction name"),
    jurisdiction_level: str = Query(None, description="Filter by jurisdiction level (country, state, etc.)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available representatives for user settings with filtering and pagination"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await representative_service.get_available_representatives(
            page=page,
            limit=limit,
            search_query=search_query,
            title_filter=title_filter,
            jurisdiction_name=jurisdiction_name,
            jurisdiction_level=jurisdiction_level
        )
        
        return APIResponse(
            success=True,
            message="Representatives for settings retrieved successfully",
            data={
                "representatives": result["representatives"],
                "pagination": result["pagination"]
            }
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors
