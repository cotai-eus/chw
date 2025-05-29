"""
Comprehensive Concurrent Scenarios Stress Tests

Advanced high-concurrency scenarios testing real-world usage patterns.
"""
import asyncio
import random
import time
import json
from typing import List, Dict, Any
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from tests.stress.conftest import StressTestRunner, StressTestConfig
from app.main import app


class TestRealWorldConcurrentScenarios:
    """Test realistic high-concurrency scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_mixed_workload_stress(self, heavy_stress_config):
        """Test mixed workload with different types of operations."""
        stress_runner = StressTestRunner(heavy_stress_config)
        
        # Simulate different user roles and behaviors
        user_behaviors = [
            {"weight": 0.4, "type": "reader", "operations": ["list", "view", "search"]},
            {"weight": 0.3, "type": "editor", "operations": ["create", "update", "list"]},
            {"weight": 0.2, "type": "admin", "operations": ["create", "update", "delete", "list"]},
            {"weight": 0.1, "type": "api_client", "operations": ["batch_create", "export", "import"]}
        ]
        
        async def mixed_workload_test(user_id: int, request_id: int, client: AsyncClient):
            """Simulate mixed user behavior."""
            # Select user behavior based on weights
            behavior = self._select_weighted_behavior(user_behaviors, user_id)
            operation = random.choice(behavior["operations"])
            
            # Execute operation based on type
            if operation == "list":
                response = await client.get("/api/v1/companies/")
            elif operation == "view":
                company_id = (user_id % 10) + 1
                response = await client.get(f"/api/v1/companies/{company_id}")
            elif operation == "search":
                response = await client.get("/api/v1/tenders/search?q=test")
            elif operation == "create":
                response = await client.post(
                    "/api/v1/tenders/",
                    json={
                        "title": f"Test Tender {user_id}-{request_id}",
                        "description": "Stress test tender",
                        "category": "TECHNOLOGY"
                    }
                )
            elif operation == "update":
                tender_id = (user_id % 5) + 1
                response = await client.put(
                    f"/api/v1/tenders/{tender_id}",
                    json={"description": f"Updated by user {user_id}"}
                )
            elif operation == "delete":
                tender_id = (user_id % 3) + 1
                response = await client.delete(f"/api/v1/tenders/{tender_id}")
            elif operation == "batch_create":
                # Simulate batch operations
                tenders = [
                    {
                        "title": f"Batch Tender {i}",
                        "description": "Batch created tender",
                        "category": "TECHNOLOGY"
                    }
                    for i in range(5)
                ]
                response = await client.post("/api/v1/tenders/batch", json=tenders)
            else:
                response = await client.get("/api/v1/companies/")
            
            # Allow various response codes depending on operation
            assert response.status_code in [200, 201, 204, 400, 401, 403, 404, 422]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                mixed_workload_test, client
            )
        
        # Custom assertions for mixed workload
        assert metrics.total_requests > 0
        assert metrics.successful_requests > metrics.total_requests * 0.7  # 70% success rate
        print(f"Mixed workload stress: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    def _select_weighted_behavior(self, behaviors: List[Dict], user_id: int) -> Dict:
        """Select behavior based on weights and user_id."""
        # Use user_id to ensure consistent behavior per user
        random.seed(user_id)
        rand = random.random()
        cumulative_weight = 0
        
        for behavior in behaviors:
            cumulative_weight += behavior["weight"]
            if rand <= cumulative_weight:
                return behavior
        
        return behaviors[-1]  # Fallback
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_burst_traffic_scenario(self, stress_config):
        """Test burst traffic patterns (flash crowds)."""
        
        async def burst_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate burst traffic to popular endpoints."""
            # Popular endpoints that might get burst traffic
            endpoints = [
                "/api/v1/tenders/",
                "/api/v1/companies/",
                "/api/v1/tenders/search?q=popular",
                "/api/v1/quotes/",
            ]
            
            endpoint = random.choice(endpoints)
            response = await client.get(endpoint)
            assert response.status_code in [200, 429, 503]  # Allow rate limiting/service unavailable
        
        # Configure for burst scenario
        burst_config = StressTestConfig(
            concurrent_users=300,  # High concurrency
            requests_per_user=3,   # Few requests per user
            test_duration_seconds=30,  # Short duration
            ramp_up_seconds=2,     # Very fast ramp up
            max_response_time_ms=3000,
            error_threshold_percent=20.0  # More lenient for burst
        )
        
        stress_runner = StressTestRunner(burst_config)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                burst_request, client
            )
        
        # Burst-specific assertions
        assert metrics.requests_per_second > 50  # High RPS expected
        print(f"Burst traffic: {metrics.requests_per_second:.2f} RPS, {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_gradual_load_increase(self):
        """Test gradual load increase to find breaking points."""
        
        async def simple_request(user_id: int, request_id: int, client: AsyncClient):
            """Simple request for load testing."""
            response = await client.get("/api/v1/companies/")
            assert response.status_code in [200, 429, 503]
        
        # Test with increasing load levels
        load_levels = [10, 25, 50, 100, 200, 300]
        results = {}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for concurrent_users in load_levels:
                print(f"Testing with {concurrent_users} concurrent users...")
                
                config = StressTestConfig(
                    concurrent_users=concurrent_users,
                    requests_per_user=5,
                    test_duration_seconds=30,
                    max_response_time_ms=5000,
                    error_threshold_percent=25.0
                )
                
                stress_runner = StressTestRunner(config)
                
                try:
                    metrics = await stress_runner.run_concurrent_test(
                        simple_request, client
                    )
                    
                    results[concurrent_users] = {
                        'success_rate': (metrics.successful_requests / metrics.total_requests) * 100,
                        'avg_response_time': metrics.average_response_time,
                        'rps': metrics.requests_per_second,
                        'memory_mb': metrics.memory_usage_mb
                    }
                    
                    # Stop if success rate drops below 50%
                    if results[concurrent_users]['success_rate'] < 50:
                        print(f"Performance degraded significantly at {concurrent_users} users")
                        break
                        
                except Exception as e:
                    print(f"Load test failed at {concurrent_users} users: {e}")
                    break
                
                # Brief pause between tests
                await asyncio.sleep(5)
        
        # Print results summary
        print("\nLoad Test Results:")
        for users, metrics in results.items():
            print(f"{users} users: {metrics['success_rate']:.1f}% success, "
                  f"{metrics['avg_response_time']:.0f}ms avg, "
                  f"{metrics['rps']:.1f} RPS")
        
        assert len(results) > 0, "No successful load tests completed"


class TestConcurrentDataModification:
    """Test concurrent data modification scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_tender_updates(self, stress_config):
        """Test concurrent updates to the same tender."""
        stress_runner = StressTestRunner(stress_config)
        
        # Use a fixed tender ID for all concurrent updates
        tender_id = 1
        
        async def concurrent_update(user_id: int, request_id: int, client: AsyncClient):
            """Update the same tender concurrently."""
            update_data = {
                "description": f"Updated by user {user_id} at {time.time()}",
                "updated_by": user_id
            }
            
            response = await client.put(
                f"/api/v1/tenders/{tender_id}",
                json=update_data
            )
            
            # Expect either success or conflict
            assert response.status_code in [200, 409, 422, 404]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                concurrent_update, client
            )
        
        # Should handle conflicts gracefully
        assert metrics.total_requests > 0
        print(f"Concurrent updates: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self, stress_config):
        """Test concurrent user session management."""
        stress_runner = StressTestRunner(stress_config)
        
        async def session_test(user_id: int, request_id: int, client: AsyncClient):
            """Test session creation and management."""
            # Login
            login_response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"testuser{user_id % 10}@example.com",
                    "password": "testpassword123"
                }
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                
                # Make authenticated requests
                await client.get("/api/v1/users/profile", headers=headers)
                await client.get("/api/v1/companies/", headers=headers)
                
                # Logout
                await client.post("/api/v1/auth/logout", headers=headers)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                session_test, client
            )
        
        print(f"Concurrent sessions: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestLongRunningOperations:
    """Test scenarios with long-running operations."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(self, light_stress_config):
        """Test concurrent file upload operations."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def file_upload_test(user_id: int, request_id: int, client: AsyncClient):
            """Simulate file upload."""
            # Create fake file data
            file_content = b"x" * (1024 * 10)  # 10KB file
            files = {
                "file": ("test_file.txt", file_content, "text/plain")
            }
            
            response = await client.post(
                "/api/v1/files/upload",
                files=files
            )
            
            assert response.status_code in [200, 201, 413, 422]  # Allow file size errors
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                file_upload_test, client
            )
        
        print(f"Concurrent uploads: {metrics.successful_requests}/{metrics.total_requests} successful")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_report_generation(self, light_stress_config):
        """Test concurrent report generation."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def report_generation_test(user_id: int, request_id: int, client: AsyncClient):
            """Test report generation."""
            response = await client.post(
                "/api/v1/reports/generate",
                json={
                    "type": "tender_summary",
                    "format": "pdf",
                    "user_id": user_id
                }
            )
            
            assert response.status_code in [200, 202, 400, 429]  # Allow async responses
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                report_generation_test, client
            )
        
        print(f"Concurrent reports: {metrics.successful_requests}/{metrics.total_requests} successful")
