"""
Stress Test Configuration

Configuration and utilities for stress testing scenarios.
"""
import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import psutil
import aiohttp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


@dataclass
class StressTestConfig:
    """Configuration for stress tests."""
    concurrent_users: int = 100
    requests_per_user: int = 10
    test_duration_seconds: int = 60
    ramp_up_seconds: int = 10
    ramp_down_seconds: int = 5
    max_response_time_ms: int = 1000
    error_threshold_percent: float = 5.0
    memory_threshold_mb: int = 512
    cpu_threshold_percent: float = 80.0


@dataclass
class StressTestMetrics:
    """Metrics collected during stress tests."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    requests_per_second: float = 0.0
    errors: List[str] = None
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class StressTestRunner:
    """Runner for stress tests with monitoring and metrics collection."""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.metrics = StressTestMetrics()
        self.start_time = None
        self.response_times: List[float] = []
        
    async def run_concurrent_test(
        self,
        test_function: Callable,
        *args,
        **kwargs
    ) -> StressTestMetrics:
        """Run a test function with multiple concurrent users."""
        self.start_time = time.time()
        
        # Start system monitoring
        monitor_task = asyncio.create_task(self._monitor_system())
        
        # Create semaphore to limit concurrent connections
        semaphore = asyncio.Semaphore(self.config.concurrent_users)
        
        # Create tasks for all users
        tasks = []
        for user_id in range(self.config.concurrent_users):
            task = asyncio.create_task(
                self._run_user_session(
                    semaphore, test_function, user_id, *args, **kwargs
                )
            )
            tasks.append(task)
            
            # Ramp up delay
            if self.config.ramp_up_seconds > 0:
                delay = self.config.ramp_up_seconds / self.config.concurrent_users
                await asyncio.sleep(delay)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop monitoring
        monitor_task.cancel()
        
        # Calculate final metrics
        self._calculate_final_metrics()
        
        return self.metrics
    
    async def _run_user_session(
        self,
        semaphore: asyncio.Semaphore,
        test_function: Callable,
        user_id: int,
        *args,
        **kwargs
    ):
        """Run a single user session with multiple requests."""
        async with semaphore:
            for request_id in range(self.config.requests_per_user):
                try:
                    start_time = time.time()
                    await test_function(user_id, request_id, *args, **kwargs)
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    self.response_times.append(response_time)
                    self.metrics.successful_requests += 1
                    
                except Exception as e:
                    self.metrics.failed_requests += 1
                    self.metrics.errors.append(f"User {user_id}, Request {request_id}: {str(e)}")
                
                self.metrics.total_requests += 1
    
    async def _monitor_system(self):
        """Monitor system resources during the test."""
        max_memory = 0.0
        max_cpu = 0.0
        
        try:
            while True:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                max_memory = max(max_memory, memory_mb)
                max_cpu = max(max_cpu, cpu_percent)
                
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.metrics.memory_usage_mb = max_memory
            self.metrics.cpu_usage_percent = max_cpu
    
    def _calculate_final_metrics(self):
        """Calculate final metrics from collected data."""
        if self.response_times:
            self.metrics.average_response_time = sum(self.response_times) / len(self.response_times)
            self.metrics.min_response_time = min(self.response_times)
            self.metrics.max_response_time = max(self.response_times)
        
        if self.start_time:
            duration = time.time() - self.start_time
            self.metrics.requests_per_second = self.metrics.total_requests / duration if duration > 0 else 0
    
    def assert_performance_thresholds(self):
        """Assert that performance metrics meet the configured thresholds."""
        # Check error rate
        error_rate = (self.metrics.failed_requests / self.metrics.total_requests * 100) if self.metrics.total_requests > 0 else 0
        assert error_rate <= self.config.error_threshold_percent, f"Error rate {error_rate:.2f}% exceeds threshold {self.config.error_threshold_percent}%"
        
        # Check average response time
        assert self.metrics.average_response_time <= self.config.max_response_time_ms, f"Average response time {self.metrics.average_response_time:.2f}ms exceeds threshold {self.config.max_response_time_ms}ms"
        
        # Check memory usage
        assert self.metrics.memory_usage_mb <= self.config.memory_threshold_mb, f"Memory usage {self.metrics.memory_usage_mb:.2f}MB exceeds threshold {self.config.memory_threshold_mb}MB"
        
        # Check CPU usage
        assert self.metrics.cpu_usage_percent <= self.config.cpu_threshold_percent, f"CPU usage {self.metrics.cpu_usage_percent:.2f}% exceeds threshold {self.config.cpu_threshold_percent}%"


class DatabaseStressHelper:
    """Helper for database stress testing."""
    
    @staticmethod
    async def create_concurrent_sessions(count: int) -> List[AsyncSession]:
        """Create multiple database sessions for concurrent testing."""
        # This would need to be implemented based on your database session factory
        pass
    
    @staticmethod
    async def stress_test_queries(
        session: AsyncSession,
        query_functions: List[Callable],
        iterations: int = 100
    ):
        """Run multiple database queries concurrently."""
        tasks = []
        for _ in range(iterations):
            for query_func in query_functions:
                task = asyncio.create_task(query_func(session))
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful vs failed queries
        successful = sum(1 for result in results if not isinstance(result, Exception))
        failed = len(results) - successful
        
        return {
            'total': len(results),
            'successful': successful,
            'failed': failed,
            'errors': [str(r) for r in results if isinstance(r, Exception)]
        }


class WebSocketStressHelper:
    """Helper for WebSocket stress testing."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.connections: List[aiohttp.ClientWebSocketResponse] = []
    
    async def create_connections(self, count: int, endpoint: str = "/ws"):
        """Create multiple WebSocket connections."""
        session = aiohttp.ClientSession()
        
        for i in range(count):
            try:
                ws = await session.ws_connect(f"{self.base_url}{endpoint}")
                self.connections.append(ws)
            except Exception as e:
                print(f"Failed to create WebSocket connection {i}: {e}")
    
    async def send_messages_concurrently(self, message: dict, count: int = 100):
        """Send messages from all connections concurrently."""
        tasks = []
        
        for connection in self.connections:
            for _ in range(count):
                task = asyncio.create_task(connection.send_json(message))
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for result in results if not isinstance(result, Exception))
        failed = len(results) - successful
        
        return {
            'total': len(results),
            'successful': successful,
            'failed': failed,
            'connections': len(self.connections)
        }
    
    async def close_all_connections(self):
        """Close all WebSocket connections."""
        for connection in self.connections:
            try:
                await connection.close()
            except:
                pass
        self.connections.clear()


@pytest.fixture
def stress_config():
    """Default stress test configuration."""
    return StressTestConfig(
        concurrent_users=50,
        requests_per_user=5,
        test_duration_seconds=30,
        max_response_time_ms=2000,
        error_threshold_percent=10.0
    )


@pytest.fixture
def stress_runner(stress_config):
    """Stress test runner with default configuration."""
    return StressTestRunner(stress_config)


@pytest.fixture
def light_stress_config():
    """Light stress test configuration for CI/CD."""
    return StressTestConfig(
        concurrent_users=10,
        requests_per_user=3,
        test_duration_seconds=15,
        max_response_time_ms=3000,
        error_threshold_percent=15.0
    )


@pytest.fixture
def heavy_stress_config():
    """Heavy stress test configuration for performance testing."""
    return StressTestConfig(
        concurrent_users=200,
        requests_per_user=20,
        test_duration_seconds=120,
        max_response_time_ms=800,
        error_threshold_percent=2.0,
        memory_threshold_mb=1024,
        cpu_threshold_percent=70.0
    )
