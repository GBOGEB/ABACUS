"""Live V3.1 integration and negative admission/federation cases."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
sys.path.insert(0, str(BASE / "scripts"))

from four_plane_preflight import execute  # noqa: E402

from federation_bridge import evaluate_exchange, release_candidate  # noqa: E402
from four_planes import (  # noqa: E402
    EvidenceError,
    Source,
    clean_log,
    diagnostic_receipt,
    federated_join,
    ldab_receipt,
    runtime_receipt,
)
from ldab_adapter import consume_bd_ldab  # noqa: E402
from runtime_probe import (  # noqa: E402
    observe_docker_availability,
    observe_host,
    observe_lldb_availability,
    os_identity,
    transient_loopback_probe,
)
from yaml_control import (  # noqa: E402
    evaluate_dispatch,
    load_yaml,
    normalize_yaml,
    semantic_diff,
    validate_federation_policy,
    validate_plan,
)

SHA = "a" * 40
OTHER = "b" * 40
DIG = "c" * 64
SRC = Source("GBOGEB/ABACUS", SHA, 123, 456)
PLAN = load_yaml((BASE / "config/workflow-groups.yaml").read_text())
FED = load_yaml((BASE / "config/federation-bindings.yaml").read_text())


def debug(**kwargs):
    return {
        "tool": "LLDB",
        "session_id": "demo-session",
        "binary_build_id": DIG,
        "verified_step_count": 2,
        "frames": [],
        **kwargs,
    }


def runtime(**kwargs):
    r = {
        "os_family": "macOS",
        "os_release": "Darwin",
        "kernel": "23.0.0",
        "container_runtime": "none",
        "ports": [],
        "runner_id": "demo",
    }
    r.update(kwargs)
    return r


class SourceAndIdentity(unittest.TestCase):
    def test_valid_source(self):
        self.assertEqual(SRC.binding()["job_id"], 456)

    def test_optional_execution_sha(self):
        self.assertEqual(
            Source("GBOGEB/CODEX", SHA, 2, executed_sha=OTHER).executed_sha, OTHER
        )

    def test_source_rejects_malformed_sha(self):
        for x in ("123", "A" * 40, "", None):
            with self.subTest(sha=x), self.assertRaises(EvidenceError):
                Source("GBOGEB/ABACUS", x, 1)

    def test_source_rejects_other_repos(self):
        for x in ("/foo", "repo", "a/b/c", "../x", "a b/c"):
            with self.subTest(repo=x), self.assertRaises(EvidenceError):
                Source(x, SHA, 1)

    def test_bool_ids_not_integer(self):
        with self.assertRaises(EvidenceError):
            Source("GBOGEB/ABACUS", SHA, True)
        with self.assertRaises(EvidenceError):
            Source("GBOGEB/ABACUS", SHA, 1, True)

    def test_no_self_promotion(self):
        with self.assertRaises(EvidenceError):
            diagnostic_receipt(SRC, debug(), trust="EXTERNAL_REVIEWED")

    def test_artifact_digest_invalid(self):
        with self.assertRaises(EvidenceError):
            diagnostic_receipt(SRC, debug(), artifact_sha256="z" * 64)


class Diagnostic(unittest.TestCase):
    def test_native_mac_lldb_needs_no_container(self):
        r = diagnostic_receipt(SRC, debug())
        self.assertEqual(r["plane"], "diagnostic")
        self.assertIsNone(r["data"]["container_id"])
        self.assertFalse(r["merge_authority"])

    def test_dap_supported(self):
        d = debug()
        d["tool"] = "LLDB-DAP"
        self.assertEqual(diagnostic_receipt(SRC, d)["data"]["tool"], "LLDB-DAP")

    def test_step_zero_not_pass(self):
        d = debug()
        d["verified_step_count"] = 0
        self.assertFalse(
            diagnostic_receipt(SRC, d, trust="LOCAL_OBSERVED")["data"][
                "observed_step_evidence"
            ]
        )

    def test_negative_and_bool_steps_rejected(self):
        for bad in (True, -1, 2.5, "10"):
            d = debug()
            d["verified_step_count"] = bad
            with self.subTest(bad=bad), self.assertRaises(EvidenceError):
                diagnostic_receipt(SRC, d)

    def test_declared_steps_are_not_verified(self):
        d = diagnostic_receipt(SRC, debug())
        self.assertIsNone(d["data"]["observed_step_evidence"])

    def test_missing_buildid_rejected(self):
        d = debug()
        del d["binary_build_id"]
        with self.assertRaises(EvidenceError):
            diagnostic_receipt(SRC, d)

    def test_frame_bounds(self):
        d = debug()
        d["frames"] = [{}] * 65
        with self.assertRaises(EvidenceError):
            diagnostic_receipt(SRC, d)

    def test_bad_time(self):
        d = debug()
        d["started_at"] = "2026-01-01T00:00:00"
        with self.assertRaises(EvidenceError):
            diagnostic_receipt(SRC, d)

    def test_root_link_does_not_prove_cause(self):
        r = ldab_receipt(SRC, {"root_id": "R-001", "finding_fingerprint": DIG})
        self.assertEqual(r["causal_disposition"], "UNCLASSIFIED")
        self.assertEqual(r["data"]["disposition"], "HYPOTHESIS")

    def test_ldab_cannot_self_accept(self):
        with self.assertRaises(EvidenceError):
            ldab_receipt(
                SRC,
                {
                    "root_id": "R-001",
                    "finding_fingerprint": DIG,
                    "disposition": "ACCEPT",
                },
            )

    def test_ldab_requires_stable_root(self):
        with self.assertRaises(EvidenceError):
            ldab_receipt(SRC, {"root_id": "..", "finding_fingerprint": DIG})

    def test_ldab_repair_sha(self):
        with self.assertRaises(EvidenceError):
            ldab_receipt(
                SRC,
                {
                    "root_id": "R-001",
                    "finding_fingerprint": DIG,
                    "repair_commit": "oops",
                },
            )


class Runtime(unittest.TestCase):
    def test_os_runtime_is_not_debugger(self):
        r = runtime_receipt(SRC, runtime())
        self.assertEqual(r["plane"], "runtime")
        self.assertEqual(r["data"]["container_runtime"], "none")

    def test_rhel_without_docker(self):
        self.assertEqual(
            runtime_receipt(SRC, runtime(os_family="RHEL9"))["data"]["os_family"],
            "RHEL9",
        )

    def test_container_requires_image(self):
        with self.assertRaises(EvidenceError):
            runtime_receipt(
                SRC, runtime(container_runtime="docker", container_id="123")
            )

    def test_valid_digest_pinned_container(self):
        r = runtime_receipt(
            SRC,
            runtime(
                container_runtime="docker",
                container_id="123",
                image_digest="sha256:" + DIG,
            ),
        )
        self.assertEqual(r["data"]["container_id"], "123")

    def test_no_live_port_without_probe(self):
        with self.assertRaises(EvidenceError):
            runtime_receipt(
                SRC, runtime(ports=[{"port": 8787, "state": "OBSERVED_LISTENING"}])
            )

    def test_port_bool_rejected(self):
        with self.assertRaises(EvidenceError):
            runtime_receipt(SRC, runtime(ports=[{"port": True, "state": "UNKNOWN"}]))

    def test_port_lifecycle_closes(self):
        receipt = transient_loopback_probe()
        self.assertEqual(receipt["state"], "OBSERVED_CLOSED")
        self.assertTrue(receipt["tested_at"])

    def test_actual_os_observation(self):
        o = os_identity()
        self.assertIn(
            o["os_family"],
            ["RHEL8", "RHEL9", "Ubuntu", "Debian", "macOS", "Windows", "OTHER"],
        )
        self.assertIn("kernel", o)

    def test_actual_host_receipt(self):
        r = observe_host(SRC, port_probe=True)
        self.assertEqual(r["plane"], "runtime")
        self.assertEqual(r["data"]["ports"][0]["state"], "OBSERVED_CLOSED")
        self.assertEqual(r["trust"], "LOCAL_OBSERVED")

    def test_actual_docker_discovery_no_deployment(self):
        d = observe_docker_availability()
        self.assertIsNone(d["containers"])
        self.assertEqual(d["daemon"], "UNKNOWN")

    def test_actual_lldb_version_not_session_proof(self):
        d = observe_lldb_availability()
        self.assertIsNone(d["real_step_count"])
        self.assertIn(d["session_status"], ["UNKNOWN", "NOT_EXECUTED"])

    def test_secret_redaction(self):
        r = clean_log("token=SECRET123456 abc ghp_abcdefghijklmnopqrstuvwxyz ABC")
        self.assertNotIn("SECRET123", r["excerpt"])
        self.assertNotIn("ghp_abc", r["excerpt"])
        self.assertTrue(r["redacted"])

    def test_log_truncation(self):
        r = clean_log("x" * 40000)
        self.assertTrue(r["truncated"])
        self.assertLessEqual(len(r["excerpt"].encode()), 32768)


class YamlOrchestration(unittest.TestCase):
    def test_real_plan_eight_tasks(self):
        v = validate_plan(PLAN)
        self.assertEqual(v["task_count"], 8)
        self.assertEqual(v["topological_order"][0], "YAML_PREFLIGHT")

    def test_formatter_roundtrip(self):
        raw = (BASE / "config/workflow-groups.yaml").read_text()
        text, digest = normalize_yaml(raw)
        self.assertFalse(semantic_diff(raw, text)["changed"])
        self.assertEqual(digest, semantic_diff(raw, text)["after_digest"])

    def test_yaml_on_not_bool(self):
        self.assertEqual(load_yaml("on: pull_request\n")["on"], "pull_request")

    def test_yaml_aliases_rejected(self):
        with self.assertRaises(EvidenceError):
            load_yaml("a: &x foo\nb: *x\n")

    def test_yaml_duplicate_keys_rejected(self):
        for raw in ("a: 1\na: 2\n", "outer:\n  x: 1\n  x: 2\n"):
            with self.subTest(raw=raw), self.assertRaises(EvidenceError):
                load_yaml(raw)

    def test_yaml_merge_alias_rejected(self):
        with self.assertRaises(EvidenceError):
            load_yaml("a: &x {value: 1}\nb: {<<: *x}\n")

    def test_yaml_document_count(self):
        with self.assertRaises(EvidenceError):
            load_yaml("a: 1\n---\nb: 2\n")

    def test_yaml_oversized(self):
        with self.assertRaises(EvidenceError):
            load_yaml("a: " + "x" * 1000, max_bytes=64)

    def test_yaml_semantic_change_detection(self):
        self.assertTrue(semantic_diff("a: 1\n", "a: 2\n")["changed"])

    def test_unknown_dependency(self):
        p = copy.deepcopy(PLAN)
        p["tasks"][0]["needs"] = ["MISSING"]
        with self.assertRaises(EvidenceError):
            validate_plan(p)

    def test_cycle_rejected(self):
        p = copy.deepcopy(PLAN)
        p["tasks"][0]["needs"] = ["KPI_PULSE"]
        with self.assertRaises(EvidenceError):
            validate_plan(p)

    def test_duplicate_task_rejected(self):
        p = copy.deepcopy(PLAN)
        p["tasks"].append(copy.deepcopy(p["tasks"][0]))
        with self.assertRaises(EvidenceError):
            validate_plan(p)

    def test_overlap_rejected(self):
        p = copy.deepcopy(PLAN)
        p["tasks"].append(
            {
                "id": "SECOND_WRITER",
                "plane": "orchestration",
                "owner": "other",
                "mode": "REVIEW_REQUIRED",
                "needs": [],
                "write_paths": ["tools/everred_v3/src/four_planes.py"],
            }
        )
        with self.assertRaises(EvidenceError):
            validate_plan(p)

    def test_reader_may_not_write_source(self):
        p = copy.deepcopy(PLAN)
        p["tasks"][0]["write_paths"] = ["docs/ci"]
        with self.assertRaises(EvidenceError):
            validate_plan(p)

    def test_path_traversal_rejected(self):
        p = copy.deepcopy(PLAN)
        p["tasks"][-1]["write_paths"] = ["../ci"]
        with self.assertRaises(EvidenceError):
            validate_plan(p)

    def test_block_unverified_dep(self):
        r = evaluate_dispatch(PLAN, {"YAML_PREFLIGHT": "PASS"})
        tasks = {x["id"]: x for x in r["tasks"]}
        self.assertEqual(tasks["LDAB_CORRELATION"]["state"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(tasks["CONTROLLED_MUTATION"]["state"], "HOLD_REVIEW")
        self.assertFalse(r["executed"])

    def test_red_dependency_blocks(self):
        r = evaluate_dispatch(PLAN, {"YAML_PREFLIGHT": "FAIL"})
        self.assertEqual(
            next(x for x in r["tasks"] if x["id"] == "DEBUG_LLDB")["state"],
            "BLOCKED_UPSTREAM_RED",
        )

    def test_federation_two_bindings(self):
        self.assertEqual(validate_federation_policy(FED)["binding_count"], 2)

    def test_federation_authority_transfer_blocked(self):
        p = copy.deepcopy(FED)
        p["bindings"][0]["action"] = "ACCEPT"
        with self.assertRaises(EvidenceError):
            validate_federation_policy(p)

    def test_federation_duplicate_rejected(self):
        p = copy.deepcopy(FED)
        p["bindings"].append(copy.deepcopy(p["bindings"][0]))
        with self.assertRaises(EvidenceError):
            validate_federation_policy(p)


class Federation(unittest.TestCase):
    def setUp(self):
        self.source = Source("GBOGEB/CODEX", SHA, 999, 5, OTHER)
        self.payload = {
            "producer_repo": "GBOGEB/CODEX",
            "domain": "lldb-dap",
            "source_sha": SHA,
            "executed_sha": OTHER,
            "artifact_sha256": hashlib.sha256(b"bytes").hexdigest(),
            "receipt_id": "CODEX-DBG-01",
        }

    def test_bound_bytes_are_not_approval(self):
        r = evaluate_exchange(
            FED,
            producer=self.source,
            consumer_repo="GBOGEB/ABACUS",
            receipt=self.payload,
            artifact_bytes=b"bytes",
        )
        self.assertEqual(r["consumer_disposition"], "DEFER")
        self.assertEqual(
            r["integrity"], "LOCAL_BYTES_HASH_MATCHED_NOT_NATIVE_JOB_ATTESTED"
        )
        self.assertFalse(r["authority_transfer"])

    def test_declared_checksum_not_verified(self):
        r = evaluate_exchange(
            FED,
            producer=self.source,
            consumer_repo="GBOGEB/ABACUS",
            receipt=self.payload,
        )
        self.assertEqual(r["integrity"], "DECLARED_UNVERIFIED")

    def test_wrong_producer_rejected(self):
        p = dict(self.payload, producer_repo="GBOGEB/ABACUS")
        with self.assertRaises(EvidenceError):
            evaluate_exchange(
                FED, producer=self.source, consumer_repo="GBOGEB/ABACUS", receipt=p
            )

    def test_wrong_executed_sha_rejected(self):
        p = dict(self.payload, executed_sha=SHA)
        with self.assertRaises(EvidenceError):
            evaluate_exchange(
                FED, producer=self.source, consumer_repo="GBOGEB/ABACUS", receipt=p
            )

    def test_wrong_payload_hash_rejected(self):
        with self.assertRaises(EvidenceError):
            evaluate_exchange(
                FED,
                producer=self.source,
                consumer_repo="GBOGEB/ABACUS",
                receipt=self.payload,
                artifact_bytes=b"tampered",
            )

    def test_missing_policy_binding(self):
        with self.assertRaises(EvidenceError):
            evaluate_exchange(
                FED,
                producer=self.source,
                consumer_repo="GBOGEB/cryoplant-project",
                receipt=self.payload,
            )

    def test_review_queue_always_holds(self):
        r = evaluate_exchange(
            FED,
            producer=self.source,
            consumer_repo="GBOGEB/ABACUS",
            receipt=self.payload,
        )
        p = release_candidate([r])
        self.assertEqual(p["independently_accepted"], None)
        self.assertEqual(p["admission"], "HOLD")


class JoinAndNative(unittest.TestCase):
    def test_exact_sha_separates_receipts(self):
        a = runtime_receipt(SRC, runtime())
        b = runtime_receipt(Source("GBOGEB/ABACUS", OTHER, 124), runtime())
        joined = federated_join([a, b])
        self.assertEqual(joined["group_count"], 2)

    def test_diagnostic_distinct_from_runtime(self):
        a = diagnostic_receipt(SRC, debug())
        b = runtime_receipt(SRC, runtime())
        joined = federated_join([a, b])
        self.assertEqual(len(joined["groups"][0]["planes"]["diagnostic"]), 1)
        self.assertEqual(len(joined["groups"][0]["planes"]["runtime"]), 1)
        self.assertEqual(joined["global_admission"], "HOLD")

    def test_receipt_tampering_rejected(self):
        a = runtime_receipt(SRC, runtime())
        a["data"]["os_family"] = "RHEL9"
        with self.assertRaises(EvidenceError):
            federated_join([a])

    def test_duplicate_receipts_rejected(self):
        a = runtime_receipt(SRC, runtime())
        with self.assertRaises(EvidenceError):
            federated_join([a, a])

    def test_native_preflight_source_preserving(self):
        r = execute("GBOGEB/ABACUS", SHA, 777)
        self.assertEqual(r["joined_census"]["observation_count"], 1)
        self.assertEqual(r["source_binding"]["source_sha"], SHA)
        self.assertEqual(r["claims"]["admission"], "HOLD")
        self.assertIsNone(r["claims"]["remote_worker_count"])
        self.assertIsNone(r["claims"]["self_hosted_rhel_verified"])

    def test_schema_validator(self):
        jsonschema = None
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        if jsonschema is None:
            self.skipTest("jsonschema not installed")
        schema = json.loads(
            (BASE / "contracts/four-plane-receipt.schema.json").read_text()
        )
        instance = diagnostic_receipt(SRC, debug())
        jsonschema.validate(instance, schema)
        instance["merge_authority"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance, schema)


class CanonicalLdabIntegration(unittest.TestCase):
    def fixture(self):
        return {
            "schema": "bd.ldab.joined.census.v1",
            "scope": {
                "repository": "GBOGEB/ABACUS",
                "head_sha": SHA,
                "run_id": 123,
                "job_id": 456,
            },
            "roots": [
                {
                    "root_id": "BD-001",
                    "category": "BANDIT",
                    "fingerprint": DIG,
                    "owner_lane": "B3-subprocess",
                    "observations": [
                        {
                            "repository": "GBOGEB/ABACUS",
                            "source_sha": SHA,
                            "run_id": 123,
                            "job_id": 456,
                        }
                    ],
                },
                {
                    "root_id": "CI-001",
                    "category": "CI",
                    "fingerprint": None,
                    "observations": [],
                },
            ],
            "metrics": {"full_bandit_unique": 1},
            "unlinked_debug_receipts": [],
            "merge_admission": "HOLD",
            "authority_transfer": False,
            "security_waiver": False,
        }

    def test_canonical_bridge(self):
        result = consume_bd_ldab(self.fixture(), expected_source=SRC)
        self.assertEqual(len(result["bandit_candidates"]), 1)
        self.assertEqual(result["ci_candidate_ids"], ["CI-001"])
        self.assertEqual(
            result["bandit_candidates"][0]["data"]["disposition"], "HYPOTHESIS"
        )
        self.assertIsNone(result["causal_roots_confirmed"])

    def test_cross_sha_rejected(self):
        source = self.fixture()
        source["scope"]["head_sha"] = OTHER
        with self.assertRaises(EvidenceError):
            consume_bd_ldab(source, expected_source=SRC)

    def test_denominator_mismatch_rejected(self):
        source = self.fixture()
        source["metrics"]["full_bandit_unique"] = 2
        with self.assertRaises(EvidenceError):
            consume_bd_ldab(source, expected_source=SRC)

    def test_canonical_must_hold(self):
        source = self.fixture()
        source["merge_admission"] = "ADMIT"
        with self.assertRaises(EvidenceError):
            consume_bd_ldab(source, expected_source=SRC)

    def test_duplicate_canonical_roots_rejected(self):
        source = self.fixture()
        source["roots"].append(dict(source["roots"][0]))
        with self.assertRaises(EvidenceError):
            consume_bd_ldab(source, expected_source=SRC)


class ContractSchemaIntegration(unittest.TestCase):
    def test_config_jsonschema_parity(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema absent")
        for name, payload in (("execution-plan", PLAN), ("federation-policy", FED)):
            with self.subTest(name=name):
                schema = json.loads(
                    (BASE / "contracts" / (name + ".schema.json")).read_text()
                )
                jsonschema.validate(payload, schema)

    def test_unknown_group_denied_by_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema absent")
            return
        schema = json.loads((BASE / "contracts/execution-plan.schema.json").read_text())
        p = copy.deepcopy(PLAN)
        p["tasks"][0]["mode"] = "BYPASS_GATE"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(p, schema)


if __name__ == "__main__":
    unittest.main()
