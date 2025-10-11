"""
System Performance Monitoring and Alerting
Tracks CPU, memory, tasks, and application metrics in real-time
"""

import psutil
import threading
import time
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Comprehensive system performance monitoring"""
    
    def __init__(self, sample_interval: float = 30.0):
        self.sample_interval = sample_interval
        self.running = False
        self.monitor_thread = None
        
        # Metrics storage (circular buffer)
        self.max_samples = 100
        self.metrics = {
            'cpu_percent': [],
            'memory_mb': [],
            'memory_percent': [],
            'open_files': [],
            'thread_count': [],
            'asyncio_tasks': [],
            'timestamps': [],
            'kafka_consumer_status': [],
            'trace_count': [],
            'active_managed_tasks': []
        }
        
        # Performance thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning_mb': 1024,  # 1GB
            'memory_critical_mb': 2048,  # 2GB
            'tasks_warning': 50,
            'tasks_critical': 100,
            'open_files_warning': 500,
            'open_files_critical': 1000
        }
        
        # Alert tracking
        self.alerts_triggered = []
        self.last_alert_times = {}
        self.alert_cooldown = 300.0  # 5 minutes between same alerts
        
        logger.info(f"PerformanceMonitor initialized with {sample_interval}s interval")
    
    def start(self):
        """Start performance monitoring"""
        if self.running:
            logger.warning("Performance monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"✅ Performance monitor started (interval: {self.sample_interval}s)")
    
    def stop(self):
        """Stop performance monitoring"""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🛑 Performance monitor stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        try:
            process = psutil.Process()
        except Exception as e:
            logger.error(f"Failed to get current process: {e}")
            self.running = False
            return
        
        while self.running:
            try:
                # Collect system metrics
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                memory_percent = process.memory_percent()
                
                try:
                    open_files = len(process.open_files())
                except (psutil.AccessDenied, OSError):
                    open_files = 0
                
                thread_count = process.num_threads()
                
                # AsyncIO task count - safely access
                asyncio_tasks = 0
                kafka_status = "unknown"
                trace_count = 0
                managed_tasks = 0
                
                # Store metrics (circular buffer)
                now = time.time()
                self._add_metric('cpu_percent', cpu_percent, now)
                self._add_metric('memory_mb', memory_mb, now)
                self._add_metric('memory_percent', memory_percent, now)
                self._add_metric('open_files', open_files, now)
                self._add_metric('thread_count', thread_count, now)
                self._add_metric('asyncio_tasks', asyncio_tasks, now)
                self._add_metric('kafka_consumer_status', kafka_status, now)
                self._add_metric('trace_count', trace_count, now)
                self._add_metric('active_managed_tasks', managed_tasks, now)
                self._add_metric('timestamps', now, now)
                
                # Check thresholds and trigger alerts
                self._check_thresholds({
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'asyncio_tasks': asyncio_tasks,
                    'open_files': open_files,
                    'managed_tasks': managed_tasks
                })
                
                # Log periodic status (every 10 samples)
                if len(self.metrics['timestamps']) % 10 == 0:
                    logger.info(
                        f"📊 System Status: CPU={cpu_percent:.1f}%, "
                        f"RAM={memory_mb:.1f}MB ({memory_percent:.1f}%), "
                        f"Files={open_files}, Threads={thread_count}"
                    )
                
            except Exception as e:
                logger.error(f"❌ Performance monitoring error: {e}")
            
            time.sleep(self.sample_interval)
    
    def _add_metric(self, metric_name: str, value: Any, timestamp: float):
        """Add metric value to circular buffer"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
        
        # Maintain circular buffer size
        if len(self.metrics[metric_name]) > self.max_samples:
            self.metrics[metric_name] = self.metrics[metric_name][-self.max_samples:]
    
    def _check_thresholds(self, current_values: Dict[str, float]):
        """Check performance thresholds and trigger alerts"""
        current_time = time.time()
        
        alerts = []
        
        # CPU thresholds
        cpu = current_values.get('cpu_percent', 0)
        if cpu >= self.thresholds['cpu_critical']:
            alerts.append(('cpu_critical', f"Critical CPU usage: {cpu:.1f}%"))
        elif cpu >= self.thresholds['cpu_warning']:
            alerts.append(('cpu_warning', f"High CPU usage: {cpu:.1f}%"))
        
        # Memory thresholds
        memory = current_values.get('memory_mb', 0)
        if memory >= self.thresholds['memory_critical_mb']:
            alerts.append(('memory_critical', f"Critical memory usage: {memory:.1f}MB"))
        elif memory >= self.thresholds['memory_warning_mb']:
            alerts.append(('memory_warning', f"High memory usage: {memory:.1f}MB"))
        
        # Task count thresholds
        tasks = current_values.get('asyncio_tasks', 0)
        if tasks >= self.thresholds['tasks_critical']:
            alerts.append(('tasks_critical', f"Critical AsyncIO task count: {tasks}"))
        elif tasks >= self.thresholds['tasks_warning']:
            alerts.append(('tasks_warning', f"High AsyncIO task count: {tasks}"))
        
        # File descriptor thresholds
        files = current_values.get('open_files', 0)
        if files >= self.thresholds['open_files_critical']:
            alerts.append(('files_critical', f"Critical open file count: {files}"))
        elif files >= self.thresholds['open_files_warning']:
            alerts.append(('files_warning', f"High open file count: {files}"))
        
        # Process alerts with cooldown
        for alert_type, message in alerts:
            last_alert = self.last_alert_times.get(alert_type, 0)
            if current_time - last_alert >= self.alert_cooldown:
                logger.warning(f"🚨 PERFORMANCE ALERT: {message}")
                self.alerts_triggered.append({
                    'type': alert_type,
                    'message': message,
                    'timestamp': current_time,
                    'values': current_values.copy()
                })
                self.last_alert_times[alert_type] = current_time
                
                # Keep only last 50 alerts
                if len(self.alerts_triggered) > 50:
                    self.alerts_triggered = self.alerts_triggered[-50:]
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        if not self.metrics.get('timestamps') or not self.metrics['timestamps']:
            return {"error": "No metrics collected yet"}
        
        latest_idx = -1
        return {
            'cpu_percent': self.metrics['cpu_percent'][latest_idx] if self.metrics.get('cpu_percent') else 0,
            'memory_mb': self.metrics['memory_mb'][latest_idx] if self.metrics.get('memory_mb') else 0,
            'memory_percent': self.metrics['memory_percent'][latest_idx] if self.metrics.get('memory_percent') else 0,
            'open_files': self.metrics['open_files'][latest_idx] if self.metrics.get('open_files') else 0,
            'thread_count': self.metrics['thread_count'][latest_idx] if self.metrics.get('thread_count') else 0,
            'asyncio_tasks': self.metrics['asyncio_tasks'][latest_idx] if self.metrics.get('asyncio_tasks') else 0,
            'timestamp': datetime.fromtimestamp(self.metrics['timestamps'][latest_idx]).isoformat() if self.metrics.get('timestamps') else None,
            'monitoring_active': self.running
        }
    
    def get_trends(self, samples: int = 10) -> Dict[str, Any]:
        """Get performance trends over recent samples"""
        if len(self.metrics.get('timestamps', [])) < 2:
            return {"error": "Insufficient data for trends"}
        
        def calculate_trend(values, sample_count):
            if not values or len(values) < 2:
                return 0
            recent = values[-min(sample_count, len(values)):]
            if len(recent) < 2:
                return 0
            try:
                numeric_recent = [v for v in recent if isinstance(v, (int, float))]
                if len(numeric_recent) < 2:
                    return 0
                return (numeric_recent[-1] - numeric_recent[0]) / len(numeric_recent)
            except TypeError:
                return 0

        sample_count = min(samples, len(self.metrics.get('timestamps', [])))
        
        return {
            'cpu_trend': calculate_trend(self.metrics.get('cpu_percent', []), sample_count),
            'memory_trend_mb': calculate_trend(self.metrics.get('memory_mb', []), sample_count),
            'tasks_trend': calculate_trend(self.metrics.get('asyncio_tasks', []), sample_count),
            'sample_count': sample_count,
            'time_span_minutes': (
                (self.metrics['timestamps'][-1] - self.metrics['timestamps'][-sample_count]) / 60
                if len(self.metrics.get('timestamps', [])) >= sample_count else 0
            ),
            'recent_alerts': len([a for a in self.alerts_triggered if time.time() - a['timestamp'] < 3600])
        }
    
    def get_full_history(self) -> Dict[str, List]:
        """Get full metrics history (for charts/analysis)"""
        return {
            key: values.copy()
            for key, values in self.metrics.items()
            if values
        }
    
    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from the specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            alert for alert in self.alerts_triggered
            if alert['timestamp'] >= cutoff_time
        ]