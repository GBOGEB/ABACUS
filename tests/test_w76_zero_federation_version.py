"""W76: pin exact-blob tests for two federation stubs and product-version fallback.

The federation tests are deliberately offline: existence checks against staged
local files are NOT authenticated peer receipts or remote-dispatch evidence.
"""
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
import unittest.mock as mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_file(path, alias):
    spec = importlib.util.spec_from_file_location(alias, ROOT / path)
    if spec is None or spec.loader is None:
        raise AssertionError("unavailable production target " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class W76VersionAndFederationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="w76-federation-")
        self.addCleanup(self.tmp.cleanup)
        self.workspace = pathlib.Path(self.tmp.name)

    def test_product_version_source_root_is_canonical(self):
        mod = load_file("DMAIC_V3/product_version.py", "w76_product_main")
        self.assertEqual(mod._root(), ROOT)
        self.assertEqual(mod.get_product_version(), mod.ABACUS_VERSION)
        self.assertEqual(mod.PACKAGE_DISTRIBUTION, "abacus-dow")

    def test_product_version_source_valid_and_missing_value_negative(self):
        mod = load_file("DMAIC_V3/product_version.py", "w76_product_local")
        project = self.workspace / "pyproject.toml"
        with mock.patch.object(mod, "_root", return_value=self.workspace):
            project.write_text('[project]\nversion = "6.1.2"\n', encoding="utf-8")
            self.assertEqual(mod.get_product_version(), "6.1.2")
            for bad in ('[project]\nname="abacus-dow"\n',
                        '[project]\nversion = ""\n',
                        '[project]\nversion = 22\n'):
                with self.subTest(project=bad):
                    project.write_text(bad, encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "version is missing"):
                        mod.get_product_version()

    def test_product_version_distribution_fallback_if_source_absent(self):
        mod = load_file("DMAIC_V3/product_version.py", "w76_product_fallback")
        with (mock.patch.object(mod, "_root", return_value=self.workspace),
              mock.patch.object(mod, "package_version", return_value="7.2.0") as query):
            self.assertEqual(mod.get_product_version(), "7.2.0")
        query.assert_called_once_with("abacus-dow")

    def test_product_version_missing_or_empty_installed_distribution(self):
        mod = load_file("DMAIC_V3/product_version.py", "w76_product_errors")
        with (mock.patch.object(mod, "_root", return_value=self.workspace),
              mock.patch.object(mod, "package_version",
                                side_effect=mod.PackageNotFoundError("abacus-dow"))):
            with self.assertRaisesRegex(RuntimeError, "version unavailable"):
                mod.get_product_version()
        with (mock.patch.object(mod, "_root", return_value=self.workspace),
              mock.patch.object(mod, "package_version", return_value="")):
            with self.assertRaisesRegex(RuntimeError, "version is empty"):
                mod.get_product_version()

    def test_federation_two_stubs_cover_four_file_presence_truth_tables(self):
        cases = (
            ("codespace_jyperter", "GBOGEB/codespace_jyperter"),
            ("cryoplant_project", "GBOGEB/cryoplant-project"),
        )
        for name, expected_repo in cases:
            with self.subTest(stub=name):
                mod = load_file(
                    "integration/" + name + "/src/federation.py",
                    "w76_federation_" + name)
                manifest = self.workspace / name / "federation" / "manifest.yaml"
                spec = self.workspace / name / "runtime" / "spec.yaml"
                manifest.parent.mkdir(parents=True)
                spec.parent.mkdir(parents=True)
                with (mock.patch.object(mod, "_INTEGRATION_MANIFEST", manifest),
                      mock.patch.object(mod, "_FEDERATION_SPEC", spec)):
                    for manifest_exists in (False, True):
                        for spec_exists in (False, True):
                            manifest.unlink(missing_ok=True)
                            spec.unlink(missing_ok=True)
                            if manifest_exists:
                                manifest.touch()
                            if spec_exists:
                                spec.touch()
                            context = {"repo": name, "pulse": 7}
                            result = mod.assimilate(context)
                            count = int(manifest_exists) + int(spec_exists)
                            status = ("error" if count == 0 else
                                      "degraded" if count == 1 else "ok")
                            with self.subTest(files=count):
                                self.assertEqual(result["status"], status)
                                self.assertIs(result["manifest_found"], manifest_exists)
                                self.assertIs(result["spec_found"], spec_exists)
                                self.assertEqual(result["repo"], expected_repo)
                                self.assertEqual(result["plane"], "auxiliary")
                                self.assertEqual(result["context"], context)
                                self.assertEqual(len(result["details"]), 2)
                                self.assertTrue(any(
                                    ("MISSING:" if not manifest_exists else "OK:")
                                    in item for item in result["details"]))
                                self.assertNotIn("native_child_attestation", result)
                                self.assertNotIn("merge_authorized", result)

    def test_federation_none_context_and_empty_context_are_equivalent(self):
        for name in ("codespace_jyperter", "cryoplant_project"):
            mod = load_file("integration/" + name + "/src/federation.py",
                            "w76_federation_context_" + name)
            with (mock.patch.object(mod, "_INTEGRATION_MANIFEST",
                                    self.workspace / "missing-manifest.yaml"),
                  mock.patch.object(mod, "_FEDERATION_SPEC",
                                    self.workspace / "missing-spec.yaml")):
                self.assertEqual(mod.assimilate(None)["context"], {})
                self.assertEqual(mod.assimilate({})["context"], {})
                self.assertEqual(mod.assimilate({"root": None})["status"], "error")

    def test_federation_present_one_missing_does_not_claim_success(self):
        for name in ("codespace_jyperter", "cryoplant_project"):
            mod = load_file("integration/" + name + "/src/federation.py",
                            "w76_federation_negative_" + name)
            present = self.workspace / ("present_" + name)
            present.touch()
            missing = self.workspace / ("absent_" + name)
            with (mock.patch.object(mod, "_INTEGRATION_MANIFEST", present),
                  mock.patch.object(mod, "_FEDERATION_SPEC", missing)):
                result = mod.assimilate({"evidence": "local-only"})
                self.assertEqual(result["status"], "degraded")
                self.assertTrue(result["manifest_found"])
                self.assertFalse(result["spec_found"])


if __name__ == "__main__":
    unittest.main()
