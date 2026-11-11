"""Regression: unified CD Ubuntu installs canonical graph test requirements."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "cd-unified.yml"
DEV_DEPS = ROOT / "requirements-dev.txt"
INSTALL = "python -m pip install -r requirements-dev.txt"


def ubuntu_job() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    matched = re.search(
        r"(?ms)^  ci-ubuntu:\s*\n(?P<body>.*?)(?=^  [A-Za-z][A-Za-z0-9_-]*:\s*\n|\Z)",
        text,
    )
    if matched is None:
        raise AssertionError("cd-unified.yml has no ci-ubuntu job")
    return matched.group("body")


class UnifiedCdCollection(unittest.TestCase):
    def test_graph_test_ssot_precedes_pytest(self):
        body = ubuntu_job()
        self.assertIn(INSTALL, body)
        self.assertIn("pytest --benchmark-disable -v --cov=. --cov-report=term-missing", body)
        self.assertLess(body.index(INSTALL),
                        body.index("pytest --benchmark-disable"))

    def test_networkx_is_source_owned_not_hardcoded(self):
        deps = DEV_DEPS.read_text(encoding="utf-8")
        self.assertIn("-r requirements.txt", deps)
        self.assertIn('networkx==3.6.1; python_version >= "3.11"', deps)
        self.assertNotIn("pip install networkx==", ubuntu_job())

    def test_no_testing_shortcut(self):
        body = ubuntu_job()
        self.assertNotIn("continue-on-error: true", body)
        self.assertNotIn("pytest --benchmark-disable -v --cov=. --cov-report=term-missing || true", body)


if __name__ == "__main__":
    unittest.main()
