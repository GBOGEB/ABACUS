"""Smoke: build a fixture folder and run the tidy-plan pathway on it (inventory -> probe -> scaffold -> moveplan).

Successor of the local runner's ``smoke`` (S1-S9), calling the engines directly. The PowerShell dry run of the
move plan is a separate step of the binary-engines workflow, which re-checks S9 after it.
"""

from __future__ import annotations

import json
import unittest

from tests.binary_engines import _env, _fixtures

STEPS = (
    ("estate_inventory", ("--root-id", "SMOKE")),
    ("estate_probe", ("--root-id", "SMOKE")),
    ("estate_scaffold", ()),
    ("estate_moveplan", ("--root-id", "SMOKE")),
)
OUTPUTS = (  # declared outputs of each step, relative to the SMOKE inventory folder or to ESTATE_HOME
    "{inv}/root_inventory.json",
    "{inv}/root_inventory.csv",
    "{inv}/zip_reverse_kahn.json",
    "{inv}/SUMMARY.md",
    "{inv}/probe/content_reclass.json",
    "{inv}/root_inventory_final.json",
    "ENGINES_INDEX.md",
    "graph/estate_graph.json",
    "{inv}/MOVE_PLAN.csv",
)


def _jsonl(path):
    return [
        json.loads(line) for line in path.read_text("utf-8").split("\n") if line.strip()
    ]


class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _env.require(*_env.DEPS)
        _env.require_kernels()
        spec = _env.engine("estate_spec")
        cls.fixture = spec.ROOTS["SMOKE"][0]
        cls.names = _fixtures.build_smoke(cls.fixture)
        cls.inv = spec.inv_dir("SMOKE")
        cls.results = {name: _env.run_main(name, *args) for name, args in STEPS}
        inv = cls.inv
        cls.rows = {
            r["name"]: r
            for r in json.loads((inv / "root_inventory.json").read_text("utf-8"))[
                "rows"
            ]
        }
        cls.zips = {
            z["name"]: z
            for z in json.loads((inv / "zip_reverse_kahn.json").read_text("utf-8"))[
                "zips"
            ]
        }
        cls.pptx = _jsonl(inv / "probe" / "PPTX.jsonl")
        cls.docx = _jsonl(inv / "probe" / "DOCX.jsonl")

    def test_s1_every_step_passes_with_its_outputs(self):
        for name, (code, out) in self.results.items():
            with self.subTest(step=name):
                self.assertEqual(code, 0, out[-2000:])
        home = _env.HOME
        rel = self.inv.relative_to(home).as_posix()
        for output in OUTPUTS:
            with self.subTest(output=output):
                self.assertTrue((home / output.format(inv=rel)).is_file())

    def test_s2_ten_types_seen(self):
        self.assertEqual(len({r["type"] for r in self.rows.values()}), 10)

    def test_s3_epics_by_name(self):
        n, epics = self.names, self.names["epics"]
        self.assertEqual(self.rows[n["xlsx"]]["epic"], epics[0])
        self.assertEqual(self.rows[n["pptx"]]["epic"], epics[1])
        self.assertEqual(self.rows[n["pdf"]]["epic"], epics[2])
        self.assertEqual(self.rows[n["md"]]["epic"], epics[3])

    def test_s4_duplicate_detected(self):
        self.assertEqual(self.rows[self.names["md_copy"]]["decision_hint"], "DUPLICATE")

    def test_s5_zip_v1_superseded_by_v2(self):
        self.assertEqual(self.zips[self.names["zip_v1"]]["kahn_layer"], 1)
        self.assertEqual(self.zips[self.names["zip_v2"]]["kahn_layer"], 0)
        self.assertEqual(self.zips[self.names["zip_v1"]]["zip_status"], "SUPERSEDED")

    def test_s6_pptx_text_box_and_bound_connector(self):
        self.assertGreaterEqual(self.pptx[0]["total_text_boxes"], 1)
        self.assertEqual(self.pptx[0]["connector_edges_bound"], 1)

    def test_s7_docx_outline_bullet_and_number_levels(self):
        facts = self.docx[0]
        self.assertTrue(facts["outline_levels"])
        self.assertIn("bullet", facts["num_formats"])
        self.assertIn("decimal", facts["num_formats"])

    def test_s8_move_plan_written(self):
        plan = (self.inv / "MOVE_PLAN.csv").read_text("utf-8").splitlines()
        self.assertEqual(len(plan), 1 + len(self.rows))
        self.assertTrue(plan[0].startswith("action,src,dest"))

    def test_s9_fixture_untouched(self):
        self.assertEqual(len(list(self.fixture.iterdir())), _fixtures.SMOKE_FILES)

    def test_untracked_outside_a_repository(self):
        if _env.engine("git_readonly").find_repo(self.fixture) is not None:
            self.skipTest("the test folder lies inside a git work tree on this machine")
        self.assertFalse(any(r["git_tracked"] for r in self.rows.values()))
        self.assertEqual(
            json.loads((self.inv / "root_inventory.json").read_text("utf-8"))[
                "git_head"
            ],
            "",
        )


if __name__ == "__main__":
    unittest.main()
