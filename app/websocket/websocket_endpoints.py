"""
WebSocket Endpoints for Real-time Search and Analytics
Handles WebSocket connections for live search updates and analytics
"""

import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.routing import APIRouter
from app.websocket.connection_manager import connection_manager, EntityType
from app.websocket.search_events import search_event_generator
from app.services.auth_service import get_current_user_optional
from app.models.pydantic_models import UserResponse

# Import WebSocket configuration
from app.core.websocket_config import get_websocket_config, WebSocketMode

# Import analytics endpoints
from app.websocket.analytics_endpoints import router as analytics_router

logger = logging.getLogger(__name__)

router = APIRouter()

# Include analytics WebSocket endpoints
router.include_router(analytics_router, prefix="/ws", tags=["analytics-websocket"])

@router.websocket("/ws/search")
async def websocket_search_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time search updates
    
    Optional authentication via token parameter
    """
    # Check if WebSocket is enabled
    config = get_websocket_config()
    if not config.is_websocket_enabled():
        logger.warning("WebSocket connection rejected - WebSocket service disabled")
        await websocket.close(code=1008, reason="WebSocket service disabled")
        return
    
    # Optional user authentication
    current_user = None
    if token:
        try:
            # You might need to adapt this based on your auth implementation
            # For now, we'll make it optional
            pass
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
    
    connection_id = None
    
    try:
        # Accept connection
        user_id = current_user.id if current_user else None
        connection_id = await connection_manager.connect(websocket, user_id)
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Start event monitoring if not already running
        if not search_event_generator.monitoring:
            import asyncio
            asyncio.create_task(search_event_generator.start_monitoring())
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process message
                await handle_websocket_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client {connection_id}: {e}")
                await send_error(websocket, "Invalid JSON format")
                
            except Exception as e:
                logger.error(f"Error handling message from {connection_id}: {e}")
                await send_error(websocket, "Internal server error")
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        if connection_id:
            await connection_manager.disconnect(connection_id)

async def handle_websocket_message(connection_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket message"""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        await handle_subscribe_message(connection_id, message)
    elif message_type == "unsubscribe":
        await handle_unsubscribe_message(connection_id, message)
    elif message_type == "ping":
        await handle_ping_message(connection_id, message)
    elif message_type == "get_stats":
        await handle_stats_message(connection_id, message)
    else:
        logger.warning(f"Unknown message type from {connection_id}: {message_type}")

async def handle_subscribe_message(connection_id: str, message: Dict[str, Any]):
    """Handle search subscription request"""
    try:
        subscription_data = message.get("data", {})
        
        subscription_id = subscription_data.get("subscription_id")
        query = subscription_data.get("query", "").strip()
        entity_types = subscription_data.get("entity_types", ["user", "post", "representative"])
        filters = subscription_data.get("filters", {})
        
        if not subscription_id or not query:
            await send_error_to_connection(connection_id, "Missing subscription_id or query")
            return
        
        # Validate entity types
        valid_entity_types = []
        for et in entity_types:
            try:
                EntityType(et)
                valid_entity_types.append(et)
            except ValueError:
                logger.warning(f"Invalid entity type: {et}")
        
        if not valid_entity_types:
            valid_entity_types = ["user", "post", "representative"]
        
        # Subscribe to search updates
        success = await connection_manager.subscribe_to_search(
            connection_id=connection_id,
            subscription_id=subscription_id,
            query=query,
            entity_types=valid_entity_types,
            filters=filters
        )
        
        if success:
            response = {
                "type": "subscription_confirmed",
                "subscription_id": subscription_id,
                "query": query,
                "entity_types": valid_entity_types,
                "timestamp": search_event_generator.last_check.get('users', "").isoformat() if hasattr(search_event_generator.last_check.get('users', ""), 'isoformat') else str(search_event_generator.last_check.get('users', ""))
            }
            
            connection_info = connection_manager.connections.get(connection_id)
            if connection_info:
                await connection_info.websocket.send_text(json.dumps(response))
                logger.info(f"Subscription confirmed: {connection_id} -> {query}")
        else:
            await send_error_to_connection(connection_id, "Failed to create subscription")
            
    except Exception as e:
        logger.error(f"Error handling subscribe message: {e}")
        await send_error_to_connection(connection_id, "Subscription error")

async def handle_unsubscribe_message(connection_id: str, message: Dict[str, Any]):
    """Handle search unsubscription request"""
    try:
        subscription_data = message.get("data", {})
        subscription_id = subscription_data.get("subscription_id")
        
        if not subscription_id:
            await send_error_to_connection(connection_id, "Missing subscription_id")
            return
        
        success = await connection_manager.unsubscribe_from_search(connection_id, subscription_id)
        
        response = {
            "type": "unsubscription_confirmed" if success else "unsubscription_failed",
            "subscription_id": subscription_id,
            "timestamp": search_event_generator.last_check.get('users', "").isoformat() if hasattr(search_event_generator.last_check.get('users', ""), 'isoformat') else str(search_event_generator.last_check.get('users', ""))
        }
        
        connection_info = connection_manager.connections.get(connection_id)
        if connection_info:
            await connection_info.websocket.send_text(json.dumps(response))
            logger.info(f"Unsubscription processed: {connection_id} -> {subscription_id}")
            
    except Exception as e:
        logger.error(f"Error handling unsubscribe message: {e}")
        await send_error_to_connection(connection_id, "Unsubscription error")

async def handle_ping_message(connection_id: str, message: Dict[str, Any]):
    """Handle ping message"""
    try:
        connection_info = connection_manager.connections.get(connection_id)
        if connection_info:
            connection_info.update_ping()
            
            response = {
                "type": "pong",
                "timestamp": search_event_generator.last_check.get('users', "").isoformat() if hasattr(search_event_generator.last_check.get('users', ""), 'isoformat') else str(search_event_generator.last_check.get('users', ""))
            }
            
            await connection_info.websocket.send_text(json.dumps(response))
            
    except Exception as e:
        logger.error(f"Error handling ping message: {e}")

async def handle_stats_message(connection_id: str, message: Dict[str, Any]):
    """Handle statistics request"""
    try:
        stats = connection_manager.get_connection_stats()
        
        response = {
            "type": "stats",
            "data": stats,
            "timestamp": search_event_generator.last_check.get('users', "").isoformat() if hasattr(search_event_generator.last_check.get('users', ""), 'isoformat') else str(search_event_generator.last_check.get('users', ""))
        }
        
        connection_info = connection_manager.connections.get(connection_id)
        if connection_info:
            await connection_info.websocket.send_text(json.dumps(response))
            
    except Exception as e:
        logger.error(f"Error handling stats message: {e}")
        await send_error_to_connection(connection_id, "Stats error")

async def send_error(websocket: WebSocket, error_message: str):
    """Send error message via WebSocket"""
    try:
        error_response = {
            "type": "error",
            "message": error_message,
            "timestamp": search_event_generator.last_check.get('users', "").isoformat() if hasattr(search_event_generator.last_check.get('users', ""), 'isoformat') else str(search_event_generator.last_check.get('users', ""))
        }
        await websocket.send_text(json.dumps(error_response))
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

async def send_error_to_connection(connection_id: str, error_message: str):
    """Send error message to a specific connection"""
    try:
        connection_info = connection_manager.connections.get(connection_id)
        if connection_info:
            await send_error(connection_info.websocket, error_message)
    except Exception as e:
        logger.error(f"Failed to send error to connection {connection_id}: {e}")

# Additional REST endpoints for WebSocket management
@router.get("/ws/search/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = connection_manager.get_connection_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket statistics"
        )

@router.post("/ws/search/broadcast")
async def broadcast_test_message(
    message: Dict[str, Any],
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """
    Broadcast a test message to all connected clients
    (Admin only for testing purposes)
    """
    try:
        # For testing - you might want to add admin check here
        test_message = {
            "type": "test_broadcast",
            "data": message,
            "timestamp": search_event_generator.last_check.get('users', "").isoformat() if hasattr(search_event_generator.last_check.get('users', ""), 'isoformat') else str(search_event_generator.last_check.get('users', ""))
        }
        
        # Send to all connections
        success_count = 0
        for connection_id, connection_info in connection_manager.connections.items():
            try:
                await connection_info.websocket.send_text(json.dumps(test_message))
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send test message to {connection_id}: {e}")
        
        return {
            "success": True,
            "message": "Test message broadcasted",
            "connections_reached": success_count,
            "total_connections": len(connection_manager.connections)
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting test message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast test message"
        )

@router.post("/ws/search/start-monitoring")
async def start_search_monitoring():
    """Start real-time search monitoring"""
    try:
        if not search_event_generator.monitoring:
            import asyncio
            asyncio.create_task(search_event_generator.start_monitoring())
            
        return {
            "success": True,
            "message": "Search monitoring started",
            "monitoring": search_event_generator.monitoring
        }
        
    except Exception as e:
        logger.error(f"Error starting search monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start search monitoring"
        )

@router.post("/ws/search/stop-monitoring")
async def stop_search_monitoring():
    """Stop real-time search monitoring"""
    try:
        await search_event_generator.stop_monitoring()
        
        return {
            "success": True,
            "message": "Search monitoring stopped",
            "monitoring": search_event_generator.monitoring
        }
        
    except Exception as e:
        logger.error(f"Error stopping search monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop search monitoring"
        )
