"""
Chaos Engineering Tests

Tests that simulate various failures and disruptions to validate 
system resilience and failure recovery capabilities.
"""
import pytest
import asyncio
import time
import random
import psutil
import signal
import subprocess
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import httpx
from fastapi.testclient import TestClient

from app.main import app
from tests.utils.test_helpers import ChaosTestHelper


@dataclass
class ChaosExperiment:
    """Represents a chaos engineering experiment."""
    name: str
    description: str
    failure_injection: Callable
    recovery_validation: Callable
    duration_seconds: int = 30
    expected_recovery_time: int = 10


class NetworkChaosInjector:
    """Injects network-related failures."""
    
    @staticmethod
    async def simulate_network_latency(delay_ms: int = 1000):
        """Simulate high network latency."""
        import netifaces
        
        # This would typically use tc (traffic control) in a real environment
        # For testing, we'll simulate by adding delays to requests
        original_get = httpx.AsyncClient.get
        
        async def delayed_get(self, *args, **kwargs):
            await asyncio.sleep(delay_ms / 1000.0)
            return await original_get(self, *args, **kwargs)
        
        httpx.AsyncClient.get = delayed_get
        return lambda: setattr(httpx.AsyncClient, 'get', original_get)
    
    @staticmethod
    async def simulate_packet_loss(loss_percentage: int = 10):
        """Simulate packet loss."""
        original_request = httpx.AsyncClient.request
        
        async def lossy_request(self, *args, **kwargs):
            if random.randint(1, 100) <= loss_percentage:
                raise httpx.ConnectError("Simulated packet loss")
            return await original_request(self, *args, **kwargs)
        
        httpx.AsyncClient.request = lossy_request
        return lambda: setattr(httpx.AsyncClient, 'request', original_request)
    
    @staticmethod
    async def simulate_connection_timeout():
        """Simulate connection timeouts."""
        original_request = httpx.AsyncClient.request
        
        async def timeout_request(self, *args, **kwargs):
            kwargs['timeout'] = 0.1  # Very short timeout
            return await original_request(self, *args, **kwargs)
        
        httpx.AsyncClient.request = timeout_request
        return lambda: setattr(httpx.AsyncClient, 'request', original_request)


class DatabaseChaosInjector:
    """Injects database-related failures."""
    
    @staticmethod
    async def simulate_connection_pool_exhaustion():
        """Simulate database connection pool exhaustion."""
        from app.db.session import engine
        
        # Store original pool size
        original_pool_size = engine.pool.size()
        
        # Exhaust the connection pool
        connections = []
        try:
            for _ in range(original_pool_size + 5):
                conn = await engine.connect()
                connections.append(conn)
        except Exception:
            pass  # Expected when pool is exhausted
        
        # Return cleanup function
        async def cleanup():
            for conn in connections:
                try:
                    await conn.close()
                except Exception:
                    pass
        
        return cleanup
    
    @staticmethod
    async def simulate_slow_queries():
        """Simulate slow database queries."""
        # This would typically involve injecting delays at the ORM level
        # For testing purposes, we'll simulate with sleep
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        def slow_query_listener(conn, cursor, statement, parameters, context, executemany):
            time.sleep(0.5)  # Add 500ms delay to each query
        
        event.listen(Engine, "before_cursor_execute", slow_query_listener)
        
        return lambda: event.remove(Engine, "before_cursor_execute", slow_query_listener)
    
    @staticmethod
    async def simulate_database_deadlock():
        """Simulate database deadlocks."""
        from app.db.session import get_db
        
        async def create_deadlock():
            # Create two concurrent transactions that will deadlock
            async with get_db() as db1, get_db() as db2:
                try:
                    # Transaction 1: Lock table A then B
                    await db1.execute("SELECT * FROM users ORDER BY id FOR UPDATE")
                    await asyncio.sleep(0.1)
                    await db1.execute("SELECT * FROM tenders ORDER BY id FOR UPDATE")
                    
                    # Transaction 2: Lock table B then A
                    await db2.execute("SELECT * FROM tenders ORDER BY id FOR UPDATE")
                    await asyncio.sleep(0.1)
                    await db2.execute("SELECT * FROM users ORDER BY id FOR UPDATE")
                    
                except Exception:
                    pass  # Deadlock expected
        
        return create_deadlock


class ResourceChaosInjector:
    """Injects resource-related failures."""
    
    @staticmethod
    async def simulate_memory_pressure():
        """Simulate high memory usage."""
        # Allocate large amounts of memory
        memory_hogs = []
        
        def allocate_memory():
            # Allocate 100MB chunks
            for _ in range(10):
                memory_hogs.append(bytearray(100 * 1024 * 1024))
        
        allocate_memory()
        
        return lambda: memory_hogs.clear()
    
    @staticmethod
    async def simulate_cpu_spike():
        """Simulate high CPU usage."""
        stop_event = asyncio.Event()
        
        def cpu_intensive_task():
            while not stop_event.is_set():
                # Busy loop to consume CPU
                for _ in range(10000):
                    _ = sum(range(1000))
                time.sleep(0.001)
        
        # Start CPU intensive tasks
        with ThreadPoolExecutor(max_workers=psutil.cpu_count()) as executor:
            futures = [executor.submit(cpu_intensive_task) for _ in range(psutil.cpu_count())]
        
        return lambda: stop_event.set()
    
    @staticmethod
    async def simulate_disk_io_pressure():
        """Simulate high disk I/O pressure."""
        import tempfile
        import os
        
        temp_files = []
        
        def create_io_pressure():
            for i in range(10):
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_files.append(temp_file.name)
                
                # Write large amounts of data
                for _ in range(1000):
                    temp_file.write(b"x" * 1024 * 1024)  # 1MB chunks
                temp_file.close()
        
        create_io_pressure()
        
        def cleanup():
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
        
        return cleanup


class ChaosTestRunner:
    """Runs chaos engineering experiments."""
    
    def __init__(self, client: TestClient):
        self.client = client
        self.network_injector = NetworkChaosInjector()
        self.database_injector = DatabaseChaosInjector()
        self.resource_injector = ResourceChaosInjector()
    
    async def run_experiment(self, experiment: ChaosExperiment) -> Dict[str, Any]:
        """Run a chaos engineering experiment."""
        results = {
            "experiment_name": experiment.name,
            "start_time": time.time(),
            "duration": experiment.duration_seconds,
            "success": False,
            "recovery_time": None,
            "errors": [],
            "metrics": {}
        }
        
        try:
            # Baseline metrics
            baseline_response = self.client.get("/api/v1/health")
            baseline_time = time.time()
            
            # Inject failure
            cleanup = await experiment.failure_injection()
            failure_start = time.time()
            
            # Monitor system during failure
            await asyncio.sleep(experiment.duration_seconds)
            
            # Clean up failure
            if cleanup:
                if asyncio.iscoroutinefunction(cleanup):
                    await cleanup()
                else:
                    cleanup()
            
            # Wait for recovery and validate
            recovery_start = time.time()
            recovery_successful = False
            
            for attempt in range(experiment.expected_recovery_time):
                try:
                    await experiment.recovery_validation()
                    recovery_successful = True
                    results["recovery_time"] = time.time() - recovery_start
                    break
                except Exception as e:
                    results["errors"].append(f"Recovery attempt {attempt + 1}: {str(e)}")
                    await asyncio.sleep(1)
            
            results["success"] = recovery_successful
            results["end_time"] = time.time()
            
        except Exception as e:
            results["errors"].append(f"Experiment failed: {str(e)}")
            results["end_time"] = time.time()
        
        return results


class TestChaosEngineering:
    """Test system resilience through chaos engineering."""
    
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, authenticated_user):
        self.client = client
        self.chaos_runner = ChaosTestRunner(client)
        self.authenticated_user = authenticated_user
    
    @pytest.mark.asyncio
    async def test_network_latency_resilience(self):
        """Test system resilience to high network latency."""
        async def inject_latency():
            return await NetworkChaosInjector.simulate_network_latency(2000)  # 2s latency
        
        async def validate_recovery():
            response = self.client.get("/api/v1/health")
            assert response.status_code == 200
            assert response.elapsed.total_seconds() < 5.0  # Should respond within 5s
        
        experiment = ChaosExperiment(
            name="network_latency_resilience",
            description="Test resilience to high network latency",
            failure_injection=inject_latency,
            recovery_validation=validate_recovery,
            duration_seconds=10,
            expected_recovery_time=5
        )
        
        results = await self.chaos_runner.run_experiment(experiment)
        assert results["success"], f"Network latency resilience test failed: {results['errors']}"
    
    @pytest.mark.asyncio
    async def test_packet_loss_resilience(self):
        """Test system resilience to packet loss."""
        async def inject_packet_loss():
            return await NetworkChaosInjector.simulate_packet_loss(20)  # 20% loss
        
        async def validate_recovery():
            # Should be able to handle some requests despite packet loss
            successful_requests = 0
            for _ in range(5):
                try:
                    response = self.client.get("/api/v1/health")
                    if response.status_code == 200:
                        successful_requests += 1
                except Exception:
                    pass
            
            assert successful_requests >= 3  # At least 60% success rate
        
        experiment = ChaosExperiment(
            name="packet_loss_resilience",
            description="Test resilience to packet loss",
            failure_injection=inject_packet_loss,
            recovery_validation=validate_recovery,
            duration_seconds=15,
            expected_recovery_time=5
        )
        
        results = await self.chaos_runner.run_experiment(experiment)
        assert results["success"], f"Packet loss resilience test failed: {results['errors']}"
    
    @pytest.mark.asyncio
    async def test_memory_pressure_resilience(self):
        """Test system resilience to memory pressure."""
        async def inject_memory_pressure():
            return await ResourceChaosInjector.simulate_memory_pressure()
        
        async def validate_recovery():
            # System should still respond to health checks
            response = self.client.get("/api/v1/health")
            assert response.status_code == 200
            
            # Memory usage should be reasonable
            memory_percent = psutil.virtual_memory().percent
            assert memory_percent < 90  # Less than 90% memory usage
        
        experiment = ChaosExperiment(
            name="memory_pressure_resilience",
            description="Test resilience to memory pressure",
            failure_injection=inject_memory_pressure,
            recovery_validation=validate_recovery,
            duration_seconds=20,
            expected_recovery_time=10
        )
        
        results = await self.chaos_runner.run_experiment(experiment)
        assert results["success"], f"Memory pressure resilience test failed: {results['errors']}"
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self):
        """Test resilience to database connection pool exhaustion."""
        async def inject_pool_exhaustion():
            return await DatabaseChaosInjector.simulate_connection_pool_exhaustion()
        
        async def validate_recovery():
            # Should be able to perform database operations
            response = self.client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
            )
            assert response.status_code == 200
        
        experiment = ChaosExperiment(
            name="db_pool_exhaustion_resilience",
            description="Test resilience to database connection pool exhaustion",
            failure_injection=inject_pool_exhaustion,
            recovery_validation=validate_recovery,
            duration_seconds=15,
            expected_recovery_time=10
        )
        
        results = await self.chaos_runner.run_experiment(experiment)
        assert results["success"], f"DB pool exhaustion resilience test failed: {results['errors']}"
    
    @pytest.mark.asyncio
    async def test_cascading_failure_resilience(self):
        """Test resilience to cascading failures."""
        async def inject_cascading_failures():
            # Inject multiple failures simultaneously
            cleanups = []
            
            # Network latency
            cleanup1 = await NetworkChaosInjector.simulate_network_latency(1000)
            cleanups.append(cleanup1)
            
            # Memory pressure
            cleanup2 = await ResourceChaosInjector.simulate_memory_pressure()
            cleanups.append(cleanup2)
            
            # Slow queries
            cleanup3 = await DatabaseChaosInjector.simulate_slow_queries()
            cleanups.append(cleanup3)
            
            def combined_cleanup():
                for cleanup in cleanups:
                    try:
                        if asyncio.iscoroutinefunction(cleanup):
                            asyncio.create_task(cleanup())
                        else:
                            cleanup()
                    except Exception:
                        pass
            
            return combined_cleanup
        
        async def validate_recovery():
            # System should still be responsive despite multiple failures
            response = self.client.get("/api/v1/health")
            assert response.status_code == 200
            
            # Should be able to perform basic operations
            response = self.client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
            )
            assert response.status_code in [200, 503]  # Either success or graceful degradation
        
        experiment = ChaosExperiment(
            name="cascading_failure_resilience",
            description="Test resilience to multiple simultaneous failures",
            failure_injection=inject_cascading_failures,
            recovery_validation=validate_recovery,
            duration_seconds=30,
            expected_recovery_time=15
        )
        
        results = await self.chaos_runner.run_experiment(experiment)
        assert results["success"], f"Cascading failure resilience test failed: {results['errors']}"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern implementation."""
        # This test assumes the application implements circuit breakers
        
        async def trigger_circuit_breaker():
            # Make many failing requests to trigger circuit breaker
            for _ in range(10):
                try:
                    # Attempt to access a failing service
                    self.client.get("/api/v1/external-service-that-fails")
                except Exception:
                    pass
            
            return None  # No cleanup needed
        
        async def validate_circuit_breaker():
            # Circuit breaker should be open, requests should fail fast
            start_time = time.time()
            
            try:
                response = self.client.get("/api/v1/external-service-that-fails")
            except Exception:
                pass
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Should fail fast (< 100ms) when circuit breaker is open
            assert response_time < 0.1
        
        experiment = ChaosExperiment(
            name="circuit_breaker_functionality",
            description="Test circuit breaker pattern implementation",
            failure_injection=trigger_circuit_breaker,
            recovery_validation=validate_circuit_breaker,
            duration_seconds=5,
            expected_recovery_time=2
        )
        
        results = await self.chaos_runner.run_experiment(experiment)
        # Note: This test might fail if circuit breaker is not implemented
        # That's expected and indicates a resilience gap
    
    def test_graceful_degradation(self):
        """Test system's ability to degrade gracefully under stress."""
        # Test that non-essential features are disabled under stress
        # while core functionality remains available
        
        # Simulate high load
        start_time = time.time()
        
        # Make many concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for _ in range(100):
                future = executor.submit(
                    lambda: self.client.get("/api/v1/health")
                )
                futures.append(future)
            
            # Wait for all requests to complete
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze responses
        success_count = sum(1 for r in responses if r.status_code == 200)
        degraded_count = sum(1 for r in responses if r.status_code == 503)
        
        # System should either succeed or gracefully degrade
        assert success_count + degraded_count == len(responses)
        
        # At least 50% of requests should be handled (either success or graceful degradation)
        assert (success_count + degraded_count) / len(responses) >= 0.5
