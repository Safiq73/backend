from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
import traceback
import asyncio
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.config_validator import validate_environment
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.development import DevelopmentMiddleware

# Add permission middleware import
try:
    from app.middleware.permission_middleware import PermissionMiddleware
    PERMISSION_MIDDLEWARE_AVAILABLE = True
except ImportError:
    PERMISSION_MIDDLEWARE_AVAILABLE = False
    print("⚠️  Permission middleware not available - running without permission checking")

from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.api.v1.api import api_router
from app.websocket.websocket_endpoints import router as websocket_router
from app.db.database import startup_db, shutdown_db, db_manager

# Validate configuration on startup
try:
    validate_environment()
    print("✅ Configuration validation completed successfully")
except (ValueError, KeyError, AttributeError) as e:
    print(f"❌ Configuration validation failed: {e}")
    
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
except (ValueError, ImportError, OSError) as e:
    print(f"❌ Logging setup failed: {e}")
    # Fallback to basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('app.main')
    logger.warning("Using fallback logging configuration")


async def _run_periodic_job(name: str, interval: int, func_sql: str):
    """Generic loop to run a SQL function periodically."""
    await asyncio.sleep(3)  # small delay after startup
    while True:
        try:
            if not settings.recs_enable_scheduler or not settings.enable_recommendations:
                await asyncio.sleep(interval)
                continue
            async with db_manager.get_connection() as conn:
                await conn.execute(func_sql)
                logger.info(f"Phase2 job '{name}' executed")
        except Exception as e:
            logger.error(f"Phase2 job '{name}' failed: {e}")
        await asyncio.sleep(interval)


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

    # Add permission middleware (temporarily disabled for stability)
    # The permission system is fully implemented and can be enabled via decorators
    if False and PERMISSION_MIDDLEWARE_AVAILABLE:
        app.add_middleware(PermissionMiddleware)
        logger.info("✅ Permission middleware enabled - API endpoints now protected")
    else:
        logger.info("🛡️  Permission system available via decorators (middleware disabled for stability)")

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
    
    # Include WebSocket router
    app.include_router(websocket_router, prefix="/api/v1")
    logger.info("WebSocket routes registered")

    # Register exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # app.add_exception_handler(Exception, general_exception_handler)
    logger.info("Exception handlers registered")
    

    # Register startup and shutdown events
    app.add_event_handler("startup", startup_db)
    app.add_event_handler("shutdown", shutdown_db)
    logger.info("Database lifecycle events registered")

    # Phase 2: schedule periodic jobs after DB startup
    scheduled_tasks = []

    @app.on_event("startup")
    async def start_phase2_jobs():
        if not settings.recs_enable_scheduler:
            logger.info("Phase2 scheduler disabled by config")
            return
        logger.info("Starting Phase2 scheduler jobs")
        scheduled_tasks.append(asyncio.create_task(_run_periodic_job(
            "post_quality",
            settings.recs_job_quality_interval_seconds,
            "SELECT update_post_quality_metrics();"
        )))
        scheduled_tasks.append(asyncio.create_task(_run_periodic_job(
            "user_topic_affinity",
            settings.recs_job_affinity_interval_seconds,
            "SELECT update_user_topic_affinities();"
        )))
        scheduled_tasks.append(asyncio.create_task(_run_periodic_job(
            "user_author_affinity",
            settings.recs_job_affinity_interval_seconds,
            "SELECT update_user_author_affinities();"
        )))
        # Optional: cleanup job to prune very old raw interactions
        scheduled_tasks.append(asyncio.create_task(_run_periodic_job(
            "cleanup_interactions",
            settings.recs_job_cleanup_interval_seconds,
            f"DELETE FROM interactions WHERE created_at < NOW() - INTERVAL '{settings.recs_cleanup_retention_days} days';"
        )))
        # Optional: refresh trending MV if exists
        scheduled_tasks.append(asyncio.create_task(_run_periodic_job(
            "refresh_trending",
            settings.recs_job_quality_interval_seconds,
            "REFRESH MATERIALIZED VIEW CONCURRENTLY trending_posts;"
        )))

    @app.on_event("shutdown")
    async def stop_phase2_jobs():
        for task in scheduled_tasks:
            task.cancel()
        if scheduled_tasks:
            await asyncio.gather(*scheduled_tasks, return_exceptions=True)
        logger.info("Phase2 scheduler jobs stopped")

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



"""



"""