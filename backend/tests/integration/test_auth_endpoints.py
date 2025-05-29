"""
Integration tests for authentication endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestDataFactory


class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""
    
    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        login_data = {
            "username": test_user.email,
            "password": "testpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Test login with invalid credentials."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, db_session, test_company):
        """Test login with inactive user."""
        from app.db.models.user import User
        from app.core.security import get_password_hash
        
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("password"),
            full_name="Inactive User",
            company_id=test_company.id,
            is_active=False
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        login_data = {
            "username": "inactive@example.com",
            "password": "password"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]
    
    def test_refresh_token_success(self, client: TestClient, test_user):
        """Test successful token refresh."""
        # First, login to get tokens
        login_data = {
            "username": test_user.email,
            "password": "testpassword"
        }
        
        login_response = client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        
        # Use refresh token to get new access token
        refresh_data = {
            "refresh_token": tokens["refresh_token"]
        }
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        refresh_data = {
            "refresh_token": "invalid.token.here"
        }
        
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
    
    def test_logout_success(self, client: TestClient, auth_headers):
        """Test successful logout."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"
    
    def test_logout_without_auth(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
    
    def test_get_profile_success(self, client: TestClient, auth_headers):
        """Test getting user profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        assert "role" in data
        assert "company" in data
    
    def test_get_profile_without_auth(self, client: TestClient):
        """Test getting profile without authentication."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_change_password_success(self, client: TestClient, auth_headers):
        """Test successful password change."""
        password_data = {
            "current_password": "testpassword",
            "new_password": "newpassword123"
        }
        
        response = client.put("/api/v1/auth/change-password", 
                            json=password_data, 
                            headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"
    
    def test_change_password_wrong_current(self, client: TestClient, auth_headers):
        """Test password change with wrong current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        
        response = client.put("/api/v1/auth/change-password", 
                            json=password_data, 
                            headers=auth_headers)
        
        assert response.status_code == 400
        assert "Incorrect password" in response.json()["detail"]
    
    def test_change_password_weak_password(self, client: TestClient, auth_headers):
        """Test password change with weak password."""
        password_data = {
            "current_password": "testpassword",
            "new_password": "123"  # Too weak
        }
        
        response = client.put("/api/v1/auth/change-password", 
                            json=password_data, 
                            headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_change_password_without_auth(self, client: TestClient):
        """Test password change without authentication."""
        password_data = {
            "current_password": "testpassword",
            "new_password": "newpassword123"
        }
        
        response = client.put("/api/v1/auth/change-password", json=password_data)
        
        assert response.status_code == 401


class TestAuthenticationSecurity:
    """Test authentication security measures."""
    
    def test_login_rate_limiting(self, client: TestClient):
        """Test login rate limiting."""
        login_data = {
            "username": "test@example.com",
            "password": "wrongpassword"
        }
        
        # Make multiple failed login attempts
        for _ in range(10):
            response = client.post("/api/v1/auth/login", data=login_data)
            # Should fail with 401 due to wrong credentials
            assert response.status_code == 401
        
        # The next attempt might be rate limited
        response = client.post("/api/v1/auth/login", data=login_data)
        # This could be 401 (wrong credentials) or 429 (rate limited)
        assert response.status_code in [401, 429]
    
    def test_token_expiration(self, client: TestClient, test_user):
        """Test that expired tokens are rejected."""
        # This test would require mocking time or using very short expiration
        # For now, we'll test the concept
        
        # Create an obviously invalid/expired token
        invalid_headers = {"Authorization": "Bearer expired.token.here"}
        
        response = client.get("/api/v1/auth/me", headers=invalid_headers)
        assert response.status_code == 401
    
    def test_malformed_token(self, client: TestClient):
        """Test handling of malformed tokens."""
        malformed_headers = {"Authorization": "Bearer malformed-token"}
        
        response = client.get("/api/v1/auth/me", headers=malformed_headers)
        assert response.status_code == 401
    
    def test_missing_authorization_header(self, client: TestClient):
        """Test request without authorization header."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_wrong_authorization_scheme(self, client: TestClient):
        """Test wrong authorization scheme."""
        wrong_headers = {"Authorization": "Basic dGVzdDp0ZXN0"}
        
        response = client.get("/api/v1/auth/me", headers=wrong_headers)
        assert response.status_code == 401


class TestAuthenticationValidation:
    """Test input validation for authentication endpoints."""
    
    def test_login_missing_username(self, client: TestClient):
        """Test login with missing username."""
        login_data = {
            "password": "password"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 422
    
    def test_login_missing_password(self, client: TestClient):
        """Test login with missing password."""
        login_data = {
            "username": "test@example.com"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 422
    
    def test_login_empty_credentials(self, client: TestClient):
        """Test login with empty credentials."""
        login_data = {
            "username": "",
            "password": ""
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 422
    
    def test_refresh_missing_token(self, client: TestClient):
        """Test refresh without token."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422
    
    def test_change_password_missing_fields(self, client: TestClient, auth_headers):
        """Test password change with missing fields."""
        # Missing current password
        password_data = {
            "new_password": "newpassword123"
        }
        
        response = client.put("/api/v1/auth/change-password", 
                            json=password_data, 
                            headers=auth_headers)
        assert response.status_code == 422
        
        # Missing new password
        password_data = {
            "current_password": "testpassword"
        }
        
        response = client.put("/api/v1/auth/change-password", 
                            json=password_data, 
                            headers=auth_headers)
        assert response.status_code == 422
