"""
Authentication service - Production implementation using raw SQL
"""
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_password, create_access_token, create_refresh_token, verify_token
from app.services.db_service import DatabaseService
from app.core.logging_config import get_logger, log_error_with_context

security = HTTPBearer(auto_error=False)
logger = get_logger('app.auth')


class AuthService:
    """Service for authentication operations using raw SQL"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        try:
            logger.info(f"Authentication attempt | Email: {email}")
            user = await self.db_service.get_user_by_email(email)
            if not user:
                logger.warning(f"Authentication failed - user not found | Email: {email}")
                return None
            
            if not verify_password(password, user['password_hash']):
                logger.warning(f"Authentication failed - invalid password | Email: {email}")
                return None
            
            logger.info(f"Authentication successful | User ID: {user['id']} | Email: {email}")
            return user
            
        except Exception as e:
            log_error_with_context(
                logger, e,
                {
                    'operation': 'authenticate_user',
                    'email': email
                }
            )
            return None
    
    async def create_tokens(self, user_id: str) -> dict:
        """Create JWT access and refresh tokens"""
        try:
            logger.info(f"Creating tokens for user: {user_id}")
            access_token = create_access_token(data={"sub": user_id})
            refresh_token = create_refresh_token(data={"sub": user_id})
            
            # Import settings to get token expiry time
            from app.core.config import settings
            
            logger.info(f"Tokens created successfully for user: {user_id}")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60  
            }
        except Exception as e:
            log_error_with_context(
                logger, e,
                {
                    'operation': 'create_tokens',
                    'user_id': user_id,
                    'user_id_type': type(user_id).__name__
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create authentication tokens"
            )
    
    async def refresh_tokens(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        try:
            logger.info("Token refresh attempt")
            payload = verify_token(refresh_token)
            if not payload:
                logger.warning("Token refresh failed - invalid token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("Token refresh failed - invalid payload")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Verify user still exists and is active
            try:
                user_uuid = UUID(user_id)
                user = await self.db_service.get_user_by_id(user_uuid)
                if not user or not user.get('is_active', True):
                    logger.warning(f"Token refresh failed - user not found or inactive: {user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User no longer active"
                    )
            except ValueError:
                logger.warning(f"Token refresh failed - invalid user ID format: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user ID"
                )
            
            # Create new tokens
            logger.info(f"Refreshing tokens for user: {user_id}")
            return await self.create_tokens(user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            log_error_with_context(
                logger, e,
                {
                    'operation': 'refresh_tokens'
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )

    async def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token by adding it to blacklist"""
        try:
            logger.info("Token revocation attempt")
            
            # Verify token format and extract payload
            payload = verify_token(refresh_token)
            if not payload:
                logger.warning("Token revocation failed - invalid token")
                return False
            
            # Add token to blacklist in database
            await self.blacklist_token(refresh_token, payload.get('exp'))
            
            logger.info("Token revoked successfully")
            return True
        except Exception as e:
            log_error_with_context(
                logger, e,
                {
                    'operation': 'revoke_token'
                }
            )
            return False
    
    async def blacklist_token(self, token: str, expires_at: int) -> bool:
        """Add token to blacklist table"""
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                query = """
                    INSERT INTO token_blacklist (token_hash, expires_at)
                    VALUES ($1, $2)
                    ON CONFLICT (token_hash) DO NOTHING
                """
                # Hash the token for privacy
                import hashlib
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                
                await conn.execute(
                    query,
                    token_hash,
                    expires_at
                )
            return True
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            async with self.db_service.get_connection_with_retry() as conn:
                import hashlib
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                
                query = """
                    SELECT 1 FROM token_blacklist 
                    WHERE token_hash = $1 AND expires_at > extract(epoch from now())
                """
                result = await conn.fetchrow(query, token_hash)
                return result is not None
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID for token validation"""

        try:
            user = await self.db_service.get_user_by_id(user_id)
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None


# Global dependency function
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current authenticated user from JWT token"""
    if not credentials:
        return None
    
    try:
        # Verify token format

        payload = verify_token(credentials.credentials)

        if not payload:
            return None
        
        # Check if token is blacklisted
        auth_service = AuthService()
        if await auth_service.is_token_blacklisted(credentials.credentials):
            logger.warning("Blacklisted token used")
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Convert string to UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            logger.debug(f"Invalid user ID format: {user_id}")
            return None

        # Get user from database
        user = await auth_service.get_user_by_id(user_uuid)
        
        if user and user.get('is_active', True):
            logger.debug(f"Current user retrieved | User ID: {user['id']}")
            return user

        return None
            
    except Exception as e:
        logger.debug(f"Get current user error: {e}")
        return None


# Optional dependency for protected routes
async def get_current_user_required(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user with required authentication"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user
