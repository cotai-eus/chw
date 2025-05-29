"""
Stress Test Runner

Main script to run comprehensive stress tests with different configurations.
"""
import asyncio
import argparse
import sys
import time
import json
import os
from pathlib import Path
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime
import psutil

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class StressTestRunner:
    """Main stress test runner with different test suites."""
    
    def __init__(self):
        self.test_suites = {
            'api': 'tests/stress/test_api_stress.py',
            'database': 'tests/stress/test_database_stress.py',
            'websocket': 'tests/stress/test_websocket_stress.py',
            'celery': 'tests/stress/test_celery_stress.py',
            'memory': 'tests/stress/test_memory_stress.py',
            'scalability': 'tests/stress/test_scalability_stress.py',
            'concurrent': 'tests/stress/test_concurrent_scenarios.py',
            'network': 'tests/stress/test_network_stress.py',
            'monitoring': 'tests/stress/test_resource_monitoring.py'
        }
        
        self.test_profiles = {
            'ci': {
                'concurrent_users': 5,
                'requests_per_user': 3,
                'duration': 10,
                'description': 'Minimal stress testing for CI/CD pipelines',
                'timeout': 60
            },
            'light': {
                'concurrent_users': 10,
                'requests_per_user': 5,
                'duration': 30,
                'description': 'Light stress testing for development',
                'timeout': 120
            },
            'medium': {
                'concurrent_users': 50,
                'requests_per_user': 10,
                'duration': 120,
                'description': 'Medium stress testing for staging validation',
                'timeout': 300
            },
            'heavy': {
                'concurrent_users': 200,
                'requests_per_user': 20,
                'duration': 300,
                'description': 'Heavy stress testing for production validation',
                'timeout': 600
            },
            'spike': {
                'concurrent_users': 500,
                'requests_per_user': 5,
                'duration': 60,
                'description': 'Spike testing for sudden load increases',
                'timeout': 180
            },
            'endurance': {
                'concurrent_users': 100,
                'requests_per_user': 100,
                'duration': 3600,  # 1 hour
                'description': 'Endurance testing for long-running stability',
                'timeout': 4200  # 70 minutes
            }
        }
        
        self.results_dir = Path("stress_test_results")
        self.results_dir.mkdir(exist_ok=True)
    
    def run_test_suite(self, 
                      suite: str, 
                      profile: str = 'medium',
                      markers: Optional[List[str]] = None,
                      verbose: bool = True) -> Dict[str, Any]:
        """Run a specific test suite with given profile."""
        
        if suite not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite}. Available: {list(self.test_suites.keys())}")
        
        if profile not in self.test_profiles:
            raise ValueError(f"Unknown profile: {profile}. Available: {list(self.test_profiles.keys())}")
        
        test_file = self.test_suites[suite]
        profile_config = self.test_profiles[profile]
        
        print(f"\n{'='*60}")
        print(f"Running {suite.upper()} stress tests")
        print(f"Profile: {profile} - {profile_config['description']}")
        print(f"Test file: {test_file}")
        print(f"{'='*60}")
        
        # Prepare pytest command
        cmd = [
            'python', '-m', 'pytest',
            test_file,
            '-v' if verbose else '-q',
            '--tb=short',
            '-x',  # Stop on first failure
            f"--timeout={profile_config.get('timeout', 300)}",
        ]
        
        # Add stress marker
        cmd.extend(['-m', 'stress'])
        
        # Add custom markers if provided
        if markers:
            for marker in markers:
                cmd.extend(['-m', marker])
        
        # Set environment variables for test configuration
        env = os.environ.copy()
        env.update({
            'STRESS_CONCURRENT_USERS': str(profile_config['concurrent_users']),
            'STRESS_REQUESTS_PER_USER': str(profile_config['requests_per_user']),
            'STRESS_DURATION': str(profile_config['duration']),
            'STRESS_PROFILE': profile
        })
        
        # Record start time and system state
        start_time = time.time()
        start_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent()
        
        try:
            # Run the test
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=profile_config.get('timeout', 300)
            )
            
            # Record end time and system state
            end_time = time.time()
            end_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
            end_cpu = psutil.cpu_percent()
            
            # Parse results
            test_result = {
                'suite': suite,
                'profile': profile,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'duration': end_time - start_time,
                'exit_code': result.returncode,
                'passed': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'system_info': {
                    'start_memory_mb': start_memory,
                    'end_memory_mb': end_memory,
                    'memory_delta_mb': end_memory - start_memory,
                    'start_cpu_percent': start_cpu,
                    'end_cpu_percent': end_cpu,
                    'cpu_cores': psutil.cpu_count(),
                    'total_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
                }
            }
            
            # Save detailed results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = self.results_dir / f"{suite}_{profile}_{timestamp}.json"
            
            with open(result_file, 'w') as f:
                json.dump(test_result, f, indent=2)
            
            print(f"\nTest completed in {test_result['duration']:.1f} seconds")
            print(f"Result: {'PASSED' if test_result['passed'] else 'FAILED'}")
            print(f"Memory usage: {test_result['system_info']['memory_delta_mb']:.1f} MB")
            print(f"Results saved to: {result_file}")
            
            if not test_result['passed']:
                print(f"\nSTDERR:")
                print(result.stderr)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            print(f"\nTest timed out after {profile_config.get('timeout', 300)} seconds")
            return {
                'suite': suite,
                'profile': profile,
                'passed': False,
                'error': 'timeout',
                'duration': profile_config.get('timeout', 300)
            }
        except Exception as e:
            print(f"\nTest failed with error: {e}")
            return {
                'suite': suite,
                'profile': profile,
                'passed': False,
                'error': str(e),
                'duration': 0
            }
    
    def run_all_suites(self, 
                      profile: str = 'medium',
                      exclude_suites: Optional[List[str]] = None,
                      include_suites: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all test suites with summary report."""
        
        exclude_suites = exclude_suites or []
        
        if include_suites:
            suites_to_run = [s for s in include_suites if s in self.test_suites]
        else:
            suites_to_run = [s for s in self.test_suites.keys() if s not in exclude_suites]
        
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE STRESS TEST EXECUTION")
        print(f"Profile: {profile}")
        print(f"Suites: {', '.join(suites_to_run)}")
        print(f"{'='*80}")
        
        overall_start = time.time()
        results = {}
        
        for suite in suites_to_run:
            try:
                result = self.run_test_suite(suite, profile)
                results[suite] = result
                
                # Brief pause between suites
                time.sleep(5)
                
            except KeyboardInterrupt:
                print(f"\nTest execution interrupted by user")
                break
            except Exception as e:
                print(f"\nError running {suite}: {e}")
                results[suite] = {
                    'suite': suite,
                    'passed': False,
                    'error': str(e)
                }
        
        overall_duration = time.time() - overall_start
        
        # Generate summary report
        summary = self._generate_summary_report(results, overall_duration, profile)
        
        # Save summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.results_dir / f"summary_{profile}_{timestamp}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        self._print_summary_report(summary)
        
        print(f"\nSummary saved to: {summary_file}")
        
        return summary
    
    def _generate_summary_report(self, 
                                results: Dict[str, Any], 
                                duration: float, 
                                profile: str) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        
        total_suites = len(results)
        passed_suites = sum(1 for r in results.values() if r.get('passed', False))
        failed_suites = total_suites - passed_suites
        
        # Calculate aggregate metrics
        total_test_duration = sum(r.get('duration', 0) for r in results.values())
        avg_memory_usage = sum(
            r.get('system_info', {}).get('memory_delta_mb', 0) 
            for r in results.values()
        ) / total_suites if total_suites > 0 else 0
        
        summary = {
            'execution_info': {
                'profile': profile,
                'start_time': datetime.now().isoformat(),
                'total_duration': duration,
                'total_test_duration': total_test_duration
            },
            'results_summary': {
                'total_suites': total_suites,
                'passed_suites': passed_suites,
                'failed_suites': failed_suites,
                'success_rate': (passed_suites / total_suites * 100) if total_suites > 0 else 0
            },
            'performance_metrics': {
                'average_memory_usage_mb': avg_memory_usage,
                'total_cpu_cores': psutil.cpu_count(),
                'total_system_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
            },
            'suite_results': results,
            'recommendations': self._generate_recommendations(results)
        }
        
        return summary
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_suites = [suite for suite, result in results.items() if not result.get('passed', False)]
        
        if failed_suites:
            recommendations.append(f"Failed suites require attention: {', '.join(failed_suites)}")
        
        # Check for high memory usage
        high_memory_suites = [
            suite for suite, result in results.items()
            if result.get('system_info', {}).get('memory_delta_mb', 0) > 500
        ]
        
        if high_memory_suites:
            recommendations.append(f"High memory usage detected in: {', '.join(high_memory_suites)}")
        
        # Check for slow tests
        slow_suites = [
            suite for suite, result in results.items()
            if result.get('duration', 0) > 300  # 5 minutes
        ]
        
        if slow_suites:
            recommendations.append(f"Performance optimization needed for: {', '.join(slow_suites)}")
        
        if not recommendations:
            recommendations.append("All tests passed within acceptable performance thresholds")
        
        return recommendations
    
    def _print_summary_report(self, summary: Dict[str, Any]):
        """Print formatted summary report."""
        print(f"\n{'='*80}")
        print(f"STRESS TEST EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        exec_info = summary['execution_info']
        results_summary = summary['results_summary']
        perf_metrics = summary['performance_metrics']
        
        print(f"Profile: {exec_info['profile']}")
        print(f"Total Duration: {exec_info['total_duration']:.1f} seconds")
        print(f"Test Duration: {exec_info['total_test_duration']:.1f} seconds")
        
        print(f"\nResults:")
        print(f"  Total Suites: {results_summary['total_suites']}")
        print(f"  Passed: {results_summary['passed_suites']}")
        print(f"  Failed: {results_summary['failed_suites']}")
        print(f"  Success Rate: {results_summary['success_rate']:.1f}%")
        
        print(f"\nPerformance:")
        print(f"  Avg Memory Usage: {perf_metrics['average_memory_usage_mb']:.1f} MB")
        print(f"  System CPU Cores: {perf_metrics['total_cpu_cores']}")
        print(f"  System Memory: {perf_metrics['total_system_memory_gb']:.1f} GB")
        
        print(f"\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
        
        print(f"\nDetailed Results:")
        for suite, result in summary['suite_results'].items():
            status = "✅ PASSED" if result.get('passed', False) else "❌ FAILED"
            duration = result.get('duration', 0)
            memory = result.get('system_info', {}).get('memory_delta_mb', 0)
            print(f"  {suite:12} {status:10} {duration:6.1f}s {memory:6.1f}MB")


def main():
    """Main entry point for stress test runner."""
    parser = argparse.ArgumentParser(description='Run comprehensive stress tests')
    
    parser.add_argument(
        '--suite', '-s',
        choices=list(StressTestRunner().test_suites.keys()) + ['all'],
        default='all',
        help='Test suite to run (default: all)'
    )
    
    parser.add_argument(
        '--profile', '-p',
        choices=list(StressTestRunner().test_profiles.keys()),
        default='medium',
        help='Test profile (default: medium)'
    )
    
    parser.add_argument(
        '--exclude', '-e',
        nargs='*',
        default=[],
        help='Test suites to exclude'
    )
    
    parser.add_argument(
        '--include', '-i',
        nargs='*',
        help='Only run these test suites'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--list-suites',
        action='store_true',
        help='List available test suites and exit'
    )
    
    parser.add_argument(
        '--list-profiles',
        action='store_true',
        help='List available test profiles and exit'
    )
    
    args = parser.parse_args()
    
    runner = StressTestRunner()
    
    if args.list_suites:
        print("Available test suites:")
        for suite in runner.test_suites:
            print(f"  {suite}")
        return
    
    if args.list_profiles:
        print("Available test profiles:")
        for profile, config in runner.test_profiles.items():
            print(f"  {profile:12} - {config['description']}")
        return
    
    try:
        if args.suite == 'all':
            result = runner.run_all_suites(
                profile=args.profile,
                exclude_suites=args.exclude,
                include_suites=args.include
            )
            
            # Exit with error code if any tests failed
            if result['results_summary']['failed_suites'] > 0:
                sys.exit(1)
        else:
            result = runner.run_test_suite(
                suite=args.suite,
                profile=args.profile,
                verbose=args.verbose
            )
            
            # Exit with error code if test failed
            if not result.get('passed', False):
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nStress test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error running stress tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
                'concurrent_users': 500,
                'requests_per_user': 5,
                'duration': 30,
                'description': 'Spike testing for auto-scaling validation'
            }
        }
    
    def run_test_suite(
        self,
        suite_name: str,
        profile: str = 'medium',
        verbose: bool = False,
        output_file: str = None
    ) -> Dict:
        """Run a specific test suite with given profile."""
        
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        if profile not in self.test_profiles:
            raise ValueError(f"Unknown test profile: {profile}")
        
        test_file = self.test_suites[suite_name]
        profile_config = self.test_profiles[profile]
        
        print(f"\\n🚀 Running {suite_name} stress tests with {profile} profile")
        print(f"📋 Profile: {profile_config['description']}")
        print(f"👥 Concurrent users: {profile_config['concurrent_users']}")
        print(f"📊 Requests per user: {profile_config['requests_per_user']}")
        print(f"⏱️  Duration: {profile_config['duration']}s")
        print("-" * 60)
        
        # Prepare pytest command
        cmd = [
            'python', '-m', 'pytest',
            test_file,
            '-m', 'stress',
            '--tb=short'
        ]
        
        if verbose:
            cmd.extend(['-v', '-s'])
        
        # Add profile-specific environment variables
        env = {
            'STRESS_CONCURRENT_USERS': str(profile_config['concurrent_users']),
            'STRESS_REQUESTS_PER_USER': str(profile_config['requests_per_user']),
            'STRESS_DURATION': str(profile_config['duration']),
            'STRESS_PROFILE': profile
        }
        
        start_time = time.time()
        
        try:
            # Run the test
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**env, **dict(os.environ)} if 'os' in globals() else env,
                timeout=profile_config['duration'] + 300  # Add 5 minutes buffer
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            test_result = {
                'suite': suite_name,
                'profile': profile,
                'duration': duration,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            # Save output if requested
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(f"Stress Test Results - {suite_name} ({profile})\\n")
                    f.write(f"Duration: {duration:.2f}s\\n")
                    f.write(f"Exit Code: {result.returncode}\\n")
                    f.write("\\nSTDOUT:\\n")
                    f.write(result.stdout)
                    f.write("\\nSTDERR:\\n")
                    f.write(result.stderr)
            
            # Print summary
            status = "✅ PASSED" if test_result['success'] else "❌ FAILED"
            print(f"\\n{status} {suite_name} stress tests completed in {duration:.2f}s")
            
            if not test_result['success']:
                print("❌ Test failures detected:")
                print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            print(f"⏰ Test suite {suite_name} timed out after {profile_config['duration'] + 300}s")
            return {
                'suite': suite_name,
                'profile': profile,
                'duration': profile_config['duration'] + 300,
                'exit_code': -1,
                'success': False,
                'error': 'Timeout'
            }
        except Exception as e:
            print(f"💥 Error running test suite {suite_name}: {e}")
            return {
                'suite': suite_name,
                'profile': profile,
                'duration': 0,
                'exit_code': -1,
                'success': False,
                'error': str(e)
            }
    
    def run_all_suites(
        self,
        profile: str = 'medium',
        verbose: bool = False,
        continue_on_failure: bool = True
    ) -> List[Dict]:
        """Run all test suites with given profile."""
        
        print(f"🎯 Running ALL stress test suites with {profile} profile")
        print("=" * 60)
        
        results = []
        failed_suites = []
        
        for suite_name in self.test_suites.keys():
            result = self.run_test_suite(suite_name, profile, verbose)
            results.append(result)
            
            if not result['success']:
                failed_suites.append(suite_name)
                if not continue_on_failure:
                    print(f"💥 Stopping due to failure in {suite_name}")
                    break
        
        # Print final summary
        print("\\n" + "=" * 60)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 60)
        
        total_duration = sum(r['duration'] for r in results)
        passed_suites = [r for r in results if r['success']]
        
        print(f"📈 Total suites run: {len(results)}")
        print(f"✅ Passed: {len(passed_suites)}")
        print(f"❌ Failed: {len(failed_suites)}")
        print(f"⏱️  Total duration: {total_duration:.2f}s")
        print(f"📋 Profile used: {profile}")
        
        if failed_suites:
            print(f"\\n❌ Failed suites: {', '.join(failed_suites)}")
        else:
            print("\\n🎉 All stress tests passed!")
        
        return results
    
    def run_custom_suite(
        self,
        suites: List[str],
        profile: str = 'medium',
        verbose: bool = False
    ) -> List[Dict]:
        """Run custom selection of test suites."""
        
        print(f"🎯 Running custom stress test suite: {', '.join(suites)}")
        print(f"📋 Profile: {profile}")
        print("=" * 60)
        
        results = []
        
        for suite_name in suites:
            if suite_name not in self.test_suites:
                print(f"⚠️  Skipping unknown suite: {suite_name}")
                continue
            
            result = self.run_test_suite(suite_name, profile, verbose)
            results.append(result)
        
        return results


def main():
    """Main entry point for stress test runner."""
    parser = argparse.ArgumentParser(description='Run stress tests for the FastAPI backend')
    
    parser.add_argument(
        'action',
        choices=['suite', 'all', 'custom', 'list'],
        help='Action to perform'
    )
    
    parser.add_argument(
        '--suite',
        choices=['api', 'database', 'websocket', 'celery', 'memory', 'scalability'],
        help='Specific test suite to run (required for "suite" action)'
    )
    
    parser.add_argument(
        '--suites',
        nargs='+',
        help='Multiple test suites to run (required for "custom" action)'
    )
    
    parser.add_argument(
        '--profile',
        choices=['light', 'medium', 'heavy', 'spike'],
        default='medium',
        help='Test profile to use (default: medium)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file for test results'
    )
    
    parser.add_argument(
        '--continue-on-failure',
        action='store_true',
        default=True,
        help='Continue running tests even if some fail'
    )
    
    args = parser.parse_args()
    
    runner = StressTestRunner()
    
    if args.action == 'list':
        print("📋 Available test suites:")
        for suite_name, test_file in runner.test_suites.items():
            print(f"  • {suite_name}: {test_file}")
        
        print("\\n📊 Available profiles:")
        for profile_name, config in runner.test_profiles.items():
            print(f"  • {profile_name}: {config['description']}")
        
        return
    
    elif args.action == 'suite':
        if not args.suite:
            print("❌ --suite argument is required for 'suite' action")
            sys.exit(1)
        
        result = runner.run_test_suite(
            args.suite,
            args.profile,
            args.verbose,
            args.output
        )
        
        sys.exit(0 if result['success'] else 1)
    
    elif args.action == 'all':
        results = runner.run_all_suites(
            args.profile,
            args.verbose,
            args.continue_on_failure
        )
        
        success = all(r['success'] for r in results)
        sys.exit(0 if success else 1)
    
    elif args.action == 'custom':
        if not args.suites:
            print("❌ --suites argument is required for 'custom' action")
            sys.exit(1)
        
        results = runner.run_custom_suite(
            args.suites,
            args.profile,
            args.verbose
        )
        
        success = all(r['success'] for r in results)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    import os
    main()
