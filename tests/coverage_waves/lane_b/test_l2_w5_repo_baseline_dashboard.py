"""Lane-B wave 5: repo_analysis_toolkit baseline analyzer and HTML dashboard."""

import json

import pytest

from ._l2_loader import load

ar = load("repo_analysis_toolkit/analyze_repo.py")
cd = load("repo_analysis_toolkit/create_dashboard.py")


def _write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_git(answers):
    def fake(repo, *args):
        return answers.get(args[0], "")

    return fake


GIT_ANSWERS = {
    "rev-list": "120",
    "shortlog": "  10\tAda\n   3\tBob\n\n",
    "branch": "main\norigin/main\n",
    "tag": "v2\nv1",
    "log": "2024-01-01 00:00:00 +0000\n2025-01-01 00:00:00 +0000",
}


# --- analyze_repo -------------------------------------------------------------------


def test_load_config(tmp_path, monkeypatch, capsys):
    assert ar.load_config(None) == {}
    cfg = tmp_path / "c.yaml"
    cfg.write_text("exclude_patterns: ['**/vendor/**']\n", encoding="utf-8")
    assert ar.load_config(str(cfg)) == {"exclude_patterns": ["**/vendor/**"]}
    blank = tmp_path / "b.yaml"
    blank.write_text("", encoding="utf-8")
    assert ar.load_config(str(blank)) == {}
    monkeypatch.setattr(ar, "yaml", None)
    assert ar.load_config(str(cfg)) == {}
    assert "PyYAML not installed" in capsys.readouterr().err


def test_is_excluded_and_git_wrapper(tmp_path, monkeypatch):
    from pathlib import Path

    assert ar.is_excluded(Path("a/node_modules/x.js"), {"node_modules"})
    assert not ar.is_excluded(Path("a/b.py"), {"node_modules"})

    class _Out:
        stdout = "  value \n"

    monkeypatch.setattr(ar.subprocess, "run", lambda cmd, **kw: _Out())
    assert ar.git(tmp_path, "status") == "value"

    def missing(cmd, **kw):
        raise FileNotFoundError("git")

    monkeypatch.setattr(ar.subprocess, "run", missing)
    assert ar.git(tmp_path, "status") == ""


def test_scan_files_counts_languages_and_excludes(tmp_path):
    _write(tmp_path / "a.py", "print(1)\n")
    _write(tmp_path / "pkg" / "b.ts", "let x = 1;")
    _write(tmp_path / "pkg" / "data.bin", "0" * 50)
    _write(tmp_path / "node_modules" / "c.js", "ignored")
    stats = ar.scan_files(tmp_path, set(ar.DEFAULT_EXCLUDES) | {"vendor"})
    assert stats["total_files"] == 3
    assert stats["top_level_files"] == 1 and stats["top_level_dirs"] == 1
    assert dict(stats["languages_by_count"]) == {
        "Python": 1,
        "TypeScript": 1,
        "Other": 1,
    }
    assert stats["largest_files"][0]["bytes"] == 50


def test_scan_git(tmp_path, monkeypatch):
    assert ar.scan_git(tmp_path) == {"is_git_repo": False}
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(ar, "git", _fake_git(GIT_ANSWERS))
    stats = ar.scan_git(tmp_path)
    assert stats["commits"] == 120 and stats["contributors_total"] == 2
    assert stats["branches_total"] == 2 and stats["tags_recent"] == ["v2", "v1"]
    assert stats["first_commit"] == "2024-01-01 00:00:00 +0000"
    monkeypatch.setattr(ar, "git", _fake_git({}))
    empty = ar.scan_git(tmp_path)
    assert (
        empty["commits"] == 0
        and empty["first_commit"] == ""
        and empty["tags_total"] == 0
    )


def test_scan_docs_and_ci(tmp_path):
    assert ar.scan_ci(tmp_path) == {
        "workflows": [],
        "workflow_count": 0,
        "issue_templates": [],
        "pr_template": False,
        "dependabot": False,
    }
    _write(tmp_path / "README.md")
    _write(tmp_path / "readme.txt")
    _write(tmp_path / "docs" / "index.md")
    _write(tmp_path / ".github" / "CONTRIBUTING.md")
    _write(tmp_path / "LICENSE.txt")
    _write(tmp_path / ".github" / "workflows" / "ci.yml")
    _write(tmp_path / ".github" / "ISSUE_TEMPLATE" / "bug.md")
    _write(tmp_path / ".github" / "PULL_REQUEST_TEMPLATE.md")
    _write(tmp_path / ".github" / "dependabot.yml")
    docs = ar.scan_docs(tmp_path)
    assert sorted(docs["readmes_at_root"]) == ["README.md", "readme.txt"]
    assert docs["docs_dir"] and docs["contributing_md"] and docs["license_present"]
    assert not docs["docs_versioned"] and not docs["security_md"]
    ci = ar.scan_ci(tmp_path)
    assert ci["workflows"] == ["ci.yml"] and ci["pr_template"] and ci["dependabot"]


def test_estimate_score_bounds():
    assert (
        ar.estimate_score({"top_level_files": 99, "top_level_dirs": 99}, {}, {}, {})
        == 0
    )
    full = ar.estimate_score(
        {"top_level_files": 1, "top_level_dirs": 1},
        {"is_git_repo": True, "commits": 51, "tags_total": 1},
        {
            "readmes_at_root": ["README.md"],
            "docs_dir": True,
            "contributing_md": True,
            "license_present": True,
            "security_md": True,
        },
        {
            "workflow_count": 40,
            "issue_templates": ["a"],
            "pr_template": True,
            "dependabot": True,
        },
    )
    assert full == 71


def test_analyze_main(tmp_path, monkeypatch, capsys):
    assert ar.main(["--repo", str(tmp_path / "missing")]) == 2
    assert "is not a directory" in capsys.readouterr().err

    repo = tmp_path / "repo"
    _write(repo / "README.md")
    _write(repo / "vendor" / "lib.py")
    _write(repo / "src" / "main.py")
    (repo / ".git").mkdir()
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("exclude_patterns: ['**/vendor/**', '*.tmp']\n", encoding="utf-8")
    monkeypatch.setattr(ar, "git", _fake_git(GIT_ANSWERS))
    out = tmp_path / "reports" / "baseline.json"
    assert ar.main(["--repo", str(repo), "--out", str(out), "--config", str(cfg)]) == 0
    snapshot = json.loads(out.read_text(encoding="utf-8"))
    assert snapshot["repo_name"] == "repo"
    assert snapshot["files"]["total_files"] == 2
    assert snapshot["git"]["commits"] == 120
    assert "est. score" in capsys.readouterr().out


# --- create_dashboard -----------------------------------------------------------------


def test_readers_handle_missing_files(tmp_path):
    assert cd.read_baseline(tmp_path / "none.json") == {}
    assert cd.read_classification(tmp_path / "none.csv") == ([], {})
    assert cd.read_text_if_exists(tmp_path / "none.md") == ""


def test_render_empty_baseline():
    page = cd.render("", {"repo_name": "fallback"}, {}, [], "")
    assert "Repo analysis dashboard — fallback" in page
    assert "<tr><td colspan='3'>No data</td></tr>" in page
    assert "<tr><td colspan='2'>No data</td></tr>" in page
    assert "(no lineage report found)" in page and "(none)" in page
    assert "<span></span>" in page


def test_render_escapes_and_orders():
    baseline = {
        "files": {"total_files": 7, "languages_by_count": [["Python", 5], ["<C>", 2]]},
        "git": {"commits": 3, "contributors_total": 2, "tags_total": 1},
        "docs": {"readmes_at_root": ["README.md"], "license_present": True},
        "ci": {"workflow_count": 1, "workflows": ["ci<x>.yml"], "pr_template": False},
        "estimated_health_score": 42,
    }
    page = cd.render("R&D", baseline, {"Stale": 1, "Active": 3}, [], "# lineage <b>")
    assert "Repo analysis dashboard — R&amp;D" in page
    assert page.index("<td>Active</td><td>3</td><td>75.0%</td>") < page.index(
        "<td>Stale</td>"
    )
    assert 'class="tag-Active" style="width:75.0%"' in page
    assert "<td>&lt;C&gt;</td>" in page and "ci&lt;x&gt;.yml" in page
    assert "# lineage &lt;b&gt;" in page
    assert "<tr><td>README at root</td><td>✅</td></tr>" in page
    assert "<tr><td>PR template</td><td>❌</td></tr>" in page


@pytest.mark.parametrize("repo_name", [None, "Override"])
def test_dashboard_main_end_to_end(tmp_path, capsys, repo_name):
    reports = tmp_path / "reports"
    _write(
        reports / "baseline.json",
        json.dumps({"repo_name": "from-baseline", "files": {"total_files": 2}}),
    )
    _write(reports / "classification.csv", "path,tag\na,Active\nb,Corrupted\nc,\n")
    _write(reports / "lineage.md", "L" * 2500)
    out = tmp_path / "site" / "dash.html"
    argv = ["--reports", str(reports), "--out", str(out)]
    if repo_name:
        argv += ["--repo-name", repo_name]
    assert cd.main(argv) == 0
    page = out.read_text(encoding="utf-8")
    assert ("— " + (repo_name or "from-baseline")) in page
    assert "<td>Corrupted</td><td>1</td>" in page
    assert "L" * 2000 in page and "L" * 2001 not in page
    assert "[create_dashboard] wrote" in capsys.readouterr().out
