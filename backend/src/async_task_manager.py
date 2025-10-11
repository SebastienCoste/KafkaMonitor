"""
Centralized Async Task Management System
Prevents uncontrolled task creation and enables lifecycle management
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Set, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """Information about a managed task"""
    name: str
    created_at: float
    coro_name: str
    environment: Optional[str] = None
    task_type: str = "general"


class AsyncTaskManager:
    """Centralized async task management with lifecycle control"""
    
    def __init__(self, max_concurrent: int = 20):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks: Set[asyncio.Task] = set()
        self.task_info: Dict[asyncio.Task, TaskInfo] = {}
        self.environment_tasks: Dict[str, Set[asyncio.Task]] = {}
        self._cleanup_interval = 60.0  # Cleanup every minute
        self._stats = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_cancelled': 0,
            'tasks_failed': 0,
            'cleanup_runs': 0
        }
        
        # Start background cleanup monitor
        self._monitor_task = None
        self._start_cleanup_monitor()
        
        logger.info(f"AsyncTaskManager initialized (max_concurrent={max_concurrent})")
    
    async def create_managed_task(
        self, 
        coro, 
        name: str = None, 
        environment: str = None,
        task_type: str = "general"
    ) -> asyncio.Task:
        """Create a managed task with automatic cleanup and tracking"""
        
        task_name = name or f"task_{self._stats['tasks_created']}"
        
        # Create the task
        task = asyncio.create_task(coro, name=task_name)
        
        # Track task info
        self.active_tasks.add(task)
        self.task_info[task] = TaskInfo(
            name=task_name,
            created_at=time.time(),
            coro_name=coro.__class__.__name__ if hasattr(coro, '__class__') else str(type(coro)),
            environment=environment,
            task_type=task_type
        )
        
        # Track by environment if specified
        if environment:
            if environment not in self.environment_tasks:
                self.environment_tasks[environment] = set()
            self.environment_tasks[environment].add(task)
        
        # Add completion callback for automatic cleanup
        task.add_done_callback(self._task_done_callback)
        
        self._stats['tasks_created'] += 1
        logger.info(f"📋 Created managed task '{task_name}' (type: {task_type}, env: {environment or 'none'})")
        
        return task
    
    def _task_done_callback(self, task: asyncio.Task):
        """Callback when task completes - automatic cleanup"""
        task_info = self.task_info.get(task)
        task_name = task_info.name if task_info else "unknown"
        
        # Update stats based on how task completed
        if task.cancelled():
            self._stats['tasks_cancelled'] += 1
            logger.debug(f"📋 Task '{task_name}' was cancelled")
        elif task.exception():
            self._stats['tasks_failed'] += 1
            logger.warning(f"📋 Task '{task_name}' failed: {task.exception()}")
        else:
            self._stats['tasks_completed'] += 1
            logger.debug(f"📋 Task '{task_name}' completed successfully")
        
        # Remove from tracking
        self.active_tasks.discard(task)
        self.task_info.pop(task, None)
        
        # Remove from environment tracking
        if task_info and task_info.environment:
            env_tasks = self.environment_tasks.get(task_info.environment)
            if env_tasks:
                env_tasks.discard(task)
                if not env_tasks:
                    del self.environment_tasks[task_info.environment]
    
    async def cleanup_environment_tasks(self, environment: str):
        """Cancel and cleanup all tasks for a specific environment"""
        env_tasks = self.environment_tasks.get(environment, set()).copy()
        
        if not env_tasks:
            logger.info(f"🧹 No tasks to cleanup for environment: {environment}")
            return
        
        logger.info(f"🧹 Cleaning up {len(env_tasks)} tasks for environment: {environment}")
        
        # Cancel all environment tasks
        for task in env_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation with timeout
        if env_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*env_tasks, return_exceptions=True),
                    timeout=5.0
                )
                logger.info(f"✅ Environment '{environment}' tasks cleaned up successfully")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Some tasks for environment '{environment}' didn't respond to cancellation in time")
        
        # Force remove from tracking
        if environment in self.environment_tasks:
            del self.environment_tasks[environment]
    
    async def cleanup_all_tasks(self):
        """Cancel and cleanup all managed tasks"""
        if not self.active_tasks:
            logger.info("🧹 No active tasks to cleanup")
            return
        
        logger.info(f"🧹 Cleaning up {len(self.active_tasks)} active tasks")
        
        # Cancel all active tasks
        tasks_to_cancel = self.active_tasks.copy()
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation with timeout
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=10.0
                )
                logger.info("✅ All tasks cleaned up successfully")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Some tasks didn't respond to cancellation in time")
        
        # Force clear tracking
        self.active_tasks.clear()
        self.task_info.clear()
        self.environment_tasks.clear()
        
        logger.info("✅ Task manager cleanup completed")
    
    def _start_cleanup_monitor(self):
        """Start background task to monitor and cleanup stale tasks"""
        async def monitor():
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self._cleanup_stale_tasks()
                    self._stats['cleanup_runs'] += 1
                except Exception as e:
                    logger.error(f"❌ Task monitor error: {e}")
        
        # Create monitor task but don't track it (to avoid recursion)
        self._monitor_task = asyncio.create_task(monitor(), name="task_monitor")
    
    async def _cleanup_stale_tasks(self):
        """Remove completed tasks and identify long-running tasks"""
        current_time = time.time()
        stale_threshold = 300.0  # 5 minutes
        
        completed_tasks = [task for task in self.active_tasks if task.done()]
        long_running_tasks = [
            (task, info) for task, info in self.task_info.items()
            if (current_time - info.created_at) > stale_threshold and not task.done()
        ]
        
        # Clean up completed tasks
        for task in completed_tasks:
            self._task_done_callback(task)
        
        # Log warnings for long-running tasks
        for task, info in long_running_tasks:
            runtime_minutes = (current_time - info.created_at) / 60
            logger.warning(f"⚠️ Long-running task detected: '{info.name}' ({runtime_minutes:.1f} minutes)")
        
        if completed_tasks or long_running_tasks:
            logger.info(f"🧹 Cleanup: removed {len(completed_tasks)} completed tasks, {len(long_running_tasks)} long-running tasks detected")
    
    def get_stats(self) -> Dict[str, any]:
        """Get task manager statistics"""
        current_time = time.time()
        
        task_ages = [
            current_time - info.created_at 
            for info in self.task_info.values()
        ]
        
        return {
            **self._stats,
            'active_tasks': len(self.active_tasks),
            'max_concurrent': self.max_concurrent,
            'semaphore_available': self.semaphore._value,
            'environments_tracked': len(self.environment_tasks),
            'avg_task_age_seconds': sum(task_ages) / len(task_ages) if task_ages else 0,
            'oldest_task_age_seconds': max(task_ages) if task_ages else 0
        }
    
    async def shutdown(self):
        """Shutdown task manager gracefully"""
        logger.info("🛑 Shutting down task manager...")
        
        # Stop monitor task
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup all managed tasks
        await self.cleanup_all_tasks()
        
        logger.info("✅ Task manager shutdown completed")