"""Negative/positive contracts; no GitHub actions, remote work or dependencies."""
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "cbd_matched_coverage_delta.py"
spec = importlib.util.spec_from_file_location("cbd_matched_coverage_delta", MODULE)
metric = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metric)
PATH = "DMAIC_V3/quick_error_fix.py"
SHA = "a" * 40
HASH = "b" * 64


def manifest():
    return {"schema": "cbd.native-checkout-declaration.v1", "repository": "GBOGEB/ABACUS",
            "head_sha": SHA, "checkout_sha": SHA, "run_id": 123, "run_attempt": 2,
            "job_id": 456, "source_sha256": {PATH: HASH}}


def coverage(lines=0, branches=0):
    return {"files": {PATH: {"summary": {"covered_lines": lines,
                                             "num_statements": 165,
                                             "covered_branches": branches,
                                             "num_branches": 56}}}}


def snap(lines=0, branches=0, *, attempt=2):
    m = manifest()
    m["run_attempt"] = attempt
    return metric.make_snapshot(coverage(lines, branches), m, [PATH])


class MatchedCoverage(unittest.TestCase):
    def test_zero_to_measured_improvement(self):
        result = metric.compare(snap(), snap(120, 38, attempt=3))
        self.assertEqual(result["status"], "IMPROVED")
        self.assertEqual(result["modules"][PATH]["statement"]["before"], [0, 165])
        self.assertEqual(result["modules"][PATH]["statement"]["after"], [120, 165])
        self.assertEqual(result["modules"][PATH]["branch"]["after"], [38, 56])
        self.assertEqual(result["merge_admission"], "HOLD")
        self.assertEqual(result["formal_root_closure"], 0)

    def test_stable_numerator_returns_unchanged(self):
        self.assertEqual(metric.compare(snap(99, 31), snap(99, 31))["status"], "UNCHANGED")

    def test_regression_not_hidden_by_other_improvement(self):
        self.assertEqual(metric.compare(snap(85, 40), snap(90, 39, attempt=3))["status"], "REGRESSION")

    def test_source_change_is_not_matched(self):
        other = snap(120, 38)
        other["modules"][PATH]["sha256"] = "c" * 64
        with self.assertRaisesRegex(metric.EvidenceError, "source changed"):
            metric.compare(snap(), other)

    def test_denominator_drift_rejected(self):
        other = snap(100, 32)
        other["modules"][PATH]["num_branches"] = 60
        with self.assertRaisesRegex(metric.EvidenceError, "denominator drift"):
            metric.compare(snap(), other)

    def test_wrong_checkout_fails_closed(self):
        m = manifest()
        m["checkout_sha"] = "c" * 40
        with self.assertRaisesRegex(metric.EvidenceError, "head/checkout mismatch"):
            metric.make_snapshot(coverage(), m, [PATH])

    def test_boolean_run_id_is_not_valid(self):
        m = manifest()
        m["run_id"] = True
        with self.assertRaisesRegex(metric.EvidenceError, "run_id"):
            metric.make_snapshot(coverage(), m, [PATH])

    def test_missing_module_rejected(self):
        with self.assertRaisesRegex(metric.EvidenceError, "coverage or checksum missing"):
            metric.make_snapshot(coverage(), manifest(), ["DMAIC_V3/absent.py"])

    def test_branch_free_module_not_fake_100_percent(self):
        c = coverage(2, 0)
        c["files"][PATH]["summary"].update(num_statements=5, num_branches=0)
        a = metric.make_snapshot(c, manifest(), [PATH])
        self.assertIsNone(metric.compare(a, a)["modules"][PATH]["branch"]["after_percent"])

    def test_out_of_range_numerator_rejected(self):
        with self.assertRaisesRegex(metric.EvidenceError, "numerator exceeds"):
            metric.make_snapshot(coverage(200), manifest(), [PATH])

    def test_cli_emits_proof_without_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "coverage.json").write_text(json.dumps(coverage(120, 38)))
            (root / "manifest.json").write_text(json.dumps(manifest()))
            self.assertEqual(metric.main(["snapshot", "--coverage", str(root / "coverage.json"),
                                          "--manifest", str(root / "manifest.json"),
                                          "--module", PATH, "--out", str(root / "before.json")]), 0)
            self.assertEqual(metric.main(["compare", "--before", str(root / "before.json"),
                                          "--after", str(root / "before.json"),
                                          "--out", str(root / "delta.json")]), 0)
            self.assertEqual(json.loads((root / "delta.json").read_text())["merge_admission"], "HOLD")

    def test_cli_regression_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.json").write_text(json.dumps(snap(100, 40)))
            (root / "b.json").write_text(json.dumps(snap(99, 40, attempt=3)))
            code = metric.main(["compare", "--before", str(root / "a.json"), "--after", str(root / "b.json"), "--out", str(root / "delta.json")])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads((root / "delta.json").read_text())["status"], "REGRESSION")

    def test_malformed_input_json_object_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text("[]")
            with self.assertRaisesRegex(metric.EvidenceError, "object"):
                metric.read_json(path)

    def test_invalid_path_and_manifest_metadata_rejected(self):
        for path in ("../escape.py", "/absolute.py", "./unstable.py", "back\\slash.py"):
            with self.subTest(path=path), self.assertRaises(metric.EvidenceError):
                metric.valid_path(path)
        for key, bad in (("schema", "bad"), ("repository", "wrong"), ("head_sha", "bad")):
            m = manifest()
            m[key] = bad
            with self.subTest(key=key), self.assertRaises(metric.EvidenceError):
                metric.validate_manifest(m)

    def test_invalid_source_and_missing_coverage_structure_rejected(self):
        for value in ({}, {PATH: "short"}):
            m = manifest()
            m["source_sha256"] = value
            with self.assertRaises(metric.EvidenceError):
                metric.validate_manifest(m)
        with self.assertRaisesRegex(metric.EvidenceError, "files map"):
            metric.make_snapshot({}, manifest(), [PATH])
        with self.assertRaisesRegex(metric.EvidenceError, "unique"):
            metric.make_snapshot(coverage(), manifest(), [PATH, PATH])
        with self.assertRaisesRegex(metric.EvidenceError, "summary"):
            metric.make_snapshot({"files": {PATH: {}}}, manifest(), [PATH])

    def test_bad_counts_rejected(self):
        for k, val in (("num_statements", 0), ("covered_lines", -1),
                       ("covered_branches", "5")):
            c = coverage(1, 0)
            c["files"][PATH]["summary"][k] = val
            with self.subTest(counter=k), self.assertRaises(metric.EvidenceError):
                metric.make_snapshot(c, manifest(), [PATH])

    def test_snapshot_schema_and_authority_rejected(self):
        a = snap()
        for key, value in (("scope", "ALL_FILES"), ("merge_admission", "PASS"),
                           ("formal_root_closure", 1)):
            other = deepcopy(a)
            other[key] = value
            with self.subTest(field=key), self.assertRaises(metric.EvidenceError):
                metric.compare(a, other)

    def test_source_scope_drift_rejected(self):
        a, b = snap(), snap()
        b["modules"]["other.py"] = b["modules"].pop(PATH)
        with self.assertRaises(metric.EvidenceError):
            metric.compare(a, b)

    def test_same_run_attempt_cannot_forge_numerator_uplift(self):
        with self.assertRaisesRegex(metric.EvidenceError, "same run/attempt"):
            metric.compare(snap(), snap(100, 38))

    def test_parallel_jobs_in_same_attempt_are_not_time_series(self):
        other = snap(1, 1)
        other["job_id"] += 1
        with self.assertRaisesRegex(metric.EvidenceError, "same run/attempt"):
            metric.compare(snap(), other)

    def test_independent_declared_attempts_remain_provisional(self):
        delta = metric.compare(snap(), snap(100, 38, attempt=3))
        self.assertEqual(delta["status"], "IMPROVED")
        self.assertEqual(
            delta["declared_run_attempt_relation"],
            "DISTINCT_DECLARED_RUN_ATTEMPTS_NOT_AUTHENTICATED",
        )
        self.assertIsNone(delta["accepted_matched_main_delta"])
        self.assertEqual(delta["merge_admission"], "HOLD")

    def test_sub_micro_percentage_gain_is_not_lost_to_rounding(self):
        before, after = snap(), snap(1, 0, attempt=3)
        for sample in (before, after):
            sample["modules"][PATH]["num_statements"] = 1_000_000_000
        delta = metric.compare(before, after)
        self.assertEqual(delta["status"], "IMPROVED")
        self.assertEqual(delta["modules"][PATH]["statement"]["delta_covered_items"], 1)
        self.assertEqual(delta["modules"][PATH]["statement"]["delta_percentage_points"], 0)

    def test_cli_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            with self.assertRaises(SystemExit) as exit_info:
                metric.main(["compare", "--before", str(path),
                             "--after", str(path), "--out", str(path)])
            self.assertEqual(exit_info.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
