#!/usr/bin/env python3
"""
Test Manager - Consolidated Test Execution and Management

Centralized manager for all test operations, replacing multiple scattered files.
"""
import os
import sys
import time
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

# Add the project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.config.test_config import (
    ComprehensiveTestConfig, TestCategory, TestEnvironment,
    get_test_config, get_quality_gates
)


@dataclass
class TestResult:
    """Test execution result."""
    category: str
    success: bool
    duration: float
    output: str
    error: Optional[str] = None
    metrics: Dict[str, Any] = None


class TestManager:
    """Comprehensive test management system."""
    
    def __init__(self, environment: TestEnvironment = TestEnvironment.LOCAL):
        self.config = ComprehensiveTestConfig(environment)
        self.results_dir = Path("comprehensive_test_results")
        self.results_dir.mkdir(exist_ok=True)
        self.execution_start_time = None
        self.results: Dict[str, TestResult] = {}
    
    def validate_infrastructure(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate the testing infrastructure."""
        print("🔍 Validating Testing Infrastructure...")
        
        validation_results = {
            "dependencies": self._validate_dependencies(),
            "structure": self._validate_structure(),
            "configs": self._validate_configurations(),
            "files": self._validate_test_files()
        }
        
        all_valid = all(validation_results.values())
        
        print(f"\n📊 Validation Summary:")
        for component, valid in validation_results.items():
            status = "✅ VALID" if valid else "❌ INVALID"
            print(f"  {component.capitalize()}: {status}")
        
        return all_valid, validation_results
    
    def _validate_dependencies(self) -> bool:
        """Validate all required dependencies."""
        print("\n  Checking dependencies...")
        
        required_packages = [
            'pytest', 'jsonschema', 'matplotlib', 'seaborn',
            'numpy', 'pandas', 'psutil', 'httpx', 'aiohttp',
            'faker', 'locust'
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"    ✅ {package}")
            except ImportError:
                print(f"    ❌ {package}")
                missing.append(package)
        
        if missing:
            print(f"    Missing: {', '.join(missing)}")
            return False
        
        return True
    
    def _validate_structure(self) -> bool:
        """Validate test directory structure."""
        print("\n  Checking directory structure...")
        
        expected_dirs = [
            'tests/unit', 'tests/integration', 'tests/api_docs',
            'tests/security', 'tests/performance', 'tests/stress',
            'tests/e2e', 'tests/monitoring', 'tests/tools',
            'tests/config', 'tests/fixtures', 'tests/helpers'
        ]
        
        missing = []
        for test_dir in expected_dirs:
            if Path(test_dir).exists():
                print(f"    ✅ {test_dir}")
            else:
                print(f"    ❌ {test_dir}")
                missing.append(test_dir)
        
        return len(missing) == 0
    
    def _validate_configurations(self) -> bool:
        """Validate test configurations."""
        print("\n  Checking configurations...")
        
        config_files = [
            'pyproject.toml',
            'tests/conftest.py',
            'tests/config/test_config.py'
        ]
        
        valid = True
        for config_file in config_files:
            if Path(config_file).exists():
                print(f"    ✅ {config_file}")
            else:
                print(f"    ❌ {config_file}")
                valid = False
        
        return valid
    
    def _validate_test_files(self) -> bool:
        """Validate test file syntax."""
        print("\n  Checking test file syntax...")
        
        test_files = []
        for category in self.config.categories.values():
            test_path = Path(category.path)
            if test_path.exists():
                test_files.extend(test_path.glob("test_*.py"))
        
        invalid_files = []
        for test_file in test_files:
            try:
                compile(test_file.read_text(), test_file, 'exec')
                print(f"    ✅ {test_file}")
            except SyntaxError as e:
                print(f"    ❌ {test_file}: {e}")
                invalid_files.append(test_file)
        
        return len(invalid_files) == 0
    
    def list_categories(self) -> None:
        """List all available test categories."""
        print("📚 Available Test Categories:")
        print("=" * 50)
        
        for category, config in self.config.categories.items():
            status = "✅ Enabled" if config.enabled else "❌ Disabled"
            parallel = "🔄 Parallel" if config.parallel else "⏳ Sequential"
            
            print(f"  {category.value:20} - {config.description}")
            print(f"    Path: {config.path}")
            print(f"    Status: {status} | Execution: {parallel}")
            print(f"    Timeout: {config.timeout_seconds}s")
            
            if config.dependencies:
                missing_deps = self.config.validate_dependencies(category)
                if missing_deps:
                    print(f"    ⚠️  Missing dependencies: {', '.join(missing_deps)}")
            print()
    
    def run_category(self, category: TestCategory, verbose: bool = False) -> TestResult:
        """Run tests for a specific category."""
        config = self.config.get_category_config(category)
        if not config:
            raise ValueError(f"Unknown test category: {category}")
        
        print(f"\n{'='*60}")
        print(f"Running {config.name}")
        print(f"Description: {config.description}")
        print(f"Path: {config.path}")
        print(f"{'='*60}")
        
        # Validate dependencies
        missing_deps = self.config.validate_dependencies(category)
        if missing_deps:
            error_msg = f"Missing dependencies: {', '.join(missing_deps)}"
            print(f"❌ {error_msg}")
            return TestResult(
                category=category.value,
                success=False,
                duration=0.0,
                output="",
                error=error_msg
            )
        
        # Prepare environment
        env = os.environ.copy()
        env.update(self.config.get_environment_setup(category))
        
        # Prepare pytest command
        pytest_args = self.config.get_pytest_args(category)
        cmd = ['poetry', 'run', 'pytest'] + pytest_args
        
        if verbose:
            print(f"Command: {' '.join(cmd)}")
            print(f"Environment vars: {self.config.get_environment_setup(category)}")
        
        # Execute tests
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                env=env,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            output = result.stdout + result.stderr
            
            if verbose or not success:
                print(output)
            
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\nResult: {status} ({duration:.1f}s)")
            
            return TestResult(
                category=category.value,
                success=success,
                duration=duration,
                output=output,
                error=result.stderr if result.stderr else None
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Test timeout after {config.timeout_seconds}s"
            print(f"❌ {error_msg}")
            
            return TestResult(
                category=category.value,
                success=False,
                duration=duration,
                output="",
                error=error_msg
            )
        
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Execution error: {str(e)}"
            print(f"❌ {error_msg}")
            
            return TestResult(
                category=category.value,
                success=False,
                duration=duration,
                output="",
                error=error_msg
            )
    
    def run_multiple_categories(
        self, 
        categories: List[TestCategory], 
        parallel: bool = True,
        verbose: bool = False
    ) -> Dict[str, TestResult]:
        """Run multiple test categories."""
        if not categories:
            categories = self.config.get_enabled_categories()
        
        self.execution_start_time = time.time()
        results = {}
        
        if parallel:
            # Run parallel categories in parallel, sequential ones sequentially
            parallel_cats = [cat for cat in categories if self.config.get_category_config(cat).parallel]
            sequential_cats = [cat for cat in categories if not self.config.get_category_config(cat).parallel]
            
            # Run parallel categories
            if parallel_cats:
                print(f"\n🔄 Running {len(parallel_cats)} categories in parallel...")
                with ThreadPoolExecutor(max_workers=min(len(parallel_cats), 4)) as executor:
                    future_to_category = {
                        executor.submit(self.run_category, cat, verbose): cat 
                        for cat in parallel_cats
                    }
                    
                    for future in as_completed(future_to_category):
                        category = future_to_category[future]
                        try:
                            result = future.result()
                            results[category.value] = result
                        except Exception as e:
                            results[category.value] = TestResult(
                                category=category.value,
                                success=False,
                                duration=0.0,
                                output="",
                                error=str(e)
                            )
            
            # Run sequential categories
            for category in sequential_cats:
                result = self.run_category(category, verbose)
                results[category.value] = result
        
        else:
            # Run all categories sequentially
            for category in categories:
                result = self.run_category(category, verbose)
                results[category.value] = result
        
        self.results.update(results)
        return results
    
    def generate_report(self, results: Dict[str, TestResult]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_duration = time.time() - (self.execution_start_time or time.time())
        
        passed = sum(1 for r in results.values() if r.success)
        failed = len(results) - passed
        success_rate = (passed / len(results) * 100) if results else 0
        
        report = {
            "execution_info": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_duration": total_duration,
                "environment": self.config.environment.value
            },
            "summary": {
                "total_categories": len(results),
                "passed": passed,
                "failed": failed,
                "success_rate": success_rate
            },
            "category_results": {
                name: {
                    "success": result.success,
                    "duration": result.duration,
                    "error": result.error
                }
                for name, result in results.items()
            },
            "quality_gates": self._evaluate_quality_gates(results),
            "recommendations": self._generate_recommendations(results)
        }
        
        # Save report
        report_file = self.results_dir / f"test_report_{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _evaluate_quality_gates(self, results: Dict[str, TestResult]) -> Dict[str, Any]:
        """Evaluate quality gates against results."""
        gates = get_quality_gates()
        evaluation = {}
        
        for gate_name, criteria in gates.items():
            # Find matching category result
            category_result = None
            for cat_name, result in results.items():
                if gate_name in cat_name or cat_name in gate_name:
                    category_result = result
                    break
            
            if category_result:
                evaluation[gate_name] = {
                    "passed": category_result.success,
                    "criteria_met": category_result.success,  # Simplified evaluation
                    "details": criteria
                }
            else:
                evaluation[gate_name] = {
                    "passed": False,
                    "criteria_met": False,
                    "details": "Category not executed"
                }
        
        return evaluation
    
    def _generate_recommendations(self, results: Dict[str, TestResult]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [name for name, result in results.items() if not result.success]
        
        if failed_tests:
            recommendations.append(f"Investigate and fix {len(failed_tests)} failed test categories")
        
        slow_tests = [
            name for name, result in results.items() 
            if result.duration > 300  # 5 minutes
        ]
        
        if slow_tests:
            recommendations.append("Consider optimizing slow test categories for better CI performance")
        
        if not results:
            recommendations.append("No tests were executed - verify test configuration")
        
        if all(result.success for result in results.values()):
            recommendations.append("All tests passed! Consider adding more comprehensive test coverage")
        
        return recommendations
    
    def print_summary(self, results: Dict[str, TestResult]) -> None:
        """Print execution summary."""
        total_duration = time.time() - (self.execution_start_time or time.time())
        
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        passed = sum(1 for r in results.values() if r.success)
        failed = len(results) - passed
        success_rate = (passed / len(results) * 100) if results else 0
        
        print(f"Execution Time: {total_duration:.1f}s")
        print(f"Categories: {len(results)} | Passed: {passed} | Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"\nCategory Results:")
        for name, result in results.items():
            status = "✅ PASSED" if result.success else "❌ FAILED"
            print(f"  {name:20} {status:10} {result.duration:6.1f}s")
            if result.error:
                print(f"    Error: {result.error}")
        
        quality_gates = self._evaluate_quality_gates(results)
        passed_gates = sum(1 for gate in quality_gates.values() if gate["passed"])
        
        print(f"\nQuality Gates: {passed_gates}/{len(quality_gates)} passed")
        
        recommendations = self._generate_recommendations(results)
        if recommendations:
            print(f"\nRecommendations:")
            for rec in recommendations:
                print(f"  • {rec}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Comprehensive Test Manager")
    
    parser.add_argument(
        "--validate", 
        action="store_true",
        help="Validate testing infrastructure"
    )
    
    parser.add_argument(
        "--list", 
        action="store_true",
        help="List available test categories"
    )
    
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        choices=[cat.value for cat in TestCategory],
        help="Test categories to run"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel where possible"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--environment", "-e",
        choices=[env.value for env in TestEnvironment],
        default=TestEnvironment.LOCAL.value,
        help="Test environment"
    )
    
    args = parser.parse_args()
    
    # Initialize test manager
    environment = TestEnvironment(args.environment)
    manager = TestManager(environment)
    
    if args.validate:
        valid, details = manager.validate_infrastructure()
        if not valid:
            print("\n❌ Infrastructure validation failed!")
            sys.exit(1)
        else:
            print("\n✅ Infrastructure validation passed!")
            return
    
    if args.list:
        manager.list_categories()
        return
    
    if args.categories:
        categories = [TestCategory(cat) for cat in args.categories]
    else:
        categories = manager.config.get_enabled_categories()
    
    if not categories:
        print("No test categories specified or enabled.")
        return
    
    try:
        results = manager.run_multiple_categories(
            categories, 
            parallel=args.parallel,
            verbose=args.verbose
        )
        
        manager.print_summary(results)
        report = manager.generate_report(results)
        
        # Exit with error if any tests failed
        failed_count = sum(1 for r in results.values() if not r.success)
        if failed_count > 0:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
