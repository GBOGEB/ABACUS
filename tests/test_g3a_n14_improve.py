"""N14 Phase 4 improvement heuristics; mutations stay in toy temporary files."""
import ast
import tempfile
import unittest
from pathlib import Path
from DMAIC_V3.phases.phase4_improve import CodeImprover

class Phase4BranchFlight(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.worker=CodeImprover(self.root)
    def source(self,name,code):
        p=self.root/name
        p.write_text(code,encoding="utf-8")
        return p
    def test_missing_function_docstring_is_inserted(self):
        p=self.source("f.py","def f():\n    return 2\n")
        r=self.worker.add_missing_docstrings(p)
        self.assertTrue(r["success"])
        self.assertIsNotNone(ast.get_docstring(ast.parse(p.read_text()).body[0]))
    def test_existing_docstrings_are_unchanged(self):
        code='def f():\n    """Existing."""\n    return 1\n'
        p=self.source("f.py",code)
        self.assertFalse(self.worker.add_missing_docstrings(p)["success"])
        self.assertEqual(p.read_text(),code)
    def test_type_hints_skip_init_and_add_method(self):
        p=self.source("m.py","class T:\n    def __init__(self):\n        pass\n    def run(self):\n        return 2\n")
        r=self.worker.add_type_hints(p)
        self.assertTrue(r["success"])
        tree=ast.parse(p.read_text())
        methods={x.name:x for x in tree.body[-1].body if isinstance(x,ast.FunctionDef)}
        self.assertIsNone(methods["__init__"].returns)
        self.assertEqual(methods["run"].returns.id,"Any")
    def test_annotated_function_is_idempotent(self):
        code="def f() -> int:\n    return 1\n"
        p=self.source("f.py",code)
        self.assertFalse(self.worker.add_type_hints(p)["success"])
        self.assertEqual(p.read_text(),code)
    def test_invalid_source_never_rewritten_by_ast_mutators(self):
        p=self.source("bad.py","def f(:\n    return 1\n")
        before=p.read_bytes()
        for call in (self.worker.add_missing_docstrings,self.worker.add_type_hints,self.worker.remove_unused_imports):
            result=call(p)
            self.assertFalse(result["success"])
            self.assertIn("error",result)
            self.assertEqual(p.read_bytes(),before)
    def test_long_comma_line_exercises_formatting(self):
        p=self.source("long.py","values = 1, 2, 3, 4, 5, 6\n")
        r=self.worker.fix_long_lines(p,max_length=12)
        self.assertTrue(r["success"])
        self.assertIn("values = 1,",p.read_text())
    def test_long_comment_is_not_modified(self):
        code="#"+"x"*90+"\n"
        p=self.source("comment.py",code)
        self.assertFalse(self.worker.fix_long_lines(p,max_length=20)["success"])
        self.assertEqual(p.read_text(),code)
    def test_live_import_is_preserved(self):
        code="import math\nvalue=math.sqrt(9)\n"
        p=self.source("live.py",code)
        self.assertFalse(self.worker.remove_unused_imports(p)["success"])
        self.assertEqual(p.read_text(),code)
    def test_dead_import_lines_are_removed(self):
        p=self.source("dead.py","import math\nimport json\nvalue=5\n")
        result=self.worker.remove_unused_imports(p)
        self.assertTrue(result["success"])
        self.assertEqual(p.read_text(),"value=5\n")
    def test_missing_file_fails_closed(self):
        p=self.root/"missing.py"
        for call in (self.worker.add_missing_docstrings,self.worker.add_type_hints,self.worker.fix_long_lines,self.worker.remove_unused_imports):
            result=call(p)
            self.assertFalse(result["success"])
            self.assertIn("error",result)
        self.assertFalse(p.exists())
if __name__=="__main__":
    unittest.main()
