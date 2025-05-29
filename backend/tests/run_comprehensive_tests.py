#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner

Orchestrates and runs all test categories in the advanced testing infrastructure.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import json


class ComprehensiveTestRunner:
    """Runs all test categories with comprehensive reporting."""
    
    def __init__(self):
        self.test_categories = {
            'unit': {
                'path': 'tests/unit/',
                'description': 'Unit tests for individual components',
                'marker': 'unit',
                'timeout': 300
            },
            'integration': {
                'path': 'tests/integration/',
                'description': 'Integration tests including database migrations',
                'marker': 'integration',
                'timeout': 600
            },
            'api_contracts': {
                'path': 'tests/api_docs/test_contract_testing.py',
                'description': 'API contract and compatibility testing',
                'marker': 'contract',
                'timeout': 300
            },
            'security': {
                'path': 'tests/security/test_advanced_security.py',
                'description': 'Advanced security vulnerability testing',
                'marker': 'security',
                'timeout': 600
            },
            'performance_regression': {
                'path': 'tests/performance/test_regression_testing.py',
                'description': 'Performance regression detection',
                'marker': 'performance',
                'timeout': 900
            },
            'chaos_engineering': {
                'path': 'tests/stress/test_chaos_engineering.py',
                'description': 'Chaos engineering resilience tests',
                'marker': 'chaos',
                'timeout': 1200
            },
            'stress': {
                'path': 'tests/stress/',
                'description': 'High-concurrency stress testing',
                'marker': 'stress',
                'timeout': 1800
            }
        }
        
        self.results_dir = Path("comprehensive_test_results")
        self.results_dir.mkdir(exist_ok=True)
    
    def run_test_category(self, category: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific test category."""
        print(f"\n{'='*60}")
        print(f"Running {category.upper()} tests")
        print(f"Description: {config['description']}")
        print(f"Path: {config['path']}")
        print(f"{'='*60}")
        
        # Prepare pytest command
        cmd = [
            'python3', '-m', 'pytest',
            config['path'],
            '-v',
            '--tb=short',
            f'--timeout={config["timeout"]}',
            '--maxfail=5'  # Stop after 5 failures per category
        ]
        
        # Add marker if specified
        if config.get('marker'):
            cmd.extend(['-m', config['marker']])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config['timeout']
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            test_result = {
                'category': category,
                'passed': result.returncode == 0,
                'duration': duration,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timeout': config['timeout']
            }
            
            status = "✅ PASSED" if test_result['passed'] else "❌ FAILED"
            print(f"\nResult: {status}")
            print(f"Duration: {duration:.1f}s")
            
            if not test_result['passed']:
                print(f"Exit code: {result.returncode}")
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr[:1000])  # Limit output
            
            return test_result
            
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT after {config['timeout']}s")
            return {
                'category': category,
                'passed': False,
                'duration': config['timeout'],
                'exit_code': -1,
                'error': 'timeout',
                'timeout': config['timeout']
            }
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return {
                'category': category,
                'passed': False,
                'duration': 0,
                'exit_code': -1,
                'error': str(e),
                'timeout': config['timeout']
            }
    
    def run_all_tests(self, categories: List[str] = None) -> Dict[str, Any]:
        """Run all or specified test categories."""
        if categories is None:
            categories = list(self.test_categories.keys())
        
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE TEST SUITE EXECUTION")
        print(f"Categories: {', '.join(categories)}")
        print(f"{'='*80}")
        
        overall_start = time.time()
        results = {}
        
        for category in categories:
            if category not in self.test_categories:
                print(f"⚠️  Unknown category: {category}")
                continue
            
            config = self.test_categories[category]
            result = self.run_test_category(category, config)
            results[category] = result
            
            # Brief pause between categories
            time.sleep(2)
        
        overall_duration = time.time() - overall_start
        
        # Generate summary
        summary = self._generate_summary(results, overall_duration)
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"comprehensive_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        self._print_summary(summary)
        
        print(f"\nResults saved to: {results_file}")
        
        return summary
    
    def _generate_summary(self, results: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        total_categories = len(results)
        passed_categories = sum(1 for r in results.values() if r.get('passed', False))
        failed_categories = total_categories - passed_categories
        
        total_test_duration = sum(r.get('duration', 0) for r in results.values())
        
        return {
            'execution_info': {
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_duration': duration,
                'total_test_duration': total_test_duration
            },
            'results_summary': {
                'total_categories': total_categories,
                'passed_categories': passed_categories,
                'failed_categories': failed_categories,
                'success_rate': (passed_categories / total_categories * 100) if total_categories > 0 else 0
            },
            'category_results': results,
            'recommendations': self._generate_recommendations(results)
        }
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_categories = [cat for cat, result in results.items() if not result.get('passed', False)]
        
        if failed_categories:
            recommendations.append(f"Failed categories require attention: {', '.join(failed_categories)}")
        
        # Check for timeouts
        timeout_categories = [cat for cat, result in results.items() if result.get('error') == 'timeout']
        if timeout_categories:
            recommendations.append(f"Timeout issues in: {', '.join(timeout_categories)} - consider increasing timeout or optimizing tests")
        
        # Check for slow categories
        slow_categories = [
            cat for cat, result in results.items()
            if result.get('duration', 0) > 600  # 10 minutes
        ]
        if slow_categories:
            recommendations.append(f"Slow test execution in: {', '.join(slow_categories)} - consider optimization")
        
        if not recommendations:
            recommendations.append("All test categories passed successfully!")
        
        return recommendations
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print formatted summary report."""
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE TEST EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        exec_info = summary['execution_info']
        results_summary = summary['results_summary']
        
        print(f"Timestamp: {exec_info['timestamp']}")
        print(f"Total Duration: {exec_info['total_duration']:.1f}s")
        print(f"Test Duration: {exec_info['total_test_duration']:.1f}s")
        
        print(f"\nResults:")
        print(f"  Total Categories: {results_summary['total_categories']}")
        print(f"  Passed: {results_summary['passed_categories']}")
        print(f"  Failed: {results_summary['failed_categories']}")
        print(f"  Success Rate: {results_summary['success_rate']:.1f}%")
        
        print(f"\nCategory Details:")
        for category, result in summary['category_results'].items():
            status = "✅ PASSED" if result.get('passed', False) else "❌ FAILED"
            duration = result.get('duration', 0)
            print(f"  {category:20} {status:10} {duration:6.1f}s")
        
        print(f"\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive test suite')
    parser.add_argument(
        '--categories', '-c',
        nargs='+',
        choices=list(ComprehensiveTestRunner().test_categories.keys()),
        help='Test categories to run (default: all)'
    )
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List available test categories'
    )
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    if args.list_categories:
        print("Available test categories:")
        for category, config in runner.test_categories.items():
            print(f"  {category:20} - {config['description']}")
        return
    
    try:
        results = runner.run_all_tests(args.categories)
        
        # Exit with error code if any tests failed
        if results['results_summary']['failed_categories'] > 0:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error running comprehensive tests: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
