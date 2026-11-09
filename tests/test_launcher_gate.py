"""Offline tests for scripts/launcher_gate.py using fixture workflows in a temp checkout."""

from __future__ import annotations

import datetime as dt
import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("launcher_gate", ROOT / "scripts" / "launcher_gate.py")
lg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lg)

TODAY = dt.date(2026, 11, 9)

MISSING = """
name: legacy launcher
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Run inventory scan
        run: |
          pip install -r requirements.txt || true
          python runners/dmaic_runner.py --action inventory
"""

CD_OK = """
name: cd into live dir
on: [push]
env:
  APP_ROOT: app
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Run from subdir
        run: |
          cd ${{ env.APP_ROOT }}
          python main.py
          bash ./tools/run.sh
          cd ..
          python -m app.cli --help
      - name: Working directory
        working-directory: app
        run: python main.py
"""

CD_MISSING = """
on:
  push:
    branches: [main]
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: |
          cd 13_CORE_SYSTEMS/DMAIC
          python run.py
"""

TOLERATED = """
on:
  workflow_run:
    workflows: [x]
    types: [completed]
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/checkout@v7
        with:
          repository: GBOGEB/CODEX
          path: codex
      - name: child checkout, expressions, heredoc, venv, redirects, arrays
        run: |
          python codex/scripts/x.py
          python ${{ github.event.inputs.script }}
          python "$SCRIPT"
          python - <<'PY'
          print("scripts/not_a_launch.py")
          PY
          python3 -m venv .venv
          source .venv/bin/activate
          echo "x" > generated-reqs.txt
          pip install -r generated-reqs.txt
          FILES=(
            "missing/a.py"
          )
          python -c "import os"
          python -m pytest tests
          cd "$RUNNER_TEMP"
          python whatever.py
"""

PR_ONLY = """
on: pull_request
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: python does/not/exist.py
"""


def make_checkout(d: Path) -> Path:
    wf = d / ".github" / "workflows"
    wf.mkdir(parents=True)
    (d / "app" / "cli").mkdir(parents=True)
    (d / "app" / "main.py").write_text("")
    (d / "app" / "tools").mkdir()
    (d / "app" / "tools" / "run.sh").write_text("")
    (d / "app" / "cli" / "__init__.py").write_text("")
    (d / "requirements.txt").write_text("")
    for name, body in {
        "missing.yml": MISSING,
        "cd-ok.yml": CD_OK,
        "cd-missing.yml": CD_MISSING,
        "tolerated.yml": TOLERATED,
        "pr-only.yml": PR_ONLY,
    }.items():
        (wf / name).write_text(textwrap.dedent(body))
    return d


class LauncherGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_checkout(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def gate(self, exceptions: str | None = None):
        exc = self.root / "ledger" / "launcher_exceptions.yaml"
        if exceptions is not None:
            exc.parent.mkdir(exist_ok=True)
            exc.write_text(exceptions)
        rep = lg.run_gate(self.root, exc, TODAY)
        return rep, {r["workflow"].rsplit("/", 1)[-1]: r for r in rep["results"]}

    def test_missing_script_flagged(self):
        _, by = self.gate()
        f = by["missing.yml"]["findings"]
        self.assertEqual([x["resolved"] for x in f], ["runners/dmaic_runner.py"])
        self.assertEqual(f[0]["kind"], "python")

    def test_cd_into_existing_dir_resolves(self):
        _, by = self.gate()
        self.assertEqual(by["cd-ok.yml"]["findings"], [])

    def test_cd_into_missing_dir_flagged_once(self):
        _, by = self.gate()
        f = by["cd-missing.yml"]["findings"]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["kind"], "cd")
        self.assertEqual(f[0]["resolved"], "13_CORE_SYSTEMS/DMAIC")

    def test_no_false_positives_on_tolerated_patterns(self):
        _, by = self.gate()
        self.assertEqual(by["tolerated.yml"]["findings"], [])
        reasons = " ".join(s["reason"] for s in by["tolerated.yml"]["skipped"])
        self.assertIn("dynamic", reasons)
        self.assertIn("unresolvable cd", reasons)

    def test_pull_request_only_workflow_not_gated(self):
        rep, by = self.gate()
        self.assertNotIn("pr-only.yml", by)
        self.assertEqual(rep["workflows_scanned"], 5)
        self.assertEqual(rep["workflows_gated"], 4)
        self.assertEqual(rep["workflows_flagged"], 2)

    def test_exception_suppresses_and_expires(self):
        rep, _ = self.gate(
            "exceptions:\n"
            "  - workflow: missing.yml\n    reason: bridge in progress\n    owner_decision_ref: BD-16\n    expires: 2026-12-31\n"
            "  - workflow: .github/workflows/cd-missing.yml\n    reason: old\n    owner_decision_ref: x\n    expires: 2026-01-01\n"
        )
        self.assertEqual(rep["excepted"], [".github/workflows/missing.yml"])
        self.assertEqual(rep["expired_exceptions"], [".github/workflows/cd-missing.yml"])
        self.assertEqual(rep["workflows_flagged"], 1)

    def test_empty_exceptions_file_and_report_only_exit(self):
        out = self.root / "gate.json"
        rc = lg.main(["--root", str(self.root), "--out", str(out), "--today", "2026-11-09"])
        self.assertEqual(rc, 0)
        self.assertIn('"mode": "report-only"', out.read_text())

    def test_repo_exceptions_file_parses(self):
        excepted, expired = lg.load_exceptions(ROOT / "ledger" / "launcher_exceptions.yaml", TODAY)
        self.assertEqual((excepted, expired), ({}, []))


if __name__ == "__main__":
    unittest.main()
