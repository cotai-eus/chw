"""
Test Orchestration and CI/CD Integration

Comprehensive test orchestration framework for managing different test types,
parallel execution, and CI/CD pipeline integration.
"""
import pytest
import asyncio
import time
import json
import subprocess
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

from tests.stress.run_stress_tests import StressTestRunner
from tests.performance.test_regression_testing import PerformanceDatabase
from tests.security.test_advanced_security import PenetrationTester


@dataclass
class TestSuite:
    """Represents a test suite configuration."""
    name: str
    description: str
    test_files: List[str]
    markers: List[str]
    parallel: bool = False
    max_workers: int = 4
    timeout_minutes: int = 30
    retry_count: int = 0
    environment_requirements: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TestResult:
    """Represents test execution results."""
    suite_name: str
    status: str  # passed, failed, skipped, error
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    error_messages: List[str]
    coverage_percentage: Optional[float] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data


class TestOrchestrator:
    """Orchestrates execution of different test suites."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.test_suites = self._initialize_test_suites()
        self.results: List[TestResult] = []
        
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load orchestrator configuration."""
        default_config = {
            "parallel_execution": True,
            "max_parallel_suites": 3,
            "fail_fast": False,
            "generate_reports": True,
            "coverage_threshold": 80.0,
            "performance_regression_threshold": 0.2,
            "security_risk_threshold": 30
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _initialize_test_suites(self) -> Dict[str, TestSuite]:
        """Initialize all test suites."""
        return {
            "unit": TestSuite(
                name="unit",
                description="Unit tests for individual components",
                test_files=["tests/unit/"],
                markers=["unit"],
                parallel=True,
                max_workers=4,
                timeout_minutes=10
            ),
            "integration": TestSuite(
                name="integration",
                description="Integration tests for component interactions",
                test_files=["tests/integration/"],
                markers=["integration"],
                parallel=True,
                max_workers=2,
                timeout_minutes=20
            ),
            "api_contract": TestSuite(
                name="api_contract",
                description="API contract and compatibility tests",
                test_files=["tests/api_docs/test_contract_testing.py"],
                markers=["api"],
                parallel=False,
                timeout_minutes=15
            ),
            "security": TestSuite(
                name="security",
                description="Security vulnerability and penetration tests",
                test_files=["tests/security/"],
                markers=["security"],
                parallel=False,
                timeout_minutes=30,
                environment_requirements={"test_mode": "security"}
            ),
            "performance": TestSuite(
                name="performance",
                description="Performance and regression tests",
                test_files=["tests/performance/"],
                markers=["performance"],
                parallel=False,
                timeout_minutes=45
            ),
            "stress": TestSuite(
                name="stress",
                description="Stress and load testing",
                test_files=["tests/stress/"],
                markers=["stress"],
                parallel=False,
                timeout_minutes=60,
                environment_requirements={"stress_mode": "enabled"}
            ),
            "chaos": TestSuite(
                name="chaos",
                description="Chaos engineering tests",
                test_files=["tests/stress/test_chaos_engineering.py"],
                markers=["chaos"],
                parallel=False,
                timeout_minutes=30
            ),
            "e2e": TestSuite(
                name="e2e",
                description="End-to-end workflow tests",
                test_files=["tests/e2e/"],
                markers=["e2e"],
                parallel=False,
                timeout_minutes=45
            )
        }
    
    async def run_test_suite(self, suite_name: str, 
                           custom_args: Optional[List[str]] = None) -> TestResult:
        """Run a specific test suite."""
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        suite = self.test_suites[suite_name]
        start_time = datetime.now()
        
        try:
            # Prepare environment
            await self._prepare_environment(suite)
            
            # Build pytest command
            cmd = self._build_pytest_command(suite, custom_args)
            
            # Execute tests
            result = await self._execute_test_command(cmd, suite)
            
            # Parse results
            test_result = self._parse_test_results(suite_name, result, start_time)
            
            # Cleanup environment
            await self._cleanup_environment(suite)
            
            return test_result
            
        except Exception as e:
            end_time = datetime.now()
            return TestResult(
                suite_name=suite_name,
                status="error",
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                error_messages=[str(e)]
            )
    
    def _build_pytest_command(self, suite: TestSuite, 
                             custom_args: Optional[List[str]] = None) -> List[str]:
        """Build pytest command for test suite."""
        cmd = ["python", "-m", "pytest"]
        
        # Add test files/directories
        cmd.extend(suite.test_files)
        
        # Add markers
        if suite.markers:
            marker_expr = " or ".join(suite.markers)
            cmd.extend(["-m", marker_expr])
        
        # Add parallel execution
        if suite.parallel and suite.max_workers > 1:
            cmd.extend(["-n", str(suite.max_workers)])
        
        # Add coverage
        cmd.extend(["--cov=app", "--cov-report=json", "--cov-report=term"])
        
        # Add output formatting
        cmd.extend(["--json-report", "--json-report-file=test_results.json"])
        
        # Add timeout
        if suite.timeout_minutes:
            cmd.extend(["--timeout", str(suite.timeout_minutes * 60)])
        
        # Add verbosity
        cmd.extend(["-v"])
        
        # Add custom arguments
        if custom_args:
            cmd.extend(custom_args)
        
        return cmd
    
    async def _execute_test_command(self, cmd: List[str], suite: TestSuite) -> subprocess.CompletedProcess:
        """Execute test command asynchronously."""
        try:
            # Set environment variables
            env = {}
            if suite.environment_requirements:
                env.update(suite.environment_requirements)
            
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode(),
                stderr=stderr.decode()
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute test command: {e}")
    
    def _parse_test_results(self, suite_name: str, 
                           result: subprocess.CompletedProcess,
                           start_time: datetime) -> TestResult:
        """Parse test execution results."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Try to parse JSON report
        test_stats = {"tests": 0, "passed": 0, "failed": 0, "skipped": 0}
        coverage_percentage = None
        
        try:
            if Path("test_results.json").exists():
                with open("test_results.json", 'r') as f:
                    json_report = json.load(f)
                    summary = json_report.get("summary", {})
                    test_stats["tests"] = summary.get("total", 0)
                    test_stats["passed"] = summary.get("passed", 0)
                    test_stats["failed"] = summary.get("failed", 0)
                    test_stats["skipped"] = summary.get("skipped", 0)
        except Exception:
            pass
        
        # Try to parse coverage
        try:
            if Path("coverage.json").exists():
                with open("coverage.json", 'r') as f:
                    coverage_data = json.load(f)
                    coverage_percentage = coverage_data.get("totals", {}).get("percent_covered")
        except Exception:
            pass
        
        # Determine status
        if result.returncode == 0:
            status = "passed"
        elif test_stats["failed"] > 0:
            status = "failed"
        else:
            status = "error"
        
        # Extract error messages
        error_messages = []
        if result.stderr:
            error_messages.append(result.stderr)
        if result.returncode != 0 and result.stdout:
            # Extract failure information from stdout
            lines = result.stdout.split('\n')
            failure_lines = [line for line in lines if 'FAILED' in line or 'ERROR' in line]
            error_messages.extend(failure_lines[:5])  # First 5 failures
        
        return TestResult(
            suite_name=suite_name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            tests_run=test_stats["tests"],
            tests_passed=test_stats["passed"],
            tests_failed=test_stats["failed"],
            tests_skipped=test_stats["skipped"],
            error_messages=error_messages,
            coverage_percentage=coverage_percentage
        )
    
    async def _prepare_environment(self, suite: TestSuite):
        """Prepare environment for test suite."""
        # Start required services
        if suite.name in ["integration", "e2e", "stress"]:
            # Ensure database is ready
            await self._ensure_database_ready()
        
        if suite.name in ["stress", "performance"]:
            # Clear performance data
            await self._clear_performance_data()
    
    async def _cleanup_environment(self, suite: TestSuite):
        """Clean up environment after test suite."""
        # Cleanup test files
        temp_files = ["test_results.json", "coverage.json", ".coverage"]
        for file in temp_files:
            if Path(file).exists():
                Path(file).unlink()
    
    async def _ensure_database_ready(self):
        """Ensure test database is ready."""
        # This would contain logic to verify database connectivity
        # and run any necessary setup
        pass
    
    async def _clear_performance_data(self):
        """Clear performance data for fresh testing."""
        # Clear performance databases and metrics
        pass
    
    async def run_parallel_suites(self, suite_names: List[str]) -> List[TestResult]:
        """Run multiple test suites in parallel."""
        if not self.config["parallel_execution"]:
            # Run sequentially
            results = []
            for suite_name in suite_names:
                result = await self.run_test_suite(suite_name)
                results.append(result)
                
                # Check fail fast
                if self.config["fail_fast"] and result.status == "failed":
                    break
            
            return results
        
        # Run in parallel with limit
        max_parallel = min(self.config["max_parallel_suites"], len(suite_names))
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def run_with_semaphore(suite_name: str) -> TestResult:
            async with semaphore:
                return await self.run_test_suite(suite_name)
        
        tasks = [run_with_semaphore(suite_name) for suite_name in suite_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = TestResult(
                    suite_name=suite_names[i],
                    status="error",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_seconds=0,
                    tests_run=0,
                    tests_passed=0,
                    tests_failed=0,
                    tests_skipped=0,
                    error_messages=[str(result)]
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results
    
    def generate_comprehensive_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = sum(r.tests_run for r in results)
        total_passed = sum(r.tests_passed for r in results)
        total_failed = sum(r.tests_failed for r in results)
        total_skipped = sum(r.tests_skipped for r in results)
        total_duration = sum(r.duration_seconds for r in results)
        
        # Calculate overall status
        overall_status = "passed"
        if any(r.status == "failed" for r in results):
            overall_status = "failed"
        elif any(r.status == "error" for r in results):
            overall_status = "error"
        
        # Calculate coverage
        coverage_results = [r.coverage_percentage for r in results if r.coverage_percentage is not None]
        avg_coverage = sum(coverage_results) / len(coverage_results) if coverage_results else None
        
        # Quality gates
        quality_gates = {
            "coverage_threshold": {
                "threshold": self.config["coverage_threshold"],
                "actual": avg_coverage,
                "passed": avg_coverage >= self.config["coverage_threshold"] if avg_coverage else False
            },
            "test_success_rate": {
                "threshold": 95.0,
                "actual": (total_passed / total_tests * 100) if total_tests > 0 else 0,
                "passed": (total_passed / total_tests * 100) >= 95.0 if total_tests > 0 else False
            }
        }
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_suites": len(results),
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "total_duration_seconds": total_duration,
                "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            "coverage": {
                "average_percentage": avg_coverage,
                "threshold_met": quality_gates["coverage_threshold"]["passed"]
            },
            "quality_gates": quality_gates,
            "suite_results": [r.to_dict() for r in results],
            "recommendations": self._generate_recommendations(results)
        }
        
        return report
    
    def _generate_recommendations(self, results: List[TestResult]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Coverage recommendations
        coverage_results = [r.coverage_percentage for r in results if r.coverage_percentage is not None]
        if coverage_results:
            avg_coverage = sum(coverage_results) / len(coverage_results)
            if avg_coverage < self.config["coverage_threshold"]:
                recommendations.append(f"Increase test coverage from {avg_coverage:.1f}% to {self.config['coverage_threshold']:.1f}%")
        
        # Performance recommendations
        slow_suites = [r for r in results if r.duration_seconds > 300]  # 5 minutes
        if slow_suites:
            recommendations.append(f"Optimize slow test suites: {', '.join(s.suite_name for s in slow_suites)}")
        
        # Failure recommendations
        failed_suites = [r for r in results if r.status == "failed"]
        if failed_suites:
            recommendations.append(f"Fix failing test suites: {', '.join(s.suite_name for s in failed_suites)}")
        
        # General recommendations
        recommendations.extend([
            "Run tests in CI/CD pipeline on every commit",
            "Set up automated performance monitoring",
            "Regular security scanning and penetration testing",
            "Monitor test execution time trends"
        ])
        
        return recommendations


class CIPipelineIntegration:
    """CI/CD Pipeline integration helpers."""
    
    @staticmethod
    def generate_github_actions_workflow() -> str:
        """Generate GitHub Actions workflow file."""
        return """
name: Comprehensive Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:6
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
        python -m pip install --upgrade pip
        pip install poetry
        poetry install
    
    - name: Run Unit Tests
      run: |
        poetry run python -m pytest tests/unit/ -v --cov=app --cov-report=xml
    
    - name: Run Integration Tests
      run: |
        poetry run python -m pytest tests/integration/ -v
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        REDIS_URL: redis://localhost:6379
    
    - name: Run Security Tests
      run: |
        poetry run python -m pytest tests/security/ -v -m security
    
    - name: Run Performance Tests
      run: |
        poetry run python -m pytest tests/performance/ -v -m performance
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  stress-test:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install poetry
        poetry install
    
    - name: Run Stress Tests
      run: |
        poetry run python tests/stress/run_stress_tests.py --profile ci
    
    - name: Upload stress test results
      uses: actions/upload-artifact@v3
      with:
        name: stress-test-results
        path: stress_test_results/
"""
    
    @staticmethod
    def generate_jenkins_pipeline() -> str:
        """Generate Jenkinsfile for Jenkins pipeline."""
        return """
pipeline {
    agent any
    
    environment {
        DATABASE_URL = 'postgresql://postgres:postgres@localhost/test_db'
        REDIS_URL = 'redis://localhost:6379'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'pip install poetry'
                sh 'poetry install'
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh 'poetry run python -m pytest tests/unit/ -v --cov=app --cov-report=xml --junit-xml=unit-results.xml'
            }
            post {
                always {
                    junit 'unit-results.xml'
                    publishCoverage adapters: [cobertura('coverage.xml')]
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                sh 'poetry run python -m pytest tests/integration/ -v --junit-xml=integration-results.xml'
            }
            post {
                always {
                    junit 'integration-results.xml'
                }
            }
        }
        
        stage('Security Tests') {
            steps {
                sh 'poetry run python -m pytest tests/security/ -v -m security --junit-xml=security-results.xml'
            }
            post {
                always {
                    junit 'security-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'security_reports',
                        reportFiles: 'security_report.html',
                        reportName: 'Security Report'
                    ])
                }
            }
        }
        
        stage('Performance Tests') {
            when {
                branch 'main'
            }
            steps {
                sh 'poetry run python -m pytest tests/performance/ -v -m performance'
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'performance_reports',
                        reportFiles: 'performance_report.html',
                        reportName: 'Performance Report'
                    ])
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        failure {
            emailext (
                subject: "Build Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Build failed. Check console output at ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
"""


class TestOrchestrationRunner:
    """Main runner for test orchestration."""
    
    def __init__(self):
        self.orchestrator = TestOrchestrator()
    
    async def run_full_suite(self, suite_selection: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run full test suite or selected suites."""
        if suite_selection is None:
            suite_selection = ["unit", "integration", "api_contract", "security", "performance"]
        
        print(f"Running test suites: {', '.join(suite_selection)}")
        
        # Run test suites
        results = await self.orchestrator.run_parallel_suites(suite_selection)
        
        # Generate comprehensive report
        report = self.orchestrator.generate_comprehensive_report(results)
        
        # Save report
        with open("comprehensive_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report
        self._generate_html_report(report)
        
        return report
    
    def _generate_html_report(self, report: Dict[str, Any]):
        """Generate HTML test report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Comprehensive Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .suite {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; }}
        .failed {{ background-color: #f8d7da; }}
        .error {{ background-color: #fff3cd; }}
        .recommendations {{ margin: 20px 0; }}
        .recommendations li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Comprehensive Test Report</h1>
        <p>Generated: {report['generated_at']}</p>
        <p>Overall Status: <strong>{report['overall_status'].upper()}</strong></p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Suites: {report['summary']['total_suites']}</p>
        <p>Total Tests: {report['summary']['total_tests']}</p>
        <p>Passed: {report['summary']['total_passed']}</p>
        <p>Failed: {report['summary']['total_failed']}</p>
        <p>Skipped: {report['summary']['total_skipped']}</p>
        <p>Success Rate: {report['summary']['success_rate']:.1f}%</p>
        <p>Total Duration: {report['summary']['total_duration_seconds']:.1f} seconds</p>
    </div>
    
    <div class="coverage">
        <h2>Coverage</h2>
        <p>Average Coverage: {report['coverage']['average_percentage']:.1f}% 
           ({'✓' if report['coverage']['threshold_met'] else '✗'} Threshold Met)</p>
    </div>
    
    <div class="suites">
        <h2>Test Suite Results</h2>
        {self._generate_suite_html(report['suite_results'])}
    </div>
    
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
        {chr(10).join(f'<li>{rec}</li>' for rec in report['recommendations'])}
        </ul>
    </div>
</body>
</html>
"""
        
        with open("comprehensive_test_report.html", "w") as f:
            f.write(html_content)
    
    def _generate_suite_html(self, suite_results: List[Dict[str, Any]]) -> str:
        """Generate HTML for suite results."""
        html_parts = []
        
        for suite in suite_results:
            status_class = suite['status']
            html_parts.append(f"""
            <div class="suite {status_class}">
                <h3>{suite['suite_name']} - {suite['status'].upper()}</h3>
                <p>Tests: {suite['tests_run']} | Passed: {suite['tests_passed']} | 
                   Failed: {suite['tests_failed']} | Skipped: {suite['tests_skipped']}</p>
                <p>Duration: {suite['duration_seconds']:.1f} seconds</p>
                {f"<p>Coverage: {suite['coverage_percentage']:.1f}%</p>" if suite['coverage_percentage'] else ""}
                {f"<div><strong>Errors:</strong><br>{'<br>'.join(suite['error_messages'][:3])}</div>" if suite['error_messages'] else ""}
            </div>
            """)
        
        return ''.join(html_parts)


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Orchestration Runner")
    parser.add_argument("--suites", nargs="+", 
                       choices=["unit", "integration", "api_contract", "security", 
                               "performance", "stress", "chaos", "e2e"],
                       help="Test suites to run")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--generate-ci", choices=["github", "jenkins"], 
                       help="Generate CI pipeline configuration")
    
    args = parser.parse_args()
    
    if args.generate_ci:
        if args.generate_ci == "github":
            print("Generating GitHub Actions workflow...")
            workflow = CIPipelineIntegration.generate_github_actions_workflow()
            with open(".github/workflows/test.yml", "w") as f:
                f.write(workflow)
            print("Generated .github/workflows/test.yml")
        elif args.generate_ci == "jenkins":
            print("Generating Jenkinsfile...")
            pipeline = CIPipelineIntegration.generate_jenkins_pipeline()
            with open("Jenkinsfile", "w") as f:
                f.write(pipeline)
            print("Generated Jenkinsfile")
    else:
        # Run tests
        async def main():
            runner = TestOrchestrationRunner()
            report = await runner.run_full_suite(args.suites)
            
            print(f"\nTest execution completed!")
            print(f"Overall Status: {report['overall_status']}")
            print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
            print(f"Total Duration: {report['summary']['total_duration_seconds']:.1f} seconds")
            print(f"Report saved to: comprehensive_test_report.html")
            
            # Exit with appropriate code
            if report['overall_status'] == 'failed':
                exit(1)
            elif report['overall_status'] == 'error':
                exit(2)
            else:
                exit(0)
        
        asyncio.run(main())
