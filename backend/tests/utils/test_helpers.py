"""
Test utility helpers for consistent testing across the test suite.
"""
import asyncio
import json
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.company import Company
from app.models.tender import Tender
from app.models.quote import Quote
from app.models.kanban import KanbanBoard, KanbanCard


class TestDataBuilder:
    """Builder pattern for creating test data with realistic relationships."""
    
    def __init__(self, db: Session):
        self.db = db
        self.created_objects: List[Any] = []
    
    def user(self, **kwargs) -> 'TestDataBuilder':
        """Create a test user."""
        from app.crud.crud_user import crud_user
        
        user_data = {
            "email": f"user_{uuid.uuid4()}@example.com",
            "username": f"user_{uuid.uuid4()}",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            **kwargs
        }
        
        if "password" not in kwargs:
            user_data["password"] = "testpassword123"
        
        user = crud_user.create(self.db, obj_in=user_data)
        self.created_objects.append(user)
        return self
    
    def company(self, user: Optional[User] = None, **kwargs) -> 'TestDataBuilder':
        """Create a test company."""
        from app.crud.crud_company import crud_company
        
        if not user and self.created_objects:
            user = next((obj for obj in self.created_objects if isinstance(obj, User)), None)
        
        company_data = {
            "name": f"Test Company {uuid.uuid4()}",
            "cnpj": f"{uuid.uuid4().hex[:14]}",
            "email": f"company_{uuid.uuid4()}@example.com",
            "owner_id": user.id if user else None,
            "is_active": True,
            **kwargs
        }
        
        company = crud_company.create(self.db, obj_in=company_data)
        self.created_objects.append(company)
        return self
    
    def tender(self, company: Optional[Company] = None, **kwargs) -> 'TestDataBuilder':
        """Create a test tender."""
        from app.crud.crud_tender import crud_tender
        
        if not company and self.created_objects:
            company = next((obj for obj in self.created_objects if isinstance(obj, Company)), None)
        
        tender_data = {
            "title": f"Test Tender {uuid.uuid4()}",
            "description": "Test tender description",
            "company_id": company.id if company else None,
            "deadline": datetime.utcnow() + timedelta(days=30),
            "status": "draft",
            "budget": 100000.0,
            **kwargs
        }
        
        tender = crud_tender.create(self.db, obj_in=tender_data)
        self.created_objects.append(tender)
        return self
    
    def quote(self, tender: Optional[Tender] = None, user: Optional[User] = None, **kwargs) -> 'TestDataBuilder':
        """Create a test quote."""
        from app.crud.crud_quote import crud_quote
        
        if not tender and self.created_objects:
            tender = next((obj for obj in self.created_objects if isinstance(obj, Tender)), None)
        
        if not user and self.created_objects:
            user = next((obj for obj in self.created_objects if isinstance(obj, User)), None)
        
        quote_data = {
            "tender_id": tender.id if tender else None,
            "supplier_id": user.id if user else None,
            "total_price": 85000.0,
            "status": "submitted",
            "notes": "Test quote notes",
            **kwargs
        }
        
        quote = crud_quote.create(self.db, obj_in=quote_data)
        self.created_objects.append(quote)
        return self
    
    def kanban_board(self, company: Optional[Company] = None, **kwargs) -> 'TestDataBuilder':
        """Create a test Kanban board."""
        from app.crud.crud_kanban import crud_kanban_board
        
        if not company and self.created_objects:
            company = next((obj for obj in self.created_objects if isinstance(obj, Company)), None)
        
        board_data = {
            "name": f"Test Board {uuid.uuid4()}",
            "description": "Test Kanban board",
            "company_id": company.id if company else None,
            **kwargs
        }
        
        board = crud_kanban_board.create(self.db, obj_in=board_data)
        self.created_objects.append(board)
        return self
    
    def build(self) -> List[Any]:
        """Return all created objects."""
        return self.created_objects
    
    def get_latest(self, model_type: type) -> Optional[Any]:
        """Get the latest created object of a specific type."""
        for obj in reversed(self.created_objects):
            if isinstance(obj, model_type):
                return obj
        return None
    
    def cleanup(self):
        """Clean up all created objects."""
        # Note: In tests, this is usually handled by test database rollback
        pass


class APITestHelper:
    """Helper class for API testing with authentication and common operations."""
    
    def __init__(self, client: Union[TestClient, AsyncClient], user: Optional[User] = None):
        self.client = client
        self.user = user
        self._auth_headers: Optional[Dict[str, str]] = None
    
    @property
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the test user."""
        if not self._auth_headers and self.user:
            access_token = create_access_token(subject=self.user.id)
            self._auth_headers = {"Authorization": f"Bearer {access_token}"}
        return self._auth_headers or {}
    
    def set_user(self, user: User):
        """Set the user for authentication."""
        self.user = user
        self._auth_headers = None  # Reset headers
    
    async def async_get(self, url: str, **kwargs) -> Any:
        """Async GET request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        
        if isinstance(self.client, AsyncClient):
            return await self.client.get(url, headers=headers, **kwargs)
        else:
            return self.client.get(url, headers=headers, **kwargs)
    
    async def async_post(self, url: str, **kwargs) -> Any:
        """Async POST request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        
        if isinstance(self.client, AsyncClient):
            return await self.client.post(url, headers=headers, **kwargs)
        else:
            return self.client.post(url, headers=headers, **kwargs)
    
    async def async_put(self, url: str, **kwargs) -> Any:
        """Async PUT request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        
        if isinstance(self.client, AsyncClient):
            return await self.client.put(url, headers=headers, **kwargs)
        else:
            return self.client.put(url, headers=headers, **kwargs)
    
    async def async_delete(self, url: str, **kwargs) -> Any:
        """Async DELETE request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        
        if isinstance(self.client, AsyncClient):
            return await self.client.delete(url, headers=headers, **kwargs)
        else:
            return self.client.delete(url, headers=headers, **kwargs)
    
    def get(self, url: str, **kwargs) -> Any:
        """GET request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        return self.client.get(url, headers=headers, **kwargs)
    
    def post(self, url: str, **kwargs) -> Any:
        """POST request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        return self.client.post(url, headers=headers, **kwargs)
    
    def put(self, url: str, **kwargs) -> Any:
        """PUT request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        return self.client.put(url, headers=headers, **kwargs)
    
    def delete(self, url: str, **kwargs) -> Any:
        """DELETE request with authentication."""
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers)
        return self.client.delete(url, headers=headers, **kwargs)


class FileTestHelper:
    """Helper for file-related testing."""
    
    @staticmethod
    def create_temp_file(content: str = "Test file content", suffix: str = ".txt") -> str:
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    
    @staticmethod
    def create_temp_pdf(content: str = "Test PDF content") -> str:
        """Create a temporary PDF file for testing."""
        # This would require a PDF library like reportlab
        # For now, create a simple text file with PDF extension
        with tempfile.NamedTemporaryFile(mode='w', suffix=".pdf", delete=False) as f:
            f.write(content)
            return f.name
    
    @staticmethod
    def create_temp_image(format: str = "PNG") -> str:
        """Create a temporary image file for testing."""
        # This would require PIL/Pillow
        # For now, create a simple file
        suffix = f".{format.lower()}"
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write("fake image content")
            return f.name


class MockWebSocketManager:
    """Mock WebSocket manager for testing real-time features."""
    
    def __init__(self):
        self.connections: Dict[str, List[Mock]] = {}
        self.messages: List[Dict[str, Any]] = []
    
    async def connect(self, websocket: Mock, channel: str):
        """Mock WebSocket connection."""
        if channel not in self.connections:
            self.connections[channel] = []
        self.connections[channel].append(websocket)
    
    def disconnect(self, websocket: Mock, channel: str):
        """Mock WebSocket disconnection."""
        if channel in self.connections:
            if websocket in self.connections[channel]:
                self.connections[channel].remove(websocket)
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Mock broadcast message to channel."""
        self.messages.append({"channel": channel, "message": message})
        
        if channel in self.connections:
            for websocket in self.connections[channel]:
                await websocket.send_json(message)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Mock send message to specific user."""
        await self.broadcast_to_channel(f"user_{user_id}", message)
    
    def get_messages_for_channel(self, channel: str) -> List[Dict[str, Any]]:
        """Get messages sent to a specific channel."""
        return [msg["message"] for msg in self.messages if msg["channel"] == channel]
    
    def clear_messages(self):
        """Clear all stored messages."""
        self.messages.clear()


class AsyncTestHelper:
    """Helper for async testing operations."""
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float = 5.0):
        """Run a coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
        """Wait for a condition to become true."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if condition_func():
                return True
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                return False
            
            await asyncio.sleep(interval)
    
    @staticmethod
    async def collect_async_results(async_generators, max_items: int = 100):
        """Collect results from async generators."""
        results = []
        
        for async_gen in async_generators:
            async for item in async_gen:
                results.append(item)
                if len(results) >= max_items:
                    break
        
        return results


class DatabaseTestHelper:
    """Helper for database testing operations."""
    
    @staticmethod
    def assert_model_fields(model_instance: Any, expected_fields: Dict[str, Any]):
        """Assert that model instance has expected field values."""
        for field_name, expected_value in expected_fields.items():
            actual_value = getattr(model_instance, field_name)
            assert actual_value == expected_value, f"Field {field_name}: expected {expected_value}, got {actual_value}"
    
    @staticmethod
    def count_table_rows(db: Session, model_class: type) -> int:
        """Count rows in a table."""
        return db.query(model_class).count()
    
    @staticmethod
    def get_last_created(db: Session, model_class: type, order_by: str = "created_at"):
        """Get the last created record from a table."""
        return db.query(model_class).order_by(getattr(model_class, order_by).desc()).first()


class PerformanceTestHelper:
    """Helper for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """Measure function execution time."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    async def measure_async_execution_time(coro):
        """Measure async coroutine execution time."""
        import time
        start_time = time.time()
        result = await coro
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    def memory_usage():
        """Get current memory usage."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # MB


class SecurityTestHelper:
    """Helper for security testing."""
    
    @staticmethod
    def create_expired_token(user_id: int) -> str:
        """Create an expired JWT token for testing."""
        from app.core.security import create_access_token
        from datetime import datetime, timedelta
        
        # Create token that expired 1 hour ago
        expires_delta = timedelta(hours=-1)
        return create_access_token(
            subject=user_id,
            expires_delta=expires_delta
        )
    
    @staticmethod
    def create_malformed_token() -> str:
        """Create a malformed JWT token for testing."""
        return "malformed.token.here"
    
    @staticmethod
    def create_invalid_signature_token() -> str:
        """Create a token with invalid signature for testing."""
        # This would be a properly formatted JWT but with wrong signature
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.invalid_signature"


# Test data constants
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_USERNAME = "testuser"
TEST_COMPANY_NAME = "Test Company Ltd"
TEST_CNPJ = "12345678000195"

# Test file content templates
TEST_PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000074 00000 n\n0000000120 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"

TEST_WORD_CONTENT = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00"  # Start of a Word document

TEST_EXCEL_CONTENT = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00"  # Start of an Excel document
