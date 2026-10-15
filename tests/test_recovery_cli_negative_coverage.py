"""Negative controls and native CLI coverage for recovery evidence producers.

These tests never promote an admission decision or invent runtime receipts.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.recovery import bd_ldab_evidence_join
from tools.recovery import comparable_coverage
from tools.recovery import os_compat_receipt
from tools.recovery import safety_exit_census


class RecoveryCLIContractCoverageTests(unittest.TestCase):
    def run_main(self, entrypoint, args):
        with patch.object(sys, "argv", ["recovery-producer", *args]):
            entrypoint()

    def test_comparable_coverage_rejects_nonobjects(self):
        with self.assertRaises(ValueError):
            comparable_coverage.compare(None, {"modules": {}})
        with self.assertRaises(ValueError):
            comparable_coverage.compare({"modules": {}}, None)
        with self.assertRaises(ValueError):
            comparable_coverage.compare({}, {"modules": {}})

    def test_comparable_coverage_discards_invalid_module(self):
        base = {
            "modules": {
                "valid": {
                    "covered_lines": 1,
                    "eligible_lines": 3,
                    "covered_branches": 0,
                    "eligible_branches": 2,
                },
                "broken": {
                    "covered_lines": -1,
                    "eligible_lines": 3,
                    "covered_branches": 0,
                    "eligible_branches": 1,
                },
            }
        }
        head = json.loads(json.dumps(base))
        head["modules"]["valid"]["covered_lines"] = 2
        result = comparable_coverage.compare(base, head)
        self.assertEqual(result["cohort"], ["valid"])
        self.assertEqual(result["excluded"], ["broken"])
        self.assertEqual(result["line_covered_delta"], 1)
        self.assertEqual(result["admission"], "HOLD")

    def test_comparable_coverage_cli_persists_provenance(self):
        base = {"modules": {"m": {
            "covered_lines": 1, "eligible_lines": 2,
            "covered_branches": 0, "eligible_branches": 1,
        }}}
        head = json.loads(json.dumps(base))
        head["modules"]["m"]["covered_branches"] = 1
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            before, after, out = (
                folder / "before.json", folder / "after.json",
                folder / "result.json",
            )
            before.write_text(json.dumps(base))
            after.write_text(json.dumps(head))
            self.run_main(
                comparable_coverage.main,
                [str(before), str(after), "--out", str(out)],
            )
            receipt = json.loads(out.read_text())
            self.assertEqual(receipt["branch_covered_delta"], 1)
            self.assertFalse(receipt["closure_credit"])

    def test_bd_ldab_requires_arrays_and_unique_roots(self):
        with self.assertRaises(ValueError):
            bd_ldab_evidence_join.join({}, {"observations": []})
        with self.assertRaises(ValueError):
            bd_ldab_evidence_join.join({"roots": []}, {})
        roots = {"roots": [{"root_id": "R1"}, {"root_id": "R1"}]}
        with self.assertRaises(ValueError):
            bd_ldab_evidence_join.join(roots, {"observations": []})
        with self.assertRaises(ValueError):
            bd_ldab_evidence_join.join(
                {"roots": [{"root_id": 10}]}, {"observations": []},
            )

    def test_bd_ldab_rejects_nonobject_observation(self):
        with self.assertRaises(ValueError):
            bd_ldab_evidence_join.join(
                {"roots": [{"root_id": "R1"}]},
                {"observations": ["unattributable"]},
            )

    def test_bd_ldab_cli_preserves_unknown_root(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            roots, observations, out = (
                folder / "roots.json", folder / "observations.json",
                folder / "result.json",
            )
            roots.write_text(json.dumps({"roots": [{"root_id": "R1"}]}))
            observations.write_text(json.dumps({
                "observations": [{"root_id": "UNKNOWN", "fingerprint": "f"}]
            }))
            self.run_main(
                bd_ldab_evidence_join.main,
                [str(roots), str(observations), "--out", str(out)],
            )
            receipt = json.loads(out.read_text())
            self.assertIsNone(receipt["observations"][0]["root_id"])
            self.assertFalse(receipt["observations"][0]["closure_credit"])
            self.assertIsNone(receipt["root_closures"])

    def test_safety_nonzero_findings_never_promote(self):
        receipt = safety_exit_census.classify(
            0, {"vulnerabilities": [{"id": "CVE-test"}]},
        )
        self.assertEqual(receipt["finding_count"], 1)
        self.assertEqual(
            receipt["failure_class"], "NONTERMINAL_REVIEW_REQUIRED",
        )
        self.assertEqual(receipt["admission"], "HOLD")

    def test_safety_cli_emits_explicit_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "safety.json"
            self.run_main(
                safety_exit_census.main,
                ["--exit-code", "64", "--out", str(out)],
            )
            receipt = json.loads(out.read_text())
            self.assertIsNone(receipt["finding_count"])
            self.assertEqual(
                receipt["failure_class"],
                "SCAN_OR_POLICY_FAILURE_UNCLASSIFIED",
            )

    def test_os_receipt_rejects_invalid_native_proof(self):
        with self.assertRaises(ValueError):
            os_compat_receipt.validate(["not-an-object"])
        row = {
            "repository": "GBOGEB/ABACUS",
            "commit_sha": "a" * 40,
            "run_id": 100,
            "job_id": 200,
            "os_release": "RHEL 9",
            "runner": "native",
            "image_digest": "unverified",
            "conclusion": "success",
        }
        receipt = os_compat_receipt.validate(row)
        self.assertIn("sha256_image_digest", receipt["missing"])
        self.assertFalse(receipt["native_pass"])
        row["conclusion"] = "UNRECOGNIZED"
        receipt = os_compat_receipt.validate(row)
        self.assertIn("valid_conclusion", receipt["missing"])

    def test_os_receipt_cli_does_not_claim_failed_job(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, out = folder / "source.json", folder / "result.json"
            source.write_text(json.dumps({"conclusion": "failure"}))
            self.run_main(
                os_compat_receipt.main,
                [str(source), "--out", str(out)],
            )
            receipt = json.loads(out.read_text())
            self.assertFalse(receipt["native_pass"])
            self.assertEqual(receipt["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
