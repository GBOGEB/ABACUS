"""Synthetic receiver testflight; never engineering-owner acceptance.

No live cross-repo data, credentials, external files, or network writes.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.triage import accept_accelerator_atom_contract as receiver

SOURCE = "a" * 40
TARGET = "b" * 40
REQ_HASH = "c" * 64


def fixture():
    return {
        "schema": "accelerator-abacus-mapping/v0.1",
        "source_repo": "GBOGEB/cryogenic-accelerator-workspace",
        "target_repo": "GBOGEB/ABACUS",
        "source_sha": SOURCE,
        "target_sha": TARGET,
        "mapping_rows": [{
            "source_requirement_id": "SYNTHETIC-REQ-1",
            "source_requirement_sha256": REQ_HASH,
            "target_artifact": "triage/synthetic-demo.txt",
            "target_test_or_evidence": "SYNTHETIC-EVIDENCE",
            "relation_type": "trace-candidate",
            "disposition": "DEFER",
        }],
    }


def run_receiver(root, payload, *, source=SOURCE, target=TARGET):
    input_path = root / "synthetic-input.json"
    output_path = root / "bounded-output.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    args = ["receiver", "--payload", str(input_path),
            "--expected-source-sha", source, "--expected-target-sha", target,
            "--output", str(output_path)]
    with mock.patch.object(sys, "argv", args):
        with contextlib.redirect_stdout(io.StringIO()):
            receiver.main()
    return json.loads(output_path.read_text()), output_path


class ReceiverQualificationTests(unittest.TestCase):
    def test_receiver_emits_source_bound_non_authoritative_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output, _ = run_receiver(root, fixture())
            self.assertEqual(output["schema"], "abacus-accelerator-receiver/v0.1")
            self.assertEqual(output["status"], "ACCEPTED_AS_EVIDENCE_ONLY")
            self.assertEqual(output["source_sha"], SOURCE)
            self.assertEqual(output["target_sha"], TARGET)
            self.assertEqual(output["mapping_rows"], 1)
            self.assertFalse(output["release_credit"])
            self.assertFalse(output["compliance_credit"])
            self.assertEqual(output["authority_effect"], "NONE")
            self.assertEqual(output["payload_sha256"],
                             hashlib.sha256((root / "synthetic-input.json").read_bytes()).hexdigest())

    def test_receiver_supports_multiple_rows_without_acceptance_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            p = fixture()
            for state in ("REJECT", "ACCEPT"):
                row = dict(p["mapping_rows"][0], disposition=state,
                           source_requirement_id=f"SYNTHETIC-{state}")
                p["mapping_rows"].append(row)
            result, _ = run_receiver(Path(d), p)
            self.assertEqual(result["mapping_rows"], 3)
            self.assertFalse(result["release_credit"])

    def test_schema_and_source_owner_must_match(self):
        for key, invalid in [
            ("schema", "unknown"), ("source_repo", "wrong/source"),
            ("target_repo", "wrong/target"), ("source_sha", "0" * 40),
            ("target_sha", "0" * 40),
        ]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                p = fixture()
                p[key] = invalid
                with self.assertRaises(SystemExit):
                    run_receiver(Path(d), p)
                self.assertFalse((Path(d) / "bounded-output.json").exists())

    def test_bad_expected_ref_fails_closed(self):
        for field in ("source", "target"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                args = (dict(source="bad") if field == "source" else dict(target="bad"))
                with self.assertRaises(SystemExit):
                    run_receiver(Path(d), fixture(), **args)
                self.assertFalse((Path(d) / "bounded-output.json").exists())

    def test_missing_and_malformed_mapping_rows_fail_closed(self):
        mutations = [
            lambda p: p.update(mapping_rows=[]),
            lambda p: p.update(mapping_rows="not-a-list"),
            lambda p: p["mapping_rows"][0].pop("source_requirement_id"),
            lambda p: p["mapping_rows"][0].update(source_requirement_sha256="bad"),
            lambda p: p["mapping_rows"][0].update(disposition="AUTO_MERGE"),
            lambda p: p["mapping_rows"][0].update(target_artifact=""),
            lambda p: p["mapping_rows"][0].update(target_test_or_evidence=""),
        ]
        for i, transform in enumerate(mutations):
            with self.subTest(case=i), tempfile.TemporaryDirectory() as d:
                p = fixture()
                transform(p)
                with self.assertRaises((SystemExit, TypeError)):
                    run_receiver(Path(d), p)
                self.assertFalse((Path(d) / "bounded-output.json").exists())


if __name__ == "__main__":
    unittest.main()
