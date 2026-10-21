"""N15 Phase 8 native branch breadth; only temporary workspace artifacts.

No real queue, runner, source tree or governance file is modified. Candidate
symptoms remain evidence for owner review and confer no accepted root closure.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from DMAIC_V3.phases.phase8_todo_management import TODOTracker, Phase8TODOManagement

class N15Sandbox(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.tracker = TODOTracker(self.root)
        self.phase = Phase8TODOManagement.__new__(Phase8TODOManagement)
        self.phase.config = SimpleNamespace(workspace_root=str(self.root))

    def write(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def test_tracker_empty_status_and_priority_filters(self):
        self.assertEqual(self.tracker.get_todos_by_status("pending"), [])
        self.assertEqual(self.tracker.get_todos_by_priority("high"), [])
        self.assertEqual(self.tracker.get_todos_by_phase("phase8"), [])

    def test_tracker_status_filter_disjoint_from_phase(self):
        key = self.tracker.register_todo({"phase": "phase8", "description": "a", "timestamp": "t"})
        self.tracker.register_todo({"phase": "phase4", "description": "b", "timestamp": "t"})
        self.tracker.update_todo_status(key, "done")
        self.assertEqual(len(self.tracker.get_todos_by_status("pending")), 1)
        self.assertEqual(len(self.tracker.get_todos_by_phase("phase8")), 1)
        self.assertEqual(self.tracker._load_global_registry()["statistics"]["completion_rate"], 50.0)

    def test_tracker_explicit_priority_round_trip(self):
        self.tracker.register_todo({"phase": "phase8", "description": "critical",
                                    "timestamp": "a", "priority": "high", "agent": "owner"})
        registry = self.tracker._load_global_registry()
        self.assertEqual(registry["statistics"]["by_priority"]["high"], 1)
        self.assertEqual(registry["statistics"]["by_agent"]["owner"], 1)
        self.assertEqual(len(self.tracker.get_todos_by_priority("high")), 1)

    def test_tracker_unknown_status_update_is_noop(self):
        self.tracker.register_todo({"phase": "phase0", "description": "x", "timestamp": "a"})
        before = self.tracker._load_global_registry()["todos"][0]["status"]
        self.tracker.update_todo_status("nonexistent-key", "completed")
        after = self.tracker._load_global_registry()
        self.assertEqual(after["todos"][0]["status"], before)
        self.assertEqual(after["total_todos"], 1)

    def test_tracker_same_identity_upserts_without_duplicate(self):
        row = {"phase": "phase4", "description": "same", "timestamp": "one"}
        key = self.tracker.register_todo(row)
        self.assertEqual(self.tracker.register_todo({**row, "status": "completed"}), key)
        registry = self.tracker._load_global_registry()
        self.assertEqual(registry["total_todos"], 1)
        self.assertEqual(registry["statistics"]["completion_rate"], 100.0)

    def test_tracker_statistics_mixed_done_completed_and_progress(self):
        rows = [{"status": "done", "priority": "low", "phase": "p", "agent": "a"},
                {"status": "completed", "priority": "high", "phase": "p", "agent": "a"},
                {"status": "in_progress", "priority": "medium", "phase": "q", "agent": "b"}]
        stats = self.tracker._calculate_statistics(rows)
        self.assertEqual(stats["total"], 3)
        self.assertAlmostEqual(stats["completion_rate"], 200.0 / 3.0)
        self.assertEqual(stats["by_phase"]["p"], 2)

    def test_prioritization_boosts_critical_pending_item(self):
        rows = [{"priority": "low", "phase": "phase8", "status": "completed", "description": "routine"},
                {"priority": "high", "phase": "phase1", "status": "pending", "description": "urgent blocker"}]
        self.assertIs(self.phase._prioritize_todos(rows)[0], rows[1])

    def test_prioritization_handles_unknown_phase_without_owner_override(self):
        rows = [{"priority": "low", "phase": "not-a-number", "status": "pending",
                 "description": "review"},
                {"priority": "high", "phase": "phase9", "status": "pending",
                 "description": "required"}]
        result = self.phase._prioritize_todos(rows)
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], rows[1])

    def test_prioritization_empty_input_has_no_phantom_tasks(self):
        self.assertEqual(self.phase._prioritize_todos([]), [])

    def test_markdown_external_todos_completed_and_pending(self):
        self.write("TODO_A.md", "- [ ] fix critical issue\n- [x] done\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rows = self.phase._parse_todo_files()
        self.assertEqual([r["status"] for r in rows], ["pending", "completed"])
        self.assertTrue(all(r["phase"] == "external" for r in rows))

    def test_yaml_external_mapping_and_list_shapes(self):
        self.write("TODO_A.yaml", "todos:\n  - description: from-mapping\n    phase: phase8\n")
        self.write("TODO_B.yml", "- description: from-list\n  phase: phase7\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rows = self.phase._parse_todo_files()
        self.assertEqual({r["description"] for r in rows}, {"from-mapping", "from-list"})
        self.assertTrue(all(r.get("source_file") for r in rows))

    def test_yaml_invalid_file_does_not_hide_other_valid_todos(self):
        self.write("TODO_BAD.yaml", "todos: [broken\n")
        self.write("TODO_GOOD.md", "- [ ] retained\n")
        with contextlib.redirect_stdout(io.StringIO()):
            rows = self.phase._parse_todo_files()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "retained")

    def test_links_join_agent_artifact_phase_and_action(self):
        rows = [{"todo_id": "t1", "agent": "a", "phase": "phase8",
                 "artifacts": ["receipt.json"], "actions": ["review"]},
                {"todo_id": "t2", "agent": "a", "phase": "phase3",
                 "artifacts": ["receipt.json"], "actions": ["repair"]}]
        links = self.phase._create_todo_links(rows)
        self.assertEqual(links["agent_to_todos"]["a"], ["t1", "t2"])
        self.assertEqual(links["artifact_to_todos"]["receipt.json"], ["t1", "t2"])
        self.assertEqual(links["phase_to_todos"]["phase8"], ["t1"])
        self.assertEqual(links["action_to_todos"]["repair"], ["t2"])

    def test_link_graph_handles_missing_fields(self):
        links = self.phase._create_todo_links([{}])
        self.assertEqual(links["agent_to_todos"]["unknown"], ["unknown"])
        self.assertEqual(links["phase_to_todos"]["unknown"], ["unknown"])
        self.assertEqual(links["artifact_to_todos"], {})


if __name__ == "__main__":
    unittest.main()
