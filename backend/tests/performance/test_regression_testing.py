"""
Performance Regression Testing

Automated performance regression detection and historical performance tracking.
"""
import pytest
import json
import time
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fastapi.testclient import TestClient

from tests.stress.benchmark_tools import BenchmarkCollector, PerformanceAnalyzer


@dataclass
class PerformanceBenchmark:
    """Represents a performance benchmark."""
    test_name: str
    endpoint: str
    method: str
    response_time_ms: float
    throughput_rps: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: datetime
    git_commit: Optional[str] = None
    environment: str = "test"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceBenchmark':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class PerformanceDatabase:
    """Database for storing and retrieving performance benchmarks."""
    
    def __init__(self, db_path: str = "performance_benchmarks.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the performance database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_name TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                response_time_ms REAL NOT NULL,
                throughput_rps REAL NOT NULL,
                memory_usage_mb REAL NOT NULL,
                cpu_usage_percent REAL NOT NULL,
                timestamp TEXT NOT NULL,
                git_commit TEXT,
                environment TEXT DEFAULT 'test',
                UNIQUE(test_name, endpoint, timestamp)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def store_benchmark(self, benchmark: PerformanceBenchmark) -> bool:
        """Store a performance benchmark."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO performance_benchmarks 
                (test_name, endpoint, method, response_time_ms, throughput_rps, 
                 memory_usage_mb, cpu_usage_percent, timestamp, git_commit, environment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                benchmark.test_name,
                benchmark.endpoint,
                benchmark.method,
                benchmark.response_time_ms,
                benchmark.throughput_rps,
                benchmark.memory_usage_mb,
                benchmark.cpu_usage_percent,
                benchmark.timestamp.isoformat(),
                benchmark.git_commit,
                benchmark.environment
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error storing benchmark: {e}")
            return False
    
    def get_historical_data(self, test_name: str, endpoint: str, 
                           days: int = 30) -> List[PerformanceBenchmark]:
        """Get historical performance data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT test_name, endpoint, method, response_time_ms, throughput_rps,
                   memory_usage_mb, cpu_usage_percent, timestamp, git_commit, environment
            FROM performance_benchmarks
            WHERE test_name = ? AND endpoint = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (test_name, endpoint, since_date))
        
        results = []
        for row in cursor.fetchall():
            benchmark_data = {
                'test_name': row[0],
                'endpoint': row[1],
                'method': row[2],
                'response_time_ms': row[3],
                'throughput_rps': row[4],
                'memory_usage_mb': row[5],
                'cpu_usage_percent': row[6],
                'timestamp': datetime.fromisoformat(row[7]),
                'git_commit': row[8],
                'environment': row[9]
            }
            results.append(PerformanceBenchmark(**benchmark_data))
        
        conn.close()
        return results
    
    def get_baseline_performance(self, test_name: str, endpoint: str) -> Optional[PerformanceBenchmark]:
        """Get baseline performance for comparison."""
        historical_data = self.get_historical_data(test_name, endpoint, days=7)
        
        if not historical_data:
            return None
        
        # Use median of last 7 days as baseline
        response_times = [b.response_time_ms for b in historical_data]
        throughputs = [b.throughput_rps for b in historical_data]
        memory_usages = [b.memory_usage_mb for b in historical_data]
        cpu_usages = [b.cpu_usage_percent for b in historical_data]
        
        return PerformanceBenchmark(
            test_name=test_name,
            endpoint=endpoint,
            method=historical_data[0].method,
            response_time_ms=statistics.median(response_times),
            throughput_rps=statistics.median(throughputs),
            memory_usage_mb=statistics.median(memory_usages),
            cpu_usage_percent=statistics.median(cpu_usages),
            timestamp=datetime.now(),
            environment="baseline"
        )


class PerformanceRegressionDetector:
    """Detects performance regressions by comparing current performance with baselines."""
    
    def __init__(self, db: PerformanceDatabase):
        self.db = db
        self.thresholds = {
            'response_time_degradation': 0.2,  # 20% increase is a regression
            'throughput_degradation': 0.15,     # 15% decrease is a regression
            'memory_increase': 0.25,            # 25% increase is a regression
            'cpu_increase': 0.2                 # 20% increase is a regression
        }
    
    def detect_regressions(self, current: PerformanceBenchmark, 
                          baseline: PerformanceBenchmark) -> Dict[str, Any]:
        """Detect performance regressions between current and baseline performance."""
        regressions = {
            'has_regression': False,
            'regressions': [],
            'improvements': [],
            'current': current.to_dict(),
            'baseline': baseline.to_dict()
        }
        
        # Check response time regression
        response_time_change = (current.response_time_ms - baseline.response_time_ms) / baseline.response_time_ms
        if response_time_change > self.thresholds['response_time_degradation']:
            regressions['has_regression'] = True
            regressions['regressions'].append({
                'metric': 'response_time',
                'change_percent': response_time_change * 100,
                'current_value': current.response_time_ms,
                'baseline_value': baseline.response_time_ms,
                'threshold': self.thresholds['response_time_degradation'] * 100
            })
        elif response_time_change < -0.1:  # 10% improvement
            regressions['improvements'].append({
                'metric': 'response_time',
                'improvement_percent': abs(response_time_change) * 100
            })
        
        # Check throughput regression
        throughput_change = (baseline.throughput_rps - current.throughput_rps) / baseline.throughput_rps
        if throughput_change > self.thresholds['throughput_degradation']:
            regressions['has_regression'] = True
            regressions['regressions'].append({
                'metric': 'throughput',
                'change_percent': throughput_change * 100,
                'current_value': current.throughput_rps,
                'baseline_value': baseline.throughput_rps,
                'threshold': self.thresholds['throughput_degradation'] * 100
            })
        elif throughput_change < -0.1:  # 10% improvement
            regressions['improvements'].append({
                'metric': 'throughput',
                'improvement_percent': abs(throughput_change) * 100
            })
        
        # Check memory regression
        memory_change = (current.memory_usage_mb - baseline.memory_usage_mb) / baseline.memory_usage_mb
        if memory_change > self.thresholds['memory_increase']:
            regressions['has_regression'] = True
            regressions['regressions'].append({
                'metric': 'memory_usage',
                'change_percent': memory_change * 100,
                'current_value': current.memory_usage_mb,
                'baseline_value': baseline.memory_usage_mb,
                'threshold': self.thresholds['memory_increase'] * 100
            })
        elif memory_change < -0.1:  # 10% improvement
            regressions['improvements'].append({
                'metric': 'memory_usage',
                'improvement_percent': abs(memory_change) * 100
            })
        
        # Check CPU regression
        cpu_change = (current.cpu_usage_percent - baseline.cpu_usage_percent) / baseline.cpu_usage_percent
        if cpu_change > self.thresholds['cpu_increase']:
            regressions['has_regression'] = True
            regressions['regressions'].append({
                'metric': 'cpu_usage',
                'change_percent': cpu_change * 100,
                'current_value': current.cpu_usage_percent,
                'baseline_value': baseline.cpu_usage_percent,
                'threshold': self.thresholds['cpu_increase'] * 100
            })
        elif cpu_change < -0.1:  # 10% improvement
            regressions['improvements'].append({
                'metric': 'cpu_usage',
                'improvement_percent': abs(cpu_change) * 100
            })
        
        return regressions


class PerformanceReportGenerator:
    """Generates performance regression reports and visualizations."""
    
    def __init__(self, db: PerformanceDatabase):
        self.db = db
    
    def generate_trend_chart(self, test_name: str, endpoint: str, 
                           metric: str, days: int = 30) -> str:
        """Generate a trend chart for a specific metric."""
        historical_data = self.db.get_historical_data(test_name, endpoint, days)
        
        if not historical_data:
            return ""
        
        # Prepare data for plotting
        timestamps = [b.timestamp for b in historical_data]
        values = []
        
        for benchmark in historical_data:
            if metric == 'response_time':
                values.append(benchmark.response_time_ms)
            elif metric == 'throughput':
                values.append(benchmark.throughput_rps)
            elif metric == 'memory_usage':
                values.append(benchmark.memory_usage_mb)
            elif metric == 'cpu_usage':
                values.append(benchmark.cpu_usage_percent)
        
        # Create the chart
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, values, marker='o', linewidth=2, markersize=4)
        plt.title(f'{metric.replace("_", " ").title()} Trend - {endpoint}')
        plt.xlabel('Date')
        plt.ylabel(metric.replace("_", " ").title())
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save chart
        chart_path = f"performance_trend_{test_name}_{metric}.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def generate_regression_report(self, regressions: List[Dict[str, Any]]) -> str:
        """Generate a detailed regression report."""
        report = []
        report.append("# Performance Regression Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        if not any(r['has_regression'] for r in regressions):
            report.append("✅ **No performance regressions detected!**")
            report.append("")
        else:
            report.append("⚠️ **Performance regressions detected:**")
            report.append("")
        
        for regression in regressions:
            test_name = regression['current']['test_name']
            endpoint = regression['current']['endpoint']
            
            report.append(f"## {test_name} - {endpoint}")
            
            if regression['has_regression']:
                report.append("### 🔴 Regressions:")
                for reg in regression['regressions']:
                    report.append(f"- **{reg['metric']}**: {reg['change_percent']:.1f}% degradation "
                                f"(threshold: {reg['threshold']:.1f}%)")
                    report.append(f"  - Current: {reg['current_value']:.2f}")
                    report.append(f"  - Baseline: {reg['baseline_value']:.2f}")
            
            if regression['improvements']:
                report.append("### 🟢 Improvements:")
                for imp in regression['improvements']:
                    report.append(f"- **{imp['metric']}**: {imp['improvement_percent']:.1f}% improvement")
            
            if not regression['has_regression'] and not regression['improvements']:
                report.append("### ✅ No significant changes")
            
            report.append("")
        
        return "\n".join(report)


class TestPerformanceRegression:
    """Performance regression testing suite."""
    
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, authenticated_user):
        self.client = client
        self.authenticated_user = authenticated_user
        self.db = PerformanceDatabase("test_performance.db")
        self.detector = PerformanceRegressionDetector(self.db)
        self.collector = BenchmarkCollector()
    
    def run_performance_test(self, test_name: str, endpoint: str, 
                           method: str = "GET", iterations: int = 10) -> PerformanceBenchmark:
        """Run a performance test and collect metrics."""
        import psutil
        import subprocess
        
        # Get current git commit
        try:
            git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
        except Exception:
            git_commit = None
        
        response_times = []
        memory_before = psutil.virtual_memory().used / 1024 / 1024  # MB
        cpu_before = psutil.cpu_percent()
        
        # Run test iterations
        for _ in range(iterations):
            start_time = time.time()
            
            if method.upper() == "GET":
                if "users" in endpoint:
                    response = self.client.get(endpoint)
                else:
                    response = self.client.get(
                        endpoint,
                        headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
                    )
            elif method.upper() == "POST":
                # Add appropriate test data based on endpoint
                test_data = self._get_test_data_for_endpoint(endpoint)
                response = self.client.post(
                    endpoint,
                    json=test_data,
                    headers={"Authorization": f"Bearer {self.authenticated_user['token']}"}
                )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            response_times.append(response_time)
            
            # Verify response is successful
            assert response.status_code in [200, 201], f"Request failed: {response.status_code}"
        
        memory_after = psutil.virtual_memory().used / 1024 / 1024  # MB
        cpu_after = psutil.cpu_percent()
        
        # Calculate metrics
        avg_response_time = statistics.mean(response_times)
        throughput = iterations / (sum(response_times) / 1000)  # RPS
        memory_usage = memory_after - memory_before
        cpu_usage = cpu_after - cpu_before
        
        return PerformanceBenchmark(
            test_name=test_name,
            endpoint=endpoint,
            method=method,
            response_time_ms=avg_response_time,
            throughput_rps=throughput,
            memory_usage_mb=max(memory_usage, 0),  # Ensure non-negative
            cpu_usage_percent=max(cpu_usage, 0),   # Ensure non-negative
            timestamp=datetime.now(),
            git_commit=git_commit
        )
    
    def _get_test_data_for_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Get test data for POST endpoints."""
        if "users" in endpoint:
            return {
                "email": f"test{int(time.time())}@example.com",
                "full_name": "Test User",
                "password": "testpassword123"
            }
        elif "tenders" in endpoint:
            return {
                "title": f"Test Tender {int(time.time())}",
                "description": "Test tender description",
                "deadline": (datetime.now() + timedelta(days=30)).isoformat(),
                "requirements": "Test requirements"
            }
        elif "quotes" in endpoint:
            return {
                "tender_id": 1,
                "amount": 10000.00,
                "currency": "USD",
                "proposal": "Test proposal"
            }
        
        return {}
    
    @pytest.mark.performance
    def test_users_endpoint_performance(self):
        """Test and track performance of users endpoint."""
        current = self.run_performance_test("users_list", "/api/v1/users/")
        
        # Store current performance
        self.db.store_benchmark(current)
        
        # Get baseline and check for regressions
        baseline = self.db.get_baseline_performance("users_list", "/api/v1/users/")
        
        if baseline:
            regression_result = self.detector.detect_regressions(current, baseline)
            
            if regression_result['has_regression']:
                # Generate detailed report
                report_gen = PerformanceReportGenerator(self.db)
                report = report_gen.generate_regression_report([regression_result])
                
                # Save report
                with open("performance_regression_report.md", "w") as f:
                    f.write(report)
                
                # Fail test if regression detected
                pytest.fail(f"Performance regression detected in users endpoint: {regression_result['regressions']}")
    
    @pytest.mark.performance
    def test_tenders_endpoint_performance(self):
        """Test and track performance of tenders endpoint."""
        current = self.run_performance_test("tenders_list", "/api/v1/tenders/")
        
        # Store current performance
        self.db.store_benchmark(current)
        
        # Check for regressions
        baseline = self.db.get_baseline_performance("tenders_list", "/api/v1/tenders/")
        
        if baseline:
            regression_result = self.detector.detect_regressions(current, baseline)
            
            if regression_result['has_regression']:
                pytest.fail(f"Performance regression detected in tenders endpoint: {regression_result['regressions']}")
    
    @pytest.mark.performance
    def test_quotes_endpoint_performance(self):
        """Test and track performance of quotes endpoint."""
        current = self.run_performance_test("quotes_list", "/api/v1/quotes/")
        
        # Store current performance
        self.db.store_benchmark(current)
        
        # Check for regressions
        baseline = self.db.get_baseline_performance("quotes_list", "/api/v1/quotes/")
        
        if baseline:
            regression_result = self.detector.detect_regressions(current, baseline)
            
            if regression_result['has_regression']:
                pytest.fail(f"Performance regression detected in quotes endpoint: {regression_result['regressions']}")
    
    @pytest.mark.performance
    def test_create_operations_performance(self):
        """Test and track performance of create operations."""
        endpoints = [
            ("users_create", "/api/v1/users/", "POST"),
            ("tenders_create", "/api/v1/tenders/", "POST"),
        ]
        
        regressions = []
        
        for test_name, endpoint, method in endpoints:
            current = self.run_performance_test(test_name, endpoint, method, iterations=5)
            self.db.store_benchmark(current)
            
            baseline = self.db.get_baseline_performance(test_name, endpoint)
            if baseline:
                regression_result = self.detector.detect_regressions(current, baseline)
                if regression_result['has_regression']:
                    regressions.append(regression_result)
        
        if regressions:
            # Generate comprehensive report for all regressions
            report_gen = PerformanceReportGenerator(self.db)
            report = report_gen.generate_regression_report(regressions)
            
            with open("create_operations_regression_report.md", "w") as f:
                f.write(report)
            
            pytest.fail(f"Performance regressions detected in create operations: {len(regressions)} endpoints affected")
    
    def test_generate_performance_trends(self):
        """Generate performance trend reports."""
        report_gen = PerformanceReportGenerator(self.db)
        
        endpoints = [
            ("users_list", "/api/v1/users/"),
            ("tenders_list", "/api/v1/tenders/"),
            ("quotes_list", "/api/v1/quotes/")
        ]
        
        metrics = ["response_time", "throughput", "memory_usage", "cpu_usage"]
        
        for test_name, endpoint in endpoints:
            for metric in metrics:
                try:
                    chart_path = report_gen.generate_trend_chart(test_name, endpoint, metric, days=7)
                    if chart_path:
                        print(f"Generated trend chart: {chart_path}")
                except Exception as e:
                    print(f"Failed to generate chart for {test_name}/{metric}: {e}")
    
    @pytest.mark.performance
    def test_performance_budget_compliance(self):
        """Test that endpoints comply with performance budgets."""
        performance_budgets = {
            "/api/v1/users/": {"response_time_ms": 500, "throughput_rps": 100},
            "/api/v1/tenders/": {"response_time_ms": 1000, "throughput_rps": 50},
            "/api/v1/quotes/": {"response_time_ms": 800, "throughput_rps": 75}
        }
        
        violations = []
        
        for endpoint, budget in performance_budgets.items():
            test_name = endpoint.split('/')[-2] + "_budget_test"
            current = self.run_performance_test(test_name, endpoint)
            
            if current.response_time_ms > budget["response_time_ms"]:
                violations.append(f"{endpoint}: Response time {current.response_time_ms:.2f}ms exceeds budget {budget['response_time_ms']}ms")
            
            if current.throughput_rps < budget["throughput_rps"]:
                violations.append(f"{endpoint}: Throughput {current.throughput_rps:.2f} RPS below budget {budget['throughput_rps']} RPS")
        
        if violations:
            pytest.fail(f"Performance budget violations: {'; '.join(violations)}")
