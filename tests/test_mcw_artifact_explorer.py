"""Negative and UI checks for the cold artifact evidence browser."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mcw_artifact_explorer", ROOT / "tools" / "mcw_artifact_explorer.py"
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SHA = "a" * 40
STYLE = {"version": "0.2", "palette": {"tokens": {
    "define": "#562873", "measure": "#984A9C", "analyze": "#034694",
    "improve": "#B5622A", "control": "#1D7A5F", "critical": "#B42318"
}}}


def fixture():
    return {"schema": M.SCHEMA, "triggers": [
        {"event": "PR", "stage": "TYPE_QA", "action": "Cold checks"}
    ], "artifacts": [
        {"id": "ssot-json", "title": "Actual <SSOT> source",
         "format": "json", "role": "repository_source", "path": "ssot.json"},
        {"id": "derived-xlsx", "title": "Derived workbook", "format": "xlsx",
         "role": "generated_output", "generator": "generator.py",
         "depends_on": ["ssot-json"]},
        {"id": "original-docx", "title": "Original docx", "format": "docx",
         "role": "controlled_input"},
    ]}


class ColdBuildTests(unittest.TestCase):
    def setup(self, root):
        (root / "ssot.json").write_text('{"source": true}')
        (root / "generator.py").write_text("pass")
        return fixture()

    def test_renders_self_contained_html_and_truthful_states(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            result = M.evaluate(root, catalog, STYLE, SHA)
            self.assertEqual(result["role_counts"]["generated_output"], 1)
            self.assertEqual(result["states"]["LOCAL_BYTES_VERIFIED"], 1)
            self.assertEqual(result["states"]["NOT_GENERATED_IN_COLD_VIEW"], 1)
            self.assertFalse(result["binary_release_admitted"])
            page = M.render(result, STYLE)
            self.assertIn("Actual &lt;SSOT&gt;", page)
            self.assertNotIn("Actual <SSOT>", page)
            self.assertIn("Build DAG", page)
            self.assertIn("SHA-256", page)
            self.assertIn('id="format"', page)
            self.assertIn('Inspect source excerpt', page)
            self.assertIn('source', page)
            self.assertIn('[hidden]{display:none!important}', page)
            self.assertIn("Merge admission: HOLD", page)
            self.assertNotIn("<script src=", page)

    def test_missing_style_probes_visible_without_false_release(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            result = M.evaluate(root, catalog, STYLE, SHA)
            result["missing_style_probes"] = ["qps_style_manifest"]
            result["style_file_sha256"] = "f" * 64
            result["catalog_file_sha256"] = "e" * 64
            page = M.render(result, STYLE)
            self.assertIn("Missing style probes: qps_style_manifest", page)
            self.assertIn("Style file SHA-256", page)
            self.assertIn("Catalog file SHA-256", page)
            self.assertIn("Merge admission: HOLD", page)

    def test_cold_reproducibility_and_no_binary_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            p = M.render(M.evaluate(root, catalog, STYLE, SHA), STYLE)
            q = M.render(M.evaluate(root, catalog, STYLE, SHA), STYLE)
            self.assertEqual(M.digest(p.encode()), M.digest(q.encode()))
            self.assertFalse((root / "derived-xlsx").exists())

    def test_source_tampering_changes_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            before = M.evaluate(root, catalog, STYLE, SHA)
            (root / "ssot.json").write_text('{"source": false}')
            after = M.evaluate(root, catalog, STYLE, SHA)
            self.assertNotEqual(before["artifacts"][0]["evidence"]["sha256"],
                                after["artifacts"][0]["evidence"]["sha256"])

    def test_rejects_unsafe_source_and_generated_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            catalog["artifacts"][0]["path"] = "../secret"
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, STYLE, SHA)
            catalog = self.setup(root)
            catalog["artifacts"][1]["generator"] = "/etc/passwd"
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, STYLE, SHA)

    def test_rejects_missing_source_and_cycle_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            catalog["artifacts"][0]["path"] = "not-there.json"
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, STYLE, SHA)
            catalog = self.setup(root)
            catalog["artifacts"][0]["depends_on"] = ["derived-xlsx"]
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, STYLE, SHA)
            catalog = self.setup(root)
            catalog["artifacts"].append(catalog["artifacts"][0])
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, STYLE, SHA)

    def test_original_controlled_binary_hash_not_semantic_row_delta(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            original = root / "original.docx"
            original.write_bytes(b"unchanged original bytes")
            item = catalog["artifacts"][2]
            item["path"] = "original.docx"
            item["expected_sha256"] = M.digest(original.read_bytes())
            result = M.evaluate(root, catalog, STYLE, SHA)
            self.assertEqual(result["artifacts"][2]["evidence"]["state"],
                             "INPUT_HASH_VERIFIED_UNCHANGED")
            self.assertFalse(result["semantic_delta_zero_proves_byte_identity"])
            original.write_bytes(b"tampered bytes")
            with self.assertRaisesRegex(ValueError, "immutable input hash"):
                M.evaluate(root, catalog, STYLE, SHA)

    def test_invalid_trigger_and_missing_style_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            catalog = self.setup(root)
            catalog["triggers"][0]["stage"] = "MERGE"
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, STYLE, SHA)
            catalog = self.setup(root)
            with self.assertRaises(ValueError):
                M.evaluate(root, catalog, {}, SHA)

    def test_real_repository_sample_paths_and_style_contract(self):
        catalog = json.loads((ROOT / "docs" / "mcw" / "artifact_catalog.v1.json").read_text())
        style = json.loads((ROOT / "ssot" / "ssot_style.json").read_text())
        self.assertEqual(len(catalog["artifacts"]), 10)
        self.assertEqual(len(catalog["triggers"]), 9)
        self.assertEqual(style["palette"]["tokens"]["define"], "#562873")
        for item in catalog["artifacts"]:
            if item["role"] == "repository_source":
                self.assertTrue((ROOT / item["path"]).is_file())
            if item["role"] == "generated_output":
                self.assertTrue((ROOT / item["generator"]).is_file())


if __name__ == "__main__":
    unittest.main()
