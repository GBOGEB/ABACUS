"""W77 P3 measurement controls: no false zero, cohort, source or authority gain."""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import codepurple_zero_frontier as FRONTIER  # noqa: E402

MANIFEST = json.loads(
    (ROOT / "triage" / "W77_LEGACY12_SOURCE_BASELINE.json").read_text(encoding="utf-8")
)
HEAD = "a" * 40


def fixture():
    before = {"meta": {"version": "7.16.2", "branch_coverage": True}, "files": {}}
    after = copy.deepcopy(before)
    for item in MANIFEST["targets"]:
        name = item["path"]
        statements = item["baseline"]["statements"]["eligible"]
        branches = item["baseline"]["branches"]["eligible"]
        before["files"][name] = {
            "summary": {
                "num_statements": statements,
                "covered_lines": 0,
                "num_branches": branches,
                "covered_branches": 0,
            }
        }
        after["files"][name] = {
            "summary": {
                "num_statements": statements,
                "covered_lines": min(statements, 5),
                "num_branches": branches,
                "covered_branches": min(branches, 2),
            }
        }
    return before, after


class W77FrontierContractTests(unittest.TestCase):
    def test_all_twelve_recovered_in_synthetic_control(self):
        before, after = fixture()
        result = FRONTIER.compare(before, after, MANIFEST, HEAD)
        self.assertTrue(result["global_cohort_comparable"])
        self.assertEqual(result["targeted_zero_recovered"], 12)
        self.assertEqual(result["global_zero_delta"], 12)
        self.assertEqual(result["matched"]["zero_before"], 12)
        self.assertEqual(result["matched"]["zero_after"], 0)
        self.assertEqual(result["matched"]["eligible_statements"], 1889)
        self.assertEqual(result["matched"]["eligible_branches"], 238)
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["security_waiver"])

    def test_new_uncovered_script_excluded_from_original_denominator(self):
        before, after = fixture()
        after["files"]["scripts/new_pulse.py"] = {
            "summary": {
                "num_statements": 100,
                "covered_lines": 0,
                "num_branches": 10,
                "covered_branches": 0,
            }
        }
        result = FRONTIER.compare(before, after, MANIFEST, HEAD)
        self.assertEqual(result["new_files_excluded"], ["scripts/new_pulse.py"])
        self.assertEqual(result["global_zero_delta"], 12)
        self.assertEqual(result["baseline_files"], 12)
        self.assertEqual(result["candidate_files"], 13)

    def test_missing_file_is_unknown_not_zero(self):
        before, after = fixture()
        first = MANIFEST["targets"][0]["path"]
        del after["files"][first]
        result = FRONTIER.compare(before, after, MANIFEST, HEAD)
        self.assertFalse(result["global_cohort_comparable"])
        self.assertIsNone(result["global_zero_delta"])
        self.assertEqual(result["targeted_incomparable_unknown"], 1)

    def test_denominator_drift_is_incomparable(self):
        before, after = fixture()
        first = MANIFEST["targets"][0]["path"]
        after["files"][first]["summary"]["num_branches"] += 1
        result = FRONTIER.compare(before, after, MANIFEST, HEAD)
        self.assertFalse(result["global_cohort_comparable"])
        self.assertEqual(result["changed_denominator_files"], [first])
        self.assertIsNone(result["matched"])
        self.assertEqual(result["targeted_incomparable_unknown"], 1)

    def test_windows_paths_normalize_only_once(self):
        before, after = fixture()
        after["files"] = {
            name.replace("/", "\\"): data for name, data in after["files"].items()
        }
        result = FRONTIER.compare(before, after, MANIFEST, HEAD)
        self.assertEqual(result["targeted_zero_recovered"], 12)

    def test_duplicate_windows_posix_paths_rejected(self):
        before, after = fixture()
        path = "scripts/new_pulse.py"
        summary = {
            "summary": {
                "num_statements": 1,
                "covered_lines": 0,
                "num_branches": 0,
                "covered_branches": 0,
            }
        }
        after["files"][path] = summary
        after["files"][path.replace("/", "\\")] = summary
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            FRONTIER.compare(before, after, MANIFEST, HEAD)

    def test_forged_integer_and_numerator_exceeds_denominator_rejected(self):
        for invalid in (-1, True, 999999):
            before, after = fixture()
            first = MANIFEST["targets"][0]["path"]
            after["files"][first]["summary"]["covered_lines"] = invalid
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                FRONTIER.compare(before, after, MANIFEST, HEAD)

    def test_tampered_source_digest_and_changed_zero_roster_rejected(self):
        before, after = fixture()
        item = copy.deepcopy(MANIFEST)
        item["targets"][0]["baseline"]["statements"]["covered"] = 1
        with self.assertRaisesRegex(ValueError, "nonzero target"):
            FRONTIER.compare(before, after, item, HEAD)
        item = copy.deepcopy(MANIFEST)
        item["targets"][0]["source_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "digest"):
            FRONTIER.compare(before, after, item, HEAD)

    def test_missing_local_source_cannot_claim_source_identity(self):
        before, after = fixture()
        with tempfile.TemporaryDirectory(prefix="w77-blob-reverse-") as temp:
            with self.assertRaisesRegex(ValueError, "source"):
                FRONTIER.compare(before, after, MANIFEST, HEAD, source_root=temp)

    def test_actual_pinned_repository_source_digest_is_identical(self):
        item = MANIFEST["targets"][0]
        self.assertEqual(
            FRONTIER._source_sha256(item["path"], ROOT), item["source_sha256"]
        )

    def test_actual_twelve_pinned_source_digests_match(self):
        for item in MANIFEST["targets"]:
            with self.subTest(source=item["path"]):
                self.assertEqual(
                    FRONTIER._source_sha256(item["path"], ROOT),
                    item["source_sha256"],
                )

    def test_false_complete_statistics_are_never_granted(self):
        before, after = fixture()
        first = MANIFEST["targets"][0]["path"]
        after["files"][first]["summary"]["covered_lines"] = 0
        result = FRONTIER.compare(before, after, MANIFEST, HEAD)
        self.assertEqual(result["global_zero_delta"], 11)
        self.assertEqual(result["targeted_zero_recovered"], 11)
        self.assertEqual(result["accepted_root_closures"], 0)
        self.assertIsNone(result["worker_hours"])
        self.assertIsNone(result["real_runner_capacity"])
        self.assertEqual(result["m2"], "HOLD")
        self.assertEqual(result["m3"], "HOLD")
        self.assertEqual(result["pca_bt"], "NOT_ASSESSABLE")

    def test_noncanonical_paths_and_bad_head_fail_closed(self):
        for value in ("../escape.py", "C:\\disk\\source.py", "/root/x.py"):
            with self.subTest(path=value), self.assertRaises(ValueError):
                FRONTIER._normalize(value)
        before, after = fixture()
        with self.assertRaisesRegex(ValueError, "exact candidate"):
            FRONTIER.compare(before, after, MANIFEST, "short")


if __name__ == "__main__":
    unittest.main()
