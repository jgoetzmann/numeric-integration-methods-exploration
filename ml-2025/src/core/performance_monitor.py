"""
Performance Monitoring Module.

This module provides utilities for monitoring CPU usage, memory consumption,
and training performance to help optimize the training pipeline.
"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np

# Try to import psutil, make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Performance monitoring will be limited.")

@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance at a point in time."""
    
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    active_threads: int
    epoch: Optional[int] = None
    phase: Optional[str] = None  # 'evaluation', 'training', 'generation', etc.

class PerformanceMonitor:
    """Monitors system performance during training."""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.snapshots: List[PerformanceSnapshot] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.start_time = None
        
    def start_monitoring(self):
        """Start continuous performance monitoring."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        print("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                
                # Keep only recent snapshots to avoid memory issues
                if len(self.snapshots) > 1000:
                    self.snapshots = self.snapshots[-500:]
                    
            except Exception as e:
                print(f"Error in performance monitoring: {e}")
            
            time.sleep(self.sampling_interval)
    
    def _take_snapshot(self) -> PerformanceSnapshot:
        """Take a performance snapshot."""
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            return PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=process.cpu_percent(),
                memory_percent=process.memory_percent(),
                memory_used_mb=process.memory_info().rss / 1024 / 1024,
                active_threads=process.num_threads()
            )
        else:
            # Fallback without psutil
            return PerformanceSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                active_threads=1
            )
    
    def log_phase(self, phase: str, epoch: int = None):
        """Log a training phase with current performance."""
        snapshot = self._take_snapshot()
        snapshot.phase = phase
        snapshot.epoch = epoch
        self.snapshots.append(snapshot)
        
        if PSUTIL_AVAILABLE:
            print(f"[{phase}] CPU: {snapshot.cpu_percent:.1f}%, "
                  f"Memory: {snapshot.memory_percent:.1f}% ({snapshot.memory_used_mb:.1f}MB), "
                  f"Threads: {snapshot.active_threads}")
        else:
            print(f"[{phase}] Performance monitoring limited (psutil not available)")
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get summary statistics of performance."""
        if not self.snapshots:
            return {}
        
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_percent for s in self.snapshots]
        thread_values = [s.active_threads for s in self.snapshots]
        
        return {
            'avg_cpu_percent': np.mean(cpu_values),
            'max_cpu_percent': np.max(cpu_values),
            'avg_memory_percent': np.mean(memory_values),
            'max_memory_percent': np.max(memory_values),
            'avg_threads': np.mean(thread_values),
            'max_threads': np.max(thread_values),
            'monitoring_duration': self.snapshots[-1].timestamp - self.snapshots[0].timestamp if len(self.snapshots) > 1 else 0
        }
    
    def print_performance_report(self):
        """Print a detailed performance report."""
        summary = self.get_performance_summary()
        
        if not summary:
            print("No performance data available")
            return
        
        print("\n" + "="*50)
        print("PERFORMANCE REPORT")
        print("="*50)
        print(f"Monitoring Duration: {summary['monitoring_duration']:.1f} seconds")
        print(f"Average CPU Usage: {summary['avg_cpu_percent']:.1f}%")
        print(f"Peak CPU Usage: {summary['max_cpu_percent']:.1f}%")
        print(f"Average Memory Usage: {summary['avg_memory_percent']:.1f}%")
        print(f"Peak Memory Usage: {summary['max_memory_percent']:.1f}%")
        print(f"Average Thread Count: {summary['avg_threads']:.1f}")
        print(f"Peak Thread Count: {summary['max_threads']:.1f}")
        
        # Analyze phases if available
        phases = {}
        for snapshot in self.snapshots:
            if snapshot.phase:
                if snapshot.phase not in phases:
                    phases[snapshot.phase] = []
                phases[snapshot.phase].append(snapshot.cpu_percent)
        
        if phases:
            print("\nCPU Usage by Phase:")
            for phase, cpu_values in phases.items():
                avg_cpu = np.mean(cpu_values)
                print(f"  {phase}: {avg_cpu:.1f}%")
        
        print("="*50)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def start_performance_monitoring():
    """Start global performance monitoring."""
    if PSUTIL_AVAILABLE:
        performance_monitor.start_monitoring()
    else:
        print("Performance monitoring started (limited - install psutil for full monitoring)")

def stop_performance_monitoring():
    """Stop global performance monitoring."""
    if PSUTIL_AVAILABLE:
        performance_monitor.stop_monitoring()
    else:
        print("Performance monitoring stopped")

def log_training_phase(phase: str, epoch: int = None):
    """Log a training phase with performance metrics."""
    if PSUTIL_AVAILABLE:
        performance_monitor.log_phase(phase, epoch)
    else:
        print(f"[{phase}] Phase logged (install psutil for detailed metrics)")

def print_performance_report():
    """Print performance report."""
    if PSUTIL_AVAILABLE:
        performance_monitor.print_performance_report()
    else:
        print("Performance report unavailable (install psutil for detailed metrics)")

if __name__ == "__main__":
    # Test the performance monitor
    print("Testing performance monitor...")
    
    monitor = PerformanceMonitor(sampling_interval=0.5)
    monitor.start_monitoring()
    
    # Simulate some work
    time.sleep(3)
    monitor.log_phase("test_phase", 1)
    time.sleep(2)
    
    monitor.stop_monitoring()
    monitor.print_performance_report()
    
    print("Performance monitor test completed.")
