"""Deterministic negative, reverse, and force-trip controls for native MCL test telemetry.

The tests run in unittest and cannot authenticate GitHub receipts by themselves.
"""
from __future__ import annotations

import json
import unittest

from mission_control_lite.test_family_telemetry import FAMILIES, audit_native_family_log

SHA = "a" * 40
OTHER = "b" * 40


def cases(count=4):
    return [f"test_{family}_case_{n}" for family in FAMILIES for n in range(count)]


def log_for(methods=None):
    methods = cases() if methods is None else list(methods)
    output = "".join(
        f"{name} (test_mcl_adversarial_family.FamilyTests.{name}) ... ok\n"
        for name in methods
    )
    return output + f"\nRan {len(methods)} tests in 0.023s\n\nOK\n"


def sample():
    return audit_native_family_log(log_for(), SHA, 42)


class FamilyTests(unittest.TestCase):
    def test_positive_complete_native_family_census(self):
        result = sample()
        self.assertEqual(result["native_case_executions"], 16)
        self.assertEqual(result["unique_case_ids"], 16)
        self.assertEqual(result["families_represented"], 4)

    def test_positive_all_family_denominators_are_explicit(self):
        self.assertEqual(sample()["case_counts_by_family"], dict.fromkeys(FAMILIES, 4))

    def test_positive_order_invariant_canonical_case_hash(self):
        base = audit_native_family_log(log_for(cases()), SHA, 42)
        reversed_log = audit_native_family_log(log_for(reversed(cases())), SHA, 42)
        self.assertEqual(base["case_identity_sha256"], reversed_log["case_identity_sha256"])

    def test_positive_nonadmitting_and_noncalibrated_metrics(self):
        result = sample()
        self.assertEqual(result["merge_admission"], "HOLD")
        self.assertEqual(result["verified_root_closures"], 0)
        for field in ("field_false_positive_rate", "field_false_negative_rate",
                      "fault_injection_detection_rate"):
            self.assertIsNone(result[field])

    def test_positive_preserves_source_and_run_provenance(self):
        value = audit_native_family_log(log_for(), OTHER, 139)
        self.assertEqual((value["source_sha"], value["run_id"]), (OTHER, 139))

    def test_positive_nonzero_minimum_still_has_fixed_four_family_population(self):
        value = audit_native_family_log(log_for(), SHA, 42, min_per_family=1)
        self.assertEqual(value["family_presence_percent"], 100.0)
        self.assertEqual(value["minimum_per_family"], 1)

    def test_negative_missing_passing_summary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "passing unittest summary"):
            audit_native_family_log(log_for().replace("\nOK\n", "\nFAILED\n"), SHA, 42)

    def test_negative_partial_case_execution_is_rejected(self):
        partial = log_for().replace("Ran 16 tests", "Ran 17 tests")
        with self.assertRaisesRegex(ValueError, "case identity or status"):
            audit_native_family_log(partial, SHA, 42)

    def test_negative_duplicate_case_identity_is_rejected(self):
        methods = cases() + [cases()[0]]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit_native_family_log(log_for(methods), SHA, 42)

    def test_negative_unknown_type_is_rejected(self):
        methods = cases()
        methods[0] = "test_excluded_case_0"
        with self.assertRaisesRegex(ValueError, "unclassified"):
            audit_native_family_log(log_for(methods), SHA, 42)

    def test_negative_missing_family_rejected(self):
        methods = [x for x in cases() if "_force_trip_" not in x]
        with self.assertRaisesRegex(ValueError, "underrepresented"):
            audit_native_family_log(log_for(methods), SHA, 42)

    def test_negative_false_source_sha_rejected(self):
        for invalid in ("f" * 39, "G" * 40, True, None):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "source SHA"):
                audit_native_family_log(log_for(), invalid, 42)

    def test_negative_bad_run_identity_rejected(self):
        for bad in (0, -1, True, "42", None):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "run ID"):
                audit_native_family_log(log_for(), SHA, bad)

    def test_negative_malformed_log_length_rejected(self):
        with self.assertRaisesRegex(ValueError, "native test log"):
            audit_native_family_log("x" * 2_000_001, SHA, 42)

    def test_reverse_case_order_does_not_fabricate_coverage_uplift(self):
        ordered = sample()
        reversed_item = audit_native_family_log(log_for(reversed(cases())), SHA, 42)
        self.assertEqual(ordered["case_counts_by_family"], reversed_item["case_counts_by_family"])
        self.assertEqual(ordered["case_identity_sha256"], reversed_item["case_identity_sha256"])

    def test_reverse_valid_source_change_preserves_case_census_not_admission(self):
        a = sample()
        b = audit_native_family_log(log_for(), OTHER, 42)
        self.assertEqual(a["case_identity_sha256"], b["case_identity_sha256"])
        self.assertNotEqual(a["source_sha"], b["source_sha"])
        self.assertEqual(b["merge_admission"], "HOLD")

    def test_reverse_family_relabel_changes_cases_but_not_unique_execution_count(self):
        methods = cases()
        methods[0] = "test_negative_case_extra"
        methods[4] = "test_positive_case_extra"
        result = audit_native_family_log(log_for(methods), SHA, 42)
        self.assertEqual(result["native_case_executions"], 16)
        self.assertNotEqual(result["case_identity_sha256"], sample()["case_identity_sha256"])

    def test_reverse_dropped_negative_family_is_not_promoted(self):
        methods = [x for x in cases() if "_negative_" not in x]
        with self.assertRaisesRegex(ValueError, "underrepresented"):
            audit_native_family_log(log_for(methods), SHA, 42)

    def test_reverse_nonpassing_case_prevents_false_green(self):
        broken = log_for().replace("... ok\n", "... FAIL\n", 1)
        with self.assertRaisesRegex(ValueError, "case identity or status"):
            audit_native_family_log(broken, SHA, 42)

    def test_reverse_family_minimum_cannot_be_boolean(self):
        with self.assertRaisesRegex(ValueError, "minimum"):
            audit_native_family_log(log_for(), SHA, 42, min_per_family=True)

    def test_force_trip_forged_extra_ok_summary_is_rejected(self):
        forged = log_for() + "Ran 16 tests in 0.012s\n\nOK\n"
        with self.assertRaisesRegex(ValueError, "unique passing"):
            audit_native_family_log(forged, SHA, 42)

    def test_force_trip_method_identity_swap_fails_closed(self):
        bad = log_for().replace(
            "(test_mcl_adversarial_family.FamilyTests.test_positive_case_0)",
            "(test_mcl_adversarial_family.FamilyTests.test_negative_case_0)", 1)
        with self.assertRaisesRegex(ValueError, "method/qualified"):
            audit_native_family_log(bad, SHA, 42)

    def test_force_trip_status_error_in_native_case_detected(self):
        bad = log_for().replace("... ok\n", "... ERROR\n", 1)
        with self.assertRaisesRegex(ValueError, "case identity or status"):
            audit_native_family_log(bad, SHA, 42)

    def test_force_trip_unknown_provenance_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, "source SHA"):
            audit_native_family_log(log_for(), "synthetic-merge-SHA", 42)

    def test_force_trip_missing_positive_control_detected(self):
        methods = [x for x in cases() if "_positive_" not in x]
        with self.assertRaisesRegex(ValueError, "underrepresented"):
            audit_native_family_log(log_for(methods), SHA, 42)

    def test_force_trip_replayed_case_in_same_run_detected(self):
        methods = cases() + ["test_force_trip_case_0"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit_native_family_log(log_for(methods), SHA, 42)

    def test_force_trip_oversized_log_not_accepted(self):
        bad = log_for() + "x" * 2_000_000
        with self.assertRaisesRegex(ValueError, "native test log"):
            audit_native_family_log(bad, SHA, 42)

    def test_force_trip_hidden_error_banner_cannot_be_green(self):
        corrupted = log_for() + "ERROR: malicious failure masking\n"
        with self.assertRaisesRegex(ValueError, "failed native unittest status"):
            audit_native_family_log(corrupted, SHA, 42)

    def test_force_trip_empty_native_population_not_accepted(self):
        with self.assertRaises(ValueError):
            audit_native_family_log("Ran 0 tests in 0.01s\n\nOK\n", SHA, 42)


if __name__ == "__main__":
    unittest.main()
