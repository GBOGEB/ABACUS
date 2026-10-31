"""W33 bounded-admission pool testflight; no remote scheduler/dispatch credit."""

import threading
import time
import unittest

from core.execution_backbone import ExecutionBackbone


def spin(predicate, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.005)
    return False


class TestW33BoundedBackbone(unittest.TestCase):
    def test_priority_preserved_under_saturation(self):
        lock = threading.Event()
        started = threading.Event()
        seen = []

        def first():
            started.set()
            self.assertTrue(lock.wait(3.0))
            seen.append("first")

        def named(label):
            seen.append(label)

        b = ExecutionBackbone(max_workers=1)
        b.start()
        try:
            b.schedule_task("first", first, priority=1)
            self.assertTrue(started.wait(2.0))
            b.schedule_task("low", named, priority=9, args=("low",))
            b.schedule_task("high", named, priority=0, args=("high",))
            self.assertTrue(spin(lambda: b.get_metrics()["waiting_queue_size"] == 2))
            self.assertEqual(b.get_metrics()["outstanding_work"], 3)
        finally:
            lock.set()
            b.stop(wait=True, timeout=4.0)
        self.assertEqual(seen, ["first", "high", "low"])

    def test_pool_saturation_is_not_hidden_in_executor(self):
        release = threading.Event()
        occupied = threading.Event()
        count = []

        def worker(n):
            count.append(n)
            if len(count) == 2:
                occupied.set()
            self.assertTrue(release.wait(3.0))

        b = ExecutionBackbone(max_workers=2)
        b.start()
        try:
            for i in range(7):
                b.schedule_task(str(i), worker, priority=i, args=(i,))
            self.assertTrue(occupied.wait(2.0))
            self.assertTrue(spin(lambda: b.get_metrics()["waiting_queue_size"] >= 5))
            m = b.get_metrics()
            self.assertEqual(m["currently_running"], 2)
            self.assertEqual(m["admitted_inflight"], 2)
            self.assertEqual(m["waiting_queue_size"], 5)
            self.assertEqual(m["outstanding_work"], 7)
            self.assertEqual(m["local_pool_utilization_pct"], 100.0)
            self.assertLessEqual(m["admitted_not_started"], 2)
        finally:
            release.set()
            b.stop(wait=True, timeout=5.0)
        self.assertEqual(b.get_metrics()["tasks_executed"], 7)
        self.assertEqual(b.get_metrics()["queue_size"], 0)
        self.assertEqual(b.get_metrics()["outstanding_work"], 0)

    def test_stable_fifo_among_equal_priorities(self):
        b = ExecutionBackbone(max_workers=1)
        seen = []
        for n in range(5):
            b.schedule_task(str(n), lambda i=n: seen.append(i), priority=2)
        b.start()
        b.stop(wait=True, timeout=4.0)
        self.assertEqual(seen, list(range(5)))

    def test_failure_does_not_consume_pool_forever(self):
        b = ExecutionBackbone(max_workers=1)
        results = []

        def fail():
            raise RuntimeError("intentional fail")

        b.schedule_task("negative", fail)
        b.schedule_task("recovery", lambda: results.append("PASS"))
        b.start()
        b.stop(wait=True, timeout=4.0)
        m = b.get_metrics()
        self.assertEqual(results, ["PASS"])
        self.assertEqual((m["tasks_executed"], m["tasks_failed"]), (1, 1))
        self.assertEqual(m["admitted_inflight"], 0)
        self.assertEqual(m["currently_running"], 0)

    def test_two_workers_do_not_exceed_configured_slots(self):
        lock = threading.Event()
        b = ExecutionBackbone(max_workers=2)
        b.start()
        try:
            for i in range(10):
                b.schedule_task(str(i), lambda: lock.wait(3.0))
            self.assertTrue(spin(lambda: b.get_metrics()["currently_running"] == 2))
            self.assertLessEqual(b.get_metrics()["peak_running"], 2)
            self.assertEqual(b.get_metrics()["executor_pending_bound"], 2)
        finally:
            lock.set()
            b.stop(wait=True, timeout=5.0)

    def test_queue_empty_does_not_mean_work_completed(self):
        release = threading.Event()
        started = threading.Event()
        b = ExecutionBackbone(max_workers=1)
        b.start()
        try:

            def slow():
                started.set()
                release.wait(3.0)

            b.schedule_task("slow", slow)
            self.assertTrue(started.wait(2.0))
            self.assertEqual(b.task_queue.qsize(), 0)
            self.assertEqual(b.get_metrics()["outstanding_work"], 1)
            self.assertEqual(b.get_metrics()["currently_running"], 1)
            self.assertEqual(b.get_metrics()["tasks_executed"], 0)
        finally:
            release.set()
            b.stop(wait=True, timeout=4.0)

    def test_prestart_priority_retained(self):
        b = ExecutionBackbone(max_workers=1)
        seen = []
        b.schedule_task("low", lambda: seen.append("low"), priority=5)
        b.schedule_task("high", lambda: seen.append("high"), priority=1)
        self.assertEqual(b.get_metrics()["waiting_queue_size"], 2)
        b.start()
        b.stop(wait=True, timeout=4.0)
        self.assertEqual(seen, ["high", "low"])

    def test_configured_capacity_and_remote_capacity_not_conflated(self):
        b = ExecutionBackbone(max_workers=0, max_memory_mb=128)
        m = b.get_metrics()
        self.assertEqual(m["configured_local_pool_slots"], 1)
        self.assertTrue(m["max_memory_mb_is_advisory"])
        self.assertIsNone(m["remote_runner_capacity_slots"])
        self.assertEqual(m["merge_admission"], "HOLD")
        self.assertIs(m["remote_dispatch_enabled"], False)
        self.assertIs(m["authority_transfer"], False)

    def test_queue_wait_p95_has_sample_n(self):
        b = ExecutionBackbone(max_workers=1)
        release = threading.Event()
        started = threading.Event()

        def delayed():
            started.set()
            release.wait(3.0)

        b.start()
        try:
            b.schedule_task("one", delayed)
            self.assertTrue(started.wait(2.0))
            b.schedule_task("two", lambda: None)
            time.sleep(0.035)
        finally:
            release.set()
            b.stop(wait=True, timeout=4.0)
        m = b.get_metrics()
        self.assertEqual(m["queue_wait_sample_n"], 2)
        self.assertGreater(m["queue_wait_p95_seconds"], 0.02)
        self.assertEqual(m["service_sample_n"], 2)
        self.assertIsNotNone(m["service_p95_seconds"])

    def test_no_queue_p95_is_unknown_not_zero(self):
        b = ExecutionBackbone(max_workers=3)
        m = b.get_metrics()
        self.assertIsNone(m["queue_wait_p95_seconds"])
        self.assertIsNone(m["service_p95_seconds"])
        self.assertEqual(m["queue_wait_sample_n"], 0)

    def test_stop_wait_drains_all_tasks(self):
        b = ExecutionBackbone(max_workers=2)
        seen = []
        for i in range(9):
            b.schedule_task(str(i), lambda n=i: seen.append(n))
        b.start()
        b.stop(wait=True, timeout=6.0)
        self.assertEqual(len(seen), 9)
        self.assertEqual(b.get_metrics()["outstanding_work"], 0)

    def test_restart_after_drained_stop(self):
        b = ExecutionBackbone(max_workers=1)
        seen = []
        b.schedule_task("a", lambda: seen.append("a"))
        b.start()
        b.stop(wait=True, timeout=4.0)
        b.schedule_task("b", lambda: seen.append("b"))
        b.start()
        b.stop(wait=True, timeout=4.0)
        self.assertEqual(seen, ["a", "b"])

    def test_no_fabricated_execution_when_stop_does_not_drain(self):
        release = threading.Event()
        started = threading.Event()
        b = ExecutionBackbone(max_workers=1)
        b.start()

        def slow():
            started.set()
            release.wait(2.0)

        b.schedule_task("running", slow)
        self.assertTrue(started.wait(2.0))
        b.schedule_task("queued", lambda: None)
        b.stop(wait=False)
        before = b.get_metrics()
        self.assertGreaterEqual(before["queue_size"], 1)
        self.assertEqual(before["tasks_executed"], 0)
        release.set()
        b.stop(wait=True, timeout=4.0)
        self.assertEqual(b.get_metrics()["tasks_executed"], 1)
        self.assertGreaterEqual(b.get_metrics()["queue_size"], 1)


if __name__ == "__main__":
    unittest.main()
