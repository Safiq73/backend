"""
Permission Decorators for CivicPulse API

This module provides decorators for protecting API endpoints with the permission system.
Compatible with existing CivicPulse authentication system.
"""

from functools import wraps
from typing import List, Optional, Callable, Any, Dict
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from uuid import UUID

from app.services.simple_permission_service import permission_service
from app.services.auth_service import get_current_user, get_current_user_optional  # Use existing auth functions
from app.models.pydantic_models import UserResponse

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

class PermissionError(HTTPException):
    """Custom exception for permission errors"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

# FastAPI dependency to get current user (using existing auth system)
async def get_current_user_for_permissions(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user from token, returns None if not authenticated
    """
    if not credentials:
        return None
    
    try:
        # Use your existing get_current_user_optional function
        return await get_current_user_optional(credentials)
    except Exception as e:
        logger.debug(f"Authentication failed: {e}")
        return None

async def get_current_user_required_for_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user from token, raises error if not authenticated
    """
    try:
        # Use your existing get_current_user function
        return await get_current_user(credentials)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def require_permission(permission_name: str, fail_open: bool = True):
    """
    Decorator to require a specific permission for an endpoint
    
    Args:
        permission_name: The permission required (e.g., 'posts.get')
        fail_open: If True, allows access when permission system fails
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get current user from kwargs (injected by FastAPI dependencies)
            current_user = kwargs.get('current_user')
            
            if not current_user:
                if fail_open:
                    logger.warning(f"Permission check bypassed - no current user for {permission_name}")
                    return await func(*args, **kwargs)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
            
            try:
                # Check if user has the required permission
                user_id = current_user.get('id')
                if not user_id:
                    raise ValueError("User ID not found")
                
                has_permission = await permission_service.user_has_permission(
                    UUID(str(user_id)), permission_name
                )
                
                if not has_permission:
                    logger.warning(f"User {user_id} denied access to {permission_name}")
                    raise PermissionError(f"Permission '{permission_name}' required")
                
                logger.debug(f"User {user_id} granted access to {permission_name}")
                return await func(*args, **kwargs)
                
            except Exception as e:
                if isinstance(e, (HTTPException, PermissionError)):
                    raise
                
                logger.error(f"Permission check failed for {permission_name}: {e}")
                if fail_open:
                    logger.warning(f"Permission check bypassed due to error: {e}")
                    return await func(*args, **kwargs)
                else:
                    raise PermissionError("Permission check failed")
        
        return wrapper
    return decorator

def require_permissions(*permission_names: str, fail_open: bool = True):
    """
    FastAPI dependency factory to require multiple permissions
    
    Args:
        permission_names: List of required permissions
        fail_open: If True, allows access when permission system fails
    """
    async def check_permissions(
        current_user: Optional[Dict[str, Any]] = Depends(get_current_user_for_permissions)
    ) -> Optional[Dict[str, Any]]:
        if not current_user:
            if fail_open:
                return None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        try:
            user_id = UUID(str(current_user.get('id')))
            for permission_name in permission_names:
                has_permission = await permission_service.user_has_permission(
                    user_id, permission_name
                )
                if not has_permission:
                    raise PermissionError(f"Permission '{permission_name}' required")
            
            return current_user
            
        except Exception as e:
            if isinstance(e, (HTTPException, PermissionError)):
                raise
            
            logger.error(f"Permission check failed: {e}")
            if fail_open:
                return current_user
            else:
                raise PermissionError("Permission check failed")
    
    return check_permissions

def require_role(role_name: str, fail_open: bool = True):
    """
    FastAPI dependency factory to require a specific role
    
    Args:
        role_name: The role required (e.g., 'admin')
        fail_open: If True, allows access when permission system fails
    """
    async def check_role(
        current_user: Optional[Dict[str, Any]] = Depends(get_current_user_for_permissions)
    ) -> Optional[Dict[str, Any]]:
        if not current_user:
            if fail_open:
                return None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        try:
            user_id = UUID(str(current_user.get('id')))
            user_roles = await permission_service.get_user_roles(user_id)
            role_names = [role['name'] for role in user_roles]
            
            if role_name not in role_names:
                raise PermissionError(f"Role '{role_name}' required")
            
            return current_user
            
        except Exception as e:
            if isinstance(e, (HTTPException, PermissionError)):
                raise
            
            logger.error(f"Role check failed: {e}")
            if fail_open:
                return current_user
            else:
                raise PermissionError("Role check failed")
    
    return check_role

# Helper functions for programmatic permission checks
async def check_user_permission(user_id: UUID, permission_name: str) -> bool:
    """Check permissions programmatically within endpoints"""
    try:
        return await permission_service.user_has_permission(user_id, permission_name)
    except Exception as e:
        logger.error(f"Permission check failed for user {user_id}, permission {permission_name}: {e}")
        return False

async def user_has_role(user_id: UUID, role_name: str) -> bool:
    """Check if user has a specific role"""
    try:
        user_roles = await permission_service.get_user_roles(user_id)
        return any(role['name'] == role_name for role in user_roles)
    except Exception as e:
        logger.error(f"Role check failed for user {user_id}, role {role_name}: {e}")
        return False

async def user_has_admin_role(user_id: UUID) -> bool:
    """Check if user has admin or super_admin role"""
    return (await user_has_role(user_id, 'admin') or 
            await user_has_role(user_id, 'super_admin'))

async def user_has_moderator_role(user_id: UUID) -> bool:
    """Check if user has moderator, admin, or super_admin role"""
    return (await user_has_role(user_id, 'moderator') or 
            await user_has_admin_role(user_id))

# Convenience dependencies for common permission patterns
RequireAuth = Depends(get_current_user_required_for_permissions)
OptionalAuth = Depends(get_current_user_for_permissions)
RequireAdmin = require_role('admin', fail_open=False)
RequireModerator = require_role('moderator', fail_open=False)
