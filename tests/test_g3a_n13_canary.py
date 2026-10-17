"""G3A N13 four-source breadth canary, read-only production tests.

All writes happen inside TemporaryDirectory sandboxes. A reproduced symptom is
a candidate test finding, not a root closure or security/merge waiver.
"""
from __future__ import annotations
import ast
import contextlib
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from DMAIC_V3.phases.phase4_improve import CodeImprover
from DMAIC_V3.phases.phase8_todo_management import TODOTracker, Phase8TODOManagement
from DMAIC_V3.debug_pipeline import PipelineDebugger
from cicd_github_orchestrator import CICDGitHubOrchestrator, MetricsSnapshot


def symptom(name, observed, detail):
    print("N13_CANDIDATE_SYMPTOM=" + json.dumps({
        "id": name, "reproduced": bool(observed), "detail": detail,
        "evidence_class": "BOUNDED_ADVERSARIAL_FIXTURE",
        "accepted_causal_root": False, "merge_admission": "HOLD"
    }, sort_keys=True), flush=True)


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def source(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path


class Phase4ImproveCanary(Sandbox):
    def setUp(self):
        super().setUp()
        self.worker = CodeImprover(self.root)

    def test_add_missing_docstring_preserves_simple_syntax(self):
        path = self.source("function.py", "def f(x):\n    return x + 1\n")
        result = self.worker.add_missing_docstrings(path)
        self.assertTrue(result["success"])
        self.assertEqual(result["modifications"], 1)
        self.assertTrue(ast.get_docstring(ast.parse(path.read_text()).body[0]))

    def test_existing_docstrings_are_idempotent(self):
        path = self.source("existing.py", 'def f():\n    """Already documented."""\n    return 1\n')
        before = path.read_bytes()
        result = self.worker.add_missing_docstrings(path)
        self.assertFalse(result["success"])
        self.assertEqual(before, path.read_bytes())

    def test_invalid_python_is_not_silently_rewritten(self):
        path = self.source("bad.py", "def broken(:\n    pass\n")
        before = path.read_bytes()
        result = self.worker.add_missing_docstrings(path)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(before, path.read_bytes())

    def test_add_type_hints_produces_valid_ast(self):
        path = self.source("hint.py", "def f(value):\n    return value\n")
        result = self.worker.add_type_hints(path)
        self.assertTrue(result["success"])
        self.assertEqual(result["modifications"], 1)
        self.assertEqual(ast.parse(path.read_text()).body[-1].returns.id, "Any")

    def test_removal_of_one_entire_unused_import_is_safe(self):
        path = self.source("unused.py", "import math\nvalue = 1\n")
        result = self.worker.remove_unused_imports(path)
        self.assertTrue(result["success"])
        self.assertNotIn("import math", path.read_text())
        self.assertEqual(ast.literal_eval(ast.parse(path.read_text()).body[0].value), 1)

    def test_long_comment_is_not_reformatted(self):
        path = self.source("comment.py", "#" + "x"*140 + "\nvalue = 1\n")
        before = path.read_bytes()
        result = self.worker.fix_long_lines(path, max_length=60)
        self.assertFalse(result["success"])
        self.assertEqual(before, path.read_bytes())

    def test_mixed_import_line_source_loss_is_observed_not_waived(self):
        path = self.source("mixed.py", "from math import sqrt, floor\nvalue = floor(3.2)\n")
        result = self.worker.remove_unused_imports(path)
        after = path.read_text()
        broken = "floor(" in after and "import floor" not in after and "from math import" not in after
        symptom("PHASE4_MIXED_IMPORT_CLAUSE_DELETION", broken,
                "A partially unused from-import can lose a live name")
        self.assertIn("value = floor(3.2)", after)
        self.assertIn("success", result)


class Phase8TodoCanary(Sandbox):
    def setUp(self):
        super().setUp()
        self.tracker = TODOTracker(self.root)

    def test_register_todo_sets_defaults_and_registry(self):
        key = self.tracker.register_todo({"phase":"phase8","description":"check","timestamp":"N13"})
        self.assertEqual(len(key), 12)
        doc = self.tracker._load_global_registry()
        self.assertEqual(doc["total_todos"], 1)
        self.assertEqual(doc["todos"][0]["status"], "pending")
        self.assertEqual(doc["todos"][0]["priority"], "medium")

    def test_register_same_semantic_identity_upserts(self):
        first = {"phase":"phase8","description":"dedup","timestamp":"fixed"}
        key1 = self.tracker.register_todo(first)
        key2 = self.tracker.register_todo({**first,"agent":"owner"})
        self.assertEqual(key1,key2)
        self.assertEqual(self.tracker._load_global_registry()["total_todos"],1)

    def test_status_and_priority_filters_are_disjoint(self):
        self.tracker.register_todo({"phase":"phase4","description":"first","timestamp":"1","priority":"high"})
        self.tracker.register_todo({"phase":"phase8","description":"second","timestamp":"2","priority":"low"})
        self.assertEqual(len(self.tracker.get_todos_by_status("pending")),2)
        self.assertEqual(len(self.tracker.get_todos_by_priority("high")),1)
        self.assertEqual(len(self.tracker.get_todos_by_phase("phase8")),1)

    def test_completion_percentage_updates_after_status_change(self):
        key=self.tracker.register_todo({"phase":"phase8","description":"completion","timestamp":"3"})
        self.assertEqual(self.tracker._load_global_registry()["statistics"]["completion_rate"],0)
        self.tracker.update_todo_status(key,"completed")
        self.assertEqual(self.tracker._load_global_registry()["statistics"]["completion_rate"],100)

    def test_empty_statistics_have_zero_completion_not_missing(self):
        stats=self.tracker._calculate_statistics([])
        self.assertEqual(stats["total"],0)
        self.assertEqual(stats["completion_rate"],0)

    def test_priority_ranks_urgent_open_above_low_completed(self):
        phase=Phase8TODOManagement.__new__(Phase8TODOManagement)
        rows=[
          {"priority":"low","phase":"phase8","status":"completed","description":"routine"},
          {"priority":"high","phase":"phase2","status":"pending","description":"critical blocker"},
        ]
        out=phase._prioritize_todos(rows)
        self.assertIs(out[0],rows[1])
        self.assertEqual(len(out),2)

    def test_bad_phase_type_is_observed_as_candidate(self):
        phase=Phase8TODOManagement.__new__(Phase8TODOManagement)
        row={"priority":"medium","phase":None,"description":"check","status":"pending"}
        try:
            phase._prioritize_todos([row])
        except (TypeError,AttributeError) as e:
            reproduced,detail=True,type(e).__name__
        else:
            reproduced,detail=False,"handled"
        symptom("PHASE8_NONSTRING_PHASE_EXCEPTION",reproduced,detail)
        self.assertIn("phase",row)


class DebugPipelineCanary(Sandbox):
    def setUp(self):
        super().setUp()
        self.debugger=PipelineDebugger(self.root)

    def test_missing_directories_are_reported_as_critical(self):
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.debugger._check_dmaic_structure()
        self.assertEqual(r["status"],"error")
        self.assertEqual(len(r["missing_dirs"]),5)
        self.assertTrue(any(i["category"]=="structure" for i in self.debugger.issues))

    def test_present_directories_are_accepted(self):
        for p in ("DMAIC_V3","DMAIC_V3/phases","DMAIC_V3/core","DMAIC_V3/convergence","DMAIC_V3_OUTPUT"):
            (self.root/p).mkdir(parents=True,exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.debugger._check_dmaic_structure()
        self.assertEqual(r["status"],"ok")
        self.assertFalse(self.debugger.issues)

    def test_syntax_error_is_detected_in_phase_file(self):
        self.source("DMAIC_V3/phases/phase4_corrupt.py","def bad(:\n  pass\n")
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.debugger._check_imports()
        self.assertEqual(r["status"],"error")
        self.assertTrue(any(x["category"]=="imports" for x in self.debugger.issues))

    def test_python_environment_probe_reports_version(self):
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.debugger._check_python_env()
        self.assertEqual(r["status"],"ok")
        self.assertIn("version",r["details"])

    def test_missing_module_import_is_not_actually_resolved(self):
        self.source("DMAIC_V3/phases/phase4_probe.py",
                    "import n13_completely_nonexistent_module_4837\n")
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.debugger._check_imports()
        found=r["status"]=="ok" and not r["errors"]
        symptom("DEBUGGER_IMPORT_CHECK_IS_SYNTAX_ONLY",found,
                "Syntactically valid missing dependency is reported import OK")
        self.assertIn(r["status"],("ok","error"))

    def test_phase_file_census_preserves_missing_entry(self):
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.debugger._check_phase_files()
        self.assertEqual(len(r["phases"]),9)
        self.assertTrue(self.debugger.issues)


class CICDOrchestratorCanary(Sandbox):
    def setUp(self):
        super().setUp()
        with contextlib.redirect_stdout(io.StringIO()):
            self.orchestrator=CICDGitHubOrchestrator(self.root)

    def test_default_tool_config_fails_safely_closed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            tools=self.orchestrator.verify_git_tools()
        self.assertFalse(tools["gitlens"]["configured"])
        self.assertFalse(tools["gitkraken"]["pro_token_set"])

    def test_malformed_vscode_config_returns_disabled(self):
        self.source(".vscode/settings.json","invalid json")
        with contextlib.redirect_stdout(io.StringIO()):
            state=self.orchestrator._load_gitlens_config()
        self.assertFalse(state["enabled"])

    def test_duplicate_file_inventory_does_not_merge_source_paths(self):
        self.source("a.py","# Version: 1.0\nvalue = 1\n")
        self.source("b.py","# Version: 1.0\nvalue = 1\n")
        self.source(".venv/skip.py","value = 2\n")
        with contextlib.redirect_stdout(io.StringIO()):
            m=self.orchestrator.collect_metrics("N13")
        self.assertEqual(m.python_files,2)
        self.assertEqual(m.duplicate_files,1)
        self.assertEqual(len(m.file_hashes),2)

    def test_metrics_comparison_missing_pair_is_not_success(self):
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.orchestrator.compare_metrics()
        self.assertEqual(r,{"error":"Missing metrics"})

    def test_metric_diffs_keep_sign_and_denominator(self):
        snap=MetricsSnapshot("N13",4,20,2,1,2,1,{}, {})
        self.orchestrator.pre_metrics=snap
        self.orchestrator.post_metrics=replace(
            snap,total_files=5,total_lines=22,duplicate_files=0,
            import_issues=1,version_headers=2)
        with contextlib.redirect_stdout(io.StringIO()):
            d=self.orchestrator.compare_metrics()
        self.assertEqual(d["files_changed"],1)
        self.assertEqual(d["duplicates_removed"],1)
        self.assertEqual(d["import_issues_fixed"],1)
        self.assertEqual(d["version_headers_added"],1)

    def test_no_final_newline_line_count_is_candidate(self):
        self.source("lonely.py","value=42")
        with contextlib.redirect_stdout(io.StringIO()):
            r=self.orchestrator.collect_metrics("N13-edge")
        candidate=r.python_files==1 and r.total_lines==0
        symptom("ORCHESTRATOR_UNTERMINATED_LAST_LINE_UNDERCOUNT",candidate,
                "A nonempty Python line without LF contributes 0 to total_lines")
        self.assertEqual(r.python_files,1)


if __name__=="__main__":
    unittest.main()
