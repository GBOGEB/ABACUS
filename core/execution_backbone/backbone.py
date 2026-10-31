#!/usr/bin/env python3
"""ExecutionBackbone: bounded priority admission and honest local pool telemetry.

Compatibility: schedule_task(), start(), stop(), get_metrics() and legacy
counters retain their existing meanings. This is a LOCAL Python worker pool,
not a GitHub Actions runner-capacity measurement or a remote dispatch gateway.

Queue admission is capped to the number of configured workers. In particular,
pending low-priority work does not silently disappear into an unbounded executor
queue ahead of subsequently submitted high-priority work.
"""

from __future__ import annotations

import math
import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


def _p95(samples: list[float]) -> float | None:
    if not samples:
        return None
    return round(sorted(samples)[math.ceil(0.95 * len(samples)) - 1], 4)


@dataclass(order=True)
class _PriorityTask:
    priority: int
    sequence: int
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    submitted_at: str = field(
        compare=False, default_factory=lambda: datetime.now().isoformat()
    )
    submitted_monotonic: float = field(compare=False, default_factory=time.monotonic)


class ExecutionBackbone:
    """Local bounded task queue, exact outstanding-work and service telemetry.

    max_memory_mb is advisory, as in the historical implementation; this class
    cannot measure or enforce process memory without a separate source-bound
    operating-system provider. No method is allowed to dispatch remote jobs.
    """

    def __init__(self, max_workers: int = 4, max_memory_mb: int = 4096):
        self.max_workers = max(1, int(max_workers))
        self.max_memory_mb = max_memory_mb
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()

        self._executor: Optional[ThreadPoolExecutor] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_without_drain = False
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(self.max_workers)
        self._sequence = 0

        # Historical names: tasks_executed means successful completed tasks.
        self.tasks_executed = 0
        self.tasks_failed = 0
        self.tasks_submitted = 0
        self.tasks_cancelled_at_admission = 0

        self._admitted = 0
        self._active = 0
        self._peak_active = 0
        self._queue_wait_samples: List[float] = []
        self._service_samples: List[float] = []
        self._futures: List[Future] = []
        self._start_time: Optional[float] = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            if self._executor is not None:
                raise RuntimeError("BACKBONE_STOP_IN_PROGRESS")
            self._slots = threading.BoundedSemaphore(self.max_workers)
            self._stop_without_drain = False
            self._executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="execution_backbone_worker",
            )
            self._running = True
            self._start_time = time.time()
            self._worker_thread = threading.Thread(
                target=self._dispatch_loop,
                name="execution_backbone_dispatcher",
                daemon=True,
            )
            thread = self._worker_thread
        thread.start()

    def stop(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Stop, draining queued tasks by default; timeout does not fabricate drain.

        When wait=False the unadmitted priority queue remains visible; its tasks
        are not counted as executed or failed. Existing executor tasks finish
        asynchronously, and a later stop(wait=True) may join them.
        """
        with self._lock:
            self._running = False
            if not wait:
                self._stop_without_drain = True
            worker, executor = self._worker_thread, self._executor

        if worker and wait:
            worker.join(timeout=timeout)
            if worker.is_alive():
                raise TimeoutError("BACKBONE_DRAIN_INCOMPLETE")
        if executor is not None:
            executor.shutdown(wait=wait, cancel_futures=False)
            if wait:
                with self._lock:
                    self._executor = None
        if wait:
            with self._lock:
                self._worker_thread = None

    def schedule_task(
        self,
        task_id: str,
        func: Callable,
        priority: int = 5,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            self._sequence += 1
            seq = self._sequence
            self.tasks_submitted += 1
        task = _PriorityTask(
            priority=priority,
            sequence=seq,
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
        )
        self.task_queue.put(task)

    def get_metrics(self) -> Dict[str, Any]:
        """Measure pending+admitted+running separately, not just queue.qsize().

        This configured local executor has a known worker limit. The configured
        slots must never be misrepresented as remote GitHub runner capacity.
        """
        with self._lock:
            queued = self.task_queue.qsize()
            active, admitted = self._active, self._admitted
            # A worker can be admitted before its function begins.
            not_running = max(0, admitted - active)
            return {
                "tasks_submitted": self.tasks_submitted,
                "tasks_executed": self.tasks_executed,
                "tasks_failed": self.tasks_failed,
                "tasks_cancelled_at_admission": self.tasks_cancelled_at_admission,
                "queue_size": queued,
                "waiting_queue_size": queued,
                "admitted_not_started": not_running,
                "currently_running": active,
                "admitted_inflight": admitted,
                "outstanding_work": queued + admitted,
                "peak_running": self._peak_active,
                "max_workers": self.max_workers,
                "max_memory_mb": self.max_memory_mb,
                "max_memory_mb_is_advisory": True,
                "configured_local_pool_slots": self.max_workers,
                "local_pool_utilization_pct": round(100 * active / self.max_workers, 2),
                "remote_runner_capacity_slots": None,
                "queue_wait_p95_seconds": _p95(self._queue_wait_samples),
                "service_p95_seconds": _p95(self._service_samples),
                "queue_wait_sample_n": len(self._queue_wait_samples),
                "service_sample_n": len(self._service_samples),
                "executor_pending_bound": self.max_workers,
                "running": self._running,
                "uptime_seconds": round(
                    time.time() - (self._start_time or time.time()), 2
                ),
                "merge_admission": "HOLD",
                "remote_dispatch_enabled": False,
                "authority_transfer": False,
            }

    def _dispatch_loop(self) -> None:
        while True:
            with self._lock:
                if self._stop_without_drain:
                    return
                running = self._running
            if not running and self.task_queue.empty():
                return

            # Acquire capacity BEFORE removing the best task from priority queue.
            # Remaining tasks thus stay correctly visible and reprioritizable.
            if not self._slots.acquire(timeout=0.02):
                continue
            # Re-check after a blocked slot wait. stop(wait=False) may have
            # happened while a running task still held the last permit.
            with self._lock:
                cancelled_without_drain = self._stop_without_drain
            if cancelled_without_drain:
                self._slots.release()
                return
            try:
                task = self.task_queue.get(timeout=0.02)
            except queue.Empty:
                self._slots.release()
                continue

            # A stop may also race the dequeue. Preserve the task instead of
            # either running it or manufacturing a failure/cancellation.
            with self._lock:
                cancelled_without_drain = self._stop_without_drain
                if cancelled_without_drain:
                    self.task_queue.put(task)
                    self.task_queue.task_done()
                    self._slots.release()
                    return
                executor = self._executor
                if executor is not None:
                    self._admitted += 1
            if executor is None:
                with self._lock:
                    self.tasks_cancelled_at_admission += 1
                self.task_queue.task_done()
                self._slots.release()
                continue
            try:
                future = executor.submit(self._execute_task, task)
            except RuntimeError:
                # Never claim a failed execution for a task that never ran.
                with self._lock:
                    self._admitted -= 1
                    self.tasks_cancelled_at_admission += 1
                self._slots.release()
            else:
                with self._lock:
                    # Avoid an unbounded completed-Future ledger.
                    self._futures = [f for f in self._futures if not f.done()]
                    self._futures.append(future)
            finally:
                self.task_queue.task_done()

    def _execute_task(self, task: _PriorityTask) -> Any:
        with self._lock:
            self._active += 1
            self._peak_active = max(self._peak_active, self._active)
            self._queue_wait_samples.append(
                max(0.0, time.monotonic() - task.submitted_monotonic)
            )
        started = time.monotonic()
        try:
            result = task.func(*task.args, **task.kwargs)
            with self._lock:
                self.tasks_executed += 1
            return result
        except Exception as exc:
            with self._lock:
                self.tasks_failed += 1
            print(f"[EXEC-BACKBONE] Task '{task.task_id}' failed: {exc}")
            return None
        finally:
            with self._lock:
                self._service_samples.append(max(0.0, time.monotonic() - started))
                self._active -= 1
                self._admitted -= 1
            self._slots.release()
