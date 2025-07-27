"""
Representative management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.models.pydantic_models import (
    RepresentativeResponse, 
    RepresentativeWithDetails,
    RepresentativeLinkRequest, 
    UserWithRepresentativeResponse,
    APIResponse
)
from app.services.representative_service import RepresentativeService
from app.services.user_service import UserService
from app.services.auth_service import get_current_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="", tags=["representatives"])

# Initialize services
representative_service = RepresentativeService()
user_service = UserService()

@router.get("/available", response_model=APIResponse)
async def get_available_representatives(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
    search_query: Optional[str] = Query(None, description="Search in title name, jurisdiction name, or abbreviation"),
    title_filter: Optional[str] = Query(None, description="Filter by exact title name"),
    jurisdiction_name: Optional[str] = Query(None, description="Filter by exact jurisdiction name"),
    jurisdiction_level: Optional[str] = Query(None, description="Filter by jurisdiction level (country, state, etc.)")
):
    """Get available (unclaimed) representative accounts with filtering and pagination"""

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
        message="Available representatives retrieved successfully",
        data={
            "representatives": [RepresentativeResponse(**rep) for rep in result["representatives"]],
            "pagination": result["pagination"]
        }
    )
    

@router.get("/{rep_id}", response_model=APIResponse)
async def get_representative(rep_id: UUID):
    """Get representative by ID"""
    representative = await representative_service.get_representative_by_id(rep_id)
    
    if not representative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Representative not found"
        )
    
    return APIResponse(
        success=True,
        message="Representative retrieved successfully",
        data=RepresentativeResponse(**representative)
    )

@router.get("/user/{user_id}/linked", response_model=APIResponse)
async def get_user_linked_representative(
    user_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the representative account linked to a user (Admin or self only)"""
    # Check if user is accessing their own data or is admin
    if str(user_id) != current_user["id"]:
        # TODO: Add admin role check here
        # For now, allow any authenticated user to check
        pass
    
    linked_rep = await representative_service.get_user_linked_representative(user_id)
    
    return APIResponse(
        success=True,
        message="Linked representative retrieved successfully",
        data={
            "representative": RepresentativeResponse(**linked_rep) if linked_rep else None
        }
    )
    
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.post("/link", response_model=APIResponse)
async def link_representative_to_user(
    link_request: RepresentativeLinkRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):  
    """Link current user to a representative account"""
    user_id = current_user["id"]
    
    # Link the user to the representative
    user_data = await representative_service.link_user_to_representative(
        user_id, 
        link_request.representative_id
    )
    
    # Get the representative details
    rep_details = await representative_service.get_representative_with_details(link_request.representative_id)
    
    return APIResponse(
        success=True,
        message="Representative account linked successfully",
        data={
            "user": UserWithRepresentativeResponse(**user_data) if user_data else None,
            "representative": RepresentativeWithDetails(**rep_details) if rep_details else None
        }
    )

@router.put("/link", response_model=APIResponse)
async def update_user_representative_link(
    link_request: RepresentativeLinkRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):  
    """Update current user's linked representative account"""
    user_id = current_user["id"]
    
    # Update the user's linked representative
    user_data = await representative_service.update_user_representative(
        user_id, 
        link_request.representative_id
    )
    
    # Get the representative details
    rep_details = await representative_service.get_representative_with_details(link_request.representative_id)
    
    return APIResponse(
        success=True,
        message="Representative link updated successfully",
        data={
            "user": UserWithRepresentativeResponse(**user_data) if user_data else None,
            "representative": RepresentativeWithDetails(**rep_details) if rep_details else None
        }
    )
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.delete("/link", response_model=APIResponse)
async def unlink_representative_from_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Unlink current user from their representative account"""
    user_id = current_user["id"]
    
    # Unlink the user from their representative
    success = await representative_service.unlink_user_from_representative(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink representative account"
        )
    
    # Get updated user data
    user_data = await user_service.get_user_by_id(user_id)
    
    return APIResponse(
        success=True,
        message="Representative account unlinked successfully",
        data={
            "user": UserWithRepresentativeResponse(**user_data) if user_data else None
        }
    )
    # Remove generic Exception catch - let FastAPI handle unexpected errors
