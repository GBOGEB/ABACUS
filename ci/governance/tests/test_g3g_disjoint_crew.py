"""Negative resource leases and DAG guards; NO worker launch authority."""
import importlib.util
import copy
import unittest

import pytest
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


@pytest.mark.parametrize("malicious_path", [
    "/tmp/outside.py", "C:/repo/file.py", r"ci\governance\probe.py",
    "a//b.py", "a/./b.py", "a/../b.py", "a/",
    "a/\x00unsafe.py", "a/\x7funsafe.py", "a:file.py",
])
def test_w78_g3g_rejects_unsafe_cross_platform_path(malicious_path):
    doc = sample()
    doc["lanes"][2]["lease_paths"] = [malicious_path]
    with pytest.raises(ValueError, match="leased source paths"):
        m.assess(doc)


@pytest.mark.parametrize("alias", [
    "ci/governance/tests",
    "CI/GOVERNANCE/TESTS/NEW.PY",
    "ci/governance/tests/new.py/nested",
    "ci/governance/tests/new.py",
])
def test_w78_g3g_case_alias_or_parent_lease_fails_closed(alias):
    doc = sample()
    doc["lanes"][2]["repo"] = "gbogeb/abacus"
    doc["lanes"][2]["lease_paths"] = [alias]
    with pytest.raises(ValueError, match="overlapping source lease"):
        m.assess(doc)


@pytest.mark.parametrize("paths", [
    ["folder", "folder/file.py"],
    ["folder/ONE.py", "FOLDER/one.py"],
    ["folder", "FOLDER"],
])
def test_w78_g3g_rejects_intra_lane_overlap(paths):
    doc = sample()
    doc["lanes"][2]["lease_paths"] = paths
    with pytest.raises(ValueError, match="overlapping intra-lane source lease"):
        m.assess(doc)


@pytest.mark.parametrize("neighbor", [
    "ci/governance/tests/new.py-old",
    "ci/governance/tests/new2.py",
    "shared/different.py",
])
def test_w78_g3g_accepts_segment_distinct_siblings(neighbor):
    doc = sample()
    doc["lanes"][2]["repo"] = "gbogeb/abacus"
    doc["lanes"][2]["lease_paths"] = [neighbor]
    output = m.assess(doc)
    assert output["source_path_leases_disjoint"] is True
    assert output["source_write_permission_granted_by_viewer"] is False


def test_w78_g3g_aba_invalid_lease_never_authenticates_worker():
    baseline = sample()
    original = m.assess(baseline)
    changed = copy.deepcopy(baseline)
    changed["lanes"][2]["repo"] = "GBOGEB/ABACUS"
    changed["lanes"][2]["lease_paths"] = ["ci/governance/tests"]
    with pytest.raises(ValueError, match="overlapping source lease"):
        m.assess(changed)
    assert m.assess(baseline) == original
    assert original["worker_launch_ids"] is None
    assert original["accepted_causal_root_closures"] == 0


def test_w78_g3g_rejects_repository_traversal_and_empty_owners():
    for repo in ("GBOGEB/", "GBOGEB/..", "GBOGEB//repo", "OTHER/ABACUS"):
        doc = sample()
        doc["lanes"][2]["repo"] = repo
        with pytest.raises(ValueError, match="repository"):
            m.assess(doc)



if __name__ == "__main__":
    unittest.main()
