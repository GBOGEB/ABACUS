"""W48 native-local behavioral, mutation and negative RECURSE tests."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml

from scripts.cbd_recurse_fanout_w48 import _unique_pairs, compile_snapshot

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs/ci/CBD_RECURSE_W48_SYNTHETIC.json").read_text())
MANIFEST = yaml.safe_load((ROOT / "ci/cbd_recurse_local_w48.yaml").read_text())


class RecurseFanoutW48Tests(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(DATA)
        self.manifest = copy.deepcopy(MANIFEST)

    def compile(self):
        return compile_snapshot(self.data, self.manifest)

    def fail(self, text=None):
        with self.assertRaisesRegex(ValueError, text or "."):
            self.compile()

    def node(self, name):
        return next(x for x in self.data["nodes"] if x["id"] == name)

    def test_positive_structural_reach_is_not_causal_credit(self):
        result = self.compile()
        root = next(x for x in result["graph"]["observations"] if x["id"] == "event_main")
        self.assertEqual(root["direct_outdegree"], 3)
        self.assertEqual(root["reachable_nodes"], 8)
        self.assertIn("javascript", root["reached_segments"])
        self.assertFalse(root["reach_is_causal_proof"])
        self.assertEqual(result["dmaic"]["CONTROL"]["admission"], "HOLD")
        self.assertIsNone(result["dmaic"]["CONTROL"]["accepted_root_open"])
        self.assertIsNone(result["dmaic"]["CONTROL"]["authenticated_crew_launch"])

    def test_two_fixed_blob_coverage_pairs_are_measured_only_as_candidate(self):
        m = self.compile()["matched_coverage_candidates"][0]
        self.assertEqual((m["measures"]["statements"]["before"], m["measures"]["statements"]["after"]), (184, 212))
        self.assertEqual(m["measures"]["branches"]["delta"], 12)
        self.assertEqual(m["measures"]["statements"]["eligible"], 214)
        self.assertEqual(m["acceptance"], "CANDIDATE_LOCAL_VALIDATION_ONLY")

    def test_read_only_disjoint_task_selection(self):
        plan = self.compile()["dmaic"]["IMPROVE"]
        self.assertEqual(plan["candidates"], ["t10_js", "t20_py"])
        self.assertEqual(plan["decisions"]["t30_py_collision"], "POOL_CAP")
        self.assertEqual(plan["decisions"]["t40_yaml"], "UPSTREAM_NOT_VERIFIED")
        self.assertEqual(plan["decisions"]["t50_review"], "MANUAL_OR_MUTATING_HELD")
        self.assertEqual(plan["decisions"]["t60_mutation"], "MANUAL_OR_MUTATING_HELD")
        self.assertFalse(plan["execution_performed"])

    def test_explicit_unknown_is_not_zero(self):
        r = self.compile()
        self.assertIsNone(r["dmaic"]["ANALYZE"]["deduplicated_engineering_root_count"])
        self.assertIsNone(r["dmaic"]["CONTROL"]["accepted_root_closed"])
        self.assertIsNone(r["dmaic"]["CONTROL"]["accepted_main_coverage_delta"])

    def test_canonical_byte_fingerprint_is_input_order_invariant(self):
        first = self.compile()["receipt_sha256"]
        self.data["nodes"].reverse()
        self.data["edges"].reverse()
        self.data["tasks"].reverse()
        self.assertEqual(self.compile()["receipt_sha256"], first)

    def test_segment_and_branch_flow_denominator_is_bounded(self):
        vis = self.compile()["graph"]["visibility"]
        self.assertEqual(vis["expected_segment_count"], 8)
        self.assertEqual(vis["observed_segment_count"], 7)
        self.assertEqual(vis["cross_segment_edges"], 7)
        self.assertEqual(vis["cross_branch_edges"], 3)
        self.assertFalse(vis["penetration_is_native_acceptance"])

    def test_reject_duplicate_json_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            json.loads('{"id":1,"id":2}', object_pairs_hook=_unique_pairs)

    def test_reject_unknown_input_schema(self):
        self.data["schema"] = "future"
        self.fail("schema")

    def test_reject_additional_authority_fields(self):
        self.data["approved"] = True
        self.fail("unapproved")

    def test_reject_fake_control_sha(self):
        self.data["control"]["head_sha"] = "latest"
        self.fail("identity")

    def test_reject_unapproved_origin(self):
        self.data["control"]["origin"] = "AUTHENTICATED_LAUNCH"
        self.fail("origin")

    def test_reject_duplicate_node(self):
        self.data["nodes"].append(copy.deepcopy(self.data["nodes"][0]))
        self.fail("duplicate")

    def test_reject_unapproved_segment(self):
        self.node("js_consumer")["segment"] = "unspecified_segment"
        self.fail("segment")

    def test_reject_stale_sha_in_native_node(self):
        self.node("js_consumer")["sha"] = "stale"
        self.fail("SHA")

    def test_reject_boolean_native_id(self):
        self.node("js_consumer")["run_id"] = True
        self.fail("identity")

    def test_reject_partial_job_identity(self):
        self.node("scheduler_queue")["attempt"] = None
        self.fail("identity")

    def test_reject_duplicate_native_job_and_attempt(self):
        j = self.node("js_consumer")
        j.update(run_id=102, attempt=1, job_id=1002)
        self.fail("duplicate native")

    def test_reject_premature_terminal_conclusion(self):
        self.node("scheduler_queue")["conclusion"] = "success"
        self.fail("nonterminal")

    def test_reject_false_green_completed_node(self):
        self.node("js_consumer")["conclusion"] = None
        self.fail("terminal")

    def test_reject_proposal_claiming_native_job(self):
        self.node("federation_proposal").update(run_id=555, attempt=1, job_id=556)
        self.fail("local/proposal")

    def test_reject_missing_artifact_digest(self):
        self.node("python_after")["coverage"]["artifact_sha256"] = None
        self.fail("digest")

    def test_reject_forged_artifact_run_binding(self):
        self.node("python_after")["coverage"]["artifact_url"] = "https://github.com/GBOGEB/ABACUS/actions/runs/999/artifacts/991"
        self.fail("artifact URL")

    def test_reject_coverage_with_no_native_job(self):
        self.node("python_after")["job_id"] = None
        self.fail("successful native job")

    def test_reject_coverage_invalid_boolean_counts(self):
        self.node("python_after")["coverage"]["branches"]["covered"] = True
        self.fail("numerator")

    def test_reject_coverage_denominator_overrun(self):
        self.node("python_after")["coverage"]["branches"]["covered"] = 63
        self.fail("numerator")

    def test_reject_cross_blob_matched_coverage(self):
        self.node("python_after")["coverage"]["source_blob_sha"] = "e" * 40
        self.fail("not matched")

    def test_reject_cross_cell_matched_coverage(self):
        self.node("python_after")["coverage"]["cell"] = "windows_py311"
        self.fail("not matched")

    def test_reject_denominator_drift(self):
        self.node("python_after")["coverage"]["branches"]["eligible"] = 63
        self.fail("not matched")

    def test_reject_orphan_edge(self):
        self.data["edges"].append({"from": "absent", "to": "python_base", "kind": "depends_on"})
        self.fail("orphan")

    def test_reject_cyclic_edge(self):
        self.data["edges"].append({"from": "security_red", "to": "event_main", "kind": "depends_on"})
        self.fail("cyclic")

    def test_reject_duplicate_typed_edge(self):
        self.data["edges"].append(copy.deepcopy(self.data["edges"][0]))
        self.fail("duplicate typed")

    def test_reject_task_dependency_cycle(self):
        task = next(t for t in self.data["tasks"] if t["id"] == "t00_verified_base")
        task["depends_on"] = ["t40_yaml"]
        self.fail("cyclic")

    def test_reject_task_absolute_and_traversal_paths(self):
        task = next(t for t in self.data["tasks"] if t["id"] == "t20_py")
        for path in ("../source.py", "C:\\not_allowed.py", "/absolute/denied_path", "x//y"):
            task["paths"] = [path]
            self.fail("paths")

    def test_reject_unverified_completed_task(self):
        t = next(t for t in self.data["tasks"] if t["id"] == "t00_verified_base")
        t["evidence_node"] = "yaml_lint"
        self.fail("successful native")

    def test_reject_manually_forged_completed_task(self):
        t = next(t for t in self.data["tasks"] if t["id"] == "t40_yaml")
        t["state"] = "done"
        t["evidence_node"] = "federation_proposal"
        self.fail("successful native")

    def test_reject_mutating_command_injection(self):
        t = next(t for t in self.data["tasks"] if t["id"] == "t20_py")
        t["command"] = "echo rejected-input"
        self.fail("unapproved")

    def test_pool_and_wave_caps_are_enforced(self):
        self.manifest["wave_limit"] = 1
        plan = self.compile()["dmaic"]["IMPROVE"]
        self.assertEqual(plan["candidates"], ["t10_js"])
        self.assertEqual(plan["decisions"]["t20_py"], "WAVE_CAP")

    def test_invalid_manifest_capacity_fails(self):
        self.manifest["pool_capacities"]["node"] = True
        self.fail("pool")

    def test_all_four_primary_segments_have_structural_observations(self):
        groups = {g["segment"]: g for g in self.compile()["segments"]}
        for kind in ("python", "javascript", "yaml", "taskrunner"):
            with self.subTest(kind=kind):
                self.assertGreater(groups[kind]["observed_nodes"], 0)
        self.assertEqual(groups["coverage"]["observed_nodes"], 0)


if __name__ == "__main__":
    unittest.main()
