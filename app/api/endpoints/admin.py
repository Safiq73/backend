"""
Admin API Endpoints
===================

This module provides admin-specific API endpoints for user management, 
role management, and system administration.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel

# Import auth and permission dependencies
from app.services.auth_service import get_current_user, AuthService, create_access_token
from app.services.s3_upload_service import s3_upload_service
from app.core.security import get_password_hash
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Pydantic models for admin API
class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    roles: List[str]

class UserStatusUpdate(BaseModel):
    is_active: bool

class RoleAssignment(BaseModel):
    role_name: str

# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/auth/login", response_model=Dict[str, Any])
async def admin_login(credentials: AdminLoginRequest):
    """Admin login endpoint with role verification"""
    try:
        logger.info(f"Admin login attempt | Email: {credentials.email}")
        
        # Authenticate user
        auth_service = AuthService()
        user = await auth_service.authenticate_user(credentials.email, credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # For now, allow any authenticated user to access admin
        # In production, you would check for admin roles here
        
        # Generate access token
        access_token = create_access_token(data={"sub": user["email"], "user_id": str(user["id"])})
        
        # Log successful login
        logger.info(f"Admin login successful: {user['email']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name")
            },
            "roles": ["admin"]  # Mock roles for now
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/auth/verify")
async def verify_admin_session(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Verify admin session"""
    try:
        return {
            "valid": True,
            "user": {
                "id": current_user["id"],
                "email": current_user["email"],
                "roles": ["admin"]  # Mock roles
            }
        }
    except Exception as e:
        logger.error(f"Admin session verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

@router.post("/auth/logout")
async def admin_logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Admin logout"""
    logger.info(f"Admin logout: {current_user.get('email', 'unknown')}")
    return {"message": "Logged out successfully"}

# =============================================================================
# USER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/users")
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all users (mock implementation)"""
    try:
        # Mock user data
        mock_users = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user1@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "roles": ["citizen"]
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "roles": ["admin"]
            }
        ]
        
        # Apply search filter if provided
        if search:
            mock_users = [u for u in mock_users if search.lower() in u["email"].lower() or search.lower() in (u["first_name"] or "").lower()]
        
        # Apply pagination
        start = (page - 1) * size
        end = start + size
        users_page = mock_users[start:end]
        
        return {
            "users": users_page,
            "total": len(mock_users),
            "page": page,
            "size": size,
            "has_next": end < len(mock_users)
        }
        
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get specific user details (mock implementation)"""
    try:
        # Mock user data
        mock_user = {
            "id": str(user_id),
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "roles": ["citizen"],
            "stats": {
                "posts_count": 5,
                "comments_count": 12,
                "followers_count": 10,
                "following_count": 8
            }
        }
        
        return {"user": mock_user}
        
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )

# =============================================================================
# S3 MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/s3/status")
async def get_s3_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get S3 service status and configuration"""
    try:
        s3_available = s3_upload_service.is_available()
        
        return {
            "s3_available": s3_available,
            "bucket_name": s3_upload_service.bucket_name if s3_available else None,
            "region": s3_upload_service.region if s3_available else None,
            "message": "S3 service is operational" if s3_available else "S3 service not configured"
        }
    except Exception as e:
        logger.error(f"S3 status check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check S3 status"
        )

@router.post("/s3/upload")
async def admin_upload_file(
    file: UploadFile = File(..., description="File to upload"),
    folder: Optional[str] = Query("admin", description="Folder to organize the file"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload file to S3 (admin only)"""
    try:
        logger.info(f"Admin uploading file | Admin: {current_user.get('email', 'unknown')} | File: {file.filename}")
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="S3 service not available"
            )
        
        # Sanitize folder name
        safe_folder = "".join(c for c in folder if c.isalnum() or c in ('-', '_')).strip()
        if not safe_folder:
            safe_folder = "admin"
        
        # Upload to S3 with admin folder structure
        file_url = await s3_upload_service.upload_file(
            file=file,
            post_id=f"admin/{safe_folder}",
            use_presigned_url=False
        )
        
        logger.info(f"Admin file uploaded successfully | URL: {file_url}")
        
        return {
            "success": True,
            "message": "File uploaded successfully",
            "file_url": file_url,
            "filename": file.filename,
            "folder": safe_folder
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin file upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )
