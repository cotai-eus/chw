# Comprehensive Stress Testing Suite

This directory contains a comprehensive stress testing framework for high-concurrency scenarios, performance validation, and bottleneck detection.

## Overview

The stress testing suite is designed to validate system performance under various load conditions, detect bottlenecks, monitor resource usage, and provide comprehensive reporting for performance analysis.

## Test Categories

### 1. API Endpoint Stress Tests (`test_api_stress.py`)
- **Authentication endpoint stress**: High-concurrency login requests
- **User profile endpoint stress**: Authenticated user profile access
- **Company listing stress**: Public endpoint load testing
- **Tender creation stress**: Write operation performance

### 2. Database Stress Tests (`test_database_stress.py`)
- **Connection pool stress**: Database connection management
- **Concurrent transactions**: Transaction isolation and performance
- **SELECT query stress**: Read operation performance
- **INSERT/UPDATE stress**: Write operation performance
- **Deadlock handling**: Concurrent write scenarios

### 3. WebSocket Stress Tests (`test_websocket_stress.py`)
- **Concurrent connections**: Multiple WebSocket connections
- **Message handling stress**: High-frequency message processing
- **Real-time communication**: Notification and chat systems
- **Connection lifecycle**: Connect/disconnect patterns

### 4. Celery Background Tasks (`test_celery_stress.py`)
- **Task queue stress**: High-volume task processing
- **Worker performance**: Background worker efficiency
- **Task prioritization**: Priority queue handling
- **Resource usage**: Memory and CPU usage monitoring

### 5. Memory Stress Tests (`test_memory_stress.py`)
- **Memory leak detection**: Long-running memory analysis
- **Garbage collection**: Memory cleanup efficiency
- **Resource exhaustion**: High memory usage scenarios
- **Memory growth patterns**: Trend analysis

### 6. Scalability Tests (`test_scalability_stress.py`)
- **Load balancing**: Distributed load scenarios
- **Auto-scaling**: Dynamic resource allocation
- **Failover scenarios**: System resilience testing
- **Capacity planning**: Performance limits identification

### 7. Concurrent Scenarios (`test_concurrent_scenarios.py`)
- **Mixed workload**: Realistic user behavior simulation
- **Burst traffic**: Flash crowd scenarios
- **Gradual load increase**: Breaking point detection
- **Concurrent data modification**: Race condition testing

### 8. Network Stress Tests (`test_network_stress.py`)
- **High latency conditions**: Network delay simulation
- **Packet loss scenarios**: Connection reliability
- **Connection pool exhaustion**: Resource limit testing
- **Geographic distribution**: Multi-location simulation

### 9. Resource Monitoring (`test_resource_monitoring.py`)
- **Real-time monitoring**: System resource tracking
- **Bottleneck detection**: Performance analysis
- **Memory leak detection**: Extended monitoring
- **Performance profiling**: Detailed resource analysis

## Test Profiles

### CI/CD Profile (`ci`)
- **Concurrent Users**: 5
- **Requests per User**: 3
- **Duration**: 10 seconds
- **Use Case**: Quick validation in CI/CD pipelines

### Light Profile (`light`)
- **Concurrent Users**: 10
- **Requests per User**: 5
- **Duration**: 30 seconds
- **Use Case**: Development environment validation

### Medium Profile (`medium`)
- **Concurrent Users**: 50
- **Requests per User**: 10
- **Duration**: 120 seconds
- **Use Case**: Staging environment testing

### Heavy Profile (`heavy`)
- **Concurrent Users**: 200
- **Requests per User**: 20
- **Duration**: 300 seconds
- **Use Case**: Production validation and performance testing

### Spike Profile (`spike`)
- **Concurrent Users**: 500
- **Requests per User**: 5
- **Duration**: 60 seconds
- **Use Case**: Sudden traffic surge testing

### Endurance Profile (`endurance`)
- **Concurrent Users**: 100
- **Requests per User**: 100
- **Duration**: 3600 seconds (1 hour)
- **Use Case**: Long-term stability testing

## Quick Start

### Prerequisites

```bash
# Install dependencies
poetry install

# Ensure test database is running
docker-compose up -d postgres redis mongodb

# Run database migrations
alembic upgrade head
```

### Running Individual Test Suites

```bash
# Run API stress tests with medium profile
python tests/stress/run_stress_tests.py --suite api --profile medium

# Run database stress tests with heavy profile
python tests/stress/run_stress_tests.py --suite database --profile heavy

# Run all tests with light profile
python tests/stress/run_stress_tests.py --suite all --profile light
```

### Running Specific Test Categories

```bash
# Run only concurrent scenario tests
pytest tests/stress/test_concurrent_scenarios.py -m stress -v

# Run memory stress tests with custom markers
pytest tests/stress/test_memory_stress.py -m "stress and not slow" -v

# Run network tests with specific profile
STRESS_PROFILE=heavy pytest tests/stress/test_network_stress.py -m stress -v
```

## Environment Configuration

### Environment Variables

```bash
# Test configuration
export STRESS_CONCURRENT_USERS=100
export STRESS_REQUESTS_PER_USER=10
export STRESS_DURATION=120
export STRESS_PROFILE=medium

# Database URLs
export TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test_db"
export TEST_REDIS_URL="redis://localhost:6379/1"
export TEST_MONGODB_URL="mongodb://localhost:27017/test_db"

# Application settings
export TEST_API_BASE_URL="http://localhost:8000"
export TEST_WEBSOCKET_BASE_URL="ws://localhost:8000"

# Resource limits
export TEST_MAX_MEMORY_MB=1024
export TEST_MAX_CPU_PERCENT=80.0
export TEST_MAX_RESPONSE_TIME_MS=2000
```

### Configuration Files

Create a `.env.stress` file for consistent configuration:

```bash
# Copy example configuration
cp .env.example .env.stress

# Edit stress testing specific settings
vim .env.stress
```

## Advanced Usage

### Custom Test Configuration

```python
from tests.stress.conftest import StressTestConfig, StressTestRunner

# Create custom configuration
config = StressTestConfig(
    concurrent_users=150,
    requests_per_user=25,
    test_duration_seconds=180,
    max_response_time_ms=1500,
    error_threshold_percent=5.0,
    memory_threshold_mb=2048,
    cpu_threshold_percent=75.0
)

# Run with custom configuration
stress_runner = StressTestRunner(config)
```

### Resource Monitoring

```python
from tests.stress.test_resource_monitoring import ResourceMonitor

# Create detailed monitoring
monitor = ResourceMonitor(sample_interval=0.1)

# Start monitoring
monitor_task = asyncio.create_task(monitor.start_monitoring())

# ... run your tests ...

# Stop and analyze
monitor.stop_monitoring()
report = monitor.generate_report()
```

### Performance Benchmarking

```python
from tests.stress.benchmark_tools import BenchmarkCollector, PerformanceAnalyzer

# Collect benchmarks
collector = BenchmarkCollector()
analyzer = PerformanceAnalyzer(collector)

# Analyze trends
trend = analyzer.analyze_trend('api_stress_test', days=30)

# Compare versions
comparison = analyzer.compare_versions(
    'api_stress_test',
    baseline_date=datetime(2024, 1, 1),
    current_date=datetime.now()
)
```

## Interpreting Results

### Performance Metrics

1. **Requests per Second (RPS)**: Throughput measurement
2. **Response Time**: Latency measurements (avg, p95, p99)
3. **Success Rate**: Percentage of successful requests
4. **Resource Usage**: CPU, memory, and connection metrics
5. **Error Analysis**: Types and frequency of errors

### Bottleneck Identification

- **CPU Bottleneck**: High CPU usage, degraded response times
- **Memory Bottleneck**: Memory growth, potential leaks
- **Database Bottleneck**: Connection pool exhaustion, slow queries
- **Network Bottleneck**: High latency, connection timeouts

### Performance Thresholds

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Response Time (avg) | < 200ms | 200-1000ms | > 1000ms |
| Success Rate | > 99% | 95-99% | < 95% |
| CPU Usage | < 70% | 70-85% | > 85% |
| Memory Usage | < 1GB | 1-2GB | > 2GB |

## Continuous Integration

### GitHub Actions Example

```yaml
name: Stress Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  stress-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run stress tests
        run: |
          poetry run python tests/stress/run_stress_tests.py --profile ci
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: stress-test-results
          path: stress_test_results/
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    triggers {
        cron('H 2 * * *')  // Daily
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'docker-compose up -d postgres redis mongodb'
                sh 'poetry install'
            }
        }
        
        stage('Light Stress Tests') {
            steps {
                sh 'poetry run python tests/stress/run_stress_tests.py --profile light'
            }
        }
        
        stage('Medium Stress Tests') {
            when {
                branch 'main'
            }
            steps {
                sh 'poetry run python tests/stress/run_stress_tests.py --profile medium'
            }
        }
        
        stage('Cleanup') {
            always {
                sh 'docker-compose down'
                archiveArtifacts artifacts: 'stress_test_results/**', fingerprint: true
            }
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure services are running
   ```bash
   docker-compose up -d postgres redis mongodb
   ```

2. **Memory Errors**: Reduce concurrent users or increase system memory
   ```bash
   export STRESS_CONCURRENT_USERS=10
   ```

3. **Timeout Errors**: Increase timeout thresholds
   ```bash
   export TEST_MAX_RESPONSE_TIME_MS=5000
   ```

4. **Database Errors**: Check connection pool settings
   ```python
   # In database configuration
   pool_size=20
   max_overflow=30
   ```

### Performance Tuning

1. **Application Level**:
   - Connection pooling optimization
   - Query optimization
   - Caching implementation
   - Async operation usage

2. **Infrastructure Level**:
   - Database tuning
   - Load balancer configuration
   - Resource allocation
   - Network optimization

### Monitoring and Alerting

Set up monitoring for:
- Performance regression detection
- Resource usage thresholds
- Error rate monitoring
- Response time alerts

## Contributing

### Adding New Tests

1. Create test file in appropriate category
2. Use `@pytest.mark.stress` decorator
3. Follow naming convention: `test_*_stress.py`
4. Include comprehensive assertions
5. Add documentation and examples

### Test Structure Template

```python
"""
New Stress Test Category

Description of what this test category covers.
"""
import pytest
from tests.stress.conftest import StressTestRunner

class TestNewStressCategory:
    """Test class for new stress category."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_new_stress_scenario(self, stress_runner: StressTestRunner):
        """Test description."""
        
        async def test_function(user_id: int, request_id: int, client):
            """Individual test function."""
            # Test implementation
            pass
        
        metrics = await stress_runner.run_concurrent_test(test_function)
        stress_runner.assert_performance_thresholds()
        
        # Custom assertions
        assert metrics.successful_requests > 0
```

## Best Practices

1. **Start Small**: Begin with light profiles and increase gradually
2. **Monitor Resources**: Always monitor system resources during tests
3. **Baseline Performance**: Establish baseline metrics for comparison
4. **Regular Execution**: Run stress tests regularly in CI/CD
5. **Document Results**: Keep performance reports for trend analysis
6. **Environment Isolation**: Use dedicated test environments
7. **Realistic Scenarios**: Model real user behavior patterns
8. **Failure Analysis**: Investigate and document failure patterns

## Support

For issues, questions, or contributions:
- Create GitHub issues for bugs or feature requests
- Review existing documentation and examples
- Check troubleshooting section for common problems
- Monitor system resources during test execution

---

This stress testing suite provides comprehensive validation of system performance under various load conditions, helping ensure your application can handle production traffic and scale effectively.
