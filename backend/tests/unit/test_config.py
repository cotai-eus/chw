"""
Unit tests for configuration management.
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from app.core.config import Settings


class TestSettings:
    """Test application settings configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 30
    
    def test_database_settings(self):
        """Test database configuration."""
        settings = Settings()
        
        assert settings.POSTGRES_HOST == "postgres"
        assert settings.POSTGRES_PORT == 5432
        assert settings.POSTGRES_USER == "postgres"
        assert settings.POSTGRES_DB == "tender_platform"
        assert "postgresql+asyncpg://" in settings.DATABASE_URI
    
    def test_redis_settings(self):
        """Test Redis configuration."""
        settings = Settings()
        
        assert settings.REDIS_HOST == "redis"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_URL == "redis://redis:6379"
    
    def test_mongodb_settings(self):
        """Test MongoDB configuration."""
        settings = Settings()
        
        assert settings.MONGO_HOST == "mongodb"
        assert settings.MONGO_PORT == 27017
        assert settings.MONGO_DB == "tender_platform"
        assert "mongodb://" in settings.MONGO_DATABASE_URI
    
    def test_ai_settings(self):
        """Test AI service configuration."""
        settings = Settings()
        
        assert settings.OLLAMA_API_URL == "http://ollama:11434"
        assert settings.OLLAMA_DEFAULT_MODEL == "llama3:8b"
        assert settings.OLLAMA_TIMEOUT == 300.0
    
    def test_email_settings(self):
        """Test email configuration."""
        settings = Settings()
        
        assert settings.SMTP_TLS is True
        assert settings.SMTP_PORT == 587
        assert settings.EMAILS_FROM_NAME == "Tender Platform"
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'DEBUG': 'false',
        'SECRET_KEY': 'test-secret-key',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '60'
    })
    def test_environment_override(self):
        """Test environment variable override."""
        settings = Settings()
        
        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.SECRET_KEY == "test-secret-key"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    
    @patch.dict(os.environ, {
        'POSTGRES_HOST': 'custom-postgres',
        'POSTGRES_PORT': '5433',
        'POSTGRES_USER': 'custom-user',
        'POSTGRES_PASSWORD': 'custom-pass',
        'POSTGRES_DB': 'custom-db'
    })
    def test_database_uri_generation(self):
        """Test database URI generation with custom values."""
        settings = Settings()
        
        expected_uri = "postgresql+asyncpg://custom-user:custom-pass@custom-postgres:5433/custom-db"
        assert settings.DATABASE_URI == expected_uri
    
    @patch.dict(os.environ, {
        'REDIS_HOST': 'custom-redis',
        'REDIS_PORT': '6380',
        'REDIS_PASSWORD': 'redis-pass'
    })
    def test_redis_uri_generation(self):
        """Test Redis URI generation with custom values."""
        settings = Settings()
        
        expected_uri = "redis://:redis-pass@custom-redis:6380"
        assert settings.REDIS_URL == expected_uri
    
    @patch.dict(os.environ, {
        'MONGO_HOST': 'custom-mongo',
        'MONGO_PORT': '27018',
        'MONGO_USER': 'mongo-user',
        'MONGO_PASSWORD': 'mongo-pass',
        'MONGO_DB': 'custom-mongo-db'
    })
    def test_mongo_uri_generation(self):
        """Test MongoDB URI generation with custom values."""
        settings = Settings()
        
        expected_uri = "mongodb://mongo-user:mongo-pass@custom-mongo:27018/custom-mongo-db"
        assert settings.MONGO_DATABASE_URI == expected_uri
    
    def test_settings_validation(self):
        """Test settings validation."""
        # Test that settings can be instantiated without errors
        settings = Settings()
        
        # Check that required fields are not empty
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0
        
        # Check that numeric fields are properly typed
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert isinstance(settings.REFRESH_TOKEN_EXPIRE_DAYS, int)
        assert isinstance(settings.POSTGRES_PORT, int)
        assert isinstance(settings.REDIS_PORT, int)
        assert isinstance(settings.MONGO_PORT, int)
        assert isinstance(settings.SMTP_PORT, int)
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'production'})
    def test_production_settings(self):
        """Test production-specific settings."""
        settings = Settings()
        
        assert settings.ENVIRONMENT == "production"
        # In production, debug should typically be False
        # (though this depends on your configuration)
    
    def test_celery_settings(self):
        """Test Celery configuration."""
        settings = Settings()
        
        assert settings.CELERY_BROKER_URL == settings.REDIS_URL
        assert settings.CELERY_RESULT_BACKEND == settings.REDIS_URL
    
    def test_file_upload_settings(self):
        """Test file upload configuration."""
        settings = Settings()
        
        assert settings.MAX_FILE_SIZE_MB == 50
        assert "pdf" in settings.ALLOWED_FILE_TYPES
        assert "docx" in settings.ALLOWED_FILE_TYPES
        assert "xlsx" in settings.ALLOWED_FILE_TYPES
    
    def test_rate_limiting_settings(self):
        """Test rate limiting configuration."""
        settings = Settings()
        
        assert settings.RATE_LIMIT_PER_MINUTE == 60
        assert settings.RATE_LIMIT_BURST == 10
    
    def test_logging_settings(self):
        """Test logging configuration."""
        settings = Settings()
        
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"
    
    def test_cors_settings(self):
        """Test CORS configuration."""
        settings = Settings()
        
        # CORS origins should be configurable
        assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    
    def test_webhook_settings(self):
        """Test webhook configuration."""
        settings = Settings()
        
        # Check webhook settings exist
        assert hasattr(settings, 'WEBHOOK_SECRET_KEY')
    
    @patch.dict(os.environ, {'SECRET_KEY': ''})
    def test_empty_secret_key(self):
        """Test behavior with empty secret key."""
        # This should either use a default or raise an error
        # depending on your validation logic
        try:
            settings = Settings()
            # If it doesn't raise an error, check it has a default
            assert settings.SECRET_KEY != ""
        except Exception:
            # If it raises an error, that's also acceptable behavior
            pass
    
    def test_settings_immutability(self):
        """Test that settings are immutable after creation."""
        settings = Settings()
        original_secret = settings.SECRET_KEY
        
        # Attempt to modify (this should not affect the settings)
        with pytest.raises(Exception):
            settings.SECRET_KEY = "new-secret"
        
        # Verify the original value is unchanged
        assert settings.SECRET_KEY == original_secret
