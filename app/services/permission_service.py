"""
Permission Service for CivicPulse

This service handles all permission-related database operations and business logic
for the dynamic permission system based on API routes.
"""

from typing import List, Optional, Set, Dict
from uuid import UUID
import logging

from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.permission import APIPermission, SystemRole, UserRole, RoleAPIPermission
from app.models.user import User

logger = logging.getLogger(__name__)

class PermissionService:
    """Service for managing permissions and roles"""
    
    def __init__(self):
        self._role_cache: Dict[str, List[str]] = {}
        self._permission_cache: Dict[str, bool] = {}
    
    async def user_has_permission(
        self, 
        user_id: UUID, 
        permission_name: str
    ) -> bool:
        """
        Check if a user has a specific permission
        
        Args:
            user_id: UUID of the user
            permission_name: Permission to check (e.g., 'posts.detail.put')
            
        Returns:
            True if user has permission, False otherwise
        """
        async with get_db_session() as db:
            try:
                # Get user roles
                user_roles = await self.get_user_roles(user_id, db)
                
                if not user_roles:
                    return False
                
                # Check if any role has this permission
                for role in user_roles:
                    if await self._role_has_permission(role.id, permission_name, db):
                        return True
                
                return False
                
            except Exception as e:
                logger.error(f"Error checking permission {permission_name} for user {user_id}: {e}")
                return False
    
    async def get_user_roles(
        self, 
        user_id: UUID, 
        db: Optional[AsyncSession] = None
    ) -> List[SystemRole]:
        """Get all roles assigned to a user"""
        if db is None:
            async with get_db_session() as db:
                return await self._get_user_roles_impl(user_id, db)
        else:
            return await self._get_user_roles_impl(user_id, db)
    
    async def _get_user_roles_impl(
        self, 
        user_id: UUID, 
        db: AsyncSession
    ) -> List[SystemRole]:
        """Implementation of get_user_roles"""
        try:
            query = (
                select(SystemRole)
                .join(UserRole, SystemRole.id == UserRole.role_id)
                .where(UserRole.user_id == user_id)
                .where(SystemRole.is_active == True)
            )
            
            result = await db.execute(query)
            roles = result.scalars().all()
            
            return list(roles)
            
        except Exception as e:
            logger.error(f"Error getting user roles for {user_id}: {e}")
            return []
    
    async def _role_has_permission(
        self, 
        role_id: UUID, 
        permission_name: str, 
        db: AsyncSession
    ) -> bool:
        """Check if a role has a specific permission"""
        try:
            # Query to check if role has permission
            query = (
                select(RoleAPIPermission.granted)
                .join(APIPermission, RoleAPIPermission.api_permission_id == APIPermission.id)
                .where(
                    and_(
                        RoleAPIPermission.role_id == role_id,
                        APIPermission.permission_name == permission_name,
                        APIPermission.is_active == True
                    )
                )
            )
            
            result = await db.execute(query)
            granted = result.scalar()
            
            # If no explicit permission found, default to False
            return granted if granted is not None else False
            
        except Exception as e:
            logger.error(f"Error checking role permission {permission_name} for role {role_id}: {e}")
            return False
    
    async def assign_role_to_user(
        self, 
        user_id: UUID, 
        role_name: str,
        assigned_by: Optional[UUID] = None
    ) -> bool:
        """Assign a role to a user"""
        async with get_db_session() as db:
            try:
                # Get role by name
                role_query = select(SystemRole).where(
                    and_(
                        SystemRole.name == role_name,
                        SystemRole.is_active == True
                    )
                )
                role_result = await db.execute(role_query)
                role = role_result.scalar_one_or_none()
                
                if not role:
                    logger.error(f"Role {role_name} not found")
                    return False
                
                # Check if user already has this role
                existing_query = select(UserRole).where(
                    and_(
                        UserRole.user_id == user_id,
                        UserRole.role_id == role.id
                    )
                )
                existing_result = await db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"User {user_id} already has role {role_name}")
                    return True
                
                # Create new user role
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role.id,
                    assigned_by=assigned_by
                )
                
                db.add(user_role)
                await db.commit()
                
                logger.info(f"Assigned role {role_name} to user {user_id}")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error assigning role {role_name} to user {user_id}: {e}")
                return False
    
    async def remove_role_from_user(
        self, 
        user_id: UUID, 
        role_name: str
    ) -> bool:
        """Remove a role from a user"""
        async with get_db_session() as db:
            try:
                # Find and delete the user role
                query = (
                    select(UserRole)
                    .join(SystemRole, UserRole.role_id == SystemRole.id)
                    .where(
                        and_(
                            UserRole.user_id == user_id,
                            SystemRole.name == role_name
                        )
                    )
                )
                
                result = await db.execute(query)
                user_role = result.scalar_one_or_none()
                
                if user_role:
                    await db.delete(user_role)
                    await db.commit()
                    logger.info(f"Removed role {role_name} from user {user_id}")
                    return True
                else:
                    logger.info(f"User {user_id} does not have role {role_name}")
                    return False
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error removing role {role_name} from user {user_id}: {e}")
                return False
    
    async def get_user_permissions(
        self, 
        user_id: UUID
    ) -> List[str]:
        """Get all permission names that a user has"""
        async with get_db_session() as db:
            try:
                # Get all permissions for user through their roles
                query = (
                    select(APIPermission.permission_name)
                    .join(RoleAPIPermission, APIPermission.id == RoleAPIPermission.api_permission_id)
                    .join(UserRole, RoleAPIPermission.role_id == UserRole.role_id)
                    .where(
                        and_(
                            UserRole.user_id == user_id,
                            RoleAPIPermission.granted == True,
                            APIPermission.is_active == True
                        )
                    )
                    .distinct()
                )
                
                result = await db.execute(query)
                permissions = result.scalars().all()
                
                return list(permissions)
                
            except Exception as e:
                logger.error(f"Error getting permissions for user {user_id}: {e}")
                return []
    
    async def create_api_permission(
        self,
        route_path: str,
        method: str,
        permission_name: str,
        description: str,
        category: str
    ) -> bool:
        """Create a new API permission"""
        async with get_db_session() as db:
            try:
                # Check if permission already exists
                existing_query = select(APIPermission).where(
                    and_(
                        APIPermission.route_path == route_path,
                        APIPermission.method == method
                    )
                )
                existing_result = await db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Permission for {method} {route_path} already exists")
                    return True
                
                # Create new permission
                permission = APIPermission(
                    route_path=route_path,
                    method=method,
                    permission_name=permission_name,
                    description=description,
                    category=category
                )
                
                db.add(permission)
                await db.commit()
                
                logger.info(f"Created API permission: {permission_name}")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error creating API permission {permission_name}: {e}")
                return False
    
    async def sync_permissions_from_registry(self) -> bool:
        """Sync API permissions from the permissions registry"""
        from app.core.permissions import API_PERMISSIONS_REGISTRY
        
        async with get_db_session() as db:
            try:
                for perm in API_PERMISSIONS_REGISTRY:
                    await self.create_api_permission(
                        route_path=perm.route_path,
                        method=perm.method.value,
                        permission_name=perm.permission_name,
                        description=perm.description,
                        category=perm.category
                    )
                
                logger.info("Successfully synced permissions from registry")
                return True
                
            except Exception as e:
                logger.error(f"Error syncing permissions from registry: {e}")
                return False
    
    async def get_role_permissions(
        self, 
        role_name: str
    ) -> List[str]:
        """Get all permissions for a specific role"""
        async with get_db_session() as db:
            try:
                query = (
                    select(APIPermission.permission_name)
                    .join(RoleAPIPermission, APIPermission.id == RoleAPIPermission.api_permission_id)
                    .join(SystemRole, RoleAPIPermission.role_id == SystemRole.id)
                    .where(
                        and_(
                            SystemRole.name == role_name,
                            RoleAPIPermission.granted == True,
                            APIPermission.is_active == True
                        )
                    )
                )
                
                result = await db.execute(query)
                permissions = result.scalars().all()
                
                return list(permissions)
                
            except Exception as e:
                logger.error(f"Error getting permissions for role {role_name}: {e}")
                return []
