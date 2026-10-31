"""Guard: trailing-whitespace must keep Markdown two-space hard breaks.

U16 (#2505) normalised trailing whitespace repo-wide without
``--markdown-linebreak-ext=md`` and stripped the hard breaks that
tests/test_pandoc_glossary_source.py relies on.
"""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".pre-commit-config.yaml"


def _hook(hook_id):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            if hook.get("id") == hook_id:
                return hook
    raise AssertionError("hook not configured: " + hook_id)


class PrecommitMarkdownHardBreaks(unittest.TestCase):
    def test_trailing_whitespace_preserves_markdown_hard_breaks(self):
        args = _hook("trailing-whitespace").get("args", [])
        self.assertIn("--markdown-linebreak-ext=md", args)


if __name__ == "__main__":
    unittest.main()
