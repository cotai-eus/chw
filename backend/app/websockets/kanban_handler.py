"""
WebSocket handler for real-time Kanban board updates.
"""
import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.core.config import get_settings
from app.services.notification_service import NotificationService
from app.crud.kanban import CRUDKanbanBoard, CRUDKanbanColumn, CRUDKanbanCard
from app.db.session import get_db
from app.exceptions.custom_exceptions import AuthenticationError
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()


class KanbanConnectionManager:
    """Manages WebSocket connections for Kanban boards."""
    
    def __init__(self):
        # board_id -> {user_id: websocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.user_boards: Dict[str, List[str]] = {}  # user_id -> [board_ids]
    
    async def connect(self, websocket: WebSocket, board_id: str, user_id: str):
        """Connect user to a board."""
        await websocket.accept()
        
        if board_id not in self.active_connections:
            self.active_connections[board_id] = {}
        
        self.active_connections[board_id][user_id] = websocket
        
        if user_id not in self.user_boards:
            self.user_boards[user_id] = []
        if board_id not in self.user_boards[user_id]:
            self.user_boards[user_id].append(board_id)
        
        logger.info(f"User {user_id} connected to board {board_id}")
        
        # Notify other users in the board
        await self.broadcast_to_board(
            board_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "timestamp": NotificationService.get_current_timestamp()
            },
            exclude_user=user_id
        )
    
    def disconnect(self, board_id: str, user_id: str):
        """Disconnect user from a board."""
        if board_id in self.active_connections:
            if user_id in self.active_connections[board_id]:
                del self.active_connections[board_id][user_id]
                
                if not self.active_connections[board_id]:
                    del self.active_connections[board_id]
        
        if user_id in self.user_boards:
            if board_id in self.user_boards[user_id]:
                self.user_boards[user_id].remove(board_id)
                
                if not self.user_boards[user_id]:
                    del self.user_boards[user_id]
        
        logger.info(f"User {user_id} disconnected from board {board_id}")
    
    async def broadcast_to_board(
        self,
        board_id: str,
        message: dict,
        exclude_user: Optional[str] = None
    ):
        """Broadcast message to all users in a board."""
        if board_id not in self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected_users = []
        
        for user_id, websocket in self.active_connections[board_id].items():
            if exclude_user and user_id == exclude_user:
                continue
                
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(board_id, user_id)
    
    async def send_to_user(self, board_id: str, user_id: str, message: dict):
        """Send message to specific user in a board."""
        if (board_id in self.active_connections and 
            user_id in self.active_connections[board_id]):
            try:
                websocket = self.active_connections[board_id][user_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(board_id, user_id)


kanban_manager = KanbanConnectionManager()


class KanbanWebSocketHandler:
    """Handles Kanban WebSocket operations."""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.board_crud = CRUDKanbanBoard()
        self.column_crud = CRUDKanbanColumn()
        self.card_crud = CRUDKanbanCard()
    
    async def handle_connection(self, websocket: WebSocket, board_id: str, token: str):
        """Handle new WebSocket connection."""
        try:
            # Verify token and get user
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                await websocket.close(code=1008, reason="Invalid token")
                return
            
            # Verify user has access to board
            db = next(get_db())
            board = await self.board_crud.get(db, id=board_id)
            if not board or board.company_id != payload.get("company_id"):
                await websocket.close(code=1008, reason="Access denied")
                return
            
            await kanban_manager.connect(websocket, board_id, user_id)
            
            # Send current board state
            await self.send_board_state(websocket, board_id)
            
            # Handle messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_message(board_id, user_id, message)
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
            logger.error(f"WebSocket connection error: {e}")
            await websocket.close(code=1011, reason="Internal server error")
        finally:
            kanban_manager.disconnect(board_id, user_id)
            # Notify other users
            await kanban_manager.broadcast_to_board(
                board_id,
                {
                    "type": "user_left",
                    "user_id": user_id,
                    "timestamp": NotificationService.get_current_timestamp()
                }
            )
    
    async def send_board_state(self, websocket: WebSocket, board_id: str):
        """Send current board state to newly connected user."""
        try:
            db = next(get_db())
            board = await self.board_crud.get_with_columns_and_cards(db, board_id)
            
            await websocket.send_text(json.dumps({
                "type": "board_state",
                "board": {
                    "id": board.id,
                    "name": board.name,
                    "description": board.description,
                    "columns": [
                        {
                            "id": col.id,
                            "name": col.name,
                            "position": col.position,
                            "cards": [
                                {
                                    "id": card.id,
                                    "title": card.title,
                                    "description": card.description,
                                    "position": card.position,
                                    "assigned_to": card.assigned_to,
                                    "priority": card.priority,
                                    "due_date": card.due_date.isoformat() if card.due_date else None,
                                    "labels": card.labels,
                                    "created_at": card.created_at.isoformat()
                                }
                                for card in sorted(col.cards, key=lambda x: x.position)
                            ]
                        }
                        for col in sorted(board.columns, key=lambda x: x.position)
                    ]
                },
                "timestamp": NotificationService.get_current_timestamp()
            }))
        except Exception as e:
            logger.error(f"Error sending board state: {e}")
    
    async def handle_message(self, board_id: str, user_id: str, message: dict):
        """Handle incoming WebSocket message."""
        message_type = message.get("type")
        
        if message_type == "card_moved":
            await self.handle_card_moved(board_id, user_id, message)
        elif message_type == "card_created":
            await self.handle_card_created(board_id, user_id, message)
        elif message_type == "card_updated":
            await self.handle_card_updated(board_id, user_id, message)
        elif message_type == "card_deleted":
            await self.handle_card_deleted(board_id, user_id, message)
        elif message_type == "column_created":
            await self.handle_column_created(board_id, user_id, message)
        elif message_type == "column_updated":
            await self.handle_column_updated(board_id, user_id, message)
        elif message_type == "column_deleted":
            await self.handle_column_deleted(board_id, user_id, message)
        elif message_type == "typing":
            await self.handle_typing(board_id, user_id, message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_card_moved(self, board_id: str, user_id: str, message: dict):
        """Handle card movement."""
        try:
            card_id = message.get("card_id")
            new_column_id = message.get("new_column_id")
            new_position = message.get("new_position")
            
            db = next(get_db())
            
            # Update card position
            card = await self.card_crud.get(db, id=card_id)
            if card:
                update_data = {
                    "column_id": new_column_id,
                    "position": new_position
                }
                await self.card_crud.update(db, db_obj=card, obj_in=update_data)
                
                # Broadcast to other users
                await kanban_manager.broadcast_to_board(
                    board_id,
                    {
                        "type": "card_moved",
                        "card_id": card_id,
                        "new_column_id": new_column_id,
                        "new_position": new_position,
                        "moved_by": user_id,
                        "timestamp": NotificationService.get_current_timestamp()
                    },
                    exclude_user=user_id
                )
        except Exception as e:
            logger.error(f"Error handling card move: {e}")
    
    async def handle_card_created(self, board_id: str, user_id: str, message: dict):
        """Handle card creation."""
        try:
            card_data = message.get("card_data")
            
            db = next(get_db())
            card = await self.card_crud.create(db, obj_in=card_data)
            
            # Broadcast to other users
            await kanban_manager.broadcast_to_board(
                board_id,
                {
                    "type": "card_created",
                    "card": {
                        "id": card.id,
                        "title": card.title,
                        "description": card.description,
                        "column_id": card.column_id,
                        "position": card.position,
                        "assigned_to": card.assigned_to,
                        "priority": card.priority,
                        "due_date": card.due_date.isoformat() if card.due_date else None,
                        "labels": card.labels,
                        "created_at": card.created_at.isoformat()
                    },
                    "created_by": user_id,
                    "timestamp": NotificationService.get_current_timestamp()
                },
                exclude_user=user_id
            )
        except Exception as e:
            logger.error(f"Error handling card creation: {e}")
    
    async def handle_card_updated(self, board_id: str, user_id: str, message: dict):
        """Handle card update."""
        try:
            card_id = message.get("card_id")
            update_data = message.get("update_data")
            
            db = next(get_db())
            card = await self.card_crud.get(db, id=card_id)
            
            if card:
                updated_card = await self.card_crud.update(db, db_obj=card, obj_in=update_data)
                
                # Broadcast to other users
                await kanban_manager.broadcast_to_board(
                    board_id,
                    {
                        "type": "card_updated",
                        "card_id": card_id,
                        "update_data": update_data,
                        "updated_by": user_id,
                        "timestamp": NotificationService.get_current_timestamp()
                    },
                    exclude_user=user_id
                )
        except Exception as e:
            logger.error(f"Error handling card update: {e}")
    
    async def handle_card_deleted(self, board_id: str, user_id: str, message: dict):
        """Handle card deletion."""
        try:
            card_id = message.get("card_id")
            
            db = next(get_db())
            await self.card_crud.remove(db, id=card_id)
            
            # Broadcast to other users
            await kanban_manager.broadcast_to_board(
                board_id,
                {
                    "type": "card_deleted",
                    "card_id": card_id,
                    "deleted_by": user_id,
                    "timestamp": NotificationService.get_current_timestamp()
                },
                exclude_user=user_id
            )
        except Exception as e:
            logger.error(f"Error handling card deletion: {e}")
    
    async def handle_column_created(self, board_id: str, user_id: str, message: dict):
        """Handle column creation."""
        try:
            column_data = message.get("column_data")
            column_data["board_id"] = board_id
            
            db = next(get_db())
            column = await self.column_crud.create(db, obj_in=column_data)
            
            # Broadcast to other users
            await kanban_manager.broadcast_to_board(
                board_id,
                {
                    "type": "column_created",
                    "column": {
                        "id": column.id,
                        "name": column.name,
                        "position": column.position,
                        "board_id": column.board_id
                    },
                    "created_by": user_id,
                    "timestamp": NotificationService.get_current_timestamp()
                },
                exclude_user=user_id
            )
        except Exception as e:
            logger.error(f"Error handling column creation: {e}")
    
    async def handle_column_updated(self, board_id: str, user_id: str, message: dict):
        """Handle column update."""
        try:
            column_id = message.get("column_id")
            update_data = message.get("update_data")
            
            db = next(get_db())
            column = await self.column_crud.get(db, id=column_id)
            
            if column:
                await self.column_crud.update(db, db_obj=column, obj_in=update_data)
                
                # Broadcast to other users
                await kanban_manager.broadcast_to_board(
                    board_id,
                    {
                        "type": "column_updated",
                        "column_id": column_id,
                        "update_data": update_data,
                        "updated_by": user_id,
                        "timestamp": NotificationService.get_current_timestamp()
                    },
                    exclude_user=user_id
                )
        except Exception as e:
            logger.error(f"Error handling column update: {e}")
    
    async def handle_column_deleted(self, board_id: str, user_id: str, message: dict):
        """Handle column deletion."""
        try:
            column_id = message.get("column_id")
            
            db = next(get_db())
            await self.column_crud.remove(db, id=column_id)
            
            # Broadcast to other users
            await kanban_manager.broadcast_to_board(
                board_id,
                {
                    "type": "column_deleted",
                    "column_id": column_id,
                    "deleted_by": user_id,
                    "timestamp": NotificationService.get_current_timestamp()
                },
                exclude_user=user_id
            )
        except Exception as e:
            logger.error(f"Error handling column deletion: {e}")
    
    async def handle_typing(self, board_id: str, user_id: str, message: dict):
        """Handle typing indicator."""
        try:
            # Broadcast typing indicator to other users
            await kanban_manager.broadcast_to_board(
                board_id,
                {
                    "type": "typing",
                    "user_id": user_id,
                    "card_id": message.get("card_id"),
                    "is_typing": message.get("is_typing", True),
                    "timestamp": NotificationService.get_current_timestamp()
                },
                exclude_user=user_id
            )
        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}")


kanban_handler = KanbanWebSocketHandler()
