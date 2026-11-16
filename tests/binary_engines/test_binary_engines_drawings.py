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


@_env.gated(*_env.DEPS, kernels=True)
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

    def test_same_basename_in_two_dirs_keeps_two_graphs(self):
        """Same basename under two directories: outputs and locators stay root-qualified, nothing overwritten."""
        twin_dir = self.root / "twin_dir"
        twin_dir.mkdir(exist_ok=True)
        twin = twin_dir / self.deck_a.name
        shutil.copy(self.deck_a, twin)
        dg = _env.engine("deep_graph")
        before = set((_env.HOME / "deep").glob("loop_overview_a.*.pptx.graph.json"))
        code, out = _env.run_main("deep_graph", str(self.deck_a), str(twin))
        self.assertEqual(code, 0, out[-2000:])
        made = set((_env.HOME / "deep").glob("loop_overview_a.*.pptx.graph.json"))
        keys = {dg.source_key(self.deck_a), dg.source_key(twin)}
        self.assertEqual(len(keys), 2)
        self.assertGreaterEqual(len(made - before) + len(before & made), 2)
        locs = set()
        for gf in made:
            g = json.loads(gf.read_text("utf-8"))
            locs |= {n["locator"].split("#", 1)[0] for n in g["nodes"]}
        self.assertTrue(keys <= locs, (keys, locs))

    def test_reader_runs_once_per_drawing(self):
        dg = _env.engine("deep_graph")
        calls = []
        real = dg.READERS[".pptx"]

        def counting(path):
            calls.append(path)
            return real(path)

        dg.READERS[".pptx"] = counting
        try:
            code, out = _env.run_main("deep_graph", str(self.deck_a))
        finally:
            dg.READERS[".pptx"] = real
        self.assertEqual(code, 0, out[-2000:])
        self.assertEqual(len(calls), 1)

    def test_root_mode_writes_a_summary(self):
        code, out = _env.run_main("deep_graph", "--root-id", "MI")
        self.assertEqual(code, 0, out[-2000:])
        self.assertTrue((_env.HOME / "deep" / "DEEP_SUMMARY_MI.json").is_file())


# Canonical pytest has a fail-closed skipped-test taxonomy (_env.gated marks the
# actual blocker).  Under the standalone unittest binary-engines workflow, missing
# prerequisites are failures (BINARY_ENGINES_REQUIRE_DEPS=1); no pytest is required.
if __name__ == "__main__":
    unittest.main()
