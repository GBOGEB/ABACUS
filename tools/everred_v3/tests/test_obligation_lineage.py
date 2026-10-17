"""Source obligation identity and regression tests, including scope growth."""

import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from obligation_lineage import SCHEMA, compare, parse_artifact, snapshot, valid_path

A = "a" * 40
B = "b" * 40
D = "d" * 64


def module(executed, missing, ran, missed):
    return {
        "executed_lines": executed,
        "missing_lines": missing,
        "executed_branches": ran,
        "missing_branches": missed,
        "summary": {
            "num_statements": len(executed) + len(missing),
            "num_branches": len(ran) + len(missed),
        },
    }


def inputs(sha=A, files=None, blobs=None, config="same"):
    if files is None:
        files = {"x.py": module([1], [2], [[1, 2]], [[2, 3]])}
    if blobs is None:
        blobs = {p: A for p in files}
    report = {"meta": {"version": "7.16.2"}, "files": files}
    manifest = {
        "schema": SCHEMA + ".manifest",
        "repository": "GBOGEB/ABACUS",
        "source_sha": sha,
        "run_id": 42,
        "job_id": 17,
        "coverage_artifact_sha256": D,
        "file_blobs": blobs,
        "profile": {
            "tool_version": "7.16.2",
            "config_digest": config,
            "test_selection": "unit-regressions",
            "exclusions": "standard",
            "instrumentation": "branch",
        },
    }
    return report, manifest


def observed(sha=A, files=None, blobs=None, config="same"):
    data, manifest = inputs(sha, files, blobs, config)
    return snapshot(data, manifest)


class SourceObligations(unittest.TestCase):
    def test_existing_uncovered_obligations_repaired(self):
        a = observed()
        b = observed(B, {"x.py": module([1, 2], [], [[1, 2], [2, 3]], [])})
        r = compare(a, b)
        self.assertEqual(r["status"], "FULLY_STABLE_SOURCE_BLOB_MAPPING")
        self.assertEqual(
            r["families"]["branches"]["previously_uncovered_now_covered_verified"], 1
        )
        self.assertEqual(
            r["families"]["statements"]["previously_uncovered_now_covered_verified"], 1
        )
        self.assertEqual(r["families"]["branches"]["eligible_net_delta"], 0)

    def test_stable_obligation_denominator_excludes_new_scope(self):
        before = observed()
        after = observed(
            B,
            {
                "x.py": module([1, 2], [], [[1, 2], [2, 3]], []),
                "new.py": module([1, 2, 3, 4], [], [[1, 2]], []),
            },
        )
        result = compare(before, after)
        statements = result["families"]["statements"]
        branches = result["families"]["branches"]
        self.assertEqual(statements["source_matched_eligible_obligations"], 2)
        self.assertEqual(branches["source_matched_eligible_obligations"], 2)
        self.assertEqual(statements["eligible_after"], 6)
        self.assertEqual(statements["source_matched_scope_percent_after"], 33.3333)
        self.assertEqual(branches["source_matched_scope_percent_after"], 66.6667)

        changed = observed(
            B,
            {"x.py": module([1, 2], [], [[1, 2], [2, 3]], [])},
            blobs={"x.py": B},
        )
        self.assertEqual(
            compare(before, changed)["families"]["statements"][
                "source_matched_eligible_obligations"
            ], 0
        )
        unmatched = observed(B, config="changed")
        self.assertIsNone(
            compare(before, unmatched)["families"]["statements"][
                "source_matched_eligible_obligations"
            ]
        )

    def test_new_fully_covered_file_cannot_fake_old_debt(self):
        a = observed()
        files = {
            "x.py": module([1], [2], [[1, 2]], [[2, 3]]),
            "new.py": module(list(range(1, 101)), [], [[1, 2], [2, 3]], []),
        }
        b = observed(B, files)
        r = compare(a, b)
        self.assertEqual(r["status"], "PARTIALLY_ATTRIBUTABLE")
        self.assertEqual(
            r["families"]["statements"]["previously_uncovered_now_covered_verified"], 0
        )
        self.assertGreater(
            r["families"]["statements"]["rate_after"],
            r["families"]["statements"]["rate_before"],
        )
        self.assertEqual(r["families"]["statements"]["eligible_net_delta"], 100)

    def test_regression_recorded_even_when_denominator_grows(self):
        a = observed(A, {"x.py": module([1, 2], [], [[1, 2], [2, 3]], [])})
        b = observed(
            B,
            {
                "x.py": module([1], [2], [[1, 2]], [[2, 3]]),
                "new.py": module(list(range(1, 101)), [], [[1, 2]], []),
            },
        )
        out = compare(a, b)
        self.assertEqual(
            out["families"]["branches"]["previously_covered_now_uncovered_verified"], 1
        )
        self.assertEqual(
            out["families"]["statements"]["previously_covered_now_uncovered_verified"],
            1,
        )

    def test_changed_git_blob_withholds_old_debt_credit(self):
        a = observed()
        b = observed(
            B,
            {"x.py": module([1, 2], [], [[1, 2], [2, 3]], [])},
            blobs={"x.py": B},
        )
        out = compare(a, b)
        self.assertEqual(out["changed_blob_files"], ["x.py"])
        self.assertEqual(
            out["families"]["branches"]["previously_uncovered_now_covered_verified"], 0
        )
        self.assertIsNone(
            out["families"]["branches"]["old_debt_credit_on_changed_blobs"]
        )

    def test_changed_instrumentation_withholds_attribution(self):
        a = observed()
        b = observed(
            B, {"x.py": module([1, 2], [], [[1, 2], [2, 3]], [])}, config="new"
        )
        out = compare(a, b)
        self.assertFalse(out["profile_compatible"])
        self.assertIsNone(
            out["families"]["branches"]["previously_uncovered_now_covered_verified"]
        )

    def test_same_git_blob_conflicting_eligibility_rejected(self):
        a = observed()
        b = observed(B, {"x.py": module([1, 2, 3], [], [[1, 2]], [])})
        with self.assertRaisesRegex(ValueError, "inconsistent eligible"):
            compare(a, b)

    def test_duplicate_or_unsafe_source_path_rejected(self):
        for path in ("../other.py", "/etc/passwd", r"C:\Windows\a.py", "x//a.py"):
            with self.assertRaises(ValueError):
                observed(A, {path: module([1], [], [], [])})
        with self.assertRaisesRegex(ValueError, "duplicate normalized path"):
            observed(
                A,
                {
                    "src/a.py": module([1], [], [], []),
                    r"src\a.py": module([1], [], [], []),
                },
            )

    def test_duplicate_branch_and_line_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate arc"):
            observed(A, {"x.py": module([1], [], [[1, 2], [1, 2]], [])})
        with self.assertRaisesRegex(ValueError, "duplicate executed_lines"):
            observed(A, {"x.py": module([1, 1], [], [], [])})

    def test_contradictory_coverage_rejected(self):
        with self.assertRaisesRegex(ValueError, "contradictory arc"):
            observed(A, {"x.py": module([1], [], [[1, 2]], [[1, 2]])})

    def test_denominator_forgery_rejected(self):
        report, receipt = inputs()
        report["files"]["x.py"]["summary"]["num_branches"] = 999
        with self.assertRaisesRegex(ValueError, "branch denominator mismatch"):
            snapshot(report, receipt)

    def test_wrong_source_blob_scope_rejected(self):
        report, receipt = inputs()
        receipt["file_blobs"] = {"different.py": A}
        with self.assertRaisesRegex(ValueError, "scope mismatch"):
            snapshot(report, receipt)

    def test_artifact_bytes_digest_required(self):
        raw, manifest = inputs()
        import hashlib
        import json

        encoded = json.dumps(raw, sort_keys=True).encode()
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            parse_artifact(encoded, manifest)
        manifest["coverage_artifact_sha256"] = hashlib.sha256(encoded).hexdigest()
        accepted = parse_artifact(encoded, manifest)
        self.assertFalse(accepted["native_artifact_bytes_authenticated"])

    def test_cross_repository_comparison_fails(self):
        left = observed()
        right = observed(B)
        right["source"]["repository"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "cross-repository"):
            compare(left, right)

    def test_stress_600_modules_1200_arcs_deterministic(self):
        files = {
            f"module_{i:04d}.py": module([1, 2], [3], [[1, 2]], [[2, 3]])
            for i in range(600)
        }
        a = observed(A, files)
        b = observed(B, files)
        first = compare(a, b)
        second = compare(a, b)
        self.assertEqual(first, second)
        self.assertEqual(first["families"]["branches"]["eligible_after"], 1200)
        self.assertFalse(first["independent_native_receipt_verification"])


if __name__ == "__main__":
    unittest.main()
