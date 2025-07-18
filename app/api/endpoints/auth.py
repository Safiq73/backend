from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import UserCreate, UserResponse, Token, LoginRequest, APIResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.core.security import get_password_hash
from app.core.logging_config import get_logger, log_error_with_context
from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str

router = APIRouter()
auth_service = AuthService()
user_service = UserService()
logger = get_logger('app.auth')


@router.post("/register", response_model=APIResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        logger.info(f"Registration attempt | Email: {user_data.email}")
        
        # Validate email domain (basic check)
        if user_data.email.split('@')[1] in ['tempmail.com', '10minutemail.com']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temporary email addresses are not allowed"
            )
        
        # Create user data dict
        user_dict = {
            'username': user_data.username,
            'email': user_data.email,
            'password': user_data.password,
            'display_name': user_data.display_name,
            'bio': user_data.bio,
            'avatar_url': user_data.avatar_url
        }
        
        # Create new user
        user = await user_service.create_user(user_dict)
        
        # Generate tokens
        tokens = await auth_service.create_tokens(str(user['id']))
        
        logger.info(f"Registration successful | User ID: {user['id']} | Email: {user_data.email}")
        
        return APIResponse(
            success=True,
            message="User registered successfully",
            data={
                "user": {
                    "id": str(user['id']),
                    "email": user['email'],
                    "username": user['username'],
                    "display_name": user['display_name']
                },
                "tokens": tokens
            }
        )
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors
        logger.warning(f"Registration validation error | Email: {user_data.email} | Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'register',
                'email': user_data.email,
                'username': user_data.username
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=APIResponse)
async def login(login_data: LoginRequest):
    """Login user"""
    try:
        logger.info(f"Login attempt | Email: {login_data.email}")
        
        # Authenticate user
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            logger.warning(f"Login failed - invalid credentials | Email: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Generate tokens
        tokens = await auth_service.create_tokens(str(user["id"]))
        
        logger.info(f"Login successful | User ID: {user['id']} | Email: {login_data.email}")
        
        return APIResponse(
            success=True,
            message="Login successful",
            data={
                "user": {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "username": user["username"],
                    "display_name": user["display_name"]
                },
                "tokens": tokens
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            logger, e,
            {
                'operation': 'login',
                'email': login_data.email
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token"""
    try:
        logger.info(f"Token refresh attempt")
        tokens = await auth_service.refresh_tokens(request.refresh_token)
        logger.info(f"Token refresh successful")
        return tokens
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout", response_model=APIResponse)
async def logout(request: RefreshTokenRequest):
    """Logout user"""
    try:
        logger.info(f"Logout attempt")
        await auth_service.revoke_token(request.refresh_token)
        logger.info(f"Logout successful")
        return APIResponse(
            success=True,
            message="Logged out successfully"
        )
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
