"""Fail-closed root leverage and negative proof tests."""

import unittest

from scripts.gogreen_root_leverage import analyze

SHA = "a" * 40
ROOT_URL = "https://github.com/GBOGEB/ABACUS/issues/2026"


def row(pr=2070, *, run_id=100, job_id=2, root=None):
    entry = {
        "pr": pr,
        "head_sha": SHA,
        "run_id": run_id,
        "run_attempt": 1,
        "job_id": job_id,
        "job": "Security Scanning",
        "status": "failure",
        "first_red_signature": "bandit:B314",
    }
    if root:
        entry.update(
            root_id="ROOT_01",
            root_evidence=ROOT_URL,
            root_owner="ABACUS security owner",
            owner_disposition="ACCEPTED",
        )
    return entry


class RootLeverageTests(unittest.TestCase):
    def test_job_labels_do_not_infer_shared_root(self):
        result = analyze([row(2070), row(2077, run_id=101)])
        self.assertEqual(result["failed_category_overlap"][0]["count"], 2)
        self.assertEqual(result["proven_root_leverage"], [])
        self.assertEqual(result["unknown_root_prs"], [2070, 2077])
        self.assertEqual(result["owner_claim_attribution_fraction"], 0)

    def test_owned_root_duplicate_safe_and_qualification_fraction(self):
        first = row(root=True)
        result = analyze([first, first, row(2077, run_id=101, root=True)])
        self.assertEqual(result["observation_count_deduplicated"], 2)
        self.assertEqual(result["owner_claimed_root_leverage"][0]["blocked_prs"], 2)
        self.assertEqual(result["proven_root_leverage"], [])
        self.assertFalse(result["root_claims_authenticated"])
        self.assertEqual(result["candidate_pr_impact_upper_bound"], 2)
        self.assertIsNone(result["potential_unique_prs_released"])
        self.assertEqual(result["owner_claim_attribution_fraction"], 1)
        self.assertIsNone(result["root_attribution_pr_fraction"])
        self.assertIsNone(result["actually_unblocked_prs"])

    def test_mixed_confirmed_and_unknown_root_is_not_fully_attributed(self):
        result = analyze([row(root=True), row(run_id=102, job_id=3)])
        self.assertEqual(result["candidate_pr_impact_upper_bound"], 1)
        self.assertEqual(result["unknown_root_prs"], [2070])
        self.assertEqual(result["owner_claim_attribution_fraction"], 0)

    def test_no_failed_pr_denominator_does_not_mean_hundred_percent(self):
        item = row()
        item["status"] = "skipped"
        result = analyze([item])
        self.assertIsNone(result["owner_claim_attribution_fraction"])
        self.assertEqual(result["failed_pr_denominator"], 0)

    def test_no_root_without_explicit_qualified_evidence(self):
        for change in (
            {"root_id": "R"},
            {"owner_disposition": "PENDING"},
            {"root_evidence": "https://example.test/receipt"},
            {"root_owner": ""},
            {"first_red_signature": ""},
        ):
            with self.subTest(change=change):
                item = row(root=True)
                item.update(change)
                with self.assertRaises(ValueError):
                    analyze([item])

    def test_wrong_source_or_unattributed_worker_identity_rejected(self):
        for change in (
            {"head_sha": "abc"},
            {"run_id": None},
            {"run_attempt": None},
            {"job_id": 0},
            {"pr": 0},
            {"status": "in_progress"},
        ):
            with self.subTest(change=change):
                item = row()
                item.update(change)
                with self.assertRaises(ValueError):
                    analyze([item])

    def test_conflicting_same_run_job_is_rejected(self):
        original = row()
        forged = dict(original, first_red_signature="other")
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            analyze([original, forged])

    def test_conflicting_owner_per_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting root owner"):
            analyze(
                [
                    row(root=True),
                    dict(row(2077, run_id=101, root=True), root_owner="Other"),
                ]
            )

    def test_nonfailure_cannot_claim_owner_root(self):
        item = row(root=True)
        item["status"] = "success"
        with self.assertRaises(ValueError):
            analyze([item])

    def test_unowned_root_evidence_is_rejected(self):
        item = row()
        item["root_owner"] = "owner"
        with self.assertRaises(ValueError):
            analyze([item])

    def test_non_object_and_duplicate_proof_rejected(self):
        with self.assertRaisesRegex(ValueError, "observation must be object"):
            analyze([None])
        first = row()
        extra = dict(first, first_red_signature="different")
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            analyze([first, extra])

    def test_source_run_attempt_is_part_of_identity(self):
        first = row()
        retried = dict(first, run_attempt=2)
        result = analyze([first, retried])
        self.assertEqual(result["observation_count_deduplicated"], 2)
        self.assertEqual(result["failed_pr_denominator"], 1)
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["security_waiver"])

    def test_cli_json_roundtrip_with_no_merge_credit(self):
        import contextlib
        import io
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from scripts import gogreen_root_leverage

        with tempfile.TemporaryDirectory() as folder:
            inp = Path(folder) / "input.json"
            out = Path(folder) / "output.json"
            inp.write_text(json.dumps({"observations": [row()]}), encoding="utf-8")
            with patch("sys.argv", ["command", str(inp), "--output", str(out)]):
                gogreen_root_leverage.main()
            expected = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(expected["unknown_root_prs"], [2070])
            captured = io.StringIO()
            with patch("sys.argv", ["command", str(inp)]):
                with contextlib.redirect_stdout(captured):
                    gogreen_root_leverage.main()
            self.assertEqual(json.loads(captured.getvalue()), expected)
            self.assertIsNone(expected["accepted_root_closures"])

    def test_direct_script_guard_preserves_fail_closed_receipt(self):
        import contextlib
        import io
        import json
        import runpy
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        script = (
            Path(__file__).resolve().parents[1] / "scripts" / "gogreen_root_leverage.py"
        )
        with tempfile.TemporaryDirectory() as folder:
            inp = Path(folder) / "source.json"
            inp.write_text(json.dumps({"observations": [row()]}), encoding="utf-8")
            captured = io.StringIO()
            with patch("sys.argv", [str(script), str(inp)]):
                with contextlib.redirect_stdout(captured):
                    runpy.run_path(str(script), run_name="__main__")
            record = json.loads(captured.getvalue())
            self.assertFalse(record["merge_authorized"])
            self.assertIsNone(record["actually_unblocked_prs"])

    def test_empty_and_capped_cohort(self):
        self.assertIsNone(analyze([])["root_attribution_pr_fraction"])
        with self.assertRaises(ValueError):
            analyze([row()] * 513)
        with self.assertRaises(ValueError):
            analyze({"rows": []})


if __name__ == "__main__":
    unittest.main()
