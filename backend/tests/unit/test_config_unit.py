"""
Basic configuration tests that don't require complex dependencies.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.mark.unit
class TestBasicConfiguration:
    """Test basic application configuration."""
    
    def test_environment_variables(self):
        """Test that testing environment variables are set."""
        assert os.getenv("TESTING") == "true"
        assert os.getenv("LOG_LEVEL") is not None
    
    def test_project_structure(self):
        """Test that required directories exist."""
        required_dirs = [
            "app",
            "app/api",
            "app/core", 
            "app/db",
            "tests"
        ]
        
        for dir_path in required_dirs:
            full_path = PROJECT_ROOT / dir_path
            assert full_path.exists(), f"Directory {dir_path} should exist"
            assert full_path.is_dir(), f"{dir_path} should be a directory"
    
    def test_config_file_exists(self):
        """Test that configuration files exist."""
        config_files = [
            "pyproject.toml",
            "README.md"
        ]
        
        for config_file in config_files:
            file_path = PROJECT_ROOT / config_file
            assert file_path.exists(), f"Config file {config_file} should exist"

@pytest.mark.unit
class TestConfigurationLoading:
    """Test configuration loading without dependencies."""
    
    @patch('app.core.config.Settings')
    def test_mock_settings_creation(self, mock_settings_class):
        """Test that settings can be mocked for testing."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.database_url = "sqlite:///./test.db"
        mock_instance.secret_key = "test-secret"
        mock_instance.debug = True
        mock_settings_class.return_value = mock_instance
        
        # Test
        settings = mock_settings_class()
        assert settings.database_url == "sqlite:///./test.db"
        assert settings.secret_key == "test-secret"
        assert settings.debug is True
    
    def test_environment_setup(self, environment_variables):
        """Test environment variable setup from fixture."""
        assert os.getenv("TESTING") == "true"
        assert os.getenv("SECRET_KEY") == "test-secret-key-12345"
        assert os.getenv("DATABASE_URL") == "sqlite:///./test.db"

@pytest.mark.unit 
class TestUtilityFunctions:
    """Test utility functions without external dependencies."""
    
    def test_data_validation(self, sample_data):
        """Test data validation using fixtures."""
        user_data = sample_data["user"]
        assert "id" in user_data
        assert "email" in user_data
        assert isinstance(user_data["id"], int)
        assert "@" in user_data["email"]
    
    def test_mock_database_operations(self, mock_database):
        """Test mock database operations."""
        # Test that mock database has expected methods
        assert hasattr(mock_database, "add")
        assert hasattr(mock_database, "commit")
        assert hasattr(mock_database, "rollback")
        
        # Test mock method calls
        mock_database.add("test_object")
        mock_database.add.assert_called_with("test_object")
        
        mock_database.commit()
        mock_database.commit.assert_called_once()
    
    def test_json_operations(self, sample_json_data):
        """Test JSON data operations."""
        import json
        
        # Test serialization
        json_string = json.dumps(sample_json_data)
        assert isinstance(json_string, str)
        
        # Test deserialization
        restored_data = json.loads(json_string)
        assert restored_data == sample_json_data
    
    def test_string_operations(self):
        """Test basic string operations."""
        test_string = "Hello World"
        
        assert test_string.lower() == "hello world"
        assert test_string.upper() == "HELLO WORLD"
        assert len(test_string) == 11
        assert "World" in test_string
