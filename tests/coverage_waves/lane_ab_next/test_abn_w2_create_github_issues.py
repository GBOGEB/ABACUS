"""Behaviour tests for scripts/create_github_issues.py."""

import runpy

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("scripts/create_github_issues.py", name="abn_create_github_issues")
SCRIPT = REPO_ROOT / "scripts" / "create_github_issues.py"


def test_issue_catalogue_is_well_formed():
    assert len(mod.ISSUES) == 5
    for issue in mod.ISSUES:
        assert issue["title"]
        assert issue["body"].startswith("## ")
        assert "ci/cd" in issue["labels"]
    assert mod.ISSUES[1]["labels"][-1] == "P0"


def test_generate_issue_files_writes_all_outputs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert mod.generate_issue_files() is None

    out_dir = tmp_path / "github_issues"
    issue_files = sorted(out_dir.glob("issue_*.md"))
    assert len(issue_files) == 5
    first = issue_files[0]
    assert first.name.startswith("issue_01_fix_static_analysis")
    assert len(first.stem) <= len("issue_01_") + 50
    text = first.read_text(encoding="utf-8")
    assert text.startswith("# Fix Static Analysis - flake8 AttributeError\n")
    assert text.rstrip().endswith("`ci/cd`, `bug`, `code-quality`, `P1`")

    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    assert "Total issues: 5" in readme
    assert "Missing 'dmaic' module** - Priority: P0" in readme
    assert '--label "ci/cd,tests,deployment,P2"' in readme
    assert "issue_05_*.md" in readme

    quick = (out_dir / "QUICK_REFERENCE.md").read_text(encoding="utf-8")
    assert "P0 - Critical" in quick
    assert "P1 - Important" in quick
    assert "P2 - Nice to Have" in quick
    p0_section = quick.split("P0 - Critical")[1].split("P1 - Important")[0]
    assert "Bridge Smoke Tests" in p0_section
    assert "Static Analysis" not in p0_section

    out = capsys.readouterr().out
    assert "Total issues created: 5" in out
    assert "Created quick reference" in out


def test_generate_without_priority_labels(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "github_issues").mkdir()
    custom = [dict(title="Plain Issue-One", body="body text", labels=["docs"])]
    monkeypatch.setattr(mod, "ISSUES", custom)

    mod.generate_issue_files()

    out_dir = tmp_path / "github_issues"
    assert (out_dir / "issue_01_plain_issue_one.md").is_file()
    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    assert "**Plain Issue-One** - Priority: P2" in readme
    quick = (out_dir / "QUICK_REFERENCE.md").read_text(encoding="utf-8")
    assert "P0 - Critical" not in quick
    assert "P1 - Important" not in quick
    assert "P2 - Nice to Have" not in quick
    assert "Common Root Causes" in quick
    assert "Total issues created: 1" in capsys.readouterr().out


def test_main_entrypoint_generates_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert (tmp_path / "github_issues" / "QUICK_REFERENCE.md").is_file()
    assert "Done!" in capsys.readouterr().out
