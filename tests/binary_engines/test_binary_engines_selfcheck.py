"""Self-check of the binary engines: structure, configuration and code, without reading any file.

Successor of the local runner's ``selfsmoke`` for the engines alone (the runner and its registry stay local):
code/data separation, the example configuration, types, lanes, the E0-E9 DAG, the capability matrix, that every
engine compiles and imports, the gates in the mover, and the public-safety scan itself (positive and negative).
"""

from __future__ import annotations

import graphlib
import importlib.util
import os
import re
import unittest
from pathlib import Path

from tests.binary_engines import _env


class CodeAndData(unittest.TestCase):
    def setUp(self):
        _env.require("yaml")
        self.spec = _env.engine("estate_spec")

    def test_estate_home_is_outside_the_repository(self):
        self.assertEqual(self.spec.ESTATE, _env.HOME)
        self.assertNotIn(_env.REPO, [self.spec.ESTATE, *self.spec.ESTATE.parents])
        self.assertEqual(self.spec.CODE_DIR, _env.CODE)

    def test_estate_home_inside_the_repository_is_refused(self):
        spec = importlib.util.spec_from_file_location(
            "estate_spec_inside_probe", _env.CODE / "estate_spec.py"
        )
        module = importlib.util.module_from_spec(spec)
        old = os.environ["ESTATE_HOME"]
        os.environ["ESTATE_HOME"] = str(_env.REPO / "estate_outputs")
        try:
            with self.assertRaisesRegex(RuntimeError, "inside the repository"):
                spec.loader.exec_module(module)
        finally:
            os.environ["ESTATE_HOME"] = old

    def test_code_folder_holds_no_outputs(self):
        dirs = sorted(
            p.name
            for p in _env.CODE.iterdir()
            if p.is_dir() and p.name != "__pycache__"
        )
        self.assertEqual(
            dirs, [], "outputs belong under ESTATE_HOME, never next to the code"
        )
        allowed = {".py", ".ps1", ".yaml", ".md"}
        self.assertEqual(
            sorted(
                p.name
                for p in _env.CODE.iterdir()
                if p.is_file() and p.suffix not in allowed
            ),
            [],
        )

    def test_example_configuration_is_loaded(self):
        self.assertTrue(self.spec.CONFIG_IS_EXAMPLE)
        self.assertEqual(self.spec.CONFIG_PATH, _env.EXAMPLE_CONFIG)
        ids = [e[0] for e in self.spec.EPICS]
        self.assertGreaterEqual(len(ids), 4, "the smoke fixture needs four epics")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(self.spec.PERSONAL_TOKENS)
        self.assertTrue(self.spec.CONFIG.get("private_markers"))
        self.assertIsNone(
            self.spec.legend_registry(), "no owner registry in a fresh ESTATE_HOME"
        )


class Structure(unittest.TestCase):
    def setUp(self):
        _env.require("yaml")
        self.spec = _env.engine("estate_spec")

    def test_types_are_unique(self):
        letters = [t[0] for t in self.spec.TYPES]
        codes = [t[1] for t in self.spec.TYPES]
        exts = [e for t in self.spec.TYPES for e in t[2]]
        for values in (letters, codes, exts):
            self.assertEqual(len(values), len(set(values)))
        self.assertEqual(len(self.spec.EXT_TO_TYPE), len(exts))

    def test_dag_is_acyclic_and_closed(self):
        ids = [step for step, _, _ in self.spec.DAG]
        self.assertEqual(len(ids), len(set(ids)))
        lanes = {lane for lane, _ in self.spec.LANES}
        for step, needs, lane in self.spec.DAG:
            with self.subTest(step=step):
                self.assertTrue(set(needs) <= set(ids), f"{step} needs an unknown step")
                self.assertIn(lane, lanes)
        order = list(
            graphlib.TopologicalSorter(
                {s: n for s, n, _ in self.spec.DAG}
            ).static_order()
        )
        self.assertEqual(order[0], "E0_DISCOVER")
        self.assertEqual(order[-1], "E9_RECEIPT_RELEASE")

    def test_every_root_has_a_known_depth(self):
        for rid, (_, depth) in self.spec.ROOTS.items():
            with self.subTest(root=rid):
                self.assertIn(depth, self.spec.DEPTH)
        self.assertEqual(
            self.spec.ROOTS["SMOKE"][0], _env.HOME / "fixtures" / "smoke_root"
        )
        self.assertNotIn("SMOKE", self.spec.REAL_ROOTS)

    def test_decision_hints_are_declared(self):
        used = {
            "KEEP_CANONICAL",
            "PARK",
            "SUPERSEDED",
            "DUPLICATE",
            "STALE_ARCHIVE",
            "ACTIVATE_ZIP",
        }
        self.assertTrue(used <= set(self.spec.DECISIONS))

    def test_capability_matrix_is_complete(self):
        scaffold = _env.engine("estate_scaffold")
        for _, code, _, _ in self.spec.TYPES:
            with self.subTest(type=code):
                caps = scaffold.CAPS[code]
                self.assertEqual(set(caps), set(self.spec.CAPABILITIES))
                statuses = {status for status, _ in caps.values()}
                allowed = {"now", "planned", "na"}
                self.assertEqual(statuses - allowed, set())


class Code(unittest.TestCase):
    def test_every_engine_compiles_and_is_311_safe(self):
        _env.require("yaml")
        scan = _env.engine("public_safety_scan")
        for path in sorted(_env.CODE.glob("*.py")):
            with self.subTest(file=path.name):
                source = path.read_text("utf-8")
                compile(source, str(path), "exec")
                self.assertEqual(
                    scan.fstring_312_only(source),
                    [],
                    "f-string that only parses on 3.12+",
                )

    def test_cli_engines_answer_help(self):
        _env.require("yaml")
        for name in (
            "estate_inventory",
            "estate_probe",
            "estate_moveplan",
            "thread_promote",
            "truth_status",
        ):
            with self.subTest(engine=name):
                code, out = _env.run_main(name, "--help")
                self.assertEqual(code, 0)
                self.assertIn("usage", out.lower())

    def test_mover_is_a_dry_run_unless_execute(self):
        ps1 = (_env.CODE / "Invoke-EstateMove.ps1").read_text("utf-8")
        self.assertIn("[switch]$Execute", ps1)
        self.assertIn("$env:ESTATE_HOME", ps1)
        moves = [
            line for line in ps1.splitlines() if "Move-Item" in line and "$dst" in line
        ]
        self.assertEqual(len(moves), 1)
        before = ps1[: ps1.index(moves[0])]
        self.assertGreater(
            before.rfind("if ($Execute)"), before.rfind("foreach ($r in $plan)")
        )
        self.assertIn("'DRY RUN'", ps1)

    def test_legend_template_accepts_nothing(self):
        _env.require("yaml")
        import yaml

        template = yaml.safe_load(
            (_env.CODE / "LEGEND_REGISTRY.example.yaml").read_text("utf-8")
        )
        self.assertEqual(template["accepted"], [])


class PublicSafetyScan(unittest.TestCase):
    def setUp(self):
        _env.require("yaml")

    def test_engine_code_is_clean(self):
        files = [str(p) for p in sorted(_env.CODE.glob("*.py"))] + [
            str(_env.CODE / "Invoke-EstateMove.ps1")
        ]
        code, out = _env.run_main("public_safety_scan", *files)
        self.assertEqual(code, 0, out)
        self.assertNotIn("HOLD", out)

    def test_scan_holds_markers_paths_and_secrets(self):
        probe = _env.BASE / "scan_probe"
        probe.mkdir(parents=True, exist_ok=True)
        user_path = (
            "C:" + "\\Users\\" + "someone\\notes"
        )  # built at run time so this file stays clean
        token = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2"
        cases = {
            "marker.md": "mentions EXAMPLE_PRIVATE_WORD here\n",
            "path.md": f"see {user_path}\n",
            "secret.md": f"token {token}\n",
            "fstring.py": "y = f\"{'\\n'.join(['a'])}\"\n",  # backslash inside a replacement field: 3.12+ only
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                target = probe / name
                target.write_text(text, "utf-8")
                code, out = _env.run_main("public_safety_scan", str(target))
                self.assertEqual(code, 1, out)
                self.assertTrue(re.search(r"^HOLD", out, re.M), out)


if __name__ == "__main__":
    unittest.main()
