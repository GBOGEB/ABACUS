"""Tests for tools/quality_pilot/pilot_summary.py (report-only quality pilot)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pilot_summary", ROOT / "tools" / "quality_pilot" / "pilot_summary.py"
)
ps = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ps)


@pytest.fixture()
def reports(tmp_path: Path) -> Path:
    d = tmp_path / "reports"
    d.mkdir()
    (d / "mypy.txt").write_text(
        'models/a.py:10: error: Item "None" of "Any | None" has no attribute "get"  [union-attr]\n'
        "models/a.py:11: note: this is a note and must be ignored\n"
        'models/b.py:3: error: Incompatible return value type  [return-value]\n',
        encoding="utf-8",
    )
    (d / "mypy-focus.txt").write_text(
        'models/a.py:10: error: Item "None" of "Any | None" has no attribute "get"  [union-attr]\n',
        encoding="utf-8",
    )
    (d / "gitleaks.json").write_text(
        json.dumps([{"RuleID": "github-pat", "File": "ci/env.sh", "StartLine": 3,
                     "Description": "GitHub PAT", "Commit": "abcdef123456"}]),
        encoding="utf-8",
    )
    (d / "opengrep.json").write_text(
        json.dumps({"results": [{"check_id": "rules.eos-call-outside-adapter",
                                 "path": "qplant/x.py", "start": {"line": 7},
                                 "extra": {"message": "direct PropsSI", "severity": "WARNING"}}]}),
        encoding="utf-8",
    )
    (d / "code-scanning.json").write_text(
        json.dumps([{"tool": {"name": "CodeQL"}, "rule": {"id": "py/clear-text-logging"},
                     "most_recent_instance": {"location": {"path": "src/x.py", "start_line": 4},
                                              "message": {"text": "logs a secret"}}}]),
        encoding="utf-8",
    )
    (d / "timings.csv").write_text("mypy,12,1,mypy 2.3.1\ngitleaks,30,0,gitleaks 8\n", encoding="utf-8")
    return d


def test_collect_normalises_all_sources(reports: Path) -> None:
    tools = sorted(f["tool"] for f in ps.collect(reports))
    assert tools == ["codeql", "gitleaks", "mypy", "mypy", "mypy-focus", "opengrep"]


def test_code_scanning_error_payload_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "code-scanning.json").write_text(json.dumps({"message": "403"}), encoding="utf-8")
    assert ps.parse_code_scanning(tmp_path) == []


def test_summarize_writes_telemetry_sample_and_dedupes_hotspots(reports: Path) -> None:
    ps.main(["summarize", str(reports), "--run", "4", "--phase", "burn-in"])
    tel = json.loads((reports / "telemetry.json").read_text(encoding="utf-8"))
    assert tel["run"] == "4" and tel["phase"] == "burn-in"
    assert tel["tools"]["mypy"]["findings"] == 2
    assert tel["tools"]["mypy"]["seconds"] == 12 and tel["tools"]["mypy"]["exit_code"] == 1
    summary = (reports / "summary.md").read_text(encoding="utf-8")
    assert "`models/a.py` (1)" in summary  # mypy + mypy-focus same line counted once
    rows = list(csv.DictReader((reports / "triage_sample.csv").open(encoding="utf-8")))
    assert len(rows) == 6


def test_trend_classifies_direction(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    files = []
    for run, n in [(1, 10), (2, 12), (3, 15)]:
        p = tmp_path / f"t{run}.json"
        p.write_text(json.dumps({"run": str(run), "tools": {"mypy": {"findings": n}}}), encoding="utf-8")
        files.append(str(p))
    ps.main(["trend", *files])
    assert "rising — investigate" in capsys.readouterr().out


def test_score_gates_security_hit_immediately(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "triaged.csv"
    p.write_text(
        "id,tool,rule,file,line,message,verdict(TP/FP/NOISE/WONTFIX),minutes,notes\n"
        "F1,gitleaks,github-pat,ci/env.sh,3,PAT,TP,4,\n"
        "F2,mypy,union-attr,models/a.py,10,x,FP,2,\n",
        encoding="utf-8",
    )
    ps.main(["score", str(p)])
    out = capsys.readouterr().out
    assert "GATE now" in out and "too few samples" in out
