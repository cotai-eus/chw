"""WebSocket handler for real-time notifications."""

import json
import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_websocket, get_async_db
from app.services.notification_service import notification_service
from app.db.session import redis_client

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for notification WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """Connect a user to the notification system."""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        logger.info(f"User {user_id} connected to notifications (connection: {connection_id})")
        
        # Send unread notifications
        await self._send_unread_notifications(websocket, user_id)
        
        # Subscribe to Redis channel for real-time notifications
        await self._subscribe_to_notifications(user_id)
    
    async def disconnect(self, connection_id: str, user_id: str):
        """Disconnect a user from the notification system."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"User {user_id} disconnected from notifications (connection: {connection_id})")
    
    async def send_notification_to_user(self, user_id: str, notification: dict):
        """Send notification to all connections of a user."""
        if user_id in self.user_connections:
            message = {
                "type": "notification",
                "data": notification
            }
            
            # Send to all user's connections
            for connection_id in self.user_connections[user_id].copy():
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_text(
                            json.dumps(message)
                        )
                    except Exception as e:
                        logger.error(f"Failed to send notification to {connection_id}: {str(e)}")
                        # Remove failed connection
                        await self.disconnect(connection_id, user_id)
    
    async def broadcast_to_company(self, company_id: str, notification: dict):
        """Broadcast notification to all users in a company."""
        # This would require mapping company users to connections
        # For now, we'll implement user-specific notifications
        pass
    
    async def _send_unread_notifications(self, websocket: WebSocket, user_id: str):
        """Send unread notifications to a newly connected user."""
        try:
            notifications = await notification_service.get_user_notifications(
                user_id=UUID(user_id),
                limit=20,
                unread_only=True
            )
            
            if notifications:
                message = {
                    "type": "unread_notifications",
                    "data": notifications
                }
                await websocket.send_text(json.dumps(message))
                
        except Exception as e:
            logger.error(f"Failed to send unread notifications: {str(e)}")
    
    async def _subscribe_to_notifications(self, user_id: str):
        """Subscribe to Redis notifications for a user."""
        # This would be implemented with Redis pub/sub
        # For now, we'll handle it in the notification service
        pass


# Global notification manager
notification_manager = NotificationManager()


async def notification_websocket(
    websocket: WebSocket,
    user_id: str,
    connection_id: str,
    current_user=Depends(get_current_user_websocket),
    db: AsyncSession = Depends(get_async_db)
):
    """
    WebSocket endpoint for real-time notifications.
    
    Args:
        websocket: WebSocket connection
        user_id: ID of the user
        connection_id: Unique connection identifier
        current_user: Current authenticated user
        db: Database session
    """
    # Verify user access
    if str(current_user.id) != user_id:
        await websocket.close(code=4003, reason="Unauthorized")
        return
    
    await notification_manager.connect(websocket, user_id, connection_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "mark_read":
                # Mark notification as read
                notification_id = message.get("notification_id")
                if notification_id:
                    success = await notification_service.mark_notification_read(
                        notification_id, UUID(user_id)
                    )
                    
                    response = {
                        "type": "notification_marked_read",
                        "notification_id": notification_id,
                        "success": success
                    }
                    await websocket.send_text(json.dumps(response))
            
            elif message_type == "delete_notification":
                # Delete notification
                notification_id = message.get("notification_id")
                if notification_id:
                    success = await notification_service.delete_notification(
                        notification_id, UUID(user_id)
                    )
                    
                    response = {
                        "type": "notification_deleted",
                        "notification_id": notification_id,
                        "success": success
                    }
                    await websocket.send_text(json.dumps(response))
            
            elif message_type == "get_unread_count":
                # Get unread notification count
                count = await notification_service.get_unread_count(UUID(user_id))
                
                response = {
                    "type": "unread_count",
                    "count": count
                }
                await websocket.send_text(json.dumps(response))
            
            elif message_type == "ping":
                # Respond to ping with pong
                response = {"type": "pong"}
                await websocket.send_text(json.dumps(response))
            
            else:
                # Unknown message type
                response = {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }
                await websocket.send_text(json.dumps(response))
                
    except WebSocketDisconnect:
        await notification_manager.disconnect(connection_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        await notification_manager.disconnect(connection_id, user_id)
