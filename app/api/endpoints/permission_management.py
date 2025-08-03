"""
Permission Management API Endpoints

This module provides API endpoints for managing roles, permissions, and user assignments.
These endpoints are primarily for administrators and system management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from app.core.auth import (
    get_current_user,
    require_permissions,
    require_roles,
    require_role_level
)
from app.models.user import User
from app.services.permission_service import PermissionService
from app.core.permissions import (
    API_PERMISSIONS_REGISTRY,
    get_permissions_by_category,
    DEFAULT_ROLE_PERMISSIONS
)

# Pydantic models for API
class RoleResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    level: int
    color: Optional[str]
    is_system_role: bool
    is_active: bool

class PermissionResponse(BaseModel):
    id: UUID
    route_path: str
    method: str
    permission_name: str
    description: Optional[str]
    category: str
    is_active: bool

class UserRoleAssignment(BaseModel):
    user_id: UUID
    role_name: str

class RolePermissionAssignment(BaseModel):
    role_name: str
    permission_names: List[str]

class UserPermissionSummary(BaseModel):
    user_id: UUID
    username: str
    roles: List[RoleResponse]
    permissions: List[str]
    permission_count: int

router = APIRouter()
permission_service = PermissionService()

# =============================================================================
# ROLE MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/roles", response_model=List[RoleResponse])
async def get_all_roles(
    current_user: User = Depends(require_permissions("admin.system.roles.get"))
):
    """Get all system roles (admin only)"""
    try:
        # This would need to be implemented in the permission service
        roles = await permission_service.get_all_roles()
        return roles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch roles: {str(e)}"
        )

@router.get("/roles/{role_name}/permissions", response_model=List[str])
async def get_role_permissions(
    role_name: str,
    current_user: User = Depends(require_role_level(70))  # Moderator level or higher
):
    """Get all permissions for a specific role"""
    try:
        permissions = await permission_service.get_role_permissions(role_name)
        return permissions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch role permissions: {str(e)}"
        )

# =============================================================================
# PERMISSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/permissions", response_model=List[PermissionResponse])
async def get_all_permissions(
    category: Optional[str] = Query(None, description="Filter by permission category"),
    current_user: User = Depends(require_permissions("admin.system.permissions.get"))
):
    """Get all API permissions with optional category filter (admin only)"""
    try:
        permissions = await permission_service.get_all_permissions(category)
        return permissions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch permissions: {str(e)}"
        )

@router.get("/permissions/registry", response_model=Dict[str, Any])
async def get_permission_registry(
    current_user: User = Depends(require_role_level(70))
):
    """Get the permission registry (what permissions are defined in code)"""
    try:
        categories = get_permissions_by_category()
        
        registry_data = {}
        for category, perms in categories.items():
            registry_data[category] = [
                {
                    "route_path": p.route_path,
                    "method": p.method.value,
                    "permission_name": p.permission_name,
                    "description": p.description
                }
                for p in perms
            ]
        
        return {
            "categories": registry_data,
            "total_permissions": len(API_PERMISSIONS_REGISTRY),
            "default_role_permissions": DEFAULT_ROLE_PERMISSIONS
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch permission registry: {str(e)}"
        )

@router.post("/permissions/sync")
async def sync_permissions_from_registry(
    current_user: User = Depends(require_permissions("admin.system.permissions.sync"))
):
    """Sync API permissions from code registry to database (admin only)"""
    try:
        success = await permission_service.sync_permissions_from_registry()
        if success:
            return {"message": "Permissions synced successfully from registry"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync permissions"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync permissions: {str(e)}"
        )

# =============================================================================
# USER ROLE ASSIGNMENT ENDPOINTS
# =============================================================================

@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: UUID,
    assignment: UserRoleAssignment,
    current_user: User = Depends(require_permissions("admin.users.assign_roles.post"))
):
    """Assign a role to a user (admin only)"""
    try:
        success = await permission_service.assign_role_to_user(
            user_id=assignment.user_id,
            role_name=assignment.role_name,
            assigned_by=current_user.id
        )
        
        if success:
            return {"message": f"Role '{assignment.role_name}' assigned to user successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign role"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}"
        )

@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: UUID,
    role_name: str,
    current_user: User = Depends(require_permissions("admin.users.remove_roles.delete"))
):
    """Remove a role from a user (admin only)"""
    try:
        success = await permission_service.remove_role_from_user(user_id, role_name)
        
        if success:
            return {"message": f"Role '{role_name}' removed from user successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove role or role not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}"
        )

@router.get("/users/{user_id}/permissions", response_model=UserPermissionSummary)
async def get_user_permissions_summary(
    user_id: UUID,
    current_user: User = Depends(require_role_level(70))
):
    """Get complete permission summary for a user (moderator+ only)"""
    try:
        # Check if requesting user can view this information
        if current_user.id != user_id:
            # Only moderators and above can view other users' permissions
            user_permissions = await permission_service.get_user_permissions(current_user.id)
            if not any(p.startswith("admin.") or p.startswith("moderate.") for p in user_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own permissions"
                )
        
        # Get user roles and permissions
        user_roles = await permission_service.get_user_roles(user_id)
        user_permissions = await permission_service.get_user_permissions(user_id)
        
        # Get user info (you'd need to implement this)
        # user_info = await user_service.get_user_by_id(user_id)
        
        return UserPermissionSummary(
            user_id=user_id,
            username="user",  # Would get from user_info
            roles=[
                RoleResponse(
                    id=role.id,
                    name=role.name,
                    display_name=role.display_name,
                    description=role.description,
                    level=role.level,
                    color=role.color,
                    is_system_role=role.is_system_role,
                    is_active=role.is_active
                )
                for role in user_roles
            ],
            permissions=user_permissions,
            permission_count=len(user_permissions)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user permissions: {str(e)}"
        )

# =============================================================================
# CURRENT USER PERMISSION ENDPOINTS
# =============================================================================

@router.get("/my/permissions", response_model=UserPermissionSummary)
async def get_my_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get current user's permissions and roles"""
    try:
        user_roles = await permission_service.get_user_roles(current_user.id)
        user_permissions = await permission_service.get_user_permissions(current_user.id)
        
        return UserPermissionSummary(
            user_id=current_user.id,
            username=current_user.username,
            roles=[
                RoleResponse(
                    id=role.id,
                    name=role.name,
                    display_name=role.display_name,
                    description=role.description,
                    level=role.level,
                    color=role.color,
                    is_system_role=role.is_system_role,
                    is_active=role.is_active
                )
                for role in user_roles
            ],
            permissions=user_permissions,
            permission_count=len(user_permissions)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get your permissions: {str(e)}"
        )

@router.get("/my/permissions/check/{permission_name}")
async def check_my_permission(
    permission_name: str,
    current_user: User = Depends(get_current_user)
):
    """Check if current user has a specific permission"""
    try:
        has_permission = await permission_service.user_has_permission(
            current_user.id, permission_name
        )
        
        return {
            "permission": permission_name,
            "granted": has_permission,
            "user_id": current_user.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check permission: {str(e)}"
        )

# =============================================================================
# PERMISSION ANALYSIS ENDPOINTS (for debugging/admin)
# =============================================================================

@router.get("/analysis/unused-permissions")
async def get_unused_permissions(
    current_user: User = Depends(require_permissions("admin.system.analysis.get"))
):
    """Get permissions that exist in registry but aren't assigned to any role"""
    try:
        # Get all permissions from registry
        registry_permissions = {p.permission_name for p in API_PERMISSIONS_REGISTRY}
        
        # Get all assigned permissions
        assigned_permissions = set()
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            role_perms = await permission_service.get_role_permissions(role_name)
            assigned_permissions.update(role_perms)
        
        unused_permissions = registry_permissions - assigned_permissions
        
        return {
            "unused_permissions": list(unused_permissions),
            "total_registry_permissions": len(registry_permissions),
            "total_assigned_permissions": len(assigned_permissions),
            "unused_count": len(unused_permissions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze permissions: {str(e)}"
        )

@router.get("/analysis/role-hierarchy")
async def get_role_hierarchy(
    current_user: User = Depends(require_role_level(70))
):
    """Get role hierarchy and permission inheritance analysis"""
    try:
        # This would analyze the role hierarchy and show permission inheritance
        from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, expand_role_permissions
        
        hierarchy = {}
        for role_name, role_perms in DEFAULT_ROLE_PERMISSIONS.items():
            expanded_perms = expand_role_permissions(role_perms)
            hierarchy[role_name] = {
                "declared_permissions": role_perms,
                "expanded_permissions": list(expanded_perms),
                "total_permissions": len(expanded_perms)
            }
        
        return {
            "role_hierarchy": hierarchy,
            "roles_by_permission_count": sorted(
                [(role, data["total_permissions"]) for role, data in hierarchy.items()],
                key=lambda x: x[1],
                reverse=True
            )
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze role hierarchy: {str(e)}"
        )
