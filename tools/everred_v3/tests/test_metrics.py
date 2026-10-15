import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from metrics import comparable_coverage, comparable_security, compute_metrics

A = "a" * 40
B = "b" * 40


class KPI(unittest.TestCase):
    def scan(self, sha, fps, config="abc"):
        return {
            "sha": sha,
            "kind": "security_census",
            "evidence": {
                "scanner": "Bandit",
                "scope": "full",
                "config_digest": config,
                "scanner_version": "1.8.6",
                "rule_profile": "all",
                "normalization_version": "v1",
                "fingerprints": fps,
            },
        }

    def cov(self, sha, n, d, config="v1"):
        return {
            "sha": sha,
            "kind": "coverage",
            "evidence": {
                "scope": "broad",
                "unit": "statements",
                "config_id": config,
                "test_selection": "full",
                "exclusions": "standard",
                "tool_version": "7.13.3",
                "covered": n,
                "eligible": d,
            },
        }

    def test_security_exact_match(self):
        r = comparable_security(self.scan(A, ["a", "b", "c"]), self.scan(B, ["a", "d"]))
        self.assertEqual(
            (r["opened"], r["resolved"], r["persisting"], r["net_change"]),
            (1, 2, 1, -1),
        )

    def test_security_different_config_not_comparable(self):
        self.assertIsNone(
            comparable_security(self.scan(A, ["a"]), self.scan(B, ["b"], "different"))
        )

    def test_security_missing_fingerprints(self):
        a = self.scan(A, ["x"])
        b = self.scan(B, ["x"])
        b["evidence"].pop("fingerprints")
        self.assertIsNone(comparable_security(a, b))

    def test_security_duplicate_fingerprint_rejected(self):
        self.assertIsNone(
            comparable_security(self.scan(A, ["a", "a"]), self.scan(B, ["a"]))
        )

    def test_security_same_sha_rejected(self):
        self.assertIsNone(comparable_security(self.scan(A, ["a"]), self.scan(A, ["b"])))

    def test_coverage_delta(self):
        r = comparable_coverage(self.cov(A, 20, 100), self.cov(B, 25, 100))
        self.assertEqual(r["delta_percentage_points"], 5.0)

    def test_coverage_config_mismatch(self):
        self.assertIsNone(
            comparable_coverage(self.cov(A, 20, 100), self.cov(B, 30, 100, "changed"))
        )

    def test_coverage_missing_test_selection(self):
        a = self.cov(A, 1, 10)
        b = self.cov(B, 2, 10)
        a["evidence"].pop("test_selection")
        self.assertIsNone(comparable_coverage(a, b))

    def test_coverage_zero_denominator(self):
        self.assertIsNone(comparable_coverage(self.cov(A, 0, 0), self.cov(B, 1, 10)))

    def test_kpi_unknowns(self):
        r = compute_metrics([], {})
        self.assertIsNone(r["occurrence_amplification"])
        self.assertIsNone(r["recurrence_rate_pct"])

    def test_kpi_occurrence(self):
        ev = [
            {"kind": "occurrence", "root_id": "r1", "evidence": {}},
            {"kind": "occurrence", "root_id": "r1", "evidence": {}},
        ]
        self.assertEqual(
            compute_metrics(ev, {"r1": {"state": "CONFIRMED"}})[
                "occurrence_amplification"
            ],
            2.0,
        )

    def test_kpi_replay_requires_native_exact_head(self):
        root = {"r1": {"state": "CONFIRMED", "applicable_consumers": [
            {"consumer_id": "PR1", "repository": "GBOGEB/ABACUS", "head_sha": A},
            {"consumer_id": "PR2", "repository": "GBOGEB/ABACUS", "head_sha": B},
        ]}}
        ev = [{"kind": "replay", "root_id": "r1", "sha": A,
               "repo": "GBOGEB/ABACUS", "provenance": "observed",
               "evidence": {"consumer_id": "PR1", "status": "PASS",
                            "proof_type": "NATIVE_EXACT_HEAD_CI",
                            "job_status": "completed", "job_conclusion": "success",
                            "source_binding": {"repository": "GBOGEB/ABACUS",
                                               "source_sha": A, "run_id": 21, "job_id": 22}}}]
        self.assertEqual(compute_metrics(ev, root)["consumer_replay_coverage_pct"], 50.0)
        ev[0]["evidence"]["proof_type"] = "ISOLATED_PREVIEW_PASS"
        self.assertEqual(compute_metrics(ev, root)["consumer_replay_coverage_pct"], 0.0)
        ev[0]["evidence"]["proof_type"] = "NATIVE_EXACT_HEAD_CI"
        ev[0]["sha"] = B
        self.assertEqual(compute_metrics(ev, root)["consumer_replay_coverage_pct"], 0.0)

    def test_replay_legacy_registry_unknown(self):
        root = {"r1": {"state": "CONFIRMED", "applicable_consumers": ["PR1"]}}
        self.assertIsNone(compute_metrics([], root)["consumer_replay_coverage_pct"])

    def test_replay_unregistered_consumer_not_credit(self):
        root = {"r1": {"state": "CONFIRMED", "applicable_consumers": [
            {"consumer_id": "PR1", "repository": "GBOGEB/ABACUS", "head_sha": A}]}}
        ev = [{"kind": "replay", "root_id": "r1", "sha": A,
               "provenance": "observed", "evidence": {"consumer_id": "PR-OTHER", "status": "PASS"}}]
        self.assertEqual(compute_metrics(ev, root)["consumer_replay_coverage_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
