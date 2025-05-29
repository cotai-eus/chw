"""
WebSocket handler for real-time chat functionality.
"""
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from app.core.config import get_settings
from app.services.notification_service import NotificationService
from app.db.session import get_db, get_redis
from app.exceptions.custom_exceptions import AuthenticationError
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatRoom:
    """Represents a chat room with participants."""
    
    def __init__(self, room_id: str, room_type: str = "general"):
        self.room_id = room_id
        self.room_type = room_type  # general, tender, company, direct
        self.participants: Dict[str, WebSocket] = {}
        self.created_at = datetime.utcnow()
        self.message_history: List[dict] = []
        self.typing_users: Set[str] = set()
    
    async def add_participant(self, user_id: str, websocket: WebSocket):
        """Add participant to room."""
        self.participants[user_id] = websocket
        
        # Notify others about new participant
        await self.broadcast({
            "type": "user_joined",
            "user_id": user_id,
            "room_id": self.room_id,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
        
        # Send chat history to new participant
        await self.send_to_user(user_id, {
            "type": "chat_history",
            "messages": self.message_history[-50:],  # Last 50 messages
            "room_id": self.room_id
        })
    
    def remove_participant(self, user_id: str):
        """Remove participant from room."""
        if user_id in self.participants:
            del self.participants[user_id]
            self.typing_users.discard(user_id)
    
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """Broadcast message to all participants."""
        message_str = json.dumps(message)
        disconnected_users = []
        
        for user_id, websocket in self.participants.items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.remove_participant(user_id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user."""
        if user_id in self.participants:
            try:
                await self.participants[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.remove_participant(user_id)
    
    def add_message(self, message: dict):
        """Add message to room history."""
        self.message_history.append(message)
        # Keep only last 100 messages in memory
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]


class ChatConnectionManager:
    """Manages chat WebSocket connections and rooms."""
    
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}
        self.user_rooms: Dict[str, List[str]] = {}  # user_id -> [room_ids]
        self.notification_service = NotificationService()
    
    def get_or_create_room(self, room_id: str, room_type: str = "general") -> ChatRoom:
        """Get existing room or create new one."""
        if room_id not in self.rooms:
            self.rooms[room_id] = ChatRoom(room_id, room_type)
        return self.rooms[room_id]
    
    async def connect_user_to_room(
        self,
        user_id: str,
        room_id: str,
        websocket: WebSocket,
        room_type: str = "general"
    ):
        """Connect user to a chat room."""
        room = self.get_or_create_room(room_id, room_type)
        await room.add_participant(user_id, websocket)
        
        # Track user's rooms
        if user_id not in self.user_rooms:
            self.user_rooms[user_id] = []
        if room_id not in self.user_rooms[user_id]:
            self.user_rooms[user_id].append(room_id)
        
        logger.info(f"User {user_id} connected to room {room_id}")
    
    def disconnect_user_from_room(self, user_id: str, room_id: str):
        """Disconnect user from a room."""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            room.remove_participant(user_id)
            
            # Clean up empty rooms
            if not room.participants:
                del self.rooms[room_id]
        
        # Update user's rooms
        if user_id in self.user_rooms:
            if room_id in self.user_rooms[user_id]:
                self.user_rooms[user_id].remove(room_id)
            
            if not self.user_rooms[user_id]:
                del self.user_rooms[user_id]
        
        logger.info(f"User {user_id} disconnected from room {room_id}")
    
    def disconnect_user_from_all_rooms(self, user_id: str):
        """Disconnect user from all rooms."""
        if user_id in self.user_rooms:
            room_ids = self.user_rooms[user_id].copy()
            for room_id in room_ids:
                self.disconnect_user_from_room(user_id, room_id)
    
    async def send_message_to_room(self, room_id: str, message: dict):
        """Send message to all users in a room."""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            
            # Add to message history
            room.add_message(message)
            
            # Store in Redis for persistence
            await self.store_message_in_redis(room_id, message)
            
            # Broadcast to all participants
            await room.broadcast(message)
    
    async def store_message_in_redis(self, room_id: str, message: dict):
        """Store message in Redis for persistence."""
        try:
            redis = await get_redis()
            key = f"chat:room:{room_id}:messages"
            
            # Store message with expiration (30 days)
            await redis.lpush(key, json.dumps(message))
            await redis.expire(key, 30 * 24 * 60 * 60)  # 30 days
            
            # Keep only last 1000 messages
            await redis.ltrim(key, 0, 999)
        except Exception as e:
            logger.error(f"Error storing message in Redis: {e}")
    
    async def get_room_history(self, room_id: str, limit: int = 50) -> List[dict]:
        """Get room message history from Redis."""
        try:
            redis = await get_redis()
            key = f"chat:room:{room_id}:messages"
            
            messages = await redis.lrange(key, 0, limit - 1)
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            logger.error(f"Error getting room history: {e}")
            return []


chat_manager = ChatConnectionManager()


class ChatWebSocketHandler:
    """Handles chat WebSocket operations."""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        room_id: str,
        token: str,
        room_type: str = "general"
    ):
        """Handle new chat WebSocket connection."""
        try:
            # Verify token and get user
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            company_id = payload.get("company_id")
            
            if not user_id:
                await websocket.close(code=1008, reason="Invalid token")
                return
            
            # Verify user has access to room based on room type
            if not await self.verify_room_access(user_id, company_id, room_id, room_type):
                await websocket.close(code=1008, reason="Access denied")
                return
            
            await websocket.accept()
            await chat_manager.connect_user_to_room(user_id, room_id, websocket, room_type)
            
            # Handle messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_message(room_id, user_id, message)
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Internal server error"
                    }))
        
        except AuthenticationError:
            await websocket.close(code=1008, reason="Authentication failed")
        except Exception as e:
            logger.error(f"Chat WebSocket connection error: {e}")
            await websocket.close(code=1011, reason="Internal server error")
        finally:
            chat_manager.disconnect_user_from_room(user_id, room_id)
            # Notify other users
            if room_id in chat_manager.rooms:
                room = chat_manager.rooms[room_id]
                await room.broadcast({
                    "type": "user_left",
                    "user_id": user_id,
                    "room_id": room_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    async def verify_room_access(
        self,
        user_id: str,
        company_id: str,
        room_id: str,
        room_type: str
    ) -> bool:
        """Verify user has access to the chat room."""
        try:
            db = next(get_db())
            
            if room_type == "company":
                # Room is company-wide, check if user belongs to company
                return room_id == company_id
            
            elif room_type == "tender":
                # Check if user has access to tender
                from app.crud.tender import CRUDTender
                tender_crud = CRUDTender()
                tender = await tender_crud.get(db, id=room_id)
                return tender and tender.company_id == company_id
            
            elif room_type == "direct":
                # Direct message room, check if user is one of the participants
                # Room ID format: "user1_id:user2_id"
                participant_ids = room_id.split(":")
                return user_id in participant_ids
            
            elif room_type == "general":
                # General room, allow all authenticated users
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error verifying room access: {e}")
            return False
    
    async def handle_message(self, room_id: str, user_id: str, message: dict):
        """Handle incoming chat message."""
        message_type = message.get("type")
        
        if message_type == "message":
            await self.handle_chat_message(room_id, user_id, message)
        elif message_type == "typing":
            await self.handle_typing_indicator(room_id, user_id, message)
        elif message_type == "file_upload":
            await self.handle_file_upload(room_id, user_id, message)
        elif message_type == "message_reaction":
            await self.handle_message_reaction(room_id, user_id, message)
        elif message_type == "get_history":
            await self.handle_get_history(room_id, user_id, message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_chat_message(self, room_id: str, user_id: str, message: dict):
        """Handle regular chat message."""
        try:
            chat_message = {
                "type": "message",
                "id": f"{user_id}_{datetime.utcnow().timestamp()}",
                "room_id": room_id,
                "user_id": user_id,
                "content": message.get("content", ""),
                "message_type": message.get("message_type", "text"),  # text, image, file
                "reply_to": message.get("reply_to"),
                "mentions": message.get("mentions", []),
                "timestamp": datetime.utcnow().isoformat(),
                "edited": False,
                "reactions": {}
            }
            
            await chat_manager.send_message_to_room(room_id, chat_message)
            
            # Send notifications to mentioned users
            if chat_message["mentions"]:
                await self.send_mention_notifications(
                    room_id,
                    user_id,
                    chat_message["mentions"],
                    chat_message["content"]
                )
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    async def handle_typing_indicator(self, room_id: str, user_id: str, message: dict):
        """Handle typing indicator."""
        try:
            if room_id in chat_manager.rooms:
                room = chat_manager.rooms[room_id]
                
                is_typing = message.get("is_typing", False)
                if is_typing:
                    room.typing_users.add(user_id)
                else:
                    room.typing_users.discard(user_id)
                
                # Broadcast typing status
                await room.broadcast({
                    "type": "typing",
                    "room_id": room_id,
                    "user_id": user_id,
                    "is_typing": is_typing,
                    "typing_users": list(room.typing_users),
                    "timestamp": datetime.utcnow().isoformat()
                }, exclude_user=user_id)
        
        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}")
    
    async def handle_file_upload(self, room_id: str, user_id: str, message: dict):
        """Handle file upload message."""
        try:
            file_message = {
                "type": "message",
                "id": f"{user_id}_{datetime.utcnow().timestamp()}",
                "room_id": room_id,
                "user_id": user_id,
                "content": message.get("content", ""),
                "message_type": "file",
                "file_info": {
                    "filename": message.get("filename"),
                    "file_url": message.get("file_url"),
                    "file_size": message.get("file_size"),
                    "file_type": message.get("file_type"),
                    "thumbnail_url": message.get("thumbnail_url")
                },
                "timestamp": datetime.utcnow().isoformat(),
                "edited": False,
                "reactions": {}
            }
            
            await chat_manager.send_message_to_room(room_id, file_message)
        
        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
    
    async def handle_message_reaction(self, room_id: str, user_id: str, message: dict):
        """Handle message reaction (emoji)."""
        try:
            message_id = message.get("message_id")
            emoji = message.get("emoji")
            action = message.get("action", "add")  # add or remove
            
            # Update message reactions in Redis
            redis = await get_redis()
            reaction_key = f"chat:message:{message_id}:reactions"
            
            if action == "add":
                await redis.sadd(f"{reaction_key}:{emoji}", user_id)
            else:
                await redis.srem(f"{reaction_key}:{emoji}", user_id)
            
            # Get updated reactions
            reactions = {}
            for reaction_emoji in await redis.keys(f"{reaction_key}:*"):
                emoji_name = reaction_emoji.split(":")[-1]
                users = await redis.smembers(reaction_emoji)
                if users:
                    reactions[emoji_name] = list(users)
            
            # Broadcast reaction update
            if room_id in chat_manager.rooms:
                room = chat_manager.rooms[room_id]
                await room.broadcast({
                    "type": "message_reaction",
                    "room_id": room_id,
                    "message_id": message_id,
                    "emoji": emoji,
                    "user_id": user_id,
                    "action": action,
                    "reactions": reactions,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error handling message reaction: {e}")
    
    async def handle_get_history(self, room_id: str, user_id: str, message: dict):
        """Handle request for chat history."""
        try:
            limit = message.get("limit", 50)
            before_timestamp = message.get("before_timestamp")
            
            history = await chat_manager.get_room_history(room_id, limit)
            
            if room_id in chat_manager.rooms:
                room = chat_manager.rooms[room_id]
                await room.send_to_user(user_id, {
                    "type": "chat_history",
                    "room_id": room_id,
                    "messages": history,
                    "has_more": len(history) == limit,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error handling get history: {e}")
    
    async def send_mention_notifications(
        self,
        room_id: str,
        sender_id: str,
        mentioned_users: List[str],
        content: str
    ):
        """Send notifications to mentioned users."""
        try:
            for mentioned_user_id in mentioned_users:
                await self.notification_service.create_notification(
                    user_id=mentioned_user_id,
                    title="You were mentioned in chat",
                    message=f"@{sender_id}: {content[:100]}...",
                    notification_type="mention",
                    data={
                        "room_id": room_id,
                        "sender_id": sender_id,
                        "message_content": content
                    }
                )
        except Exception as e:
            logger.error(f"Error sending mention notifications: {e}")


chat_handler = ChatWebSocketHandler()
