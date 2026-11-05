"""W45: fail-closed NetworkX collection dependency contract for legacy CI."""

import json
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

    def test_unit_matrix_is_single_ssot_default_at_or_above_networkx_floor(self):
        # Single-cell matrix on the SSOT default (ssot/python_versions.yaml);
        # networkx==3.6.1 is the Python >= 3.11 pin, so the cell must stay >= 3.11.
        default = json.loads(
            (ROOT / "ssot" / "python_versions.lanes.json").read_text(encoding="utf-8")
        )["default"]
        match = re.search(r"python-version:\s*\['(3\.\d+)'\]", self.unit_job)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), default)
        self.assertGreaterEqual(tuple(map(int, default.split("."))), (3, 11))

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
