import unittest

from scripts.emit_keb_runtime_status import build_keb_runtime_status


class TestEmitKebRuntimeStatus(unittest.TestCase):
    def test_runtime_status_closes_bidirectional_feedback_loop(self):
        report = build_keb_runtime_status(timeout_seconds=2.0)

        self.assertEqual("ok", report["status"])
        self.assertEqual("completed", report["completion_status"])
        self.assertEqual(2, report["queue"]["tasks_submitted"])
        self.assertEqual(2, report["queue"]["tasks_executed"])
        self.assertEqual(0, report["queue"]["tasks_failed"])
        self.assertEqual(0, report["queue"]["queue_size_after_stop"])
        self.assertTrue(report["feedback_loop"]["complete"])
        self.assertEqual(["DOW_TO_KEB", "KEB_TO_DOW"], report["feedback_loop"]["directions_observed"])

    def test_runtime_status_carries_dmaic_control_context(self):
        report = build_keb_runtime_status(timeout_seconds=2.0)

        self.assertIn("define", report["dmaic"])
        self.assertIn("measure", report["dmaic"])
        self.assertIn("control", report["dmaic"])


if __name__ == "__main__":
    unittest.main()
