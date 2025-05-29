"""
Unit tests for core security functions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user_id
)


class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")
    
    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Different due to salt, but both should verify
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestTokenSecurity:
    """Test JWT token creation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "user123"
        token = create_access_token(subject=user_id)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are quite long
        assert "." in token  # JWT has dots separating parts
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "user123"
        token = create_refresh_token(subject=user_id)
        
        assert isinstance(token, str)
        assert len(token) > 100
        assert "." in token
    
    def test_verify_valid_token(self):
        """Test verification of valid token."""
        user_id = "user123"
        token = create_access_token(subject=user_id)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload.get("sub") == user_id
        assert "exp" in payload
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        assert payload is None
    
    def test_verify_expired_token(self):
        """Test verification of expired token."""
        user_id = "user123"
        
        # Create token with very short expiration
        with patch('app.core.security.settings.ACCESS_TOKEN_EXPIRE_MINUTES', -1):
            token = create_access_token(subject=user_id)
        
        payload = verify_token(token)
        assert payload is None
    
    def test_token_contains_correct_claims(self):
        """Test that token contains correct claims."""
        user_id = "user123"
        token = create_access_token(subject=user_id)
        payload = verify_token(token)
        
        assert payload.get("sub") == user_id
        assert payload.get("type") == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_refresh_token_type(self):
        """Test that refresh token has correct type."""
        user_id = "user123"
        token = create_refresh_token(subject=user_id)
        payload = verify_token(token)
        
        assert payload.get("sub") == user_id
        assert payload.get("type") == "refresh"


class TestGetCurrentUserId:
    """Test user ID extraction from token."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_id_success(self):
        """Test successful user ID extraction."""
        user_id = "user123"
        token = create_access_token(subject=user_id)
        
        result = await get_current_user_id(token)
        assert result == user_id
    
    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(self):
        """Test user ID extraction with invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):  # Should raise authentication error
            await get_current_user_id(invalid_token)
    
    @pytest.mark.asyncio
    async def test_get_current_user_id_expired_token(self):
        """Test user ID extraction with expired token."""
        user_id = "user123"
        
        # Create expired token
        with patch('app.core.security.settings.ACCESS_TOKEN_EXPIRE_MINUTES', -1):
            token = create_access_token(subject=user_id)
        
        with pytest.raises(Exception):  # Should raise authentication error
            await get_current_user_id(token)


class TestTokenEdgeCases:
    """Test edge cases for token handling."""
    
    def test_empty_subject(self):
        """Test token creation with empty subject."""
        token = create_access_token(subject="")
        payload = verify_token(token)
        
        assert payload.get("sub") == ""
    
    def test_none_subject(self):
        """Test token creation with None subject."""
        token = create_access_token(subject=None)
        payload = verify_token(token)
        
        assert payload.get("sub") is None
    
    def test_very_long_subject(self):
        """Test token creation with very long subject."""
        long_subject = "a" * 1000
        token = create_access_token(subject=long_subject)
        payload = verify_token(token)
        
        assert payload.get("sub") == long_subject
    
    def test_special_characters_in_subject(self):
        """Test token creation with special characters in subject."""
        special_subject = "user@domain.com!#$%^&*()"
        token = create_access_token(subject=special_subject)
        payload = verify_token(token)
        
        assert payload.get("sub") == special_subject
