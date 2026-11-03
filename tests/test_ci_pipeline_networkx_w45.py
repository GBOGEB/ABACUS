"""W45: fail-closed NetworkX collection dependency contract for legacy CI."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-pipeline.yml"
DEV_REQUIREMENTS = ROOT / "requirements-dev.txt"


class NetworkXUnitCIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.unit_job = cls.workflow.split("  unit-tests:", 1)[1].split(
            "\n  integration-tests:", 1
        )[0]
        cls.requirements = DEV_REQUIREMENTS.read_text(encoding="utf-8")

    def test_unit_matrix_is_python_311(self):
        self.assertRegex(self.unit_job, r"python-version:\s*\['3\.11'\]")

    def test_graph_pin_matches_development_contract(self):
        match = re.search(
            r'^networkx==(\S+); python_version >= "3\.11"$',
            self.requirements,
            re.MULTILINE,
        )
        self.assertIsNotNone(match)
        self.assertIn(
            'python -m pip install "networkx==' + match.group(1) + '"',
            self.unit_job,
        )

    def test_required_install_does_not_swallow_failure(self):
        self.assertIn("python -m pip install -r requirements.txt", self.unit_job)
        self.assertNotIn("|| echo", self.unit_job)
        self.assertIn("set -euo pipefail", self.unit_job)

    def test_import_preflight_precedes_pytest(self):
        install = self.unit_job.index('python -m pip install "networkx==')
        preflight = self.unit_job.index("python -c 'import networkx;")
        execute = self.unit_job.index("pytest --benchmark-disable tests/")
        self.assertLess(install, preflight)
        self.assertLess(preflight, execute)


if __name__ == "__main__":
    unittest.main()
