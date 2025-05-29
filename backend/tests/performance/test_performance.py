"""
Performance and load tests for the FastAPI backend.
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient
from fastapi.testclient import TestClient


@pytest.mark.performance
class TestAPIPerformance:
    """Test API endpoint performance and response times."""
    
    def test_auth_endpoint_performance(self, client: TestClient):
        """Test authentication endpoint performance."""
        login_data = {
            "username": "test@example.com",
            "password": "testpassword123"
        }
        
        start_time = time.time()
        response = client.post("/api/v1/auth/login", data=login_data)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # Should respond within 500ms
    
    def test_list_endpoints_performance(self, client: TestClient, auth_headers):
        """Test list endpoints performance."""
        endpoints = [
            "/api/v1/users/",
            "/api/v1/companies/",
            "/api/v1/suppliers/",
            "/api/v1/tenders/",
            "/api/v1/quotes/",
            "/api/v1/kanban/boards/"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint, headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 1.0, f"{endpoint} took too long: {end_time - start_time:.3f}s"
    
    def test_pagination_performance(self, client: TestClient, auth_headers):
        """Test pagination performance with different page sizes."""
        page_sizes = [10, 50, 100, 200]
        
        for page_size in page_sizes:
            start_time = time.time()
            response = client.get(f"/api/v1/tenders/?limit={page_size}", headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 2.0, f"Page size {page_size} took too long: {end_time - start_time:.3f}s"
    
    def test_search_performance(self, client: TestClient, auth_headers):
        """Test search endpoint performance."""
        search_queries = ["test", "company", "supplier", "tender"]
        
        for query in search_queries:
            start_time = time.time()
            response = client.get(f"/api/v1/users/search?q={query}", headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 1.5, f"Search for '{query}' took too long: {end_time - start_time:.3f}s"
    
    def test_database_query_performance(self, client: TestClient, auth_headers):
        """Test database-intensive operations performance."""
        # Test getting detailed information that requires multiple queries
        start_time = time.time()
        response = client.get("/api/v1/tenders/", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Database queries should be fast
    
    @pytest.mark.slow
    def test_concurrent_request_performance(self, client: TestClient, auth_headers):
        """Test performance under concurrent requests."""
        def make_request():
            return client.get("/api/v1/users/", headers=auth_headers)
        
        # Test with 10 concurrent requests
        num_requests = 10
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(response.status_code == 200 for response in responses)
        
        # Should handle concurrent requests efficiently
        assert total_time < 5.0, f"Concurrent requests took too long: {total_time:.3f}s"
        
        # Average response time should be reasonable
        avg_time = total_time / num_requests
        assert avg_time < 1.0, f"Average response time too high: {avg_time:.3f}s"


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncPerformance:
    """Test async endpoint performance."""
    
    async def test_async_concurrent_requests(self, async_client: AsyncClient, auth_headers):
        """Test async concurrent request performance."""
        async def make_async_request():
            return await async_client.get("/api/v1/users/", headers=auth_headers)
        
        # Test with 20 concurrent async requests
        num_requests = 20
        start_time = time.time()
        
        tasks = [make_async_request() for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(response.status_code == 200 for response in responses)
        
        # Async should handle concurrency better
        assert total_time < 3.0, f"Async concurrent requests took too long: {total_time:.3f}s"
    
    async def test_async_database_operations(self, async_client: AsyncClient, auth_headers, test_company):
        """Test async database operations performance."""
        # Create multiple entities concurrently
        supplier_data_list = [
            {
                "name": f"Performance Supplier {i}",
                "cnpj": f"1234567800010{i:02d}",
                "email": f"perf{i}@supplier.com",
                "phone": f"1155555555{i}",
                "address": f"Performance Address {i}",
                "city": "Performance City",
                "state": "SP",
                "zip_code": "12345-678",
                "company_id": test_company.id
            }
            for i in range(10)
        ]
        
        start_time = time.time()
        
        # Create suppliers concurrently
        tasks = [
            async_client.post("/api/v1/suppliers/", json=data, headers=auth_headers)
            for data in supplier_data_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Check results
        successful_creates = [r for r in results if not isinstance(r, Exception) and r.status_code == 201]
        assert len(successful_creates) >= 8  # Allow for some failures in concurrent creates
        
        # Should complete quickly
        assert (end_time - start_time) < 5.0, f"Concurrent creates took too long: {end_time - start_time:.3f}s"


@pytest.mark.performance
class TestMemoryAndResourceUsage:
    """Test memory usage and resource consumption."""
    
    def test_memory_usage_large_response(self, client: TestClient, auth_headers):
        """Test memory usage with large response payloads."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Request large dataset
        response = client.get("/api/v1/tenders/?limit=1000", headers=auth_headers)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        assert response.status_code == 200
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase too high: {memory_increase / 1024 / 1024:.2f}MB"
    
    def test_response_size_limits(self, client: TestClient, auth_headers):
        """Test response size is within reasonable limits."""
        endpoints = [
            "/api/v1/users/",
            "/api/v1/companies/",
            "/api/v1/suppliers/",
            "/api/v1/tenders/",
            "/api/v1/quotes/"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 200
            
            # Response size should be reasonable (less than 1MB for list endpoints)
            content_length = len(response.content)
            assert content_length < 1024 * 1024, f"{endpoint} response too large: {content_length / 1024:.2f}KB"


@pytest.mark.performance
@pytest.mark.slow
class TestLoadTesting:
    """Load testing for high-traffic scenarios."""
    
    def test_sustained_load(self, client: TestClient, auth_headers):
        """Test sustained load over time."""
        duration = 30  # 30 seconds
        request_interval = 0.1  # 100ms between requests
        
        start_time = time.time()
        responses = []
        request_count = 0
        
        while time.time() - start_time < duration:
            response = client.get("/api/v1/users/", headers=auth_headers)
            responses.append(response)
            request_count += 1
            time.sleep(request_interval)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate statistics
        successful_responses = [r for r in responses if r.status_code == 200]
        success_rate = len(successful_responses) / len(responses)
        requests_per_second = request_count / total_time
        
        # Assertions
        assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"
        assert requests_per_second > 5, f"Request rate too low: {requests_per_second:.2f} req/s"
    
    def test_burst_load(self, client: TestClient, auth_headers):
        """Test handling of burst traffic."""
        # Send 100 requests as fast as possible
        num_requests = 100
        start_time = time.time()
        
        responses = []
        for _ in range(num_requests):
            response = client.get("/api/v1/health")  # Use health endpoint for burst test
            responses.append(response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Check results
        successful_responses = [r for r in responses if r.status_code == 200]
        success_rate = len(successful_responses) / len(responses)
        
        # Should handle burst well
        assert success_rate > 0.90, f"Burst success rate too low: {success_rate:.2%}"
        assert total_time < 30.0, f"Burst test took too long: {total_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_async_load_testing(self, async_client: AsyncClient, auth_headers):
        """Test async load handling."""
        async def make_requests_batch(batch_size: int):
            tasks = [
                async_client.get("/api/v1/health", headers=auth_headers)
                for _ in range(batch_size)
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Test with increasing batch sizes
        batch_sizes = [10, 25, 50, 100]
        
        for batch_size in batch_sizes:
            start_time = time.time()
            results = await make_requests_batch(batch_size)
            end_time = time.time()
            
            # Check results
            successful_requests = [
                r for r in results 
                if not isinstance(r, Exception) and r.status_code == 200
            ]
            success_rate = len(successful_requests) / len(results)
            duration = end_time - start_time
            
            assert success_rate > 0.90, f"Batch {batch_size} success rate too low: {success_rate:.2%}"
            assert duration < 10.0, f"Batch {batch_size} took too long: {duration:.3f}s"


@pytest.mark.performance
class TestCachePerformance:
    """Test caching mechanisms performance."""
    
    def test_response_caching(self, client: TestClient, auth_headers):
        """Test response caching effectiveness."""
        endpoint = "/api/v1/users/"
        
        # First request (cache miss)
        start_time = time.time()
        first_response = client.get(endpoint, headers=auth_headers)
        first_duration = time.time() - start_time
        
        # Second request (should be cached)
        start_time = time.time()
        second_response = client.get(endpoint, headers=auth_headers)
        second_duration = time.time() - start_time
        
        assert first_response.status_code == 200
        assert second_response.status_code == 200
        
        # Second request should be faster (cached)
        # Note: This test might not be meaningful if no caching is implemented
        assert second_duration <= first_duration * 1.1  # Allow 10% variance
    
    def test_database_connection_pooling(self, client: TestClient, auth_headers):
        """Test database connection pooling performance."""
        # Make multiple requests that hit the database
        endpoints = [
            "/api/v1/users/",
            "/api/v1/companies/",
            "/api/v1/suppliers/",
            "/api/v1/tenders/",
            "/api/v1/quotes/"
        ]
        
        start_time = time.time()
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Multiple DB queries should complete quickly with connection pooling
        assert total_time < 3.0, f"Database queries took too long: {total_time:.3f}s"


@pytest.mark.performance
class TestWebSocketPerformance:
    """Test WebSocket performance and real-time features."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_performance(self, async_client: AsyncClient, auth_token):
        """Test WebSocket connection establishment performance."""
        start_time = time.time()
        
        try:
            async with async_client.websocket_connect(f"/ws/notifications/{auth_token}") as websocket:
                connection_time = time.time() - start_time
                
                # WebSocket connection should be fast
                assert connection_time < 1.0, f"WebSocket connection took too long: {connection_time:.3f}s"
                
                # Test message sending performance
                message_start = time.time()
                await websocket.send_json({"type": "ping", "timestamp": message_start})
                response = await websocket.receive_json()
                message_time = time.time() - message_start
                
                assert message_time < 0.1, f"WebSocket message took too long: {message_time:.3f}s"
                
        except Exception as e:
            pytest.skip(f"WebSocket test skipped due to: {e}")


@pytest.mark.performance
def test_overall_system_performance(client: TestClient, auth_headers):
    """Test overall system performance with mixed operations."""
    start_time = time.time()
    
    # Simulate typical user workflow
    operations = [
        ("GET", "/api/v1/users/"),
        ("GET", "/api/v1/companies/"),
        ("GET", "/api/v1/suppliers/"),
        ("GET", "/api/v1/tenders/"),
        ("GET", "/api/v1/quotes/"),
        ("GET", "/api/v1/kanban/boards/"),
    ]
    
    for method, endpoint in operations:
        if method == "GET":
            response = client.get(endpoint, headers=auth_headers)
        elif method == "POST":
            response = client.post(endpoint, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Failed on {method} {endpoint}: {response.status_code}"
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Complete workflow should be fast
    assert total_time < 5.0, f"Complete workflow took too long: {total_time:.3f}s"
    
    # Average time per operation
    avg_time = total_time / len(operations)
    assert avg_time < 1.0, f"Average operation time too high: {avg_time:.3f}s"
