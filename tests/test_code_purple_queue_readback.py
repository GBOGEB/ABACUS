"""Regression contract for the Code Purple queue-view and offline readback producer."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "code_purple_execution_graph.html"
GENERATOR = ROOT / "scripts" / "everred_queue_snapshot.py"

class QueueReadbackTests(unittest.TestCase):
    def test_read_only_panel_and_accessible_controls(self):
        s = SOURCE.read_text(encoding="utf-8")
        for key in ("id=\"everredQueue\"", "id=\"evqRefresh\"", "id=\"evqSearch\"",
                    "id=\"evqView\"", "id=\"evqStatus\"", "id=\"evqRows\"",
                    "aria-live=\"polite\"", "evq-status-queued", "evq-trigger-workflow_run",
                    "evqOpen", "PARTIAL (page cap)"):
            self.assertIn(key, s)
        self.assertNotIn("actions/runs/dispatches", s)
        self.assertNotIn("gh pr merge", s)
    def test_generator_partial_and_idempotent(self):
        spec = importlib.util.spec_from_file_location("everred_queue_snapshot", GENERATOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        row = {"id": 17, "name": "CI", "event": "workflow_run",
               "created_at": "2026-10-14T10:00:00Z", "head_sha": "a"*40}
        result = module.normalize({"total_count": 2, "workflow_runs": [row]},
                                  {"total_count": 1, "workflow_runs": [row]})
        self.assertEqual(len(result["runs"]), 1)
        self.assertTrue(result["partial"])
        self.assertTrue(result["counts"]["queued"]["partial"])
        with self.assertRaises(ValueError):
            module.normalize({"total_count": 0, "workflow_runs": [row]},
                             {"total_count": 0, "workflow_runs": []})

if __name__ == "__main__":
    unittest.main()
