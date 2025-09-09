from fastapi import APIRouter
from app.api.endpoints import auth, users, posts, comments, notifications, analytics, titles, representatives, follows, search, admin, upload, recommendations, accounts

# Import eVote endpoints
try:
    from app.api.endpoints import representative_evotes
    EVOTE_ENDPOINTS_AVAILABLE = True
except ImportError:
    EVOTE_ENDPOINTS_AVAILABLE = False

# Import admin S3 endpoints (optional)
try:
    from app.api.endpoints import admin_s3
    ADMIN_S3_ENDPOINTS_AVAILABLE = True
except ImportError:
    ADMIN_S3_ENDPOINTS_AVAILABLE = False

# Import permission management endpoints (optional)
try:
    from app.api.endpoints import permission_management
    PERMISSION_ENDPOINTS_AVAILABLE = True
except ImportError:
    PERMISSION_ENDPOINTS_AVAILABLE = False

# Import admin endpoints (optional)
try:
    from app.api.endpoints import admin
    ADMIN_ENDPOINTS_AVAILABLE = True
except ImportError:
    ADMIN_ENDPOINTS_AVAILABLE = False

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(titles.router, prefix="/titles", tags=["titles"])
api_router.include_router(representatives.router, prefix="/representatives", tags=["representatives"])
api_router.include_router(follows.router, tags=["follows"])
api_router.include_router(search.router, prefix="/search", tags=["search"])

# Include upload endpoints
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])

# Include recommendations endpoints
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])

# Include eVote endpoints if available
if EVOTE_ENDPOINTS_AVAILABLE:
    api_router.include_router(representative_evotes.router, tags=["evotes"])

# Include admin S3 endpoints if available
if ADMIN_S3_ENDPOINTS_AVAILABLE:
    api_router.include_router(admin_s3.router, tags=["admin-s3"])

# Include permission management endpoints if available
if PERMISSION_ENDPOINTS_AVAILABLE:
    api_router.include_router(permission_management.router, prefix="/permissions", tags=["permissions"])

# Include admin endpoints if available
if ADMIN_ENDPOINTS_AVAILABLE:
    api_router.include_router(admin.router, tags=["admin"])
