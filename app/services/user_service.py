"""
User service layer - Production implementation using raw SQL
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException
from app.services.db_service import DatabaseService
from app.core.security import get_password_hash
from app.models.pydantic_models import RoleResponse

logger = logging.getLogger(__name__)

class UserService:
    """Service for user-related operations using raw SQL"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def _format_user_with_role(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format user data to include role information"""
        if not user_data:
            return user_data
        
        # Extract role information if present
        role_info = None
        if user_data.get('role_id'):
            role_info = {
                'id': user_data.get('role_id'),
                'role_name': user_data.get('role_name'),
                'abbreviation': user_data.get('abbreviation'),
                'level_rank': user_data.get('level_rank'),
                'role_type': user_data.get('role_type'),
                'description': user_data.get('role_description'),
                'level': user_data.get('level'),
                'is_elected': user_data.get('is_elected'),
                'term_length': user_data.get('term_length'),
                'status': user_data.get('role_status'),
                'created_at': user_data.get('created_at'),
                'updated_at': user_data.get('updated_at')
            }
        
        # Create clean user data
        clean_user_data = {
            'id': user_data.get('id'),
            'username': user_data.get('username'),
            'email': user_data.get('email'),
            'password_hash': user_data.get('password_hash'),
            'display_name': user_data.get('display_name'),
            'bio': user_data.get('bio'),
            'avatar_url': user_data.get('avatar_url'),
            'role': user_data.get('role'),
            'is_active': user_data.get('is_active'),
            'is_verified': user_data.get('is_verified'),
            'created_at': user_data.get('created_at'),
            'updated_at': user_data.get('updated_at'),
            'role_info': role_info
        }
        
        return clean_user_data
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await self.db_service.get_user_by_email(user_data['email'])
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
            
            if user_data.get('username'):
                existing_username = await self.db_service.get_user_by_username(user_data['username'])
                if existing_username:
                    raise HTTPException(status_code=400, detail="Username already taken")
            
            # Hash password if provided
            if 'password' in user_data:
                user_data['password_hash'] = get_password_hash(user_data['password'])
                del user_data['password']  # Remove plain password
            
            # Create user in database
            user = await self.db_service.create_user(user_data)
            
            logger.info(f"Created user {user['id']} with email {user['email']}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(status_code=500, detail="Failed to create user")
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user = await self.db_service.get_user_by_id(user_id)
            return self._format_user_with_role(user) if user else None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            user = await self.db_service.get_user_by_email(email)
            return self._format_user_with_role(user) if user else None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user")
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            user = await self.db_service.get_user_by_username(username)
            return self._format_user_with_role(user) if user else None
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user")
    
    async def update_user(self, user_id: UUID, user_data: Dict[str, Any], current_user_id: UUID) -> Dict[str, Any]:
        """Update user profile"""
        try:
            # Check if user is updating their own profile or is admin
            if user_id != current_user_id:
                # TODO: Add admin role check here
                raise HTTPException(status_code=403, detail="Not authorized to update this user")
            
            # Check if email/username are being changed and not already taken
            if user_data.get('email'):
                existing_user = await self.db_service.get_user_by_email(user_data['email'])
                if existing_user and UUID(existing_user['id']) != user_id:
                    raise HTTPException(status_code=400, detail="Email already registered")
            
            if user_data.get('username'):
                existing_user = await self.db_service.get_user_by_username(user_data['username'])
                if existing_user and UUID(existing_user['id']) != user_id:
                    raise HTTPException(status_code=400, detail="Username already taken")
            
            # Hash password if being updated
            if 'password' in user_data:
                user_data['password_hash'] = get_password_hash(user_data['password'])
                del user_data['password']  # Remove plain password
            
            # Update user in database
            user = await self.db_service.update_user(user_id, user_data)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            logger.info(f"Updated user {user_id}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update user")
    
    async def delete_user(self, user_id: UUID, current_user_id: UUID) -> bool:
        """Delete user account"""
        try:
            # Check if user is deleting their own account or is admin
            if user_id != current_user_id:
                # TODO: Add admin role check here
                raise HTTPException(status_code=403, detail="Not authorized to delete this user")
            
            # Delete user from database
            success = await self.db_service.delete_user(user_id)
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            
            logger.info(f"Deleted user {user_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete user")
    
    async def get_user_stats(self, user_id: UUID) -> Dict[str, int]:
        """Get user statistics"""
        try:
            stats = await self.db_service.get_user_stats(user_id)
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user statistics")
