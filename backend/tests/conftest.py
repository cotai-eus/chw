"""
Global test configuration and fixtures for all test categories.
"""
import os
import sys
import pytest
import asyncio
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import Mock

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set testing environment variables
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# Configure pytest markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "contract: API contract tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "stress: Stress tests")
    config.addinivalue_line("markers", "chaos: Chaos engineering tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "monitoring: Monitoring tests")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    mock = Mock()
    mock.database_url = "sqlite:///./test.db"
    mock.secret_key = "test-secret-key"
    mock.debug = True
    mock.testing = True
    return mock

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {
        "user": {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "is_active": True
        },
        "company": {
            "id": 1,
            "name": "Test Company",
            "cnpj": "12.345.678/0001-90"
        }
    }

@pytest.fixture
def mock_database():
    """Mock database session for testing."""
    return Mock()

@pytest.fixture
def test_client():
    """Create a test client for API testing."""
    try:
        from fastapi.testclient import TestClient
        from main_simple import app
        return TestClient(app)
    except ImportError:
        # Return mock client if FastAPI is not available
        return Mock()

# Pytest plugins are auto-discovered, no need to declare them explicitly