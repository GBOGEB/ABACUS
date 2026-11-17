"""Lane A wave 14: core.execution_backbone.backbone dispatch and stop branches."""

import queue
from concurrent.futures import Future

import pytest

from core.execution_backbone import backbone as bb


def _ok(value):
    return value * 2


def _boom():
    raise ValueError("kaboom")


class _Slots:
    """Fake semaphore whose acquire runs a hook and returns a scripted answer."""

    def __init__(self, answers, hook=None):
        self.answers = list(answers)
        self.hook = hook
        self.released = 0

    def acquire(self, timeout=None):
        if self.hook is not None:
            self.hook()
        return self.answers.pop(0)

    def release(self):
        self.released += 1


class _Queue:
    """Fake queue whose get runs a hook and returns or raises a scripted item."""

    def __init__(self, items, hook=None):
        self.items = list(items)
        self.hook = hook
        self.put_back = []
        self.done = 0

    def empty(self):
        return not self.items

    def qsize(self):
        return len(self.items)

    def get(self, timeout=None):
        if self.hook is not None:
            self.hook()
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def put(self, item):
        self.put_back.append(item)

    def task_done(self):
        self.done += 1


class _Executor:
    def __init__(self, exc=None):
        self.exc = exc
        self.submitted = []

    def submit(self, func, task):
        if self.exc is not None:
            raise self.exc
        self.submitted.append(task)
        fut = Future()
        fut.set_result(None)
        return fut


def _task(seq=1, func=_ok, args=(3,)):
    return bb._PriorityTask(
        priority=5, sequence=seq, task_id="t%d" % seq, func=func, args=args
    )


def test_p95_empty_and_values():
    assert bb._p95([]) is None
    assert bb._p95([1.0, 2.0, 3.0]) == 3.0
    assert bb._p95([float(i) for i in range(1, 21)]) == 19.0


def test_priority_task_ordering():
    assert _task(1) < _task(2)
    hi = bb._PriorityTask(priority=1, sequence=9, task_id="h", func=_ok)
    assert hi < _task(1)


def test_init_clamps_workers_and_initial_metrics():
    b = bb.ExecutionBackbone(max_workers=0, max_memory_mb=10)
    assert b.max_workers == 1
    m = b.get_metrics()
    assert m["running"] is False
    assert m["queue_wait_p95_seconds"] is None
    assert m["outstanding_work"] == 0
    assert m["remote_runner_capacity_slots"] is None
    assert m["merge_admission"] == "HOLD"


def test_real_run_success_and_failure(capsys):
    b = bb.ExecutionBackbone(max_workers=2)
    b.start()
    b.start()  # second start while running is a no-op
    b.schedule_task("good", _ok, args=(4,))
    b.schedule_task("bad", _boom, priority=1)
    b.schedule_task("kw", _ok, kwargs={"value": 1})
    b.stop(wait=True, timeout=5.0)
    m = b.get_metrics()
    assert m["tasks_submitted"] == 3
    assert m["tasks_executed"] == 2
    assert m["tasks_failed"] == 1
    assert m["service_sample_n"] == 3
    assert m["queue_wait_sample_n"] == 3
    assert m["currently_running"] == 0
    assert m["admitted_inflight"] == 0
    assert b._executor is None and b._worker_thread is None
    assert "Task 'bad' failed: kaboom" in capsys.readouterr().out
    # After a full stop the backbone can be started again.
    b.start()
    b.stop()


def test_start_while_stop_in_progress_raises():
    b = bb.ExecutionBackbone()
    b._executor = _Executor()
    with pytest.raises(RuntimeError, match="BACKBONE_STOP_IN_PROGRESS"):
        b.start()


def test_stop_timeout_raises():
    class _Stuck:
        def join(self, timeout=None):
            self.timeout = timeout

        def is_alive(self):
            return True

    b = bb.ExecutionBackbone()
    b._worker_thread = _Stuck()
    with pytest.raises(TimeoutError, match="BACKBONE_DRAIN_INCOMPLETE"):
        b.stop(timeout=0.01)


def test_stop_without_wait_keeps_handles():
    b = bb.ExecutionBackbone(max_workers=1)
    b.start()
    b.stop(wait=False)
    assert b._stop_without_drain is True
    assert b._executor is not None
    b._worker_thread.join(timeout=2.0)
    b.stop(wait=True)
    assert b._executor is None


def test_stop_never_started_is_noop():
    b = bb.ExecutionBackbone()
    b.stop()
    b.stop(wait=False)
    assert b._running is False


def test_dispatch_returns_when_stopped_without_drain():
    b = bb.ExecutionBackbone()
    b._stop_without_drain = True
    b.task_queue.put(_task())
    b._dispatch_loop()
    assert b.task_queue.qsize() == 1


def test_dispatch_slot_timeout_then_exit():
    b = bb.ExecutionBackbone()
    b._running = True

    def stop_flag():
        b._stop_without_drain = True

    b._slots = _Slots([False], hook=stop_flag)
    b._dispatch_loop()
    assert b._slots.released == 0


def test_dispatch_stop_after_slot_acquire_releases():
    b = bb.ExecutionBackbone()
    b._running = True

    def stop_flag():
        b._stop_without_drain = True

    b._slots = _Slots([True], hook=stop_flag)
    b._dispatch_loop()
    assert b._slots.released == 1


def test_dispatch_queue_empty_releases_and_loops():
    b = bb.ExecutionBackbone()
    b._running = True

    def halt():
        b._running = False

    b.task_queue = _Queue([queue.Empty()], hook=halt)
    b._slots = _Slots([True])
    b._dispatch_loop()
    assert b._slots.released == 1


def test_dispatch_stop_race_after_dequeue_requeues():
    b = bb.ExecutionBackbone()
    b._running = True
    task = _task()

    def stop_flag():
        b._stop_without_drain = True

    b.task_queue = _Queue([task], hook=stop_flag)
    b._slots = _Slots([True])
    b._dispatch_loop()
    assert b.task_queue.put_back == [task]
    assert b.task_queue.done == 1
    assert b._slots.released == 1
    assert b.tasks_failed == 0 and b.tasks_cancelled_at_admission == 0


def test_dispatch_without_executor_cancels_at_admission():
    b = bb.ExecutionBackbone()
    b.task_queue.put(_task())
    b._dispatch_loop()
    assert b.tasks_cancelled_at_admission == 1
    assert b._admitted == 0
    assert b.get_metrics()["queue_size"] == 0


def test_dispatch_submit_runtime_error_is_not_failure():
    b = bb.ExecutionBackbone()
    b._executor = _Executor(exc=RuntimeError("shutdown"))
    b.task_queue.put(_task())
    b._dispatch_loop()
    assert b.tasks_cancelled_at_admission == 1
    assert b.tasks_failed == 0
    assert b._admitted == 0


def test_dispatch_submit_records_future_and_prunes_done():
    b = bb.ExecutionBackbone(max_workers=3)
    ex = _Executor()
    b._executor = ex
    b.task_queue.put(_task(1))
    b.task_queue.put(_task(2))
    b._dispatch_loop()
    assert [t.task_id for t in ex.submitted] == ["t1", "t2"]
    assert len(b._futures) == 1  # the earlier done future was pruned
    assert b._admitted == 2
    m = b.get_metrics()
    assert m["admitted_not_started"] == 2
    assert m["outstanding_work"] == 2


def test_execute_task_success_and_failure(capsys):
    b = bb.ExecutionBackbone(max_workers=1)
    b._slots.acquire()
    b._admitted = 1
    assert b._execute_task(_task(1)) == 6
    b._slots.acquire()
    b._admitted = 1
    assert b._execute_task(_task(2, func=_boom, args=())) is None
    assert b.tasks_executed == 1
    assert b.tasks_failed == 1
    assert b._peak_active == 1
    assert b._active == 0
    assert b.get_metrics()["service_p95_seconds"] is not None
    assert "Task 't2' failed" in capsys.readouterr().out
