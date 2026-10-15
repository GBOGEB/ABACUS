"""Adversarial, no-authority regression tests for QPS DOW evidence."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

from test_qps_math_wormhole_dow import ARTIFACT, P, SHA, mod, reseal, synthetic


class DOWAdversarialTests(TestCase):
    def check_mutation(self, section, key, value, expected):
        item = copy.deepcopy(synthetic())
        item[section][key] = value
        issues = mod.classify(
            reseal(item),
            expected_sha=SHA,
            expected_artifact_digest=ARTIFACT,
        )
        self.assertIn(expected, issues)

    def test_malformed_scalar_and_list(self):
        for value in (None, 123, "", [], ["private"]):
            with self.subTest(value=value):
                self.assertEqual(
                    ["MALFORMED_RECEIPT"],
                    mod.classify(
                        value, expected_sha=SHA,
                        expected_artifact_digest=ARTIFACT,
                    ),
                )

    def test_wrong_schema_and_route_identity(self):
        for key, value in (
            ("schema", "gg-math-qps-wormhole/v999"),
            ("route_id", "QPS-UNKNOWN"),
        ):
            item = synthetic()
            item[key] = value
            self.assertIn(
                "SCHEMA_VERSION_MISMATCH",
                mod.classify(
                    reseal(item), expected_sha=SHA,
                    expected_artifact_digest=ARTIFACT,
                ),
            )

    def test_reordered_route_rejected(self):
        item = synthetic()
        item["route"].reverse()
        self.assertIn(
            "INVALID_P4_ROUTE_OR_FAKE_HOP",
            mod.classify(
                reseal(item), expected_sha=SHA,
                expected_artifact_digest=ARTIFACT,
            ),
        )

    def test_provider_identity_requires_exact_shape(self):
        for value in (None, {}, {"repo": "GBOGEB/gg_MATH"}):
            with self.subTest(value=value):
                item = synthetic()
                item["producer"] = value
                self.assertIn(
                    "PROVIDER_IDENTITY_MISSING",
                    mod.classify(
                        reseal(item), expected_sha=SHA,
                        expected_artifact_digest=ARTIFACT,
                    ),
                )

    def test_provider_sha_and_repository(self):
        self.check_mutation(
            "producer", "source_sha", "NOT-A-SHA", "PROVIDER_SHA_INVALID"
        )
        self.check_mutation(
            "producer", "repo", "GBOGEB/unknown", "PROVIDER_SHA_INVALID"
        )

    def test_path_traversal_and_absolute_paths(self):
        for path in (
            "../private.json", (Path(tempfile.gettempdir()) / "private.json").as_posix(), r"private\secret.json",
            "C:private.json", "folder/./file.json", "folder/../file.json",
        ):
            with self.subTest(path=path):
                self.check_mutation(
                    "producer", "artifact_path", path,
                    "ARTIFACT_IDENTITY_INVALID",
                )

    def test_artifact_digest_wrong_format(self):
        self.check_mutation(
            "producer", "artifact_sha256", "NOT-A-DIGEST",
            "ARTIFACT_IDENTITY_INVALID",
        )

    def test_method_shape_and_whitelist(self):
        item = synthetic()
        item["method"] = None
        self.assertIn(
            "METHOD_SCHEMA_INVALID",
            mod.classify(
                reseal(item), expected_sha=SHA,
                expected_artifact_digest=ARTIFACT,
            ),
        )
        self.check_mutation(
            "method", "id", "UNKNOWN_METHOD",
            "METHOD_AUTHORITY_OR_BT_INVALID",
        )

    def test_non_synthetic_and_unicode_population(self):
        for population in ("QPS_PRIVATE_BID", "SYNTHETIC_\u00e9"):
            with self.subTest(population=population):
                self.check_mutation(
                    "method", "population_id", population,
                    "UNSAFE_POPULATION",
                )

    def test_foreign_threshold_authority_rejected(self):
        self.check_mutation(
            "method", "threshold_authority", "CODEX",
            "METHOD_AUTHORITY_OR_BT_INVALID",
        )

    def test_fake_runtime_job_and_steps_rejected(self):
        self.check_mutation(
            "execution", "run_id", 12345, "UNAUTHENTICATED_RUNTIME_CREDIT"
        )
        self.check_mutation(
            "execution", "positive_steps", 4,
            "UNAUTHENTICATED_RUNTIME_CREDIT",
        )

    def test_project_decision_injection_rejected(self):
        self.check_mutation(
            "lineage", "qps_child_state", "ACCEPT",
            "PROJECT_DECISION_INJECTION",
        )
        self.check_mutation(
            "lineage", "wave", "", "PROJECT_DECISION_INJECTION"
        )

    def test_noncanonical_nan_is_rejected(self):
        item = synthetic()
        item["lineage"]["pulse"] = float("nan")
        item["receipt_sha256"] = "0" * 64
        self.assertIn(
            "NONCANONICAL_RECEIPT",
            mod.classify(
                item, expected_sha=SHA,
                expected_artifact_digest=ARTIFACT,
            ),
        )

    def test_fingerprint_and_digest_do_not_grant_authority(self):
        item = synthetic()
        item["producer"]["source_sha"] = "b" * 40
        result = mod.observe(
            reseal(item), expected_sha=SHA,
            expected_artifact_digest=ARTIFACT,
        )
        self.assertGreater(result["measurement"]["unique_roots"], 0)
        self.assertEqual(0, result["measurement"]["runtime_authenticated"])
        self.assertFalse(result["qps_acceptance"])
        self.assertEqual(0, result["formal_credit_delta"])
        self.assertEqual(
            mod.sha256_json({
                k: v for k, v in result.items() if k != "receipt_sha256"
            }),
            result["receipt_sha256"],
        )

    def test_cli_positive_path_remains_proposal_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "provider.json"
            output = Path(tmp) / "candidate.json"
            receipt.write_text(json.dumps(synthetic()), encoding="utf-8")
            command = [
                sys.executable, str(P),
                "--provider-receipt", str(receipt),
                "--provider-sha", SHA,
                "--artifact-sha256", ARTIFACT,
                "--out", str(output),
            ]
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertEqual(0, result.returncode, result.stderr)
            body = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("VALID_PROPOSAL_ONLY", body["status"])
            self.assertEqual("UNVERIFIED", body["replay_status"])
            self.assertFalse(body["qps_acceptance"])

    def test_cli_rejects_oversize_and_wrong_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "provider.json"
            output = Path(tmp) / "candidate.json"
            receipt.write_bytes(b" " * (mod.MAX_SIZE + 1))
            command = [
                sys.executable, str(P),
                "--provider-receipt", str(receipt),
                "--provider-sha", SHA,
                "--artifact-sha256", ARTIFACT,
                "--out", str(output),
            ]
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(output.exists())
            receipt.write_text(json.dumps(synthetic()), encoding="utf-8")
            command[command.index(SHA)] = "b" * 40
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertEqual(1, result.returncode)
            body = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("DEFER_INVALID_CONTRACT", body["status"])
