"""Deterministic offline UI, canonical stage, and anti-admission contracts."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_mission_cycle import build

SOURCE = ROOT / "data/bd_queue_20261014.json"
TEMPLATE = ROOT / "dashboard/mission_cycle_template.html"
OUTPUT = ROOT / "dashboard/mission_cycle.html"
SCRIPT = ROOT / "dashboard/mission_cycle.js"


class MissionCycleHTML(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bd = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.template = TEMPLATE.read_text(encoding="utf-8")

    def test_committed_file_is_identical_to_canonical_builder(self):
        first = build(self.bd, self.template)
        self.assertEqual(first, build(self.bd, self.template))
        self.assertEqual(first, OUTPUT.read_text(encoding="utf-8"))

    def test_no_fake_model_or_unlock_credit(self):
        generated = build(self.bd, self.template)
        doc = generated.split('<script id="guidance" type="application/json">', 1)[1]
        doc = doc.split("</script>", 1)[0]
        guidance = json.loads(doc)
        self.assertEqual(guidance["stages"], [
            "Mission", "Wave", "Pulse", "Receipt", "Reallocate", "Recurse"
        ])
        self.assertFalse(guidance["merge_authorized"])
        self.assertTrue(guidance["cards"])
        for row in guidance["cards"].values():
            self.assertIsNone(row["unlock_yield_pct"])
            self.assertIsNone(row["bt_rank"])
            self.assertEqual(row["admission"], "HOLD")

    def test_missing_duplicate_marker_and_wrong_source_rejected(self):
        for source in (self.template.replace("@@GUIDANCE_JSON@@", ""),
                       self.template + "@@GUIDANCE_JSON@@"):
            with self.subTest(source_len=len(source)):
                with self.assertRaisesRegex(ValueError, "marker"):
                    build(self.bd, source)
        bad = dict(self.bd, disposition="ADMIT")
        with self.assertRaisesRegex(ValueError, "authority"):
            build(bad, self.template)

    def test_clickable_single_action_and_offline_boundary(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('p.addEventListener("click"', script)
        self.assertIn('name.addEventListener("click"', script)
        self.assertIn("Why this ranks", script)
        self.assertIn("What it unblocks", script)
        self.assertIn("Next action", script)
        self.assertIn('"Pending", "Yes", "No"', script)
        self.assertIn("DRAFT_NOT_SUBMITTED", script)
        self.assertIn('admission: "HOLD"', script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("XMLHttpRequest", script)
        self.assertIn("script-src 'self'", self.template)
        self.assertIn('class="legend"', self.template)
        self.assertIn('id="cycle"', self.template)


if __name__ == "__main__":
    unittest.main()
