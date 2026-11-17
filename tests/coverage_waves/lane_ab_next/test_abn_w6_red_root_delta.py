"""Behaviour tests for scripts/red_root_delta.py (git mocked)."""

import json
from argparse import Namespace
from types import SimpleNamespace

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/red_root_delta.py", name="abn_w6_red_root_delta")


def _git(monkeypatch, verify_rc=0, diff_rc=0, diff_out=""):
    calls = []

    def fake_run(cmd, cwd=None, capture_output=False, text=False, check=False):
        calls.append(cmd)
        if cmd[1] == "rev-parse":
            return SimpleNamespace(returncode=verify_rc, stdout="", stderr="")
        return SimpleNamespace(returncode=diff_rc, stdout=diff_out, stderr="")

    monkeypatch.setattr(mod.shutil, "which", lambda name: "git")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return calls


def _args(root, **kw):
    base = dict(
        root=str(root),
        base=None,
        lane="lane-x",
        black_log=None,
        isort_log=None,
        flake8_log=None,
        bandit_json=None,
    )
    base.update(kw)
    return Namespace(**base)


def test_normalise_strips_root_dot_and_backslashes(tmp_path):
    root_text = tmp_path.resolve().as_posix()
    assert mod.normalise(" " + root_text + "/pkg/a.py ", tmp_path) == "pkg/a.py"
    assert mod.normalise("././pkg/b.py", tmp_path) == "pkg/b.py"
    assert mod.normalise("pkg\\c.py", tmp_path) == "pkg/c.py"


def test_changed_files_no_base_and_no_git(tmp_path, monkeypatch):
    assert mod.changed_files(tmp_path, None) is None
    assert mod.changed_files(tmp_path, "") is None
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.changed_files(tmp_path, "main") is None


def test_changed_files_verify_fails(tmp_path, monkeypatch):
    calls = _git(monkeypatch, verify_rc=1)
    assert mod.changed_files(tmp_path, "main") is None
    assert calls[0][-1] == "main^{commit}"
    assert len(calls) == 1


def test_changed_files_diff_fails(tmp_path, monkeypatch):
    _git(monkeypatch, diff_rc=128)
    assert mod.changed_files(tmp_path, "main") is None


def test_changed_files_sorted_unique(tmp_path, monkeypatch):
    calls = _git(monkeypatch, diff_out="b.py\n\n a.py \nb.py\n")
    assert mod.changed_files(tmp_path, "main") == ["a.py", "b.py"]
    assert calls[1][1:] == ["diff", "--name-only", "main", "HEAD"]


def test_changed_python_files_filters_existing(tmp_path, monkeypatch):
    (tmp_path / "keep.py").write_bytes(b"x = 1\n")
    (tmp_path / "stub.pyi").write_bytes(b"x: int\n")
    _git(monkeypatch, diff_out="keep.py\nstub.pyi\ngone.py\nREADME.md\n")
    assert mod.changed_python_files(tmp_path, "main") == ["keep.py", "stub.pyi"]
    assert mod.changed_python_files(tmp_path, None) is None


def test_config_changes():
    paths = ["pyproject.toml", "src/a.py", "requirements-dev.txt", "x/.flake8"]
    assert mod.config_changes(paths) == ["pyproject.toml", "requirements-dev.txt"]


def test_read_helper(tmp_path):
    assert mod._read(None) is None
    assert mod._read(tmp_path / "missing.log") is None
    log = tmp_path / "l.log"
    log.write_bytes(b"hello\n")
    assert mod._read(log) == "hello\n"


def test_census_black(tmp_path):
    assert mod.census_black(None, tmp_path, None) == {"status": "not_run"}
    text = "\n".join(
        [
            "would reformat a.py",
            "would reformat ./b.py  ",
            "error: cannot format c.py: Cannot parse",
            "All done!",
        ]
    )
    res = mod.census_black(text, tmp_path, {"a.py", "c.py"})
    assert res["status"] == "parsed"
    assert res["files_total"] == 2
    assert res["files_on_touched"] == ["a.py"]
    assert res["files_elsewhere"] == 1
    assert res["parse_errors"]["files_on_touched"] == ["c.py"]
    no_ctx = mod.census_black(text, tmp_path, None)
    assert no_ctx["files_on_touched"] == []
    assert no_ctx["files_elsewhere"] == 2


def test_census_isort(tmp_path):
    assert mod.census_isort(None, tmp_path, set()) == {"status": "not_run"}
    text = "ERROR: x.py Imports are incorrectly sorted and/or formatted.\nok\n"
    res = mod.census_isort(text, tmp_path, {"x.py"})
    assert res == {
        "status": "parsed",
        "files_total": 1,
        "files_on_touched": ["x.py"],
        "files_elsewhere": 0,
    }


def test_census_flake8(tmp_path):
    assert mod.census_flake8(None, tmp_path, set()) == {"status": "not_run"}
    text = "a.py:3:1: F821 undefined name 'x'\nnoise\nb.pyi:10:5: E999 bad\n"
    res = mod.census_flake8(text, tmp_path, {"a.py"})
    assert res["findings_total"] == 2
    assert res["findings_on_touched"] == [dict(path="a.py", line=3, code="F821")]
    assert res["findings_elsewhere"] == 1
    assert mod.census_flake8(text, tmp_path, None)["findings_on_touched"] == []


def test_census_bandit(tmp_path):
    assert mod.census_bandit(None, tmp_path, set()) == {"status": "not_run"}
    assert mod.census_bandit("{not json", tmp_path, set()) == {"status": "unparseable"}
    report = {
        "results": [
            {
                "filename": "./a.py",
                "line_number": 4,
                "test_id": "B602",
                "issue_severity": "HIGH",
            },
            {"filename": "z.py", "line_number": 1},
        ],
        "errors": [{"filename": "a.py"}, {"filename": "q.py"}],
    }
    res = mod.census_bandit(json.dumps(report), tmp_path, {"a.py"})
    assert res["findings_total"] == 2
    assert res["findings_on_touched"][0]["test_id"] == "B602"
    assert res["findings_elsewhere"] == 1
    assert res["parse_errors"]["files_on_touched"] == ["a.py"]
    empty = mod.census_bandit("{}", tmp_path, None)
    assert empty["findings_total"] == 0
    assert empty["findings_on_touched"] == []


def test_touched_count_variants():
    assert mod.touched_count({"findings_on_touched": [1, 2]}) == 2
    assert mod.touched_count({"files_on_touched": ["a"]}) == 1
    tool = {"files_on_touched": ["a"], "parse_errors": {"files_on_touched": ["b"]}}
    assert mod.touched_count(tool) == 2
    assert mod.touched_count({}) == 0


def test_build_payload_no_pr_context(tmp_path):
    payload = mod.build_payload(_args(tmp_path))
    assert payload["attribution"] == "no_pr_context"
    assert payload["touched_findings_qualification"] == "NO_PR_CONTEXT"
    assert payload["touched_findings_upper_bound"] is None
    assert payload["base"] is None
    assert payload["tools"] == {}


def test_build_payload_config_change(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_bytes(b"x = 1\n")
    _git(monkeypatch, diff_out="a.py\nsetup.cfg\n")
    payload = mod.build_payload(_args(tmp_path, base="main"))
    assert payload["attribution"] == "indeterminate"
    assert payload["config_changes"] == ["setup.cfg"]
    assert payload["touched_findings_qualification"] == "INDETERMINATE_CONFIG_CHANGE"
    assert payload["base"] == "main"


def test_build_payload_no_scanners(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_bytes(b"x = 1\n")
    _git(monkeypatch, diff_out="a.py\n")
    payload = mod.build_payload(_args(tmp_path, base="main"))
    assert payload["attribution"] == "attributable"
    assert payload["touched_findings_qualification"] == "NO_SCANNERS_SELECTED"


def test_build_payload_incomplete_and_qualified(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_bytes(b"x = 1\n")
    _git(monkeypatch, diff_out="a.py\n")
    black = tmp_path / "black.log"
    black.write_bytes(b"would reformat a.py\n")
    isort = tmp_path / "isort.log"
    isort.write_bytes(b"ERROR: a.py Imports are incorrectly sorted\n")
    flake = tmp_path / "flake.log"
    flake.write_bytes(b"a.py:1:1: F821 undefined name\n")
    bandit = tmp_path / "bandit.json"
    bandit.write_bytes(json.dumps({"results": [{"filename": "a.py"}]}).encode())
    payload = mod.build_payload(
        _args(
            tmp_path,
            base="main",
            black_log=black,
            isort_log=isort,
            flake8_log=flake,
            bandit_json=bandit,
        )
    )
    assert payload["touched_findings_qualification"] == "QUALIFIED_INPUTS_ONLY"
    assert payload["touched_findings_upper_bound"] == 4
    assert payload["incomplete_tools"] == []
    payload2 = mod.build_payload(
        _args(tmp_path, base="main", black_log=tmp_path / "missing.log")
    )
    assert payload2["touched_findings_qualification"] == "INCOMPLETE_SCANNER_INPUTS"
    assert payload2["incomplete_tools"] == ["black"]
    assert payload2["touched_findings_upper_bound"] is None


def test_summary_markdown_no_pr_context():
    payload = {
        "lane": "L",
        "attribution": "no_pr_context",
        "tools": {
            "black": {"status": "not_run"},
            "flake8_critical": {
                "status": "parsed",
                "findings_total": 3,
                "findings_on_touched": [],
                "findings_elsewhere": 3,
            },
        },
    }
    md = mod.summary_markdown(payload)
    assert "No pull-request base available" in md
    assert "| black | not_run | – | – |" in md
    assert "| flake8_critical | 3 | – | 3 |" in md
    assert "**UNKNOWN** (UNKNOWN)" in md
    assert "| Elsewhere |" in md


def test_summary_markdown_attributable_and_indeterminate():
    tool = {
        "status": "parsed",
        "files_total": 2,
        "files_on_touched": ["a.py"],
        "files_elsewhere": 1,
        "parse_errors": {
            "files_total": 0,
            "files_on_touched": [],
            "files_elsewhere": 0,
        },
    }
    payload = {
        "lane": "L",
        "attribution": "attributable",
        "changed_python_files": ["a.py"],
        "config_changes": [],
        "tools": {"black": tool},
        "touched_findings_upper_bound": 1,
        "touched_findings_qualification": "QUALIFIED_INPUTS_ONLY",
    }
    md = mod.summary_markdown(payload)
    assert "PR-changed Python files: **1**" in md
    assert "Elsewhere (inherited)" in md
    assert "| black | 2 | 1 | 1 |" in md
    assert "| black parse errors | 0 | 0 | 0 |" in md
    assert "**1** (QUALIFIED_INPUTS_ONLY)" in md
    payload.update(attribution="indeterminate", config_changes=["tox.ini"])
    md2 = mod.summary_markdown(payload)
    assert "**Attribution indeterminate:** this PR changes `tox.ini`" in md2
    assert "Elsewhere (inherited)" not in md2


def test_main_writes_json_and_summary(tmp_path, capsys):
    out = tmp_path / "o" / "delta.json"
    summary = tmp_path / "summary.md"
    summary.write_bytes(b"prior\n")
    rc = mod.main(
        [
            "--lane",
            "lint",
            "--root",
            str(tmp_path),
            "--out",
            str(out),
            "--summary",
            str(summary),
        ]
    )
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["lane"] == "lint"
    assert data["schema"] == mod.SCHEMA
    text = summary.read_text(encoding="utf-8")
    assert text.startswith("prior")
    assert "Red-root delta census — lint" in text
    assert "Red-root delta census — lint" in capsys.readouterr().out


def test_main_without_summary(tmp_path, capsys):
    out = tmp_path / "delta.json"
    assert mod.main(["--lane", "x", "--root", str(tmp_path), "--out", str(out)]) == 0
    assert out.is_file()
    assert "Qualified touched-file bound" in capsys.readouterr().out
