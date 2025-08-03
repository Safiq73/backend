"""
Advanced Analytics API Endpoints
Provides comprehensive analytics and insights for the CivicPulse platform
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.analytics_service import analytics_service
from app.services.auth_service import get_current_user_optional, get_current_user
from app.models.pydantic_models import UserResponse
from app.core.permission_decorators import require_permissions

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard", summary="Get Comprehensive Dashboard Analytics")
async def get_dashboard_analytics(
    time_period: str = Query("7d", description="Time period (1d, 7d, 30d)", regex="^(1d|7d|30d)$"),
    current_user: UserResponse = Depends(require_permissions("analytics.get"))
):
    """
    Get comprehensive analytics for the dashboard.
    
    This endpoint provides:
    - Platform metrics (users, posts, engagement)
    - Search analytics and trends
    - User behavior insights
    - Content performance
    - Real-time statistics
    
    **Requires authentication** for access to analytics data.
    """
    try:
        # For now, allow any authenticated user. In production, restrict to admins
        analytics_data = await analytics_service.get_comprehensive_dashboard_analytics(
            time_period=time_period,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "data": analytics_data,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Dashboard analytics failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analytics temporarily unavailable: {str(e)}"
        )

@router.get("/search-insights", summary="Get Detailed Search Insights")
async def get_search_insights(
    time_period: str = Query("7d", description="Time period (1d, 7d, 30d)", regex="^(1d|7d|30d)$"),
    current_user: UserResponse = Depends(require_permissions("analytics.get"))
):
    """
    Get detailed search insights and patterns.
    
    Provides insights on:
    - Search patterns by day of week
    - Query length analysis
    - Improving search terms
    - User search behavior
    
    **Requires authentication** for access to analytics data.
    """
    try:
        insights = await analytics_service.get_search_insights(
            time_period=time_period,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "data": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Search insights failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search insights temporarily unavailable: {str(e)}"
        )

@router.get("/real-time", summary="Get Real-time Platform Statistics")
async def get_real_time_stats(
    current_user: UserResponse = Depends(require_permissions("analytics.get"))
):
    """
    Get real-time platform statistics.
    
    Provides live data on:
    - Active users
    - Recent searches
    - Response times
    - Recent activity
    
    **Authentication optional** - some data requires authentication.
    """
    try:
        # Get real-time stats (some data available to everyone)
        stats = await analytics_service._get_real_time_stats()
        
        # Add more detailed stats for authenticated users
        if current_user:
            dashboard_data = await analytics_service.get_comprehensive_dashboard_analytics("1d")
            stats.update({
                "authenticated_data": {
                    "search_trends_24h": dashboard_data["search_analytics"]["search_trends"][-24:],
                    "platform_health": dashboard_data["platform_metrics"]
                }
            })
        
        return {
            "success": True,
            "data": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Real-time stats failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Real-time stats temporarily unavailable: {str(e)}"
        )

@router.post("/clear-cache", summary="Clear Analytics Cache")
async def clear_analytics_cache(
    current_user: UserResponse = Depends(require_permissions("analytics.clear_cache"))
):
    """
    Clear the analytics cache to force fresh data generation.
    
    **Requires authentication** - typically admin only in production.
    """
    try:
        await analytics_service.clear_cache()
        
        return {
            "success": True,
            "message": "Analytics cache cleared successfully",
            "cleared_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/health", summary="Analytics Service Health Check")
async def analytics_health_check():
    """
    Health check endpoint for the analytics service.
    
    Returns the current status of analytics functionality.
    """
    try:
        # Try to get basic stats to verify service health
        stats = await analytics_service._get_real_time_stats()
        
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.utcnow().isoformat(),
            "database_connection": "ok",
            "cache_status": "ok",
            "sample_data": {
                "active_users_last_hour": stats.get("active_users_last_hour", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "analytics",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
