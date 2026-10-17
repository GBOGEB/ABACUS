"""Deterministic wave-history tests and negative cohort controls."""
import importlib.util
import pathlib
import unittest
from copy import deepcopy

P = pathlib.Path(__file__).resolve().parents[1] / "mission_wave_history.py"
S = importlib.util.spec_from_file_location("mission_wave_history", P)
M = importlib.util.module_from_spec(S)
S.loader.exec_module(M)
SHA1 = "a" * 40
SHA2 = "b" * 40


def snap(sha=SHA1, ok=1, bad=0, active=0):
    manifest = []
    for i in range(ok + bad + active):
        st = "completed" if i < ok + bad else "queued"
        conclusion = "success" if i < ok else "failure" if st == "completed" else None
        manifest.append({"run_id": i + 1, "workflow_id": i + 500,
                         "name": "Test " + str(i), "status": st,
                         "conclusion": conclusion})
    return {
        "schema": "mission.control.ci-telemetry.v1",
        "repo": "GBOGEB/ABACUS",
        "sha": sha,
        "provenance": "LIVE_GITHUB_API_READ_ONLY",
        "run_count": len(manifest),
        "terminal_run_count": ok + bad,
        "run_census_complete": True,
        "run_states": {"completed/success": ok, "completed/failure": bad,
                       "queued/none": active},
        "run_manifest": manifest,
        "job_metrics": {"sampled_jobs": 0, "queue_p50_s": None,
                        "execution_p50_s": None},
        "family_run_states": {"MIP": {"completed/success": ok,
                                     "completed/failure": bad,
                                     "queued/none": active}},
    }


def doc():
    return {"schema": M.INPUT,
            "waves": [{"wave_id": "W1", "observations": [snap()]},
                      {"wave_id": "W2", "observations": [snap(SHA2)]}]}


class WaveHistoryTests(unittest.TestCase):
    def test_matched_workflow_set(self):
        result = M.rollup(doc())
        c = result["wave_comparisons"][0]["by_repo"]["GBOGEB/ABACUS"]
        self.assertEqual(c["status"], "MATCHED_WORKFLOW_SET_ONLY")
        self.assertEqual(c["delta_success"], 0)
        self.assertIsNone(result["global_coverage_delta_pp"])

    def test_nonterminal_withholds_comparison(self):
        x = doc()
        x["waves"][1]["observations"] = [snap(SHA2, 1, 0, 1)]
        c = M.rollup(x)["wave_comparisons"][0]["by_repo"]["GBOGEB/ABACUS"]
        self.assertEqual(c["status"], "INCOMPARABLE_WORKFLOW_SET")

    def test_same_workflows_but_pending_withholds(self):
        x = doc()
        for wave in x["waves"]:
            wave["observations"] = [snap(SHA1, 0, 0, 1)]
        c = M.rollup(x)["wave_comparisons"][0]["by_repo"]["GBOGEB/ABACUS"]
        self.assertEqual(c["status"], "NONTERMINAL_WITHHELD")

    def test_partial_census_withholds(self):
        x = doc()
        x["waves"][1]["observations"][0]["run_census_complete"] = False
        c = M.rollup(x)["wave_comparisons"][0]["by_repo"]["GBOGEB/ABACUS"]
        self.assertEqual(c["status"], "INCOMPLETE_RUN_CENSUS")

    def test_separate_skips_failures_and_cancellations(self):
        result = M.tally_states({
            "completed/success": 1, "completed/failure": 2,
            "completed/skipped": 4, "completed/cancelled": 1,
            "queued/none": 3,
        })
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["skipped"], 4)
        self.assertEqual(result["cancelled"], 1)
        self.assertEqual(result["nonterminal"], 3)

    def test_repeat_workflow_ids_preserve_cohort(self):
        x = doc()
        for wave in x["waves"]:
            o = wave["observations"][0]
            o["run_count"] = 2
            o["terminal_run_count"] = 2
            o["run_states"] = {"completed/success": 2}
            o["run_manifest"].append({
                "run_id": 2, "workflow_id": 500,
                "name": "Repeat", "status": "completed",
                "conclusion": "success",
            })
        compared = M.rollup(x)["wave_comparisons"][0]
        self.assertEqual(
            compared["by_repo"]["GBOGEB/ABACUS"]["status"],
            "MATCHED_WORKFLOW_SET_ONLY",
        )

    def test_duplicate_run_id_withheld(self):
        x = doc()
        for wave in x["waves"]:
            o = wave["observations"][0]
            o["run_count"] = 2
            o["terminal_run_count"] = 2
            o["run_states"] = {"completed/success": 2}
            o["run_manifest"].append(dict(o["run_manifest"][0]))
        compared = M.rollup(x)["wave_comparisons"][0]
        self.assertEqual(
            compared["by_repo"]["GBOGEB/ABACUS"]["status"],
            "INCOMPARABLE_WORKFLOW_SET",
        )

    def test_duplicate_wave_rejected(self):
        x = doc()
        x["waves"][1]["wave_id"] = "W1"
        with self.assertRaises(ValueError):
            M.rollup(x)

    def test_duplicate_repo_rejected(self):
        x = doc()
        x["waves"][0]["observations"].append(deepcopy(snap()))
        with self.assertRaises(ValueError):
            M.rollup(x)

    def test_missing_api_provenance_rejected(self):
        x = doc()
        x["waves"][0]["observations"][0]["provenance"] = "SYNTHETIC"
        with self.assertRaises(ValueError):
            M.rollup(x)

    def test_bad_count_rejected(self):
        x = doc()
        x["waves"][0]["observations"][0]["run_count"] = 99
        with self.assertRaises(ValueError):
            M.rollup(x)

    def test_mip_pulse_requires_matched_sha(self):
        x = doc()
        x["waves"][0]["mip_pulses"] = [{
            "schema": "abacus.mip.wave-pulse.v1",
            "repository": "GBOGEB/ABACUS",
            "head_sha": SHA2, "wave_id": "W1",
            "coverage": {"status": "COMPARABLE", "delta_pp": 1.0},
            "root_counts": {},
        }]
        with self.assertRaises(ValueError):
            M.rollup(x)

    def test_unknown_coverage_never_zero(self):
        x = doc()
        x["waves"][0]["mip_pulses"] = [{
            "schema": "abacus.mip.wave-pulse.v1",
            "repository": "GBOGEB/ABACUS",
            "head_sha": SHA1, "wave_id": "W1",
            "coverage": {"status": "UNKNOWN"},
            "root_counts": {"open": 2},
        }]
        s = M.rollup(x)["waves"][0]
        self.assertIsNone(s["coverage_by_repo"]["GBOGEB/ABACUS"]["delta_pp"])
        self.assertIsNone(s["formal_root_closures_credited"])

    def test_solo_amber_not_approval(self):
        x = doc()
        x["waves"][0]["solo_decisions"] = [{
            "head_sha": SHA1, "decision": "AMBER_REQUESTED",
            "merge_admitted": False,
        }]
        s = M.rollup(x)["waves"][0]
        self.assertEqual(s["amber_requests"], 1)
        self.assertFalse(s["merge_admitted"])

    def test_fake_amber_authority_rejected(self):
        x = doc()
        x["waves"][0]["solo_decisions"] = [{
            "head_sha": SHA1, "decision": "AMBER_REQUESTED",
            "merge_admitted": True,
        }]
        with self.assertRaises(ValueError):
            M.rollup(x)


if __name__ == "__main__":
    unittest.main()
