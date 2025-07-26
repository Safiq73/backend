"""
Title management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from uuid import UUID

from app.models.pydantic_models import TitleCreate, TitleUpdate, TitleResponse, APIResponse
from app.services.db_service import DatabaseService
from app.services.auth_service import get_current_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="", tags=["titles"])

# Initialize database service
db_service = DatabaseService()

@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_title(
    title_data: TitleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new title (Admin only)"""
    try:
        # TODO: Add admin permission check
        # if current_user.get('title_info', {}).get('title_name') != 'Admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        title_dict = title_data.model_dump()
        created_title = await db_service.create_title(title_dict)
        
        logger.info(f"Title created successfully | ID: {created_title['id']} | Name: {created_title['title_name']}")
        
        return APIResponse(
            success=True,
            message="Title created successfully",
            data=TitleResponse(**created_title)
        )
    
    except ValueError as e:
        logger.warning(f"Role creation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during role creation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=APIResponse)
async def get_all_titles():
    """Get all active titles"""
    try:
        titles = await db_service.get_all_titles()
        title_responses = [TitleResponse(**title) for title in titles]
        
        return APIResponse(
            success=True,
            message="Titles retrieved successfully",
            data=title_responses
        )
    
    except Exception as e:
        logger.error(f"Error retrieving titles: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{title_id}", response_model=APIResponse)
async def get_title(title_id: UUID):
    """Get title by ID"""
    try:
        title = await db_service.get_title_by_id(title_id)
        
        if not title:
            raise HTTPException(status_code=404, detail="Title not found")
        
        return APIResponse(
            success=True,
            message="Title retrieved successfully",
            data=TitleResponse(**title)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving title {title_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{title_id}", response_model=APIResponse)
async def update_title(
    title_id: UUID,
    title_update: TitleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update role (Admin only)"""
    try:
        # TODO: Add admin permission check
        # if current_user.get('title_info', {}).get('title_name') != 'Admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if title exists
        existing_title = await db_service.get_title_by_id(title_id)
        if not existing_title:
            raise HTTPException(status_code=404, detail="Title not found")
        
        # Update title
        update_data = title_update.model_dump(exclude_unset=True)
        updated_title = await db_service.update_title(title_id, update_data)
        
        logger.info(f"Title updated successfully | ID: {title_id}")
        
        return APIResponse(
            success=True,
            message="Title updated successfully",
            data=TitleResponse(**updated_title)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating title {title_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{title_id}", response_model=APIResponse)
async def delete_title(
    title_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Delete title (Admin only)"""
    try:
        # TODO: Add admin permission check
        # if current_user.get('title_info', {}).get('title_name') != 'Admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if title exists
        existing_title = await db_service.get_title_by_id(title_id)
        if not existing_title:
            raise HTTPException(status_code=404, detail="Title not found")
        
        # TODO: Check if any users are assigned to this title
        # if users_with_title:
        #     raise HTTPException(status_code=400, detail="Cannot delete title with assigned users")
        
        success = await db_service.delete_title(title_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete title")
        
        logger.info(f"Title deleted successfully | ID: {title_id}")
        
        return APIResponse(
            success=True,
            message="Title deleted successfully",
            data=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting title {title_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
