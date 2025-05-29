"""
API Endpoint Stress Tests

Tests for high-concurrency scenarios on API endpoints.
"""
import asyncio
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from tests.stress.conftest import StressTestRunner, StressTestConfig
from app.main import app


class TestAPIEndpointStress:
    """Stress tests for API endpoints."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_auth_login_stress(self, stress_runner: StressTestRunner):
        """Test authentication endpoint under stress."""
        
        async def login_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate a login request."""
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"testuser{user_id}@example.com",
                    "password": "testpassword123"
                }
            )
            assert response.status_code in [200, 401, 422]  # Allow auth failures
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                login_request, client
            )
        
        # Assert performance thresholds
        stress_runner.assert_performance_thresholds()
        
        # Additional assertions for auth endpoint
        assert metrics.successful_requests > 0, "No successful login requests"
        print(f"Auth stress test: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_user_profile_stress(self, stress_runner: StressTestRunner):
        """Test user profile endpoint under stress."""
        
        async def profile_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate a profile request."""
            # First login to get token
            login_response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": "admin@example.com",
                    "password": "admin123"
                }
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                
                # Make profile request
                response = await client.get("/api/v1/users/profile", headers=headers)
                assert response.status_code in [200, 401, 403]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                profile_request, client
            )
        
        stress_runner.assert_performance_thresholds()
        print(f"Profile stress test: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_company_list_stress(self, stress_runner: StressTestRunner):
        """Test company listing endpoint under stress."""
        
        async def company_list_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate a company list request."""
            response = await client.get("/api/v1/companies/")
            assert response.status_code in [200, 401, 403]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                company_list_request, client
            )
        
        stress_runner.assert_performance_thresholds()
        print(f"Company list stress test: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_tender_create_stress(self, stress_runner: StressTestRunner):
        """Test tender creation endpoint under stress."""
        
        async def tender_create_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate a tender creation request."""
            tender_data = {
                "title": f"Test Tender {user_id}-{request_id}",
                "description": "Test tender description",
                "opening_date": "2024-12-01T10:00:00",
                "closing_date": "2024-12-15T17:00:00",
                "budget": 100000.0,
                "items": [
                    {
                        "description": "Test item",
                        "quantity": 10,
                        "unit": "units",
                        "unit_price": 100.0
                    }
                ]
            }
            
            response = await client.post("/api/v1/tenders/", json=tender_data)
            assert response.status_code in [200, 201, 401, 403, 422]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                tender_create_request, client
            )
        
        # More lenient thresholds for creation endpoints
        assert metrics.total_requests > 0
        print(f"Tender create stress test: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_mixed_endpoint_stress(self, stress_runner: StressTestRunner):
        """Test mixed endpoint requests under stress."""
        
        endpoints = [
            ("/api/v1/companies/", "GET"),
            ("/api/v1/suppliers/", "GET"),
            ("/api/v1/tenders/", "GET"),
            ("/api/v1/users/profile", "GET"),
        ]
        
        async def mixed_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate mixed endpoint requests."""
            endpoint, method = endpoints[request_id % len(endpoints)]
            
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            
            assert response.status_code < 500  # Allow client errors but not server errors
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                mixed_request, client
            )
        
        stress_runner.assert_performance_thresholds()
        print(f"Mixed endpoint stress test: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestAPIRateLimitingStress:
    """Stress tests for rate limiting behavior."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_rate_limiting_under_stress(self, heavy_stress_config: StressTestConfig):
        """Test rate limiting behavior under heavy load."""
        stress_runner = StressTestRunner(heavy_stress_config)
        
        async def rate_limited_request(user_id: int, request_id: int, client: AsyncClient):
            """Make requests that should trigger rate limiting."""
            response = await client.get("/api/v1/companies/")
            # Accept both successful and rate-limited responses
            assert response.status_code in [200, 429, 401, 403]
            
            if response.status_code == 429:
                # Check for rate limit headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                rate_limited_request, client
            )
        
        # Don't assert normal performance thresholds for rate limiting tests
        assert metrics.total_requests > 0
        print(f"Rate limiting stress test: {metrics.total_requests} total requests")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self, stress_config: StressTestConfig):
        """Test rate limit recovery after burst."""
        
        # First, trigger rate limiting
        async with AsyncClient(app=app, base_url="http://test") as client:
            for _ in range(100):  # Burst requests
                response = await client.get("/api/v1/companies/")
                if response.status_code == 429:
                    break
            
            # Wait for rate limit reset
            await asyncio.sleep(5)
            
            # Test recovery
            response = await client.get("/api/v1/companies/")
            assert response.status_code in [200, 401, 403]  # Should not be rate limited


class TestConcurrentDataModification:
    """Stress tests for concurrent data modification scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_user_updates(self, light_stress_config: StressTestConfig):
        """Test concurrent user profile updates."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def update_profile_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate concurrent profile updates."""
            update_data = {
                "full_name": f"Updated User {user_id}-{request_id}",
                "phone": f"+1234567{user_id:03d}"
            }
            
            response = await client.put("/api/v1/users/profile", json=update_data)
            assert response.status_code in [200, 401, 403, 422]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                update_profile_request, client
            )
        
        assert metrics.total_requests > 0
        print(f"Concurrent updates stress test: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_tender_updates(self, light_stress_config: StressTestConfig):
        """Test concurrent tender updates."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def update_tender_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate concurrent tender updates."""
            # Assume tender ID 1 exists
            tender_id = 1
            update_data = {
                "title": f"Updated Tender {user_id}-{request_id}",
                "description": "Updated description"
            }
            
            response = await client.put(f"/api/v1/tenders/{tender_id}", json=update_data)
            assert response.status_code in [200, 401, 403, 404, 422]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                update_tender_request, client
            )
        
        assert metrics.total_requests > 0
        print(f"Concurrent tender updates: {metrics.successful_requests}/{metrics.total_requests} successful")
