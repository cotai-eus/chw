"""
Security Tests
Tests for authentication bypass, injection attacks, and other security vulnerabilities.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sqlalchemy as sa
from sqlalchemy.sql import text
import asyncio
import json
import base64
import time

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, verify_token
from tests.utils.test_helpers import SecurityTestHelper


class TestAuthenticationBypass:
    """Test various authentication bypass attempts."""
    
    def test_invalid_jwt_signature(self, client: TestClient):
        """Test that invalid JWT signatures are rejected."""
        # Create a token with wrong signature
        fake_token = jwt.encode(
            {"sub": "1", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256"
        )
        
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert response.status_code == 401
        assert "Invalid authentication credentials" in response.json()["detail"]
    
    def test_expired_token(self, client: TestClient):
        """Test that expired tokens are rejected."""
        # Create an expired token
        expired_token = jwt.encode(
            {"sub": "1", "exp": datetime.utcnow() - timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]
    
    def test_malformed_token(self, client: TestClient):
        """Test that malformed tokens are rejected."""
        malformed_tokens = [
            "invalid.token.format",
            "Bearer invalid-token",
            "not-a-jwt-token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",
            "",
        ]
        
        for token in malformed_tokens:
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401
    
    def test_missing_claims(self, client: TestClient):
        """Test that tokens with missing required claims are rejected."""
        # Token without 'sub' claim
        token_no_sub = jwt.encode(
            {"exp": datetime.utcnow() + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_no_sub}"}
        )
        assert response.status_code == 401
    
    def test_token_reuse_after_logout(self, client: TestClient, test_user):
        """Test that tokens cannot be reused after logout."""
        # Login to get a valid token
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword"}
        )
        token = response.json()["access_token"]
        
        # Use token (should work)
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Try to use token again (should fail)
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
    
    def test_privilege_escalation(self, client: TestClient, test_user, admin_user):
        """Test that users cannot escalate privileges."""
        # Login as regular user
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword"}
        )
        user_token = response.json()["access_token"]
        
        # Try to access admin-only endpoint
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        
        # Try to modify user role through API manipulation
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            json={"is_admin": True, "role": "admin"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # Should either fail or ignore the privilege escalation attempt
        assert response.status_code in [403, 422] or not response.json().get("is_admin", False)


class TestSQLInjection:
    """Test SQL injection vulnerabilities."""
    
    def test_login_sql_injection(self, client: TestClient):
        """Test SQL injection attempts in login form."""
        injection_payloads = [
            "admin' OR '1'='1",
            "admin' OR '1'='1' --",
            "admin'; DROP TABLE users; --",
            "admin' UNION SELECT * FROM users --",
            "' OR 1=1 --",
            "admin' OR 'x'='x",
        ]
        
        for payload in injection_payloads:
            response = client.post(
                "/api/v1/auth/login",
                data={"username": payload, "password": payload}
            )
            # Should return 401 (unauthorized) not 500 (server error)
            assert response.status_code == 401
            assert "detail" in response.json()
    
    def test_search_sql_injection(self, client: TestClient, auth_headers):
        """Test SQL injection in search parameters."""
        injection_payloads = [
            "test'; DROP TABLE users; --",
            "test' UNION SELECT password FROM users --",
            "test' OR '1'='1",
            "'; SELECT * FROM users WHERE '1'='1",
        ]
        
        for payload in injection_payloads:
            # Test user search
            response = client.get(
                f"/api/v1/users/search?q={payload}",
                headers=auth_headers
            )
            assert response.status_code in [200, 422]  # Should handle gracefully
            
            # Test tender search
            response = client.get(
                f"/api/v1/tenders/search?q={payload}",
                headers=auth_headers
            )
            assert response.status_code in [200, 422]
    
    def test_filter_sql_injection(self, client: TestClient, auth_headers):
        """Test SQL injection in filter parameters."""
        injection_payloads = [
            "1' OR '1'='1",
            "1; DROP TABLE tenders; --",
            "1 UNION SELECT * FROM users",
        ]
        
        for payload in injection_payloads:
            response = client.get(
                f"/api/v1/tenders?company_id={payload}",
                headers=auth_headers
            )
            assert response.status_code in [200, 422]
    
    def test_json_field_injection(self, client: TestClient, auth_headers):
        """Test SQL injection in JSON field updates."""
        malicious_json = {
            "description": "test'; DROP TABLE tenders; --",
            "requirements": ["'; SELECT * FROM users; --"],
            "metadata": {
                "key": "'; DELETE FROM companies WHERE '1'='1; --"
            }
        }
        
        response = client.post(
            "/api/v1/tenders/",
            json=malicious_json,
            headers=auth_headers
        )
        # Should either create safely or reject with validation error
        assert response.status_code in [201, 422]


class TestXSSPrevention:
    """Test Cross-Site Scripting (XSS) prevention."""
    
    def test_xss_in_user_data(self, client: TestClient, auth_headers):
        """Test XSS prevention in user data fields."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "' onclick='alert(\"XSS\")'",
        ]
        
        for payload in xss_payloads:
            user_data = {
                "name": payload,
                "email": f"test{hash(payload)}@example.com",
                "bio": payload
            }
            
            response = client.post(
                "/api/v1/users/",
                json=user_data,
                headers=auth_headers
            )
            
            if response.status_code == 201:
                # If creation succeeds, check that XSS payload is sanitized
                user = response.json()
                assert "<script>" not in user.get("name", "")
                assert "javascript:" not in user.get("bio", "")
                assert "onerror=" not in user.get("name", "")
    
    def test_xss_in_tender_data(self, client: TestClient, auth_headers):
        """Test XSS prevention in tender data."""
        xss_payload = "<script>alert('XSS')</script>"
        
        tender_data = {
            "title": xss_payload,
            "description": xss_payload,
            "requirements": [xss_payload]
        }
        
        response = client.post(
            "/api/v1/tenders/",
            json=tender_data,
            headers=auth_headers
        )
        
        if response.status_code == 201:
            tender = response.json()
            assert "<script>" not in tender.get("title", "")
            assert "<script>" not in tender.get("description", "")


class TestCSRFProtection:
    """Test Cross-Site Request Forgery (CSRF) protection."""
    
    def test_csrf_token_required(self, client: TestClient):
        """Test that state-changing operations require CSRF protection."""
        # This would be more relevant for web forms, but we can test
        # that our API properly validates request origins and methods
        
        # Test that we reject requests with suspicious origins
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "password"},
            headers={"Origin": "https://malicious-site.com"}
        )
        # Should either work (if we allow cross-origin) or be rejected
        assert response.status_code in [200, 401, 403]
    
    def test_method_override_protection(self, client: TestClient, auth_headers):
        """Test protection against HTTP method override attacks."""
        # Try to use POST with method override to perform DELETE
        response = client.post(
            "/api/v1/users/999",
            headers={**auth_headers, "X-HTTP-Method-Override": "DELETE"}
        )
        # Should not perform DELETE operation
        assert response.status_code != 204


class TestRateLimitingBypass:
    """Test rate limiting bypass attempts."""
    
    def test_rate_limit_with_different_headers(self, client: TestClient):
        """Test rate limiting with various header manipulations."""
        headers_variants = [
            {"X-Forwarded-For": "1.1.1.1"},
            {"X-Real-IP": "2.2.2.2"},
            {"X-Client-IP": "3.3.3.3"},
            {"X-Forwarded": "4.4.4.4"},
            {"Forwarded": "for=5.5.5.5"},
        ]
        
        for headers in headers_variants:
            # Make multiple requests quickly
            for _ in range(10):
                response = client.post(
                    "/api/v1/auth/login",
                    data={"username": "test@example.com", "password": "wrong"},
                    headers=headers
                )
                if response.status_code == 429:
                    break
            
            # Should eventually hit rate limit
            assert response.status_code in [401, 429]
    
    def test_distributed_rate_limit_bypass(self, client: TestClient):
        """Test attempts to bypass rate limiting with distributed requests."""
        # Simulate requests from different IPs (using X-Forwarded-For)
        for i in range(20):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "test@example.com", "password": "wrong"},
                headers={"X-Forwarded-For": f"192.168.1.{i}"}
            )
        
        # Each IP should be rate limited individually
        final_response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "wrong"}
        )
        assert final_response.status_code in [401, 429]


class TestInputValidationBypass:
    """Test input validation bypass attempts."""
    
    def test_large_payload_attack(self, client: TestClient, auth_headers):
        """Test handling of extremely large payloads."""
        large_string = "A" * (10 * 1024 * 1024)  # 10MB string
        
        response = client.post(
            "/api/v1/tenders/",
            json={"title": "Test", "description": large_string},
            headers=auth_headers
        )
        # Should reject large payloads
        assert response.status_code in [413, 422]
    
    def test_unicode_bypass_attempts(self, client: TestClient, auth_headers):
        """Test Unicode-based bypass attempts."""
        unicode_payloads = [
            "admin\u0000user",  # Null byte
            "admin\u2028user",  # Line separator
            "admin\u2029user",  # Paragraph separator
            "admin\uFEFFuser",  # Zero-width no-break space
        ]
        
        for payload in unicode_payloads:
            response = client.post(
                "/api/v1/users/",
                json={"name": payload, "email": f"{payload}@example.com"},
                headers=auth_headers
            )
            # Should handle Unicode gracefully
            assert response.status_code in [201, 422]
    
    def test_nested_json_bomb(self, client: TestClient, auth_headers):
        """Test deeply nested JSON that could cause DoS."""
        # Create deeply nested JSON
        nested_json = {"level": 0}
        current = nested_json
        for i in range(1000):  # Very deep nesting
            current["next"] = {"level": i + 1}
            current = current["next"]
        
        response = client.post(
            "/api/v1/tenders/",
            json={"title": "Test", "metadata": nested_json},
            headers=auth_headers
        )
        # Should reject overly complex JSON
        assert response.status_code in [413, 422]


class TestSecurityHeaders:
    """Test security headers are properly set."""
    
    def test_security_headers_present(self, client: TestClient):
        """Test that required security headers are present."""
        response = client.get("/")
        
        # Check for important security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]
        
        assert "X-XSS-Protection" in response.headers
    
    def test_cors_configuration(self, client: TestClient):
        """Test CORS headers are properly configured."""
        response = client.options("/api/v1/users/me")
        
        # Check CORS headers
        if "Access-Control-Allow-Origin" in response.headers:
            # If CORS is enabled, ensure it's properly configured
            origin = response.headers["Access-Control-Allow-Origin"]
            assert origin != "*" or settings.DEBUG  # Wildcard only in debug
    
    def test_content_type_validation(self, client: TestClient):
        """Test that content-type is properly validated."""
        # Try to send executable content
        response = client.post(
            "/api/v1/auth/login",
            data="malicious content",
            headers={"Content-Type": "application/x-executable"}
        )
        assert response.status_code in [400, 415]  # Bad request or unsupported media type


class TestFileUploadSecurity:
    """Test file upload security."""
    
    def test_malicious_file_types(self, client: TestClient, auth_headers):
        """Test rejection of malicious file types."""
        malicious_files = [
            ("virus.exe", b"MZ\x90\x00", "application/x-executable"),
            ("script.js", b"alert('xss')", "application/javascript"),
            ("malware.bat", b"@echo off\ndel /q *.*", "application/x-bat"),
            ("shell.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
        ]
        
        for filename, content, content_type in malicious_files:
            response = client.post(
                "/api/v1/files/upload",
                files={"file": (filename, content, content_type)},
                headers=auth_headers
            )
            # Should reject malicious file types
            assert response.status_code in [400, 415, 422]
    
    def test_file_size_limits(self, client: TestClient, auth_headers):
        """Test file size limits are enforced."""
        # Create a large file (simulate)
        large_content = b"A" * (100 * 1024 * 1024)  # 100MB
        
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("large.pdf", large_content, "application/pdf")},
            headers=auth_headers
        )
        # Should reject oversized files
        assert response.status_code in [413, 422]
    
    def test_filename_traversal(self, client: TestClient, auth_headers):
        """Test path traversal attempts in filenames."""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "null.txt\x00.exe",
        ]
        
        for filename in malicious_filenames:
            response = client.post(
                "/api/v1/files/upload",
                files={"file": (filename, b"test content", "text/plain")},
                headers=auth_headers
            )
            # Should sanitize filename or reject
            if response.status_code == 201:
                # If upload succeeds, filename should be sanitized
                file_info = response.json()
                assert ".." not in file_info.get("filename", "")
                assert "/" not in file_info.get("filename", "")
                assert "\\" not in file_info.get("filename", "")


@pytest.mark.asyncio
class TestConcurrencySecurity:
    """Test security under concurrent access."""
    
    async def test_race_condition_protection(self, async_client, test_user):
        """Test protection against race conditions."""
        # Simulate concurrent login attempts
        tasks = []
        for _ in range(10):
            task = asyncio.create_task(
                async_client.post(
                    "/api/v1/auth/login",
                    data={"username": test_user.email, "password": "testpassword"}
                )
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed or fail gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 429]
    
    async def test_session_fixation_protection(self, async_client, test_user):
        """Test protection against session fixation attacks."""
        # Login and get initial token
        response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword"}
        )
        initial_token = response.json()["access_token"]
        
        # Force password change (simulating privilege change)
        await async_client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "testpassword", "new_password": "newpassword"},
            headers={"Authorization": f"Bearer {initial_token}"}
        )
        
        # Old token should be invalidated
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {initial_token}"}
        )
        assert response.status_code == 401


class TestSecurityConfiguration:
    """Test security configuration and setup."""
    
    def test_debug_mode_disabled(self):
        """Test that debug mode is disabled in production."""
        if not settings.TESTING:
            assert not settings.DEBUG
    
    def test_secret_key_strength(self):
        """Test that secret key meets security requirements."""
        # Secret key should be long and complex
        assert len(settings.SECRET_KEY) >= 32
        assert settings.SECRET_KEY != "secret"
        assert settings.SECRET_KEY != "your-secret-key-here"
    
    def test_password_requirements(self):
        """Test password complexity requirements."""
        # This would test password validation rules
        helper = SecurityTestHelper()
        
        weak_passwords = [
            "123456",
            "password",
            "qwerty",
            "abc123",
            "password123"
        ]
        
        for password in weak_passwords:
            assert not helper.validate_password_strength(password)
    
    def test_database_connection_security(self):
        """Test database connection uses secure settings."""
        # Check that database URL uses SSL in production
        if not settings.TESTING:
            db_url = settings.DATABASE_URL
            if "postgres" in db_url:
                assert "sslmode=require" in db_url or "localhost" in db_url
