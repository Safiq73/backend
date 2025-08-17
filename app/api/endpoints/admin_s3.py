"""
Admin S3 Management API Endpoints
================================

This module provides S3 file management endpoints for administrators.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.auth import get_current_user, admin_required
from app.services.s3_upload import S3UploadService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-s3"])

# Initialize S3 service
s3_service = S3UploadService()

# =============================================================================
# RESPONSE MODELS
# =============================================================================

class S3StatusResponse(BaseModel):
    status: str
    bucket_name: str
    total_files: int
    total_size_mb: float
    folders: List[str]

class S3UploadResponse(BaseModel):
    success: bool
    file_url: str
    file_key: str
    file_size: int
    message: str

class S3DeleteResponse(BaseModel):
    success: bool
    message: str

# =============================================================================
# S3 MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/s3/status", response_model=S3StatusResponse)
async def get_s3_status(current_user: Dict[str, Any] = Depends(admin_required)):
    """
    Get S3 bucket status and statistics (Admin only)
    """
    try:
        # Get bucket information
        bucket_name = s3_service.bucket_name
        
        # List all objects to get statistics
        objects = s3_service.s3_client.list_objects_v2(Bucket=bucket_name)
        
        total_files = objects.get('KeyCount', 0)
        total_size = sum([obj['Size'] for obj in objects.get('Contents', [])])
        total_size_mb = total_size / (1024 * 1024)  # Convert to MB
        
        # Get folder structure
        folders = set()
        for obj in objects.get('Contents', []):
            key_parts = obj['Key'].split('/')
            if len(key_parts) > 1:
                folders.add(key_parts[0])
        
        return S3StatusResponse(
            status="active",
            bucket_name=bucket_name,
            total_files=total_files,
            total_size_mb=round(total_size_mb, 2),
            folders=list(folders)
        )
        
    except Exception as e:
        logger.error(f"S3 status check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get S3 status: {str(e)}"
        )

@router.post("/s3/upload", response_model=S3UploadResponse)
async def admin_upload_file(
    file: UploadFile = File(...),
    folder: Optional[str] = Form("admin"),
    current_user: Dict[str, Any] = Depends(admin_required)
):
    """
    Upload a file to S3 (Admin only)
    """
    try:
        # Validate file
        await s3_service._validate_file(file)
        
        # Upload file with admin folder structure
        file_key = f"{folder}/{file.filename}"
        file_url = await s3_service.upload_file(file, file_key)
        
        logger.info(f"Admin file uploaded: {file_key} by {current_user.get('email', 'unknown')}")
        
        return S3UploadResponse(
            success=True,
            file_url=file_url,
            file_key=file_key,
            file_size=file.size or 0,
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin file upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )

@router.delete("/s3/delete/{file_key:path}", response_model=S3DeleteResponse)
async def admin_delete_file(
    file_key: str,
    current_user: Dict[str, Any] = Depends(admin_required)
):
    """
    Delete a file from S3 (Admin only)
    """
    try:
        # Delete file
        success = await s3_service.delete_file(file_key)
        
        if success:
            logger.info(f"Admin file deleted: {file_key} by {current_user.get('email', 'unknown')}")
            return S3DeleteResponse(
                success=True,
                message="File deleted successfully"
            )
        else:
            return S3DeleteResponse(
                success=False,
                message="File not found or could not be deleted"
            )
            
    except Exception as e:
        logger.error(f"Admin file deletion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File deletion failed: {str(e)}"
        )

@router.get("/s3/files")
async def list_s3_files(
    folder: Optional[str] = None,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(admin_required)
):
    """
    List files in S3 bucket (Admin only)
    """
    try:
        prefix = folder + "/" if folder else ""
        
        response = s3_service.s3_client.list_objects_v2(
            Bucket=s3_service.bucket_name,
            Prefix=prefix,
            MaxKeys=limit
        )
        
        files = []
        for obj in response.get('Contents', []):
            files.append({
                "key": obj['Key'],
                "size": obj['Size'],
                "last_modified": obj['LastModified'].isoformat(),
                "url": f"https://{s3_service.bucket_name}.s3.{s3_service.region}.amazonaws.com/{obj['Key']}"
            })
        
        return {
            "files": files,
            "total": len(files),
            "truncated": response.get('IsTruncated', False)
        }
        
    except Exception as e:
        logger.error(f"S3 file listing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@router.post("/s3/cleanup")
async def cleanup_orphaned_files(
    dry_run: bool = True,
    current_user: Dict[str, Any] = Depends(admin_required)
):
    """
    Clean up orphaned files in S3 (Admin only)
    """
    try:
        # This would need to be implemented based on your business logic
        # For now, just return a placeholder response
        
        if dry_run:
            message = "Dry run completed. No files were deleted."
        else:
            message = "Cleanup completed."
            
        logger.info(f"S3 cleanup {'(dry run)' if dry_run else ''} by {current_user.get('email', 'unknown')}")
        
        return {
            "success": True,
            "message": message,
            "dry_run": dry_run,
            "files_processed": 0,
            "files_deleted": 0
        }
        
    except Exception as e:
        logger.error(f"S3 cleanup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )
