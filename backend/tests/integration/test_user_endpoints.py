"""
Integration tests for user management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestDataFactory


class TestUserEndpoints:
    """Test user management API endpoints."""
    
    def test_get_users_list(self, client: TestClient, auth_headers):
        """Test getting list of users."""
        response = client.get("/api/v1/users/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test user
    
    def test_get_users_pagination(self, client: TestClient, auth_headers):
        """Test user list pagination."""
        response = client.get("/api/v1/users/?skip=0&limit=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_get_user_by_id(self, client: TestClient, auth_headers, test_user):
        """Test getting specific user by ID."""
        response = client.get(f"/api/v1/users/{test_user.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
    
    def test_get_nonexistent_user(self, client: TestClient, auth_headers):
        """Test getting non-existent user."""
        response = client.get("/api/v1/users/nonexistent-id", headers=auth_headers)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_create_user_success(self, client: TestClient, admin_headers):
        """Test successful user creation."""
        user_data = TestDataFactory.user_create_data({
            "email": "newuser@example.com",
            "full_name": "New User",
            "role": "user"
        })
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=admin_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["role"] == user_data["role"]
        assert data["is_active"] is True
    
    def test_create_user_duplicate_email(self, client: TestClient, admin_headers, test_user):
        """Test creating user with duplicate email."""
        user_data = TestDataFactory.user_create_data({
            "email": test_user.email,  # Duplicate email
            "full_name": "Duplicate User"
        })
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=admin_headers)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_create_user_invalid_email(self, client: TestClient, admin_headers):
        """Test creating user with invalid email."""
        user_data = TestDataFactory.user_create_data({
            "email": "invalid-email",  # Invalid email format
        })
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=admin_headers)
        
        assert response.status_code == 422
    
    def test_create_user_weak_password(self, client: TestClient, admin_headers):
        """Test creating user with weak password."""
        user_data = TestDataFactory.user_create_data({
            "password": "123",  # Too weak
        })
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=admin_headers)
        
        assert response.status_code == 422
    
    def test_create_user_without_admin_permission(self, client: TestClient, auth_headers):
        """Test creating user without admin permissions."""
        user_data = TestDataFactory.user_create_data()
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=auth_headers)
        
        assert response.status_code == 403
    
    def test_update_user_success(self, client: TestClient, admin_headers, test_user):
        """Test successful user update."""
        update_data = {
            "full_name": "Updated Name",
            "role": "admin"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", 
                            json=update_data, 
                            headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "admin"
    
    def test_update_user_email(self, client: TestClient, admin_headers, test_user):
        """Test updating user email."""
        update_data = {
            "email": "updated@example.com"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", 
                            json=update_data, 
                            headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "updated@example.com"
    
    def test_update_user_duplicate_email(self, client: TestClient, admin_headers, test_user):
        """Test updating user with duplicate email."""
        # Create another user first
        user_data = TestDataFactory.user_create_data({
            "email": "another@example.com"
        })
        
        create_response = client.post("/api/v1/users/", 
                                    json=user_data, 
                                    headers=admin_headers)
        another_user = create_response.json()
        
        # Try to update first user with second user's email
        update_data = {
            "email": another_user["email"]
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", 
                            json=update_data, 
                            headers=admin_headers)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_update_nonexistent_user(self, client: TestClient, admin_headers):
        """Test updating non-existent user."""
        update_data = {
            "full_name": "Updated Name"
        }
        
        response = client.put("/api/v1/users/nonexistent-id", 
                            json=update_data, 
                            headers=admin_headers)
        
        assert response.status_code == 404
    
    def test_update_user_without_permission(self, client: TestClient, auth_headers, test_user):
        """Test updating user without admin permissions."""
        update_data = {
            "full_name": "Updated Name"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 403
    
    def test_deactivate_user(self, client: TestClient, admin_headers, test_user):
        """Test deactivating user."""
        response = client.put(f"/api/v1/users/{test_user.id}/deactivate", 
                            headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    def test_activate_user(self, client: TestClient, admin_headers, test_user):
        """Test activating user."""
        # First deactivate
        client.put(f"/api/v1/users/{test_user.id}/deactivate", 
                  headers=admin_headers)
        
        # Then activate
        response = client.put(f"/api/v1/users/{test_user.id}/activate", 
                            headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
    
    def test_delete_user(self, client: TestClient, admin_headers, test_user):
        """Test deleting user."""
        response = client.delete(f"/api/v1/users/{test_user.id}", 
                               headers=admin_headers)
        
        assert response.status_code == 200
        
        # Verify user is deleted
        get_response = client.get(f"/api/v1/users/{test_user.id}", 
                                headers=admin_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_user(self, client: TestClient, admin_headers):
        """Test deleting non-existent user."""
        response = client.delete("/api/v1/users/nonexistent-id", 
                               headers=admin_headers)
        
        assert response.status_code == 404
    
    def test_delete_user_without_permission(self, client: TestClient, auth_headers, test_user):
        """Test deleting user without admin permissions."""
        response = client.delete(f"/api/v1/users/{test_user.id}", 
                               headers=auth_headers)
        
        assert response.status_code == 403


class TestUserSearch:
    """Test user search functionality."""
    
    def test_search_users_by_email(self, client: TestClient, auth_headers, test_user):
        """Test searching users by email."""
        response = client.get(f"/api/v1/users/search?email={test_user.email}", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(user["email"] == test_user.email for user in data)
    
    def test_search_users_by_name(self, client: TestClient, auth_headers, test_user):
        """Test searching users by name."""
        response = client.get(f"/api/v1/users/search?name={test_user.full_name}", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(user["full_name"] == test_user.full_name for user in data)
    
    def test_search_users_by_role(self, client: TestClient, auth_headers):
        """Test searching users by role."""
        response = client.get("/api/v1/users/search?role=user", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert all(user["role"] == "user" for user in data)
    
    def test_search_users_no_results(self, client: TestClient, auth_headers):
        """Test user search with no results."""
        response = client.get("/api/v1/users/search?email=nonexistent@example.com", 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestUserProfile:
    """Test user profile management."""
    
    def test_get_own_profile(self, client: TestClient, auth_headers, test_user):
        """Test getting own profile."""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
    
    def test_update_own_profile(self, client: TestClient, auth_headers):
        """Test updating own profile."""
        update_data = {
            "full_name": "Updated Own Name"
        }
        
        response = client.put("/api/v1/users/me", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Own Name"
    
    def test_update_own_email(self, client: TestClient, auth_headers):
        """Test updating own email."""
        update_data = {
            "email": "newemail@example.com"
        }
        
        response = client.put("/api/v1/users/me", 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"
    
    def test_cannot_update_own_role(self, client: TestClient, auth_headers):
        """Test that users cannot update their own role."""
        update_data = {
            "role": "admin"
        }
        
        response = client.put("/api/v1/users/me", 
                            json=update_data, 
                            headers=auth_headers)
        
        # Should either ignore the role field or return an error
        assert response.status_code in [200, 400, 403]
        
        if response.status_code == 200:
            # If successful, role should not have changed
            data = response.json()
            assert data["role"] != "admin"


class TestUserValidation:
    """Test input validation for user endpoints."""
    
    def test_create_user_missing_required_fields(self, client: TestClient, admin_headers):
        """Test creating user with missing required fields."""
        # Missing email
        user_data = {
            "password": "password",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=admin_headers)
        assert response.status_code == 422
    
    def test_update_user_invalid_email_format(self, client: TestClient, admin_headers, test_user):
        """Test updating user with invalid email format."""
        update_data = {
            "email": "invalid-email-format"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", 
                            json=update_data, 
                            headers=admin_headers)
        
        assert response.status_code == 422
    
    def test_create_user_invalid_role(self, client: TestClient, admin_headers):
        """Test creating user with invalid role."""
        user_data = TestDataFactory.user_create_data({
            "role": "invalid_role"
        })
        
        response = client.post("/api/v1/users/", 
                             json=user_data, 
                             headers=admin_headers)
        
        assert response.status_code == 422
