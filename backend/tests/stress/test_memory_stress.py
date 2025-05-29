"""
Memory and Resource Usage Stress Tests

Tests for memory leaks, resource exhaustion, and system resource management.
"""
import asyncio
import gc
import psutil
import pytest
import time
from typing import List, Dict
import tracemalloc

from tests.stress.conftest import StressTestRunner
from httpx import AsyncClient
from app.main import app


class TestMemoryUsageStress:
    """Stress tests for memory usage and leak detection."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, stress_runner: StressTestRunner):
        """Test for memory leaks during extended operation."""
        
        # Start memory tracing
        tracemalloc.start()
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_snapshots = []
        
        async def memory_intensive_operation(user_id: int, request_id: int, client: AsyncClient):
            """Perform memory-intensive operations."""
            try:
                # Make multiple API calls that create objects
                responses = []
                
                # Create and process data
                for i in range(5):
                    response = await client.get("/api/v1/companies/")
                    responses.append(response)
                    
                    # Process response data
                    if response.status_code == 200:
                        data = response.json()
                        # Simulate data processing
                        processed_data = [item for item in data if isinstance(item, dict)]
                
                # Take memory snapshot
                current, peak = tracemalloc.get_traced_memory()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_snapshots.append({
                    'user_id': user_id,
                    'request_id': request_id,
                    'traced_memory_mb': current / 1024 / 1024,
                    'process_memory_mb': current_memory
                })
                
                # Force garbage collection
                if request_id % 10 == 0:
                    gc.collect()
                
            except Exception as e:
                print(f"Memory operation error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                memory_intensive_operation, client
            )
        
        # Analyze memory usage
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        tracemalloc.stop()
        
        # Check for excessive memory growth
        max_acceptable_growth = 200  # MB
        assert memory_growth < max_acceptable_growth, f"Memory growth {memory_growth:.2f}MB exceeds threshold {max_acceptable_growth}MB"
        
        print(f"Memory test: Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB, Growth: {memory_growth:.2f}MB")
        print(f"Memory snapshots: {len(memory_snapshots)} recorded")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_garbage_collection_stress(self, light_stress_config):
        """Test garbage collection under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        gc_stats_before = gc.get_stats()
        
        async def gc_stress_operation(user_id: int, request_id: int):
            """Operations that create garbage for collection."""
            try:
                # Create objects that should be garbage collected
                large_list = [f"item_{i}_{user_id}_{request_id}" for i in range(1000)]
                large_dict = {f"key_{i}": f"value_{i}_{user_id}" for i in range(500)}
                
                # Create circular references
                class Node:
                    def __init__(self, value):
                        self.value = value
                        self.children = []
                        self.parent = None
                
                root = Node(f"root_{user_id}_{request_id}")
                for i in range(10):
                    child = Node(f"child_{i}")
                    child.parent = root
                    root.children.append(child)
                
                # Simulate processing
                processed = [item.upper() for item in large_list[:100]]
                
                # Force garbage collection periodically
                if request_id % 5 == 0:
                    collected = gc.collect()
                
            except Exception as e:
                print(f"GC stress error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(gc_stress_operation)
        
        # Force final garbage collection
        final_collected = gc.collect()
        gc_stats_after = gc.get_stats()
        
        print(f"GC stress test: {metrics.successful_requests}/{metrics.total_requests} successful")
        print(f"Final GC collected: {final_collected} objects")


class TestResourceExhaustionStress:
    """Stress tests for resource exhaustion scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_file_descriptor_stress(self, light_stress_config):
        """Test file descriptor usage under stress."""
        stress_runner = StressTestRunner(light_stress_config)
        
        opened_files = []
        
        async def file_descriptor_test(user_id: int, request_id: int):
            """Test file descriptor usage."""
            try:
                import tempfile
                
                # Create temporary files
                for i in range(3):
                    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
                    temp_file.write(f"Test data for user {user_id}, request {request_id}, file {i}")
                    temp_file.close()
                    opened_files.append(temp_file.name)
                
                # Open and read files
                for file_path in opened_files[-3:]:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        assert "Test data" in content
                
            except Exception as e:
                print(f"File descriptor test error: {e}")
                raise e
            finally:
                # Cleanup
                import os
                for file_path in opened_files[-3:]:
                    try:
                        os.unlink(file_path)
                    except:
                        pass
        
        try:
            metrics = await stress_runner.run_concurrent_test(file_descriptor_test)
            print(f"File descriptor stress: {metrics.successful_requests}/{metrics.total_requests} successful")
            
        finally:
            # Cleanup remaining files
            import os
            for file_path in opened_files:
                try:
                    os.unlink(file_path)
                except:
                    pass
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_thread_pool_exhaustion(self, light_stress_config):
        """Test thread pool exhaustion scenarios."""
        stress_runner = StressTestRunner(light_stress_config)
        
        async def thread_pool_test(user_id: int, request_id: int):
            """Test thread pool usage."""
            try:
                import concurrent.futures
                import threading
                
                def cpu_bound_task(n):
                    """CPU-bound task for thread testing."""
                    result = 0
                    for i in range(n):
                        result += i * i
                    return result
                
                # Use thread pool for CPU-bound tasks
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    futures = []
                    
                    for i in range(5):
                        future = executor.submit(cpu_bound_task, 1000 + (request_id * 100))
                        futures.append(future)
                    
                    # Wait for completion with timeout
                    for future in concurrent.futures.as_completed(futures, timeout=5):
                        result = future.result()
                        assert result > 0
                
            except Exception as e:
                print(f"Thread pool test error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(thread_pool_test)
        print(f"Thread pool stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestCPUUsageStress:
    """Stress tests for CPU usage patterns."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_cpu_intensive_operations(self, stress_runner: StressTestRunner):
        """Test CPU-intensive operations under stress."""
        
        process = psutil.Process()
        cpu_measurements = []
        
        async def cpu_intensive_operation(user_id: int, request_id: int):
            """Perform CPU-intensive operations."""
            try:
                start_time = time.time()
                start_cpu = process.cpu_percent()
                
                # CPU-intensive calculation
                result = 0
                iterations = 50000 + (request_id * 1000)
                
                for i in range(iterations):
                    result += i ** 2
                    if i % 10000 == 0:
                        # Yield control periodically
                        await asyncio.sleep(0.001)
                
                end_time = time.time()
                end_cpu = process.cpu_percent()
                
                cpu_measurements.append({
                    'user_id': user_id,
                    'request_id': request_id,
                    'duration': end_time - start_time,
                    'cpu_percent': end_cpu,
                    'iterations': iterations,
                    'result': result
                })
                
                assert result > 0
                
            except Exception as e:
                print(f"CPU intensive operation error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(cpu_intensive_operation)
        
        # Analyze CPU usage
        if cpu_measurements:
            avg_cpu = sum(m['cpu_percent'] for m in cpu_measurements) / len(cpu_measurements)
            max_cpu = max(m['cpu_percent'] for m in cpu_measurements)
            avg_duration = sum(m['duration'] for m in cpu_measurements) / len(cpu_measurements)
            
            print(f"CPU stress test: Avg CPU: {avg_cpu:.2f}%, Max CPU: {max_cpu:.2f}%, Avg Duration: {avg_duration:.3f}s")
        
        stress_runner.assert_performance_thresholds()
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_mixed_workload_stress(self, stress_runner: StressTestRunner):
        """Test mixed CPU and I/O workload under stress."""
        
        async def mixed_workload_operation(user_id: int, request_id: int, client: AsyncClient):
            """Perform mixed CPU and I/O operations."""
            try:
                # I/O operation - API call
                response = await client.get(f"/api/v1/companies/?page={request_id % 5 + 1}")
                
                # CPU operation - data processing
                if response.status_code == 200:
                    data = response.json()
                    
                    # CPU-intensive processing
                    processed_items = []
                    for i, item in enumerate(data if isinstance(data, list) else []):
                        # Simulate complex processing
                        for j in range(100):
                            calculated = (i * j) ** 0.5
                        processed_items.append(calculated)
                
                # Another I/O operation
                response2 = await client.get("/api/v1/suppliers/")
                
                assert response.status_code in [200, 401, 403]
                
            except Exception as e:
                print(f"Mixed workload error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                mixed_workload_operation, client
            )
        
        stress_runner.assert_performance_thresholds()
        print(f"Mixed workload stress: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestSystemResourceMonitoring:
    """Stress tests with comprehensive system resource monitoring."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_comprehensive_resource_monitoring(self, stress_runner: StressTestRunner):
        """Test with comprehensive resource monitoring."""
        
        process = psutil.Process()
        resource_snapshots = []
        
        async def monitored_operation(user_id: int, request_id: int, client: AsyncClient):
            """Operation with resource monitoring."""
            try:
                start_time = time.time()
                
                # Take resource snapshot before operation
                memory_before = process.memory_info().rss / 1024 / 1024
                cpu_before = process.cpu_percent()
                
                # Perform operation
                response = await client.get("/api/v1/tenders/")
                
                if response.status_code == 200:
                    data = response.json()
                    # Process data
                    processed = [str(item) for item in data if item]
                
                # Simulate additional work
                for i in range(1000):
                    temp_data = {"key": f"value_{i}_{user_id}_{request_id}"}
                
                end_time = time.time()
                
                # Take resource snapshot after operation
                memory_after = process.memory_info().rss / 1024 / 1024
                cpu_after = process.cpu_percent()
                
                resource_snapshots.append({
                    'user_id': user_id,
                    'request_id': request_id,
                    'duration': end_time - start_time,
                    'memory_before': memory_before,
                    'memory_after': memory_after,
                    'memory_delta': memory_after - memory_before,
                    'cpu_before': cpu_before,
                    'cpu_after': cpu_after,
                    'response_status': response.status_code
                })
                
            except Exception as e:
                print(f"Monitored operation error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                monitored_operation, client
            )
        
        # Analyze resource usage patterns
        if resource_snapshots:
            total_memory_delta = sum(s['memory_delta'] for s in resource_snapshots)
            avg_duration = sum(s['duration'] for s in resource_snapshots) / len(resource_snapshots)
            max_memory_delta = max(s['memory_delta'] for s in resource_snapshots)
            
            print(f"Resource monitoring results:")
            print(f"  Total memory delta: {total_memory_delta:.2f}MB")
            print(f"  Max memory delta per operation: {max_memory_delta:.2f}MB")
            print(f"  Average operation duration: {avg_duration:.3f}s")
            print(f"  Resource snapshots collected: {len(resource_snapshots)}")
        
        stress_runner.assert_performance_thresholds()
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_resource_cleanup_verification(self, light_stress_config):
        """Test that resources are properly cleaned up after operations."""
        stress_runner = StressTestRunner(light_stress_config)
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        initial_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        async def resource_cleanup_test(user_id: int, request_id: int):
            """Test resource cleanup."""
            try:
                import tempfile
                temp_files = []
                
                # Create temporary resources
                for i in range(3):
                    temp_file = tempfile.NamedTemporaryFile(delete=False)
                    temp_file.write(b"temporary data for cleanup test")
                    temp_file.close()
                    temp_files.append(temp_file.name)
                
                # Create in-memory data structures
                large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}
                
                # Process data
                processed = {k: v.upper() for k, v in large_data.items() if len(v) > 50}
                
                # Cleanup temporary files
                import os
                for temp_file in temp_files:
                    os.unlink(temp_file)
                
                # Clear references
                del large_data
                del processed
                
            except Exception as e:
                print(f"Resource cleanup test error: {e}")
                raise e
        
        metrics = await stress_runner.run_concurrent_test(resource_cleanup_test)
        
        # Force garbage collection
        gc.collect()
        
        # Check resource cleanup
        final_memory = process.memory_info().rss / 1024 / 1024
        final_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        memory_growth = final_memory - initial_memory
        fd_growth = final_fds - initial_fds
        
        print(f"Resource cleanup verification:")
        print(f"  Memory growth: {memory_growth:.2f}MB")
        print(f"  File descriptor growth: {fd_growth}")
        print(f"  Operations completed: {metrics.successful_requests}/{metrics.total_requests}")
        
        # Assert reasonable resource usage
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.2f}MB"
        assert abs(fd_growth) < 10, f"File descriptor leak detected: {fd_growth}"
