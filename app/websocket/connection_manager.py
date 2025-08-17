"""
WebSocket Connection Manager for Real-time Search Updates
Handles WebSocket connections, subscriptions, and broadcasting
"""

import json
import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
from enum import Enum

# Import WebSocket configuration
from ..core.websocket_config import get_websocket_config, WebSocketMode

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Types of real-time search events"""
    NEW_RESULT = "new_result"
    UPDATED_RESULT = "updated_result"
    REMOVED_RESULT = "removed_result"
    ENGAGEMENT_UPDATE = "engagement_update"
    SEARCH_TRENDING = "search_trending"
    CONNECTION_STATUS = "connection_status"

class EntityType(str, Enum):
    """Entity types for search updates"""
    USER = "user"
    POST = "post"
    REPRESENTATIVE = "representative"

@dataclass
class SearchUpdateEvent:
    """Real-time search update event"""
    event_type: EventType
    entity_type: EntityType
    entity_id: str
    data: Dict[str, Any]
    affected_queries: List[str]
    timestamp: datetime
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "event_type": self.event_type.value,
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "data": self.data,
            "affected_queries": self.affected_queries,
            "timestamp": self.timestamp.isoformat(),
            "relevance_score": self.relevance_score,
            "metadata": self.metadata or {}
        }

@dataclass
class SearchSubscription:
    """Search subscription for a WebSocket connection"""
    query: str
    entity_types: List[EntityType]
    filters: Dict[str, Any]
    created_at: datetime
    last_update: datetime

class ConnectionInfo:
    """Information about a WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, user_id: Optional[str] = None):
        self.websocket = websocket
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.subscriptions: Dict[str, SearchSubscription] = {}
        self.message_count = 0
        self.is_active = True

    def add_subscription(self, subscription_id: str, subscription: SearchSubscription):
        """Add a search subscription"""
        self.subscriptions[subscription_id] = subscription
        logger.debug(f"Added subscription {subscription_id} for query: {subscription.query}")

    def remove_subscription(self, subscription_id: str):
        """Remove a search subscription"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            logger.debug(f"Removed subscription {subscription_id}")

    def update_ping(self):
        """Update last ping timestamp"""
        self.last_ping = datetime.utcnow()

    def is_subscribed_to_query(self, query: str) -> bool:
        """Check if connection is subscribed to a specific query"""
        return any(sub.query.lower() == query.lower() for sub in self.subscriptions.values())

class ConnectionManager:
    """Manages WebSocket connections and real-time search updates"""

    def __init__(self):
        # Active WebSocket connections
        self.connections: Dict[str, ConnectionInfo] = {}
        
        # Query subscriptions - maps query to connection IDs
        self.query_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Entity subscriptions - maps entity_type to connection IDs
        self.entity_subscriptions: Dict[EntityType, Set[str]] = defaultdict(set)
        
        # Rate limiting
        self.rate_limits: Dict[str, List[datetime]] = defaultdict(list)
        self.max_messages_per_minute = 60
        
        # Update batching
        self.pending_updates: Dict[str, List[SearchUpdateEvent]] = defaultdict(list)
        self.batch_interval = 2.0  # seconds
        
        # Start background tasks
        self._cleanup_task = None
        self._batch_task = None

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """Accept a new WebSocket connection"""
        config = get_websocket_config()
        
        # Check if WebSocket is enabled
        if not config.is_websocket_enabled():
            logger.warning("WebSocket connection rejected - WebSocket disabled")
            await websocket.close(code=1008, reason="WebSocket service disabled")
            raise RuntimeError("WebSocket service is disabled")
        
        # Check connection limits
        if len(self.connections) >= config.max_connections:
            logger.warning("WebSocket connection rejected - connection limit reached")
            await websocket.close(code=1008, reason="Connection limit reached")
            raise RuntimeError("Maximum connections reached")
        
        await websocket.accept()
        
        connection_id = f"conn_{id(websocket)}_{datetime.utcnow().timestamp()}"
        connection_info = ConnectionInfo(websocket, user_id)
        
        self.connections[connection_id] = connection_info
        
        logger.info(f"WebSocket connected: {connection_id}, User: {user_id}")
        
        # Send connection confirmation
        await self._send_to_connection(connection_id, {
            "event_type": EventType.CONNECTION_STATUS.value,
            "status": "connected",
            "connection_id": connection_id,
            "websocket_mode": config.mode.value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Deliver pending notifications if user is authenticated
        if user_id:
            from app.services.notification_service import notification_service
            await notification_service.deliver_pending_notifications(user_id, connection_id)
        
        # Start background tasks if not running
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        if not self._batch_task:
            self._batch_task = asyncio.create_task(self._batch_updates())
        
        return connection_id

    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id in self.connections:
            connection_info = self.connections[connection_id]
            
            # Remove from all subscriptions
            for subscription_id in list(connection_info.subscriptions.keys()):
                await self._unsubscribe_from_query(connection_id, subscription_id)
            
            # Remove connection
            del self.connections[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe_to_search(
        self, 
        connection_id: str, 
        subscription_id: str,
        query: str, 
        entity_types: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Subscribe a connection to search updates for a specific query"""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        # Create subscription
        subscription = SearchSubscription(
            query=query.lower().strip(),
            entity_types=[EntityType(et) for et in entity_types],
            filters=filters or {},
            created_at=datetime.utcnow(),
            last_update=datetime.utcnow()
        )
        
        # Add to connection
        connection_info.add_subscription(subscription_id, subscription)
        
        # Add to query subscriptions
        normalized_query = query.lower().strip()
        self.query_subscriptions[normalized_query].add(connection_id)
        
        # Add to entity subscriptions
        for entity_type in subscription.entity_types:
            self.entity_subscriptions[entity_type].add(connection_id)
        
        logger.info(f"Subscription added: {connection_id} -> {query} ({entity_types})")
        
        return True

    async def unsubscribe_from_search(self, connection_id: str, subscription_id: str) -> bool:
        """Remove a search subscription"""
        return await self._unsubscribe_from_query(connection_id, subscription_id)

    async def _unsubscribe_from_query(self, connection_id: str, subscription_id: str) -> bool:
        """Internal method to remove subscription"""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        if subscription_id not in connection_info.subscriptions:
            return False
        
        subscription = connection_info.subscriptions[subscription_id]
        
        # Remove from query subscriptions
        normalized_query = subscription.query
        if normalized_query in self.query_subscriptions:
            self.query_subscriptions[normalized_query].discard(connection_id)
            if not self.query_subscriptions[normalized_query]:
                del self.query_subscriptions[normalized_query]
        
        # Remove from entity subscriptions
        for entity_type in subscription.entity_types:
            self.entity_subscriptions[entity_type].discard(connection_id)
            if not self.entity_subscriptions[entity_type]:
                del self.entity_subscriptions[entity_type]
        
        # Remove from connection
        connection_info.remove_subscription(subscription_id)
        
        logger.info(f"Subscription removed: {connection_id} -> {subscription_id}")
        return True

    async def broadcast_search_update(self, event: SearchUpdateEvent):
        """Broadcast a search update to relevant subscribers"""
        config = get_websocket_config()
        
        # Skip broadcasting if WebSocket is disabled
        if not config.should_use_websocket("search"):
            logger.debug(f"Skipping WebSocket broadcast - search WebSocket disabled")
            return
        
        logger.debug(f"Broadcasting {event.event_type} for {event.entity_type}:{event.entity_id}")
        
        # Find relevant connections
        relevant_connections = set()
        
        # Add connections subscribed to affected queries
        for query in event.affected_queries:
            normalized_query = query.lower().strip()
            if normalized_query in self.query_subscriptions:
                relevant_connections.update(self.query_subscriptions[normalized_query])
        
        # Add connections subscribed to the entity type
        if event.entity_type in self.entity_subscriptions:
            relevant_connections.update(self.entity_subscriptions[event.entity_type])
        
        # Add to pending updates for batching
        for connection_id in relevant_connections:
            if connection_id in self.connections:
                self.pending_updates[connection_id].append(event)
        
        logger.debug(f"Update queued for {len(relevant_connections)} connections")

    async def _batch_updates(self):
        """Background task to batch and send updates"""
        while True:
            try:
                if self.pending_updates:
                    # Process all pending updates
                    for connection_id, events in list(self.pending_updates.items()):
                        if events and connection_id in self.connections:
                            # Group events by type and entity for efficiency
                            batched_events = self._group_events(events)
                            
                            for batch in batched_events:
                                await self._send_to_connection(connection_id, {
                                    "event_type": "batch_update",
                                    "events": [event.to_dict() for event in batch],
                                    "batch_size": len(batch),
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                    
                    # Clear pending updates
                    self.pending_updates.clear()
                
                await asyncio.sleep(self.batch_interval)
                
            except Exception as e:
                logger.error(f"Error in batch updates: {e}")
                await asyncio.sleep(5)

    def _group_events(self, events: List[SearchUpdateEvent]) -> List[List[SearchUpdateEvent]]:
        """Group events into batches for efficient transmission"""
        # Simple batching - group by entity type
        batches = defaultdict(list)
        
        for event in events:
            batch_key = f"{event.entity_type}_{event.event_type}"
            batches[batch_key].append(event)
        
        # Convert to list of batches, max 10 events per batch
        result = []
        for batch_events in batches.values():
            for i in range(0, len(batch_events), 10):
                result.append(batch_events[i:i+10])
        
        return result

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection with rate limiting"""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        # Rate limiting check
        if not self._check_rate_limit(connection_id):
            logger.warning(f"Rate limit exceeded for connection {connection_id}")
            return False
        
        try:
            await connection_info.websocket.send_text(json.dumps(message))
            connection_info.message_count += 1
            connection_info.update_ping()
            return True
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected during send: {connection_id}")
            await self.disconnect(connection_id)
            return False
            
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            return False

    def _check_rate_limit(self, connection_id: str) -> bool:
        """Check if connection is within rate limits"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old timestamps
        self.rate_limits[connection_id] = [
            ts for ts in self.rate_limits[connection_id] 
            if ts > minute_ago
        ]
        
        # Check limit
        if len(self.rate_limits[connection_id]) >= self.max_messages_per_minute:
            return False
        
        # Add current timestamp
        self.rate_limits[connection_id].append(now)
        return True

    async def _cleanup_inactive_connections(self):
        """Background task to clean up inactive connections"""
        while True:
            try:
                now = datetime.utcnow()
                inactive_threshold = now - timedelta(minutes=30)
                
                inactive_connections = []
                for connection_id, connection_info in self.connections.items():
                    if connection_info.last_ping < inactive_threshold:
                        inactive_connections.append(connection_id)
                
                for connection_id in inactive_connections:
                    logger.info(f"Cleaning up inactive connection: {connection_id}")
                    await self.disconnect(connection_id)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def ping_all_connections(self):
        """Send ping to all active connections"""
        ping_message = {
            "event_type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for connection_id in list(self.connections.keys()):
            await self._send_to_connection(connection_id, ping_message)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        config = get_websocket_config()
        
        total_connections = len(self.connections)
        total_subscriptions = sum(len(conn.subscriptions) for conn in self.connections.values())
        
        entity_stats = {}
        for entity_type, connections in self.entity_subscriptions.items():
            entity_stats[entity_type.value] = len(connections)
        
        query_stats = len(self.query_subscriptions)
        
        return {
            "websocket_enabled": config.is_websocket_enabled(),
            "websocket_mode": config.mode.value,
            "total_connections": total_connections,
            "total_subscriptions": total_subscriptions,
            "entity_subscriptions": entity_stats,
            "unique_queries": query_stats,
            "pending_updates": sum(len(events) for events in self.pending_updates.values()),
            "max_connections": config.max_connections,
            "rate_limit": config.max_messages_per_minute
        }

# Global connection manager instance
connection_manager = ConnectionManager()
