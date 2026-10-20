"""Tests for scripts/red_root_delta.py (CODE PURPLE red-root delta census).

Written with unittest assertion methods so the test file adds no Bandit
B101 findings to the repository-wide security scan.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess  # nosec B404 - test drives a throwaway local git repo
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "red_root_delta.py"
SPEC = importlib.util.spec_from_file_location("red_root_delta", SCRIPT)
red_root_delta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(red_root_delta)

GIT = shutil.which("git")


@unittest.skipIf(GIT is None, "git not available")
class RedRootDeltaTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self._git("init", "-q")
        self._git("config", "user.email", "ci@example.invalid")
        self._git("config", "user.name", "ci")
        (self.repo / "pkg").mkdir()
        self._write("pkg/old.py", "x = 1\n")
        self._write("pkg/touched.py", "y = 1\n")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "base")
        self._write("pkg/touched.py", "y = 2\n")
        self._write("pkg/new.py", "z = 1\n")
        self._write("README.md", "doc\n")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "pr")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _git(self, *args: str) -> None:
        subprocess.run(  # nosec B603 - fixed argv, shell=False
            [GIT, *args], cwd=self.repo, check=True, capture_output=True
        )

    def _write(self, rel: str, text: str) -> None:
        (self.repo / rel).write_text(text, encoding="utf-8")

    def _run(self, base: str | None, **logs: str) -> dict:
        out = self.tmp / "out.json"
        argv = ["--lane", "test", "--root", str(self.repo), "--out", str(out)]
        if base:
            argv += ["--base", base]
        for name, text in logs.items():
            path = self.tmp / f"{name}.txt"
            path.write_text(text, encoding="utf-8")
            argv += [f"--{name.replace('_', '-')}", str(path)]
        self.assertEqual(red_root_delta.main(argv), 0)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_changed_python_files_only_lists_python(self) -> None:
        changed = red_root_delta.changed_python_files(self.repo, "HEAD~1")
        self.assertEqual(changed, ["pkg/new.py", "pkg/touched.py"])

    def test_missing_base_reports_no_pr_context(self) -> None:
        payload = self._run("deadbeef", flake8_log="")
        self.assertFalse(payload["pr_context"])
        self.assertIsNone(payload["base"])
        self.assertIsNone(payload["touched_findings_upper_bound"])
        self.assertEqual(payload["touched_findings_qualification"], "NO_PR_CONTEXT")

    def test_black_and_isort_split_absolute_paths(self) -> None:
        root = self.repo.resolve().as_posix()
        black = (
            f"would reformat {root}/pkg/old.py\n"
            f"would reformat {root}/pkg/touched.py\n"
            f"error: cannot format {root}/pkg/new.py: Cannot parse: 1:6\n"
            "Oh no!\n"
        )
        isort = (
            f"ERROR: {root}/pkg/old.py Imports are incorrectly sorted "
            "and/or formatted.\n"
        )
        payload = self._run("HEAD~1", black_log=black, isort_log=isort)
        black_row = payload["tools"]["black"]
        self.assertEqual(black_row["files_total"], 2)
        self.assertEqual(black_row["files_on_touched"], ["pkg/touched.py"])
        self.assertEqual(black_row["files_elsewhere"], 1)
        self.assertEqual(black_row["parse_errors"]["files_on_touched"], ["pkg/new.py"])
        self.assertEqual(payload["tools"]["isort"]["files_on_touched"], [])
        self.assertEqual(payload["tools"]["isort"]["files_elsewhere"], 1)
        # touched.py reformat + new.py parse failure: parse errors count.
        self.assertEqual(payload["touched_findings_upper_bound"], 2)

    def test_black_parse_failure_alone_is_visible(self) -> None:
        root = self.repo.resolve().as_posix()
        black = f"error: cannot format {root}/pkg/new.py: Cannot parse: 1:6\n"
        summary = self.tmp / "summary.md"
        out = self.tmp / "parse.json"
        log = self.tmp / "black.log"
        log.write_text(black, encoding="utf-8")
        argv = ["--lane", "cq", "--root", str(self.repo), "--base", "HEAD~1"]
        argv += ["--black-log", str(log), "--out", str(out)]
        argv += ["--summary", str(summary)]
        self.assertEqual(red_root_delta.main(argv), 0)
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["touched_findings_upper_bound"], 1)
        text = summary.read_text(encoding="utf-8")
        self.assertIn("| black | 0 | 0 | 0 |", text)
        self.assertIn("| black parse errors | 1 | 1 | 0 |", text)

    def test_config_change_makes_attribution_indeterminate(self) -> None:
        self._write("pyproject.toml", "[tool.black]\nline-length = 60\n")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "config only")
        root = self.repo.resolve().as_posix()
        black = f"would reformat {root}/pkg/old.py\n"
        summary = self.tmp / "summary.md"
        out = self.tmp / "cfg.json"
        log = self.tmp / "black.log"
        log.write_text(black, encoding="utf-8")
        argv = ["--lane", "cq", "--root", str(self.repo), "--base", "HEAD~1"]
        argv += ["--black-log", str(log), "--out", str(out)]
        argv += ["--summary", str(summary)]
        self.assertEqual(red_root_delta.main(argv), 0)
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["attribution"], "indeterminate")
        self.assertEqual(payload["config_changes"], ["pyproject.toml"])
        self.assertEqual(payload["changed_python_files"], [])
        self.assertIsNone(payload["touched_findings_upper_bound"])
        self.assertEqual(payload["touched_findings_qualification"], "INDETERMINATE_CONFIG_CHANGE")
        text = summary.read_text(encoding="utf-8")
        self.assertIn("Attribution indeterminate", text)
        self.assertNotIn("Elsewhere (inherited)", text)

    def test_requirements_change_is_config(self) -> None:
        self.assertEqual(
            red_root_delta.config_changes(
                ["requirements-test.txt", "docs/a.md", "pkg/x.py", "setup.cfg"]
            ),
            ["requirements-test.txt", "setup.cfg"],
        )

    def test_deleted_python_file_is_not_touched(self) -> None:
        self._git("rm", "-q", "pkg/old.py")
        self._git("commit", "-q", "-m", "delete")
        changed = red_root_delta.changed_python_files(self.repo, "HEAD~1")
        self.assertEqual(changed, [])

    def test_flake8_and_bandit_rows(self) -> None:
        flake8 = (
            "./pkg/old.py:1:8: E999 SyntaxError: invalid syntax\n"
            "    def f(:\n"
            "./pkg/new.py:3:1: F821 undefined name 'q'\n"
            "1     E999 SyntaxError: invalid syntax\n"
            "2\n"
        )
        bandit = json.dumps(
            {
                "results": [
                    {
                        "filename": "./pkg/touched.py",
                        "line_number": 4,
                        "test_id": "B603",
                        "issue_severity": "LOW",
                    },
                    {
                        "filename": "./pkg/old.py",
                        "line_number": 9,
                        "test_id": "B310",
                        "issue_severity": "MEDIUM",
                    },
                ],
                "errors": [{"filename": "./pkg/old.py", "reason": "syntax"}],
            }
        )
        payload = self._run("HEAD~1", flake8_log=flake8, bandit_json=bandit)
        flake = payload["tools"]["flake8_critical"]
        self.assertEqual(flake["findings_total"], 2)
        self.assertEqual(
            flake["findings_on_touched"],
            [{"path": "pkg/new.py", "line": 3, "code": "F821"}],
        )
        sec = payload["tools"]["bandit"]
        self.assertEqual(sec["findings_total"], 2)
        self.assertEqual(
            [row["test_id"] for row in sec["findings_on_touched"]], ["B603"]
        )
        self.assertEqual(sec["parse_errors"]["files_elsewhere"], 1)
        self.assertEqual(payload["touched_findings_upper_bound"], 2)

    def test_missing_and_unparseable_inputs_do_not_fail(self) -> None:
        payload = self._run("HEAD~1", bandit_json="{not json")
        self.assertEqual(payload["tools"]["bandit"], {"status": "unparseable"})
        self.assertIsNone(payload["touched_findings_upper_bound"])
        out = self.tmp / "absent.json"
        argv = [
            "--lane",
            "x",
            "--root",
            str(self.repo),
            "--black-log",
            str(self.tmp / "absent.log"),
            "--out",
            str(out),
        ]
        self.assertEqual(red_root_delta.main(argv), 0)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["tools"]["black"], {"status": "not_run"})

    def test_valid_empty_scanner_is_qualified_zero(self) -> None:
        payload = self._run("HEAD~1", flake8_log="")
        self.assertEqual(payload["touched_findings_upper_bound"], 0)
        self.assertEqual(payload["touched_findings_qualification"], "QUALIFIED_INPUTS_ONLY")
        self.assertEqual(payload["incomplete_tools"], [])

    def test_absent_black_log_is_unknown_even_with_valid_flake8(self) -> None:
        out = self.tmp / "partial.json"
        empty = self.tmp / "valid_flake8.log"
        empty.write_text("", encoding="utf-8")
        argv = [
            "--lane", "mixed", "--root", str(self.repo),
            "--base", "HEAD~1",
            "--flake8-log", str(empty),
            "--black-log", str(self.tmp / "missing_black.log"),
            "--out", str(out),
        ]
        self.assertEqual(red_root_delta.main(argv), 0)
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertIsNone(payload["touched_findings_upper_bound"])
        self.assertEqual(payload["touched_findings_qualification"], "INCOMPLETE_SCANNER_INPUTS")
        self.assertEqual(payload["incomplete_tools"], ["black"])

    def test_unparseable_bandit_never_yields_verified_zero(self) -> None:
        payload = self._run("HEAD~1", bandit_json="{")
        self.assertIsNone(payload["touched_findings_upper_bound"])
        self.assertEqual(payload["touched_findings_qualification"], "INCOMPLETE_SCANNER_INPUTS")
        self.assertEqual(payload["incomplete_tools"], ["bandit"])

    def test_no_selected_scanners_is_unknown(self) -> None:
        payload = self._run("HEAD~1")
        self.assertIsNone(payload["touched_findings_upper_bound"])
        self.assertEqual(payload["touched_findings_qualification"], "NO_SCANNERS_SELECTED")

    def test_valid_positive_finding_retains_bound(self) -> None:
        payload = self._run(
            "HEAD~1",
            flake8_log="pkg/new.py:3:1: F821 undefined name 'missing'\\n",
        )
        self.assertEqual(payload["touched_findings_upper_bound"], 1)
        self.assertEqual(payload["touched_findings_qualification"], "QUALIFIED_INPUTS_ONLY")

    def test_unknown_bound_is_explicit_in_summary(self) -> None:
        payload = self._run("HEAD~1", bandit_json="{broken")
        summary = red_root_delta.summary_markdown(payload)
        self.assertIn("Qualified touched-file bound: **UNKNOWN**", summary)
        self.assertIn("INCOMPLETE_SCANNER_INPUTS", summary)
        self.assertNotIn("Qualified touched-file bound: **0**", summary)

    def test_summary_is_written_and_states_evidence_only(self) -> None:
        summary = self.tmp / "summary.md"
        log = self.tmp / "f.log"
        log.write_text("", encoding="utf-8")
        argv = [
            "--lane",
            "code-quality",
            "--root",
            str(self.repo),
            "--base",
            "HEAD~1",
            "--flake8-log",
            str(log),
            "--out",
            str(self.tmp / "s.json"),
            "--summary",
            str(summary),
        ]
        self.assertEqual(red_root_delta.main(argv), 0)
        text = summary.read_text(encoding="utf-8")
        self.assertIn("Red-root delta census — code-quality", text)
        self.assertIn("| flake8_critical | 0 | 0 | 0 |", text)
        self.assertIn("Elsewhere (inherited)", text)
        self.assertIn("does not change the enforcement verdict", text)


if __name__ == "__main__":
    unittest.main()
