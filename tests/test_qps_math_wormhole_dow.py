"""ABACUS/DOW independent synthetic gg_MATH wormhole observation tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "runtime/federation/qps_math_wormhole_dow.py"
spec = importlib.util.spec_from_file_location("qps_math_wormhole_dow", P)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = "a" * 40
ARTIFACT = hashlib.sha256(b"public synthetic math method card\n").hexdigest()


def synthetic():
    body = {
        "schema": "gg-math-qps-wormhole/v1",
        "route_id": "QPS-MATH-P4-3P3-V1",
        "route": ["GBOGEB/gg_MATH", "GBOGEB/CODEX", "GBOGEB/ABACUS", "GBOGEB/cryoplant-project"],
        "producer": {"repo": "GBOGEB/gg_MATH", "source_sha": SHA,
                     "artifact_path": "research/MATH_METHOD_DEPENDENCY_GRAPH_v1.yaml",
                     "artifact_sha256": ARTIFACT},
        "method": {"id": "M04_PCA", "population_id": "SYNTHETIC_PCA_REFERENCE",
                   "data_class": "SYNTHETIC_REFERENCE", "threshold_authority": "QPS_ONLY",
                   "observed_pairwise_fitted": False},
        "lineage": {"wave": "W259", "pulse": "P4", "qps_child_state": "UNKNOWN"},
        "execution": {"state": "PROPOSED_UNVERIFIED", "run_id": None,
                      "job_id": None, "positive_steps": None},
        "authority": {"authority_transfer": False, "formal_credit_delta": 0,
                      "engineering_acceptance": False,
                      "hard_gate_compensation_allowed": False, "release_credit": False},
        "completed_hops": [],
    }
    return {**body, "receipt_sha256": mod.sha256_json(body)}


def reseal(item):
    item["receipt_sha256"] = mod.sha256_json({
        k: v for k, v in item.items() if k != "receipt_sha256"
    })
    return item


class WormholeDOWTests(TestCase):
    def test_valid_envelope_is_proposal_only(self):
        observation = mod.observe(synthetic(), expected_sha=SHA,
                                  expected_artifact_digest=ARTIFACT)
        self.assertEqual("VALID_PROPOSAL_ONLY", observation["status"])
        self.assertEqual(1, observation["measurement"]["contract_valid"])
        self.assertEqual(0, observation["measurement"]["runtime_authenticated"])
        self.assertEqual(0, observation["measurement"]["qps_dispositions"])
        self.assertFalse(observation["qps_acceptance"])

    def test_cross_repo_sha_binding_fail_closed(self):
        receipt = mod.observe(synthetic(), expected_sha="b"*40,
                              expected_artifact_digest=ARTIFACT)
        self.assertEqual("DEFER_INVALID_CONTRACT", receipt["status"])
        self.assertIn("EXACT_PROVIDER_SHA_DIFFERENCE",
                      [r["cause"] for r in receipt["roots"]])

    def test_artifact_digest_binding_fail_closed(self):
        receipt = mod.observe(synthetic(), expected_sha=SHA,
                              expected_artifact_digest="0"*64)
        self.assertIn("ARTIFACT_DIGEST_DIFFERENCE",
                      [r["cause"] for r in receipt["roots"]])

    def test_tampering_is_not_skipped(self):
        value = synthetic()
        value["method"]["id"] = "M08_BRADLEY_TERRY"
        receipt = mod.observe(value, expected_sha=SHA,
                              expected_artifact_digest=ARTIFACT)
        self.assertIn("RECEIPT_DIGEST_MISMATCH",
                      [r["cause"] for r in receipt["roots"]])

    def test_private_field_rejected(self):
        value = synthetic()
        value["private_payload"] = "not for parent"
        receipt = mod.observe(reseal(value), expected_sha=SHA,
                              expected_artifact_digest=ARTIFACT)
        self.assertEqual(["UNEXPECTED_FIELDS_OR_PRIVATE_DATA"],
                         [r["cause"] for r in receipt["roots"]])

    def test_unverified_hop_must_not_become_execution(self):
        value = synthetic()
        value["completed_hops"] = [{"repo": "GBOGEB/CODEX", "state": "PASS"}]
        receipt = mod.observe(reseal(value), expected_sha=SHA,
                              expected_artifact_digest=ARTIFACT)
        self.assertIn("INVALID_P4_ROUTE_OR_FAKE_HOP",
                      [r["cause"] for r in receipt["roots"]])

    def test_math_does_not_generate_observed_bt(self):
        value = synthetic()
        value["method"]["observed_pairwise_fitted"] = True
        receipt = mod.observe(reseal(value), expected_sha=SHA,
                              expected_artifact_digest=ARTIFACT)
        self.assertIn("METHOD_AUTHORITY_OR_BT_INVALID",
                      [r["cause"] for r in receipt["roots"]])

    def test_non_authoritative_metric_stays_non_authoritative(self):
        value = synthetic()
        value["authority"]["formal_credit_delta"] = 10
        receipt = mod.observe(reseal(value), expected_sha=SHA,
                              expected_artifact_digest=ARTIFACT)
        self.assertIn("AUTHORITY_INVERSION", [r["cause"] for r in receipt["roots"]])
        self.assertEqual(0, receipt["formal_credit_delta"])

    def test_deterministic_roots_and_digest(self):
        value = synthetic()
        value["producer"]["source_sha"] = "c"*40
        a = mod.observe(reseal(value), expected_sha=SHA,
                        expected_artifact_digest=ARTIFACT)
        b = mod.observe(reseal(value), expected_sha=SHA,
                        expected_artifact_digest=ARTIFACT)
        self.assertEqual(a, b)
        self.assertEqual(len(a["roots"]), len({r["fingerprint"] for r in a["roots"]}))
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])

    def test_missing_envelope_is_deferred_not_zero(self):
        a = mod.observe(None, expected_sha=SHA, expected_artifact_digest=ARTIFACT)
        self.assertEqual(1, a["measurement"]["received"])
        self.assertEqual(1, a["measurement"]["invalid"])
        self.assertEqual("DEFER_INVALID_CONTRACT", a["status"])


    def test_native_provider_proposal_source_bound_but_unverified(self):
        fixture = ROOT / "tests/fixtures/qps_math_wormhole_provider_v1.json"
        provider = json.loads(fixture.read_text(encoding="utf-8"))
        sha = "2f84623180bafbd582f90febb542381ed9ce679e"
        artifact = "114e9fa0ded6adc8d1020bef1826c45bb63417a851efac9f2ed35aef7e501759"
        evidence = mod.observe(provider, expected_sha=sha,
                               expected_artifact_digest=artifact)
        self.assertEqual("VALID_PROPOSAL_ONLY", evidence["status"])
        self.assertEqual(0, evidence["measurement"]["runtime_authenticated"])
        self.assertFalse(evidence["qps_acceptance"])
