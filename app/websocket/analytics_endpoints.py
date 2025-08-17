"""
Analytics WebSocket Endpoints
Provides WebSocket endpoints for real-time analytics updates
"""

import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.websocket.connection_manager import connection_manager
from app.websocket.analytics_monitor import analytics_monitor, AnalyticsEventType
from app.services.auth_service import get_current_user_optional, get_current_user
from app.models.pydantic_models import UserResponse

# Import WebSocket configuration
from app.core.websocket_config import get_websocket_config

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/analytics")
async def websocket_analytics_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time analytics updates.
    
    Supports:
    - Real-time platform metrics
    - Search analytics updates  
    - User activity monitoring
    - System alerts
    
    Message format:
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "analytics_types": ["platform_metrics", "search_trends", "user_activity", "system_alert"],
        "options": {}
    }
    """
    # Check if WebSocket is enabled
    config = get_websocket_config()
    if not config.is_websocket_enabled():
        logger.warning("WebSocket analytics connection rejected - WebSocket service disabled")
        await websocket.close(code=1008, reason="WebSocket service disabled")
        return
    connection_id = None
    user_id = None
    
    try:
        # Authenticate user if token provided
        if token:
            try:
                # You'll need to implement token-based WebSocket auth
                # For now, we'll accept the connection
                pass
            except Exception as e:
                logger.warning(f"WebSocket analytics auth failed: {e}")

        # Accept WebSocket connection
        connection_id = await connection_manager.connect(websocket, user_id)
        logger.info(f"Analytics WebSocket connected: {connection_id}")

        # Send welcome message
        await websocket.send_text(json.dumps({
            "event_type": "connection_established",
            "connection_id": connection_id,
            "message": "Analytics WebSocket connection established",
            "available_analytics": [
                AnalyticsEventType.PLATFORM_METRICS,
                AnalyticsEventType.SEARCH_TRENDS,
                AnalyticsEventType.USER_ACTIVITY,
                AnalyticsEventType.SYSTEM_ALERT,
                AnalyticsEventType.CONTENT_UPDATE
            ],
            "timestamp": analytics_monitor._get_current_timestamp()
        }))

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_analytics_message(connection_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "event_type": "error",
                    "error": "Invalid JSON format",
                    "timestamp": analytics_monitor._get_current_timestamp()
                }))
            except Exception as e:
                logger.error(f"Error handling analytics WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "event_type": "error", 
                    "error": str(e),
                    "timestamp": analytics_monitor._get_current_timestamp()
                }))
                
    except WebSocketDisconnect:
        logger.info(f"Analytics WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Analytics WebSocket error: {e}")
    finally:
        if connection_id:
            # Unsubscribe from all analytics
            await analytics_monitor.unsubscribe_from_analytics(connection_id)
            # Disconnect from connection manager
            await connection_manager.disconnect(connection_id)

async def handle_analytics_message(connection_id: str, message: Dict[str, Any]):
    """Handle incoming analytics WebSocket messages"""
    
    action = message.get("action")
    
    if action == "subscribe":
        analytics_types = message.get("analytics_types", [])
        if analytics_types:
            await analytics_monitor.subscribe_to_analytics(connection_id, analytics_types)
            
            # Send confirmation
            await connection_manager._send_to_connection(connection_id, {
                "event_type": "subscription_confirmed",
                "analytics_types": analytics_types,
                "message": f"Subscribed to {len(analytics_types)} analytics types",
                "timestamp": analytics_monitor._get_current_timestamp()
            })
        else:
            await connection_manager._send_to_connection(connection_id, {
                "event_type": "error",
                "error": "No analytics types specified for subscription",
                "timestamp": analytics_monitor._get_current_timestamp()
            })
    
    elif action == "unsubscribe":
        analytics_types = message.get("analytics_types")
        await analytics_monitor.unsubscribe_from_analytics(connection_id, analytics_types)
        
        # Send confirmation
        await connection_manager._send_to_connection(connection_id, {
            "event_type": "unsubscription_confirmed",
            "analytics_types": analytics_types or "all",
            "timestamp": analytics_monitor._get_current_timestamp()
        })
    
    elif action == "ping":
        # Respond with pong and current stats
        stats = analytics_monitor.get_analytics_stats()
        await connection_manager._send_to_connection(connection_id, {
            "event_type": "pong",
            "analytics_stats": stats,
            "timestamp": analytics_monitor._get_current_timestamp()
        })
    
    elif action == "get_current_metrics":
        # Send current platform metrics
        from app.services.analytics_service import analytics_service
        current_metrics = await analytics_service._get_real_time_stats()
        
        await connection_manager._send_to_connection(connection_id, {
            "event_type": "current_metrics",
            "data": current_metrics,
            "timestamp": analytics_monitor._get_current_timestamp()
        })
    
    else:
        await connection_manager._send_to_connection(connection_id, {
            "event_type": "error",
            "error": f"Unknown action: {action}",
            "supported_actions": ["subscribe", "unsubscribe", "ping", "get_current_metrics"],
            "timestamp": analytics_monitor._get_current_timestamp()
        })

@router.post("/start-monitoring", summary="Start Real-time Analytics Monitoring")
async def start_analytics_monitoring(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Start real-time analytics monitoring.
    
    **Requires authentication** - typically admin only.
    """
    try:
        await analytics_monitor.start_monitoring()
        
        return {
            "success": True,
            "message": "Analytics monitoring started",
            "monitoring": analytics_monitor.is_monitoring,
            "started_at": analytics_monitor._get_current_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to start analytics monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start monitoring: {str(e)}"
        )

@router.post("/stop-monitoring", summary="Stop Real-time Analytics Monitoring")
async def stop_analytics_monitoring(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Stop real-time analytics monitoring.
    
    **Requires authentication** - typically admin only.
    """
    try:
        await analytics_monitor.stop_monitoring()
        
        return {
            "success": True,
            "message": "Analytics monitoring stopped",
            "monitoring": analytics_monitor.is_monitoring,
            "stopped_at": analytics_monitor._get_current_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop analytics monitoring: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop monitoring: {str(e)}"
        )

@router.get("/stats", summary="Get Analytics Monitoring Statistics")
async def get_analytics_stats(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Get current analytics monitoring statistics.
    
    Shows:
    - Monitoring status
    - Active subscriptions
    - Connection counts
    """
    try:
        stats = analytics_monitor.get_analytics_stats()
        connection_stats = connection_manager.get_connection_stats()
        
        return {
            "success": True,
            "data": {
                "analytics_monitoring": stats,
                "connection_manager": connection_stats,
                "websocket_health": "ok"
            },
            "timestamp": analytics_monitor._get_current_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to get analytics stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )

@router.post("/broadcast-test", summary="Test Analytics Broadcast")
async def test_analytics_broadcast(
    event_type: str,
    message: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Test analytics broadcasting functionality.
    
    **Requires authentication** - for testing purposes.
    """
    try:
        test_data = {
            "type": "test_broadcast",
            "message": message,
            "triggered_by": current_user.username,
            "timestamp": analytics_monitor._get_current_timestamp()
        }
        
        await analytics_monitor._broadcast_analytics_event(event_type, test_data)
        
        return {
            "success": True,
            "message": f"Test broadcast sent for event type: {event_type}",
            "data": test_data
        }
        
    except Exception as e:
        logger.error(f"Failed to send test broadcast: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test broadcast: {str(e)}"
        )

# Add timestamp helper to analytics_monitor if not already present
def _get_current_timestamp():
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat()

# Monkey patch the method if it doesn't exist
if not hasattr(analytics_monitor, '_get_current_timestamp'):
    analytics_monitor._get_current_timestamp = _get_current_timestamp
