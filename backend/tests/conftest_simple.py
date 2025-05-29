"""
Simplified conftest.py for basic testing.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from main_simple import app

# Test configuration
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return MagicMock()

@pytest.fixture
def sample_data():
    """Sample test data."""
    return {
        "user": {
            "email": "test@example.com",
            "name": "Test User",
            "role": "user"
        },
        "company": {
            "name": "Test Company",
            "cnpj": "12345678901234",
            "email": "company@test.com"
        }
    }

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Pytest configuration
pytest_plugins = []
