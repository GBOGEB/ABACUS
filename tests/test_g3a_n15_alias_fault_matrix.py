"""N15 cross-Python source-identical forward, reverse and negative import cases."""

import ast
import tempfile
import unittest
from pathlib import Path

from DMAIC_V3.phases.phase4_improve import CodeImprover


class N15SameSourceAliasControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.worker = CodeImprover(self.root)

    def apply(self, content):
        file = self.root / "probe.py"
        file.write_text(content, encoding="utf-8")
        status = self.worker.remove_unused_imports(file)
        actual = file.read_text(encoding="utf-8")
        ast.parse(actual)
        return status, actual

    def test_string_exports_keep_import_without_ast_load_name(self):
        _, text = self.apply('from math import floor\n__all__ = ["floor"]\n')
        self.assertIn("from math import floor", text)

    def test_eval_dynamic_reference_does_not_drop_import(self):
        _, text = self.apply("import math\nvalue = eval('math.floor(3.5)')\n")
        env = {}
        exec(text, env)
        self.assertEqual(env["value"], 3)

    def test_globals_dynamic_reference_does_not_drop_import(self):
        _, text = self.apply("import math\nvalue = globals()['math'].floor(3.5)\n")
        env = {}
        exec(text, env)
        self.assertEqual(env["value"], 3)

    def test_module_alias_reference_keeps_import(self):
        _, text = self.apply("import math as m\nvalue = m.floor(3.5)\n")
        env = {}
        exec(text, env)
        self.assertEqual(env["value"], 3)

    def test_nested_try_import_is_not_removed(self):
        _, text = self.apply(
            "try:\n    import math\nexcept ImportError:\n    math = None\n"
        )
        self.assertIn("    import math", text)

    def test_multiline_mixed_from_import_is_preserved(self):
        _, text = self.apply(
            "from math import (\n    sqrt,\n    floor,\n)\nvalue = floor(4.9)\n"
        )
        env = {}
        exec(text, env)
        self.assertEqual(env["value"], 4)

    def test_terminal_line_without_newline_is_preserved(self):
        status, text = self.apply("import math\nvalue = 7")
        self.assertTrue(status["success"])
        self.assertEqual(text, "value = 7")

    def test_batch_unused_imports_remove_once_then_idempotent(self):
        status, text = self.apply("import math\nimport json\nvalue = 7\n")
        self.assertTrue(status["success"])
        self.assertEqual(status["modifications"], 2)
        file = self.root / "probe.py"
        second = self.worker.remove_unused_imports(file)
        self.assertFalse(second["success"])
        self.assertEqual(file.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
