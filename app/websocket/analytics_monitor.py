"""
Real-time Analytics WebSocket Integration
Provides live analytics updates through WebSocket connections
"""

import json
import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from app.websocket.connection_manager import connection_manager
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class AnalyticsEventType:
    """Types of real-time analytics events"""
    NEW_SEARCH = "new_search"
    USER_ACTIVITY = "user_activity"
    PLATFORM_METRICS = "platform_metrics"
    SEARCH_TRENDS = "search_trends"
    CONTENT_UPDATE = "content_update"
    SYSTEM_ALERT = "system_alert"

class RealTimeAnalyticsMonitor:
    """Monitors and broadcasts real-time analytics events"""

    def __init__(self):
        self.is_monitoring = False
        self.monitor_task = None
        self.analytics_connections: Dict[str, Set[str]] = defaultdict(set)
        self.update_interval = 30  # seconds
        
    async def start_monitoring(self):
        """Start real-time analytics monitoring"""
        if self.is_monitoring:
            logger.info("Analytics monitoring already running")
            return
            
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Real-time analytics monitoring started")

    async def stop_monitoring(self):
        """Stop real-time analytics monitoring"""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Real-time analytics monitoring stopped")

    async def subscribe_to_analytics(self, connection_id: str, analytics_types: List[str]):
        """Subscribe a connection to specific analytics events"""
        for analytics_type in analytics_types:
            self.analytics_connections[analytics_type].add(connection_id)
        
        logger.info(f"Connection {connection_id} subscribed to analytics: {analytics_types}")

    async def unsubscribe_from_analytics(self, connection_id: str, analytics_types: List[str] = None):
        """Unsubscribe from analytics events"""
        if analytics_types is None:
            # Unsubscribe from all
            for analytics_type in list(self.analytics_connections.keys()):
                self.analytics_connections[analytics_type].discard(connection_id)
        else:
            for analytics_type in analytics_types:
                self.analytics_connections[analytics_type].discard(connection_id)
        
        logger.info(f"Connection {connection_id} unsubscribed from analytics")

    async def _monitoring_loop(self):
        """Main monitoring loop for real-time analytics"""
        last_metrics = {}
        
        while self.is_monitoring:
            try:
                # Get current metrics
                current_metrics = await analytics_service._get_real_time_stats()
                
                # Compare with previous metrics and broadcast updates
                await self._check_and_broadcast_updates(last_metrics, current_metrics)
                
                # Broadcast periodic platform metrics
                await self._broadcast_platform_metrics(current_metrics)
                
                # Update last metrics
                last_metrics = current_metrics.copy()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _check_and_broadcast_updates(self, last_metrics: Dict, current_metrics: Dict):
        """Check for significant changes and broadcast updates"""
        
        # Check for new search activity
        last_searches = last_metrics.get("searches_last_hour", 0)
        current_searches = current_metrics.get("searches_last_hour", 0)
        
        if current_searches > last_searches:
            await self._broadcast_analytics_event(
                AnalyticsEventType.NEW_SEARCH,
                {
                    "type": "search_activity_spike",
                    "new_searches": current_searches - last_searches,
                    "total_searches": current_searches,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        # Check for user activity changes
        last_active_users = last_metrics.get("active_users_last_hour", 0)
        current_active_users = current_metrics.get("active_users_last_hour", 0)
        
        if current_active_users != last_active_users:
            await self._broadcast_analytics_event(
                AnalyticsEventType.USER_ACTIVITY,
                {
                    "type": "active_users_update",
                    "active_users": current_active_users,
                    "change": current_active_users - last_active_users,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        # Check for response time changes (alert if degrading)
        last_response_time = last_metrics.get("avg_response_time_last_hour", 0)
        current_response_time = current_metrics.get("avg_response_time_last_hour", 0)
        
        if current_response_time > last_response_time * 1.5 and current_response_time > 1000:  # Alert if 50% slower and > 1s
            await self._broadcast_analytics_event(
                AnalyticsEventType.SYSTEM_ALERT,
                {
                    "type": "performance_degradation",
                    "alert_level": "warning",
                    "metric": "response_time",
                    "current_value": current_response_time,
                    "threshold": 1000,
                    "message": f"Search response time increased to {current_response_time:.0f}ms",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def _broadcast_platform_metrics(self, metrics: Dict):
        """Broadcast periodic platform metrics"""
        await self._broadcast_analytics_event(
            AnalyticsEventType.PLATFORM_METRICS,
            {
                "type": "platform_metrics_update",
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def _broadcast_analytics_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast analytics event to subscribed connections"""
        
        # Get connections subscribed to this event type
        subscribed_connections = self.analytics_connections.get(event_type, set())
        
        if not subscribed_connections:
            return

        message = {
            "event_type": "analytics_update",
            "analytics_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Send to each subscribed connection
        for connection_id in list(subscribed_connections):  # Copy to avoid modification during iteration
            try:
                # Use the existing connection manager to send the message
                sent = await connection_manager._send_to_connection(connection_id, message)
                if not sent:
                    # Connection is no longer valid, remove it
                    self.analytics_connections[event_type].discard(connection_id)
            except Exception as e:
                logger.error(f"Failed to send analytics update to {connection_id}: {e}")
                # Remove problematic connection
                self.analytics_connections[event_type].discard(connection_id)

    async def broadcast_search_event(self, search_data: Dict[str, Any]):
        """Broadcast a real-time search event"""
        await self._broadcast_analytics_event(
            AnalyticsEventType.SEARCH_TRENDS,
            {
                "type": "new_search",
                "query": search_data.get("query", ""),
                "entity_type": search_data.get("search_type", ""),
                "result_count": search_data.get("result_count", 0),
                "response_time_ms": search_data.get("search_time_ms", 0),
                "user_id": search_data.get("user_id"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def broadcast_content_event(self, content_type: str, action: str, content_data: Dict[str, Any]):
        """Broadcast content-related events (new posts, comments, etc.)"""
        await self._broadcast_analytics_event(
            AnalyticsEventType.CONTENT_UPDATE,
            {
                "type": f"{content_type}_{action}",
                "content_type": content_type,
                "action": action,
                "data": content_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def get_analytics_stats(self) -> Dict[str, Any]:
        """Get current analytics monitoring statistics"""
        return {
            "monitoring_active": self.is_monitoring,
            "subscription_counts": {
                analytics_type: len(connections) 
                for analytics_type, connections in self.analytics_connections.items()
            },
            "total_subscriptions": sum(len(connections) for connections in self.analytics_connections.values()),
            "update_interval_seconds": self.update_interval
        }

# Global analytics monitor instance
analytics_monitor = RealTimeAnalyticsMonitor()
