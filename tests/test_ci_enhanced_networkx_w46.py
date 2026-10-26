"""W46: prevent repeat networkx collection failures in enhanced CI."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-enhanced.yml"
DEV = ROOT / "requirements-dev.txt"


class EnhancedCICollectionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = WORKFLOW.read_text(encoding="utf-8")
        cls.jobs = {}
        for name in ("test-ubuntu", "test-rhel-8", "test-rhel-9"):
            match = re.search(r"(?ms)^  " + re.escape(name) + r":\n(.*?)(?=^  [\w-]+:\n|\Z)", source)
            if match is None:
                raise AssertionError("missing job " + name)
            cls.jobs[name] = match.group(1)
        cls.dev = DEV.read_text(encoding="utf-8")

    def test_pinned_graph_dependency_owned_by_dev_requirements(self):
        self.assertRegex(self.dev, r'(?m)^networkx==[\d.]+; python_version >= "3\.11"$')
        self.assertIn("-r requirements.txt", self.dev)

    def test_all_root_pytest_jobs_install_graph_dependency(self):
        for name, body in self.jobs.items():
            with self.subTest(job=name):
                self.assertIn("python -m pip install -r requirements-dev.txt", body)
                self.assertNotIn("pip install -r requirements.txt\n", body)

    def test_all_jobs_preflight_before_pytest(self):
        for name, body in self.jobs.items():
            with self.subTest(job=name):
                install = body.index("python -m pip install -r requirements-dev.txt")
                preflight = body.index("python -c 'import networkx;")
                pytest = body.index("pytest", preflight)
                self.assertLess(install, preflight)
                self.assertLess(preflight, pytest)

    def test_all_jobs_fail_closed(self):
        for name, body in self.jobs.items():
            with self.subTest(job=name):
                self.assertRegex(body, r"set -e(?:u|x|o| )*")
                self.assertNotIn("|| true", body)
                self.assertNotIn("|| echo", body)

    def test_ubuntu_cache_tracks_graph_pin(self):
        self.assertIn("hashFiles('requirements*.txt')", WORKFLOW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
