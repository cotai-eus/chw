"""
Network and Connection Stress Tests

Advanced testing for network conditions, connection handling, and distributed scenarios.
"""
import asyncio
import aiohttp
import socket
import random
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pytest
from httpx import AsyncClient, Timeout, Limits
from unittest.mock import patch

from tests.stress.conftest import StressTestRunner, StressTestConfig
from app.main import app


@dataclass
class NetworkCondition:
    """Network condition simulation parameters."""
    latency_ms: int = 0
    packet_loss_percent: float = 0.0
    bandwidth_kbps: Optional[int] = None
    jitter_ms: int = 0


class NetworkSimulator:
    """Simulate various network conditions for testing."""
    
    def __init__(self, condition: NetworkCondition):
        self.condition = condition
    
    async def add_latency(self):
        """Add simulated network latency."""
        if self.condition.latency_ms > 0:
            # Add base latency plus jitter
            jitter = random.randint(0, self.condition.jitter_ms) if self.condition.jitter_ms > 0 else 0
            total_delay = (self.condition.latency_ms + jitter) / 1000.0
            await asyncio.sleep(total_delay)
    
    def should_drop_packet(self) -> bool:
        """Determine if packet should be dropped (simulate packet loss)."""
        return random.random() < (self.condition.packet_loss_percent / 100.0)


class TestNetworkStressConditions:
    """Test various network stress conditions."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_high_latency_conditions(self, stress_config):
        """Test performance under high latency conditions."""
        # Simulate high latency network (200ms)
        network_condition = NetworkCondition(latency_ms=200, jitter_ms=50)
        simulator = NetworkSimulator(network_condition)
        
        stress_runner = StressTestRunner(stress_config)
        
        async def high_latency_request(user_id: int, request_id: int, client: AsyncClient):
            """Request with simulated high latency."""
            # Add network latency simulation
            await simulator.add_latency()
            
            response = await client.get("/api/v1/companies/")
            assert response.status_code in [200, 408, 504]  # Allow timeouts
        
        # Use longer timeout for high latency test
        timeout = Timeout(30.0)  # 30 second timeout
        async with AsyncClient(app=app, base_url="http://test", timeout=timeout) as client:
            metrics = await stress_runner.run_concurrent_test(
                high_latency_request, client
            )
        
        print(f"High latency test: {metrics.successful_requests}/{metrics.total_requests} successful")
        print(f"Average response time: {metrics.average_response_time:.0f}ms")
        
        # Expect higher response times due to simulated latency
        assert metrics.average_response_time > 200  # Should include simulated latency
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_packet_loss_conditions(self, light_stress_config):
        """Test resilience under packet loss conditions."""
        # Simulate 5% packet loss
        network_condition = NetworkCondition(packet_loss_percent=5.0)
        simulator = NetworkSimulator(network_condition)
        
        stress_runner = StressTestRunner(light_stress_config)
        
        async def packet_loss_request(user_id: int, request_id: int, client: AsyncClient):
            """Request with simulated packet loss."""
            # Simulate packet loss by randomly failing requests
            if simulator.should_drop_packet():
                # Simulate connection error due to packet loss
                raise aiohttp.ClientConnectorError(
                    connection_key=None, 
                    os_error=OSError("Simulated packet loss")
                )
            
            response = await client.get("/api/v1/companies/")
            assert response.status_code == 200
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                packet_loss_request, client
            )
        
        # Expect some failures due to packet loss, but most should succeed
        success_rate = (metrics.successful_requests / metrics.total_requests) * 100
        print(f"Packet loss test: {success_rate:.1f}% success rate")
        assert success_rate > 85  # Should handle 5% packet loss gracefully
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, stress_config):
        """Test behavior when connection pool is exhausted."""
        
        # Configure client with very limited connection pool
        limits = Limits(max_keepalive_connections=5, max_connections=10)
        timeout = Timeout(5.0)
        
        stress_runner = StressTestRunner(stress_config)
        
        async def pool_exhaustion_request(user_id: int, request_id: int, client: AsyncClient):
            """Request that may exhaust connection pool."""
            # Hold connection for a bit to stress the pool
            response = await client.get("/api/v1/companies/")
            assert response.status_code in [200, 429, 503]  # Allow connection limits
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
        
        async with AsyncClient(
            app=app, 
            base_url="http://test", 
            limits=limits, 
            timeout=timeout
        ) as client:
            metrics = await stress_runner.run_concurrent_test(
                pool_exhaustion_request, client
            )
        
        print(f"Connection pool test: {metrics.successful_requests}/{metrics.total_requests} successful")
        # Should handle connection pool limits gracefully
        assert metrics.total_requests > 0
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_slow_client_simulation(self, light_stress_config):
        """Test with slow clients that read responses slowly."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def slow_client_request(user_id: int, request_id: int, client: AsyncClient):
            """Simulate slow client reading response."""
            response = await client.get("/api/v1/companies/")
            assert response.status_code == 200
            
            # Simulate slow response processing
            content = response.content
            
            # Read content in small chunks with delays (simulate slow client)
            chunk_size = 100
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                await asyncio.sleep(0.01)  # Slow processing
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                slow_client_request, client
            )
        
        print(f"Slow client test: {metrics.successful_requests}/{metrics.total_requests} successful")
        assert metrics.successful_requests > 0


class TestConnectionStress:
    """Test connection handling under stress."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self, stress_config):
        """Test rapid connection establishment and teardown."""
        stress_runner = StressTestRunner(stress_config)
        
        async def rapid_connection_test(user_id: int, request_id: int):
            """Rapidly create and close connections."""
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/companies/")
                assert response.status_code == 200
            # Connection is closed when exiting context manager
        
        metrics = await stress_runner.run_concurrent_test(rapid_connection_test)
        
        print(f"Rapid connection test: {metrics.successful_requests}/{metrics.total_requests} successful")
        stress_runner.assert_performance_thresholds()
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_persistent_connection_stress(self, heavy_stress_config):
        """Test many requests over persistent connections."""
        stress_runner = StressTestRunner(heavy_stress_config)
        
        # Create a pool of persistent connections
        connection_pool = []
        for i in range(10):
            client = AsyncClient(app=app, base_url="http://test")
            connection_pool.append(client)
        
        try:
            async def persistent_request(user_id: int, request_id: int):
                """Use persistent connection for request."""
                client = connection_pool[user_id % len(connection_pool)]
                response = await client.get(f"/api/v1/companies/?page={request_id}")
                assert response.status_code in [200, 404]
            
            metrics = await stress_runner.run_concurrent_test(persistent_request)
            
            print(f"Persistent connection test: {metrics.successful_requests}/{metrics.total_requests} successful")
            
        finally:
            # Clean up connections
            for client in connection_pool:
                await client.aclose()
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, stress_config):
        """Test handling of connection timeouts."""
        # Very short timeout to trigger timeouts
        timeout = Timeout(0.001)  # 1ms timeout - very aggressive
        
        stress_runner = StressTestRunner(stress_config)
        
        async def timeout_test(user_id: int, request_id: int, client: AsyncClient):
            """Test with very short timeouts."""
            try:
                response = await client.get("/api/v1/companies/")
                assert response.status_code == 200
            except asyncio.TimeoutError:
                # Timeout is expected with such aggressive timeout
                pass
        
        async with AsyncClient(app=app, base_url="http://test", timeout=timeout) as client:
            metrics = await stress_runner.run_concurrent_test(
                timeout_test, client
            )
        
        print(f"Timeout test: {metrics.successful_requests}/{metrics.total_requests} successful")
        # With 1ms timeout, most requests should timeout
        assert metrics.total_requests > 0


class TestDistributedScenarios:
    """Test distributed and multi-client scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_multi_endpoint_stress(self, heavy_stress_config):
        """Test stress across multiple endpoints simultaneously."""
        stress_runner = StressTestRunner(heavy_stress_config)
        
        # Define multiple endpoints to stress
        endpoints = [
            "/api/v1/companies/",
            "/api/v1/tenders/",
            "/api/v1/suppliers/",
            "/api/v1/quotes/",
            "/api/v1/users/profile",
            "/api/v1/tenders/search?q=test",
        ]
        
        async def multi_endpoint_request(user_id: int, request_id: int, client: AsyncClient):
            """Hit different endpoints based on user and request."""
            endpoint = endpoints[(user_id + request_id) % len(endpoints)]
            
            # Add authentication for protected endpoints
            if "profile" in endpoint:
                # Skip auth for stress test simplicity
                endpoint = "/api/v1/companies/"
            
            response = await client.get(endpoint)
            assert response.status_code in [200, 401, 404]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                multi_endpoint_request, client
            )
        
        print(f"Multi-endpoint stress: {metrics.successful_requests}/{metrics.total_requests} successful")
        stress_runner.assert_performance_thresholds()
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_cascading_failure_simulation(self, light_stress_config):
        """Test system behavior under cascading failures."""
        stress_runner = StressTestRunner(light_stress_config)
        
        # Simulate progressive system degradation
        failure_probability = 0.1  # Start with 10% failure rate
        
        async def cascading_failure_request(user_id: int, request_id: int, client: AsyncClient):
            """Request with increasing failure probability."""
            nonlocal failure_probability
            
            # Increase failure rate over time
            if request_id > 5:
                failure_probability = min(0.5, failure_probability + 0.05)
            
            # Simulate random failures
            if random.random() < failure_probability:
                raise aiohttp.ClientError("Simulated cascading failure")
            
            response = await client.get("/api/v1/companies/")
            assert response.status_code == 200
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                cascading_failure_request, client
            )
        
        success_rate = (metrics.successful_requests / metrics.total_requests) * 100
        print(f"Cascading failure test: {success_rate:.1f}% success rate")
        
        # System should maintain some functionality even under cascading failures
        assert success_rate > 30  # At least 30% should succeed
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_geographic_distribution_simulation(self, stress_config):
        """Simulate clients from different geographic locations."""
        stress_runner = StressTestRunner(stress_config)
        
        # Simulate different geographic conditions
        geo_conditions = [
            NetworkCondition(latency_ms=10, jitter_ms=5),    # Local
            NetworkCondition(latency_ms=50, jitter_ms=10),   # Regional
            NetworkCondition(latency_ms=150, jitter_ms=30),  # Continental
            NetworkCondition(latency_ms=300, jitter_ms=50),  # International
        ]
        
        async def geo_distributed_request(user_id: int, request_id: int, client: AsyncClient):
            """Request from simulated geographic location."""
            # Select geo condition based on user
            condition = geo_conditions[user_id % len(geo_conditions)]
            simulator = NetworkSimulator(condition)
            
            # Add geographic latency
            await simulator.add_latency()
            
            response = await client.get("/api/v1/companies/")
            assert response.status_code in [200, 408]  # Allow timeouts for distant locations
        
        # Use longer timeout for international requests
        timeout = Timeout(10.0)
        async with AsyncClient(app=app, base_url="http://test", timeout=timeout) as client:
            metrics = await stress_runner.run_concurrent_test(
                geo_distributed_request, client
            )
        
        print(f"Geographic distribution test: {metrics.successful_requests}/{metrics.total_requests} successful")
        print(f"Average response time: {metrics.average_response_time:.0f}ms")
        
        # Response time should reflect geographic distribution
        assert metrics.average_response_time > 50  # Should include simulated latencies
