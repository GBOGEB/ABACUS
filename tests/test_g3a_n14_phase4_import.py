"""N14 source-owner regression specification for mixed/aliased imports.

Tests only temporary files. A failing pre-repair test demonstrates a specific
behavioral red, not root admission. A source repair must pass all old tests.
"""
import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

from DMAIC_V3.phases.phase4_improve import CodeImprover


class N14AliasSafeImportRepair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.worker = CodeImprover(self.root)

    def transform(self, source):
        path = self.root / "fixture.py"
        path.write_text(source, encoding="utf-8")
        result = self.worker.remove_unused_imports(path)
        rendered = path.read_text(encoding="utf-8")
        ast.parse(rendered)
        return result, rendered, path

    def test_mixed_from_import_must_preserve_used_binding(self):
        _, text, path = self.transform("from math import sqrt, floor\nvalue = floor(3.2)\n")
        self.assertIn("from math import", text)
        namespace = {}
        exec(compile(text, str(path), "exec"), namespace)
        self.assertEqual(namespace["value"], 3)

    def test_alias_from_import_must_preserve_used_alias(self):
        _, text, path = self.transform("from math import sqrt as root, floor as down\nvalue = down(3.2)\n")
        namespace = {}
        exec(compile(text, str(path), "exec"), namespace)
        self.assertEqual(namespace["value"], 3)

    def test_mixed_import_must_preserve_used_module(self):
        _, text, path = self.transform("import math, json\nvalue = math.floor(3.2)\n")
        namespace = {}
        exec(compile(text, str(path), "exec"), namespace)
        self.assertEqual(namespace["value"], 3)

    def test_aliased_import_must_preserve_used_alias(self):
        _, text, path = self.transform("import json as serializer, math as unused\nvalue = serializer.dumps({'a': 1})\n")
        namespace = {}
        exec(compile(text, str(path), "exec"), namespace)
        self.assertIn('"a": 1', namespace["value"])

    def test_simple_unused_import_is_removed(self):
        result, text, _ = self.transform("import math\nvalue = 2\n")
        self.assertTrue(result["success"])
        self.assertNotIn("import math", text)
        self.assertIn("value = 2", text)

    def test_simple_unused_from_import_is_removed(self):
        result, text, _ = self.transform("from math import sqrt\nvalue = 2\n")
        self.assertTrue(result["success"])
        self.assertNotIn("from math import", text)

    def test_future_import_is_always_retained(self):
        _, text, _ = self.transform("from __future__ import annotations\nvalue = 2\n")
        self.assertIn("from __future__ import annotations", text)

    def test_star_import_is_not_changed_by_guessing(self):
        _, text, _ = self.transform("from math import *\nvalue = 2\n")
        self.assertIn("from math import *", text)

    def test_side_by_side_statements_are_not_broken(self):
        _, text, path = self.transform("import math; value = 7\n")
        namespace = {}
        exec(compile(text, str(path), "exec"), namespace)
        self.assertEqual(namespace["value"], 7)

    def test_annotated_import_statement_is_preserved(self):
        _, text, _ = self.transform("import math  # review: side effects\nvalue = 2\n")
        self.assertIn("import math", text)

    def test_nested_import_is_not_erased_by_global_heuristic(self):
        _, text, path = self.transform("def f():\n    import math\n    return 2\n")
        namespace = {}
        exec(compile(text, str(path), "exec"), namespace)
        self.assertEqual(namespace["f"](), 2)
        self.assertIn("    import math", text)

    def test_invalid_python_fails_without_mutating_file(self):
        path = self.root / "invalid.py"
        source = "from math import sqrt,\n"
        path.write_text(source, encoding="utf-8")
        result = self.worker.remove_unused_imports(path)
        self.assertFalse(result["success"])
        self.assertEqual(path.read_text(encoding="utf-8"), source)

    def test_reverse_regression_and_second_pass_are_idempotent(self):
        source = "from math import sqrt, floor\nvalue = floor(3.2)\n"
        _, first, path = self.transform(source)
        second = self.worker.remove_unused_imports(path)
        self.assertFalse(second["success"])
        self.assertEqual(first, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
