import hashlib
import importlib.util
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("adapter", ROOT / "tools/mcw_receipt_adapters.py")
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
RSPEC = importlib.util.spec_from_file_location("rollup", ROOT / "tools/mcw_federation_rollup.py")
R = importlib.util.module_from_spec(RSPEC)
RSPEC.loader.exec_module(R)
SHA = "a" * 40


def mcl():
    return {"schema": "mcl.coverage.pulse.v1", "repository": "GBOGEB/ABACUS",
            "source_sha": SHA, "merge_admission": "HOLD",
            "verified_root_closures": 0, "tests_passed": 52,
            "scope_id": "mcl/branch", "comparison": {"status": "UNKNOWN"},
            "totals": {"covered_lines": 8, "num_statements": 10,
                       "covered_branches": 3, "num_branches": 5}}


def ldab():
    return {"schema": "mip.ldab.telemetry.v1", "repository": "GBOGEB/ABACUS",
            "source_sha": SHA, "merge_admission": "HOLD", "authority_transfer": False,
            "security_waiver": False,
            "source_census": {"root": {"candidate_file_count": 104,
                "sample_count": 20, "evidence_level": "SOURCE_DISCOVERY_ONLY",
                "live_runtime_inferred": False},
                "nested": {"candidate_file_count": 12, "sample_count": 12,
                "evidence_level": "SOURCE_DISCOVERY_ONLY", "live_runtime_inferred": False},
                "combined_candidates": None, "combined_is_disjoint": False,
                "candidate_files_are_not_sessions": True},
            "runtime": {"abacus_native_debug_sessions": None,
                        "authenticated_port_leases": None,
                        "active_runner_workers": None, "ldab_verified_repairs": None,
                        "debug_probe_steps": None,
                        "proof_state": "UNKNOWN_NO_RUNTIME_RECEIPT"},
            "diagnostic_execution": {"diagnostic_scope": "FEDERATION_CONTRACT_ONLY",
                                     "diagnostic": "nested_debug_ldab",
                                     "state": "EXECUTED_PASS",
                                     "contract_checks_total": 3,
                                     "contract_checks_passed": 3,
                                     "contract_checks_failed": 0,
                                     "source_contract": (
                                         "integration/codespace_jyperter/"
                                         "tests/test_smoke_federation.py"
                                     ),
                                     "source_contract_sha256": "f" * 64}}


def bd():
    return {"schema": "bd.ldab.joined.census.v1",
            "scope": {"repository": "GBOGEB/ABACUS", "head_sha": SHA},
            "merge_admission": "HOLD", "authority_transfer": False,
            "security_waiver": False, "formal_credit_delta": 0,
            "security_disposition": "INDEPENDENT_REVIEW_REQUIRED",
            "metrics": {"full_bandit_unique": 9, "active_workers": None,
                        "changed_line_coverage": None},
            "roots": [{"root_id": "BD-example", "disposition": "OPEN_UNREVIEWED"}],
            "unlinked_debug_receipts": []}


class ReceiptAdaptersTests(unittest.TestCase):
    def setup_sources(self, root):
        for name, doc in (("mcl.json", mcl()), ("ldab.json", ldab()), ("bd.json", bd())):
            (root / name).write_text(json.dumps(doc))
        return {"MCL": "mcl.json", "LDAB": "ldab.json", "CENSUS": "bd.json"}

    def test_three_source_adapters_no_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            obj = A.build(root, self.setup_sources(root), "GBOGEB/ABACUS", SHA, "W1")
            report = R.rollup(obj, root)
            self.assertEqual(report["counts"]["unverified_source_metric_nodes"], 3)
            self.assertEqual(report["counts"]["local_byte_verified_nodes"], 0)
            self.assertEqual(report["confirmed_root_closures"], 0)
            self.assertEqual(report["merge_admission"], "HOLD")
            lookup = {x["family"]: x for x in report["nodes"]}
            self.assertEqual(lookup["LDAB"]["source_observation"]["metrics"]["root_candidate_files"], 104)
            self.assertIsNone(lookup["LDAB"]["source_observation"]["metrics"]["deduplicated_candidate_files"])
            self.assertEqual(lookup["MCL"]["source_observation"]["metrics"]["line_percent_reported"], 80)
            self.assertIsNone(lookup["MCL"]["source_observation"]["metrics"]["focused_test_denominator"])
            self.assertFalse(lookup["MCL"]["native_gha_authenticated"])

    def test_source_identity_and_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mapping = self.setup_sources(root)
            with self.assertRaises(ValueError):
                A.build(root, {"MCL": "../bad.json"}, "GBOGEB/ABACUS", SHA, "W1")
            with self.assertRaises(ValueError):
                A.build(root, mapping, "GBOGEB/ABACUS", "b" * 40, "W1")
            with self.assertRaises(ValueError):
                A.build(root, mapping, "GBOGEB/ABACUS", SHA, "W 1")

    def test_ldab_nested_is_not_additive_and_runtime_forgery_rejected(self):
        obj = ldab()
        self.assertIsNone(A._ldab(obj)["deduplicated_candidate_files"])
        for value in (0, 5):
            changed = json.loads(json.dumps(obj))
            changed["runtime"]["abacus_native_debug_sessions"] = value
            with self.assertRaises(ValueError):
                A._ldab(changed)
        changed = json.loads(json.dumps(obj))
        changed["source_census"]["combined_candidates"] = 116
        with self.assertRaises(ValueError):
            A._ldab(changed)

    def test_bd_false_closure_and_waiver_rejected(self):
        obj = bd()
        self.assertEqual(A._bd(obj)["root_candidate_groups"], 1)
        changed = json.loads(json.dumps(obj))
        changed["roots"][0]["disposition"] = "VERIFIED_CLOSED"
        with self.assertRaises(ValueError):
            A._bd(changed)
        changed = json.loads(json.dumps(obj))
        changed["security_waiver"] = True
        with self.assertRaises(ValueError):
            A.adapt(changed, "CENSUS", "GBOGEB/ABACUS", SHA, "f" * 64, "W1")

    def test_mcl_numerators_and_guard(self):
        source = mcl()
        self.assertEqual(A._mcl(source)["branch_percent_reported"], 60)
        for value in (-1, 11, True):
            bad = json.loads(json.dumps(source))
            bad["totals"]["covered_lines"] = value
            with self.assertRaises(ValueError):
                A._mcl(bad)
        bad = json.loads(json.dumps(source))
        bad["verified_root_closures"] = 1
        with self.assertRaises(ValueError):
            A._mcl(bad)

    def test_rollup_rejects_claimed_authenticated_observation(self):
        node = {"id": "a", "repository": "GBOGEB/ABACUS", "source_sha": SHA,
                "family": "LDAB", "source_observation": {"schema": "test",
                "local_sha256": "f" * 64, "metrics": {},
                "evidence_grade": "AUTHENTICATED"}}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                R.rollup({"schema": R.INPUT_SCHEMA, "wave_id": "W", "nodes": [node], "edges": []}, d)

    def test_nested_absent_retains_unknown_combined_count(self):
        observation = ldab()
        observation["source_census"]["nested"] = None
        observation["diagnostic_execution"]["state"] = "NOT_EXECUTED"
        result = A._ldab(observation)
        self.assertIsNone(result["nested_candidate_files"])
        self.assertIsNone(result["deduplicated_candidate_files"])

    def test_both_executable_entrypoints(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_sources(root)
            intermediate = root / "input.json"
            final = root / "result.json"
            with patch.object(sys, "argv", [
                "adapter", "--artifact-root", d,
                "--repository", "GBOGEB/ABACUS", "--source-sha", SHA,
                "--wave-id", "W2", "--ldab", "ldab.json",
                "--output", str(intermediate),
            ]):
                runpy.run_path(str(ROOT / "tools/mcw_receipt_adapters.py"),
                               run_name="__main__")
            with patch.object(sys, "argv", [
                "mcw", "--input", str(intermediate),
                "--artifact-root", d, "--output", str(final),
            ]):
                runpy.run_path(str(ROOT / "tools/mcw_federation_rollup.py"),
                               run_name="__main__")
            result = json.loads(final.read_text())
            self.assertEqual(result["counts"]["unverified_source_metric_nodes"], 1)
            self.assertEqual(result["merge_admission"], "HOLD")

    def test_cli_emits_explicit_source_only_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_sources(root)
            with patch.object(sys, "argv", ["adapter", "--artifact-root", d,
                "--repository", "GBOGEB/ABACUS", "--source-sha", SHA,
                "--wave-id", "W1", "--mcl", "mcl.json", "--output", str(root / "out.json")]):
                A.main()
            produced = json.loads((root / "out.json").read_text())
            self.assertEqual(produced["nodes"][0]["family"], "MCL")
            self.assertEqual(produced["producer_trust"], "UNAUTHENTICATED_SOURCE_BYTES_ONLY")
            self.assertEqual(len(produced["edges"]), 0)


    def test_source_schema_family_mapping_is_exact(self):
        self.assertEqual(A.SOURCES, R.SOURCE_OBSERVATION_SCHEMAS)
        for family in ("MCL", "LDAB", "CENSUS"):
            forged = {
                "schema": R.INPUT_SCHEMA, "wave_id": "W1", "edges": [],
                "nodes": [{
                    "id": "foreign", "repository": "GBOGEB/ABACUS",
                    "source_sha": SHA, "family": family,
                    "source_observation": {
                        "schema": "other.contract.v1",
                        "local_sha256": "f" * 64,
                        "evidence_grade": "UNAUTHENTICATED_SOURCE_BYTES",
                        "metrics": {},
                    },
                }],
            }
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError):
                    R.rollup(forged, d)

    def test_ldab_rejects_claimed_waiver_or_runtime_steps(self):
        for change in ("waiver", "debug"):
            obj = ldab()
            if change == "waiver":
                obj["security_waiver"] = True
            else:
                obj["runtime"]["debug_probe_steps"] = 4
            with self.assertRaises(ValueError):
                A._ldab(obj)

    def test_ldab_rejects_forged_executed_contract(self):
        for key, value in (
            ("contract_checks_total", None),
            ("contract_checks_passed", 0),
            ("contract_checks_failed", 1),
            ("source_contract_sha256", "invalid"),
            ("source_contract", "incorrect.py"),
        ):
            obj = ldab()
            obj["diagnostic_execution"][key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    A._ldab(obj)

    def test_ldab_rejects_executed_without_nested_census(self):
        obj = ldab()
        obj["source_census"]["nested"] = None
        with self.assertRaises(ValueError):
            A._ldab(obj)


if __name__ == "__main__":
    unittest.main()
