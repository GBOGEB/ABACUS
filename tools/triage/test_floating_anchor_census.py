import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("census", Path(__file__).with_name("floating_anchor_census.py"))
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)


class CensusTests(unittest.TestCase):
    def test_governance_directory_is_not_link_evidence(self):
        for prefix in ("triage", "federation", "architecture", "contracts"):
            self.assertFalse(census.linked_by_path(prefix + "/agent.py", "KEB"))

    def test_anchor_boundaries(self):
        self.assertTrue(census.linked_by_path("src/keb/keb_client.py", "KEB"))
        self.assertTrue(census.linked_by_path("agents/dow_extract.py", "DOW"))
        self.assertFalse(census.linked_by_path("window/agent.py", "DOW"))

    def test_embedded_versions(self):
        for prefix in ("ABACUS-v032", "tools_v2.3", "tracking_v2.3", "DMAIC_V3", "triage/vendor", "triage/w86_child_snapshot"):
            self.assertEqual(census.classify_path(prefix + "/agent.py"), "embedded_version_or_subrepo")

    def test_no_silent_truncation_or_credit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(45):
                (root / ("agent_%s.py" % i)).touch()
            report = census.build_report(root, "fixture", "KEB")
            self.assertEqual(len(report["floating_buckets"]["engine_like_unlinked"]["paths"]), 45)
            self.assertIsNone(report["totals"]["verified_linked_engine_like_files"])
            self.assertEqual(report["totals"]["engine_like_files"], report["totals"]["floating_engine_like_files"] + report["totals"]["anchor_named_engine_like_files"])


if __name__ == "__main__":
    unittest.main()

