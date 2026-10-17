"""Fail-closed contract for shared root-conftest pytest prerequisites."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "everred-v3-validation.yml"
CONFTEST = ROOT / "tests" / "conftest.py"


class EVERREDPytestDependencies(unittest.TestCase):
    def test_root_conftest_import_is_accounted_for(self):
        self.assertIn("import numpy as np", CONFTEST.read_text(encoding="utf-8"))
        self.assertIn(
            "numpy==1.26.4",
            WORKFLOW.read_text(encoding="utf-8"),
        )

    def test_black_and_isort_share_one_canonical_profile(self):
        config = (ROOT / "tools" / "everred_v3" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('[tool.isort]\nprofile = "black"\n', config)
        self.assertIn("line_length = 88", config)
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("black==26.10.1 isort==9.0.2", workflow)
        self.assertIn("python -m black --check src scripts tests", workflow)
        self.assertIn("python -m isort --check-only src scripts tests", workflow)

    def test_all_python_versions_share_same_dependency_step(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python-version: ['3.10', '3.12']", workflow)
        self.assertIn(
            "python -m pytest -q ../../tests/test_bd_ldab_join_census.py", workflow
        )
        self.assertIn("jsonschema==4.25.1 pytest numpy==1.26.4", workflow)


if __name__ == "__main__":
    unittest.main()
