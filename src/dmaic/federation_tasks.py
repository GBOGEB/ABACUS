"""Bounded DELTA_1 federation worker orchestration runtime.

ABACUS is the DELTA_1 runtime plane.  This module provides an intentionally
small deterministic task/worker core that can be driven by MCP adapters,
GitHub automation, or local runners without making any provider-specific API
call itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

TERMINAL_STATES = {"completed", "failed"}


@dataclass(frozen=True)
class WorkflowRef:
    program: str
    wave: str
    subwave: str
    phase: str
    sprint: str
    task: str
    subtask: str

    @property
    def workflow_id(self) -> str:
        return "-".join(
            (
                self.program,
                self.wave,
                self.subwave,
                self.phase,
                self.sprint,
                self.task,
                self.subtask,
            )
        )


@dataclass(frozen=True)
class BridgeEnvelope:
    correlation_id: str
    source_repo: str
    target_repo: str
    contract: str
    workflow: WorkflowRef
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerTask:
    task_id: str
    workflow: WorkflowRef
    capability: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "queued"
    assigned_worker: str | None = None
    attempts: int = 0
    result: dict[str, Any] | None = None


@dataclass(frozen=True)
class Worker:
    worker_id: str
    capabilities: frozenset[str]


class FederationOrchestrator:
    """Deterministic FIFO scheduler for bounded federation worker tasks."""

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}
        self._tasks: dict[str, WorkerTask] = {}
        self._queue: list[str] = []

    def register_worker(self, worker_id: str, capabilities: Iterable[str]) -> Worker:
        if not worker_id:
            raise ValueError("worker_id must be non-empty")
        caps = frozenset(cap for cap in capabilities if cap)
        if not caps:
            raise ValueError("worker must declare at least one capability")
        worker = Worker(worker_id=worker_id, capabilities=caps)
        self._workers[worker_id] = worker
        return worker

    def submit(self, task: WorkerTask) -> WorkerTask:
        if task.task_id in self._tasks:
            raise ValueError(f"duplicate task_id: {task.task_id}")
        if task.status != "queued":
            raise ValueError("new tasks must start queued")
        self._tasks[task.task_id] = task
        self._queue.append(task.task_id)
        return task

    def lease(self, worker_id: str) -> WorkerTask | None:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise KeyError(f"unknown worker: {worker_id}")
        for task_id in list(self._queue):
            task = self._tasks[task_id]
            if task.status == "queued" and task.capability in worker.capabilities:
                task.status = "leased"
                task.assigned_worker = worker_id
                task.attempts += 1
                self._queue.remove(task_id)
                return task
        return None

    def complete(
        self,
        worker_id: str,
        task_id: str,
        *,
        success: bool,
        result: dict[str, Any] | None = None,
    ) -> WorkerTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"unknown task: {task_id}")
        if task.status != "leased" or task.assigned_worker != worker_id:
            raise ValueError("task is not leased to this worker")
        task.status = "completed" if success else "failed"
        task.result = result or {}
        return task

    def requeue(self, task_id: str) -> WorkerTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"unknown task: {task_id}")
        if task.status not in {"leased", "failed"}:
            raise ValueError("only leased or failed tasks may be requeued")
        task.status = "queued"
        task.assigned_worker = None
        task.result = None
        if task_id not in self._queue:
            self._queue.append(task_id)
        return task

    def snapshot(self) -> dict[str, Any]:
        states: dict[str, int] = {}
        for task in self._tasks.values():
            states[task.status] = states.get(task.status, 0) + 1
        return {
            "workers": {
                worker_id: sorted(worker.capabilities)
                for worker_id, worker in sorted(self._workers.items())
            },
            "tasks": {
                task_id: {
                    **asdict(task),
                    "workflow_id": task.workflow.workflow_id,
                }
                for task_id, task in sorted(self._tasks.items())
            },
            "metrics": {
                "worker_count": len(self._workers),
                "task_count": len(self._tasks),
                "queue_depth": len(self._queue),
                "terminal_count": sum(
                    count for state, count in states.items() if state in TERMINAL_STATES
                ),
                "states": states,
            },
        }
