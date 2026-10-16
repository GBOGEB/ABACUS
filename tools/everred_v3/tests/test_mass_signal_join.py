"""Negative and positive root-candidate tests without scanner suppression."""

from __future__ import annotations

import copy
import json
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mass_signal_join as mod  # noqa: E402

SHA = "a" * 40
DIG = "b" * 64


def source(scanner, rule=None, *, mode="detailed", run=10):
    item = {
        "scanner": scanner,
        "repository": "GBOGEB/ABACUS",
        "head_sha": SHA,
        "run_id": run,
        "attempt": 1,
        "job_id": run + 1,
        "artifact_sha256": DIG,
        "config_sha256": DIG,
        "mode": mode,
        "enforcement": {
            "continue_on_error": scanner == "semgrep",
            "workflow_conclusion": "success",
            "required_check": None,
        },
    }
    if mode == "detailed":
        item["findings"] = [{"rule_id": rule, "path": "src/process.py", "line": 12}]
    else:
        item["counts"] = {"E501": 3, "F401": 1}
        item["total"] = 4
    return item


def payload():
    return {
        "schema": mod.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "head_sha": SHA,
        "sources": [
            source("bandit", "B602", run=10),
            source("ruff", "S607", run=20),
            source("semgrep", "python.command-injection", run=30),
            source("flake8", mode="aggregate", run=40),
        ],
    }


class CrossScannerTests(unittest.TestCase):
    def test_one_candidate_not_three_confirmed_roots(self):
        report = mod.normalize(payload())
        self.assertEqual(1, report["candidate_count"])
        self.assertEqual(
            ["bandit", "ruff", "semgrep"],
            report["cross_scanner_candidates"][0]["scanners"],
        )
        self.assertEqual(0, report["accepted_root_closures"])
        self.assertIsNone(report["verified_causal_roots"])
        self.assertEqual("DEFER", report["qps_engineering_acceptance"])

    def test_aggregate_is_not_a_fake_fingerprint(self):
        report = mod.normalize(payload())
        self.assertEqual(4, report["scanner_totals"]["flake8"])
        self.assertNotIn("flake8", report["detailed_fingerprint_counts"])
        self.assertEqual(1, report["detailed_fingerprint_counts"]["bandit"])

    def test_advisory_green_does_not_grant_clean_scanner(self):
        report = mod.normalize(payload())
        semgrep = next(x for x in report["enforcement"] if x["scanner"] == "semgrep")
        self.assertTrue(semgrep["continue_on_error"])
        self.assertEqual("success", semgrep["workflow_conclusion"])
        self.assertEqual("UNKNOWN", semgrep["merge_admission"])

    def test_same_scanner_duplicate_occurrence_not_a_new_root(self):
        doc = payload()
        doc["sources"][0]["findings"].append(
            copy.deepcopy(doc["sources"][0]["findings"][0])
        )
        result = mod.normalize(doc)
        self.assertEqual(2, result["scanner_totals"]["bandit"])
        self.assertEqual(1, result["detailed_fingerprint_counts"]["bandit"])
        self.assertEqual(1, result["candidate_count"])

    def test_different_source_sha_never_joins(self):
        doc = payload()
        doc["sources"][2]["head_sha"] = "c" * 40
        with self.assertRaisesRegex(mod.InvalidCensus, "cross-head"):
            mod.normalize(doc)

    def test_duplicate_run_job_not_counted_twice(self):
        doc = payload()
        doc["sources"].append(copy.deepcopy(doc["sources"][0]))
        with self.assertRaisesRegex(mod.InvalidCensus, "duplicate scanner"):
            mod.normalize(doc)


    def test_repeated_artifact_on_new_run_is_rejected(self):
        doc = payload()
        repeated = copy.deepcopy(doc["sources"][0])
        repeated["run_id"] = 1001
        repeated["job_id"] = 1002
        doc["sources"].append(repeated)
        with self.assertRaisesRegex(mod.InvalidCensus, "duplicate scanner artifact"):
            mod.normalize(doc)

    def test_noncanonical_repository_identities_rejected(self):
        for repository in ("GBOGEB/", "GBOGEB/.", "GBOGEB/..",
                           "GBOGEB/foo/bar", "GBOGEB/foo bar"):
            with self.subTest(repository=repository):
                doc = payload()
                doc["repository"] = repository
                for item in doc["sources"]:
                    item["repository"] = repository
                with self.assertRaisesRegex(mod.InvalidCensus, "repository identity"):
                    mod.normalize(doc)

    def test_native_terminal_conclusions_retained_without_promotion(self):
        for conclusion in ("timed_out", "neutral", "skipped", "action_required",
                           "stale", "startup_failure"):
            with self.subTest(conclusion=conclusion):
                doc = payload()
                doc["sources"][0]["enforcement"]["workflow_conclusion"] = conclusion
                result = mod.normalize(doc)
                observed = next(e for e in result["enforcement"]
                                if e["scanner"] == "bandit")
                self.assertEqual(conclusion, observed["workflow_conclusion"])
                self.assertEqual("HOLD", result["merge_admission"])

    def test_input_aliases_rejected_and_evidence_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "evidence.json"
            raw = json.dumps(payload()).encode("utf-8")
            original.write_bytes(raw)
            alias = root / "hardlink.json"
            os.link(original, alias)
            targets = [original, alias]
            symlink = root / "symlink.json"
            try:
                symlink.symlink_to(original)
            except (OSError, NotImplementedError):
                pass
            else:
                targets.append(symlink)
            from unittest.mock import patch

            for destination in targets:
                with self.subTest(destination=destination):
                    with patch.object(sys, "argv",
                                      ["join", "--input", str(original),
                                       "--output", str(destination)]):
                        with self.assertRaisesRegex(
                                mod.InvalidCensus, "output aliases input"):
                            mod.main()
                    self.assertEqual(raw, original.read_bytes())

    def test_invalid_artifact_hash_rejected(self):
        doc = payload()
        doc["sources"][0]["artifact_sha256"] = "zero"
        with self.assertRaises(mod.InvalidCensus):
            mod.normalize(doc)

    def test_boolean_run_number_rejected(self):
        doc = payload()
        doc["sources"][0]["run_id"] = True
        with self.assertRaisesRegex(mod.InvalidCensus, "run/job/attempt"):
            mod.normalize(doc)

    def test_missing_enforcement_never_defaults_to_blocking(self):
        doc = payload()
        doc["sources"][2]["enforcement"] = {}
        with self.assertRaisesRegex(mod.InvalidCensus, "enforcement"):
            mod.normalize(doc)

    def test_aggregate_count_sum_must_match_total(self):
        doc = payload()
        doc["sources"][3]["total"] = 5
        with self.assertRaisesRegex(mod.InvalidCensus, "denominator"):
            mod.normalize(doc)

    def test_aggregate_boolean_count_rejected(self):
        doc = payload()
        doc["sources"][3]["counts"]["F401"] = True
        with self.assertRaises(mod.InvalidCensus):
            mod.normalize(doc)

    def test_aggregate_cannot_claim_raw_locations(self):
        doc = payload()
        doc["sources"][3]["findings"] = []
        with self.assertRaises(mod.InvalidCensus):
            mod.normalize(doc)

    def test_detailed_cannot_claim_second_total(self):
        doc = payload()
        doc["sources"][0]["total"] = 1000
        with self.assertRaises(mod.InvalidCensus):
            mod.normalize(doc)

    def test_path_escape_and_abs_path_rejected(self):
        for path in (
            "../a.py",
            "/tmp/a.py",
            "a/../b.py",
            "C:/secret.py",
            "a\\b.py",
            "a//b.py",
        ):
            with self.subTest(path=path):
                doc = payload()
                doc["sources"][0]["findings"][0]["path"] = path
                with self.assertRaises(mod.InvalidCensus):
                    mod.normalize(doc)

    def test_other_locations_do_not_create_cross_scanner_causality(self):
        doc = payload()
        doc["sources"][1]["findings"][0]["line"] = 14
        doc["sources"][2]["findings"][0]["line"] = 15
        self.assertEqual(0, mod.normalize(doc)["candidate_count"])

    def test_scanner_specific_rules_are_not_joined_as_causal_roots(self):
        doc = payload()
        doc["sources"][0]["findings"][0]["rule_id"] = "B101"
        doc["sources"][1]["findings"][0]["rule_id"] = "F541"
        doc["sources"][2]["findings"][0]["rule_id"] = "python.other"
        self.assertEqual(0, mod.normalize(doc)["candidate_count"])

    def test_cli_source_byte_hash_and_readonly_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "input.json"
            output_path = root / "out" / "census.json"
            input_path.write_text(json.dumps(payload()), encoding="utf-8")
            from unittest.mock import patch

            with patch.object(
                sys,
                "argv",
                ["join", "--input", str(input_path), "--output", str(output_path)],
            ):
                mod.main()
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(64, len(report["input_sha256"]))
            self.assertEqual("HOLD", report["merge_admission"])
            self.assertFalse(report["authority_transfer"])


    def test_additional_cross_scanner_rule_families(self):
        expected = [
            ("ruff", "S110", "ERROR_OBSERVABILITY"),
            ("ruff", "S112", "ERROR_OBSERVABILITY"),
            ("ruff", "S314", "UNSAFE_XML"),
            ("ruff", "S324", "CRYPTOGRAPHIC_INTENT"),
            ("bandit", "B303", "CRYPTOGRAPHIC_INTENT"),
            ("bandit", "B324", "CRYPTOGRAPHIC_INTENT"),
            ("semgrep", "python.unsafe-xml", "UNSAFE_XML"),
            ("codeql", "python.weak-hash", "CRYPTOGRAPHIC_INTENT"),
            ("flake8", "E722", "ERROR_OBSERVABILITY"),
        ]
        for scanner, rule, group in expected:
            with self.subTest(scanner=scanner, rule=rule):
                self.assertEqual(group, mod.family(scanner, rule))

    def test_actual_cli_main_entrypoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "source.json"
            output_path = root / "out" / "census.json"
            input_path.write_text(json.dumps(payload()), encoding="utf-8")
            from unittest.mock import patch

            with patch.object(
                sys,
                "argv",
                ["join", "--input", str(input_path), "--output", str(output_path)],
            ):
                runpy.run_path(str(Path(mod.__file__).resolve()), run_name="__main__")
            receipt = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(SHA, receipt["source_sha"])
            self.assertEqual(0, receipt["accepted_root_closures"])


if __name__ == "__main__":
    unittest.main()
