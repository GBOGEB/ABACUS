"""Negative and deterministic tests for the LDAB telemetry claim boundaries."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "mip_ldab_telemetry.py"
SPEC = importlib.util.spec_from_file_location("mip_ldab_telemetry", SOURCE)
telemetry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telemetry)

SHA = "a" * 40
CHECKSUM = "b" * 64
LANE = "repo_self_assess_debug_ldab"


def root(count=3, paths=None):
    if paths is None:
        paths = ["scripts/mip_repo_self_index.py", "docs/debug.md"]
    return {
        "repo": {"sha": SHA},
        "assessments": {
            LANE: {
                "status": "green" if count else "red",
                "signals": count,
                "sample_paths": paths,
            }
        },
    }


def nested(count=1, paths=None):
    if paths is None:
        paths = ["tests/test_smoke_federation.py"]
    return {
        "surface": {
            "path": "integration/codespace_jyperter",
            "parent_sha": SHA,
        },
        "assessments": {
            LANE: {
                "status": "green" if count else "red",
                "signals": count,
                "sample_paths": paths,
            }
        },
    }


def diagnostic():
    return {
        "repository": "GBOGEB/ABACUS",
        "diagnostic": "nested_debug_ldab",
        "parent_sha": SHA,
        "source_contract":
            "integration/codespace_jyperter/tests/test_smoke_federation.py",
        "source_contract_sha256": CHECKSUM,
        "verification": "PASS",
        "checks": {"contract": True, "assimilate": True, "manifest": True},
        "failed_checks": [],
    }


class LDABTelemetryTests(unittest.TestCase):
    def test_enumerates_source_signals_without_runtime_claims(self):
        result = telemetry.summarize(root(), nested(), diagnostic(), SHA)
        self.assertEqual(result["schema"], "mip.ldab.telemetry.v1")
        self.assertEqual(result["source_census"]["root"]["candidate_file_count"], 3)
        self.assertEqual(result["source_census"]["root"]["sample_count"], 2)
        self.assertTrue(result["source_census"]["root"]["sample_truncated"])
        self.assertEqual(result["source_census"]["nested"]["candidate_file_count"], 1)
        self.assertIsNone(result["source_census"]["combined_candidates"])
        self.assertFalse(result["source_census"]["combined_is_disjoint"])
        self.assertEqual(result["diagnostic_execution"]["contract_checks_total"], 3)
        self.assertEqual(result["diagnostic_execution"]["state"], "EXECUTED_PASS")
        self.assertEqual(result["diagnostic_execution"]["diagnostic_scope"],
                         "FEDERATION_CONTRACT_ONLY")
        self.assertIsNone(result["runtime"]["abacus_native_debug_sessions"])
        self.assertIsNone(result["runtime"]["authenticated_port_leases"])
        self.assertIsNone(result["runtime"]["ldab_verified_repairs"])
        self.assertEqual(result["runtime"]["proof_state"],
                         "UNKNOWN_NO_RUNTIME_RECEIPT")
        self.assertFalse(result["authority_transfer"])
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_root_source_only_is_not_executed_debugger(self):
        data = telemetry.summarize(root(), None, None, SHA)
        self.assertEqual(data["diagnostic_execution"]["state"], "NOT_EXECUTED")
        self.assertIsNone(data["diagnostic_execution"]["contract_checks_passed"])
        self.assertEqual(data["claims"]["native_lldb_dap"], "UNKNOWN")

    def test_zero_source_files_is_zero_not_missing_runtime(self):
        data = telemetry.summarize(root(count=0, paths=[]), None, None, SHA)
        self.assertEqual(data["source_census"]["root"]["candidate_file_count"], 0)
        self.assertIsNone(data["runtime"]["abacus_native_debug_sessions"])

    def test_repeat_output_is_byte_identical_without_mutating_input(self):
        a, b, c = root(), nested(), diagnostic()
        originals = copy.deepcopy((a, b, c))
        first = telemetry.stable_json(telemetry.summarize(a, b, c, SHA))
        second = telemetry.stable_json(telemetry.summarize(a, b, c, SHA))
        self.assertEqual(first.encode(), second.encode())
        self.assertEqual((a, b, c), originals)
        self.assertEqual(json.loads(first)["repository"], "GBOGEB/ABACUS")

    def test_rejects_stale_root_sha(self):
        a = root()
        a["repo"]["sha"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "root source SHA mismatch"):
            telemetry.summarize(a, None, None, SHA)

    def test_rejects_stale_nested_sha(self):
        b = nested()
        b["surface"]["parent_sha"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "nested source identity"):
            telemetry.summarize(root(), b, diagnostic(), SHA)

    def test_rejects_nonhex_expected_sha(self):
        with self.assertRaises(ValueError):
            telemetry.summarize(root(), None, None, "not-a-full-sha")

    def test_rejects_missing_diagnostic_if_nested_present(self):
        with self.assertRaisesRegex(ValueError, "diagnostic missing"):
            telemetry.summarize(root(), nested(), None, SHA)

    def test_rejects_orphan_diagnostic(self):
        with self.assertRaisesRegex(ValueError, "orphan"):
            telemetry.summarize(root(), None, diagnostic(), SHA)

    def test_rejects_failed_diagnostic_and_false_green(self):
        d = diagnostic()
        d["checks"]["assimilate"] = False
        d["verification"] = "FAIL"
        d["failed_checks"] = ["assimilate"]
        with self.assertRaisesRegex(ValueError, "diagnostic failed"):
            telemetry.summarize(root(), nested(), d, SHA)

    def test_rejects_unproven_pass_with_empty_checks(self):
        d = diagnostic()
        d["checks"] = {}
        with self.assertRaisesRegex(ValueError, "denominator invalid"):
            telemetry.summarize(root(), nested(), d, SHA)

    def test_rejects_contract_digest_or_identity_mismatch(self):
        d = diagnostic()
        d["source_contract_sha256"] = "unavailable"
        with self.assertRaisesRegex(ValueError, "contract mismatch"):
            telemetry.summarize(root(), nested(), d, SHA)

    def test_rejects_denominator_underflow(self):
        with self.assertRaisesRegex(ValueError, "denominator invalid"):
            telemetry.summarize(root(count=1), None, None, SHA)

    def test_rejects_duplicate_debug_source_paths(self):
        with self.assertRaisesRegex(ValueError, "sample conflicts"):
            telemetry.summarize(root(count=2, paths=["src/debug.py", "src/debug.py"]),
                                None, None, SHA)

    def test_rejects_status_derived_from_file_presence_mismatch(self):
        a = root()
        a["assessments"][LANE]["status"] = "red"
        with self.assertRaisesRegex(ValueError, "source status mismatch"):
            telemetry.summarize(a, None, None, SHA)

    def test_root_status_follows_kit_diagnostic_not_file_presence(self):
        signals_only = root()
        signals_only["assessments"][LANE]["status"] = "amber"
        census = telemetry.summarize(signals_only, None, None, SHA)
        self.assertEqual(
            census["source_census"]["root"]["producer_assessment"], "AMBER"
        )
        proven_without_signals = root(count=0, paths=[])
        proven_without_signals["assessments"][LANE]["status"] = "green"
        telemetry.summarize(proven_without_signals, None, None, SHA)

    def test_nested_status_still_derives_from_file_presence(self):
        n = nested()
        n["assessments"][LANE]["status"] = "amber"
        with self.assertRaisesRegex(ValueError, "nested LDAB source status mismatch"):
            telemetry.summarize(root(), n, diagnostic(), SHA)

    def test_rejects_nonboolean_checks(self):
        d = diagnostic()
        d["checks"]["assimilate"] = 1
        with self.assertRaisesRegex(ValueError, "denominator invalid"):
            telemetry.summarize(root(), nested(), d, SHA)

    def test_rejects_invalid_repository(self):
        with self.assertRaisesRegex(ValueError, "repository identity"):
            telemetry.summarize(root(), None, None, SHA, "GBOGEB/CODEX")

    def test_full_inventory_classifies_debug_logs_and_incidental(self):
        paths = ["DOW_LOGS/latest.json", "scripts/debug.py",
                 "tools/build_catalog.py"]
        a = root(count=3, paths=paths)
        a["assessments"][LANE]["all_candidate_paths"] = paths
        report = telemetry.summarize(a, None, None, SHA)
        scope = report["source_census"]["root"]
        self.assertTrue(scope["inventory_complete"])
        self.assertEqual(scope["source_taxonomy"], "ldab.lexical.v1")
        self.assertEqual(scope["source_class_counts"], {
            "explicit_debug": 1,
            "telemetry_logs_trace": 1,
            "lexical_incidental": 1,
        })
        self.assertEqual(len(scope["full_source_inventory"]), 3)

    def test_broad_substrings_are_not_real_debuggers(self):
        classify = telemetry._candidate_class
        self.assertEqual(classify("runtime/adaptive-governance.yaml"),
                         "lexical_incidental")
        self.assertEqual(classify("tools/build_catalog.py"),
                         "lexical_incidental")
        self.assertEqual(classify("src/semantic-topology.py"),
                         "lexical_incidental")
        self.assertEqual(classify("scripts/lldb_dap_probe.py"),
                         "explicit_debug")

    def test_full_inventory_must_reconcile_denominator(self):
        a = root(count=3)
        a["assessments"][LANE]["all_candidate_paths"] = ["scripts/debug.py"]
        with self.assertRaisesRegex(ValueError, "denominator mismatch"):
            telemetry.summarize(a, None, None, SHA)

    def test_full_inventory_must_be_sorted_unique_and_match_sample(self):
        a = root(count=2, paths=["docs/debug.md", "scripts/debug.py"])
        a["assessments"][LANE]["all_candidate_paths"] = [
            "scripts/debug.py", "docs/debug.md"
        ]
        with self.assertRaisesRegex(ValueError, "order/sample mismatch"):
            telemetry.summarize(a, None, None, SHA)

    def test_nested_full_inventory_is_not_added_to_root(self):
        a = root(count=1, paths=["scripts/debug.py"])
        a["assessments"][LANE]["all_candidate_paths"] = ["scripts/debug.py"]
        b = nested(
            count=1, paths=["scripts/mip_debug_diagnostic.py"]
        )
        b["assessments"][LANE]["all_candidate_paths"] = [
            "scripts/mip_debug_diagnostic.py"
        ]
        result = telemetry.summarize(a, b, diagnostic(), SHA)
        self.assertTrue(result["source_census"]["nested"]["inventory_complete"])
        self.assertIsNone(result["source_census"]["combined_candidates"])

    def test_rejects_unknown_execution_origin(self):
        d = diagnostic()
        d["parent_sha"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "contract mismatch"):
            telemetry.summarize(root(), nested(), d, SHA)


forbidden_paths = (
    "", ".", "./", "././", "../secrets", "/tmp/port",
    "src/../secret", "src//debug.py", "C:\\\\temp\\\\debug.json",
)


def _add_invalid_path_case(path, index):
    def test_method(self):
        with self.assertRaises(ValueError):
            telemetry.summarize(root(count=1, paths=[path]), None, None, SHA)
    setattr(LDABTelemetryTests, f"test_invalid_path_{index:02d}", test_method)


for i, path in enumerate(forbidden_paths):
    _add_invalid_path_case(path, i)


if __name__ == "__main__":
    unittest.main()
