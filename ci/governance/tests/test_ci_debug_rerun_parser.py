"""Regression checks for the CI debug-rerun workflow's embedded pytest parser."""

import ast
import re
import textwrap
import unittest
from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "ci-failure-debug-rerun.yml"
)


def load_patterns():
    """Parse regex literals from the real workflow without executing its script."""
    yaml = WORKFLOW.read_text(encoding="utf-8")
    embedded = yaml.split("python - << 'PYEOF'", 1)[1].split(
        "\n          PYEOF", 1
    )[0]
    module = ast.parse(textwrap.dedent(embedded))
    patterns = {}
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "re"
            and call.func.attr == "search"
            and isinstance(call.args[0], ast.Constant)
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                patterns[target.id] = re.compile(call.args[0].value)
    return patterns


class DebugFailureParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = load_patterns()

    def test_all_expected_regexes_compile(self):
        self.assertEqual(
            set(self.patterns),
            {"nodeid_match", "file_line_match", "longrepr_match"},
        )

    def test_failed_pytest_report_is_detected(self):
        output = (
            'File "DMAIC_V3/tests/test_bridge.py", line 27, in test_case\n'
            "E   AssertionError: expected 2\n"
            "FAILED DMAIC_V3/tests/test_bridge.py::test_case - AssertionError\n"
        )
        self.assertEqual(
            self.patterns["nodeid_match"].search(output).group(1),
            "DMAIC_V3/tests/test_bridge.py::test_case",
        )
        self.assertEqual(
            self.patterns["file_line_match"].search(output).group(2), "27"
        )
        self.assertEqual(
            self.patterns["longrepr_match"].search(output).group(1),
            "AssertionError: expected 2",
        )

    def test_successful_pytest_report_has_no_false_failure(self):
        output = "================ 106 passed, 1 warning in 2.78s ================\n"
        for pattern in self.patterns.values():
            with self.subTest(pattern=pattern.pattern):
                self.assertIsNone(pattern.search(output))


if __name__ == "__main__":
    unittest.main()


def test_zz_g_ab_red_canary():
    """Throwaway red canary (method vector D); never merge."""
    assert False
