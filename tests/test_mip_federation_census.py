"""Negative controls for read-only federation and Mission Control scaling."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "tools/mip2/mip_federation_census.py"
SPEC = importlib.util.spec_from_file_location("mip_federation_census", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = "a" * 40


class FederationCensusTests(unittest.TestCase):
    """Exercise both per-domain breadth and evidence rejection."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = {
            "schema": MODULE.SCHEMA,
            "repositories": [
                {
                    "repository": "GBOGEB/ABACUS",
                    "head_sha": HEAD,
                    "evidence": [],
                },
            ],
        }

    def evaluate(self):
        """Evaluate the locally stored manifest."""
        return MODULE.evaluate(self.manifest, self.root)

    def add_receipt(self):
        """Bind a local byte-digest fixture to one simulated native identity."""
        payload = {"repository": "GBOGEB/ABACUS", "head_sha": HEAD}
        path = self.root / "native.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        item = {
            "domain": "MIP",
            "repository": "GBOGEB/ABACUS",
            "head_sha": HEAD,
            "run_id": 123,
            "job_id": 456,
            "path": path.name,
            "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        self.manifest["repositories"][0]["evidence"].append(item)
        return item

    def test_missing_domains_are_unknown_not_zero(self):
        result = self.evaluate()
        self.assertEqual(16, result["total_domain_slots"])
        self.assertEqual(0, result["filled_receipt_slots"])
        self.assertEqual("UNKNOWN", result["cells"][0]["locally_hash_verified_receipts"])
        self.assertEqual("UNKNOWN", result["authenticated_fanout"])

    def test_all_eight_domains_are_visible(self):
        result = self.evaluate()
        self.assertEqual(8, result["domain_breadth"])
        self.assertEqual(set(MODULE.DOMAINS), {
            cell["domain"] for cell in result["cells"]
        })
        self.assertIn("LDAB_LLDB", MODULE.markdown(result))
        self.assertIn("THREE_P", MODULE.markdown(result))

    def test_valid_local_receipt_does_not_claim_crew_authentication(self):
        self.add_receipt()
        result = self.evaluate()
        self.assertEqual(1, result["filled_receipt_slots"])
        self.assertEqual(1, result["cells"][1]["locally_hash_verified_receipts"])
        self.assertEqual("UNKNOWN", result["cells"][1]["accepted_rex"])
        self.assertEqual("HOLD", result["merge_admission"])

    def test_bad_digest_fails_closed(self):
        receipt = self.add_receipt()
        receipt["artifact_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.evaluate()

    def test_cross_repo_spoof_rejected(self):
        receipt = self.add_receipt()
        receipt["repository"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "cross-repo"):
            self.evaluate()

    def test_stale_source_sha_rejected(self):
        receipt = self.add_receipt()
        receipt["head_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "mixed-head"):
            self.evaluate()

    def test_duplicate_native_receipt_rejected(self):
        receipt = self.add_receipt()
        self.manifest["repositories"][0]["evidence"].append(dict(receipt))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.evaluate()

    def test_unsafe_artifact_path_rejected(self):
        receipt = self.add_receipt()
        receipt["path"] = "../native.json"
        with self.assertRaisesRegex(ValueError, "escapes root"):
            self.evaluate()

    def test_unallowlisted_repo_fails_closed(self):
        self.manifest["repositories"][0]["repository"] = "other/project"
        with self.assertRaisesRegex(ValueError, "invalid repository"):
            self.evaluate()

    def test_two_repos_do_not_imply_authenticated_fanout(self):
        self.manifest["repositories"].append({
            "repository": "GBOGEB/CODEX",
            "head_sha": "b" * 40,
            "evidence": [],
        })
        result = self.evaluate()
        self.assertEqual(result["repository_breadth"], 2)
        self.assertEqual(result["authenticated_fanout"], "UNKNOWN")
        self.assertEqual(result["federation_main_coverage_delta"], "UNKNOWN")

    def test_wrong_payload_source_rejected(self):
        self.add_receipt()
        (self.root / "native.json").write_text(
            json.dumps({"repository": "GBOGEB/CODEX", "head_sha": HEAD}),
            encoding="utf-8",
        )
        receipt = self.manifest["repositories"][0]["evidence"][0]
        receipt["artifact_sha256"] = hashlib.sha256(
            (self.root / "native.json").read_bytes()
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
