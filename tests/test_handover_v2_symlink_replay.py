"""Reject externally backed capsule members, even when their bytes match.

The original V2 producer accepted a symlinked capsule member with a correct
digest. This is a local self-contained replay contract; it does not authorize
merge, remote source authentication or admission.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "handover_v2_symlink_core", ROOT / "tools/handover_v2/build_handover.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Canonical V2 core is unavailable")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


class TestV2SelfContainedReplay(unittest.TestCase):
    def test_external_symlink_cannot_pass_manifest_verification(self):
        with TemporaryDirectory() as temporary:
            work = Path(temporary)
            capsule = work / "capsule"
            capsule.mkdir()
            original = work / "outside.txt"
            original.write_bytes(b"identical archived bytes\n")
            (capsule / "input.json").write_bytes(b"{}\n")
            member = capsule / "dropin.md"
            try:
                member.symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest("Filesystem does not support symbolic links")
            contents = {
                "input.json": (capsule / "input.json").read_bytes(),
                "dropin.md": original.read_bytes(),
            }
            manifest = {
                "file_hashes_sha256": {
                    name: core.sha256(blob) for name, blob in contents.items()
                }
            }
            manifest["manifest_root_sha256"] = core.sha256(core.canonical(manifest))
            manifest_bytes = core.canonical(manifest)
            (capsule / "manifest.json").write_bytes(manifest_bytes)
            expected = {**contents, "manifest.json": manifest_bytes}
            with patch.object(core, "expected_files", return_value=(expected, manifest_bytes)):
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    core.capsule_verify(capsule)

    def test_regular_capsule_member_is_not_rejected_as_a_symlink(self):
        with TemporaryDirectory() as temporary:
            work = Path(temporary)
            capsule = work / "capsule"
            capsule.mkdir()
            (capsule / "input.json").write_bytes(b"{}\n")
            (capsule / "dropin.md").write_bytes(b"identical archived bytes\n")
            contents = {
                "input.json": (capsule / "input.json").read_bytes(),
                "dropin.md": (capsule / "dropin.md").read_bytes(),
            }
            manifest = {
                "file_hashes_sha256": {
                    name: core.sha256(blob) for name, blob in contents.items()
                }
            }
            manifest["manifest_root_sha256"] = core.sha256(core.canonical(manifest))
            manifest_bytes = core.canonical(manifest)
            (capsule / "manifest.json").write_bytes(manifest_bytes)
            expected = {**contents, "manifest.json": manifest_bytes}
            with patch.object(core, "expected_files", return_value=(expected, manifest_bytes)):
                data, saved = core.capsule_verify(capsule)
            self.assertEqual(data, {})
            self.assertEqual(saved["manifest_root_sha256"], manifest["manifest_root_sha256"])


if __name__ == "__main__":
    unittest.main()
