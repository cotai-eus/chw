#!/usr/bin/env python3
"""
Comprehensive Test Configuration

Centralized configuration for all test categories and infrastructure.
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TestCategory(Enum):
    """Test category enumeration."""
    UNIT = "unit"
    INTEGRATION = "integration"
    API_CONTRACTS = "api_contracts"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STRESS = "stress"
    CHAOS = "chaos"
    E2E = "e2e"
    MONITORING = "monitoring"


class TestEnvironment(Enum):
    """Test environment enumeration."""
    LOCAL = "local"
    CI = "ci"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class TestThresholds:
    """Test threshold configurations."""
    # Performance thresholds
    max_response_time_ms: int = 500
    max_memory_usage_mb: int = 512
    max_cpu_usage_percent: float = 80.0
    min_success_rate_percent: float = 99.5
    max_regression_percent: float = 10.0
    
    # Security thresholds
    max_vulnerabilities: int = 0
    min_security_score: int = 95
    
    # Stress test thresholds
    max_concurrent_users: int = 1000
    test_duration_seconds: int = 300
    ramp_up_seconds: int = 30
    
    # Chaos engineering thresholds
    min_resilience_score: int = 90
    max_recovery_time_seconds: int = 30
    
    # Database thresholds
    max_query_time_ms: int = 100
    max_connection_pool_size: int = 20


@dataclass
class TestCategoryConfig:
    """Configuration for a test category."""
    name: str
    description: str
    path: str
    marker: str
    timeout_seconds: int
    enabled: bool = True
    parallel: bool = False
    dependencies: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=dict)


class ComprehensiveTestConfig:
    """Comprehensive test configuration manager."""
    
    def __init__(self, environment: TestEnvironment = TestEnvironment.LOCAL):
        self.environment = environment
        self.base_path = Path(__file__).parent.parent
        self.thresholds = TestThresholds()
        self._setup_categories()
        self._setup_quality_gates()
    
    def _setup_categories(self):
        """Setup test category configurations."""
        self.categories = {
            TestCategory.UNIT: TestCategoryConfig(
                name="Unit Tests",
                description="Unit tests for individual components",
                path="tests/unit/",
                marker="unit",
                timeout_seconds=300,
                parallel=True
            ),
            
            TestCategory.INTEGRATION: TestCategoryConfig(
                name="Integration Tests",
                description="Integration tests including database migrations",
                path="tests/integration/",
                marker="integration",
                timeout_seconds=600,
                dependencies=["postgresql", "redis"],
                environment_vars={
                    "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
                    "REDIS_URL": "redis://localhost:6379/0"
                }
            ),
            
            TestCategory.API_CONTRACTS: TestCategoryConfig(
                name="API Contract Tests",
                description="API contract and compatibility testing",
                path="tests/api_docs/",
                marker="contract",
                timeout_seconds=300,
                dependencies=["jsonschema"]
            ),
            
            TestCategory.SECURITY: TestCategoryConfig(
                name="Security Tests",
                description="Advanced security vulnerability testing",
                path="tests/security/",
                marker="security",
                timeout_seconds=600,
                dependencies=["bandit", "safety"]
            ),
            
            TestCategory.PERFORMANCE: TestCategoryConfig(
                name="Performance Tests",
                description="Performance regression detection",
                path="tests/performance/",
                marker="performance",
                timeout_seconds=900,
                dependencies=["matplotlib", "pandas"]
            ),
            
            TestCategory.STRESS: TestCategoryConfig(
                name="Stress Tests",
                description="High-concurrency stress testing",
                path="tests/stress/",
                marker="stress",
                timeout_seconds=1800,
                dependencies=["locust", "psutil"]
            ),
            
            TestCategory.CHAOS: TestCategoryConfig(
                name="Chaos Engineering",
                description="Chaos engineering resilience tests",
                path="tests/stress/",
                marker="chaos",
                timeout_seconds=1200,
                dependencies=["chaos-toolkit"]
            ),
            
            TestCategory.E2E: TestCategoryConfig(
                name="End-to-End Tests",
                description="Complete user journey testing",
                path="tests/e2e/",
                marker="e2e",
                timeout_seconds=1800,
                dependencies=["selenium", "playwright"]
            ),
            
            TestCategory.MONITORING: TestCategoryConfig(
                name="Monitoring Tests",
                description="Monitoring and observability validation",
                path="tests/monitoring/",
                marker="monitoring",
                timeout_seconds=300,
                dependencies=["prometheus-client"]
            )
        }
    
    def _setup_quality_gates(self):
        """Setup quality gate configurations."""
        self.quality_gates = {
            'api_contracts': {
                'max_failures': 0,
                'min_coverage': 95,
                'max_response_time': self.thresholds.max_response_time_ms
            },
            'security': {
                'max_vulnerabilities': self.thresholds.max_vulnerabilities,
                'min_security_score': self.thresholds.min_security_score
            },
            'performance': {
                'max_regression': self.thresholds.max_regression_percent,
                'min_success_rate': self.thresholds.min_success_rate_percent
            },
            'chaos': {
                'min_resilience_score': self.thresholds.min_resilience_score,
                'max_recovery_time': self.thresholds.max_recovery_time_seconds
            },
            'stress': {
                'max_error_rate': 1.0,  # 1%
                'min_throughput': 100,  # requests/second
                'max_response_time': self.thresholds.max_response_time_ms * 2
            }
        }
    
    def get_category_config(self, category: TestCategory) -> TestCategoryConfig:
        """Get configuration for a specific test category."""
        return self.categories.get(category)
    
    def get_enabled_categories(self) -> List[TestCategory]:
        """Get list of enabled test categories."""
        return [cat for cat, config in self.categories.items() if config.enabled]
    
    def get_parallel_categories(self) -> List[TestCategory]:
        """Get list of categories that can run in parallel."""
        return [cat for cat, config in self.categories.items() if config.parallel]
    
    def get_pytest_args(self, category: TestCategory) -> List[str]:
        """Get pytest arguments for a specific category."""
        config = self.get_category_config(category)
        if not config:
            return []

        args = [
            config.path,
            "-v",
            "--tb=short",
            f"-m {config.marker}"
        ]
        
        # Add timeout only if pytest-timeout is available
        try:
            import pytest_timeout
            args.append(f"--timeout={config.timeout_seconds}")
        except ImportError:
            pass

        # Add coverage for unit tests
        if category == TestCategory.UNIT:
            args.extend([
                "--cov=app",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-fail-under=0"  # Don't fail on low coverage during development
            ])

        # Add JSON report for CI
        if self.environment == TestEnvironment.CI:
            args.append(f"--json-report --json-report-file=reports/{category.value}.json")

        return args
    
    def get_environment_setup(self, category: TestCategory) -> Dict[str, str]:
        """Get environment variables for a specific category."""
        config = self.get_category_config(category)
        base_env = {
            "TESTING": "true",
            "LOG_LEVEL": "INFO",
            "TEST_CATEGORY": category.value,
            "TEST_ENVIRONMENT": self.environment.value
        }
        
        if config and config.environment_vars:
            base_env.update(config.environment_vars)
        
        return base_env
    
    def validate_dependencies(self, category: TestCategory) -> List[str]:
        """Validate dependencies for a category and return missing ones."""
        config = self.get_category_config(category)
        if not config or not config.dependencies:
            return []
        
        missing = []
        for dep in config.dependencies:
            try:
                __import__(dep.replace("-", "_"))
            except ImportError:
                missing.append(dep)
        
        return missing
    
    def generate_pytest_ini(self) -> str:
        """Generate pytest.ini configuration."""
        return f"""[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --maxfail=5
    --durations=10

markers =
    unit: Unit tests
    integration: Integration tests
    contract: API contract tests
    security: Security tests
    performance: Performance tests
    stress: Stress tests
    chaos: Chaos engineering tests
    e2e: End-to-end tests
    monitoring: Monitoring tests
    slow: Slow running tests
    heavy: Heavy resource usage tests
    smoke: Smoke tests
    regression: Regression tests

timeout = 300
timeout_method = thread

# Coverage settings
coverage_omit = 
    tests/*
    */migrations/*
    */venv/*
    */__pycache__/*

# Test discovery
minversion = 7.0
"""
    
    def generate_test_execution_plan(self, categories: Optional[List[TestCategory]] = None) -> Dict[str, Any]:
        """Generate execution plan for test categories."""
        if categories is None:
            categories = self.get_enabled_categories()
        
        parallel_categories = []
        sequential_categories = []
        
        for category in categories:
            config = self.get_category_config(category)
            if config and config.parallel:
                parallel_categories.append(category)
            else:
                sequential_categories.append(category)
        
        return {
            "parallel_execution": {
                "categories": [cat.value for cat in parallel_categories],
                "max_workers": min(len(parallel_categories), 4)
            },
            "sequential_execution": {
                "categories": [cat.value for cat in sequential_categories]
            },
            "total_estimated_time": sum(
                self.get_category_config(cat).timeout_seconds 
                for cat in categories
            ),
            "quality_gates": self.quality_gates
        }


# Global configuration instance
test_config = ComprehensiveTestConfig()


# Utility functions for easy access
def get_test_config() -> ComprehensiveTestConfig:
    """Get the global test configuration instance."""
    return test_config


def get_quality_gates() -> Dict[str, Any]:
    """Get quality gate configurations."""
    return test_config.quality_gates


def get_test_thresholds() -> TestThresholds:
    """Get test threshold configurations."""
    return test_config.thresholds


def update_thresholds(**kwargs):
    """Update test thresholds."""
    for key, value in kwargs.items():
        if hasattr(test_config.thresholds, key):
            setattr(test_config.thresholds, key, value)
