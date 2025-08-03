"""
Authentication dependencies for CivicPulse FastAPI application

This module provides FastAPI dependencies for authentication and authorization
that integrate with the dynamic permission system.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.security import verify_token
from app.db.session import get_db_session
from app.models.user import User
from app.services.permission_service import PermissionService

logger = logging.getLogger(__name__)

# Security scheme for JWT bearer tokens
security = HTTPBearer()

# Permission service instance
permission_service = PermissionService()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get the current authenticated user from JWT token
    
    Args:
        credentials: JWT token from Authorization header
        db: Database session
        
    Returns:
        User object if authenticated
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Verify and decode the token
        payload = verify_token(credentials.credentials)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # Get user from database
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None
    Useful for endpoints that work with or without authentication
    
    Args:
        credentials: Optional JWT token from Authorization header
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if active
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_permissions(*permission_names: str):
    """
    Dependency factory to require specific permissions
    
    Usage:
        @app.get("/api/v1/admin/users", dependencies=[Depends(require_permissions("admin.users.get"))])
        async def get_admin_users():
            pass
    
    Args:
        *permission_names: One or more permission names required
        
    Returns:
        FastAPI dependency function
    """
    async def check_permissions(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if current user has all required permissions"""
        for permission_name in permission_names:
            has_permission = await permission_service.user_has_permission(
                current_user.id, permission_name
            )
            
            if not has_permission:
                logger.warning(
                    f"Permission denied: User {current_user.id} lacks permission '{permission_name}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission_name}' required"
                )
        
        return current_user
    
    return check_permissions

def require_roles(*role_names: str):
    """
    Dependency factory to require specific roles
    
    Usage:
        @app.get("/api/v1/admin/dashboard", dependencies=[Depends(require_roles("admin", "moderator"))])
        async def admin_dashboard():
            pass
    
    Args:
        *role_names: One or more role names (user must have at least one)
        
    Returns:
        FastAPI dependency function
    """
    async def check_roles(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if current user has at least one of the required roles"""
        user_roles = await permission_service.get_user_roles(current_user.id)
        user_role_names = {role.name for role in user_roles}
        
        required_roles = set(role_names)
        if not user_role_names.intersection(required_roles):
            logger.warning(
                f"Role check failed: User {current_user.id} has roles {user_role_names}, "
                f"but requires one of {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(role_names)}"
            )
        
        return current_user
    
    return check_roles

def require_role_level(min_level: int):
    """
    Dependency factory to require minimum role level
    
    Usage:
        @app.get("/api/v1/moderate", dependencies=[Depends(require_role_level(70))])
        async def moderate_content():
            pass
    
    Args:
        min_level: Minimum role level required
        
    Returns:
        FastAPI dependency function
    """
    async def check_role_level(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if current user has role with sufficient level"""
        user_roles = await permission_service.get_user_roles(current_user.id)
        
        if not user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned"
            )
        
        max_user_level = max(role.level for role in user_roles)
        
        if max_user_level < min_level:
            logger.warning(
                f"Role level check failed: User {current_user.id} has max level {max_user_level}, "
                f"but requires level {min_level}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role level {min_level} or higher required"
            )
        
        return current_user
    
    return check_role_level

async def get_user_permissions(
    current_user: User = Depends(get_current_user)
) -> list[str]:
    """
    Dependency to get current user's permissions
    Useful for endpoints that need to know user capabilities
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of permission names
    """
    return await permission_service.get_user_permissions(current_user.id)

async def get_user_roles(
    current_user: User = Depends(get_current_user)
) -> list:
    """
    Dependency to get current user's roles
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of role objects
    """
    return await permission_service.get_user_roles(current_user.id)
