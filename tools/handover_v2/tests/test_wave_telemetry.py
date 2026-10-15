"""Negative controls for sequential V2 pulse and federation summaries."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wave_telemetry as telemetry

SHA_A = "a" * 40
SHA_B = "b" * 40
ROOT = "f" * 64


def state(sha: str = SHA_A) -> dict:
    return {
        "subject": {"repository": "GBOGEB/ABACUS", "head_sha": sha},
        "snapshot": {"captured_at_utc": "2026-10-15T08:00:00Z"},
        "metrics": [], "unknowns": [], "gates": [], "blockers": [],
        "authority": {"merge_decision": "HOLD", "independent_approval": "NOT_ESTABLISHED",
                      "effective_branch_protection": "UNKNOWN"},
    }


def ratio(sha=SHA_A, *, covered=8, eligible=10, config="0" * 64):
    return {
        "id": "scope.branch", "state": "MEASURED", "measure_type": "RATIO",
        "source_sha": sha, "numerator": covered, "denominator": eligible,
        "basis": {"scope_id": "scope", "paths": ["scripts/x.py"],
                  "unit_definition": "branch-arc", "instrumentor": "coverage.py",
                  "instrumentor_version": "7.16.2", "configuration_sha256": config,
                  "selection": "tests/test_x.py"},
    }


class WaveTelemetryTests(unittest.TestCase):
    def test_measured_ratio(self):
        s = state()
        s["metrics"] = [ratio()]
        r = telemetry.summarize_state(s, ROOT)
        self.assertEqual(r["metrics"]["current"]["scope.branch"]["percent"], 80.0)
        self.assertIsNone(r["fanout"]["authenticated_worker_launches"])
        self.assertEqual(r["admission"], "HOLD")

    def test_source_mismatch_is_rejected(self):
        s = state()
        s["metrics"] = [ratio(SHA_B)]
        with self.assertRaisesRegex(ValueError, "source mismatch"):
            telemetry.summarize_state(s, ROOT)

    def test_unknown_is_not_zero(self):
        s = state()
        m = ratio()
        m.update(state="UNKNOWN", numerator=None, denominator=None, value=0)
        s["metrics"] = [m]
        with self.assertRaisesRegex(ValueError, "UNKNOWN"):
            telemetry.summarize_state(s, ROOT)

    def test_comparison_counts_and_denominator(self):
        a, b = state(), state(SHA_B)
        a["metrics"] = [ratio(covered=7, eligible=10)]
        b["metrics"] = [ratio(SHA_B, covered=9, eligible=11)]
        d = telemetry.compare_states(a, b, ROOT, "e" * 64)["metric_deltas"][0]
        self.assertTrue(d["comparable"])
        self.assertEqual(d["covered_delta"], 2)
        self.assertEqual(d["eligible_delta"], 1)
        self.assertNotEqual(d["percentage_point_delta"], 0)

    def test_missing_configuration_blocks_comparison(self):
        a, b = ratio(config=None), ratio(SHA_B, config=None)
        ok, reason = telemetry.comparable(a, b)
        self.assertFalse(ok)
        self.assertIn("configuration", reason)

    def test_selection_change_blocks_comparison(self):
        a, b = ratio(), ratio(SHA_B)
        b["basis"]["selection"] = "different suite"
        self.assertFalse(telemetry.comparable(a, b)[0])

    def test_identical_sha_blocks_independent_wave(self):
        self.assertFalse(telemetry.comparable(ratio(), ratio())[0])

    def test_historical_ratio_never_becomes_current(self):
        s = state()
        h = ratio()
        h["state"] = "HISTORICAL"
        s["metrics"] = [h]
        r = telemetry.summarize_state(s, ROOT)
        self.assertNotIn("scope.branch", r["metrics"]["current"])
        self.assertIn("scope.branch", r["metrics"]["historical"])

    def test_unlinked_root_not_counted_as_burndown(self):
        s = state()
        s["blockers"] = [{"id": "B1", "classification": "ROOT",
                          "disposition": "RESOLVED", "root_cause_fingerprint": None}]
        r = telemetry.summarize_state(s, ROOT)
        self.assertIsNone(r["roots"]["closed_count"])
        self.assertIsNone(r["roots"]["fingerprinted_count"])

    def test_unknown_disappearance_not_claimed_as_root_closure(self):
        a, b = state(), state(SHA_B)
        a["unknowns"] = [{"id": "missing_ci", "owner": "O",
                          "reason": "missing", "acquisition": "check CI"}]
        d = telemetry.compare_states(a, b, ROOT, "e" * 64)
        self.assertEqual(d["unknown_net_reduction"], 1)
        self.assertIsNone(d["root_burndown"])

    def test_duplicate_unknown_rejected(self):
        s = state()
        u = {"id": "X", "owner": "O", "reason": "R", "acquisition": "A"}
        s["unknowns"] = [u, copy.deepcopy(u)]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            telemetry.summarize_state(s, ROOT)

    def test_federation_counts_only_supplied_verified_capsules(self):
        r = telemetry.summarize_state(state(), ROOT)
        out = telemetry.federate([r], ["GBOGEB/ABACUS", "GBOGEB/CODEX",
                                       "GBOGEB/cryoplant-project"])
        self.assertEqual(out["verified_local_capsules"], 1)
        self.assertEqual(out["target_count"], 3)
        self.assertEqual(out["breadth_percent"], 33.3333)
        self.assertEqual(len(out["unobserved_repositories"]), 2)
        self.assertIsNone(out["worker_fanout_executed"])

    def test_federation_rejects_duplicated_repository(self):
        r = telemetry.summarize_state(state(), ROOT)
        with self.assertRaisesRegex(ValueError, "one current pulse"):
            telemetry.federate([r, r], ["GBOGEB/ABACUS"])

    def test_federation_rejects_waiver(self):
        r = telemetry.summarize_state(state(), ROOT)
        r["security_waiver"] = True
        with self.assertRaisesRegex(ValueError, "waive"):
            telemetry.federate([r], ["GBOGEB/ABACUS"])

    def test_federation_cross_repo_metric_delta_unknown(self):
        r = telemetry.summarize_state(state(), ROOT)
        out = telemetry.federate([r], ["GBOGEB/ABACUS"])
        self.assertIsNone(out["comparable_federation_coverage_delta"])
        self.assertEqual(out["pca_promotion"], "WITHHELD")
        self.assertEqual(out["bt_promotion"], "WITHHELD")

    def test_receipt_serialization_is_deterministic(self):
        r1 = telemetry.summarize_state(state(), ROOT)
        r2 = telemetry.summarize_state(state(), ROOT)
        self.assertEqual(telemetry.canonical(r1), telemetry.canonical(r2))
        self.assertEqual(r1["receipt_sha256"], r2["receipt_sha256"])

    def test_current_gate_requires_exact_sha(self):
        s = state()
        s["gates"] = [{"id": "b0", "scope": "EXACT_HEAD", "status": "PASS",
                        "required_for_admission": True, "source_sha": SHA_B}]
        r = telemetry.summarize_state(s, ROOT)
        self.assertFalse(r["gates"]["required_all_pass"])
        self.assertEqual(r["admission"], "HOLD")

    def test_nonmeasured_history_cannot_be_compared(self):
        old = ratio()
        old["state"] = "HISTORICAL"
        self.assertFalse(telemetry.comparable(old, ratio(SHA_B))[0])

    def test_different_paths_disqualify_comparison(self):
        b, a = ratio(), ratio(SHA_B)
        a["basis"]["paths"] = ["scripts/other.py"]
        self.assertIn("path scope", telemetry.comparable(b, a)[1])

    def test_unknown_observation_retains_missing_reason(self):
        s = state()
        s["metrics"] = [{"id": "unknown.branch", "state": "UNKNOWN",
                         "numerator": None, "denominator": None, "value": None,
                         "missing_reason": "No native receipt"}]
        v = telemetry.summarize_state(s, ROOT)
        self.assertEqual(v["metrics"]["unknown"]["unknown.branch"]["reason"],
                         "No native receipt")

    def test_unsupported_observation_state_rejected(self):
        s = state()
        s["metrics"] = [{"id": "bad", "state": "TARGET"}]
        with self.assertRaisesRegex(ValueError, "unsupported"):
            telemetry.summarize_state(s, ROOT)

    def test_invalid_ratio_counts_rejected(self):
        for numerator, denominator in ((True, 3), (4, 3), (-1, 1), (0, 0),
                                       (2.0, 3), (1, None)):
            with self.subTest(n=numerator, d=denominator):
                x = ratio()
                x["numerator"], x["denominator"] = numerator, denominator
                with self.assertRaisesRegex(ValueError, "invalid ratio"):
                    telemetry.validate_ratio(x)

    def test_duplicate_gate_id_rejected(self):
        s = state()
        g = {"id": "B0", "scope": "EXACT_HEAD", "status": "PASS",
             "source_sha": SHA_A, "required_for_admission": True}
        s["gates"] = [g, copy.deepcopy(g)]
        with self.assertRaisesRegex(ValueError, "duplicate current gate"):
            telemetry.summarize_state(s, ROOT)

    def test_derived_admission_is_only_candidate_not_approval(self):
        s = state()
        s["authority"] = {"merge_decision": "ADMIT", "independent_approval":
                          "ESTABLISHED", "effective_branch_protection": "VERIFIED"}
        s["gates"] = [{"id": "governance", "scope": "EXACT_HEAD",
                       "status": "PASS", "required_for_admission": True,
                       "source_sha": SHA_A}]
        out = telemetry.summarize_state(s, ROOT)
        self.assertEqual(out["admission"], "CANDIDATE_ONLY_REQUIRES_LIVE_AUTHORITY")
        self.assertFalse(out["authority_transfer"])

    def test_metric_without_counterpart_cannot_generate_delta(self):
        a, b = state(), state(SHA_B)
        b["metrics"] = [ratio(SHA_B)]
        delta = telemetry.compare_states(a, b, ROOT, "e" * 64)
        self.assertEqual(delta["metric_deltas"], [])

    def test_cli_pulse_with_verified_capsule_stub(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "pulse.json"
            with patch.object(telemetry, "load_capsule", return_value=(
                state(), {"manifest_root_sha256": ROOT})), patch.object(
                    sys, "argv", ["wave_telemetry.py", "pulse", "--capsule", tmp,
                                  "--out", str(out)]):
                telemetry.main()
            row = json.loads(out.read_text())
            self.assertEqual(row["schema"], telemetry.SCHEMA)
            self.assertEqual(row["repo"], "GBOGEB/ABACUS")

    def test_cli_compare_with_verified_capsule_stubs(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "delta.json"
            with patch.object(telemetry, "load_capsule", side_effect=[
                    (state(), {"manifest_root_sha256": ROOT}),
                    (state(SHA_B), {"manifest_root_sha256": "e" * 64})
                ]), patch.object(sys, "argv", ["wave_telemetry.py", "compare",
                     "--before", tmp, "--after", tmp, "--out", str(out)]):
                telemetry.main()
            row = json.loads(out.read_text())
            self.assertEqual(row["schema"], "handover.wave.delta.v1")
            self.assertEqual(row["after_sha"], SHA_B)

    def test_cli_federation_with_verified_capsule_stub(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "federation.json"
            with patch.object(telemetry, "load_capsule", return_value=(
                state(), {"manifest_root_sha256": ROOT})), patch.object(sys,
                "argv", ["wave_telemetry.py", "federate", "--capsules", tmp,
                         "--repositories", "GBOGEB/ABACUS", "GBOGEB/CODEX",
                         "--out", str(out)]):
                telemetry.main()
            row = json.loads(out.read_text())
            self.assertEqual(row["breadth_percent"], 50.0)
            self.assertEqual(row["rollout_status"], "OBSERVATION_ONLY")

    def test_cli_federation_without_capsules_keeps_unknown(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "federation.json"
            with patch.object(sys, "argv", ["wave_telemetry.py", "federate",
                           "--repositories", "GBOGEB/ABACUS", "--out", str(out)]):
                telemetry.main()
            row = json.loads(out.read_text())
            self.assertEqual(row["verified_local_capsules"], 0)
            self.assertIsNone(row["worker_fanout_executed"])

    def test_federation_rejects_wrong_schema(self):
        r = telemetry.summarize_state(state(), ROOT)
        r["schema"] = "wrong"
        with self.assertRaisesRegex(ValueError, "unscoped federation"):
            telemetry.federate([r], ["GBOGEB/ABACUS"])

    def test_ineligible_comparison_does_not_credit_delta(self):
        a, b = state(), state(SHA_B)
        a["metrics"] = [ratio()]
        b["metrics"] = [ratio(SHA_B, config="1" * 64)]
        row = telemetry.compare_states(a, b, ROOT, "e" * 64)["metric_deltas"][0]
        self.assertFalse(row["comparable"])
        self.assertIsNone(row["covered_delta"])
        self.assertIsNone(row["percentage_point_delta"])

    def test_duplicate_metric_ids_rejected(self):
        s = state()
        s["metrics"] = [ratio(), ratio()]
        with self.assertRaisesRegex(ValueError, "duplicate metric"):
            telemetry.summarize_state(s, ROOT)

    def test_nondigest_manifest_root_rejected(self):
        with self.assertRaisesRegex(ValueError, "manifest root"):
            telemetry.summarize_state(state(), "z" * 64)

    def test_main_module_entrypoint_is_executable(self):
        import runpy
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "cli.json"
            with patch.object(sys, "argv", ["wave_telemetry.py", "federate",
                     "--repositories", "GBOGEB/ABACUS", "--out", str(out)]):
                runpy.run_path(str(Path(telemetry.__file__)), run_name="__main__")
            self.assertEqual(json.loads(out.read_text())["target_count"], 1)


if __name__ == "__main__":
    unittest.main()
