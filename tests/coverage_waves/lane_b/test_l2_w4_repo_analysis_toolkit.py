"""Lane-B wave 4: repo_analysis_toolkit classifier and lineage tracer.

Git calls are replaced with fakes so the tests never shell out.
"""

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from ._l2_loader import load

ca = load("repo_analysis_toolkit/classify_artifacts.py")
gl = load("repo_analysis_toolkit/generate_lineage.py")


def _iso(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%d %H:%M:%S %z"
    )


# --- classify_artifacts helpers ---------------------------------------------------


def test_load_config(tmp_path, monkeypatch):
    assert ca.load_config(None) == {}
    cfg = tmp_path / "c.yaml"
    cfg.write_text("classification:\n  active_age_days: 5\n", encoding="utf-8")
    assert ca.load_config(str(cfg)) == {"classification": {"active_age_days": 5}}
    empty = tmp_path / "e.yaml"
    empty.write_text("", encoding="utf-8")
    assert ca.load_config(str(empty)) == {}
    monkeypatch.setattr(ca, "yaml", None)
    assert ca.load_config(str(cfg)) == {}


def test_git_last_commit_parses_output(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(stdout=" 2026-01-02 03:04:05 +0000 | Ada Lovelace \n")

    monkeypatch.setattr(ca.subprocess, "run", fake_run)
    assert ca.git_last_commit(tmp_path, "a.py") == (
        "2026-01-02 03:04:05 +0000",
        "Ada Lovelace",
    )
    assert calls[0][-2:] == ["--", "a.py"]
    monkeypatch.setattr(
        ca.subprocess, "run", lambda cmd, **kw: SimpleNamespace(stdout="\n")
    )
    assert ca.git_last_commit(tmp_path, "a.py") == ("", "")


def test_sha1_of(tmp_path):
    f = tmp_path / "f.txt"
    f.write_bytes(b"abc")
    assert ca.sha1_of(f) == "a9993e364706816aba3e25717850c26c9cd0d89d"
    assert ca.sha1_of(tmp_path / "missing") == ""


def test_days_since():
    assert ca.days_since("") == -1
    assert ca.days_since(_iso(3)) == 3
    assert ca.days_since("2000-01-01T00:00:00") > 9000
    assert ca.days_since("not a date") == -1


def test_is_corrupted(tmp_path, monkeypatch):
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    assert ca.is_corrupted(empty, 0)
    good = tmp_path / "ok.json"
    good.write_text('{"a": 1}', encoding="utf-8")
    assert not ca.is_corrupted(good, good.stat().st_size)
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    assert ca.is_corrupted(bad, bad.stat().st_size)
    text = tmp_path / "a.md"
    text.write_text("# hi", encoding="utf-8")
    assert not ca.is_corrupted(text, 4)
    assert ca.is_corrupted(tmp_path / "gone.png", 10)
    png = tmp_path / "x.png"
    png.write_bytes(b"")
    # A non-zero declared size with an empty header is still a broken image.
    assert ca.is_corrupted(png, 10)


# --- classify_artifacts.classify ------------------------------------------------------


def _tree(tmp_path):
    repo = tmp_path / "repo"
    (repo / "node_modules").mkdir(parents=True)
    (repo / "node_modules" / "skip.js").write_text("x", encoding="utf-8")
    (repo / "skipme").mkdir()
    (repo / "skipme" / "x.txt").write_text("x", encoding="utf-8")
    files = {
        "new.txt": ("same", 1),
        "copy.txt": ("same", 400),
        "mid.txt": ("mid", 200),
        "old.txt": ("old", 500),
        "ancient.txt": ("ancient", 1000),
        "untracked.txt": ("untracked", None),
        "empty.txt": ("", 1),
        "empty2.txt": ("", 2),
    }
    ages = {}
    for name, (content, age) in files.items():
        (repo / name).write_text(content, encoding="utf-8")
        ages[name] = age
    return repo, ages


def _fake_git(ages):
    def fake(repo, rel):
        age = ages.get(rel)
        return ("", "") if age is None else (_iso(age), "dev")

    return fake


def _read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return {row["path"]: row for row in csv.DictReader(handle)}


def test_classify_tags_and_dedup(tmp_path, monkeypatch, capsys):
    repo, ages = _tree(tmp_path)
    monkeypatch.setattr(ca, "git_last_commit", _fake_git(ages))
    out = tmp_path / "reports" / "c.csv"
    cfg = {
        "classification": {"stale_age_days": 730},
        "exclude_patterns": ["**/skipme/**", "*.tmp"],
    }
    rc = ca.classify(SimpleNamespace(repo=str(repo), out=str(out), dedup=True), cfg)
    assert rc == 0
    rows = _read(out)
    assert set(rows) == set(ages)
    assert rows["new.txt"]["tag"] == "Active"
    assert rows["copy.txt"]["tag"] == "Redundant"
    assert rows["mid.txt"]["tag"] == "Archived"
    assert rows["old.txt"]["tag"] == "Stale" and rows["old.txt"]["confidence"] == "0.8"
    assert rows["ancient.txt"]["confidence"] == "0.9"
    assert (
        rows["untracked.txt"]["tag"] == "Active"
        and rows["untracked.txt"]["age_days"] == "-1"
    )
    # Zero-byte duplicates stay Corrupted rather than being re-tagged Redundant.
    assert rows["empty.txt"]["tag"] == rows["empty2.txt"]["tag"] == "Corrupted"
    output = capsys.readouterr().out
    assert "(8 rows)" in output and "Redundant        1" in output


def test_classify_without_dedup_and_empty_repo(tmp_path, monkeypatch):
    repo, ages = _tree(tmp_path)
    monkeypatch.setattr(ca, "git_last_commit", _fake_git(ages))
    out = tmp_path / "plain.csv"
    assert ca.main(["--repo", str(repo), "--out", str(out)]) == 0
    rows = _read(out)
    assert rows["copy.txt"]["tag"] == "Stale" and rows["copy.txt"]["sha1"] == ""
    blank = tmp_path / "blank"
    blank.mkdir()
    empty_out = tmp_path / "empty.csv"
    assert ca.main(["--repo", str(blank), "--out", str(empty_out)]) == 0
    assert empty_out.read_text(encoding="utf-8").startswith("path,size_bytes,age_days")


def test_classify_rejects_missing_repo(tmp_path, capsys):
    assert (
        ca.main(["--repo", str(tmp_path / "nope"), "--out", str(tmp_path / "x.csv")])
        == 2
    )
    assert "is not a directory" in capsys.readouterr().err


# --- generate_lineage --------------------------------------------------------------


def _git_outputs(tags="", branches="", log=""):
    def fake(repo, *args):
        if args[0] == "for-each-ref" and args[-1] == "refs/tags":
            return tags
        if args[0] == "for-each-ref":
            return branches
        return log

    return fake


def test_git_wrapper(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return SimpleNamespace(stdout="out")

    monkeypatch.setattr(gl.subprocess, "run", fake_run)
    assert gl.git(tmp_path, "status") == "out"
    assert seen["cmd"] == ["git", "-C", str(tmp_path), "status"]


def test_collect_tags_branches_history(monkeypatch, tmp_path):
    monkeypatch.setattr(
        gl,
        "git",
        _git_outputs(
            tags="v1|2026-01-01 00:00:00 +0000|abc\n\nv2|2026-02-01 00:00:00 +0000|def\n",
            branches="\n".join(
                [
                    "main|" + _iso(1) + "|dev",
                    "old|" + _iso(400) + "|dev",
                    "naive|2000-01-01T00:00:00|dev",
                    "baddate|yesterday|dev",
                    "nodate||dev",
                    "short|x",
                    "",
                ]
            ),
            log="s1|2026-02-01 00:00:00 +0000|Ann|fix | pipe\ns0|2026-01-01 00:00:00 +0000|Bob|init",
        ),
    )
    tags = gl.collect_tags(tmp_path)
    assert [t["name"] for t in tags] == ["v1", "v2"] and tags[1]["sha"] == "def"
    branches = {b["name"]: b["abandoned"] for b in gl.collect_branches(tmp_path, 180)}
    assert branches == {
        "main": False,
        "old": True,
        "naive": True,
        "baddate": False,
        "nodate": False,
    }
    commits = gl.collect_history(tmp_path, limit=5)
    assert commits[0] == {
        "sha": "s1",
        "date": "2026-02-01 00:00:00 +0000",
        "author": "Ann",
        "subject": "fix | pipe",
    }


def test_build_mermaid_and_markdown(tmp_path):
    tags = [
        {"name": "v1", "date": "2026-01-01 00:00:00", "sha": "a"},
        {"name": "v0", "date": "", "sha": "b"},
    ]
    branches = [
        {"name": "main", "date": "2026-01-02", "author": "dev", "abandoned": True}
    ]
    mermaid = gl.build_mermaid(tags, branches, tag_limit=1)
    assert "2026-01-01 : v1" in mermaid and "v0" not in mermaid
    assert "| `main` | 2026-01-02 | dev | YES |" in mermaid
    assert "Branch state" not in gl.build_mermaid(tags, [], 5)
    commits = [
        {"sha": "1" * 40, "date": "2026-02-01", "author": "Ann", "subject": "a|b"},
        {"sha": "0" * 40, "date": "2026-01-01", "author": "Bob", "subject": "init"},
    ]
    md = gl.render_markdown(tmp_path / "proj", tags, branches, commits, mermaid)
    assert md.startswith("# Lineage analysis — proj")
    assert "(1 flagged abandoned)" in md
    assert "First commit (within sample): `0000000000`" in md
    assert "a\\|b" in md
    assert "First commit" not in gl.render_markdown(tmp_path, [], [], [], "")


def test_maybe_render_svg(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(gl.shutil, "which", lambda name: None)
    gl.maybe_render_svg("```mermaid\ntimeline\n```", tmp_path / "d.svg")
    assert "not found" in capsys.readouterr().err

    runs = []

    def fake_run(cmd, check):
        runs.append((cmd, Path(cmd[2]).read_text(encoding="utf-8")))

    monkeypatch.setattr(gl.shutil, "which", lambda name: "/usr/bin/mmdc")
    monkeypatch.setattr(gl.subprocess, "run", fake_run)
    gl.maybe_render_svg("```mermaid\ntimeline\n```", tmp_path / "d.svg")
    assert runs[0][0][0] == "/usr/bin/mmdc" and runs[0][1] == "timeline"
    assert not (tmp_path / "d.mmd").exists()
    gl.maybe_render_svg("plain", tmp_path / "e.svg")
    assert runs[1][1] == "plain"


def test_lineage_main(monkeypatch, tmp_path, capsys):
    assert gl.main(["--repo", str(tmp_path), "--out", str(tmp_path / "x.md")]) == 2
    assert "not a git repository" in capsys.readouterr().err

    (tmp_path / ".git").mkdir()
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "lineage:\n  abandoned_branch_days: 1\n  diagram_tag_limit: 2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        gl,
        "git",
        _git_outputs(branches="b|" + _iso(10) + "|dev", log="s|2026-01-01|A|m"),
    )
    rendered = []
    monkeypatch.setattr(
        gl, "maybe_render_svg", lambda block, path: rendered.append(path)
    )
    out = tmp_path / "out" / "lineage.md"
    rc = gl.main(
        [
            "--repo",
            str(tmp_path),
            "--out",
            str(out),
            "--config",
            str(cfg),
            "--diagram",
            str(tmp_path / "d.svg"),
        ]
    )
    assert rc == 0 and rendered == [tmp_path / "d.svg"]
    assert "| `b` |" in out.read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert "branches    = 1  (abandoned: 1)" in printed
    assert gl.load_config(None) == {}


@pytest.mark.parametrize("mod", [ca, gl])
def test_load_config_without_yaml(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "yaml", None)
    assert mod.load_config(str(tmp_path / "x.yaml")) == {}


# --- validate_cleanup ----------------------------------------------------------------

vc = load("repo_analysis_toolkit/validate_cleanup.py")


@pytest.mark.parametrize(
    "name,ok",
    [
        ("snake_case.py", True),
        ("tool_v2.py", True),
        ("Tool_v2.1_final.py", True),
        ("Tool.py", False),
        ("notes.md", False),
        ("_v2-a.py", False),
        ("Tool_v.py", False),
        ("Bad-Name_v2.py", False),
        ("Tool_vX.py", False),
        ("Tool_v2__x.py", False),
        ("Tool_v2_x-y.py", False),
    ],
)
def test_python_name_compliance(name, ok):
    assert vc.is_python_name_compliant(name) is ok


def _write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _exemplary_repo(root):
    _write(root / "README.md", "r" * 200)
    for name in (
        "CONTRIBUTING.md",
        "LICENSE",
        "CHANGELOG.md",
        "SECURITY.md",
        "MAINTENANCE_SCHEDULE.md",
    ):
        _write(root / name)
    for section in ("docs", "docs_versioned", "src"):
        _write(root / section / "README.md")
    _write(root / "src" / "good_module.py")
    _write(root / ".venv" / "Ignored.py")
    for wf in (
        "ci.yml",
        "deploy-docs.yml",
        "release.yml",
        "dashboard-health.yml",
        "a.yml",
        "b.yml",
        "c.yml",
    ):
        _write(root / ".github" / "workflows" / wf)
    _write(root / ".github" / "PULL_REQUEST_TEMPLATE.md")
    _write(root / ".github" / "CODEOWNERS")
    for i in range(4):
        _write(root / ".github" / "ISSUE_TEMPLATE" / f"t{i}.md")
    return root


def test_validate_cleanup_exemplary_repo(tmp_path, capsys):
    repo = _exemplary_repo(tmp_path / "good")
    out = tmp_path / "r" / "v.json"
    assert vc.main(["--repo", str(repo), "--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert {s["category"]: s["score"] for s in payload["sections"]} == {
        "documentation": 25,
        "organization": 25,
        "automation": 25,
        "governance": 25,
    }
    assert payload["band"] == "Excellent" and payload["total_score"] == 100
    assert "TOTAL          100 / 100   (Excellent)" in capsys.readouterr().out


def test_validate_cleanup_sparse_repo(tmp_path):
    repo = tmp_path / "sparse"
    _write(repo / "README.md", "short")
    _write(repo / "Lib" / "BadName.py")
    _write(repo / "node_modules" / "x.js")
    for wf in ("ci.yml", "lint.yml", "metrics.yml"):
        _write(repo / ".github" / "workflows" / wf)
    _write(repo / ".github" / "ISSUE_TEMPLATE" / "bug.md")
    for i in range(16):
        _write(repo / f"f{i}.txt")
    docs = vc.check_docs(repo)
    assert docs["score"] == 0 and docs["items"]["section_readme_misses"] == ["Lib"]
    org = vc.check_organization(repo)
    assert org["score"] == 5 and org["items"]["python_name_compliance_ratio"] == 0.0
    auto = vc.check_automation(repo)
    assert auto["score"] == 10 and auto["items"]["expected_workflows_found"] == [
        "ci.yml"
    ]
    gov = vc.check_governance(repo)
    assert gov["score"] == 2 and gov["items"]["issue_templates"] == ["bug.md"]
    assert vc.main(["--repo", str(repo), "--out", str(tmp_path / "v.json")]) == 1


def test_validate_cleanup_empty_repo_and_missing(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert vc.check_organization(empty)["items"]["python_name_compliance_ratio"] == 1.0
    assert vc.check_automation(empty)["score"] == 0
    assert vc.check_governance(empty)["items"]["issue_templates"] == []
    assert vc.main(["--repo", str(tmp_path / "missing")]) == 2
    assert "is not a directory" in capsys.readouterr().err


@pytest.mark.parametrize(
    "total,band,rc",
    [(80, "Good", 0), (60, "Needs improvement", 1), (10, "Critical", 1)],
)
def test_validate_cleanup_bands(tmp_path, monkeypatch, total, band, rc):
    fixed = {"category": "documentation", "score": total, "max": 25, "items": {}}
    zero = dict(fixed, score=0)
    monkeypatch.setattr(vc, "check_docs", lambda repo: fixed)
    for name in ("check_organization", "check_automation", "check_governance"):
        monkeypatch.setattr(vc, name, lambda repo: zero)
    out = tmp_path / "v.json"
    assert vc.main(["--repo", str(tmp_path), "--out", str(out)]) == rc
    assert json.loads(out.read_text(encoding="utf-8"))["band"] == band
