"""
Load Balancing and Scalability Stress Tests

Tests for application behavior under load balancing scenarios and scalability limits.
"""
import asyncio
import pytest
from httpx import AsyncClient
import time
from typing import List, Dict
import random

from tests.stress.conftest import StressTestRunner
from app.main import app


class TestLoadBalancingStress:
    """Stress tests for load balancing scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_session_affinity_stress(self, stress_runner: StressTestRunner):
        """Test session affinity under load balancing."""
        
        user_sessions = {}
        
        async def session_affinity_test(user_id: int, request_id: int, client: AsyncClient):
            """Test session consistency across requests."""
            try:
                # First request - login to establish session
                if user_id not in user_sessions:
                    login_response = await client.post(
                        "/api/v1/auth/login",
                        data={
                            "username": f"testuser{user_id}@example.com",
                            "password": "testpassword123"
                        }
                    )
                    
                    if login_response.status_code == 200:
                        token_data = login_response.json()
                        user_sessions[user_id] = {
                            "token": token_data.get("access_token"),
                            "session_id": token_data.get("session_id")
                        }
                
                # Subsequent requests using session
                if user_id in user_sessions and user_sessions[user_id]["token"]:
                    headers = {
                        "Authorization": f"Bearer {user_sessions[user_id]['token']}",
                        "X-Session-ID": user_sessions[user_id].get("session_id", "")
                    }
                    
                    # Make authenticated requests
                    endpoints = [
                        "/api/v1/users/profile",
                        "/api/v1/companies/",
                        "/api/v1/tenders/",
                        "/api/v1/suppliers/"
                    ]
                    
                    endpoint = endpoints[request_id % len(endpoints)]
                    response = await client.get(endpoint, headers=headers)
                    
                    # Check for consistent session behavior
                    assert response.status_code in [200, 401, 403, 404]
                    
                    # Verify session headers in response
                    if "X-Session-ID" in response.headers:
                        response_session = response.headers["X-Session-ID"]
                        if user_sessions[user_id].get("session_id"):
                            assert response_session == user_sessions[user_id]["session_id"]
                
            except Exception as e:
                print(f"Session affinity test error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                session_affinity_test, client
            )
        
        print(f"Session affinity stress: {metrics.successful_requests}/{metrics.total_requests} successful")
        print(f"Active user sessions: {len(user_sessions)}")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_distributed_cache_stress(self, stress_runner: StressTestRunner):
        """Test distributed cache behavior under stress."""
        
        cache_operations = []
        
        async def cache_stress_test(user_id: int, request_id: int, client: AsyncClient):
            """Test cache operations under stress."""
            try:
                # Simulate cache-heavy operations
                cache_key = f"user_{user_id}_data"
                
                # Operations that typically use cache
                operations = [
                    # Get user profile (likely cached)
                    lambda: client.get("/api/v1/users/profile"),
                    
                    # Get company data (likely cached)
                    lambda: client.get(f"/api/v1/companies/{(user_id % 10) + 1}"),
                    
                    # Get tender list (with pagination - cache per page)
                    lambda: client.get(f"/api/v1/tenders/?page={request_id % 5 + 1}"),
                    
                    # Get supplier list (cached with filters)
                    lambda: client.get(f"/api/v1/suppliers/?active=true&page={request_id % 3 + 1}")
                ]
                
                operation = operations[request_id % len(operations)]
                start_time = time.time()
                
                response = await operation()
                
                end_time = time.time()
                response_time = end_time - start_time
                
                cache_operations.append({
                    'user_id': user_id,
                    'request_id': request_id,
                    'operation': operation.__name__ if hasattr(operation, '__name__') else 'lambda',
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'cache_header': response.headers.get('X-Cache-Status', 'unknown')
                })
                
                assert response.status_code < 500
                
            except Exception as e:
                print(f"Cache stress test error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                cache_stress_test, client
            )
        
        # Analyze cache performance
        if cache_operations:
            avg_response_time = sum(op['response_time'] for op in cache_operations) / len(cache_operations)
            cache_hits = sum(1 for op in cache_operations if op.get('cache_header') == 'HIT')
            cache_misses = sum(1 for op in cache_operations if op.get('cache_header') == 'MISS')
            
            print(f"Cache stress test results:")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Cache hits: {cache_hits}, misses: {cache_misses}")
            print(f"  Cache hit ratio: {(cache_hits / len(cache_operations) * 100):.2f}%" if cache_operations else "N/A")
        
        stress_runner.assert_performance_thresholds()


class TestScalabilityLimits:
    """Stress tests for scalability limits."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_concurrent_user_limit(self, heavy_stress_config):
        """Test application behavior at concurrent user limits."""
        stress_runner = StressTestRunner(heavy_stress_config)
        
        user_tracking = {}
        
        async def concurrent_user_test(user_id: int, request_id: int, client: AsyncClient):
            """Simulate individual user behavior."""
            try:
                # Track unique users
                if user_id not in user_tracking:
                    user_tracking[user_id] = {
                        'first_request': time.time(),
                        'request_count': 0,
                        'errors': 0
                    }
                
                user_tracking[user_id]['request_count'] += 1
                
                # Simulate realistic user session
                user_actions = [
                    # Login/authentication
                    lambda: client.post("/api/v1/auth/login", data={
                        "username": f"loadtest{user_id}@example.com",
                        "password": "password123"
                    }),
                    
                    # Browse data
                    lambda: client.get("/api/v1/companies/"),
                    lambda: client.get("/api/v1/tenders/"),
                    lambda: client.get("/api/v1/suppliers/"),
                    
                    # View details
                    lambda: client.get(f"/api/v1/tenders/{(request_id % 20) + 1}"),
                    lambda: client.get(f"/api/v1/companies/{(request_id % 10) + 1}"),
                    
                    # Search operations
                    lambda: client.get(f"/api/v1/tenders/?search=test_{request_id}"),
                    lambda: client.get(f"/api/v1/suppliers/?search=supplier_{request_id}")
                ]
                
                # Perform random user action
                action = random.choice(user_actions)
                response = await action()
                
                if response.status_code >= 500:
                    user_tracking[user_id]['errors'] += 1
                
                # Add realistic delays between requests
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
            except Exception as e:
                print(f"Concurrent user test error for user {user_id}: {e}")
                user_tracking[user_id]['errors'] += 1
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                concurrent_user_test, client
            )
        
        # Analyze user scalability
        total_users = len(user_tracking)
        total_requests = sum(user['request_count'] for user in user_tracking.values())
        total_errors = sum(user['errors'] for user in user_tracking.values())
        
        print(f"Concurrent user limit test:")
        print(f"  Total unique users: {total_users}")
        print(f"  Total requests: {total_requests}")
        print(f"  Total errors: {total_errors}")
        print(f"  Error rate: {(total_errors / total_requests * 100):.2f}%" if total_requests > 0 else "N/A")
        
        # Assert scalability thresholds
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        assert error_rate < 10, f"Error rate {error_rate:.2f}% exceeds 10% threshold"
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_data_volume_scalability(self, stress_runner: StressTestRunner):
        """Test application behavior with large data volumes."""
        
        async def data_volume_test(user_id: int, request_id: int, client: AsyncClient):
            """Test operations with large data volumes."""
            try:
                # Test pagination with large datasets
                page_sizes = [10, 50, 100, 200]
                page_size = page_sizes[request_id % len(page_sizes)]
                
                # Request large pages of data
                response = await client.get(
                    f"/api/v1/tenders/?page=1&size={page_size}&include_items=true"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verify data integrity with large responses
                    if isinstance(data, dict) and 'items' in data:
                        items = data['items']
                        assert len(items) <= page_size
                        
                        # Process large data response
                        for item in items[:10]:  # Process first 10 items
                            if isinstance(item, dict):
                                # Simulate data processing
                                processed = {k: str(v) for k, v in item.items()}
                
                # Test search with large result sets
                search_response = await client.get(
                    f"/api/v1/tenders/?search=&page=1&size={page_size}"
                )
                
                assert search_response.status_code in [200, 401, 403]
                
            except Exception as e:
                print(f"Data volume test error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                data_volume_test, client
            )
        
        stress_runner.assert_performance_thresholds()
        print(f"Data volume scalability: {metrics.successful_requests}/{metrics.total_requests} successful")


class TestAutoScalingStress:
    """Stress tests for auto-scaling behavior."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_gradual_load_increase(self, light_stress_config):
        """Test gradual load increase to trigger auto-scaling."""
        
        response_times = []
        load_phases = []
        
        # Phase 1: Low load
        print("Phase 1: Low load (10 concurrent users)")
        low_load_config = light_stress_config
        low_load_config.concurrent_users = 10
        stress_runner = StressTestRunner(low_load_config)
        
        async def low_load_test(user_id: int, request_id: int, client: AsyncClient):
            start_time = time.time()
            response = await client.get("/api/v1/companies/")
            end_time = time.time()
            
            response_times.append({
                'phase': 1,
                'user_id': user_id,
                'response_time': end_time - start_time,
                'status_code': response.status_code
            })
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            await stress_runner.run_concurrent_test(low_load_test, client)
        
        # Wait between phases
        await asyncio.sleep(2)
        
        # Phase 2: Medium load
        print("Phase 2: Medium load (30 concurrent users)")
        medium_load_config = light_stress_config
        medium_load_config.concurrent_users = 30
        stress_runner = StressTestRunner(medium_load_config)
        
        async def medium_load_test(user_id: int, request_id: int, client: AsyncClient):
            start_time = time.time()
            response = await client.get("/api/v1/tenders/")
            end_time = time.time()
            
            response_times.append({
                'phase': 2,
                'user_id': user_id,
                'response_time': end_time - start_time,
                'status_code': response.status_code
            })
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            await stress_runner.run_concurrent_test(medium_load_test, client)
        
        # Wait between phases
        await asyncio.sleep(2)
        
        # Phase 3: High load
        print("Phase 3: High load (50 concurrent users)")
        high_load_config = light_stress_config
        high_load_config.concurrent_users = 50
        stress_runner = StressTestRunner(high_load_config)
        
        async def high_load_test(user_id: int, request_id: int, client: AsyncClient):
            start_time = time.time()
            response = await client.get("/api/v1/suppliers/")
            end_time = time.time()
            
            response_times.append({
                'phase': 3,
                'user_id': user_id,
                'response_time': end_time - start_time,
                'status_code': response.status_code
            })
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            await stress_runner.run_concurrent_test(high_load_test, client)
        
        # Analyze scaling behavior
        phase_stats = {}
        for phase in [1, 2, 3]:
            phase_responses = [r for r in response_times if r['phase'] == phase]
            if phase_responses:
                avg_response_time = sum(r['response_time'] for r in phase_responses) / len(phase_responses)
                success_rate = sum(1 for r in phase_responses if r['status_code'] < 400) / len(phase_responses) * 100
                
                phase_stats[phase] = {
                    'avg_response_time': avg_response_time,
                    'success_rate': success_rate,
                    'total_requests': len(phase_responses)
                }
        
        print("Auto-scaling behavior analysis:")
        for phase, stats in phase_stats.items():
            print(f"  Phase {phase}: Avg response time: {stats['avg_response_time']:.3f}s, Success rate: {stats['success_rate']:.2f}%")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_spike_load_handling(self, light_stress_config):
        """Test sudden load spikes to verify auto-scaling response."""
        
        spike_metrics = []
        
        async def spike_load_test(user_id: int, request_id: int, client: AsyncClient):
            """Simulate sudden load spike."""
            try:
                start_time = time.time()
                
                # Perform multiple rapid requests to simulate spike
                rapid_requests = []
                for i in range(3):
                    response = await client.get(f"/api/v1/companies/?page={i+1}")
                    rapid_requests.append({
                        'response_time': time.time() - start_time,
                        'status_code': response.status_code
                    })
                    start_time = time.time()  # Reset for next request
                
                spike_metrics.extend(rapid_requests)
                
            except Exception as e:
                print(f"Spike load test error: {e}")
                raise e
        
        # Create sudden load spike
        spike_config = light_stress_config
        spike_config.concurrent_users = 100  # Sudden spike
        spike_config.requests_per_user = 3
        spike_config.ramp_up_seconds = 1  # Very fast ramp up
        
        stress_runner = StressTestRunner(spike_config)
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                spike_load_test, client
            )
        
        # Analyze spike handling
        if spike_metrics:
            avg_response_time = sum(m['response_time'] for m in spike_metrics) / len(spike_metrics)
            max_response_time = max(m['response_time'] for m in spike_metrics)
            success_rate = sum(1 for m in spike_metrics if m['status_code'] < 400) / len(spike_metrics) * 100
            
            print(f"Spike load handling results:")
            print(f"  Avg response time: {avg_response_time:.3f}s")
            print(f"  Max response time: {max_response_time:.3f}s")
            print(f"  Success rate: {success_rate:.2f}%")
            print(f"  Total spike requests: {len(spike_metrics)}")
            
            # Assert spike handling thresholds
            assert success_rate > 70, f"Success rate {success_rate:.2f}% too low for spike handling"
            assert max_response_time < 10, f"Max response time {max_response_time:.3f}s too high for spike handling"


class TestFailoverStress:
    """Stress tests for failover scenarios."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_service_degradation_handling(self, light_stress_config):
        """Test application behavior during service degradation."""
        stress_runner = StressTestRunner(light_stress_config)
        
        degradation_results = []
        
        async def degradation_test(user_id: int, request_id: int, client: AsyncClient):
            """Test service behavior during degradation."""
            try:
                # Simulate different levels of service degradation
                degradation_level = request_id % 4
                
                if degradation_level == 0:
                    # Normal operation
                    response = await client.get("/api/v1/companies/")
                elif degradation_level == 1:
                    # Slow database (timeout simulation)
                    response = await asyncio.wait_for(
                        client.get("/api/v1/tenders/?include_items=true"),
                        timeout=5.0
                    )
                elif degradation_level == 2:
                    # External service unavailable
                    response = await client.get("/api/v1/suppliers/?external_data=true")
                else:
                    # Cache unavailable
                    response = await client.get("/api/v1/users/profile")
                
                degradation_results.append({
                    'user_id': user_id,
                    'degradation_level': degradation_level,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                })
                
                # Accept degraded service responses
                assert response.status_code in [200, 202, 503, 504, 401, 403]
                
            except asyncio.TimeoutError:
                # Timeout is acceptable during degradation
                degradation_results.append({
                    'user_id': user_id,
                    'degradation_level': degradation_level,
                    'status_code': 504,
                    'response_time': 5.0
                })
            except Exception as e:
                print(f"Degradation test error: {e}")
                raise e
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            metrics = await stress_runner.run_concurrent_test(
                degradation_test, client
            )
        
        # Analyze degradation handling
        if degradation_results:
            for level in range(4):
                level_results = [r for r in degradation_results if r['degradation_level'] == level]
                if level_results:
                    avg_response_time = sum(r['response_time'] for r in level_results) / len(level_results)
                    success_rate = sum(1 for r in level_results if r['status_code'] < 400) / len(level_results) * 100
                    
                    print(f"Degradation level {level}: Avg response time: {avg_response_time:.3f}s, Success rate: {success_rate:.2f}%")
        
        print(f"Service degradation handling: {len(degradation_results)} total requests processed")
