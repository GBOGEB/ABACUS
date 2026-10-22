"""Negative resource leases and DAG guards; NO worker launch authority."""
import importlib.util
import copy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/g3g_disjoint_crew.py"
spec = importlib.util.spec_from_file_location("g3g_disjoint_crew", FILE)
m = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(m)

SHA = "a" * 40
PARENTS = ["GOVERNANCE", "ADMISSION", "CREDENTIALS", "BROWSER", "FEDERATION"]


def sample():
    return {
        "schema": "codepurple.g3g_disjoint_plan.v1",
        "cohort": "G3G_READ_ONLY_TEST",
        "merge_admission": "HOLD", "authority_transfer": False,
        "active_workers_launched": None, "human_worker_hours": None,
        "parents": [{"id": x, "accepted_closed": False} for x in PARENTS],
        "lanes": [
            {"id": "gov", "repo": "GBOGEB/ABACUS", "parent": "GOVERNANCE",
             "head_sha": SHA, "state": "NATIVE_PASS", "depends_on": [],
             "lease_paths": ["ci/governance/tests/new.py"],
             "receipt": {"source_sha": SHA, "run_id": 100,
                         "attempt": 1, "job_id": 200, "conclusion": "success"},
             "first_red_fingerprint": None, "accepted_root_id": None,
             "worker_hours": None, "worker_capacity": None},
            {"id": "cred", "repo": "GBOGEB/pipeline-automation-hub",
             "parent": "CREDENTIALS", "head_sha": SHA,
             "state": "HOLD_OWNER", "depends_on": ["gov"],
             "lease_paths": [],
             "first_red_fingerprint": "NO_CROSS_REPO_READ_TOKEN",
             "observed_occurrences": 3, "accepted_root_id": None,
             "worker_hours": None, "worker_capacity": None},
            {"id": "probe", "repo": "GBOGEB/pipeline-automation-hub",
             "parent": "FEDERATION", "head_sha": SHA,
             "state": "READ_ONLY_PROBE", "depends_on": ["gov"],
             "lease_paths": ["mission-control/qa/probe.py"],
             "accepted_root_id": None, "worker_hours": None,
             "worker_capacity": None},
        ],
    }


class G3GDisjointCrewTests(unittest.TestCase):
    def test_disjoint_dag_has_one_read_only_unblocked_lane(self):
        x = m.assess(sample())
        self.assertEqual(x["total_lanes"], 3)
        self.assertEqual(x["read_only_unblocked_lanes"], ["probe"])
        self.assertEqual(x["graph_edges"], 2)
        self.assertEqual(x["max_dependency_depth_nodes_not_duration"], 2)
        self.assertEqual(x["source_observed_occurrences"],
                         {"NO_CROSS_REPO_READ_TOKEN": 3})
        self.assertIsNone(x["effective_runner_slots"])
        self.assertFalse(x["source_write_permission_granted_by_viewer"])

    def test_real_worker_launch_count_cannot_be_invented(self):
        data = sample()
        data["active_workers_launched"] = 3
        with self.assertRaisesRegex(ValueError, "authority"):
            m.assess(data)

    def test_dependency_cycle_fails_closed(self):
        data = sample()
        data["lanes"][0]["depends_on"] = ["probe"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            m.assess(data)

    def test_overlapping_nested_source_paths_rejected(self):
        data = sample()
        data["lanes"][1]["lease_paths"] = [
            "mission-control/qa"]
        with self.assertRaisesRegex(ValueError, "overlapping source lease"):
            m.assess(data)

    def test_same_path_in_different_repos_is_disjoint(self):
        data = sample()
        data["lanes"][2]["lease_paths"] = ["ci/governance/tests/new.py"]
        self.assertTrue(m.assess(data)["source_path_leases_disjoint"])

    def test_parent_closure_cannot_be_self_awarded(self):
        data = sample()
        data["parents"][0]["accepted_closed"] = True
        with self.assertRaisesRegex(ValueError, "closure"):
            m.assess(data)

    def test_missing_terminal_native_job_is_not_green(self):
        data = sample()
        data["lanes"][0]["receipt"]["job_id"] = None
        with self.assertRaisesRegex(ValueError, "terminal"):
            m.assess(data)

    def test_wrong_source_sha_is_not_native_proof(self):
        data = sample()
        data["lanes"][0]["receipt"]["source_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "terminal"):
            m.assess(data)

    def test_unknown_worker_hours_are_not_zero(self):
        data = sample()
        data["lanes"][0]["worker_hours"] = 0
        with self.assertRaisesRegex(ValueError, "UNKNOWN"):
            m.assess(data)

    def test_dependency_unknown_suppresses_read_only_eligibility(self):
        data = sample()
        data["lanes"][2]["depends_on"] = ["cred"]
        x = m.assess(data)
        self.assertEqual(x["read_only_unblocked_lanes"], [])
        self.assertEqual(x["advisory_readonly_parallel_limit"], 0)

    def test_unverified_root_id_not_accepted(self):
        data = sample()
        data["lanes"][1]["accepted_root_id"] = "ROOT_1"
        with self.assertRaisesRegex(ValueError, "accepted causal root"):
            m.assess(data)

    def test_path_traversal_denied(self):
        data = sample()
        data["lanes"][2]["lease_paths"] = ["../other/repo.py"]
        with self.assertRaisesRegex(ValueError, "leased source paths"):
            m.assess(data)

    def test_repeated_fingerprint_is_not_two_causal_roots(self):
        data = sample()
        data["lanes"][2]["first_red_fingerprint"] = "NO_CROSS_REPO_READ_TOKEN"
        data["lanes"][2]["observed_occurrences"] = 2
        x = m.assess(data)
        self.assertEqual(x["distinct_first_red_fingerprints"], 1)
        self.assertEqual(x["fingerprint_manifestations_by_lane"][
            "NO_CROSS_REPO_READ_TOKEN"], 2)
        self.assertEqual(x["source_observed_occurrences"][
            "NO_CROSS_REPO_READ_TOKEN"], 5)
        self.assertEqual(x["accepted_causal_root_closures"], 0)


class G3GSutSourceLeaseTests(unittest.TestCase):
    """SUT targets and test-file edits require separate collision proofs."""

    def declared(self):
        data = sample()
        for lane in data["lanes"]:
            lane["sut_paths"] = list(lane["lease_paths"])
        return data

    def test_legacy_plan_without_target_inventory_is_unknown(self):
        result = m.assess(sample())
        self.assertTrue(result["source_path_leases_disjoint"])
        self.assertIsNone(result["sut_source_leases_disjoint"])
        self.assertFalse(result["sut_lease_census_complete"])
        self.assertEqual(result["sut_unreported_lane_ids"],
                         ["cred", "gov", "probe"])

    def test_explicit_disjoint_sut_lease_is_positive_control(self):
        result = m.assess(self.declared())
        self.assertTrue(result["sut_source_leases_disjoint"])
        self.assertTrue(result["sut_lease_census_complete"])
        self.assertEqual(result["sut_source_target_count"], 2)
        self.assertEqual(result["sut_unreported_lane_ids"], [])
        self.assertFalse(result["source_write_permission_granted_by_viewer"])

    def test_different_test_paths_same_sut_is_not_disjoint(self):
        data = self.declared()
        data["lanes"][2]["repo"] = "GBOGEB/ABACUS"
        data["lanes"][2]["sut_paths"] = list(data["lanes"][0]["sut_paths"])
        with self.assertRaisesRegex(ValueError, "overlapping SUT source target"):
            m.assess(data)

    def test_nested_sut_directory_overlap_is_rejected(self):
        data = self.declared()
        data["lanes"][2]["repo"] = "GBOGEB/ABACUS"
        data["lanes"][0]["sut_paths"] = ["DMAIC_V3"]
        data["lanes"][2]["sut_paths"] = ["DMAIC_V3/analyze_recent_files.py"]
        with self.assertRaisesRegex(ValueError, "overlapping SUT source target"):
            m.assess(data)

    def test_reverse_order_cannot_hide_colliding_suts(self):
        data = self.declared()
        data["lanes"][2]["repo"] = "GBOGEB/ABACUS"
        data["lanes"][2]["sut_paths"] = list(data["lanes"][0]["sut_paths"])
        data["lanes"].reverse()
        with self.assertRaisesRegex(ValueError, "overlapping SUT source target"):
            m.assess(data)

    def test_identical_sut_names_are_scoped_to_repository(self):
        data = self.declared()
        data["lanes"][0]["sut_paths"] = ["integration/shared.py"]
        data["lanes"][2]["sut_paths"] = ["integration/shared.py"]
        self.assertTrue(m.assess(data)["sut_source_leases_disjoint"])

    def test_repository_name_case_does_not_hide_lease_collisions(self):
        data = sample()
        data["lanes"][2]["repo"] = "GBOGEB/abacus"
        data["lanes"][2]["lease_paths"] = list(
            data["lanes"][0]["lease_paths"])
        with self.assertRaisesRegex(ValueError, "overlapping source lease"):
            m.assess(data)

        data = self.declared()
        data["lanes"][2]["repo"] = "GBOGEB/abacus"
        data["lanes"][2]["sut_paths"] = list(
            data["lanes"][0]["sut_paths"])
        with self.assertRaisesRegex(ValueError,
                                    "overlapping SUT source target"):
            m.assess(data)

    def test_traversal_or_malformed_target_inventory_rejected(self):
        for targets in ("integration/shared.py", ["../secret.py"],
                        ["integration/./shared.py"], ["integration/shared.py"] * 2):
            with self.subTest(targets=targets):
                data = self.declared()
                data["lanes"][0]["sut_paths"] = targets
                with self.assertRaisesRegex(ValueError, "SUT source paths"):
                    m.assess(data)

    def test_empty_sut_claim_with_a_write_lease_is_unknown(self):
        data = self.declared()
        data["lanes"][0]["sut_paths"] = []
        result = m.assess(data)
        self.assertIsNone(result["sut_source_leases_disjoint"])
        self.assertFalse(result["sut_lease_census_complete"])
        self.assertIn("gov", result["sut_unreported_lane_ids"])
        self.assertIsNone(result["sut_source_target_count"])

    def test_partial_sut_census_never_claims_global_independence(self):
        data = self.declared()
        del data["lanes"][2]["sut_paths"]
        result = m.assess(data)
        self.assertIsNone(result["sut_source_leases_disjoint"])
        self.assertEqual(result["sut_unreported_lane_ids"], ["probe"])


if __name__ == "__main__":
    unittest.main()
