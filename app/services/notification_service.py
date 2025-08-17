"""
Real-time Notification Service for CivicPulse
Handles notification creation, delivery via WebSocket, and persistence
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

from app.websocket.connection_manager import connection_manager
from app.models.pydantic_models import NotificationType, NotificationResponse
from app.core.logging_config import get_logger

logger = get_logger('app.notifications')

class NotificationEvent:
    """Represents a real-time notification event"""
    
    def __init__(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        post_id: Optional[UUID] = None,
        comment_id: Optional[UUID] = None,
        triggered_by_user_id: Optional[UUID] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = uuid4()
        self.user_id = user_id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.post_id = post_id
        self.comment_id = comment_id
        self.triggered_by_user_id = triggered_by_user_id
        self.action_url = action_url
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.read = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "notification_type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "post_id": str(self.post_id) if self.post_id else None,
            "comment_id": str(self.comment_id) if self.comment_id else None,
            "triggered_by_user_id": str(self.triggered_by_user_id) if self.triggered_by_user_id else None,
            "action_url": self.action_url,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "read": self.read
        }

class RealTimeNotificationService:
    """Manages real-time notifications via WebSocket"""
    
    def __init__(self):
        self.pending_notifications: Dict[str, List[NotificationEvent]] = {}
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> [connection_ids]
        
    async def send_notification(self, notification: NotificationEvent) -> bool:
        """
        Send a notification to a user via WebSocket
        Falls back to storing for later delivery if user not connected
        """
        try:
            user_id_str = str(notification.user_id)
            
            # Get active connections for this user
            user_connections = await self._get_user_connections(user_id_str)
            
            if user_connections:
                # Send to all user's active connections
                success_count = 0
                for connection_id in user_connections:
                    success = await self._send_to_connection(connection_id, notification)
                    if success:
                        success_count += 1
                
                logger.info(
                    f"Notification sent to {success_count}/{len(user_connections)} connections "
                    f"for user {user_id_str}: {notification.notification_type.value}"
                )
                return success_count > 0
            else:
                # Store for later delivery
                await self._store_for_later_delivery(notification)
                logger.info(f"User {user_id_str} not connected, notification stored for later delivery")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def send_bulk_notifications(self, notifications: List[NotificationEvent]) -> Dict[str, int]:
        """Send multiple notifications efficiently"""
        results = {"sent": 0, "stored": 0, "failed": 0}
        
        for notification in notifications:
            try:
                success = await self.send_notification(notification)
                if success:
                    results["sent"] += 1
                else:
                    results["stored"] += 1
            except Exception as e:
                logger.error(f"Failed to send bulk notification: {e}")
                results["failed"] += 1
        
        return results

    async def notify_post_update(
        self,
        post_id: UUID,
        post_title: str,
        followers: List[UUID],
        update_type: str,
        triggered_by_user_id: Optional[UUID] = None
    ):
        """Notify followers about post updates"""
        notifications = []
        
        for user_id in followers:
            # Don't notify the user who made the update
            if triggered_by_user_id and user_id == triggered_by_user_id:
                continue
                
            notification = NotificationEvent(
                user_id=user_id,
                notification_type=NotificationType.ISSUE_UPDATE,
                title=f"Post Update",
                message=f'"{post_title}" has been {update_type}',
                post_id=post_id,
                triggered_by_user_id=triggered_by_user_id,
                action_url=f"/posts/{post_id}",
                metadata={"update_type": update_type}
            )
            notifications.append(notification)
        
        return await self.send_bulk_notifications(notifications)

    async def notify_new_comment(
        self,
        post_id: UUID,
        post_title: str,
        comment_id: UUID,
        commenter_name: str,
        post_author_id: UUID,
        mentioned_users: List[UUID] = None
    ):
        """Notify about new comments"""
        notifications = []
        
        # Notify post author
        notification = NotificationEvent(
            user_id=post_author_id,
            notification_type=NotificationType.COMMENT,
            title="New Comment",
            message=f'{commenter_name} commented on "{post_title}"',
            post_id=post_id,
            comment_id=comment_id,
            action_url=f"/posts/{post_id}#comment-{comment_id}"
        )
        notifications.append(notification)
        
        # Notify mentioned users
        if mentioned_users:
            for user_id in mentioned_users:
                if user_id != post_author_id:  # Don't duplicate notification
                    notification = NotificationEvent(
                        user_id=user_id,
                        notification_type=NotificationType.MENTION,
                        title="You were mentioned",
                        message=f'{commenter_name} mentioned you in a comment on "{post_title}"',
                        post_id=post_id,
                        comment_id=comment_id,
                        action_url=f"/posts/{post_id}#comment-{comment_id}"
                    )
                    notifications.append(notification)
        
        return await self.send_bulk_notifications(notifications)

    async def notify_vote(
        self,
        post_id: UUID,
        post_title: str,
        post_author_id: UUID,
        voter_name: str,
        vote_type: str
    ):
        """Notify about votes on posts"""
        notification = NotificationEvent(
            user_id=post_author_id,
            notification_type=NotificationType.VOTE,
            title=f"New {vote_type}",
            message=f'{voter_name} {vote_type}d your post "{post_title}"',
            post_id=post_id,
            action_url=f"/posts/{post_id}",
            metadata={"vote_type": vote_type}
        )
        
        return await self.send_notification(notification)

    async def notify_assignment(
        self,
        post_id: UUID,
        post_title: str,
        assignee_id: UUID,
        assigner_name: str
    ):
        """Notify about post assignments"""
        notification = NotificationEvent(
            user_id=assignee_id,
            notification_type=NotificationType.ASSIGNMENT,
            title="You've been assigned to a post",
            message=f'{assigner_name} assigned you to "{post_title}"',
            post_id=post_id,
            action_url=f"/posts/{post_id}",
        )
        
        return await self.send_notification(notification)

    async def _get_user_connections(self, user_id: str) -> List[str]:
        """Get all active WebSocket connections for a user"""
        # Integration with your existing connection manager
        connections = []
        for connection_id, connection_info in connection_manager.connections.items():
            if connection_info.user_id == user_id:
                connections.append(connection_id)
        return connections

    async def _send_to_connection(self, connection_id: str, notification: NotificationEvent) -> bool:
        """Send notification to a specific WebSocket connection"""
        try:
            message = {
                "event_type": "notification",
                "data": notification.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Use your existing connection manager
            return await connection_manager._send_to_connection(connection_id, message)
            
        except Exception as e:
            logger.error(f"Failed to send to connection {connection_id}: {e}")
            return False

    async def _store_for_later_delivery(self, notification: NotificationEvent):
        """Store notification for later delivery when user comes online"""
        user_id_str = str(notification.user_id)
        
        if user_id_str not in self.pending_notifications:
            self.pending_notifications[user_id_str] = []
        
        self.pending_notifications[user_id_str].append(notification)
        
        # Keep only last 50 notifications per user to prevent memory issues
        if len(self.pending_notifications[user_id_str]) > 50:
            self.pending_notifications[user_id_str] = self.pending_notifications[user_id_str][-50:]

    async def deliver_pending_notifications(self, user_id: str, connection_id: str):
        """Deliver pending notifications when user connects"""
        if user_id in self.pending_notifications:
            notifications = self.pending_notifications[user_id]
            
            logger.info(f"Delivering {len(notifications)} pending notifications to user {user_id}")
            
            for notification in notifications:
                await self._send_to_connection(connection_id, notification)
            
            # Clear delivered notifications
            del self.pending_notifications[user_id]

# Global notification service instance
notification_service = RealTimeNotificationService()
