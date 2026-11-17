"""W72 case-level temporal signal quality and strict scope matching controls."""

from __future__ import annotations

import unittest

from tools.w72_testcase_telemetry import compare, parse_junit


def doc(*cases):
    items = []
    for cls, name, state, time in cases:
        outcome = {
            "failed": "<failure/>",
            "error": "<error/>",
            "skipped": '<skipped message="env precondition"/>',
            "passed": "",
        }[state]
        items.append(
            f'<testcase classname="{cls}" name="{name}" time="{time}">{outcome}</testcase>'
        )
    return (
        '<testsuite tests="' + str(len(cases)) + '">' + "".join(items) + "</testsuite>"
    ).encode()


class W72TemporalControls(unittest.TestCase):
    def test_green_collection_true_denominator(self):
        result = parse_junit(
            doc(("A", "one", "passed", "0.1"), ("B", "two", "skipped", "0"))
        )
        self.assertEqual(
            result["counts"],
            {"collected": 2, "passed": 1, "failed": 0, "errors": 0, "skipped": 1},
        )
        self.assertEqual(result["duration_observations"], 2)
        self.assertEqual(result["duration_p95_s"], 0.1)
        self.assertFalse(result["skip_owner_classified"])

    def test_case_recovery_is_not_root_closure(self):
        b = parse_junit(doc(("A", "one", "failed", "1"), ("A", "two", "passed", "1")))
        a = parse_junit(doc(("A", "one", "passed", "1"), ("A", "two", "passed", "1")))
        r = compare(b, a)
        self.assertEqual(r["recovered_cases"], 1)
        self.assertEqual(r["regressed_cases"], 0)
        self.assertTrue(r["population_scope_matched"])
        self.assertIsNone(r["root_closures"])

    def test_regression_is_attributed_by_case_id(self):
        b = parse_junit(doc(("A", "one", "passed", "1")))
        a = parse_junit(doc(("A", "one", "error", "1")))
        self.assertEqual(compare(b, a)["regressed_case_ids"], ["A::one"])

    def test_new_and_removed_avoid_false_comparable_delta(self):
        b = parse_junit(doc(("A", "old", "passed", "1")))
        a = parse_junit(doc(("A", "new", "passed", "1")))
        r = compare(b, a)
        self.assertFalse(r["population_scope_matched"])
        self.assertEqual((r["added_cases"], r["missing_cases"]), (1, 1))

    def test_unsorted_xml_stable_case_fingerprint(self):
        a = parse_junit(
            doc(("Z", "last", "passed", "1"), ("A", "first", "passed", "1"))
        )
        b = parse_junit(
            doc(("A", "first", "passed", "1"), ("Z", "last", "passed", "1"))
        )
        self.assertEqual(a["case_identity_fingerprint"], b["case_identity_fingerprint"])

    def test_real_pytest_xml_header_allowed(self):
        x = b'<?xml version="1.0" encoding="utf-8"?><testsuite tests="1"><testcase classname="a" name="x"/></testsuite>'
        self.assertEqual(parse_junit(x)["counts"]["passed"], 1)

    def test_doctype_xml_refused(self):
        p = b'<!DOCTYPE testsuite [<!ENTITY ext SYSTEM "file:///etc/passwd">]><testsuite tests="1"><testcase name="x"/></testsuite>'
        with self.assertRaises(ValueError):
            parse_junit(p)

    def test_pis_not_xml_refused(self):
        p = b'<?proc data?><testsuite tests="1"><testcase name="x"/></testsuite>'
        with self.assertRaises(ValueError):
            parse_junit(p)

    def test_malformed_xml_refused(self):
        with self.assertRaises(ValueError):
            parse_junit(b"<testsuite>")

    def test_duplicate_cases_refused(self):
        with self.assertRaises(ValueError):
            parse_junit(doc(("A", "one", "passed", "0"), ("A", "one", "passed", "0")))

    def test_declared_count_wrong_refused(self):
        with self.assertRaises(ValueError):
            parse_junit(
                b'<testsuite tests="30"><testcase classname="a" name="x"/></testsuite>'
            )

    def test_empty_collection_refused(self):
        with self.assertRaises(ValueError):
            parse_junit(b'<testsuite tests="0"/>')

    def test_multiple_terminal_markers_refused(self):
        with self.assertRaises(ValueError):
            parse_junit(
                b'<testsuite tests="1"><testcase name="x"><skipped/><failure/></testcase></testsuite>'
            )

    def test_negative_and_nonfinite_duration_refused(self):
        for bad in ("-1", "nan", "inf", "xyz"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_junit(doc(("A", "x", "passed", bad)))

    def test_missing_duration_unknown(self):
        r = parse_junit(
            b'<testsuite tests="1"><testcase classname="a" name="x"/></testsuite>'
        )
        self.assertIsNone(r["duration_p95_s"])
        self.assertEqual(r["duration_observations"], 0)

    def test_too_long_case_id_refused(self):
        with self.assertRaises(ValueError):
            parse_junit(doc(("A", "x" * 810, "passed", "0")))

    def test_unknown_schema_does_not_compare(self):
        a = parse_junit(doc(("A", "x", "passed", "0")))
        a["schema"] = "bogus"
        with self.assertRaises(ValueError):
            compare(a, parse_junit(doc(("A", "x", "passed", "0"))))

    def test_malformed_comparison_duplicate_rejected(self):
        a = parse_junit(doc(("A", "x", "passed", "0")))
        a["cases"].append(a["cases"][0])
        a["counts"]["collected"] += 1
        with self.assertRaises(ValueError):
            compare(a, a)

    def test_skips_not_credited_as_passes(self):
        r = parse_junit(doc(("A", "x", "skipped", "0")))
        self.assertEqual(r["counts"]["passed"], 0)
        self.assertFalse(r["skip_owner_classified"])

    def test_no_forged_independence(self):
        x = parse_junit(doc(("A", "x", "passed", "1")))
        self.assertIsNone(compare(x, x)["independent_trials"])


if __name__ == "__main__":
    unittest.main()
