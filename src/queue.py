"""
AgentHands - Task Queue
In-memory priority queue for MVP (Redis for production)
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import heapq

from .models import TaskPriority


@dataclass(order=True)
class QueueItem:
    """Item in the priority queue."""
    priority_value: int
    created_at: float
    task_id: str = field(compare=False)
    priority: TaskPriority = field(compare=False)


class TaskQueue:
    """
    In-memory priority queue for tasks.
    
    Priority order:
    1. immediate (priority_value=0)
    2. priority (priority_value=1)
    3. standard (priority_value=2)
    
    Within same priority, FIFO by creation time.
    """
    
    def __init__(self):
        self._queue: List[QueueItem] = []
        self._task_lookup: Dict[str, QueueItem] = {}
        self._lock = asyncio.Lock()
        self._running = False
    
    async def start(self):
        """Start the queue."""
        self._running = True
        print("📋 Task queue started")
    
    async def stop(self):
        """Stop the queue."""
        self._running = False
        print("📋 Task queue stopped")
    
    async def enqueue(self, task_id: str, priority: str = "standard") -> int:
        """
        Add a task to the queue.
        Returns queue position (1-indexed).
        """
        async with self._lock:
            # Map priority to value
            priority_enum = TaskPriority(priority)
            priority_value = {
                TaskPriority.IMMEDIATE: 0,
                TaskPriority.PRIORITY: 1,
                TaskPriority.STANDARD: 2
            }[priority_enum]
            
            item = QueueItem(
                priority_value=priority_value,
                created_at=datetime.utcnow().timestamp(),
                task_id=task_id,
                priority=priority_enum
            )
            
            heapq.heappush(self._queue, item)
            self._task_lookup[task_id] = item
            
            # Calculate position
            position = await self._calculate_position(task_id)
            return position
    
    async def dequeue(self) -> Optional[str]:
        """
        Get the next task to execute.
        Returns task_id or None if queue is empty.
        """
        async with self._lock:
            while self._queue:
                item = heapq.heappop(self._queue)
                # Check if task is still in lookup (not cancelled via lazy deletion)
                if item.task_id in self._task_lookup:
                    del self._task_lookup[item.task_id]
                    # Periodically clean up orphaned heap entries
                    await self._cleanup_heap()
                    return item.task_id
                # Item was cancelled/removed, continue to next
            return None
    
    async def peek(self) -> Optional[str]:
        """Look at the next task without removing it."""
        async with self._lock:
            for item in self._queue:
                if item.task_id in self._task_lookup:
                    return item.task_id
            return None
    
    async def remove(self, task_id: str) -> bool:
        """
        Remove a task from the queue (for cancellation).
        Uses lazy deletion - item stays in heap but marked as removed.
        Returns True if removed, False if not found.
        """
        async with self._lock:
            if task_id in self._task_lookup:
                del self._task_lookup[task_id]
                # Note: Item stays in heap but will be skipped on dequeue
                # Periodically clean up orphaned items in dequeue
                return True
            return False
    
    async def _cleanup_heap(self):
        """
        Clean up orphaned items in the heap (lazy deletion cleanup).
        Called periodically during dequeue operations.
        """
        # Only clean up if heap is significantly larger than active items
        if len(self._queue) > len(self._task_lookup) * 2 + 100:
            # Rebuild heap with only active items
            active_items = [item for item in self._queue if item.task_id in self._task_lookup]
            heapq.heapify(active_items)
            self._queue = active_items
    
    async def position(self, task_id: str) -> Optional[int]:
        """Get the current position of a task in the queue."""
        async with self._lock:
            return await self._calculate_position(task_id)
    
    async def _calculate_position(self, task_id: str) -> Optional[int]:
        """Calculate position (must be called with lock held)."""
        if task_id not in self._task_lookup:
            return None
        
        target_item = self._task_lookup[task_id]
        
        # Sort queue and find position
        sorted_items = sorted(
            [item for item in self._queue if item.task_id in self._task_lookup]
        )
        
        for i, item in enumerate(sorted_items):
            if item.task_id == task_id:
                return i + 1  # 1-indexed
        
        return None
    
    async def size(self) -> int:
        """Get the number of tasks in the queue."""
        async with self._lock:
            return len(self._task_lookup)
    
    async def get_stats(self) -> Dict:
        """Get queue statistics."""
        async with self._lock:
            by_priority = {
                "immediate": 0,
                "priority": 0,
                "standard": 0
            }
            
            for item in self._task_lookup.values():
                by_priority[item.priority.value] += 1
            
            return {
                "total": len(self._task_lookup),
                "by_priority": by_priority
            }


class PersistentTaskQueue(TaskQueue):
    """
    Extended queue that persists to database.
    For production use - reconstructs queue on startup.
    """
    
    def __init__(self, database=None):
        super().__init__()
        self.db = database
    
    def set_database(self, db):
        """Set database reference after initialization."""
        self.db = db
    
    async def start(self):
        """Start queue and load pending tasks from database."""
        self._running = True
        if self.db:
            await self._load_from_database()
            await self._recover_stuck_tasks()
        print("📋 Persistent task queue started")
    
    async def stop(self):
        """Stop the queue gracefully."""
        self._running = False
        
        # Log remaining queue size for debugging
        async with self._lock:
            remaining = len(self._task_lookup)
            if remaining > 0:
                print(f"📋 Queue stopped with {remaining} tasks remaining (will reload on restart)")
        
        print("📋 Task queue stopped")
    
    async def _load_from_database(self):
        """Load queued tasks from database on startup."""
        try:
            tasks = await self.db.get_queued_tasks(limit=1000)
            for task in tasks:
                # Use super to avoid any DB writes during load
                async with self._lock:
                    if task.task_id not in self._task_lookup:
                        priority_enum = TaskPriority(task.priority.value)
                        priority_value = {
                            TaskPriority.IMMEDIATE: 0,
                            TaskPriority.PRIORITY: 1,
                            TaskPriority.STANDARD: 2
                        }[priority_enum]
                        
                        item = QueueItem(
                            priority_value=priority_value,
                            created_at=task.created_at.timestamp(),
                            task_id=task.task_id,
                            priority=priority_enum
                        )
                        
                        heapq.heappush(self._queue, item)
                        self._task_lookup[task.task_id] = item
            
            if tasks:
                print(f"📋 Loaded {len(tasks)} queued tasks from database")
        except Exception as e:
            print(f"⚠️ Error loading tasks from database: {e}")
    
    async def _recover_stuck_tasks(self):
        """Recover tasks stuck in 'executing' state."""
        try:
            stuck_tasks = await self.db.get_stuck_tasks(stuck_threshold_minutes=30)
            
            for task in stuck_tasks:
                print(f"⚠️ Found stuck task: {task.task_id}, failing it...")
                await self.db.fail_stuck_task(
                    task.task_id,
                    reason="Task was stuck in executing state during startup recovery"
                )
            
            if stuck_tasks:
                print(f"🔧 Recovered {len(stuck_tasks)} stuck tasks")
        except Exception as e:
            print(f"⚠️ Error recovering stuck tasks: {e}")
    
    async def enqueue(self, task_id: str, priority: str = "standard") -> int:
        """Add a task to the queue (persisted in DB already)."""
        # Tasks are already in DB when this is called, just add to memory queue
        return await super().enqueue(task_id, priority)
    
    async def dequeue(self) -> Optional[str]:
        """Get the next task to execute."""
        task_id = await super().dequeue()
        
        # Task status will be updated by executor when it starts
        return task_id
