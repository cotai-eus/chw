"""
Stress Test Configuration and Utilities

Configuration files and utilities for running stress tests.
"""
import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class StressTestEnvironment:
    """Environment configuration for stress tests."""
    
    # Database settings
    database_url: str = "postgresql+asyncpg://test:test@localhost:5432/test_db"
    redis_url: str = "redis://localhost:6379/1"
    mongodb_url: str = "mongodb://localhost:27017/test_db"
    
    # Application settings
    api_base_url: str = "http://localhost:8000"
    websocket_base_url: str = "ws://localhost:8000"
    
    # Test settings
    test_timeout: int = 300  # 5 minutes
    cleanup_after_test: bool = True
    generate_reports: bool = True
    
    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    max_response_time_ms: int = 5000
    
    @classmethod
    def from_environment(cls) -> 'StressTestEnvironment':
        """Create configuration from environment variables."""
        return cls(
            database_url=os.getenv('TEST_DATABASE_URL', cls.database_url),
            redis_url=os.getenv('TEST_REDIS_URL', cls.redis_url),
            mongodb_url=os.getenv('TEST_MONGODB_URL', cls.mongodb_url),
            api_base_url=os.getenv('TEST_API_BASE_URL', cls.api_base_url),
            websocket_base_url=os.getenv('TEST_WEBSOCKET_BASE_URL', cls.websocket_base_url),
            test_timeout=int(os.getenv('TEST_TIMEOUT', cls.test_timeout)),
            cleanup_after_test=os.getenv('TEST_CLEANUP', 'true').lower() == 'true',
            generate_reports=os.getenv('TEST_GENERATE_REPORTS', 'true').lower() == 'true',
            max_memory_mb=int(os.getenv('TEST_MAX_MEMORY_MB', cls.max_memory_mb)),
            max_cpu_percent=float(os.getenv('TEST_MAX_CPU_PERCENT', cls.max_cpu_percent)),
            max_response_time_ms=int(os.getenv('TEST_MAX_RESPONSE_TIME_MS', cls.max_response_time_ms))
        )


# Predefined test configurations
STRESS_TEST_CONFIGS = {
    'ci_cd': {
        'concurrent_users': 5,
        'requests_per_user': 3,
        'test_duration_seconds': 10,
        'max_response_time_ms': 3000,
        'error_threshold_percent': 20.0,
        'memory_threshold_mb': 256,
        'description': 'Minimal stress testing for CI/CD pipelines'
    },
    'development': {
        'concurrent_users': 10,
        'requests_per_user': 5,
        'test_duration_seconds': 30,
        'max_response_time_ms': 2000,
        'error_threshold_percent': 15.0,
        'memory_threshold_mb': 512,
        'description': 'Light stress testing for development validation'
    },
    'staging': {
        'concurrent_users': 50,
        'requests_per_user': 10,
        'test_duration_seconds': 120,
        'max_response_time_ms': 1500,
        'error_threshold_percent': 10.0,
        'memory_threshold_mb': 1024,
        'description': 'Medium stress testing for staging environment'
    },
    'production_validation': {
        'concurrent_users': 200,
        'requests_per_user': 20,
        'test_duration_seconds': 300,
        'max_response_time_ms': 1000,
        'error_threshold_percent': 5.0,
        'memory_threshold_mb': 2048,
        'description': 'Heavy stress testing for production validation'
    },
    'load_testing': {
        'concurrent_users': 500,
        'requests_per_user': 50,
        'test_duration_seconds': 600,
        'max_response_time_ms': 2000,
        'error_threshold_percent': 8.0,
        'memory_threshold_mb': 4096,
        'description': 'Load testing for capacity planning'
    },
    'spike_testing': {
        'concurrent_users': 1000,
        'requests_per_user': 10,
        'test_duration_seconds': 60,
        'max_response_time_ms': 5000,
        'error_threshold_percent': 15.0,
        'memory_threshold_mb': 3072,
        'description': 'Spike testing for auto-scaling validation'
    }
}


def get_stress_config(config_name: str) -> Dict[str, Any]:
    """Get stress test configuration by name."""
    if config_name not in STRESS_TEST_CONFIGS:
        raise ValueError(f"Unknown stress test configuration: {config_name}")
    
    config = STRESS_TEST_CONFIGS[config_name].copy()
    
    # Override with environment variables if present
    config.update({
        'concurrent_users': int(os.getenv('STRESS_CONCURRENT_USERS', config['concurrent_users'])),
        'requests_per_user': int(os.getenv('STRESS_REQUESTS_PER_USER', config['requests_per_user'])),
        'test_duration_seconds': int(os.getenv('STRESS_DURATION', config['test_duration_seconds'])),
        'max_response_time_ms': int(os.getenv('STRESS_MAX_RESPONSE_TIME', config['max_response_time_ms'])),
        'error_threshold_percent': float(os.getenv('STRESS_ERROR_THRESHOLD', config['error_threshold_percent'])),
        'memory_threshold_mb': int(os.getenv('STRESS_MEMORY_THRESHOLD', config['memory_threshold_mb']))
    })
    
    return config


# Test data generators
TEST_DATA_GENERATORS = {
    'users': lambda count: [
        {
            'email': f'stress_user_{i}@example.com',
            'full_name': f'Stress Test User {i}',
            'password': 'stress_test_password_123'
        }
        for i in range(count)
    ],
    
    'companies': lambda count: [
        {
            'name': f'Stress Test Company {i}',
            'cnpj': f'{i:014d}',
            'email': f'company{i}@stress-test.com',
            'phone': f'+55119999{i:04d}',
            'address': f'Test Address {i}, Test City'
        }
        for i in range(count)
    ],
    
    'tenders': lambda count: [
        {
            'title': f'Stress Test Tender {i}',
            'description': f'Description for stress test tender {i}',
            'opening_date': '2024-12-01T10:00:00',
            'closing_date': '2024-12-15T17:00:00',
            'budget': 10000.0 + (i * 1000),
            'items': [
                {
                    'description': f'Item {j} for tender {i}',
                    'quantity': 10 + j,
                    'unit': 'units',
                    'unit_price': 100.0 + (j * 10)
                }
                for j in range(3)
            ]
        }
        for i in range(count)
    ],
    
    'suppliers': lambda count: [
        {
            'name': f'Stress Test Supplier {i}',
            'cnpj': f'{i+1000:014d}',
            'email': f'supplier{i}@stress-test.com',
            'phone': f'+55118888{i:04d}',
            'address': f'Supplier Address {i}, Supplier City',
            'is_active': True
        }
        for i in range(count)
    ]
}


def generate_test_data(data_type: str, count: int = 10):
    """Generate test data for stress testing."""
    if data_type not in TEST_DATA_GENERATORS:
        raise ValueError(f"Unknown test data type: {data_type}")
    
    return TEST_DATA_GENERATORS[data_type](count)


# Performance benchmarks
PERFORMANCE_BENCHMARKS = {
    'api_endpoints': {
        'login': {'max_response_time': 500, 'min_throughput': 100},
        'list_companies': {'max_response_time': 200, 'min_throughput': 200},
        'create_tender': {'max_response_time': 1000, 'min_throughput': 50},
        'search_tenders': {'max_response_time': 300, 'min_throughput': 150},
        'user_profile': {'max_response_time': 150, 'min_throughput': 300}
    },
    
    'database_operations': {
        'select_query': {'max_response_time': 50, 'min_throughput': 1000},
        'insert_operation': {'max_response_time': 100, 'min_throughput': 500},
        'update_operation': {'max_response_time': 75, 'min_throughput': 600},
        'complex_join': {'max_response_time': 200, 'min_throughput': 200}
    },
    
    'websocket_operations': {
        'connection_establishment': {'max_response_time': 1000, 'min_throughput': 100},
        'message_send': {'max_response_time': 50, 'min_throughput': 1000},
        'broadcast_message': {'max_response_time': 100, 'min_throughput': 500}
    },
    
    'celery_tasks': {
        'email_task': {'max_response_time': 2000, 'min_throughput': 50},
        'ai_analysis': {'max_response_time': 5000, 'min_throughput': 20},
        'file_processing': {'max_response_time': 3000, 'min_throughput': 30},
        'notification_task': {'max_response_time': 500, 'min_throughput': 200}
    }
}


def get_performance_benchmark(category: str, operation: str) -> Dict[str, int]:
    """Get performance benchmark for specific operation."""
    if category not in PERFORMANCE_BENCHMARKS:
        raise ValueError(f"Unknown benchmark category: {category}")
    
    if operation not in PERFORMANCE_BENCHMARKS[category]:
        raise ValueError(f"Unknown operation in {category}: {operation}")
    
    return PERFORMANCE_BENCHMARKS[category][operation]


# Stress test reporting utilities
class StressTestReporter:
    """Utility class for generating stress test reports."""
    
    @staticmethod
    def generate_summary_report(test_results: Dict[str, Any]) -> str:
        """Generate a summary report from test results."""
        report = []
        report.append("# Stress Test Summary Report")
        report.append(f"Generated on: {test_results.get('timestamp', 'Unknown')}")
        report.append("")
        
        # Overall metrics
        report.append("## Overall Metrics")
        report.append(f"- Total requests: {test_results.get('total_requests', 0)}")
        report.append(f"- Successful requests: {test_results.get('successful_requests', 0)}")
        report.append(f"- Failed requests: {test_results.get('failed_requests', 0)}")
        report.append(f"- Average response time: {test_results.get('avg_response_time', 0):.2f}ms")
        report.append(f"- Requests per second: {test_results.get('requests_per_second', 0):.2f}")
        report.append("")
        
        # Resource usage
        if 'resource_usage' in test_results:
            resource = test_results['resource_usage']
            report.append("## Resource Usage")
            report.append(f"- Peak memory usage: {resource.get('peak_memory_mb', 0):.2f}MB")
            report.append(f"- Peak CPU usage: {resource.get('peak_cpu_percent', 0):.2f}%")
            report.append("")
        
        # Test suite results
        if 'test_suites' in test_results:
            report.append("## Test Suite Results")
            for suite_name, suite_result in test_results['test_suites'].items():
                status = "✅ PASSED" if suite_result.get('success', False) else "❌ FAILED"
                report.append(f"- {suite_name}: {status}")
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        if test_results.get('failed_requests', 0) > 0:
            error_rate = (test_results['failed_requests'] / test_results['total_requests']) * 100
            if error_rate > 10:
                report.append("- ⚠️ High error rate detected - investigate application stability")
        
        if test_results.get('avg_response_time', 0) > 2000:
            report.append("- ⚠️ High response times detected - consider performance optimization")
        
        return "\\n".join(report)
    
    @staticmethod
    def save_report(report_content: str, filename: str):
        """Save report to file."""
        with open(filename, 'w') as f:
            f.write(report_content)
        print(f"📄 Report saved to: {filename}")


# Export commonly used configurations
DEFAULT_STRESS_CONFIG = get_stress_config('development')
CI_STRESS_CONFIG = get_stress_config('ci_cd')
PRODUCTION_STRESS_CONFIG = get_stress_config('production_validation')
