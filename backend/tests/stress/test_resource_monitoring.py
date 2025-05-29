"""
Resource Monitoring and Bottleneck Detection Tests

Advanced monitoring for resource usage and bottleneck identification during stress tests.
"""
import asyncio
import psutil
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import pytest
from httpx import AsyncClient

from tests.stress.conftest import StressTestRunner, StressTestConfig
from app.main import app


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    open_files: int
    connections: int


@dataclass
class BottleneckAnalysis:
    """Analysis of potential bottlenecks."""
    resource_type: str
    severity: str  # low, medium, high, critical
    max_usage: float
    avg_usage: float
    threshold_breached: bool
    recommendations: List[str] = field(default_factory=list)


class ResourceMonitor:
    """Advanced resource monitoring during stress tests."""
    
    def __init__(self, sample_interval: float = 0.5):
        self.sample_interval = sample_interval
        self.snapshots: List[ResourceSnapshot] = []
        self.monitoring = False
        self.process = psutil.Process()
    
    async def start_monitoring(self):
        """Start continuous resource monitoring."""
        self.monitoring = True
        self.snapshots.clear()
        
        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                await asyncio.sleep(self.sample_interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                break
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
    
    def _take_snapshot(self) -> ResourceSnapshot:
        """Take a snapshot of current resource usage."""
        # CPU and memory
        cpu_percent = self.process.cpu_percent()
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        # Disk I/O
        try:
            disk_io = self.process.io_counters()
            disk_read = disk_io.read_bytes
            disk_write = disk_io.write_bytes
        except (AttributeError, psutil.AccessDenied):
            disk_read = disk_write = 0
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            net_sent = net_io.bytes_sent
            net_recv = net_io.bytes_recv
        except (AttributeError, psutil.AccessDenied):
            net_sent = net_recv = 0
        
        # File descriptors and connections
        try:
            open_files = self.process.num_fds()
        except (AttributeError, psutil.AccessDenied):
            open_files = 0
        
        try:
            connections = len(self.process.connections())
        except (AttributeError, psutil.AccessDenied):
            connections = 0
        
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            disk_io_read=disk_read,
            disk_io_write=disk_write,
            network_io_sent=net_sent,
            network_io_recv=net_recv,
            open_files=open_files,
            connections=connections
        )
    
    def analyze_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Analyze collected data for bottlenecks."""
        if not self.snapshots:
            return []
        
        analyses = []
        
        # CPU Analysis
        cpu_values = [s.cpu_percent for s in self.snapshots]
        cpu_max = max(cpu_values)
        cpu_avg = sum(cpu_values) / len(cpu_values)
        
        cpu_analysis = BottleneckAnalysis(
            resource_type="CPU",
            max_usage=cpu_max,
            avg_usage=cpu_avg,
            severity=self._get_cpu_severity(cpu_max, cpu_avg),
            threshold_breached=cpu_max > 80.0
        )
        
        if cpu_max > 90:
            cpu_analysis.recommendations.append("Consider CPU scaling or optimization")
        if cpu_avg > 70:
            cpu_analysis.recommendations.append("Sustained high CPU usage detected")
        
        analyses.append(cpu_analysis)
        
        # Memory Analysis
        memory_values = [s.memory_mb for s in self.snapshots]
        memory_max = max(memory_values)
        memory_avg = sum(memory_values) / len(memory_values)
        
        memory_analysis = BottleneckAnalysis(
            resource_type="Memory",
            max_usage=memory_max,
            avg_usage=memory_avg,
            severity=self._get_memory_severity(memory_max, memory_avg),
            threshold_breached=memory_max > 1024.0  # 1GB
        )
        
        if memory_max > 2048:
            memory_analysis.recommendations.append("High memory usage - check for leaks")
        if self._detect_memory_growth():
            memory_analysis.recommendations.append("Potential memory leak detected")
        
        analyses.append(memory_analysis)
        
        # Connection Analysis
        conn_values = [s.connections for s in self.snapshots]
        conn_max = max(conn_values)
        conn_avg = sum(conn_values) / len(conn_values)
        
        conn_analysis = BottleneckAnalysis(
            resource_type="Connections",
            max_usage=conn_max,
            avg_usage=conn_avg,
            severity=self._get_connection_severity(conn_max, conn_avg),
            threshold_breached=conn_max > 100
        )
        
        if conn_max > 200:
            conn_analysis.recommendations.append("High connection count - check connection pooling")
        
        analyses.append(conn_analysis)
        
        return analyses
    
    def _get_cpu_severity(self, max_cpu: float, avg_cpu: float) -> str:
        """Determine CPU usage severity."""
        if max_cpu > 95 or avg_cpu > 85:
            return "critical"
        elif max_cpu > 85 or avg_cpu > 70:
            return "high"
        elif max_cpu > 70 or avg_cpu > 50:
            return "medium"
        else:
            return "low"
    
    def _get_memory_severity(self, max_memory: float, avg_memory: float) -> str:
        """Determine memory usage severity."""
        if max_memory > 4096 or avg_memory > 3072:  # 4GB max, 3GB avg
            return "critical"
        elif max_memory > 2048 or avg_memory > 1536:  # 2GB max, 1.5GB avg
            return "high"
        elif max_memory > 1024 or avg_memory > 768:   # 1GB max, 768MB avg
            return "medium"
        else:
            return "low"
    
    def _get_connection_severity(self, max_conn: int, avg_conn: float) -> str:
        """Determine connection usage severity."""
        if max_conn > 500 or avg_conn > 300:
            return "critical"
        elif max_conn > 200 or avg_conn > 150:
            return "high"
        elif max_conn > 100 or avg_conn > 75:
            return "medium"
        else:
            return "low"
    
    def _detect_memory_growth(self) -> bool:
        """Detect if memory usage is consistently growing."""
        if len(self.snapshots) < 10:
            return False
        
        # Check if memory is growing over time
        memory_values = [s.memory_mb for s in self.snapshots]
        first_half = memory_values[:len(memory_values)//2]
        second_half = memory_values[len(memory_values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        # Consider it a leak if memory increased by more than 50%
        return second_avg > first_avg * 1.5
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive resource usage report."""
        if not self.snapshots:
            return {"error": "No monitoring data available"}
        
        analyses = self.analyze_bottlenecks()
        
        # Calculate summary statistics
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]
        conn_values = [s.connections for s in self.snapshots]
        
        report = {
            "monitoring_duration": self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            "sample_count": len(self.snapshots),
            "cpu_stats": {
                "max": max(cpu_values),
                "min": min(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "p95": self._percentile(cpu_values, 95),
                "p99": self._percentile(cpu_values, 99)
            },
            "memory_stats": {
                "max_mb": max(memory_values),
                "min_mb": min(memory_values),
                "avg_mb": sum(memory_values) / len(memory_values),
                "p95_mb": self._percentile(memory_values, 95),
                "p99_mb": self._percentile(memory_values, 99)
            },
            "connection_stats": {
                "max": max(conn_values),
                "min": min(conn_values),
                "avg": sum(conn_values) / len(conn_values)
            },
            "bottlenecks": [
                {
                    "resource": analysis.resource_type,
                    "severity": analysis.severity,
                    "max_usage": analysis.max_usage,
                    "avg_usage": analysis.avg_usage,
                    "threshold_breached": analysis.threshold_breached,
                    "recommendations": analysis.recommendations
                }
                for analysis in analyses
            ]
        }
        
        return report
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class TestResourceMonitoring:
    """Test resource monitoring and bottleneck detection."""
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_resource_monitoring_during_stress(self, heavy_stress_config):
        """Test comprehensive resource monitoring during stress test."""
        stress_runner = StressTestRunner(heavy_stress_config)
        monitor = ResourceMonitor(sample_interval=0.1)  # High frequency sampling
        
        async def monitored_request(user_id: int, request_id: int, client: AsyncClient):
            """Request with resource monitoring."""
            # Mix of operations to stress different resources
            operations = [
                lambda: client.get("/api/v1/companies/"),
                lambda: client.get("/api/v1/tenders/"),
                lambda: client.post(
                    "/api/v1/tenders/",
                    json={
                        "title": f"Monitor Test {user_id}-{request_id}",
                        "description": "x" * 1000,  # Larger payload
                        "category": "TECHNOLOGY"
                    }
                ),
                lambda: client.get(f"/api/v1/tenders/search?q=test{user_id}")
            ]
            
            operation = operations[request_id % len(operations)]
            response = await operation()
            assert response.status_code in [200, 201, 400, 401, 422, 429]
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        try:
            async with AsyncClient(app=app, base_url="http://test") as client:
                metrics = await stress_runner.run_concurrent_test(
                    monitored_request, client
                )
        finally:
            # Stop monitoring
            monitor.stop_monitoring()
            monitor_task.cancel()
            
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # Generate and analyze report
        report = monitor.generate_report()
        
        # Print detailed report
        print("\n" + "="*50)
        print("RESOURCE MONITORING REPORT")
        print("="*50)
        print(f"Test Duration: {report['monitoring_duration']:.2f} seconds")
        print(f"Samples Collected: {report['sample_count']}")
        print(f"Requests: {metrics.successful_requests}/{metrics.total_requests} successful")
        print(f"RPS: {metrics.requests_per_second:.2f}")
        
        print("\nCPU Statistics:")
        cpu_stats = report['cpu_stats']
        print(f"  Max: {cpu_stats['max']:.1f}%")
        print(f"  Avg: {cpu_stats['avg']:.1f}%")
        print(f"  P95: {cpu_stats['p95']:.1f}%")
        print(f"  P99: {cpu_stats['p99']:.1f}%")
        
        print("\nMemory Statistics:")
        mem_stats = report['memory_stats']
        print(f"  Max: {mem_stats['max_mb']:.1f} MB")
        print(f"  Avg: {mem_stats['avg_mb']:.1f} MB")
        print(f"  P95: {mem_stats['p95_mb']:.1f} MB")
        print(f"  P99: {mem_stats['p99_mb']:.1f} MB")
        
        print("\nBottleneck Analysis:")
        for bottleneck in report['bottlenecks']:
            print(f"  {bottleneck['resource']}: {bottleneck['severity']} severity")
            print(f"    Max Usage: {bottleneck['max_usage']:.1f}")
            print(f"    Avg Usage: {bottleneck['avg_usage']:.1f}")
            if bottleneck['recommendations']:
                print(f"    Recommendations: {', '.join(bottleneck['recommendations'])}")
        
        # Assertions based on monitoring
        assert report['sample_count'] > 10, "Insufficient monitoring samples"
        
        # Check for critical bottlenecks
        critical_bottlenecks = [
            b for b in report['bottlenecks'] 
            if b['severity'] == 'critical'
        ]
        
        if critical_bottlenecks:
            print(f"\nWARNING: {len(critical_bottlenecks)} critical bottlenecks detected!")
            for bottleneck in critical_bottlenecks:
                print(f"  - {bottleneck['resource']}: {bottleneck['recommendations']}")
        
        # Ensure test completed successfully despite potential bottlenecks
        assert metrics.total_requests > 0
        
        # Save report for analysis
        with open("/tmp/stress_test_resource_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: /tmp/stress_test_resource_report.json")
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, light_stress_config):
        """Test for memory leaks during extended operations."""
        # Extended test configuration
        leak_config = StressTestConfig(
            concurrent_users=20,
            requests_per_user=50,  # More requests per user
            test_duration_seconds=180,  # 3 minutes
            max_response_time_ms=3000,
            error_threshold_percent=15.0
        )
        
        stress_runner = StressTestRunner(leak_config)
        monitor = ResourceMonitor(sample_interval=1.0)  # 1 second intervals
        
        async def memory_intensive_request(user_id: int, request_id: int, client: AsyncClient):
            """Memory intensive operations to detect leaks."""
            # Operations that might cause memory leaks
            response = await client.post(
                "/api/v1/tenders/",
                json={
                    "title": f"Leak Test {user_id}-{request_id}",
                    "description": "x" * 10000,  # Large description
                    "category": "TECHNOLOGY",
                    "requirements": ["req" + str(i) for i in range(100)],  # Large array
                    "metadata": {f"key_{i}": f"value_{i}" * 100 for i in range(50)}  # Large dict
                }
            )
            assert response.status_code in [200, 201, 400, 422]
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        try:
            async with AsyncClient(app=app, base_url="http://test") as client:
                metrics = await stress_runner.run_concurrent_test(
                    memory_intensive_request, client
                )
        finally:
            monitor.stop_monitoring()
            monitor_task.cancel()
            
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # Analyze for memory leaks
        report = monitor.generate_report()
        memory_growth_detected = monitor._detect_memory_growth()
        
        print(f"\nMemory Leak Detection Results:")
        print(f"  Memory Growth Detected: {memory_growth_detected}")
        print(f"  Max Memory Usage: {report['memory_stats']['max_mb']:.1f} MB")
        print(f"  Average Memory Usage: {report['memory_stats']['avg_mb']:.1f} MB")
        
        # Fail test if significant memory leak detected
        if memory_growth_detected:
            memory_bottlenecks = [
                b for b in report['bottlenecks'] 
                if b['resource'] == 'Memory' and 'leak' in str(b['recommendations'])
            ]
            
            if memory_bottlenecks:
                pytest.fail(f"Memory leak detected: {memory_bottlenecks[0]['recommendations']}")
        
        assert metrics.total_requests > 0
