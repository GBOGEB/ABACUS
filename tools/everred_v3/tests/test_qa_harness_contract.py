"""Fail-closed static regression checks for offline browser QA.

These checks do not claim Playwright or Chromium executed.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "qa_browser.py"


class BrowserHarnessContract(unittest.TestCase):
    """Guard the standalone self-contained browser QA contract."""

    def test_no_background_subprocess_or_debug_port(self):
        source = HARNESS.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("http.server", source)
        self.assertNotIn("8765", source)

    def test_negative_import_rejection_is_retained(self):
        source = HARNESS.read_text(encoding="utf-8")
        self.assertIn("invalid.json", source)
        self.assertIn("Import rejected", source)
        self.assertIn("set_input_files(", source)

    def test_desktop_mobile_and_tabs_remain_interactive(self):
        source = HARNESS.read_text(encoding="utf-8")
        self.assertIn("await page.set_content(", source)
        self.assertIn("#rootSearch", source)
        self.assertIn("#diagramViewer svg", source)
        self.assertIn("qa-desktop.png", source)
        self.assertIn("qa-mobile.png", source)


if __name__ == "__main__":
    unittest.main()
