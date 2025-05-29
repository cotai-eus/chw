"""
Performance Benchmarking and Comparison Tools

Tools for benchmarking performance and comparing results across different runs.
"""
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd


@dataclass
class BenchmarkMetrics:
    """Comprehensive benchmark metrics."""
    test_name: str
    timestamp: datetime
    duration_seconds: float
    requests_per_second: float
    average_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    success_rate_percent: float
    error_count: int
    memory_usage_mb: float
    cpu_usage_percent: float
    concurrent_users: int
    total_requests: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkMetrics':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class BenchmarkCollector:
    """Collect and store benchmark metrics."""
    
    def __init__(self, results_dir: Path = Path("benchmark_results")):
        self.results_dir = results_dir
        self.results_dir.mkdir(exist_ok=True)
        self.current_benchmarks: List[BenchmarkMetrics] = []
    
    def add_benchmark(self, metrics: BenchmarkMetrics):
        """Add benchmark metrics."""
        self.current_benchmarks.append(metrics)
        
        # Save individual benchmark
        timestamp = metrics.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"{metrics.test_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
    
    def save_batch(self, batch_name: str):
        """Save current batch of benchmarks."""
        if not self.current_benchmarks:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = self.results_dir / f"batch_{batch_name}_{timestamp}.json"
        
        batch_data = {
            'batch_name': batch_name,
            'timestamp': datetime.now().isoformat(),
            'benchmarks': [b.to_dict() for b in self.current_benchmarks]
        }
        
        with open(batch_file, 'w') as f:
            json.dump(batch_data, f, indent=2)
        
        print(f"Saved {len(self.current_benchmarks)} benchmarks to {batch_file}")
        self.current_benchmarks.clear()
    
    def load_benchmarks(self, 
                       test_name: Optional[str] = None,
                       since: Optional[datetime] = None) -> List[BenchmarkMetrics]:
        """Load benchmark metrics from storage."""
        benchmarks = []
        
        for file_path in self.results_dir.glob("*.json"):
            if file_path.name.startswith("batch_"):
                # Load batch file
                with open(file_path) as f:
                    batch_data = json.load(f)
                
                for benchmark_data in batch_data.get('benchmarks', []):
                    benchmark = BenchmarkMetrics.from_dict(benchmark_data)
                    if self._matches_filter(benchmark, test_name, since):
                        benchmarks.append(benchmark)
            else:
                # Load individual benchmark file
                try:
                    with open(file_path) as f:
                        benchmark_data = json.load(f)
                    
                    benchmark = BenchmarkMetrics.from_dict(benchmark_data)
                    if self._matches_filter(benchmark, test_name, since):
                        benchmarks.append(benchmark)
                except (json.JSONDecodeError, KeyError):
                    # Skip invalid files
                    continue
        
        return sorted(benchmarks, key=lambda b: b.timestamp)
    
    def _matches_filter(self, 
                       benchmark: BenchmarkMetrics,
                       test_name: Optional[str],
                       since: Optional[datetime]) -> bool:
        """Check if benchmark matches filter criteria."""
        if test_name and benchmark.test_name != test_name:
            return False
        
        if since and benchmark.timestamp < since:
            return False
        
        return True


class PerformanceAnalyzer:
    """Analyze performance trends and regressions."""
    
    def __init__(self, collector: BenchmarkCollector):
        self.collector = collector
    
    def analyze_trend(self, 
                     test_name: str,
                     metric: str = 'requests_per_second',
                     days: int = 30) -> Dict[str, Any]:
        """Analyze performance trend for a specific metric."""
        since = datetime.now() - timedelta(days=days)
        benchmarks = self.collector.load_benchmarks(test_name=test_name, since=since)
        
        if len(benchmarks) < 2:
            return {
                'error': f'Insufficient data for trend analysis (found {len(benchmarks)} benchmarks)'
            }
        
        # Extract metric values
        values = [getattr(b, metric) for b in benchmarks]
        timestamps = [b.timestamp for b in benchmarks]
        
        # Calculate trend statistics
        trend_analysis = {
            'test_name': test_name,
            'metric': metric,
            'period_days': days,
            'sample_count': len(benchmarks),
            'current_value': values[-1],
            'baseline_value': values[0],
            'min_value': min(values),
            'max_value': max(values),
            'average_value': statistics.mean(values),
            'median_value': statistics.median(values),
            'std_deviation': statistics.stdev(values) if len(values) > 1 else 0,
            'percentage_change': ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
            'trend_direction': self._determine_trend_direction(values),
            'regression_detected': self._detect_regression(values, metric),
            'timestamps': [t.isoformat() for t in timestamps],
            'values': values
        }
        
        return trend_analysis
    
    def compare_versions(self, 
                        test_name: str,
                        baseline_date: datetime,
                        current_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Compare performance between two versions/dates."""
        current_date = current_date or datetime.now()
        
        # Get baseline benchmark (closest to baseline_date)
        baseline_benchmarks = self.collector.load_benchmarks(test_name=test_name)
        baseline_benchmark = min(
            baseline_benchmarks,
            key=lambda b: abs((b.timestamp - baseline_date).total_seconds()),
            default=None
        )
        
        # Get current benchmark (closest to current_date)
        current_benchmark = min(
            baseline_benchmarks,
            key=lambda b: abs((b.timestamp - current_date).total_seconds()),
            default=None
        )
        
        if not baseline_benchmark or not current_benchmark:
            return {
                'error': 'Could not find benchmarks for comparison'
            }
        
        # Compare metrics
        comparison = {
            'test_name': test_name,
            'baseline': {
                'timestamp': baseline_benchmark.timestamp.isoformat(),
                'metrics': baseline_benchmark.to_dict()
            },
            'current': {
                'timestamp': current_benchmark.timestamp.isoformat(),
                'metrics': current_benchmark.to_dict()
            },
            'changes': {}
        }
        
        # Calculate percentage changes for key metrics
        key_metrics = [
            'requests_per_second',
            'average_response_time_ms',
            'p95_response_time_ms',
            'success_rate_percent',
            'memory_usage_mb',
            'cpu_usage_percent'
        ]
        
        for metric in key_metrics:
            baseline_value = getattr(baseline_benchmark, metric)
            current_value = getattr(current_benchmark, metric)
            
            if baseline_value != 0:
                change_percent = ((current_value - baseline_value) / baseline_value) * 100
                
                # Determine if change is improvement or regression
                is_improvement = self._is_improvement(metric, change_percent)
                
                comparison['changes'][metric] = {
                    'baseline_value': baseline_value,
                    'current_value': current_value,
                    'absolute_change': current_value - baseline_value,
                    'percentage_change': change_percent,
                    'is_improvement': is_improvement,
                    'is_significant': abs(change_percent) > 5.0  # 5% threshold
                }
        
        return comparison
    
    def generate_performance_report(self, 
                                  test_names: Optional[List[str]] = None,
                                  days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        since = datetime.now() - timedelta(days=days)
        
        if test_names:
            all_benchmarks = []
            for test_name in test_names:
                benchmarks = self.collector.load_benchmarks(test_name=test_name, since=since)
                all_benchmarks.extend(benchmarks)
        else:
            all_benchmarks = self.collector.load_benchmarks(since=since)
        
        if not all_benchmarks:
            return {'error': 'No benchmark data found for the specified period'}
        
        # Group by test name
        benchmarks_by_test = {}
        for benchmark in all_benchmarks:
            if benchmark.test_name not in benchmarks_by_test:
                benchmarks_by_test[benchmark.test_name] = []
            benchmarks_by_test[benchmark.test_name].append(benchmark)
        
        # Generate report for each test
        test_reports = {}
        for test_name, benchmarks in benchmarks_by_test.items():
            if len(benchmarks) > 1:
                trend = self.analyze_trend(test_name, days=days)
                test_reports[test_name] = trend
        
        # Overall summary
        latest_benchmarks = {}
        for test_name, benchmarks in benchmarks_by_test.items():
            latest_benchmarks[test_name] = max(benchmarks, key=lambda b: b.timestamp)
        
        summary = {
            'report_period_days': days,
            'total_tests': len(benchmarks_by_test),
            'total_benchmarks': len(all_benchmarks),
            'test_reports': test_reports,
            'latest_performance': {
                test_name: {
                    'timestamp': benchmark.timestamp.isoformat(),
                    'requests_per_second': benchmark.requests_per_second,
                    'average_response_time_ms': benchmark.average_response_time_ms,
                    'success_rate_percent': benchmark.success_rate_percent,
                    'memory_usage_mb': benchmark.memory_usage_mb
                }
                for test_name, benchmark in latest_benchmarks.items()
            },
            'recommendations': self._generate_performance_recommendations(test_reports)
        }
        
        return summary
    
    def _determine_trend_direction(self, values: List[float]) -> str:
        """Determine overall trend direction."""
        if len(values) < 2:
            return 'insufficient_data'
        
        # Simple linear trend analysis
        n = len(values)
        x = list(range(n))
        
        # Calculate slope using least squares
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        if abs(slope) < 0.01:  # Very small slope
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def _detect_regression(self, values: List[float], metric: str) -> bool:
        """Detect performance regression."""
        if len(values) < 3:
            return False
        
        # Compare recent values to baseline
        baseline = statistics.mean(values[:3])  # First 3 values
        recent = statistics.mean(values[-3:])   # Last 3 values
        
        if baseline == 0:
            return False
        
        change_percent = ((recent - baseline) / baseline) * 100
        
        # Define regression thresholds based on metric type
        regression_thresholds = {
            'requests_per_second': -10.0,      # 10% decrease is regression
            'average_response_time_ms': 20.0,  # 20% increase is regression
            'p95_response_time_ms': 25.0,      # 25% increase is regression
            'success_rate_percent': -5.0,      # 5% decrease is regression
            'memory_usage_mb': 30.0,           # 30% increase is regression
            'cpu_usage_percent': 25.0          # 25% increase is regression
        }
        
        threshold = regression_thresholds.get(metric, 15.0)  # Default 15%
        
        # For "higher is better" metrics, negative threshold means regression
        # For "lower is better" metrics, positive threshold means regression
        if metric in ['requests_per_second', 'success_rate_percent']:
            return change_percent < threshold
        else:
            return change_percent > threshold
    
    def _is_improvement(self, metric: str, change_percent: float) -> bool:
        """Determine if a change is an improvement."""
        # For "higher is better" metrics
        if metric in ['requests_per_second', 'success_rate_percent']:
            return change_percent > 0
        
        # For "lower is better" metrics
        if metric in ['average_response_time_ms', 'p95_response_time_ms', 
                     'p99_response_time_ms', 'memory_usage_mb', 'cpu_usage_percent']:
            return change_percent < 0
        
        return False
    
    def _generate_performance_recommendations(self, test_reports: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on analysis."""
        recommendations = []
        
        regressions = [
            test_name for test_name, report in test_reports.items()
            if report.get('regression_detected', False)
        ]
        
        if regressions:
            recommendations.append(f"Performance regressions detected in: {', '.join(regressions)}")
        
        # Check for high variability
        high_variability_tests = [
            test_name for test_name, report in test_reports.items()
            if report.get('std_deviation', 0) / report.get('average_value', 1) > 0.2  # CV > 20%
        ]
        
        if high_variability_tests:
            recommendations.append(f"High performance variability in: {', '.join(high_variability_tests)}")
        
        # Check for declining trends
        declining_tests = [
            test_name for test_name, report in test_reports.items()
            if report.get('trend_direction') == 'decreasing' and report.get('metric') == 'requests_per_second'
        ]
        
        if declining_tests:
            recommendations.append(f"Declining performance trends in: {', '.join(declining_tests)}")
        
        if not recommendations:
            recommendations.append("Performance is stable across all monitored tests")
        
        return recommendations


class PerformanceReporter:
    """Generate performance reports and visualizations."""
    
    def __init__(self, analyzer: PerformanceAnalyzer):
        self.analyzer = analyzer
    
    def create_trend_chart(self, 
                          test_name: str,
                          metric: str = 'requests_per_second',
                          days: int = 30,
                          output_file: Optional[str] = None) -> str:
        """Create trend chart for a specific metric."""
        trend_data = self.analyzer.analyze_trend(test_name, metric, days)
        
        if 'error' in trend_data:
            print(f"Cannot create chart: {trend_data['error']}")
            return ""
        
        # Create the chart
        plt.figure(figsize=(12, 6))
        
        timestamps = [datetime.fromisoformat(ts) for ts in trend_data['timestamps']]
        values = trend_data['values']
        
        plt.plot(timestamps, values, marker='o', linewidth=2, markersize=4)
        plt.title(f'{test_name} - {metric.replace("_", " ").title()} Trend', fontsize=14)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel(metric.replace('_', ' ').title(), fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Add trend line
        from scipy import stats
        x_numeric = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_numeric, values)
        trend_line = [slope * x + intercept for x in x_numeric]
        plt.plot(timestamps, trend_line, '--', color='red', alpha=0.7, label=f'Trend (R²={r_value**2:.3f})')
        
        plt.legend()
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Chart saved to: {output_file}")
        else:
            output_file = f"{test_name}_{metric}_trend.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Chart saved to: {output_file}")
        
        plt.close()
        return output_file
    
    def create_comparison_report(self, 
                               baseline_date: datetime,
                               test_names: List[str],
                               output_file: str = "performance_comparison.html") -> str:
        """Create HTML comparison report."""
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Comparison Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .improvement { color: green; font-weight: bold; }
                .regression { color: red; font-weight: bold; }
                .neutral { color: #666; }
                .significant { background-color: #fff3cd; }
            </style>
        </head>
        <body>
            <h1>Performance Comparison Report</h1>
            <p>Baseline Date: {baseline_date}</p>
            <p>Generated: {current_date}</p>
        """.format(
            baseline_date=baseline_date.strftime("%Y-%m-%d %H:%M"),
            current_date=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        
        for test_name in test_names:
            comparison = self.analyzer.compare_versions(test_name, baseline_date)
            
            if 'error' in comparison:
                html_content += f"<h2>{test_name}</h2><p>Error: {comparison['error']}</p>"
                continue
            
            html_content += f"<h2>{test_name}</h2>"
            html_content += "<table>"
            html_content += "<tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Change</th><th>Status</th></tr>"
            
            for metric, change_data in comparison['changes'].items():
                baseline_val = change_data['baseline_value']
                current_val = change_data['current_value']
                change_percent = change_data['percentage_change']
                is_improvement = change_data['is_improvement']
                is_significant = change_data['is_significant']
                
                # Format values based on metric type
                if 'percent' in metric:
                    baseline_str = f"{baseline_val:.1f}%"
                    current_str = f"{current_val:.1f}%"
                elif 'ms' in metric:
                    baseline_str = f"{baseline_val:.1f}ms"
                    current_str = f"{current_val:.1f}ms"
                elif 'mb' in metric.lower():
                    baseline_str = f"{baseline_val:.1f}MB"
                    current_str = f"{current_val:.1f}MB"
                else:
                    baseline_str = f"{baseline_val:.2f}"
                    current_str = f"{current_val:.2f}"
                
                change_str = f"{change_percent:+.1f}%"
                
                # Determine status and styling
                if is_improvement:
                    status = "Improvement"
                    status_class = "improvement"
                elif change_percent < 0 and not is_improvement:
                    status = "Regression"
                    status_class = "regression"
                else:
                    status = "Neutral"
                    status_class = "neutral"
                
                row_class = "significant" if is_significant else ""
                
                html_content += f"""
                <tr class="{row_class}">
                    <td>{metric.replace('_', ' ').title()}</td>
                    <td>{baseline_str}</td>
                    <td>{current_str}</td>
                    <td>{change_str}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
                """
            
            html_content += "</table>"
        
        html_content += "</body></html>"
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Comparison report saved to: {output_file}")
        return output_file


# Usage example
def create_comprehensive_benchmark_suite():
    """Create a comprehensive benchmarking suite."""
    collector = BenchmarkCollector()
    analyzer = PerformanceAnalyzer(collector)
    reporter = PerformanceReporter(analyzer)
    
    return collector, analyzer, reporter


if __name__ == "__main__":
    # Example usage
    collector, analyzer, reporter = create_comprehensive_benchmark_suite()
    
    # Generate performance report for last 30 days
    report = analyzer.generate_performance_report(days=30)
    print(json.dumps(report, indent=2))
