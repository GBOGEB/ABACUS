"""Repository map page (docs/repo-structure/index.html): deterministic, self-contained, in sync."""

from __future__ import annotations

import html
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "root_refactor" / "discovery_page.py"
SPEC = importlib.util.spec_from_file_location("root_discovery_page", SCRIPT)
page_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(page_mod)


class DiscoveryPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = page_mod.render()

    def test_render_is_deterministic(self):
        self.assertEqual(self.page, page_mod.render())

    def test_committed_page_is_current(self):
        out = ROOT / page_mod.OUT
        self.assertTrue(out.is_file(), f"{page_mod.OUT} missing; run: {page_mod.REGEN}")
        self.assertEqual(
            out.read_bytes().decode("utf-8"),
            self.page,
            f"{page_mod.OUT} is stale; run: {page_mod.REGEN}",
        )

    def test_self_contained(self):
        low = self.page.lower()
        self.assertNotIn("<script src", low)
        self.assertNotIn("http://", low)
        self.assertNotIn('rel="stylesheet"', low)
        self.assertNotIn("rel=stylesheet", low)
        self.assertNotIn("@import", low)
        self.assertIn("https://github.com/GBOGEB/ABACUS", self.page)
        self.assertIn("https://gbogeb.github.io/ABACUS/", self.page)

    def test_every_file_is_listed(self):
        for r in page_mod.load_inventory():
            self.assertIn(html.escape(r["path"]), self.page, r["path"])
        for m in page_mod.relocate_mod.load_map():
            self.assertIn(html.escape(m["new_path"]), self.page, m["new_path"])

    def test_no_real_user_path(self):
        self.assertNotIn("C:\\Users", self.page)
        self.assertNotIn("C:/Users", self.page)

    def test_newlines_and_size(self):
        self.assertNotIn("\r", self.page)
        self.assertLess(len(self.page.encode("utf-8")), 400_000)


if __name__ == "__main__":
    unittest.main()
