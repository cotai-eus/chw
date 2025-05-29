"""Notification service for managing real-time notifications."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
import aioredis

from app.core.config import settings
from app.db.session import redis_client

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications and real-time communication."""
    
    def __init__(self):
        self.redis = redis_client
        self.notification_prefix = "notification:"
        self.user_notifications_prefix = "user_notifications:"
        self.company_notifications_prefix = "company_notifications:"
    
    async def create_notification(
        self,
        user_id: UUID,
        company_id: UUID,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a new notification for a user.
        
        Args:
            user_id: ID of the user to notify
            company_id: ID of the company
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, warning, error, success)
            data: Additional data for the notification
            expires_at: Optional expiration time
            
        Returns:
            Created notification information
        """
        try:
            notification_id = str(UUID())
            
            notification = {
                "id": notification_id,
                "user_id": str(user_id),
                "company_id": str(company_id),
                "title": title,
                "message": message,
                "type": notification_type,
                "data": data or {},
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "read": False
            }
            
            # Store notification
            notification_key = f"{self.notification_prefix}{notification_id}"
            await self.redis.set(
                notification_key,
                json.dumps(notification),
                ex=86400 * 30  # 30 days TTL
            )
            
            # Add to user's notification list
            user_key = f"{self.user_notifications_prefix}{user_id}"
            await self.redis.lpush(user_key, notification_id)
            await self.redis.expire(user_key, 86400 * 30)
            
            # Add to company's notification list
            company_key = f"{self.company_notifications_prefix}{company_id}"
            await self.redis.lpush(company_key, notification_id)
            await self.redis.expire(company_key, 86400 * 30)
            
            # Publish to real-time channel
            await self._publish_real_time(user_id, notification)
            
            logger.info(f"Notification created: {notification_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            return {"error": str(e)}
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of notifications to return
            unread_only: Whether to return only unread notifications
            
        Returns:
            List of notifications
        """
        try:
            user_key = f"{self.user_notifications_prefix}{user_id}"
            notification_ids = await self.redis.lrange(user_key, 0, limit - 1)
            
            notifications = []
            for notification_id in notification_ids:
                notification_key = f"{self.notification_prefix}{notification_id}"
                notification_data = await self.redis.get(notification_key)
                
                if notification_data:
                    notification = json.loads(notification_data)
                    
                    # Filter unread if requested
                    if unread_only and notification.get("read", False):
                        continue
                    
                    # Check expiration
                    if notification.get("expires_at"):
                        expires_at = datetime.fromisoformat(notification["expires_at"])
                        if expires_at < datetime.utcnow():
                            continue
                    
                    notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {str(e)}")
            return []
    
    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: UUID
    ) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of the notification
            user_id: ID of the user
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification_key = f"{self.notification_prefix}{notification_id}"
            notification_data = await self.redis.get(notification_key)
            
            if not notification_data:
                return False
            
            notification = json.loads(notification_data)
            
            # Verify ownership
            if notification.get("user_id") != str(user_id):
                return False
            
            # Mark as read
            notification["read"] = True
            notification["read_at"] = datetime.utcnow().isoformat()
            
            # Update in Redis
            await self.redis.set(
                notification_key,
                json.dumps(notification),
                ex=86400 * 30
            )
            
            logger.info(f"Notification {notification_id} marked as read")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {str(e)}")
            return False
    
    async def delete_notification(
        self,
        notification_id: str,
        user_id: UUID
    ) -> bool:
        """
        Delete a notification.
        
        Args:
            notification_id: ID of the notification
            user_id: ID of the user
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification_key = f"{self.notification_prefix}{notification_id}"
            notification_data = await self.redis.get(notification_key)
            
            if not notification_data:
                return False
            
            notification = json.loads(notification_data)
            
            # Verify ownership
            if notification.get("user_id") != str(user_id):
                return False
            
            # Delete notification
            await self.redis.delete(notification_key)
            
            # Remove from user's list
            user_key = f"{self.user_notifications_prefix}{user_id}"
            await self.redis.lrem(user_key, 1, notification_id)
            
            # Remove from company's list
            company_id = notification.get("company_id")
            if company_id:
                company_key = f"{self.company_notifications_prefix}{company_id}"
                await self.redis.lrem(company_key, 1, notification_id)
            
            logger.info(f"Notification {notification_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete notification: {str(e)}")
            return False
    
    async def get_unread_count(self, user_id: UUID) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of unread notifications
        """
        try:
            notifications = await self.get_user_notifications(
                user_id=user_id,
                unread_only=True
            )
            return len(notifications)
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {str(e)}")
            return 0
    
    async def notify_tender_created(
        self,
        tender_data: Dict[str, Any],
        company_id: UUID,
        creator_id: UUID
    ) -> bool:
        """
        Send notification when a tender is created.
        
        Args:
            tender_data: Tender information
            company_id: Company ID
            creator_id: ID of the user who created the tender
            
        Returns:
            True if successful
        """
        try:
            # This would typically notify relevant users in the company
            # For now, just notify the creator
            await self.create_notification(
                user_id=creator_id,
                company_id=company_id,
                title="Tender Created",
                message=f"Tender '{tender_data.get('title')}' has been created successfully",
                notification_type="success",
                data={
                    "tender_id": tender_data.get("id"),
                    "action": "view_tender"
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send tender creation notification: {str(e)}")
            return False
    
    async def notify_quote_received(
        self,
        quote_data: Dict[str, Any],
        company_id: UUID,
        recipient_id: UUID
    ) -> bool:
        """
        Send notification when a quote is received.
        
        Args:
            quote_data: Quote information
            company_id: Company ID
            recipient_id: ID of the user to notify
            
        Returns:
            True if successful
        """
        try:
            await self.create_notification(
                user_id=recipient_id,
                company_id=company_id,
                title="New Quote Received",
                message=f"Quote #{quote_data.get('quote_number')} received from {quote_data.get('supplier_name')}",
                notification_type="info",
                data={
                    "quote_id": quote_data.get("id"),
                    "action": "view_quote"
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send quote notification: {str(e)}")
            return False
    
    async def notify_deadline_approaching(
        self,
        tender_data: Dict[str, Any],
        user_id: UUID,
        company_id: UUID,
        days_remaining: int
    ) -> bool:
        """
        Send notification when tender deadline is approaching.
        
        Args:
            tender_data: Tender information
            user_id: User ID
            company_id: Company ID
            days_remaining: Number of days until deadline
            
        Returns:
            True if successful
        """
        try:
            await self.create_notification(
                user_id=user_id,
                company_id=company_id,
                title="Tender Deadline Approaching",
                message=f"Tender '{tender_data.get('title')}' deadline is in {days_remaining} days",
                notification_type="warning",
                data={
                    "tender_id": tender_data.get("id"),
                    "days_remaining": days_remaining,
                    "action": "view_tender"
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send deadline notification: {str(e)}")
            return False
    
    async def _publish_real_time(
        self,
        user_id: UUID,
        notification: Dict[str, Any]
    ):
        """Publish notification to real-time channel."""
        try:
            channel = f"notifications:{user_id}"
            await self.redis.publish(channel, json.dumps(notification))
            
        except Exception as e:
            logger.error(f"Failed to publish real-time notification: {str(e)}")
    
    async def cleanup_expired_notifications(self):
        """Clean up expired notifications."""
        try:
            # This would be called periodically by a background task
            # to remove expired notifications
            pass
            
        except Exception as e:
            logger.error(f"Failed to cleanup notifications: {str(e)}")


# Global instance
notification_service = NotificationService()
