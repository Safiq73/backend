"""
Updated FastAPI application main.py with permission system integration

This demonstrates how to integrate the permission middleware and initialize 
the permission system on application startup.
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
import traceback
from contextlib import asynccontextmanager

# Existing imports
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.config_validator import validate_environment
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.development import DevelopmentMiddleware

# New permission middleware
from app.middleware.permission_middleware import permission_middleware

from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.api.v1.api import api_router
from app.websocket.websocket_endpoints import router as websocket_router
from app.db.database import startup_db, shutdown_db

# Permission system imports
from app.services.permission_service import PermissionService

# Validate configuration on startup
try:
    validate_environment()
    print("✅ Configuration validation completed successfully")
except (ValueError, KeyError, AttributeError) as e:
    print(f"❌ Configuration validation failed: {e}")
    print("⚠️  Continuing in debug mode with configuration warnings...")

# Setup logging
try:
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file,
        enable_console=getattr(settings, 'enable_console_logging', True)
    )
    logger = get_logger('app.main')
    logger.info("Logging configuration completed successfully")
except (ValueError, ImportError, OSError) as e:
    print(f"❌ Logging setup failed: {e}")
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('app.main')
    logger.warning("Using fallback logging configuration")

async def startup_events():
    """Application startup events"""
    logger.info("Starting application startup sequence...")
    
    # Initialize database
    await startup_db()
    
    # Initialize permission system
    await initialize_permission_system()
    
    logger.info("Application startup completed successfully")

async def shutdown_events():
    """Application shutdown events"""
    logger.info("Starting application shutdown sequence...")
    
    # Shutdown database
    await shutdown_db()
    
    logger.info("Application shutdown completed")

async def initialize_permission_system():
    """Initialize the permission system on startup"""
    try:
        logger.info("Initializing permission system...")
        
        permission_service = PermissionService()
        
        # Sync permissions from registry to database
        success = await permission_service.sync_permissions_from_registry()
        
        if success:
            logger.info("Permission system initialized successfully")
        else:
            logger.error("Failed to initialize permission system")
            
    except Exception as e:
        logger.error(f"Error initializing permission system: {e}")
        # Don't fail startup for permission system issues in development
        if not settings.debug:
            raise

# Permission middleware for automatic route permission checking
class PermissionCheckMiddleware:
    """Middleware to automatically check permissions for API routes"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        # Skip permission check for certain routes
        skip_paths = [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/api/v1/auth/register", "/api/v1/auth/login"
        ]
        
        # Skip for static files and health checks
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Skip for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        try:
            # Check permissions through middleware
            # Note: This is simplified - in production you might want more sophisticated logic
            await permission_middleware.check_route_permission(request)
            
        except HTTPException as e:
            # Return permission error
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Permission middleware error: {e}")
            # Allow request to continue if permission check fails (fail open in development)
            if not settings.debug:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Permission check failed"}
                )
        
        return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    await startup_events()
    yield
    # Shutdown
    await shutdown_events()

def create_application() -> FastAPI:
    """Create and configure FastAPI application with permission system"""
    
    logger.info(f"Creating FastAPI application | Debug: {settings.debug} | Version: {settings.version}")
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan  # Use lifespan for startup/shutdown events
    )

    # Add permission middleware (before other middleware that might modify request)
    if getattr(settings, 'enable_permission_middleware', True):
        app.add_middleware(PermissionCheckMiddleware)
        logger.info("Permission middleware enabled")

    # Add development middleware for local testing
    if settings.debug or getattr(settings, 'environment', '') == 'development':
        app.add_middleware(
            DevelopmentMiddleware,
            enable_auth=getattr(settings, 'enable_authentication', False)
        )
        logger.info("Development middleware enabled for local testing")

    # Security headers middleware
    if getattr(settings, 'enable_security_headers', True):
        app.add_middleware(SecurityHeadersMiddleware)
        logger.info("Security headers middleware enabled")

    # CORS middleware
    cors_origins = getattr(settings, 'allowed_origins', ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=getattr(settings, 'allow_credentials', True),
        allow_methods=getattr(settings, 'allow_methods', ["*"]),
        allow_headers=getattr(settings, 'allow_headers', ["*"]),
        expose_headers=["*"],
    )
    logger.info(f"CORS middleware configured with origins: {cors_origins}")

    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("API routes registered")
    
    # Include WebSocket router
    app.include_router(websocket_router, prefix="/api/v1")
    logger.info("WebSocket routes registered")

    # Register exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    logger.info("Exception handlers registered")

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
            "version": settings.version,
            "permission_system": "enabled" if getattr(settings, 'enable_permission_middleware', True) else "disabled"
        }

    # Permission system status endpoint (for debugging)
    @app.get("/api/v1/system/permissions/status")
    async def permission_system_status():
        """Get permission system status (admin only in production)"""
        try:
            permission_service = PermissionService()
            
            # Get some basic stats
            from app.core.permissions import API_PERMISSIONS_REGISTRY
            
            return {
                "status": "active",
                "registered_permissions": len(API_PERMISSIONS_REGISTRY),
                "permission_categories": list(set(p.category for p in API_PERMISSIONS_REGISTRY)),
                "middleware_enabled": getattr(settings, 'enable_permission_middleware', True)
            }
        except Exception as e:
            logger.error(f"Error getting permission system status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    logger.info("FastAPI application created successfully with permission system")
    return app

app = create_application()

# Optional: Add route to manually sync permissions (for development/admin)
@app.post("/api/v1/admin/permissions/sync")
async def sync_permissions():
    """Manually sync permissions from registry (admin only)"""
    try:
        permission_service = PermissionService()
        success = await permission_service.sync_permissions_from_registry()
        
        if success:
            return {"message": "Permissions synced successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to sync permissions")
            
    except Exception as e:
        logger.error(f"Error syncing permissions: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing permissions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
