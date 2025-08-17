from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional
import json
import logging
import uuid
from pathlib import Path

from app.services.db_service import DatabaseService
from app.services.auth_service import get_current_user
from app.models.pydantic_models import PushSubscriptionCreate, PushSubscriptionResponse, NotificationResponse
from app.core.logging_config import get_logger

logger = get_logger('app.notifications')
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
db_service = DatabaseService()

@router.post("/subscribe", response_model=Dict[str, Any])
async def subscribe_to_push_notifications(
    subscription_data: PushSubscriptionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Subscribe a user to push notifications
    """
    try:
        user_id = uuid.UUID(current_user['id'])
        
        # Check if subscription already exists
        existing_subscription = await db_service.execute_query(
            """
            SELECT id FROM push_subscriptions 
            WHERE user_id = $1 AND endpoint = $2
            """,
            user_id, subscription_data.endpoint
        )
        
        if existing_subscription:
            # Update existing subscription
            await db_service.execute_query(
                """
                UPDATE push_subscriptions 
                SET p256dh_key = $1, auth_key = $2, is_active = true, updated_at = NOW()
                WHERE user_id = $3 AND endpoint = $4
                """,
                subscription_data.keys.p256dh,
                subscription_data.keys.auth,
                user_id,
                subscription_data.endpoint
            )
            
            logger.info(f"Updated push subscription for user {current_user['id']}")
            return {
                "message": "Push subscription updated successfully",
                "subscription_id": str(existing_subscription[0]['id'])
            }
        
        # Create new subscription
        result = await db_service.execute_query(
            """
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh_key, auth_key, is_active)
            VALUES ($1, $2, $3, $4, true)
            RETURNING id
            """,
            user_id,
            subscription_data.endpoint,
            subscription_data.keys.p256dh,
            subscription_data.keys.auth
        )
        
        logger.info(f"Created new push subscription for user {current_user['id']}")
        
        return {
            "message": "Push subscription created successfully",
            "subscription_id": str(result[0]['id'])
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to push notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to push notifications"
        )

@router.delete("/unsubscribe")
async def unsubscribe_from_push_notifications(
    endpoint: str = Query(..., description="Push subscription endpoint"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Unsubscribe a user from push notifications
    """
    try:
        user_id = uuid.UUID(current_user['id'])
        
        subscription = await db_service.execute_query(
            """
            SELECT id FROM push_subscriptions 
            WHERE user_id = $1 AND endpoint = $2
            """,
            user_id, endpoint
        )
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Push subscription not found"
            )
        
        # Soft delete - mark as inactive
        await db_service.execute_query(
            """
            UPDATE push_subscriptions 
            SET is_active = false, updated_at = NOW()
            WHERE user_id = $1 AND endpoint = $2
            """,
            user_id, endpoint
        )
        
        logger.info(f"Deactivated push subscription for user {current_user['id']}")
        
        return {"message": "Successfully unsubscribed from push notifications"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from push notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from push notifications"
        )

@router.get("/subscriptions", response_model=list[PushSubscriptionResponse])
async def get_user_push_subscriptions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all active push subscriptions for the current user
    """
    try:
        user_id = uuid.UUID(current_user['id'])
        
        subscriptions = await db_service.execute_query(
            """
            SELECT id, endpoint, created_at, is_active
            FROM push_subscriptions 
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at DESC
            """,
            user_id
        )
        
        return [
            PushSubscriptionResponse(
                id=sub['id'],
                endpoint=sub['endpoint'],
                created_at=sub['created_at'],
                is_active=sub['is_active']
            )
            for sub in subscriptions
        ]
        
    except Exception as e:
        logger.error(f"Error getting push subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get push subscriptions"
        )

@router.post("/test-push")
async def test_push_notification(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send a test push notification to the current user
    """
    try:
        from app.services.notification_service import notification_service
        
        # Send test notification
        await notification_service.send_notification(
            user_id=current_user['id'],
            notification_type="test",
            title="Test Push Notification",
            message="This is a test push notification from CivicPulse!",
            action_url="/notifications-test"
        )
        
        return {"message": "Test push notification sent successfully"}
        
    except Exception as e:
        logger.error(f"Error sending test push notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test push notification"
        )

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """
    Get the VAPID public key for push notifications
    """
    try:
        # Try to read from config file first
        config_path = Path(__file__).parent.parent.parent / "config" / "vapid_keys.json"
        
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                vapid_config = json.load(f)
                return {"public_key": vapid_config["public_key"]}
        
        # Fallback to environment variable
        import os
        public_key = os.getenv('VAPID_PUBLIC_KEY')
        if public_key:
            return {"public_key": public_key}
        
        # Final fallback (should not be used in production)
        logger.warning("Using placeholder VAPID public key - configure real keys for production!")
        public_key = "BAGbZLcPHdFYm51AkCL_zLl2VG5TrgKSTwCmD6d_OIhuISRztuPYQt4bNexSj8AelMveylS_J2uuEhILYnJq0uM"
        
        return {"public_key": public_key}
        
    except Exception as e:
        logger.error(f"Error getting VAPID public key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get VAPID public key"
        )
