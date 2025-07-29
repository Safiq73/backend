"""
User service layer - Production implementation using raw SQL
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException
from app.services.db_service import DatabaseService
from app.core.security import get_password_hash
from app.models.pydantic_models import TitleResponse

logger = logging.getLogger(__name__)

class UserService:
    """Service for user-related operations using raw SQL"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def _format_user_with_title(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format user data to include title information"""
        if not user_data:
            return user_data
        
        # Create clean user data
        clean_user_data = {
            'id': user_data.get('id'),
            'username': user_data.get('username'),
            'email': user_data.get('email'),
            'password_hash': user_data.get('password_hash'),
            'display_name': user_data.get('display_name'),
            'bio': user_data.get('bio'),
            'avatar_url': user_data.get('avatar_url'),
            'title': user_data.get('title'),  # Updated: this field now called 'title' (refers to title UUID)
            'is_active': user_data.get('is_active'),
            'is_verified': user_data.get('is_verified'),
            'created_at': user_data.get('created_at'),
            'updated_at': user_data.get('updated_at'),
        }
        
        return clean_user_data
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
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
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user = await self.db_service.get_user_by_id(user_id)
        return self._format_user_with_title(user) if user else None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        user = await self.db_service.get_user_by_email(email)
        return self._format_user_with_title(user) if user else None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        user = await self.db_service.get_user_by_username(username)
        return self._format_user_with_title(user) if user else None
    
    async def update_user(self, user_id: UUID, user_data: Dict[str, Any], current_user_id: UUID) -> Dict[str, Any]:
        """Update user profile"""
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
    
    async def delete_user(self, user_id: UUID, current_user_id: UUID) -> bool:
        """Delete user account"""
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
    
    async def get_user_stats(self, user_id: UUID) -> Dict[str, int]:
        """Get user statistics"""
        stats = await self.db_service.get_user_stats(user_id)
        return stats
