#!/usr/bin/env python3
"""
KEB - Kernel Execution Backbone
Lightweight task scheduling and parallel execution engine for V2.3 agents.

Provides:
- Priority-based task queue
- Configurable worker pool (bounded by max_workers)
- Memory-capped execution (max_memory_mb advisory)
- Non-blocking task submission via schedule_task()
- start() / stop() lifecycle management
"""
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(order=True)
class _PriorityTask:
    """Internal wrapper that makes tasks comparable by priority (lower int = higher priority)."""
    priority: int
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    submitted_at: str = field(compare=False, default_factory=lambda: datetime.now().isoformat())


class KEB:
    """
    Kernel Execution Backbone.

    Manages a priority queue of callable tasks executed by a bounded worker
    pool.  Designed for memory-constrained environments (advisory
    ``max_memory_mb`` limit) and deterministic shutdown.

    Usage::

        keb = KEB(max_workers=4, max_memory_mb=2048)
        keb.start()
        keb.schedule_task("my_task", some_function, priority=3, args=(x,))
        # ... submit more tasks ...
        while not keb.task_queue.empty():
            time.sleep(0.05)
        keb.stop()
    """

    def __init__(self, max_workers: int = 4, max_memory_mb: int = 4096):
        self.max_workers = max(1, max_workers)
        self.max_memory_mb = max_memory_mb

        # Expose as public attribute so callers can check .empty()
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()

        self._executor: Optional[ThreadPoolExecutor] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        self.tasks_executed: int = 0
        self.tasks_failed: int = 0
        self.tasks_submitted: int = 0

        self._futures: List[Future] = []
        self._start_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the worker pool and dispatch loop."""
        with self._lock:
            if self._running:
                return
            self._executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="keb_worker",
            )
            self._running = True
            self._start_time = time.time()
            self._worker_thread = threading.Thread(
                target=self._dispatch_loop,
                name="keb_dispatcher",
                daemon=True,
            )
            self._worker_thread.start()

        print(f"[KEB] Started with {self.max_workers} workers "
              f"(memory limit: {self.max_memory_mb} MB)")

    def stop(self, wait: bool = True, timeout: float = 30.0) -> None:
        """
        Signal the dispatcher to stop and optionally wait for completion.

        Parameters
        ----------
        wait:
            If True (default), block until the dispatcher drains the queue
            and the executor finishes all running tasks.
        timeout:
            Maximum seconds to wait when *wait* is True.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._worker_thread and wait:
            self._worker_thread.join(timeout=timeout)

        if self._executor:
            self._executor.shutdown(wait=wait, cancel_futures=False)
            self._executor = None

        uptime = round(time.time() - (self._start_time or time.time()), 2)
        print(f"[KEB] Stopped. executed={self.tasks_executed} "
              f"failed={self.tasks_failed} uptime={uptime}s")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule_task(
        self,
        task_id: str,
        func: Callable,
        priority: int = 5,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Submit a callable for execution.

        Parameters
        ----------
        task_id:
            Human-readable identifier (used in logs).
        func:
            Zero-or-more-argument callable to execute.
        priority:
            Execution priority; lower numbers run first (default 5).
        args:
            Positional arguments forwarded to *func*.
        kwargs:
            Keyword arguments forwarded to *func*.
        """
        task = _PriorityTask(
            priority=priority,
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
        )
        self.task_queue.put(task)
        self.tasks_submitted += 1
        print(f"[KEB] Scheduled task '{task_id}' (priority={priority})")

    def get_metrics(self) -> Dict[str, Any]:
        """Return current execution metrics."""
        return {
            'tasks_submitted': self.tasks_submitted,
            'tasks_executed': self.tasks_executed,
            'tasks_failed': self.tasks_failed,
            'queue_size': self.task_queue.qsize(),
            'max_workers': self.max_workers,
            'max_memory_mb': self.max_memory_mb,
            'running': self._running,
            'uptime_seconds': round(time.time() - (self._start_time or time.time()), 2),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _dispatch_loop(self) -> None:
        """Continuously pull tasks from the priority queue and execute them."""
        while self._running or not self.task_queue.empty():
            try:
                task: _PriorityTask = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._executor is None:
                # Executor was shut down; discard remaining tasks
                self.task_queue.task_done()
                continue

            future = self._executor.submit(self._execute_task, task)
            self._futures.append(future)
            self.task_queue.task_done()

    def _execute_task(self, task: _PriorityTask) -> Any:
        """Execute a single task; update counters on success/failure."""
        print(f"[KEB] Executing task '{task.task_id}'")
        try:
            result = task.func(*task.args, **task.kwargs)
            self.tasks_executed += 1
            print(f"[KEB] Task '{task.task_id}' completed successfully")
            return result
        except Exception as exc:
            self.tasks_failed += 1
            print(f"[KEB] Task '{task.task_id}' failed: {exc}")
            return None
