"""EVERRED V3 offline KPI-leaf dashboard regression contracts."""

import re
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMPLATE = BASE / "dashboard" / "template.html"
BUILT = BASE / "dashboard" / "index.html"


class DashboardLeafContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TEMPLATE.read_text(encoding="utf-8")
        cls.built = BUILT.read_text(encoding="utf-8")

    def test_leaf_controls_exist_in_source_and_built(self):
        markers = (
            'id="gateRail"',
            'id="kpiFilter"',
            'id="kpiSearch"',
            'id="kpiViewCount"',
            'id="rootLeafCards"',
            'id="diagramLeafCards"',
            'id="pulseLeafCards"',
            'id="exportKpiBtn"',
            "function renderKpiLeaves()",
            "function renderRootLeaves(records)",
            "function renderPulseLeaves()",
        )
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)
                self.assertIn(marker, self.built)

    def test_template_generated_viewer_logic_same(self):
        for marker in (
            "function renderKpiLeaves()",
            "function renderGateRail(g,labels)",
            "function renderRootLeaves(records)",
            "function renderPulseLeaves()",
        ):
            with self.subTest(marker=marker):
                self.assertEqual(self.source.count(marker), 1)
                self.assertEqual(self.built.count(marker), 1)
        self.assertNotIn("@@SNAPSHOT@@", self.built)
        self.assertIn('id="bootstrap" type="application/json"', self.built)

    def test_unknown_and_scope_boundaries_remain_explicit(self):
        for guard in (
            "Number.isInteger(s.covered)",
            "Number.isInteger(s.eligible)",
            "UNTRUSTED LOCAL INPUT",
            "HISTORICAL SOURCE",
            "Trend unavailable:",
            "Baseline pulses hidden",
            "merge_admission",
            "NOT admission readiness",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, self.source)

    def test_architecture_tabs_not_deleted(self):
        self.assertIn("renderDiagram(0)", self.built)
        self.assertEqual(len(re.findall(r'data-tab="[0-4]"', self.source)), 5)
        self.assertIn('id="rootRows"', self.source)
        self.assertIn('id="diagramViewer"', self.source)


if __name__ == "__main__":
    unittest.main()
