from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import logging
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.config_validator import validate_environment
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.development import DevelopmentMiddleware
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.api.v1.api import api_router
from app.db.database import startup_db, shutdown_db

# Validate configuration on startup
try:
    validate_environment()
    print("✅ Configuration validation completed successfully")
except Exception as e:
    print(f"❌ Configuration validation failed: {e}")
    if not getattr(settings, 'debug', True):
        raise
    print("⚠️  Continuing in debug mode with configuration warnings...")

# Setup logging with enhanced verbosity for development
try:
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file,
        enable_console=getattr(settings, 'enable_console_logging', True)
    )
    logger = get_logger('app.main')
    logger.info("Logging configuration completed successfully")
except Exception as e:
    print(f"❌ Logging setup failed: {e}")
    # Fallback to basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('app.main')
    logger.warning("Using fallback logging configuration")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    logger.info(f"Creating FastAPI application | Debug: {settings.debug} | Version: {settings.version}")
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        docs_url="/docs",  # Always enable docs in development
        redoc_url="/redoc",  # Always enable redoc in development
        openapi_url="/openapi.json",  # Always enable OpenAPI spec
    )

    # Add development middleware for local testing
    if settings.debug or getattr(settings, 'environment', '') == 'development':
        app.add_middleware(
            DevelopmentMiddleware,
            enable_auth=getattr(settings, 'enable_authentication', False)
        )
        logger.info("Development middleware enabled for local testing")

    # Conditionally add security headers middleware (disabled for local development)
    if getattr(settings, 'enable_security_headers', True):
        app.add_middleware(SecurityHeadersMiddleware)
        logger.info("Security headers middleware enabled")
    else:
        logger.info("Security headers middleware disabled for local development")

    # Conditionally add rate limiting middleware (disabled for local development)
    if getattr(settings, 'enable_rate_limiting', True) and settings.rate_limit_per_minute > 0:
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.rate_limit_per_minute,
            period=60
        )
        logger.info("Rate limiting middleware enabled")
    else:
        logger.info("Rate limiting middleware disabled for local development")

    # Add logging middleware
    if settings.enable_request_logging or settings.enable_performance_logging:
        app.add_middleware(
            LoggingMiddleware,
            enable_request_logging=settings.enable_request_logging,
            enable_performance_logging=settings.enable_performance_logging
        )
        logger.info("Logging middleware enabled")

    # Set up CORS - Fully open for local development
    cors_origins = getattr(settings, 'allowed_origins', ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=getattr(settings, 'allow_credentials', True),
        allow_methods=getattr(settings, 'allow_methods', ["*"]),
        allow_headers=getattr(settings, 'allow_headers', ["*"]),
        expose_headers=["*"],
    )
    logger.info(f"CORS middleware configured with origins: {cors_origins} (fully open for development)")

    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("API routes registered")

    # Register exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    logger.info("Exception handlers registered")

    # Register startup and shutdown events
    app.add_event_handler("startup", startup_db)
    app.add_event_handler("shutdown", shutdown_db)
    logger.info("Database lifecycle events registered")

    # Global OPTIONS handler for CORS preflight requests
    @app.options("/{path:path}")
    async def handle_options(path: str):
        return {"message": "OK"}

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.version
        }

    logger.info("FastAPI application created successfully")
    return app


app = create_application()
