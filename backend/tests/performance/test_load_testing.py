"""
Load testing utilities and benchmarks for the FastAPI backend.
"""
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
from httpx import AsyncClient
from fastapi.testclient import TestClient


class LoadTestResult:
    """Container for load test results."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: List[int] = []
        self.errors: List[Exception] = []
        self.start_time: float = 0
        self.end_time: float = 0
        self.total_requests: int = 0
    
    @property
    def duration(self) -> float:
        """Total test duration in seconds."""
        return self.end_time - self.start_time
    
    @property
    def requests_per_second(self) -> float:
        """Average requests per second."""
        return self.total_requests / self.duration if self.duration > 0 else 0
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if not self.status_codes:
            return 0.0
        successful = sum(1 for code in self.status_codes if 200 <= code < 300)
        return (successful / len(self.status_codes)) * 100
    
    @property
    def avg_response_time(self) -> float:
        """Average response time in seconds."""
        return statistics.mean(self.response_times) if self.response_times else 0
    
    @property
    def median_response_time(self) -> float:
        """Median response time in seconds."""
        return statistics.median(self.response_times) if self.response_times else 0
    
    @property
    def p95_response_time(self) -> float:
        """95th percentile response time in seconds."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index]
    
    @property
    def p99_response_time(self) -> float:
        """99th percentile response time in seconds."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(0.99 * len(sorted_times))
        return sorted_times[index]
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of the load test results."""
        return {
            "total_requests": self.total_requests,
            "duration": round(self.duration, 2),
            "requests_per_second": round(self.requests_per_second, 2),
            "success_rate": round(self.success_rate, 2),
            "avg_response_time": round(self.avg_response_time * 1000, 2),  # Convert to ms
            "median_response_time": round(self.median_response_time * 1000, 2),
            "p95_response_time": round(self.p95_response_time * 1000, 2),
            "p99_response_time": round(self.p99_response_time * 1000, 2),
            "error_count": len(self.errors)
        }


class LoadTester:
    """Utility class for running load tests."""
    
    def __init__(self, client: TestClient, auth_headers: Dict[str, str]):
        self.client = client
        self.auth_headers = auth_headers
    
    def run_constant_load_test(
        self,
        endpoint: str,
        duration: int,
        requests_per_second: float,
        method: str = "GET",
        data: Dict[str, Any] = None
    ) -> LoadTestResult:
        """
        Run a constant load test for a specified duration.
        
        Args:
            endpoint: API endpoint to test
            duration: Test duration in seconds
            requests_per_second: Target requests per second
            method: HTTP method (GET, POST, etc.)
            data: Request data for POST/PUT requests
        
        Returns:
            LoadTestResult with performance metrics
        """
        result = LoadTestResult()
        result.start_time = time.time()
        
        interval = 1.0 / requests_per_second
        end_time = result.start_time + duration
        
        while time.time() < end_time:
            request_start = time.time()
            
            try:
                if method.upper() == "GET":
                    response = self.client.get(endpoint, headers=self.auth_headers)
                elif method.upper() == "POST":
                    response = self.client.post(endpoint, json=data, headers=self.auth_headers)
                elif method.upper() == "PUT":
                    response = self.client.put(endpoint, json=data, headers=self.auth_headers)
                else:
                    response = self.client.request(method, endpoint, headers=self.auth_headers)
                
                request_time = time.time() - request_start
                result.response_times.append(request_time)
                result.status_codes.append(response.status_code)
                result.total_requests += 1
                
            except Exception as e:
                result.errors.append(e)
            
            # Wait for next request (maintain constant rate)
            elapsed = time.time() - request_start
            if elapsed < interval:
                time.sleep(interval - elapsed)
        
        result.end_time = time.time()
        return result
    
    def run_burst_test(
        self,
        endpoint: str,
        burst_size: int,
        method: str = "GET",
        data: Dict[str, Any] = None
    ) -> LoadTestResult:
        """
        Run a burst test with concurrent requests.
        
        Args:
            endpoint: API endpoint to test
            burst_size: Number of concurrent requests
            method: HTTP method
            data: Request data for POST/PUT requests
        
        Returns:
            LoadTestResult with performance metrics
        """
        result = LoadTestResult()
        result.start_time = time.time()
        
        def make_request():
            request_start = time.time()
            try:
                if method.upper() == "GET":
                    response = self.client.get(endpoint, headers=self.auth_headers)
                elif method.upper() == "POST":
                    response = self.client.post(endpoint, json=data, headers=self.auth_headers)
                elif method.upper() == "PUT":
                    response = self.client.put(endpoint, json=data, headers=self.auth_headers)
                else:
                    response = self.client.request(method, endpoint, headers=self.auth_headers)
                
                request_time = time.time() - request_start
                return {
                    "response_time": request_time,
                    "status_code": response.status_code,
                    "error": None
                }
            except Exception as e:
                request_time = time.time() - request_start
                return {
                    "response_time": request_time,
                    "status_code": 500,
                    "error": e
                }
        
        with ThreadPoolExecutor(max_workers=burst_size) as executor:
            futures = [executor.submit(make_request) for _ in range(burst_size)]
            
            for future in as_completed(futures):
                response_data = future.result()
                result.response_times.append(response_data["response_time"])
                result.status_codes.append(response_data["status_code"])
                if response_data["error"]:
                    result.errors.append(response_data["error"])
                result.total_requests += 1
        
        result.end_time = time.time()
        return result
    
    def run_ramp_up_test(
        self,
        endpoint: str,
        max_users: int,
        ramp_duration: int,
        test_duration: int,
        method: str = "GET",
        data: Dict[str, Any] = None
    ) -> LoadTestResult:
        """
        Run a ramp-up load test that gradually increases load.
        
        Args:
            endpoint: API endpoint to test
            max_users: Maximum number of concurrent users
            ramp_duration: Time to reach max users (seconds)
            test_duration: Total test duration (seconds)
            method: HTTP method
            data: Request data
        
        Returns:
            LoadTestResult with performance metrics
        """
        result = LoadTestResult()
        result.start_time = time.time()
        
        def worker(user_id: int, start_delay: float):
            time.sleep(start_delay)
            end_time = result.start_time + test_duration
            
            while time.time() < end_time:
                request_start = time.time()
                try:
                    if method.upper() == "GET":
                        response = self.client.get(endpoint, headers=self.auth_headers)
                    elif method.upper() == "POST":
                        response = self.client.post(endpoint, json=data, headers=self.auth_headers)
                    else:
                        response = self.client.request(method, endpoint, headers=self.auth_headers)
                    
                    request_time = time.time() - request_start
                    result.response_times.append(request_time)
                    result.status_codes.append(response.status_code)
                    result.total_requests += 1
                    
                except Exception as e:
                    result.errors.append(e)
                
                time.sleep(0.1)  # Small delay between requests
        
        # Calculate start delays for gradual ramp-up
        with ThreadPoolExecutor(max_workers=max_users) as executor:
            futures = []
            for i in range(max_users):
                start_delay = (i / max_users) * ramp_duration
                future = executor.submit(worker, i, start_delay)
                futures.append(future)
            
            # Wait for all workers to complete
            for future in as_completed(futures):
                future.result()
        
        result.end_time = time.time()
        return result


class AsyncLoadTester:
    """Async utility class for running load tests."""
    
    def __init__(self, async_client: AsyncClient, auth_headers: Dict[str, str]):
        self.async_client = async_client
        self.auth_headers = auth_headers
    
    async def run_async_burst_test(
        self,
        endpoint: str,
        burst_size: int,
        method: str = "GET",
        data: Dict[str, Any] = None
    ) -> LoadTestResult:
        """
        Run an async burst test with concurrent requests.
        """
        result = LoadTestResult()
        result.start_time = time.time()
        
        async def make_async_request():
            request_start = time.time()
            try:
                if method.upper() == "GET":
                    response = await self.async_client.get(endpoint, headers=self.auth_headers)
                elif method.upper() == "POST":
                    response = await self.async_client.post(endpoint, json=data, headers=self.auth_headers)
                elif method.upper() == "PUT":
                    response = await self.async_client.put(endpoint, json=data, headers=self.auth_headers)
                else:
                    response = await self.async_client.request(method, endpoint, headers=self.auth_headers)
                
                request_time = time.time() - request_start
                return {
                    "response_time": request_time,
                    "status_code": response.status_code,
                    "error": None
                }
            except Exception as e:
                request_time = time.time() - request_start
                return {
                    "response_time": request_time,
                    "status_code": 500,
                    "error": e
                }
        
        # Create and execute concurrent tasks
        tasks = [make_async_request() for _ in range(burst_size)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for response_data in results:
            if isinstance(response_data, dict):
                result.response_times.append(response_data["response_time"])
                result.status_codes.append(response_data["status_code"])
                if response_data["error"]:
                    result.errors.append(response_data["error"])
            else:
                result.errors.append(response_data)
            result.total_requests += 1
        
        result.end_time = time.time()
        return result
    
    async def run_async_sustained_test(
        self,
        endpoint: str,
        duration: int,
        concurrent_users: int,
        method: str = "GET",
        data: Dict[str, Any] = None
    ) -> LoadTestResult:
        """
        Run an async sustained load test.
        """
        result = LoadTestResult()
        result.start_time = time.time()
        end_time = result.start_time + duration
        
        async def worker():
            while time.time() < end_time:
                request_start = time.time()
                try:
                    if method.upper() == "GET":
                        response = await self.async_client.get(endpoint, headers=self.auth_headers)
                    elif method.upper() == "POST":
                        response = await self.async_client.post(endpoint, json=data, headers=self.auth_headers)
                    else:
                        response = await self.async_client.request(method, endpoint, headers=self.auth_headers)
                    
                    request_time = time.time() - request_start
                    result.response_times.append(request_time)
                    result.status_codes.append(response.status_code)
                    result.total_requests += 1
                    
                except Exception as e:
                    result.errors.append(e)
                
                await asyncio.sleep(0.01)  # Small delay
        
        # Run concurrent workers
        tasks = [worker() for _ in range(concurrent_users)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        result.end_time = time.time()
        return result


@pytest.mark.performance
@pytest.mark.slow
class TestLoadTestingUtilities:
    """Test the load testing utilities themselves."""
    
    def test_constant_load_test(self, client: TestClient, auth_headers):
        """Test constant load testing utility."""
        tester = LoadTester(client, auth_headers)
        
        result = tester.run_constant_load_test(
            endpoint="/api/v1/health",
            duration=5,  # 5 seconds
            requests_per_second=2.0
        )
        
        assert result.total_requests >= 8  # Should make ~10 requests
        assert result.duration >= 4.5  # Should run for ~5 seconds
        assert result.success_rate > 90  # Most requests should succeed
        assert result.requests_per_second >= 1.5  # Should achieve target rate
    
    def test_burst_load_test(self, client: TestClient, auth_headers):
        """Test burst load testing utility."""
        tester = LoadTester(client, auth_headers)
        
        result = tester.run_burst_test(
            endpoint="/api/v1/health",
            burst_size=20
        )
        
        assert result.total_requests == 20
        assert result.duration < 10  # Should complete quickly
        assert result.success_rate > 80  # Most requests should succeed
    
    @pytest.mark.asyncio
    async def test_async_burst_test(self, async_client: AsyncClient, auth_headers):
        """Test async burst load testing utility."""
        tester = AsyncLoadTester(async_client, auth_headers)
        
        result = await tester.run_async_burst_test(
            endpoint="/api/v1/health",
            burst_size=50
        )
        
        assert result.total_requests == 50
        assert result.duration < 5  # Async should be faster
        assert result.success_rate > 80
    
    def test_load_test_result_metrics(self, client: TestClient, auth_headers):
        """Test load test result metrics calculation."""
        tester = LoadTester(client, auth_headers)
        
        result = tester.run_burst_test(
            endpoint="/api/v1/health",
            burst_size=10
        )
        
        summary = result.summary()
        
        # Verify all metrics are present
        required_metrics = [
            "total_requests", "duration", "requests_per_second",
            "success_rate", "avg_response_time", "median_response_time",
            "p95_response_time", "p99_response_time", "error_count"
        ]
        
        for metric in required_metrics:
            assert metric in summary
            assert isinstance(summary[metric], (int, float))
            assert summary[metric] >= 0


@pytest.mark.performance
@pytest.mark.slow
class TestRealWorldLoadScenarios:
    """Test real-world load scenarios."""
    
    def test_api_endpoint_load_scenarios(self, client: TestClient, auth_headers):
        """Test various API endpoints under load."""
        tester = LoadTester(client, auth_headers)
        
        scenarios = [
            {"endpoint": "/api/v1/health", "burst_size": 50, "expected_success_rate": 95},
            {"endpoint": "/api/v1/users/", "burst_size": 20, "expected_success_rate": 90},
            {"endpoint": "/api/v1/companies/", "burst_size": 15, "expected_success_rate": 90},
            {"endpoint": "/api/v1/suppliers/", "burst_size": 15, "expected_success_rate": 90},
        ]
        
        for scenario in scenarios:
            result = tester.run_burst_test(
                endpoint=scenario["endpoint"],
                burst_size=scenario["burst_size"]
            )
            
            assert result.success_rate >= scenario["expected_success_rate"], \
                f"Endpoint {scenario['endpoint']} failed load test: {result.success_rate}% success rate"
            
            assert result.avg_response_time < 2.0, \
                f"Endpoint {scenario['endpoint']} too slow: {result.avg_response_time:.3f}s avg response time"
    
    @pytest.mark.asyncio
    async def test_mixed_workload_scenario(self, async_client: AsyncClient, auth_headers):
        """Test mixed workload scenario with different endpoints."""
        tester = AsyncLoadTester(async_client, auth_headers)
        
        # Simulate mixed workload
        endpoints = [
            "/api/v1/health",
            "/api/v1/users/",
            "/api/v1/companies/",
            "/api/v1/suppliers/",
            "/api/v1/tenders/",
        ]
        
        # Run concurrent tests on different endpoints
        tasks = [
            tester.run_async_burst_test(endpoint, 10)
            for endpoint in endpoints
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all tests passed
        for i, result in enumerate(results):
            assert result.success_rate > 80, \
                f"Endpoint {endpoints[i]} failed: {result.success_rate}% success rate"
            
            assert result.avg_response_time < 3.0, \
                f"Endpoint {endpoints[i]} too slow: {result.avg_response_time:.3f}s"
    
    def test_database_intensive_load(self, client: TestClient, auth_headers):
        """Test database-intensive operations under load."""
        tester = LoadTester(client, auth_headers)
        
        # Test endpoints that perform database queries
        db_endpoints = [
            "/api/v1/users/",
            "/api/v1/suppliers/",
            "/api/v1/tenders/",
            "/api/v1/quotes/",
        ]
        
        for endpoint in db_endpoints:
            result = tester.run_constant_load_test(
                endpoint=endpoint,
                duration=10,  # 10 seconds
                requests_per_second=3.0
            )
            
            assert result.success_rate > 85, \
                f"DB endpoint {endpoint} failed: {result.success_rate}% success rate"
            
            assert result.p95_response_time < 2.0, \
                f"DB endpoint {endpoint} p95 too high: {result.p95_response_time:.3f}s"
