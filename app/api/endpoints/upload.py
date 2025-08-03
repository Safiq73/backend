"""
File Upload API Endpoints
=========================

This module provides generic file upload endpoints that can be used
across the application for various upload needs.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from app.services.auth_service import get_current_user
from app.services.s3_upload_service import s3_upload_service
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/single", response_model=Dict[str, Any])
async def upload_single_file(
    file: UploadFile = File(..., description="File to upload"),
    folder: Optional[str] = Query("general", description="Folder to organize the file"),
    make_public: bool = Query(False, description="Whether to generate a public URL"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload a single file to S3"""
    try:
        logger.info(f"Uploading single file | User: {current_user['id']} | File: {file.filename}")
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File upload service temporarily unavailable"
            )
        
        # Sanitize folder name
        safe_folder = "".join(c for c in folder if c.isalnum() or c in ('-', '_')).strip()
        if not safe_folder:
            safe_folder = "general"
        
        # Upload to S3 with user-specific folder structure
        file_url = await s3_upload_service.upload_file(
            file=file,
            post_id=f"uploads/{current_user['id']}/{safe_folder}",
            use_presigned_url=not make_public
        )
        
        logger.info(f"Single file uploaded successfully | User: {current_user['id']} | URL: {file_url}")
        
        return {
            "success": True,
            "message": "File uploaded successfully",
            "data": {
                "file_url": file_url,
                "filename": file.filename,
                "folder": safe_folder,
                "size": file.size,
                "content_type": file.content_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single file upload failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.post("/multiple", response_model=Dict[str, Any])
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="Files to upload"),
    folder: Optional[str] = Query("general", description="Folder to organize the files"),
    make_public: bool = Query(False, description="Whether to generate public URLs"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload multiple files to S3"""
    try:
        logger.info(f"Uploading multiple files | User: {current_user['id']} | Count: {len(files)}")
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File upload service temporarily unavailable"
            )
        
        # Sanitize folder name
        safe_folder = "".join(c for c in folder if c.isalnum() or c in ('-', '_')).strip()
        if not safe_folder:
            safe_folder = "general"
        
        # Upload all files
        uploaded_files = []
        failed_files = []
        
        for file in files:
            try:
                file_url = await s3_upload_service.upload_file(
                    file=file,
                    post_id=f"uploads/{current_user['id']}/{safe_folder}",
                    use_presigned_url=not make_public
                )
                
                uploaded_files.append({
                    "filename": file.filename,
                    "file_url": file_url,
                    "size": file.size,
                    "content_type": file.content_type
                })
                
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {e}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        logger.info(f"Multiple files upload completed | User: {current_user['id']} | Success: {len(uploaded_files)} | Failed: {len(failed_files)}")
        
        return {
            "success": len(uploaded_files) > 0,
            "message": f"Uploaded {len(uploaded_files)} of {len(files)} files successfully",
            "data": {
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "folder": safe_folder,
                "total_count": len(files),
                "success_count": len(uploaded_files),
                "failure_count": len(failed_files)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multiple file upload failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload files"
        )


@router.delete("/delete", response_model=Dict[str, Any])
async def delete_file(
    file_url: str = Query(..., description="URL of the file to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a file from S3"""
    try:
        logger.info(f"Deleting file | User: {current_user['id']} | URL: {file_url}")
        
        # Verify the file URL belongs to this user (security check)
        if f"uploads/{current_user['id']}" not in file_url and f"users/{current_user['id']}" not in file_url:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own files"
            )
        
        # Check if S3 service is available
        if not s3_upload_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File deletion service temporarily unavailable"
            )
        
        # Delete from S3
        deletion_success = await s3_upload_service.delete_file(file_url)
        
        if deletion_success:
            logger.info(f"File deleted successfully | User: {current_user['id']} | URL: {file_url}")
            return {
                "success": True,
                "message": "File deleted successfully",
                "data": {"deleted_url": file_url}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion failed | User: {current_user['id']} | Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_upload_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get file upload service status"""
    try:
        s3_available = s3_upload_service.is_available()
        
        return {
            "success": True,
            "data": {
                "upload_service_available": s3_available,
                "max_image_size_mb": s3_upload_service.MAX_IMAGE_SIZE // (1024 * 1024),
                "max_video_size_mb": s3_upload_service.MAX_VIDEO_SIZE // (1024 * 1024),
                "allowed_image_types": s3_upload_service.ALLOWED_IMAGE_TYPES,
                "allowed_video_types": s3_upload_service.ALLOWED_VIDEO_TYPES,
                "message": "Upload service is operational" if s3_available else "Upload service not available"
            }
        }
        
    except Exception as e:
        logger.error(f"Upload status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check upload service status"
        )
