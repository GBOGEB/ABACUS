"""G3A W16 five-KPI contract: positive and fail-closed branches."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

from MIP.statistics import g3a_w16_kpi as kpi
from MIP.statistics.g3a_w16_kpi import METRIC_NAMES, evaluate

SHA = "a" * 40
EPOCH = "G3A_W16_SYNTHETIC_TEST_EPOCH"
# Synthetic epoch, independent of the live pin: the contract is tested on fixed
# numbers so a re-pin of the real manifest never rewrites these tests.
FOUR_BRANCHES = {
    "DMAIC_V3/debug_pipeline.py": 116,
    "DMAIC_V3/phases/phase4_improve.py": 132,
    "DMAIC_V3/phases/phase8_todo_management.py": 118,
    "cicd_github_orchestrator.py": 78,
}


def blob(path):
    return format(sorted(FOUR_BRANCHES).index(path) + 1, "040x")


def synthetic_epoch(pending=False):
    files = {
        path: {
            "role": "kpi",
            "blob": blob(path),
            "branches": {"3.12": None if pending else den},
        }
        for path, den in FOUR_BRANCHES.items()
    }
    files["scripts/g3a_bounded_mission.py"] = {
        "role": "control",
        "blob": "f" * 40,
        "branches": {"3.12": 116},
    }
    return {
        "source_epoch": EPOCH,
        "kpi_python": "3.12",
        "min_tests": 121,
        "status": "PENDING_NATIVE_MEASUREMENT" if pending else "PINNED",
        "files": files,
    }


def native():
    vals = {
        "DMAIC_V3/debug_pipeline.py": 94,
        "DMAIC_V3/phases/phase4_improve.py": 50,
        "DMAIC_V3/phases/phase8_todo_management.py": 35,
        "cicd_github_orchestrator.py": 23,
    }
    return {
        "schema": "code-purple.g3a.w16.native.v1",
        "source_epoch": EPOCH,
        "checkout_sha": SHA,
        "source_blobs": {k: blob(k) for k in FOUR_BRANCHES},
        "run_id": 38901984001,
        "run_attempt": 1,
        "tests": 130,
        "files": {
            k: {"covered": vals[k], "eligible": FOUR_BRANCHES[k]} for k in FOUR_BRANCHES
        },
        "covered": sum(vals.values()),
        "eligible": 444,
        "merge_admission": "HOLD",
    }


class SyntheticEpochCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(kpi, "load_epoch", return_value=synthetic_epoch())
        patcher.start()
        self.addCleanup(patcher.stop)


class W16DecisionMetricTests(SyntheticEpochCase):
    def test_unmeasured_values_are_null_not_false_green(self):
        x = evaluate(None)
        self.assertEqual(x["metric_count"], 5)
        self.assertEqual(tuple(x["metrics"]), METRIC_NAMES)
        self.assertIsNone(x["metrics"]["matched_coverage"]["ratio"])
        self.assertIsNone(x["metrics"]["time_to_evidence"]["queue_seconds"])
        self.assertEqual(x["native_state"], "NATIVE_NOT_MEASURED")

    def test_valid_current_epoch_is_444_not_historical_446(self):
        x = evaluate(native())
        self.assertEqual(x["metrics"]["matched_coverage"]["d"], 444)
        self.assertEqual(x["metrics"]["matched_coverage"]["k"], 202)
        self.assertEqual(x["metrics"]["matched_coverage"]["uncovered"], 242)
        self.assertIsNone(x["metrics"]["matched_coverage"]["cross_epoch_delta"])
        self.assertEqual(
            x["metrics"]["proof_yield"]["single_exact_head_focused_proof"], 1.0
        )

    def test_timing_only_from_bounded_clock_measurement(self):
        x = evaluate(native(), start_s=10.5, end_s=15.1)
        self.assertEqual(
            x["metrics"]["time_to_evidence"]["measured_test_execution_seconds"], 4.6
        )
        self.assertIsNone(x["metrics"]["time_to_evidence"]["queue_p95_seconds"])

    def test_clock_reverse_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "clock"):
            evaluate(None, start_s=15.1, end_s=10.5)

    def test_denom_drift_rejected(self):
        x = native()
        x["files"]["DMAIC_V3/phases/phase4_improve.py"]["eligible"] = 134
        with self.assertRaisesRegex(ValueError, "denominator"):
            evaluate(x)

    def test_identity_schema_and_source_guard(self):
        for key, value, match in [
            ("checkout_sha", "invalid", "head"),
            ("source_blobs", {"DMAIC_V3/debug_pipeline.py": "b" * 40}, "blob"),
            ("source_epoch", "N14", "epoch"),
            ("merge_admission", "GO", "merge"),
        ]:
            x = native()
            x[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, match):
                evaluate(x)

    def test_proof_yield_cannot_be_given_by_too_few_tests(self):
        x = native()
        x["tests"] = 98
        with self.assertRaisesRegex(ValueError, "test"):
            evaluate(x)

    def test_root_closure_requires_distinct_authentication(self):
        with self.assertRaisesRegex(ValueError, "closure"):
            evaluate(native(), independently_verified_roots=1)

    def test_no_statistical_certificate_from_six_claimed_pulses(self):
        x = evaluate(native(), comparable_independent_pulses=6)
        state = x["metrics"]["statistical_control"]
        self.assertEqual(state["state"], "REQUIRES_SLOPE_EQUIVALENCE_AND_REVIEW")
        self.assertEqual(state["pca"], "NOT_QUALIFIED")
        self.assertEqual(state["bt"], "NO_PAIRWISE_OUTCOMES")
        self.assertEqual(state["six_sigma"], "NOT_ASSESSED")
        self.assertEqual(x["merge_admission"], "HOLD")

    def test_receipt_shape_guards(self):
        for key, value, match in [
            ("schema", "code-purple.g3a.n15.cross-python.v1", "schema"),
            ("run_id", 0, "run"),
            ("files", {}, "population"),
        ]:
            x = native()
            x[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, match):
                evaluate(x)

    def test_pulse_count_must_be_positive_int(self):
        with self.assertRaisesRegex(ValueError, "pulse"):
            evaluate(None, comparable_independent_pulses=0)

    def test_pending_epoch_never_passes(self):
        with self.assertRaisesRegex(ValueError, "pending native measurement"):
            evaluate(native(), epoch=synthetic_epoch(pending=True))
        x = evaluate(None, epoch=synthetic_epoch(pending=True))
        self.assertEqual(x["epoch_status"], "PENDING_NATIVE_MEASUREMENT")
        self.assertEqual(x["native_state"], "NATIVE_NOT_MEASURED")


class LiveEpochManifestTests(unittest.TestCase):
    def test_live_manifest_is_complete_and_self_consistent(self):
        epoch = kpi.load_epoch()
        self.assertEqual(epoch["schema"], "code-purple.g3a.w16.epoch.v1")
        self.assertIn(epoch["kpi_python"], epoch["pythons"])
        roles = sorted(v["role"] for v in epoch["files"].values())
        self.assertEqual(roles, ["control", "kpi", "kpi", "kpi", "kpi"])
        measured = all(
            isinstance(v["branches"].get(p), int)
            for v in epoch["files"].values()
            for p in epoch["pythons"]
        )
        self.assertEqual(
            epoch["status"], "PINNED" if measured else "PENDING_NATIVE_MEASUREMENT"
        )
        for entry in epoch["files"].values():
            self.assertRegex(entry["blob"], r"^[0-9a-f]{40}$")


class W16KpiCliTests(SyntheticEpochCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_main(self, *args):
        argv = ["g3a_w16_kpi.py", *map(str, args)]
        with (
            mock.patch.object(sys, "argv", argv),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            rc = kpi.main()
        return rc, out.getvalue()

    def test_cli_writes_pass_receipt_with_clock(self):
        receipt = self.root / "n16_receipt.json"
        receipt.write_text(json.dumps(native()), encoding="utf-8")
        (self.root / "start.txt").write_text("10.5\n")
        (self.root / "end.txt").write_text("15.1\n")
        out = self.root / "out/w16_kpis.json"
        rc, text = self.run_main(
            "--receipt",
            receipt,
            "--start-s",
            self.root / "start.txt",
            "--end-s",
            self.root / "end.txt",
            "--out",
            out,
        )
        self.assertEqual(rc, 0)
        self.assertIn("G3A_W16_KPIS=NATIVE_FOCUSED_PROOF_PASS", text)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(
            data["metrics"]["time_to_evidence"]["measured_test_execution_seconds"], 4.6
        )

    def test_cli_missing_receipt_is_not_measured_and_red(self):
        out = self.root / "w16_kpis.json"
        rc, text = self.run_main("--receipt", self.root / "absent.json", "--out", out)
        self.assertEqual(rc, 2)
        self.assertIn("NATIVE_NOT_MEASURED", text)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertIsNone(
            data["metrics"]["time_to_evidence"]["measured_test_execution_seconds"]
        )


if __name__ == "__main__":
    unittest.main()
