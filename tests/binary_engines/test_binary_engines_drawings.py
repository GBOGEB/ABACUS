"""Drawings and decks end to end: deep_graph (geometry kernel) and slide_atlas (similarity kernel).

The decks are written into the MI root of the example configuration (the parent of ESTATE_HOME), inventoried,
probed and scaffolded like any root, then read by the two engines.
"""

from __future__ import annotations

import json
import shutil
import unittest

from tests.binary_engines import _env, _fixtures

WORDS = (
    "the feed line carries cold gas from the storage tank to the pump skid and back through the return "
    "header while the bypass valve stays closed during normal operation of the loop"
)


class DecksAndDrawings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _env.require(*_env.DEPS)
        _env.require_kernels()
        cls.root = _env.BASE
        cls.deck_a = cls.root / "loop_overview_a.pptx"
        cls.deck_b = cls.root / "loop_overview_b.pptx"
        cls.deck_c = cls.root / "loop_overview_c.pptx"
        _fixtures.build_deck(cls.deck_a, "loop A", WORDS)
        shutil.copy(cls.deck_a, cls.deck_b)  # the same slide pasted into another deck
        _fixtures.build_deck(
            cls.deck_c,
            "loop A",
            WORDS.replace("operation of the loop", "operation of the plant"),
        )
        cls.steps = [
            _env.run_main("estate_inventory", "--root-id", "MI"),
            _env.run_main("estate_probe", "--root-id", "MI", "--types", "PPTX"),
            _env.run_main("estate_scaffold"),
            _env.run_main("slide_atlas"),
        ]
        cls.atlas = json.loads(
            (_env.HOME / "deep" / "slide_atlas.json").read_text("utf-8")
        )

    def test_steps_pass(self):
        for code, out in self.steps:
            self.assertEqual(code, 0, out[-2000:])

    def test_copies_and_edits_are_found_across_decks(self):
        kinds = {p["kind"] for p in self.atlas["pairs"] if not p["same_deck"]}
        self.assertIn("EXACT_COPY", kinds)
        self.assertIn("EDITED", kinds)
        self.assertEqual(len(self.atlas["decks"]), 3)

    def test_one_family_with_two_versions(self):
        families = self.atlas["families"]
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["decks"], 3)
        self.assertEqual(len(families[0]["versions"]), 2)

    def test_bound_connector_is_a_deferred_candidate_link(self):
        dg = _env.engine("deep_graph")
        g = dg.read_pptx(self.deck_a)
        bound = [e for e in g["edges"] if e["how"] == "bound"]
        self.assertEqual(len(bound), 1)
        self.assertEqual(bound[0]["evidence"], "FILE_CONNECTED")
        self.assertEqual(
            bound[0]["semantic_type"],
            "DEFER",
            "no legend and no registry: the meaning is not guessed",
        )
        atoms = dg.keb_candidates(g)
        self.assertEqual(len(atoms), 1)
        self.assertIn("P-101", atoms[0]["statement"])
        self.assertIn("T-201", atoms[0]["statement"])
        self.assertEqual(atoms[0]["validation_result"], "UNVALIDATED")

    def test_root_mode_writes_a_summary(self):
        code, out = _env.run_main("deep_graph", "--root-id", "MI")
        self.assertEqual(code, 0, out[-2000:])
        self.assertTrue((_env.HOME / "deep" / "DEEP_SUMMARY_MI.json").is_file())


if __name__ == "__main__":
    unittest.main()
