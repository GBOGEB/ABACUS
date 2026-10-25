"""Root refactor waves: link rewriting and the non-breaking relocation invariant."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "root_refactor" / "relocate.py"
SPEC = importlib.util.spec_from_file_location("root_relocate", SCRIPT)
relocate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relocate)

DEST = "docs_versioned/generated_reports"
MOVES = {"Report_1.md": f"{DEST}/Report_1.md", "Report_2.md": f"{DEST}/Report_2.md",
         "My File.md": f"{DEST}/My File.md"}


def row(**kw):
    base = {"old_path": "a.md", "new_path": "docs_versioned/x/a.md", "family": "F1",
            "wave": "W1", "disposition": "ARCHIVE_PRESERVE_LINKS"}
    base.update(kw)
    return base


class RewriteLinksTest(unittest.TestCase):
    def test_inbound_link_follows_moved_file(self):
        text = "See [run](Report_1.md) and [ref][r].\n\n[r]: Report_2.md\n"
        out = relocate.rewrite_links(text, "README.md", "README.md", MOVES)
        self.assertIn(f"[run]({DEST}/Report_1.md)", out)
        self.assertIn(f"[r]: {DEST}/Report_2.md", out)

    def test_inbound_link_from_nested_document(self):
        out = relocate.rewrite_links("[x](../Report_1.md)", "docs/a.md", "docs/a.md", MOVES)
        self.assertEqual(out, "[x](../docs_versioned/generated_reports/Report_1.md)")

    def test_moved_document_rebases_its_own_links(self):
        text = ('[home](README.md) [sib](Report_2.md) [web](https://x.y/README.md) '
                '[top](#summary) <a href="docs/index.html">d</a>')
        out = relocate.rewrite_links(text, "Report_1.md", MOVES["Report_1.md"], MOVES)
        self.assertIn("[home](../../README.md)", out)
        self.assertIn("[sib](Report_2.md)", out)
        self.assertIn("[web](https://x.y/README.md)", out)
        self.assertIn("[top](#summary)", out)
        self.assertIn('href="../../docs/index.html"', out)

    def test_fragment_title_and_encoding_are_kept(self):
        out = relocate.rewrite_links('[m](My%20File.md#sec "t")', "README.md", "README.md", MOVES)
        self.assertEqual(out, f'[m]({DEST.replace(" ", "%20")}/My%20File.md#sec "t")')

    def test_fenced_code_is_left_alone(self):
        text = "```\n[x](Report_1.md)\n```\n[y](Report_1.md)\n"
        out = relocate.rewrite_links(text, "README.md", "README.md", MOVES)
        self.assertIn("```\n[x](Report_1.md)\n```", out)
        self.assertIn(f"[y]({DEST}/Report_1.md)", out)

    def test_unrelated_document_is_unchanged(self):
        text = "[a](docs/x.md) [b](../outside.md) [c](mailto:a@b)"
        self.assertEqual(relocate.rewrite_links(text, "README.md", "README.md", MOVES), text)

    def test_links_to_finds_only_live_links(self):
        text = "`Report_1.md` | Report_1.md\n[x](Report_1.md)\n```\n[y](Report_1.md)\n```\n"
        self.assertEqual(relocate.links_to(text, "README.md", {"Report_1.md"}), ["Report_1.md"])


class CodeMentionsTest(unittest.TestCase):
    def test_bare_root_names_are_found_and_nested_paths_are_not(self):
        olds = {"Report_1.md", "HANDOVER.md"}
        text = ('BOOK = ["Report_1.md", "docs/HANDOVER.md"]\n'
                "  - HANDOVER.md\ngit add Report_1.md.bak\n")
        self.assertEqual(relocate.code_mentions(text, olds), ["HANDOVER.md", "Report_1.md"])
        self.assertEqual(relocate.code_mentions("docs/HANDOVER.md Report_1.md.bak", olds), [])
        self.assertEqual(relocate.code_mentions("anything", set()), [])


class ValidateRowsTest(unittest.TestCase):
    def test_good_row_passes(self):
        self.assertEqual(relocate.validate_rows([row()]), [])

    def test_bad_rows_are_rejected(self):
        bad = [row(old_path="docs/a.md", new_path="docs_versioned/x/b.md"),
               row(old_path="b.md", new_path="b2.md"),
               row(old_path="c.md", new_path="docs_versioned/x/c.md", family="F9"),
               row(old_path="d.md", new_path="docs_versioned/x/d.md", wave="wave1"),
               row(old_path="e.md", new_path="docs_versioned/x/e.md", disposition="DELETE"),
               row(old_path="docs/a.md", new_path="docs_versioned/x/a.md")]
        errors = "\n".join(relocate.validate_rows(bad))
        for needle in ("not a root file", "sub-folder path", "family", "wave", "disposition", "duplicate"):
            self.assertIn(needle, errors)


class RepositoryRelocationTest(unittest.TestCase):
    def test_every_mapped_move_is_applied_and_link_safe(self):
        """Old root paths are gone, new paths exist, and no live link still targets an old path."""
        self.assertTrue(relocate.load_map(), "relocation map is missing or empty")
        self.assertEqual(relocate.check(), [])


if __name__ == "__main__":
    unittest.main()
