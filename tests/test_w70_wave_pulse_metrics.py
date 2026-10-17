"""Negative, provenance and comparability controls for W70 pulse receipts."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import w70_wave_pulse_metrics as p

HEAD = "a" * 40
SCOPE = "b" * 64


def sample():
    lanes = {}
    for i, lane in enumerate(p.LANES):
        lanes[lane] = {
            "source_sha": HEAD,
            "lane": lane,
            "totals": {
                "total_population": 10 + i,
                "backlog_open": i + 1,
                "backlog_closed": 9,
            },
        }
    feature = {
        "source_sha": HEAD,
        "total_population": sum(10 + i for i in range(5)),
        "total_open_backlog": sum(i + 1 for i in range(5)),
    }
    coverage = {
        "meta": {"version": "7.13.3"},
        "files": {
            "tools/w70_wave_pulse_metrics.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 88,
                    "num_branches": 30,
                    "covered_branches": 24,
                }
            }
        },
    }
    return feature, lanes, coverage


def make(**kwargs):
    feature, lanes, coverage = sample()
    return p.build(
        feature,
        lanes,
        coverage,
        repo="GBOGEB/ABACUS",
        sha=HEAD,
        run_id=17,
        attempt=1,
        scope_digest=SCOPE,
        **kwargs,
    )


class W70PulseTests(unittest.TestCase):
    def test_real_counts_and_withheld_credit(self):
        r = make()
        self.assertEqual(60, r["debt"]["measured_lane_population_sum"])
        self.assertEqual(15, r["debt"]["open_manifestations_sum"])
        self.assertEqual(45, r["debt"]["closed_manifestations_sum"])
        self.assertIsNone(r["debt"]["unique_confirmed_roots"])
        self.assertEqual(88.0, r["coverage"]["line"]["pct"])
        self.assertEqual(80.0, r["coverage"]["branch"]["pct"])
        self.assertIsNone(r["native_run_authenticated"])
        self.assertEqual("HOLD", r["admission"])

    def test_deterministic_and_digest(self):
        self.assertEqual(make(), make())
        r = make()
        self.assertEqual(
            r["receipt_sha256"],
            p.sha256(
                p.stable({k: v for k, v in r.items() if k != "receipt_sha256"}).encode()
            ),
        )

    def test_missing_baseline_is_null_not_zero(self):
        result = make()["coverage_delta"]
        self.assertEqual("NO_BASELINE", result["reason"])
        self.assertIsNone(result["line_delta_pp"])
        self.assertIsNone(result["debt_delta"])

    def test_scope_matched_delta(self):
        old = make()
        feature, lanes, coverage = sample()
        coverage["files"]["tools/w70_wave_pulse_metrics.py"]["summary"][
            "covered_lines"
        ] = 92
        coverage["files"]["tools/w70_wave_pulse_metrics.py"]["summary"][
            "covered_branches"
        ] = 27
        new = p.build(
            feature,
            lanes,
            coverage,
            repo="GBOGEB/ABACUS",
            sha=HEAD,
            run_id=18,
            attempt=1,
            scope_digest=SCOPE,
            previous=old,
        )
        self.assertTrue(new["coverage_delta"]["comparable"])
        self.assertEqual(4.0, new["coverage_delta"]["line_delta_pp"])
        self.assertEqual(10.0, new["coverage_delta"]["branch_delta_pp"])
        self.assertIsNone(new["coverage_delta"]["debt_delta"])

    def test_changed_source_withholds_delta(self):
        old = make()
        feature, lanes, coverage = sample()
        new = p.build(
            feature,
            lanes,
            coverage,
            repo="GBOGEB/ABACUS",
            sha=HEAD,
            run_id=18,
            attempt=1,
            scope_digest="c" * 64,
            previous=old,
        )
        self.assertEqual(
            "INSTRUMENTED_SCOPE_OR_TOOL_CHANGED", new["coverage_delta"]["reason"]
        )
        self.assertIsNone(new["coverage_delta"]["line_delta_pp"])

    def test_mismatched_population_not_same_scope(self):
        old = make()
        old["coverage"]["line"]["eligible"] = 101
        old["receipt_sha256"] = p.sha256(
            p.stable({k: v for k, v in old.items() if k != "receipt_sha256"}).encode()
        )
        res = make(previous=old)
        self.assertEqual(
            "ELIGIBLE_DENOMINATOR_CHANGED", res["coverage_delta"]["reason"]
        )

    def test_baseline_tampering_is_blocked(self):
        old = make()
        old["coverage"]["line"]["pct"] = 100
        with self.assertRaisesRegex(ValueError, "digest"):
            make(previous=old)

    def test_baseline_repo_not_comparable(self):
        old = make()
        old["repository"] = "GBOGEB/CODEX"
        old["receipt_sha256"] = p.sha256(
            p.stable({k: v for k, v in old.items() if k != "receipt_sha256"}).encode()
        )
        self.assertEqual(
            "DIFFERENT_REPOSITORY", make(previous=old)["coverage_delta"]["reason"]
        )

    def test_reject_invalid_baseline_schema(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            make(previous={})

    def test_reject_nonfinite_raw_numerators(self):
        feature, lanes, coverage = sample()
        coverage["files"]["tools/w70_wave_pulse_metrics.py"]["summary"][
            "covered_lines"
        ] = float("nan")
        with self.assertRaisesRegex(ValueError, "invalid line"):
            p.build(
                feature,
                lanes,
                coverage,
                repo="GBOGEB/ABACUS",
                sha=HEAD,
                run_id=17,
                attempt=1,
                scope_digest=SCOPE,
            )

    def test_reject_boolean_counts(self):
        feature, lanes, coverage = sample()
        lanes[p.LANES[0]]["totals"]["backlog_open"] = True
        with self.assertRaisesRegex(ValueError, "invalid debt"):
            p.build(
                feature,
                lanes,
                coverage,
                repo="GBOGEB/ABACUS",
                sha=HEAD,
                run_id=17,
                attempt=1,
                scope_digest=SCOPE,
            )

    def test_reject_missing_lane(self):
        feature, lanes, coverage = sample()
        lanes.pop(p.LANES[2])
        with self.assertRaisesRegex(ValueError, "five lane"):
            p.verify_lanes(feature, lanes, HEAD)

    def test_reject_forged_lane_sha(self):
        feature, lanes, coverage = sample()
        lanes[p.LANES[1]]["source_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "SHA"):
            p.verify_lanes(feature, lanes, HEAD)

    def test_reject_incorrect_feature_totals(self):
        feature, lanes, coverage = sample()
        feature["total_population"] = 61
        with self.assertRaisesRegex(ValueError, "aggregate"):
            p.verify_lanes(feature, lanes, HEAD)

    def test_reject_coverage_wrong_module(self):
        feature, lanes, cov = sample()
        cov["files"] = {"other.py": list(cov["files"].values())[0]}
        with self.assertRaisesRegex(ValueError, "scope"):
            p.source_metrics(cov, SCOPE)

    def test_reject_mixed_scope(self):
        feature, lanes, cov = sample()
        cov["files"]["other.py"] = {"summary": {}}
        with self.assertRaisesRegex(ValueError, "exactly one"):
            p.source_metrics(cov, SCOPE)

    def test_reject_missing_version_and_invalid_digest(self):
        _, _, cov = sample()
        with self.assertRaisesRegex(ValueError, "digest"):
            p.source_metrics(cov, "bad")
        cov["meta"].pop("version")
        with self.assertRaisesRegex(ValueError, "version"):
            p.source_metrics(cov, SCOPE)

    def test_reject_zero_branch_denominator(self):
        _, _, cov = sample()
        cov["files"][p.SCOPE_FILE]["summary"]["num_branches"] = 0
        with self.assertRaisesRegex(ValueError, "invalid line"):
            p.source_metrics(cov, SCOPE)

    def test_reject_wrong_run_id_and_repo(self):
        feature, lanes, coverage = sample()
        for repo, run_id, attempt in (
            ("GBOGEB/ABACUS", True, 1),
            ("GBOGEB/ABACUS", 1, 0),
            ("not-a-repo", 1, 1),
        ):
            with self.subTest(repo=repo, run_id=run_id, attempt=attempt):
                with self.assertRaises(ValueError):
                    p.build(
                        feature,
                        lanes,
                        coverage,
                        repo=repo,
                        sha=HEAD,
                        run_id=run_id,
                        attempt=attempt,
                        scope_digest=SCOPE,
                    )

    def test_text_summary_distinguishes_root_and_manifestations(self):
        text = p.summary(make())
        self.assertIn("not distinct root count", text)
        self.assertIn("UNKNOWN / HOLD / ZERO", text)
        self.assertIn("80.0%", text)

    def test_git_checkout_identity_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gitdir = root / ".git"
            gitdir.mkdir()
            (gitdir / "HEAD").write_text(HEAD, encoding="utf-8")
            self.assertEqual(p.checked_out_head(root), HEAD)
            (gitdir / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "detached exact-SHA"):
                p.checked_out_head(root)
            (gitdir / "HEAD").unlink()
            with self.assertRaisesRegex(ValueError, "unavailable"):
                p.checked_out_head(root)

    def test_git_worktree_pointer_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gitdir = root / "tracked"
            gitdir.mkdir()
            (gitdir / "HEAD").write_text(HEAD, encoding="utf-8")
            (root / ".git").write_text("gitdir: tracked\n", encoding="utf-8")
            self.assertEqual(p.checked_out_head(root), HEAD)

    def test_file_output_main_and_exact_checkout_rejection(self):
        feature, lanes, coverage = sample()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for lane, obj in lanes.items():
                (root / (lane + ".json")).write_text(json.dumps(obj))
            (root / "FEATURE_ROW.json").write_text(json.dumps(feature))
            cov = root / "cov.json"
            cov.write_text(json.dumps(coverage))
            source = root / "source.py"
            source.write_text("print('hello')")
            target = root / "pulse.json"
            args = [
                "w70",
                "--lane-dir",
                str(root),
                "--coverage",
                str(cov),
                "--source-path",
                str(source),
                "--sha",
                HEAD,
                "--run-id",
                "17",
                "--attempt",
                "1",
                "--out",
                str(target),
                "--summary",
                str(root / "summary.md"),
            ]
            with (
                patch.object(sys, "argv", args),
                patch.object(p, "checked_out_head", return_value=HEAD),
            ):
                self.assertEqual(0, p.main())
            self.assertTrue(target.exists())
            self.assertIn("W70 exact-SHA", (root / "summary.md").read_text())
            with (
                patch.object(sys, "argv", args),
                patch.object(p, "checked_out_head", return_value="c" * 40),
            ):
                with self.assertRaisesRegex(ValueError, "HEAD differs"):
                    p.main()


if __name__ == "__main__":
    unittest.main()
