"""Regression contract for read-only CODE PURPLE evidence correlation."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/code_purple_bootstrap_ldab_census.py"
SPEC = importlib.util.spec_from_file_location("code_purple_bootstrap_ldab_census", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40
FP = "b" * 64


def base(receipts=None):
    return {"schema": "code-purple.bootstrap-ldab.input.v1",
            "repository": "GBOGEB/ABACUS", "source_sha": SHA,
            "receipts": [] if receipts is None else receipts}


def receipt(kind, run=1, job=2, **extras):
    return {"kind": kind, "repository": "GBOGEB/ABACUS",
            "source_sha": SHA, "run_id": run, "job_id": job, **extras}


class CensusTests(unittest.TestCase):
    def test_absent_native_evidence_is_unknown(self):
        x = MODULE.summarize(base([{"kind": "proposal", "transition": "closed"}]))
        self.assertIsNone(x["bootstrap"]["passed"])
        self.assertIsNone(x["bd"]["closed"])
        self.assertIsNone(x["lldb"]["launches"])
        self.assertEqual("UNKNOWN", x["compatibility"]["rhel9"]["status"])
        self.assertEqual("HOLD", x["merge_admission"])

    def test_bootstrap_and_os_receipts(self):
        x = MODULE.summarize(base([
            receipt("bootstrap", passed=28, failed=0, skipped=2, runner="ubuntu-24.04"),
            receipt("compatibility", 3, 4, platform="rhel8",
                    native=True, status="FAIL", runner="rhel8-runner")]))
        self.assertEqual(28, x["bootstrap"]["passed"])
        self.assertEqual("FAIL", x["compatibility"]["rhel8"]["status"])
        self.assertEqual("UNKNOWN", x["compatibility"]["ubi9"]["status"])

    def test_ldab_fingerprint_match_to_native_debug_job(self):
        x = MODULE.summarize(base([
            receipt("lldb", 1, 2, native=True, status="DAP_PASS"),
            receipt("ldab", 3, 4, root_id="BD-1", fingerprint=FP,
                    debug_job={"run_id": 1, "job_id": 2}),
            receipt("ldab", 5, 6, root_id="BD-2", fingerprint=FP,
                    debug_job={"run_id": 9, "job_id": 9})]))
        self.assertEqual({"matched": 1, "unmatched": 1}, x["ldab"])
        self.assertEqual(1, x["lldb"]["dap_success"])

    def test_verified_bd_root_transitions(self):
        rows = [receipt("bd", i, i + 20, native=True, verified=True,
                        transition=t, root_id=str(i), fingerprint=FP)
                for i, t in enumerate(("opened", "closed", "reopened"), 1)]
        self.assertEqual({"opened": 1, "closed": 1, "reopened": 1},
                         MODULE.summarize(base(rows))["bd"])

    def test_reject_fabricated_bd_closure(self):
        with self.assertRaises(ValueError):
            MODULE.summarize(base([receipt("bd", native=False, verified=True,
                                           transition="closed", root_id="BD", fingerprint=FP)]))

    def test_reject_cross_sha_and_duplicate_native_job(self):
        bad = receipt("bootstrap", passed=1, failed=0, skipped=0, runner="ubuntu")
        bad["source_sha"] = "c" * 40
        with self.assertRaises(ValueError):
            MODULE.summarize(base([bad]))
        good = receipt("lldb", native=True, status="DAP_PASS")
        with self.assertRaises(ValueError):
            MODULE.summarize(base([good, good]))

    def test_reject_missing_or_negative_native_identifiers(self):
        for run, job in [(0, 2), (1, -2), ("1", 2)]:
            row = receipt("lldb", run, job, native=True, status="DAP_PASS")
            with self.subTest(run=run, job=job), self.assertRaises(ValueError):
                MODULE.summarize(base([row]))

    def test_reject_fake_debugger_and_os_success(self):
        with self.assertRaises(ValueError):
            MODULE.summarize(base([receipt("lldb", native=False,
                                           status="DAP_PASS")]))
        with self.assertRaises(ValueError):
            MODULE.summarize(base([receipt("compatibility", platform="ubi9",
                                           native=False, status="PASS",
                                           runner="reported-only")]))

    def test_reject_unlinked_invalid_fingerprint(self):
        with self.assertRaises(ValueError):
            MODULE.summarize(base([receipt("ldab", root_id="BD-X",
                                           fingerprint="bad",
                                           debug_job={"run_id": 5, "job_id": 6})]))

    def test_malformed_proposals_fail_closed(self):
        with self.assertRaises(ValueError):
            MODULE.summarize(base([None]))

    def test_dependency_order_preserved(self):
        stages = MODULE.summarize(base())["stage_order"]
        edges = {x["id"]: x["needs"] for x in stages}
        self.assertIn("DEBUG_LLDB", edges["LDAB_CORRELATION"])
        self.assertIn("LDAB_CORRELATION", edges["JOINED_CENSUS"])
        self.assertIn("JOINED_CENSUS", edges["KPI_PULSE"])


if __name__ == "__main__":
    unittest.main()
