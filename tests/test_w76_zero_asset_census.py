"""W76 adversarial census tests: fail closed on false zero-reduction claims."""
from __future__ import annotations

import copy
import hashlib
import tempfile
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODFILE = ROOT / "ci" / "w76_zero_coverage.py"
SPEC = importlib.util.spec_from_file_location("w76_zero_gate", MODFILE)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)
BASE = json.loads((ROOT / "ci" / "w76_zero_coverage_baseline.json").read_text())
SHA = "a" * 40
LOG = b"----------------------------------------------------------------------\nRan 31 tests in 0.03s\n\nOK\n"


def coverage_for(baseline=BASE, *, recovered=True):
    files = {}
    for record in baseline["files"]:
        s = record["eligible_statements"]
        b = record["eligible_branches"]
        files[record["path"]] = {"summary": {
            "num_statements": s, "covered_lines": min(s, 4) if recovered else 0,
            "num_branches": b, "covered_branches": min(b, 2) if recovered else 0}}
    return {"meta": {"branch_coverage": True, "version": "7.16.2"}, "files": files}


def examine(baseline=None, coverage=None, get_blob=None, log=LOG):
    current_baseline = copy.deepcopy(BASE) if baseline is None else baseline
    if coverage is None:
        coverage = coverage_for(current_baseline)
    blob_by_path = {row["path"]: row["source_blob_sha"]
                    for row in current_baseline["files"]}
    return GATE.measure(current_baseline, coverage, SHA,
                        get_blob if get_blob is not None
                        else lambda p: blob_by_path[p],
                        GATE.parse_terminal(log))


class W76ZeroAssetAuditTests(unittest.TestCase):
    def test_positive_all_ten_converts_zero_bucket_without_global_claim(self):
        result = examine()
        self.assertEqual(result["targeted_executable_assets"], 10)
        self.assertEqual(result["recovered_zero_covered_assets"], 10)
        self.assertEqual(result["still_zero_covered_assets"], 0)
        self.assertEqual(result["unknown_or_incomparable_assets"], 0)
        self.assertIsNone(result["zero_covered_global_current"])
        self.assertFalse(result["merge_authorized"])
        self.assertEqual(result["owner_acceptance"], "DEFER")
        self.assertEqual(result["matched_statement_coverage"]["eligible"], 233)
        self.assertEqual(result["matched_branch_coverage"]["eligible"], 50)
        self.assertEqual(result["matched_statement_coverage"]["baseline_covered"], 0)
        self.assertEqual(result["tests"]["passed"], 31)

    def test_zero_candidate_does_not_claim_reduction(self):
        candidate = coverage_for(recovered=False)
        receipt = examine(coverage=candidate)
        self.assertEqual(receipt["recovered_zero_covered_assets"], 0)
        self.assertEqual(receipt["still_zero_covered_assets"], 10)

    def test_missing_file_means_unknown_not_zero(self):
        candidate = coverage_for()
        removed = BASE["files"][0]["path"]
        candidate["files"].pop(removed)
        receipt = examine(coverage=candidate)
        self.assertEqual(receipt["recovered_zero_covered_assets"], 9)
        self.assertEqual(receipt["still_zero_covered_assets"], 0)
        self.assertEqual(receipt["unknown_or_incomparable_assets"], 1)
        row = next(row for row in receipt["files"] if row["path"] == removed)
        self.assertEqual(row["status"], "UNKNOWN_MISSING_COVERAGE")

    def test_instrumented_branch_denominator_drift_is_incomparable(self):
        candidate = coverage_for()
        candidate["files"][BASE["files"][0]["path"]]["summary"]["num_branches"] = 1
        receipt = examine(coverage=candidate)
        self.assertEqual(receipt["unknown_or_incomparable_assets"], 1)
        self.assertEqual(receipt["recovered_zero_covered_assets"], 9)

    def test_statement_denominator_drift_cannot_yield_matched_uplift(self):
        candidate = coverage_for()
        candidate["files"][BASE["files"][0]["path"]]["summary"]["num_statements"] += 1
        receipt = examine(coverage=candidate)
        self.assertEqual(receipt["recovered_zero_covered_assets"], 9)
        self.assertEqual(receipt["unknown_or_incomparable_assets"], 1)

    def test_forged_git_blob_refused_before_coverage_credit(self):
        with self.assertRaisesRegex(ValueError, "source bytes changed"):
            examine(get_blob=lambda p: "f" * 40)

    def test_boolean_and_negative_numerators_are_invalid(self):
        for val in (-1, True, "5"):
            cov = coverage_for()
            cov["files"][BASE["files"][0]["path"]]["summary"]["covered_lines"] = val
            with self.subTest(val=val), self.assertRaisesRegex(ValueError, "invalid count"):
                examine(coverage=cov)

    def test_covered_count_cannot_exceed_eligible_count(self):
        cov = coverage_for()
        file = BASE["files"][0]
        cov["files"][file["path"]]["summary"]["covered_lines"] = 99
        with self.assertRaisesRegex(ValueError, "exceeds denominator"):
            examine(coverage=cov)

    def test_coverage_requires_exact_version_and_branch_instrumentation(self):
        for key, bad in (("version", "7.15.0"),
                         ("branch_coverage", False),
                         ("branch_coverage", None)):
            cov = coverage_for()
            cov["meta"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaisesRegex(
                    ValueError, "branch mode or coverage version drift"):
                examine(coverage=cov)

    def test_baseline_duplicate_path_fails_closed(self):
        b = copy.deepcopy(BASE)
        b["files"].append(copy.deepcopy(b["files"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate baseline"):
            examine(baseline=b)

    def test_baseline_paths_cannot_escape_or_alias_repository(self):
        for path in ("../scope.py", "/abs.py", "src//evil.py",
                     "src/.git/config.py", "src/./alias.py", "C:\\windows\\bad.py"):
            with self.subTest(path=path):
                b = copy.deepcopy(BASE)
                b["files"][0]["path"] = path
                with self.assertRaisesRegex(ValueError, "unsafe or noncanonical"):
                    examine(baseline=b, get_blob=lambda p: "a" * 40)

    def test_baseline_cannot_upgrade_or_replace_nonzero_initial_coverage(self):
        for key, val in (("baseline_covered_statements", 1),
                         ("baseline_covered_branches", 1),
                         ("eligible_statements", 0)):
            b = copy.deepcopy(BASE)
            b["files"][0][key] = val
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, "baseline must contain executable zero-covered"):
                examine(baseline=b)

    def test_baseline_cannot_transfer_authority(self):
        for key in ("authority_transfer", "merge_authorized", "qps_owner_accepted"):
            b = copy.deepcopy(BASE)
            b["acceptance"][key] = True
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "authority"):
                examine(baseline=b)

    def test_unittest_terminal_requires_successful_unique_population(self):
        logs = [b"Ran 2 tests in 0.01s\nFAILED (failures=1)\n",
                b"Ran 0 tests in 0.01s\nOK\n",
                b"Ran 2 tests in 0.01s\nOK (skipped=2)\n",
                b"Ran 3 tests in 0.01s\nRan 3 tests in 0.02s\nOK\n"]
        for log in logs:
            with self.subTest(log=log), self.assertRaises(ValueError):
                GATE.parse_terminal(log)
        positive = GATE.parse_terminal(
            b"Ran 9 tests in 0.04s\nOK (skipped=1)\n")
        self.assertEqual(positive, {"executed": 9, "passed": 8,
                                    "failed": 0, "skipped": 1})

    def test_missing_measurement_and_invalid_head_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "source-file census"):
            examine(coverage={"meta": coverage_for()["meta"]})
        with self.assertRaisesRegex(ValueError, "source identity"):
            GATE.measure(BASE, coverage_for(), "short",
                         lambda p: "a"*40, GATE.parse_terminal(LOG))

    def test_pulse_never_estimates_worker_capacity_or_statistics(self):
        r = examine()
        self.assertIsNone(r["worker_hours"])
        self.assertIsNone(r["real_worker_capacity"])
        self.assertEqual(r["m1"], "STRUCTURAL_RECEIPT")
        self.assertEqual(r["m2"], "HOLD")
        self.assertEqual(r["m3"], "HOLD")
        self.assertEqual(r["pca"], "NOT_ASSESSABLE")
        self.assertEqual(r["bt"], "NOT_ASSESSABLE")
        self.assertFalse(r["native_artifact_bytes_verified"])


    def test_windows_backslash_paths_are_normalized_to_exact_roster(self):
        candidate = coverage_for()
        candidate["files"] = {
            name.replace("/", "\\"): record
            for name, record in candidate["files"].items()
        }
        receipt = examine(coverage=candidate)
        self.assertEqual(receipt["recovered_zero_covered_assets"], 10)
        self.assertEqual(receipt["unknown_or_incomparable_assets"], 0)
        self.assertEqual(receipt["matched_statement_coverage"]["candidate_covered"], 40)

    def test_windows_and_posix_alias_for_same_file_is_rejected(self):
        candidate = coverage_for()
        name = BASE["files"][0]["path"]
        candidate["files"][name.replace("/", "\\")] = copy.deepcopy(
            candidate["files"][name])
        with self.assertRaisesRegex(ValueError, "duplicate normalized coverage"):
            examine(coverage=candidate)


    def test_detached_git_head_identity_and_ref_reverse(self):
        with tempfile.TemporaryDirectory(prefix="w76-head-") as temp:
            root = pathlib.Path(temp)
            gitdir = root / ".git"
            gitdir.mkdir()
            (gitdir / "HEAD").write_text("a" * 40 + "\n", encoding="ascii")
            self.assertEqual(GATE.exact_checkout_sha(root), "a" * 40)
            (gitdir / "HEAD").write_text("ref: refs/heads/main\n",
                                         encoding="ascii")
            with self.assertRaisesRegex(ValueError, "detached exact"):
                GATE.exact_checkout_sha(root)

    def test_source_blob_hash_is_git_object_identity_not_security_claim(self):
        with tempfile.TemporaryDirectory(prefix="w76-blob-") as temp:
            root = pathlib.Path(temp)
            (root / "src").mkdir()
            path = root / "src" / "demo.py"
            raw = b"answer = 42\n"
            path.write_bytes(raw)
            expected = hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw,
                usedforsecurity=False,
            ).hexdigest()
            self.assertEqual(
                GATE.source_blob_sha(root, "src/demo.py"), expected
            )
            path.write_bytes(b"answer = 43\n")
            self.assertNotEqual(
                GATE.source_blob_sha(root, "src/demo.py"), expected
            )

    def test_source_blob_disallows_missing_symlink_and_traversal(self):
        with tempfile.TemporaryDirectory(prefix="w76-unsafe-") as temp:
            root = pathlib.Path(temp)
            (root / "src").mkdir()
            with self.assertRaisesRegex(ValueError, "unsafe or missing"):
                GATE.source_blob_sha(root, "src/absent.py")
            with self.assertRaisesRegex(ValueError, "unsafe or noncanonical"):
                GATE.source_blob_sha(root, "../outside.py")
            source = root / "src" / "real.py"
            source.write_text("x = 2\n", encoding="utf-8")
            alias = root / "src" / "alias.py"
            try:
                alias.symlink_to(source)
            except (OSError, NotImplementedError):
                return
            with self.assertRaisesRegex(ValueError, "unsafe or missing"):
                GATE.source_blob_sha(root, "src/alias.py")


if __name__ == "__main__":
    unittest.main()
