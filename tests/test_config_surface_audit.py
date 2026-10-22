"""Synthetic regression tests for deep config and DAG syntax census."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "config_surface_audit",
    Path(__file__).resolve().parents[1] / "tools" / "triage"
    / "config_surface_audit.py",
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class ConfigSurfaceTest(unittest.TestCase):
    def test_yaml_workflow_on_remains_string(self):
        source = "name: build\non: pull_request\njobs:\n  a:\n    runs-on: ubuntu\n"
        kind, concerns = audit.check_text(".github/workflows/c.yml", source)
        self.assertEqual((kind, concerns), ("YAML", []))

    def test_yaml_duplicate_key_red(self):
        with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
            audit.check_text("c.yml", "a: 1\na: 2\n")

    def test_workflow_needs_dangling_red(self):
        source = "jobs:\n  a:\n    needs: missing\n    runs-on: ubuntu\n"
        with self.assertRaisesRegex(ValueError, "unknown workflow job"):
            audit.check_text(".github/workflows/x.yml", source)

    def test_workflow_cycle_red(self):
        source = "jobs:\n  a:\n    needs: b\n  b:\n    needs: a\n"
        with self.assertRaisesRegex(ValueError, "cyclic"):
            audit.check_text(".github/workflows/x.yml", source)

    def test_workflow_dynamic_is_unknown(self):
        source = "jobs:\n  a:\n    needs: '${{ matrix.target }}'\n"
        _, concerns = audit.check_text(".github/workflows/x.yml", source)
        self.assertEqual(concerns, ["DYNAMIC_JOB_NEEDS_NOT_RESOLVED"])

    def test_json_duplicate_key_red(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            audit.check_text("a.json", '{"a":1,"a":2}')

    def test_json_nonfinite_red(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            audit.check_text("a.json", '{"value":NaN}')

    def test_toml_duplicate_section_red(self):
        with self.assertRaises(Exception):
            audit.check_text("pyproject.toml", "[a]\nx = 1\n[a]\ny = 2\n")

    def test_ini_duplicate_section_red(self):
        with self.assertRaises(Exception):
            audit.check_text("pytest.ini", "[test]\na=1\n[test]\nb=2\n")

    def test_python_init_syntax_only(self):
        self.assertEqual(
            audit.check_text("pkg/__init__.py", "raise RuntimeError('not run')\n"),
            ("PYTHON_INIT", []),
        )
        with self.assertRaises(SyntaxError):
            audit.check_text("pkg/__init__.py", "def broken(:\n")

    def test_diagram_unverified_not_false_green(self):
        self.assertEqual(
            audit.check_text("diagram.mmd", "flowchart TD\n  A-->B\n")[1],
            ["NO_BUILTIN_MERMAID_SEMANTIC_PARSER"],
        )
        self.assertEqual(
            audit.check_text("diagram.dot", "digraph G { a -> b }")[1],
            ["EXTERNAL_DOT_VALIDATOR_NOT_EXECUTED"],
        )

    def test_bounded_population_and_missing_file(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "good.yaml").write_text("a: b\n", encoding="utf-8")
            (base / "bad.json").write_text('{"x": 1, "x": 2}', encoding="utf-8")
            result = audit.audit(
                base, ["good.yaml", "bad.json", "missing.toml"]
            )
            self.assertEqual(result["counts"]["SYNTAX_PASS"], 1)
            self.assertEqual(result["counts"]["SYNTAX_RED"], 2)
            self.assertIsNone(result["untracked_or_ignored_files"])

    def test_size_limit_fails_visible_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "long.json").write_text('{"long":"word"}', encoding="utf-8")
            result = audit.audit(base, ["long.json"], limit=5)
            self.assertEqual(result["counts"]["UNKNOWN_OVERSIZE"], 1)

    def test_duplicate_inventory_path_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "duplicate source"):
                audit.audit(Path(root), ["a.json", "a.json"])


if __name__ == "__main__":
    unittest.main()
