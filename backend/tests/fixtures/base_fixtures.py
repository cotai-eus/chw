"""
Test fixtures for all test categories.
"""
import pytest
from typing import Dict, Any, Generator
from unittest.mock import Mock, MagicMock
import json
import tempfile
import os

@pytest.fixture
def mock_user_data() -> Dict[str, Any]:
    """Mock user data for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "is_superuser": False,
        "created_at": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def mock_company_data() -> Dict[str, Any]:
    """Mock company data for testing."""
    return {
        "id": 1,
        "name": "Test Company",
        "cnpj": "12.345.678/0001-90",
        "status": "active",
        "plan_type": "premium"
    }

@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = MagicMock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.query = Mock()
    session.close = Mock()
    return session

@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        temp.write('{"test": "data"}')
        temp_path = temp.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture
def mock_api_response():
    """Mock API response for testing."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"success": True, "data": {}}
    response.text = '{"success": true, "data": {}}'
    response.headers = {"Content-Type": "application/json"}
    return response

@pytest.fixture
def sample_json_data() -> Dict[str, Any]:
    """Sample JSON data for testing."""
    return {
        "string_field": "test string",
        "number_field": 42,
        "boolean_field": True,
        "array_field": [1, 2, 3],
        "object_field": {
            "nested_string": "nested value",
            "nested_number": 123
        }
    }

@pytest.fixture
def environment_variables():
    """Set and restore environment variables for testing."""
    original_env = os.environ.copy()
    test_env = {
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "sqlite:///./test.db",
        "SECRET_KEY": "test-secret-key-12345"
    }
    
    # Set test environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
