"""Real-byte ZIP / internal-path / replay controls; no acceptance credit."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from mission_control_lite.artifact_bundle import stage, verify_zip

SHA = "a" * 40
EVENT = "b" * 40


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        folder = self.root / "evidence"
        folder.mkdir(parents=True)
        (folder / "output.json").write_text('{"measured":true}')
        (folder / "coverage.json").write_text('{"run":42}')
        outputs = []
        for name in ("output.json", "coverage.json"):
            content = (folder / name).read_bytes()
            outputs.append({"path": "evidence/" + name,
                            "sha256": hashlib.sha256(content).hexdigest(),
                            "bytes": len(content)})
        rec = {"schema": "mcl.receipt.v1", "mission_id": "MCL",
               "task_id": "test", "root_id": "root1", "source_sha": SHA,
               "run_id": "42", "timestamp": "2026-10-18T20:00:00Z",
               "artifacts": outputs}
        (folder / "receipt.json").write_text(json.dumps(rec))
        (folder / "provenance.json").write_text(json.dumps({
            "executed_sha": SHA, "pull_head_sha": SHA, "event_sha": EVENT,
            "checkout_kind": "pull_head"}))
        (folder / "census.json").write_text('{"roots":[]}')

    def make_zip(self, flattened=False):
        bundle = self.base / "upload-root"
        stage("evidence/receipt.json", self.root, bundle,
              ["evidence/provenance.json", "evidence/census.json"])
        path = self.base / "artifact.zip"
        with zipfile.ZipFile(path, "w") as z:
            for file in sorted(bundle.rglob("*")):
                if file.is_file():
                    rel = file.relative_to(bundle).as_posix()
                    z.write(file, Path(rel).name if flattened else rel)
        return path, "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

    def test_positive_preserved_prefix_and_full_reingest(self):
        path, digest = self.make_zip()
        result = verify_zip(path, digest, ingest_roundtrip=True)
        self.assertEqual(result["attested"], 2)
        self.assertEqual(result["source_identity"], "PULL_HEAD_NOT_SYNTHETIC_EVENT")
        self.assertEqual(result["ingest_roundtrip"], "PASS")
        self.assertEqual(result["admission"], "HOLD")

    def test_negative_flattened_zip_fails_even_with_correct_digest(self):
        path, digest = self.make_zip(flattened=True)
        with self.assertRaisesRegex(ValueError, "evidence/"):
            verify_zip(path, digest)

    def test_negative_modified_outer_zip_digest(self):
        path, digest = self.make_zip()
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("evidence/extra.json", "bad")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            verify_zip(path, digest)

    def test_negative_modified_internal_bytes_with_new_zip_digest(self):
        path, _ = self.make_zip()
        entries = {}
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                entries[name] = z.read(name)
        entries["evidence/output.json"] = b'{"measured":false}'
        with zipfile.ZipFile(path, "w") as z:
            for key, value in entries.items():
                z.writestr(key, value)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "internal bytes"):
            verify_zip(path, digest)

    def test_negative_path_traversal_zip_even_with_correct_digest(self):
        path, _ = self.make_zip()
        with zipfile.ZipFile(path, "a") as z:
            z.writestr("../escape", "bad")
        with self.assertRaisesRegex(ValueError, "unsafe archive path"):
            verify_zip(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_negative_synthetic_merge_cannot_claim_pull_head(self):
        path, _ = self.make_zip()
        contents = {}
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                contents[name] = z.read(name)
        prov = json.loads(contents["evidence/provenance.json"])
        prov["executed_sha"] = EVENT
        contents["evidence/provenance.json"] = json.dumps(prov).encode()
        with zipfile.ZipFile(path, "w") as z:
            for name, data in contents.items():
                z.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "not executed PR head"):
            verify_zip(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_negative_reject_stale_stage_destination(self):
        self.make_zip()
        with self.assertRaisesRegex(ValueError, "stale reuse"):
            stage("evidence/receipt.json", self.root, self.base / "upload-root")

    def test_negative_no_trusted_source_byte_substitution(self):
        (self.root / "evidence/output.json").write_text('{"measured":false}')
        with self.assertRaisesRegex(ValueError, "do not match"):
            stage("evidence/receipt.json", self.root, self.base / "bundle-other")

    def test_negative_source_symlink_rejected(self):
        target = self.root / "evidence/output.json"
        target.unlink()
        target.symlink_to(self.base / "other")
        with self.assertRaises(ValueError):
            stage("evidence/receipt.json", self.root, self.base / "bundle-other")

    def test_negative_missing_github_digest(self):
        path, _ = self.make_zip()
        with self.assertRaisesRegex(ValueError, "missing GitHub digest"):
            verify_zip(path, None)


if __name__ == "__main__":
    unittest.main()
