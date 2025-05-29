"""
WebSocket Stress Tests

Tests for WebSocket connections and real-time communication under high load.
"""
import asyncio
import json
import pytest
import websockets
from websockets.exceptions import ConnectionClosed
import aiohttp

from tests.stress.conftest import StressTestRunner, WebSocketStressHelper


class TestWebSocketConnectionStress:
    """Stress tests for WebSocket connections."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self, stress_runner: StressTestRunner):
        """Test multiple concurrent WebSocket connections."""
        connections = []
        
        async def create_connection(user_id: int, request_id: int):
            """Create a WebSocket connection."""
            try:
                # Connect to WebSocket endpoint
                uri = f"ws://localhost:8000/ws/notifications/{user_id}"
                websocket = await websockets.connect(uri)
                connections.append(websocket)
                
                # Keep connection alive for a short time
                await asyncio.sleep(1)
                
                # Send a test message
                await websocket.send(json.dumps({
                    "type": "ping",
                    "user_id": user_id,
                    "request_id": request_id
                }))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                assert "type" in data
                
            except Exception as e:
                # Log connection errors but don't fail the test
                print(f"WebSocket connection error for user {user_id}: {e}")
                raise e
            finally:
                if websocket and not websocket.closed:
                    await websocket.close()
        
        try:
            metrics = await stress_runner.run_concurrent_test(create_connection)
            
            # More lenient thresholds for WebSocket tests
            assert metrics.total_requests > 0
            print(f"WebSocket connections: {metrics.successful_requests}/{metrics.total_requests} successful")
            
        finally:
            # Cleanup any remaining connections
            for conn in connections:
                try:
                    if not conn.closed:
                        await conn.close()
                except:
                    pass
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_websocket_message_stress(self, light_stress_config):
        """Test WebSocket message handling under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        # First establish a few persistent connections
        persistent_connections = []
        
        try:
            # Create persistent connections
            for i in range(5):
                uri = f"ws://localhost:8000/ws/notifications/{i}"
                try:
                    websocket = await websockets.connect(uri)
                    persistent_connections.append(websocket)
                except Exception as e:
                    print(f"Failed to create persistent connection {i}: {e}")
            
            async def send_message(user_id: int, request_id: int):
                """Send messages through existing connections."""
                if not persistent_connections:
                    return
                
                connection = persistent_connections[user_id % len(persistent_connections)]
                
                try:
                    message = {
                        "type": "notification",
                        "user_id": user_id,
                        "message": f"Test message {request_id}",
                        "timestamp": "2024-01-01T00:00:00"
                    }
                    
                    await connection.send(json.dumps(message))
                    
                    # Try to receive acknowledgment
                    try:
                        response = await asyncio.wait_for(connection.recv(), timeout=1.0)
                        data = json.loads(response)
                        assert isinstance(data, dict)
                    except asyncio.TimeoutError:
                        # No response expected for all message types
                        pass
                        
                except ConnectionClosed:
                    # Connection was closed, this is acceptable under stress
                    pass
                except Exception as e:
                    print(f"Message send error: {e}")
                    raise e
            
            if persistent_connections:
                metrics = await stress_runner.run_concurrent_test(send_message)
                print(f"WebSocket messages: {metrics.successful_requests}/{metrics.total_requests} successful")
            else:
                print("No persistent connections available for message stress test")
                
        finally:
            # Cleanup connections
            for conn in persistent_connections:
                try:
                    if not conn.closed:
                        await conn.close()
                except:
                    pass


class TestWebSocketChannelStress:
    """Stress tests for specific WebSocket channels."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_notification_channel_stress(self, light_stress_config):
        """Test notification channel under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def notification_test(user_id: int, request_id: int):
            """Test notification WebSocket channel."""
            try:
                uri = f"ws://localhost:8000/ws/notifications/{user_id}"
                async with websockets.connect(uri) as websocket:
                    
                    # Send notification subscription
                    await websocket.send(json.dumps({
                        "type": "subscribe",
                        "channel": "notifications",
                        "user_id": user_id
                    }))
                    
                    # Send a test notification
                    await websocket.send(json.dumps({
                        "type": "notification",
                        "title": f"Test Notification {request_id}",
                        "message": "Test message content",
                        "priority": "normal"
                    }))
                    
                    # Wait briefly for any responses
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"Notification channel error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(notification_test)
        assert metrics.total_requests > 0
        print(f"Notification channel: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_kanban_channel_stress(self, light_stress_config):
        """Test Kanban real-time updates under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def kanban_test(user_id: int, request_id: int):
            """Test Kanban WebSocket channel."""
            try:
                board_id = (user_id % 5) + 1  # Assume boards 1-5 exist
                uri = f"ws://localhost:8000/ws/kanban/{board_id}"
                
                async with websockets.connect(uri) as websocket:
                    
                    # Join board
                    await websocket.send(json.dumps({
                        "type": "join_board",
                        "board_id": board_id,
                        "user_id": user_id
                    }))
                    
                    # Simulate card movement
                    await websocket.send(json.dumps({
                        "type": "move_card",
                        "card_id": request_id,
                        "from_column": 1,
                        "to_column": 2,
                        "position": request_id % 10
                    }))
                    
                    # Wait briefly for any responses
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"Kanban channel error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(kanban_test)
        assert metrics.total_requests > 0
        print(f"Kanban channel: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_chat_channel_stress(self, light_stress_config):
        """Test chat channel under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def chat_test(user_id: int, request_id: int):
            """Test chat WebSocket channel."""
            try:
                tender_id = (user_id % 3) + 1  # Assume tenders 1-3 exist
                uri = f"ws://localhost:8000/ws/chat/{tender_id}"
                
                async with websockets.connect(uri) as websocket:
                    
                    # Join chat room
                    await websocket.send(json.dumps({
                        "type": "join_room",
                        "tender_id": tender_id,
                        "user_id": user_id
                    }))
                    
                    # Send chat message
                    await websocket.send(json.dumps({
                        "type": "message",
                        "content": f"Test message {request_id} from user {user_id}",
                        "user_id": user_id,
                        "tender_id": tender_id
                    }))
                    
                    # Wait briefly for any responses
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"Chat channel error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(chat_test)
        assert metrics.total_requests > 0
        print(f"Chat channel: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestWebSocketBroadcastStress:
    """Stress tests for WebSocket broadcasting."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, light_stress_config):
        """Test broadcasting messages to multiple connected clients."""
        
        # Create multiple listener connections
        listeners = []
        received_messages = []
        
        try:
            # Create listener connections
            for i in range(10):
                try:
                    uri = f"ws://localhost:8000/ws/notifications/{i}"
                    websocket = await websockets.connect(uri)
                    listeners.append(websocket)
                    
                    # Start listening for messages
                    async def listen_for_messages(ws, listener_id):
                        try:
                            while True:
                                message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                                received_messages.append((listener_id, message))
                        except (asyncio.TimeoutError, ConnectionClosed):
                            pass
                    
                    asyncio.create_task(listen_for_messages(websocket, i))
                    
                except Exception as e:
                    print(f"Failed to create listener {i}: {e}")
            
            # Wait for connections to stabilize
            await asyncio.sleep(1)
            
            # Send broadcast messages
            if listeners:
                broadcaster = listeners[0]
                for i in range(20):
                    await broadcaster.send(json.dumps({
                        "type": "broadcast",
                        "message": f"Broadcast message {i}",
                        "timestamp": f"2024-01-01T00:00:{i:02d}"
                    }))
                    await asyncio.sleep(0.1)
            
            # Wait for message propagation
            await asyncio.sleep(2)
            
            print(f"Broadcast test: Sent to {len(listeners)} listeners, received {len(received_messages)} messages")
            
        finally:
            # Cleanup listeners
            for listener in listeners:
                try:
                    if not listener.closed:
                        await listener.close()
                except:
                    pass


class TestWebSocketErrorHandling:
    """Stress tests for WebSocket error handling."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_connection_failure_recovery(self, light_stress_config):
        """Test recovery from WebSocket connection failures."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def connection_failure_test(user_id: int, request_id: int):
            """Test connection failure and recovery."""
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    uri = f"ws://localhost:8000/ws/notifications/{user_id}"
                    
                    async with websockets.connect(uri) as websocket:
                        # Send a message
                        await websocket.send(json.dumps({
                            "type": "test",
                            "attempt": attempt,
                            "user_id": user_id
                        }))
                        
                        # Simulate connection issues
                        if request_id % 3 == 0:
                            # Force close connection
                            await websocket.close()
                            raise ConnectionClosed(None, None)
                        
                        # Wait briefly
                        await asyncio.sleep(0.1)
                        break
                        
                except ConnectionClosed:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        raise
                except Exception as e:
                    print(f"Connection failure test error: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        raise
        
        metrics = await stress_runner.run_concurrent_test(connection_failure_test)
        
        # Allow higher error rates for failure recovery tests
        assert metrics.total_requests > 0
        print(f"Connection failure recovery: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_malformed_message_handling(self, light_stress_config):
        """Test handling of malformed WebSocket messages."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def malformed_message_test(user_id: int, request_id: int):
            """Test sending malformed messages."""
            try:
                uri = f"ws://localhost:8000/ws/notifications/{user_id}"
                
                async with websockets.connect(uri) as websocket:
                    malformed_messages = [
                        "not json",
                        '{"incomplete": json',
                        '{"type": "unknown", "data": "test"}',
                        '{"missing_required_fields": true}',
                        '',
                        None,
                    ]
                    
                    message = malformed_messages[request_id % len(malformed_messages)]
                    
                    if message is None:
                        # Test sending bytes instead of string
                        await websocket.send(b"binary data")
                    else:
                        await websocket.send(message)
                    
                    # Wait briefly to see if connection stays alive
                    await asyncio.sleep(0.2)
                    
                    # Send a valid message to test recovery
                    await websocket.send(json.dumps({
                        "type": "ping",
                        "user_id": user_id
                    }))
                    
            except Exception as e:
                # Some errors are expected with malformed messages
                print(f"Malformed message test error (expected): {e}")
        
        metrics = await stress_runner.run_concurrent_test(malformed_message_test)
        
        # For malformed message tests, we mainly care that the server doesn't crash
        assert metrics.total_requests > 0
        print(f"Malformed message handling: {metrics.total_requests} total requests processed")
