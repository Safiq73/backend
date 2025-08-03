from pydantic_settings import BaseSettings
from typing import Optional, List
import os

# Ensure we load from the correct .env file
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')


class Settings(BaseSettings):
    # App
    app_name: str = "CivicPulse API"
    debug: bool = True
    version: str = "1.0.0"
    environment: str = "development"  # Explicitly set environment mode
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Logging - Enhanced for local development
    log_level: str = "DEBUG"  # More verbose logging for development
    log_file: Optional[str] = "logs/civicpulse.log"
    enable_request_logging: bool = True
    enable_performance_logging: bool = True
    enable_console_logging: bool = True  # Force console output for debugging
    
    # Security - Relaxed for local development
    secret_key: str = "development-secret-key-change-in-production-12345678901234567890"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    enable_authentication: bool = False  # Disable auth for local testing
    enable_email_verification: bool = False  # Disable email verification
    enable_otp_verification: bool = False  # Disable OTP verification
    enable_ip_blacklisting: bool = False  # Disable IP blacklisting
    enable_security_headers: bool = False  # Disable security headers for local dev
    
    # Database - PostgreSQL with PostGIS
    database_url: str = "postgresql://mahammad.safiq@localhost:5432/civicpulse"
    
    # CORS - Fully open for local development
    allowed_origins: List[str] = ["*"]  # Allow all origins for development
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]  # Allow all methods
    allow_headers: List[str] = ["*"]  # Allow all headers
    
    # File Upload & Media
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = ["image/jpeg", "image/png", "image/gif", "video/mp4", "video/webm"]
    max_files_per_post: int = 10  # Maximum files per post
    
    # External Services (AWS S3 for media storage)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_s3_endpoint_url: Optional[str] = None  # For local development with MinIO
    s3_max_image_size: int = 10 * 1024 * 1024  # 10MB for images
    s3_max_video_size: int = 100 * 1024 * 1024  # 100MB for videos
    
    # Cloudinary (for file uploads)
    cloudinary_cloud_name: Optional[str] = None
    cloudinary_api_key: Optional[str] = None
    cloudinary_api_secret: Optional[str] = None
    
    # Email (for notifications)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # Search & Analytics
    search_results_per_page: int = 20
    max_search_results: int = 1000
    
    # Spatial queries
    default_search_radius_meters: int = 1000  # 1km default radius for location searches
    max_search_radius_meters: int = 50000     # 50km max radius
    
    # News API Configuration
    newsapi_key: Optional[str] = None
    newsapi_country: str = "in"  # Default country for news
    
    # Mixed Content Configuration
    posts_ratio: float = 0.4  # 40% posts, 60% news by default
    min_posts_per_page: int = 0  # Minimum posts per page
    max_posts_per_page: int = 20  # Maximum posts per page
    
    # Rate limiting - Disabled for local development
    rate_limit_per_minute: int = 0  # 0 = disabled
    rate_limit_per_hour: int = 0    # 0 = disabled
    enable_rate_limiting: bool = False  # Explicitly disable rate limiting
    
    # Performance
    database_pool_size: int = 20
    database_max_overflow: int = 30
    query_timeout_seconds: int = 30
    
    # WebSocket Configuration
    websocket_mode: str = "disabled"
    enable_realtime: bool = False
    enable_search_ws: bool = False
    enable_analytics_ws: bool = False
    enable_notifications_ws: bool = False
    rest_polling_interval: int = 30
    
    # Permission System
    enable_permission_middleware: bool = False
    permission_fail_open: bool = True
    
    class Config:
        env_file = ENV_FILE_PATH
        case_sensitive = False


settings = Settings()
