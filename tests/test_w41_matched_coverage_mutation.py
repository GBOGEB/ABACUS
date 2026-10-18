"""W41 disjoint coverage integrity/temporal fault-injection tests.

Coverage ratios and mutations below are fixture oracles, not accepted native
coverage or root-closure credit. No GitHub calls, dispatch or security waiver.
"""

import copy
import inspect
import unittest

from scripts import cbd_matched_coverage_delta as matched
from scripts import cbd_coverage_temporal_gate as temporal

HEAD = "a" * 40
HASH_A = "b" * 64
HASH_B = "c" * 64
A = "DMAIC_V3/quick_error_fix.py"
B = "DMAIC_V3/quick_error_lister.py"


def make_manifest(run=100, attempt=1, checkout=HEAD):
    return {
        "schema": "cbd.native-checkout-declaration.v1",
        "repository": "GBOGEB/ABACUS",
        "head_sha": HEAD,
        "checkout_sha": checkout,
        "run_id": run,
        "run_attempt": attempt,
        "job_id": run + 200,
        "source_sha256": {A: HASH_A, B: HASH_B},
    }


def coverage(a_lines=100, b_lines=70, a_branches=30, b_branches=20,
             at="2026-10-18T10:10:00Z"):
    return {
        "meta": {"branch_coverage": True, "timestamp": at},
        "files": {
            A: {"summary": {"covered_lines": a_lines, "num_statements": 165,
                            "covered_branches": a_branches, "num_branches": 56}},
            B: {"summary": {"covered_lines": b_lines, "num_statements": 104,
                            "covered_branches": b_branches, "num_branches": 38}},
        },
    }


def measured(run=100, attempt=1, a_lines=100, b_lines=70,
             a_branches=30, b_branches=20):
    return matched.make_snapshot(
        coverage(a_lines, b_lines, a_branches, b_branches),
        make_manifest(run=run, attempt=attempt), [A, B],
    )


def junit(tests=2, cases=None, when="2026-10-18T10:00:00Z", elapsed="60",
          failures=0, errors=0, skipped=0):
    if cases is None:
        cases = (
            '<testcase classname="contract" name="one"/>'
            '<testcase classname="contract" name="two"/>'
        )
    return (
        '<testsuites><testsuite tests="' + str(tests) + '" failures="'
        + str(failures) + '" errors="' + str(errors) + '" skipped="'
        + str(skipped) + '" timestamp="' + when + '" time="'
        + elapsed + '">' + cases + '</testsuite></testsuites>'
    )


def evaluate(c=None, j=None, coverage_head=HEAD, test_head=HEAD):
    return temporal.measure(
        coverage() if c is None else c,
        junit() if j is None else j,
        {"exact_sha": coverage_head}, {"exact_sha": test_head},
        expected_sha=HEAD,
    )


class SourceMatchedDifferentialProof(unittest.TestCase):
    def test_two_module_improvement_with_exact_denominators(self):
        before = measured()
        after = measured(run=101, attempt=2, a_lines=130, b_lines=85,
                         a_branches=42, b_branches=31)
        result = matched.compare(before, after)
        self.assertEqual(result["status"], "IMPROVED")
        self.assertEqual(result["modules"][A]["statement"]["before"], [100, 165])
        self.assertEqual(result["modules"][A]["statement"]["after"], [130, 165])
        self.assertEqual(result["modules"][B]["branch"]["before"], [20, 38])
        self.assertEqual(result["modules"][B]["branch"]["after"], [31, 38])
        self.assertIsNone(result["accepted_matched_main_delta"])
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_regression_dominates_other_module_improvement(self):
        old = measured()
        new = measured(run=101, attempt=2, a_lines=99, b_lines=95)
        result = matched.compare(old, new)
        self.assertEqual(result["status"], "REGRESSION")
        self.assertEqual(result["modules"][A]["statement"]["delta_covered_items"], -1)
        self.assertEqual(result["modules"][B]["statement"]["delta_covered_items"], 25)

    def test_regression_operator_mutant_is_killed(self):
        source = inspect.getsource(matched.compare)
        needle = 'regression |= new[nkey] < old[nkey]'
        self.assertEqual(source.count(needle), 1)
        # Independently calculate the wrong-sign mutant's outcome without
        # executing generated code or introducing a new security-scanner debt.
        old = measured()
        new = measured(run=101, attempt=2, a_lines=99)
        original = old["modules"][A]["covered_lines"]
        changed = new["modules"][A]["covered_lines"]
        self.assertEqual(matched.compare(old, new)["status"], "REGRESSION")
        self.assertFalse(changed > original)
        self.assertTrue(changed < original)

    def test_source_and_denominator_mutations_rejected(self):
        old = measured()
        for label in ("source", "statement_denominator", "branch_denominator",
                      "missing_module", "different_scope"):
            with self.subTest(label=label):
                changed = measured(run=101, attempt=2)
                if label == "source":
                    changed["modules"][A]["sha256"] = "d" * 64
                elif label == "statement_denominator":
                    changed["modules"][A]["num_statements"] += 1
                elif label == "branch_denominator":
                    changed["modules"][B]["num_branches"] += 1
                elif label == "missing_module":
                    changed["modules"].pop(B)
                else:
                    changed["scope"] = "BROAD_MAIN_COVERAGE"
                with self.assertRaises(matched.EvidenceError):
                    matched.compare(old, changed)

    def test_same_run_attempt_cannot_invent_delta(self):
        old = measured()
        changed = measured(a_lines=105)
        with self.assertRaisesRegex(matched.EvidenceError, "same run/attempt"):
            matched.compare(old, changed)

    def test_manifest_and_counter_faults_do_not_produce_snapshot(self):
        original = make_manifest()
        for label in ("wrong_checkout", "bad_run", "bad_checksum",
                      "traversal", "windows_path", "bad_counter"):
            with self.subTest(label=label):
                m = copy.deepcopy(original)
                c = coverage()
                modules = [A, B]
                if label == "wrong_checkout":
                    m["checkout_sha"] = "f" * 40
                elif label == "bad_run":
                    m["run_id"] = True
                elif label == "bad_checksum":
                    m["source_sha256"][A] = "not-a-sha256"
                elif label == "traversal":
                    modules = ["../bad.py"]
                elif label == "windows_path":
                    modules = ["C:\\temp\\bad.py"]
                elif label == "bad_counter":
                    c["files"][A]["summary"]["covered_lines"] = 166
                with self.assertRaises(matched.EvidenceError):
                    matched.make_snapshot(c, m, modules)


class TemporalAndJUnitIntegrity(unittest.TestCase):
    def test_valid_native_fixture_is_review_only(self):
        out = evaluate()
        self.assertEqual(out["status"], "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW")
        self.assertEqual([out["covered_target_statements"], out["eligible_target_statements"]],
                         [170, 269])
        self.assertEqual([out["covered_target_branches"], out["eligible_target_branches"]],
                         [50, 94])
        self.assertIsNone(out["accepted_coverage_uplift"])
        self.assertEqual(out["merge_admission"], "HOLD")

    def test_temporal_boundary_and_stale_mutation(self):
        exact = evaluate(c=coverage(at="2026-10-18T10:01:00Z"))
        self.assertEqual(exact["time_gap_seconds"], 0)
        self.assertEqual(exact["status"], "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW")
        stale = evaluate(c=coverage(at="2026-10-18T10:00:59Z"))
        self.assertEqual(stale["status"], "HOLD")
        self.assertEqual(stale["coverage_provenance"], "STALE_BEFORE_TEST_COMPLETION")

    def test_duplicate_junit_case_cannot_count_twice(self):
        double = ('<testcase classname="same" name="duplicate"/>'
                  '<testcase classname="same" name="duplicate"/>')
        out = evaluate(j=junit(cases=double))
        self.assertEqual(out["junit_count_integrity"], "MISMATCH")
        self.assertEqual(out["status"], "HOLD")

    def test_skipped_only_and_failed_suite_rejected(self):
        skipped_cases = (
            '<testcase classname="contract" name="one"><skipped/></testcase>'
            '<testcase classname="contract" name="two"><skipped/></testcase>'
        )
        with self.assertRaises(ValueError):
            evaluate(j=junit(cases=skipped_cases, skipped=2))
        failed_cases = (
            '<testcase classname="contract" name="one"><failure/></testcase>'
            '<testcase classname="contract" name="two"/>'
        )
        with self.assertRaises(ValueError):
            evaluate(j=junit(cases=failed_cases, failures=1))

    def test_inflated_junit_header_fails_closed(self):
        out = evaluate(j=junit(tests=30))
        self.assertEqual(out["status"], "HOLD")
        self.assertEqual(out["junit_test_cases_observed"], 2)
        self.assertEqual(out["junit_test_cases_declared"], 30)

    def test_cross_sha_and_branch_instrumentation_rejected(self):
        for part in ("coverage_sha", "test_sha", "branch_false", "missing_target"):
            with self.subTest(part=part):
                c = coverage()
                cov_head = HEAD
                test_head = HEAD
                if part == "coverage_sha":
                    cov_head = "e" * 40
                elif part == "test_sha":
                    test_head = "e" * 40
                elif part == "branch_false":
                    c["meta"]["branch_coverage"] = False
                else:
                    c["files"].pop(B)
                with self.assertRaises(ValueError):
                    evaluate(c=c, coverage_head=cov_head, test_head=test_head)


if __name__ == "__main__":
    unittest.main()
