from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts import validate_ssot_style as style


class ValidateSsotStyleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = style.load_manifest(style.DEFAULT_MANIFEST)

    def test_manifest_is_valid(self) -> None:
        self.assertEqual(style.validate_manifest(self.manifest), [])

    def test_missing_required_html_gate_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact_contract"]["html"].remove("playwright_navigation")

        errors = style.validate_manifest(manifest)

        self.assertTrue(any("missing required HTML QA gate" in error for error in errors))

    def test_awake_probe_score_counts_existing_paths(self) -> None:
        manifest = {
            "awake_probes": [
                {"id": "live", "kind": "html", "path": "live.html", "weight": 3},
                {"id": "missing", "kind": "graph", "path": "missing.yaml", "weight": 1},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "live.html").write_text("<html></html>", encoding="utf-8")

            report = style.score_awake_probes(manifest, root=root)

        self.assertEqual(report["awake_score"], 75.0)
        self.assertEqual(report["by_kind"]["html"], {"awake": 1, "total": 1})
        self.assertEqual(report["by_kind"]["graph"], {"awake": 0, "total": 1})

    def test_penetration_score_uses_content_signals(self) -> None:
        manifest = {
            "awake_probes": [
                {"id": "graph", "kind": "graph", "path": "graph.yaml", "weight": 1},
                {"id": "qa", "kind": "playwright", "path": "qa.py", "weight": 1},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "graph.yaml").write_text(
                "nodes:\n  - id: a\ndepends_on:\n  - b\nobjectives:\n  - test\n",
                encoding="utf-8",
            )
            (root / "qa.py").write_text(
                "from playwright.sync_api import sync_playwright\n"
                "page.on('console', print)\n"
                "page.evaluate('document.body.scrollWidth')\n",
                encoding="utf-8",
            )

            report = style.score_penetration(manifest, root=root)

        self.assertEqual(report["penetration_score"], 100.0)
        self.assertEqual(report["by_kind"]["graph"], {"depth": 4, "max_depth": 4})


if __name__ == "__main__":
    unittest.main()
