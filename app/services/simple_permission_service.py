"""
Simple Permission Service for CivicPulse - Adapted to existing database patterns

This service provides basic permission checking using raw SQL queries
compatible with the existing CivicPulse database architecture.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.db.database import db_manager

logger = logging.getLogger(__name__)

class SimplePermissionService:
    """Simplified permission service using raw SQL queries"""
    
    async def user_has_permission(self, user_id: UUID, permission_name: str) -> bool:
        """
        Check if a user has a specific permission
        
        Args:
            user_id: The user's UUID
            permission_name: The permission name (e.g., 'posts.detail.put')
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            async with db_manager.get_connection() as conn:
                # Query to check if user has the permission through their roles
                query = """
                    SELECT EXISTS (
                        SELECT 1 
                        FROM user_roles ur
                        JOIN system_roles sr ON ur.role_id = sr.id
                        JOIN role_api_permissions rap ON sr.id = rap.role_id
                        JOIN api_permissions ap ON rap.permission_id = ap.id
                        WHERE ur.user_id = $1 
                        AND ap.permission_name = $2
                        AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                    ) as has_permission
                """
                
                result = await conn.fetchrow(query, user_id, permission_name)
                return result['has_permission'] if result else False
                
        except Exception as e:
            logger.error(f"Error checking permission for user {user_id}, permission {permission_name}: {e}")
            return False
    
    async def get_user_roles(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all roles assigned to a user
        
        Args:
            user_id: The user's UUID
            
        Returns:
            List of role dictionaries
        """
        try:
            async with db_manager.get_connection() as conn:
                query = """
                    SELECT sr.id, sr.name, sr.display_name, sr.description, 
                           sr.level, sr.color, ur.assigned_at, ur.expires_at
                    FROM user_roles ur
                    JOIN system_roles sr ON ur.role_id = sr.id
                    WHERE ur.user_id = $1
                    AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                    ORDER BY sr.level DESC
                """
                
                results = await conn.fetch(query, user_id)
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {e}")
            return []
    
    async def assign_role_to_user(self, user_id: UUID, role_name: str, assigned_by: Optional[UUID] = None) -> bool:
        """
        Assign a role to a user
        
        Args:
            user_id: The user's UUID
            role_name: The role name to assign
            assigned_by: UUID of the user assigning the role
            
        Returns:
            True if role was assigned successfully, False otherwise
        """
        try:
            async with db_manager.get_connection() as conn:
                # Get role ID by name
                role_query = "SELECT id FROM system_roles WHERE name = $1"
                role_result = await conn.fetchrow(role_query, role_name)
                
                if not role_result:
                    logger.error(f"Role '{role_name}' not found")
                    return False
                
                role_id = role_result['id']
                
                # Insert user role assignment
                insert_query = """
                    INSERT INTO user_roles (user_id, role_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                """
                
                await conn.execute(insert_query, user_id, role_id, assigned_by)
                
                logger.info(f"Assigned role '{role_name}' to user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error assigning role '{role_name}' to user {user_id}: {e}")
            return False
    
    async def remove_role_from_user(self, user_id: UUID, role_name: str) -> bool:
        """
        Remove a role from a user
        
        Args:
            user_id: The user's UUID
            role_name: The role name to remove
            
        Returns:
            True if role was removed successfully, False otherwise
        """
        try:
            async with db_manager.get_connection() as conn:
                query = """
                    DELETE FROM user_roles 
                    WHERE user_id = $1 
                    AND role_id = (SELECT id FROM system_roles WHERE name = $2)
                """
                
                result = await conn.execute(query, user_id, role_name)
                
                # Extract number of affected rows from result string like "DELETE 1"
                affected_rows = int(result.split()[-1]) if result.split() else 0
                
                if affected_rows > 0:
                    logger.info(f"Removed role '{role_name}' from user {user_id}")
                    return True
                else:
                    logger.warning(f"Role '{role_name}' was not assigned to user {user_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error removing role '{role_name}' from user {user_id}: {e}")
            return False
    
    async def get_all_roles(self) -> List[Dict[str, Any]]:
        """
        Get all available system roles
        
        Returns:
            List of all role dictionaries
        """
        try:
            async with db_manager.get_connection() as conn:
                query = """
                    SELECT id, name, display_name, description, level, color, is_system_role
                    FROM system_roles
                    ORDER BY level DESC
                """
                
                results = await conn.fetch(query)
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting all roles: {e}")
            return []
    
    async def get_route_permission_name(self, route_path: str, method: str) -> Optional[str]:
        """
        Get the permission name for a specific route and method
        
        Args:
            route_path: The API route path
            method: The HTTP method
            
        Returns:
            Permission name if found, None otherwise
        """
        try:
            async with db_manager.get_connection() as conn:
                query = """
                    SELECT permission_name 
                    FROM api_permissions 
                    WHERE route_path = $1 AND method = $2
                """
                
                result = await conn.fetchrow(query, route_path, method.upper())
                return result['permission_name'] if result else None
                
        except Exception as e:
            logger.error(f"Error getting permission for route {route_path} {method}: {e}")
            return None

# Global permission service instance
permission_service = SimplePermissionService()


# FastAPI dependency function
async def get_permission_service() -> SimplePermissionService:
    """FastAPI dependency to get permission service instance"""
    return permission_service


# Convenience functions for common operations
async def check_user_permission(user_id: UUID, permission_name: str) -> bool:
    """Check if user has permission - convenience function"""
    return await permission_service.user_has_permission(user_id, permission_name)


async def assign_default_role_to_user(user_id: UUID, role_name: str = "citizen") -> bool:
    """Assign default role to a new user"""
    return await permission_service.assign_role_to_user(user_id, role_name)
