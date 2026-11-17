"""Source regression for the 26-Oct Pandoc XeLaTeX undefined \\n control."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / "docs/ci/CBD_EOSS_N7_TAXONOMY_DAG_SIPOC_20261017.md"


class PandocGlossarySource(unittest.TestCase):
    def test_three_glossary_roles_use_real_markdown_line_breaks(self):
        text = GLOSSARY.read_text(encoding="utf-8")
        for role in ("LOCAL", "REPO", "FEDERATION"):
            with self.subTest(role=role):
                self.assertIn("**" + role + ":**", text)
        self.assertIn("pre-push.  \n**REPO:**", text)
        self.assertIn("first-red.  \n**FEDERATION:**", text)

    def test_literal_escape_is_not_a_tex_command(self):
        text = GLOSSARY.read_text(encoding="utf-8")
        # Raw backslash-n was interpreted by XeLaTeX as an undefined control sequence.
        self.assertNotIn("  " + chr(92) + "n**REPO:**", text)
        self.assertNotIn("  " + chr(92) + "n**FEDERATION:**", text)

    def test_document_stays_source_only(self):
        self.assertTrue(GLOSSARY.is_file())
        self.assertNotIn(chr(0), GLOSSARY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
