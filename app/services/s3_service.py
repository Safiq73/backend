"""
Mock S3 Service for CivicPulse
This service provides mock S3 functionality for image and video storage.
In production, this would interact with actual AWS S3.
"""
import uuid
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger('app.s3_service')


class MockS3Service:
    """Mock S3 service that returns static URLs for images and videos"""
    
    # Mock static URLs for different content types
    MOCK_IMAGES = [
        "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800&h=600&fit=crop&crop=edges",  # City infrastructure
        "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=800&h=600&fit=crop&crop=edges",  # Road maintenance
        "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=800&h=600&fit=crop&crop=edges",  # City skyline
        "https://images.unsplash.com/photo-1519983734-4e0cf1bb6ae2?w=800&h=600&fit=crop&crop=edges",  # Community park
        "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?w=800&h=600&fit=crop&crop=edges",  # Public transportation
    ]
    
    MOCK_VIDEOS = [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    ]
    
    def __init__(self):
        self.bucket_name = "civicpulse-mock-bucket"
        logger.info("Mock S3 Service initialized")
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        """
        Mock file upload - returns a static URL based on content type
        In production, this would upload to actual S3 and return the S3 URL
        """
        try:
            # Generate a mock file key
            file_extension = filename.split('.')[-1].lower()
            mock_file_key = f"uploads/{uuid.uuid4()}.{file_extension}"
            
            logger.info(f"Mock upload: {filename} -> {mock_file_key}")
            
            # Return mock URL based on content type
            if content_type.startswith('image/'):
                # Cycle through mock images based on filename hash
                index = hash(filename) % len(self.MOCK_IMAGES)
                mock_url = self.MOCK_IMAGES[index]
            elif content_type.startswith('video/'):
                # Cycle through mock videos based on filename hash
                index = hash(filename) % len(self.MOCK_VIDEOS)
                mock_url = self.MOCK_VIDEOS[index]
            else:
                # Default to first image for unknown types
                mock_url = self.MOCK_IMAGES[0]
            
            logger.info(f"Mock S3 upload successful: {mock_url}")
            return mock_url
            
        except Exception as e:
            logger.error(f"Mock S3 upload failed: {str(e)}")
            raise
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Mock file deletion - always returns True
        In production, this would delete from actual S3
        """
        try:
            logger.info(f"Mock S3 delete: {file_url}")
            return True
        except Exception as e:
            logger.error(f"Mock S3 delete failed: {str(e)}")
            return False
    
    async def get_signed_url(self, file_key: str, expiration: int = 3600) -> str:
        """
        Mock signed URL generation
        In production, this would generate actual S3 signed URLs
        """
        try:
            # For mock, just return the original URL
            logger.info(f"Mock signed URL generated for: {file_key}")
            return file_key
        except Exception as e:
            logger.error(f"Mock signed URL generation failed: {str(e)}")
            raise
    
    def get_default_image_url(self, post_type: str = "general") -> str:
        """Get a default image URL based on post type"""
        type_mapping = {
            "issue": self.MOCK_IMAGES[1],  # Road maintenance
            "announcement": self.MOCK_IMAGES[0],  # City infrastructure
            "news": self.MOCK_IMAGES[2],  # City skyline
            "accomplishment": self.MOCK_IMAGES[3],  # Community park
        }
        return type_mapping.get(post_type, self.MOCK_IMAGES[0])
    
    def get_default_video_url(self) -> str:
        """Get a default video URL"""
        return self.MOCK_VIDEOS[0]


# Global instance
s3_service = MockS3Service()
