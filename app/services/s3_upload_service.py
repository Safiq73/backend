"""
AWS S3 Service for CivicPulse
This service handles uploading images and videos to Amazon S3.
"""
import uuid
import boto3
import mimetypes
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, List, BinaryIO
from fastapi import HTTPException, UploadFile
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger('app.s3_upload_service')


class S3UploadService:
    """AWS S3 service for handling file uploads"""
    
    # Allowed MIME types for uploads
    ALLOWED_IMAGE_TYPES = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
    ]
    
    ALLOWED_VIDEO_TYPES = [
        'video/mp4', 'video/webm', 'video/ogg', 'video/avi', 'video/mov'
    ]
    
    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self):
        self.bucket_name = settings.aws_s3_bucket
        self.region = settings.aws_region
        
        # Initialize S3 client
        self._initialize_s3_client()
        
    def _initialize_s3_client(self):
        """Initialize the S3 client with credentials"""
        try:
            if not settings.aws_access_key_id or not settings.aws_secret_access_key:
                logger.warning("AWS credentials not found, S3 uploads will be disabled")
                self.s3_client = None
                return
                
            if not self.bucket_name:
                logger.warning("S3 bucket name not configured, S3 uploads will be disabled")
                self.s3_client = None
                return
            
            # Create S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=self.region,
                endpoint_url=settings.aws_s3_endpoint_url  # For local MinIO/LocalStack testing
            )
            
            # Test connection by checking if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"S3 service initialized successfully with bucket: {self.bucket_name}")
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    logger.error(f"S3 bucket '{self.bucket_name}' not found")
                elif error_code == 403:
                    logger.error(f"Access denied to S3 bucket '{self.bucket_name}'")
                else:
                    logger.error(f"Error accessing S3 bucket: {e}")
                self.s3_client = None
                
        except NoCredentialsError:
            logger.error("AWS credentials not available")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def _validate_file(self, file: UploadFile) -> None:
        """Validate file type and size"""
        # Check if file has content
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
            
        # Determine MIME type
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        if not content_type:
            raise HTTPException(status_code=400, detail="Unable to determine file type")
        
        # Check if file type is allowed
        if content_type not in self.ALLOWED_IMAGE_TYPES + self.ALLOWED_VIDEO_TYPES:
            allowed_types = ', '.join(self.ALLOWED_IMAGE_TYPES + self.ALLOWED_VIDEO_TYPES)
            raise HTTPException(
                status_code=400, 
                detail=f"File type '{content_type}' not allowed. Allowed types: {allowed_types}"
            )
        
        # Check file size based on type
        if hasattr(file, 'size') and file.size:
            if content_type in self.ALLOWED_IMAGE_TYPES and file.size > self.MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Image file too large. Maximum size: {self.MAX_IMAGE_SIZE // (1024*1024)}MB"
                )
            elif content_type in self.ALLOWED_VIDEO_TYPES and file.size > self.MAX_VIDEO_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Video file too large. Maximum size: {self.MAX_VIDEO_SIZE // (1024*1024)}MB"
                )
    
    def _generate_file_key(self, filename: str, post_id: Optional[str] = None) -> str:
        """Generate a unique file key for S3"""
        # Extract file extension
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())
        
        # Create folder structure: posts/{post_id}/{unique_id}.{extension} or uploads/{unique_id}.{extension}
        if post_id:
            file_key = f"posts/{post_id}/{unique_id}.{file_extension}"
        else:
            file_key = f"uploads/{unique_id}.{file_extension}"
            
        return file_key
    
    async def upload_file(self, file: UploadFile, post_id: Optional[str] = None, use_presigned_url: bool = False) -> str:
        """
        Upload a file to S3 and return the public URL or presigned URL
        
        Args:
            file: The uploaded file
            post_id: Optional post ID to organize files
            use_presigned_url: If True, return a presigned URL instead of direct URL
            
        Returns:
            str: The public URL or presigned URL of the uploaded file
            
        Raises:
            HTTPException: If upload fails or file is invalid
        """
        if not self.s3_client:
            raise HTTPException(
                status_code=503, 
                detail="S3 service unavailable. Please check configuration."
            )
        
        # Validate the file
        self._validate_file(file)
        
        try:
            # Generate unique file key
            file_key = self._generate_file_key(file.filename, post_id)
            
            # Read file content
            file_content = await file.read()
            
            # Reset file pointer for potential re-reading
            await file.seek(0)
            
            # Determine content type
            content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
            
            # Upload to S3
            extra_args = {
                'ContentType': content_type,
                'CacheControl': 'max-age=31536000',  # Cache for 1 year
            }
            
            # Add content disposition for better handling
            if content_type.startswith('image/'):
                extra_args['ContentDisposition'] = 'inline'
            elif content_type.startswith('video/'):
                extra_args['ContentDisposition'] = 'inline'
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                **extra_args
            )
            
            # Generate public URL (Note: bucket must be configured for public access)
            # Alternative: use presigned URLs if bucket is private
            if use_presigned_url:
                # Generate presigned URL for private bucket access
                file_url = self.generate_presigned_url(file_key, expiration=86400)  # 24 hours
            else:
                # Generate direct URL (requires public bucket or bucket policy)
                if settings.aws_s3_endpoint_url:
                    # For local development (MinIO/LocalStack)
                    file_url = f"{settings.aws_s3_endpoint_url}/{self.bucket_name}/{file_key}"
                else:
                    # For AWS S3
                    file_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
            
            logger.info(f"File uploaded successfully: {file.filename} -> {file_url}")
            return file_url
            
        except ClientError as e:
            logger.error(f"S3 upload failed for file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file to S3")
        except Exception as e:
            logger.error(f"Unexpected error during file upload: {e}")
            raise HTTPException(status_code=500, detail="An error occurred during file upload")
    
    async def upload_multiple_files(self, files: List[UploadFile], post_id: Optional[str] = None, use_presigned_url: bool = False) -> List[str]:
        """
        Upload multiple files to S3
        
        Args:
            files: List of uploaded files
            post_id: Optional post ID to organize files
            use_presigned_url: If True, return presigned URLs instead of direct URLs
            
        Returns:
            List[str]: List of public URLs or presigned URLs of uploaded files
        """
        if not files:
            return []
        
        uploaded_urls = []
        failed_uploads = []
        
        for file in files:
            try:
                url = await self.upload_file(file, post_id, use_presigned_url)
                uploaded_urls.append(url)
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {e}")
                failed_uploads.append(file.filename)
        
        if failed_uploads:
            logger.warning(f"Some files failed to upload: {failed_uploads}")
            # Optionally raise exception if any uploads failed
            # raise HTTPException(status_code=500, detail=f"Failed to upload files: {', '.join(failed_uploads)}")
        
        return uploaded_urls
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from S3 using its URL
        
        Args:
            file_url: The public URL of the file to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available for file deletion")
            return False
        
        try:
            # Extract file key from URL
            # Expected URL format: https://bucket.s3.region.amazonaws.com/file-key
            if f"{self.bucket_name}.s3.{self.region}.amazonaws.com/" in file_url:
                file_key = file_url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")[1]
            else:
                logger.error(f"Invalid S3 URL format: {file_url}")
                return False
            
            # Delete from S3
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            
            logger.info(f"File deleted successfully: {file_url}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 deletion failed for file {file_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during file deletion: {e}")
            return False
    
    def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for private file access
        
        Args:
            file_key: The S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: The presigned URL
        """
        if not self.s3_client:
            raise HTTPException(status_code=503, detail="S3 service unavailable")
        
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate presigned URL")
    
    def is_available(self) -> bool:
        """Check if S3 service is available and properly configured"""
        return self.s3_client is not None


# Global instance
s3_upload_service = S3UploadService()
