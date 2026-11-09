"""Bounded, read-only contract tests for the Mission Control hub projection."""

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/code-purple-mcl-hub"


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.titles = 0
        self.scripts = []
        self.inside_script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "title":
            self.titles += 1
        if tag == "script":
            self.inside_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.inside_script = False

    def handle_data(self, value):
        if self.inside_script:
            self.scripts.append(value)


class HubContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads((HERE / "ledger.json").read_text(encoding="utf-8"))
        cls.html = (HERE / "index.html").read_text(encoding="utf-8")
        cls.doc = Inspect()
        cls.doc.feed(cls.html)

    def test_historical_runs_immutable_nonadmitting(self):
        self.assertEqual(
            [(x["run"], x["head_prefix"]) for x in self.ledger["immutable_history"]],
            [
                (38624410381, "d7740c7"),
                (38626368234, "c0f75f2"),
                (38627296781, "b344a4b"),
            ],
        )
        self.assertTrue(
            all(
                x["credit"] == "HISTORICAL_ONLY"
                for x in self.ledger["immutable_history"]
            )
        )
        self.assertEqual(self.ledger["merge_admission"], "HOLD")

    def test_artifact_bytes_are_distinct_from_portability(self):
        record = self.ledger["focus_pr"]
        self.assertEqual(
            (
                record["artifact_outputs_verified_historically"],
                record["artifact_outputs_attested"],
            ),
            (4, 4),
        )
        self.assertEqual(
            (
                record["extraction_path_direct_pass"],
                record["extraction_path_direct_total"],
            ),
            (0, 4),
        )
        self.assertIsNone(record["native_post_download_roundtrip"])

    def test_nullable_global_proofs_and_disjoint_lanes(self):
        self.assertEqual(len(self.ledger["regions"]), 3)
        self.assertEqual(len(set(self.ledger["planned_lane_ids"])), 3)
        self.assertIsNone(self.ledger["regions"][2]["packages_accepted"])
        self.assertIsNone(self.ledger["independent_workers_verified"])
        self.assertFalse(self.ledger["regions"][2]["codex_branch_protected"])

    def test_frozen_frontier_arithmetic_and_provenance(self):
        frontier = self.ledger["next_coverage_frontier"]
        self.assertEqual(frontier["frozen_uncovered"], 374)
        self.assertEqual(frontier["frozen_eligible"], 508)
        self.assertAlmostEqual(
            frontier["maximum_conditional_pp"], 100 * 374 / 52200, places=4
        )
        self.assertTrue(frontier["evidence_class"].startswith("HISTORICAL"))

    def test_html_controls_anchors_and_local_navigation(self):
        required = {
            "refresh",
            "refreshStatus",
            "prHead",
            "testflight",
            "artifact",
            "abacusRules",
            "codexRules",
            "stability",
        }
        self.assertEqual(len(self.doc.ids), len(set(self.doc.ids)))
        self.assertTrue(required.issubset(self.doc.ids))
        self.assertEqual(self.doc.titles, 1)
        for target in self.doc.links:
            if target.startswith("http"):
                self.assertTrue(target.startswith("https://github.com/"))
            else:
                self.assertTrue((HERE / target).resolve().is_file(), target)

    def test_read_only_no_tokens_and_no_admission_methods(self):
        self.assertEqual(len(self.doc.scripts), 1)
        script = self.doc.scripts[0]
        self.assertIn("A→B→A", script)
        self.assertIn("cache:'no-store'", script)
        self.assertIn("read('/repos/GBOGEB/CODEX/branches/main')", script)
        self.assertNotIn("Authorization:", script)
        self.assertNotIn("method:'POST'", script)
        self.assertNotIn("method:'PATCH'", script)
        self.assertIn("MERGE ADMISSION: HOLD", self.html)


if __name__ == "__main__":
    unittest.main()
