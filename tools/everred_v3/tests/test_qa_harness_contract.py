"""Negative-control contracts for the offline EVERRED browser QA harness.

This static test does not claim that Chromium ran; the native Playwright
session and browser interaction still require independently linked receipts.
"""

import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "qa_browser.py"


class BrowserHarnessContract(unittest.TestCase):
    """Prevent reinstating unneeded background servers and misleading QA."""

    @staticmethod
    def _source():
        return HARNESS.read_text(encoding="utf-8")

    def test_offline_harness_never_spawns_subprocess_or_http_server(self):
        tree = ast.parse(self._source())
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertNotIn("subprocess", imports)
        self.assertNotIn("http.server", imports)
        self.assertNotIn("socketserver", imports)
        self.assertNotIn("8765", self._source())
        self.assertNotIn("subprocess.Popen", self._source())

    def test_invalid_dashboard_import_remains_a_negative_browser_case(self):
        source = self._source()
        self.assertIn("invalid.json", source)
        self.assertIn("Import rejected", source)
        self.assertIn('b\'{"schema":"bad"}\'', source)

    def test_browser_contract_remains_interactive_but_not_execution_proof(self):
        source = self._source()
        self.assertIn("await page.set_content(", source)
        self.assertIn('page.locator("#rootSearch").fill("SAFETY")', source)
        self.assertIn('page.locator("#diagramViewer svg")', source)
        self.assertIn("qa-desktop.png", source)
        self.assertIn("qa-mobile.png", source)


if __name__ == "__main__":
    unittest.main()
