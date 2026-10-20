import importlib.util
import pathlib
import unittest
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("test_observability_engine", ROOT / "test_observability.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = "a" * 40
REPO = "GBOGEB/ABACUS"


class Census(unittest.TestCase):
    def runs(self):
        def run(i, conclusion):
            return {
                "id": i,
                "name": ["Unit tests", "Bandit", "Docker deployment", "PR Feedback Gate Evaluator"][i - 1],
                "status": "completed",
                "conclusion": conclusion,
                "head_sha": SHA,
                "created_at": "2026-10-14T10:00:00Z",
            }
        return [run(1, "success"), run(2, "failure"), run(3, "cancelled"), run(4, "success")]

    def test_taxonomy(self):
        cases = [
            ("Bandit", "security"), ("RHEL 9 UBI", "runtime"),
            ("LLDB session", "runtime"), ("DAB Flake8 Census", "static"),
            ("CI - ABACUS Matrix", "unit_integration"),
            ("PR Feedback Gate Evaluator", "governance"),
        ]
        for name, expected in cases:
            self.assertEqual(mod.category(name), expected)

    def test_not_merge_authority(self):
        data = mod.normalize(
            REPO, SHA, [{"name": "pytest", "path": ".github/workflows/test.yml"}],
            self.runs(), [], expected_runs=4,
        )
        self.assertFalse(data["merge_authorized"])
        self.assertFalse(data["authority_transfer"])
        self.assertEqual(data["runs"]["success_decisive_pct"], 66.67)
        self.assertEqual(data["runs"]["cancelled_observed_pct"], 25)
        self.assertTrue(data["runs"]["complete"])
        self.assertEqual(data["catalog"]["workflows_count"], 1)
        self.assertEqual(data["models"]["bt"]["status"], "UNKNOWN")
        self.assertEqual(data["dmaic"]["Analyze"]["status"], "UNCONFIRMED")

    def test_incomplete_denominator(self):
        data = mod.normalize(REPO, SHA, [], self.runs(), [], expected_runs=400)
        self.assertFalse(data["runs"]["complete"])
        self.assertEqual(data["dmaic"]["Measure"]["status"], "PARTIAL")

    def test_reject_cross_sha(self):
        runs = self.runs()
        runs[0]["head_sha"] = "b" * 40
        data = mod.normalize(REPO, SHA, [], runs, [], expected_runs=4)
        self.assertEqual(data["runs"]["observed"], 3)
        self.assertFalse(data["runs"]["complete"])

    def test_reject_cross_run_job(self):
        data = mod.normalize(
            REPO, SHA, [], self.runs(),
            [{"id": 55, "run_id": 999, "head_sha": SHA, "conclusion": "failure"}],
        )
        self.assertEqual(data["jobs"]["observed"], 0)
        self.assertTrue(data["errors"])

    def test_no_fake_pca(self):
        self.assertEqual(mod.pca_2d([])["readiness"], "NOT_QUALIFIED")

    def test_pca_observational(self):
        jobs = []
        for i in range(40):
            base = datetime(2026, 10, 14, 12, tzinfo=timezone.utc) + timedelta(minutes=i)
            q = base.isoformat()
            s = (base + timedelta(seconds=2 + i)).isoformat()
            e = (base + timedelta(seconds=2 + i + 3 * (i % 7 + 1))).isoformat()
            jobs.append({"created_at": q, "started_at": s, "completed_at": e})
        result = mod.pca_2d(jobs)
        self.assertEqual(result["readiness"], "DESCRIPTIVE_ONLY")
        self.assertLessEqual(result["pc1_evr"], 1)
        self.assertFalse(result["causal"])

    def test_bt_no_inference_from_workflow_states(self):
        data = mod.normalize(REPO, SHA, [], self.runs(), [], expected_runs=4)
        self.assertIsNone(data["models"]["bt"]["ranking"])

    def test_bt_reject_incomplete_connected_graph(self):
        rows = [
            {
                "candidate_a": "a", "candidate_b": "b", "winner": "a",
                "trial_id": str(i), "test_contract_digest": "a" * 64,
                "source_sha": SHA, "comparable": True,
            }
            for i in range(30)
        ]
        result = mod.bt_pairs(rows, sha=SHA)
        self.assertFalse(result["fit"])
        self.assertIn("strongly connected", result["reason"])

    def test_bt_matched_connected_trials(self):
        rows = [
            {
                "candidate_a": "a", "candidate_b": "b",
                "winner": "a" if i % 2 else "b",
                "trial_id": str(i), "test_contract_digest": "a" * 64,
                "source_sha": SHA, "comparable": True,
            }
            for i in range(30)
        ]
        result = mod.bt_pairs(rows, sha=SHA)
        self.assertTrue(result["fit"])
        self.assertEqual(result["status"], "DESCRIPTIVE_FIT_ONLY")
        self.assertIsNone(result["confidence_intervals"])

    def test_bt_reject_duplicate_trial_and_mismatched_sha(self):
        rows = [
            {
                "candidate_a": "a", "candidate_b": "b", "winner": "a",
                "trial_id": "x", "test_contract_digest": "b" * 64,
                "source_sha": SHA, "comparable": True,
            }
        ] * 30
        result = mod.bt_pairs(rows, sha=SHA)
        self.assertEqual(result["rejected_records"], 29)
        self.assertFalse(result["fit"])

    def test_deterministic_data_hash(self):
        self.assertEqual(
            mod.sha256({"a": 1, "b": [1, 2]}),
            mod.sha256({"b": [1, 2], "a": 1}),
        )

    def test_bad_identity(self):
        with self.assertRaises(ValueError):
            mod.normalize(REPO, "abc", [], [], [])


if __name__ == "__main__":
    unittest.main()
