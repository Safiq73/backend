"""
Role management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from uuid import UUID

from app.models.pydantic_models import RoleCreate, RoleUpdate, RoleResponse, APIResponse
from app.services.db_service import DatabaseService
from app.services.auth_service import get_current_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="", tags=["roles"])

# Initialize database service
db_service = DatabaseService()

@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new role (Admin only)"""
    try:
        # TODO: Add admin permission check
        # if current_user.get('role_info', {}).get('role_name') != 'Admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        role_dict = role_data.model_dump()
        created_role = await db_service.create_role(role_dict)
        
        logger.info(f"Role created successfully | ID: {created_role['id']} | Name: {created_role['role_name']}")
        
        return APIResponse(
            success=True,
            message="Role created successfully",
            data=RoleResponse(**created_role)
        )
    
    except ValueError as e:
        logger.warning(f"Role creation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during role creation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=APIResponse)
async def get_all_roles():
    """Get all active roles"""
    try:
        roles = await db_service.get_all_roles()
        role_responses = [RoleResponse(**role) for role in roles]
        
        return APIResponse(
            success=True,
            message="Roles retrieved successfully",
            data=role_responses
        )
    
    except Exception as e:
        logger.error(f"Error retrieving roles: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{role_id}", response_model=APIResponse)
async def get_role(role_id: UUID):
    """Get role by ID"""
    try:
        role = await db_service.get_role_by_id(role_id)
        
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return APIResponse(
            success=True,
            message="Role retrieved successfully",
            data=RoleResponse(**role)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving role {role_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{role_id}", response_model=APIResponse)
async def update_role(
    role_id: UUID,
    role_update: RoleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update role (Admin only)"""
    try:
        # TODO: Add admin permission check
        # if current_user.get('role_info', {}).get('role_name') != 'Admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if role exists
        existing_role = await db_service.get_role_by_id(role_id)
        if not existing_role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        # Update role
        update_data = role_update.model_dump(exclude_unset=True)
        updated_role = await db_service.update_role(role_id, update_data)
        
        logger.info(f"Role updated successfully | ID: {role_id}")
        
        return APIResponse(
            success=True,
            message="Role updated successfully",
            data=RoleResponse(**updated_role)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role {role_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{role_id}", response_model=APIResponse)
async def delete_role(
    role_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Delete role (Admin only)"""
    try:
        # TODO: Add admin permission check
        # if current_user.get('role_info', {}).get('role_name') != 'Admin':
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if role exists
        existing_role = await db_service.get_role_by_id(role_id)
        if not existing_role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        # TODO: Check if any users are assigned to this role
        # if users_with_role:
        #     raise HTTPException(status_code=400, detail="Cannot delete role with assigned users")
        
        success = await db_service.delete_role(role_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete role")
        
        logger.info(f"Role deleted successfully | ID: {role_id}")
        
        return APIResponse(
            success=True,
            message="Role deleted successfully",
            data=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role {role_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
