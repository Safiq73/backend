from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from app.services.auth_service import get_current_user, get_current_user_optional
from app.services.user_service import UserService
from app.services.post_service import PostService
from app.services.representative_service import RepresentativeService
from app.services.s3_upload_service import s3_upload_service
from app.models.pydantic_models import APIResponse, UserUpdate, UserResponse, UserWithRepresentativeResponse, PublicUserWithRepresentativeResponse
from app.core.permission_decorators import require_permissions
from typing import Dict, Any, Optional
from uuid import UUID
import logging

router = APIRouter()
user_service = UserService()
post_service = PostService()
representative_service = RepresentativeService()
logger = logging.getLogger(__name__)

@router.get("/{user_id}/stats", response_model=APIResponse)
async def get_user_statistics(
    user_id: UUID = Path(..., description="ID of the user to get statistics for"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get user statistics including posts count, comments received, upvotes received"""
    try:
        # Get user to verify they exist
        user_data = await user_service.get_user_by_id(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user statistics from database
        from app.services.db_service import DatabaseService
        db_service = DatabaseService()
        stats = await db_service.get_user_stats(user_id)
        
        # Get additional stats like total views (for now, calculate estimated views)
        # TODO: Implement proper view tracking
        estimated_views = stats['posts_count'] * 127  # Mock calculation until view tracking is added
        
        user_statistics = {
            "posts_count": stats['posts_count'],
            "comments_received": stats['comments_count'],  # Comments on user's posts
            "upvotes_received": stats['upvotes_received'], # Upvotes on user's posts
            "total_views": estimated_views  # Estimated views (mock data for now)
        }
        
        logger.info(f"Retrieved statistics for user {user_id}")
        
        return APIResponse(
            success=True,
            message="User statistics retrieved successfully",
            data=user_statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user statistics for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user statistics")

@router.get("/profile", response_model=APIResponse)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile with representative information"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get full user data with role information
    user_data = await user_service.get_user_by_id(current_user["id"])
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove password_hash from response
    user_data.pop('password_hash', None)
    
    # Get all representative accounts linked to the user
    rep_accounts = await representative_service.get_user_rep_accounts(current_user["id"])
    user_data['rep_accounts'] = rep_accounts
    
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=UserWithRepresentativeResponse(**user_data)
    )

@router.get("/posts", response_model=APIResponse)
async def get_current_user_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get posts created by the current user"""
    from uuid import UUID
    
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    user_id = current_user["id"]
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID")
    
    # Ensure user_id is a UUID object
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # Get posts by the current user
    posts = await post_service.get_posts(
        skip=(page - 1) * size,
        limit=size,
        author_id=user_id,
        current_user_id=user_id
    )        

    return APIResponse(
        success=True,
        message="User posts retrieved successfully",
        data={
            "posts": posts,
            "page": page,
            "size": size,
            "total": len(posts)
        }
    )

@router.get("/{user_id}", response_model=APIResponse)
async def get_user_by_id(
    user_id: UUID = Path(..., description="ID of the user to get"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get public user profile by ID"""
    # Get user data
    user_data = await user_service.get_user_by_id(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove sensitive information for public access
    user_data.pop('password_hash', None)
    user_data.pop('email', None)  # Don't expose email to other users
    
    # Get representative accounts linked to the user
    rep_accounts = await representative_service.get_user_rep_accounts(user_id)
    user_data['rep_accounts'] = rep_accounts
    
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=PublicUserWithRepresentativeResponse(**user_data)
    )

@router.put("/profile", response_model=APIResponse)
async def update_user_profile(
    user_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile"""
    # Update user profile
    updated_user = await user_service.update_user(
        current_user['id'], 
        user_data.dict(exclude_unset=True),
        current_user['id']
    )
    
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data={"user": updated_user}
    )

@router.post("/avatar", response_model=APIResponse)
async def upload_avatar(
    file: UploadFile = File(..., description="Avatar image file"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload user avatar image to S3"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        logger.info(f"Uploading avatar | User: {current_user['id']} | File: {file.filename}")
        
        # Validate file type (only images allowed for avatars)
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="Only image files are allowed for avatars"
            )
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            logger.warning("S3 service not available for avatar upload")
            raise HTTPException(
                status_code=503,
                detail="File upload service temporarily unavailable"
            )
        
        # Upload to S3 with user-specific folder
        avatar_url = await s3_upload_service.upload_file(
            file=file,
            post_id=f"avatars/user_{current_user['id']}",
            use_presigned_url=False
        )
        
        # Update user record with new avatar URL
        user_data = {'avatar_url': avatar_url}
        updated_user = await user_service.update_user(current_user['id'], user_data, current_user['id'])
        
        logger.info(f"Avatar uploaded successfully | User: {current_user['id']} | URL: {avatar_url}")
        
        return APIResponse(
            success=True,
            message="Avatar uploaded successfully",
            data={
                "avatar_url": avatar_url,
                "user": updated_user
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar upload failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload avatar"
        )

@router.post("/cover-photo", response_model=APIResponse)
async def upload_cover_photo(
    file: UploadFile = File(..., description="Cover photo image file"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload user cover photo image to S3"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        logger.info(f"Uploading cover photo | User: {current_user['id']} | File: {file.filename}")
        
        # Validate file type (only images allowed for cover photos)
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="Only image files are allowed for cover photos"
            )
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            logger.warning("S3 service not available for cover photo upload")
            raise HTTPException(
                status_code=503,
                detail="File upload service temporarily unavailable"
            )
        
        # Upload to S3 with user-specific folder
        cover_photo_url = await s3_upload_service.upload_file(
            file=file,
            post_id=f"covers/user_{current_user['id']}",
            use_presigned_url=False
        )
        
        # Update user record with new cover photo URL
        user_data = {'cover_photo_url': cover_photo_url}
        updated_user = await user_service.update_user(current_user['id'], user_data, current_user['id'])
        
        logger.info(f"Cover photo uploaded successfully | User: {current_user['id']} | URL: {cover_photo_url}")
        
        return APIResponse(
            success=True,
            message="Cover photo uploaded successfully",
            data={
                "cover_photo_url": cover_photo_url,
                "user": updated_user
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cover photo upload failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload cover photo"
        )

@router.post("/upload-media", response_model=APIResponse)
async def upload_user_media(
    file: UploadFile = File(..., description="Media file to upload"),
    folder: Optional[str] = Query("general", description="Folder to organize the file"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload any media file for the user to S3"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        logger.info(f"Uploading user media | User: {current_user['id']} | File: {file.filename} | Folder: {folder}")
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            logger.warning("S3 service not available for media upload")
            raise HTTPException(
                status_code=503,
                detail="File upload service temporarily unavailable"
            )
        
        # Sanitize folder name
        safe_folder = "".join(c for c in folder if c.isalnum() or c in ('-', '_')).strip()
        if not safe_folder:
            safe_folder = "general"
        
        # Upload to S3 with user and folder-specific path
        media_url = await s3_upload_service.upload_file(
            file=file,
            post_id=f"users/{current_user['id']}/{safe_folder}",
            use_presigned_url=False
        )
        
        logger.info(f"User media uploaded successfully | User: {current_user['id']} | URL: {media_url}")
        
        return APIResponse(
            success=True,
            message="Media uploaded successfully",
            data={
                "media_url": media_url,
                "filename": file.filename,
                "folder": safe_folder
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User media upload failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload media"
        )

@router.delete("/media", response_model=APIResponse)
async def delete_user_media(
    media_url: str = Query(..., description="URL of the media to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete user's media file from S3"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        logger.info(f"Deleting user media | User: {current_user['id']} | URL: {media_url}")
        
        # Verify the media URL belongs to this user (security check)
        if f"users/{current_user['id']}" not in media_url and f"avatars/user_{current_user['id']}" not in media_url and f"covers/user_{current_user['id']}" not in media_url:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own media files"
            )
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            logger.warning("S3 service not available for media deletion")
            raise HTTPException(
                status_code=503,
                detail="File deletion service temporarily unavailable"
            )
        
        # Delete from S3
        deletion_success = await s3_upload_service.delete_file(media_url)
        
        if deletion_success:
            logger.info(f"User media deleted successfully | User: {current_user['id']} | URL: {media_url}")
            return APIResponse(
                success=True,
                message="Media deleted successfully",
                data={"deleted_url": media_url}
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete media file"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User media deletion failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete media"
        )

@router.get("/settings/representative", response_model=APIResponse)
async def get_user_representative_settings(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user's representative account settings"""
    # Validate current user
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get linked representative information
    linked_rep = await representative_service.get_user_linked_representative(current_user["id"])
    
    # Get available representatives for selection
    available_reps = await representative_service.get_available_representatives()
    
    return APIResponse(
        success=True,
        message="Representative settings retrieved successfully",
        data={
            "linked_representative": linked_rep,
            "available_representatives": available_reps,
            "can_change": True  # User can always change/update their representative link
        }
    )

@router.put("/{user_id}/role", response_model=APIResponse)
async def assign_user_role(
    user_id: str,
    role_id: str,
    current_user: Dict[str, Any] = Depends(require_permissions("users.role.put"))
):
    """Assign role to user (Admin only)"""
    from uuid import UUID
    
    # TODO: Add admin permission check
    # if current_user.get('title_info', {}).get('title_name') != 'Admin':
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate UUIDs
    try:
        user_uuid = UUID(user_id)
        role_uuid = UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Update user role
    updated_user = await user_service.update_user(
        user_uuid, 
        {"role": role_uuid},
        current_user['id']
    )
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return APIResponse(
        success=True,
        message="User role assigned successfully",
        data={"user": updated_user}
    )

@router.get("/settings/representative/titles", response_model=APIResponse)
async def get_available_titles(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available titles for representative linking"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        titles = await representative_service.get_available_titles()
        
        return APIResponse(
            success=True,
            message="Available titles retrieved successfully",
            data={"titles": titles}
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.get("/settings/representative/jurisdictions", response_model=APIResponse)
async def get_jurisdiction_suggestions(
    title_id: str = Query(..., description="Title ID to filter jurisdictions"),
    query: str = Query(..., min_length=1, description="Search query for jurisdiction name"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get jurisdiction suggestions based on title and search query"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        suggestions = await representative_service.get_jurisdiction_suggestions(
            title_id=title_id,
            query=query,
            limit=limit
        )
        
        return APIResponse(
            success=True,
            message="Jurisdiction suggestions retrieved successfully",
            data={"jurisdictions": suggestions}
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.get("/settings/representative/by-selection", response_model=APIResponse)
async def get_representatives_by_selection(
    title_id: str = Query(..., description="Title ID"),
    jurisdiction_id: str = Query(..., description="Jurisdiction ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available representatives for specific title and jurisdiction selection"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        representatives = await representative_service.get_representatives_by_title_and_jurisdiction(
            title_id=title_id,
            jurisdiction_id=jurisdiction_id
        )
        
        return APIResponse(
            success=True,
            message="Representatives retrieved successfully",
            data={"representatives": representatives}
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors

@router.get("/settings/representative", response_model=APIResponse)
async def get_representatives_for_settings(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
    search_query: str = Query(None, description="Search in title name, jurisdiction name, or abbreviation"),
    title_filter: str = Query(None, description="Filter by exact title name"),
    jurisdiction_name: str = Query(None, description="Filter by exact jurisdiction name"),
    jurisdiction_level: str = Query(None, description="Filter by jurisdiction level (country, state, etc.)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available representatives for user settings with filtering and pagination"""
    try:
        # Validate current user
        if not current_user or "id" not in current_user:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await representative_service.get_available_representatives(
            page=page,
            limit=limit,
            search_query=search_query,
            title_filter=title_filter,
            jurisdiction_name=jurisdiction_name,
            jurisdiction_level=jurisdiction_level
        )
        
        return APIResponse(
            success=True,
            message="Representatives for settings retrieved successfully",
            data={
                "representatives": result["representatives"],
                "pagination": result["pagination"]
            }
        )
    
    except (HTTPException, ValueError, KeyError):
        # Re-raise these specific exceptions
        raise
    # Remove generic Exception catch - let FastAPI handle unexpected errors
