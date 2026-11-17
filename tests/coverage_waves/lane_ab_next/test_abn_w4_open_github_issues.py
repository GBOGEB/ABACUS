"""Behaviour tests for scripts/open_github_issues.py (browser always patched)."""

import runpy
import urllib.parse

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("scripts/open_github_issues.py", name="abn_w4_open_github_issues")


def test_issue_catalogue_shape():
    assert mod.REPO == "GBOGEB/ABACUS"
    assert mod.BASE_URL == "https://github.com/GBOGEB/ABACUS/issues/new"
    assert len(mod.ISSUES) == 5
    assert [i["priority"] for i in mod.ISSUES] == ["P0", "P1", "P1", "P1", "P2"]
    for issue in mod.ISSUES:
        assert issue["title"]
        assert issue["labels"]
        assert issue["body"].startswith("## ")


def test_create_github_issue_url_round_trips_query():
    url = mod.create_github_issue_url("A & B?", "line1\nline2 #x", ["bug", "P0"])
    base, _, query = url.partition("?")
    assert base == mod.BASE_URL
    parsed = urllib.parse.parse_qs(query)
    assert parsed == {
        "title": ["A & B?"],
        "body": ["line1\nline2 #x"],
        "labels": ["bug,P0"],
    }


def test_create_github_issue_url_empty_labels():
    url = mod.create_github_issue_url("t", "b", [])
    assert url.endswith("labels=")


def test_main_opens_every_issue_and_sleeps_between(monkeypatch, capsys):
    opened = []
    sleeps = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    mod.main()
    assert len(opened) == len(mod.ISSUES)
    for url, issue in zip(opened, mod.ISSUES):
        query = urllib.parse.parse_qs(url.partition("?")[2])
        assert query["title"] == [issue["title"]]
    assert sleeps == [3] * (len(mod.ISSUES) - 1)
    out = capsys.readouterr().out
    assert "Repository: GBOGEB/ABACUS" in out
    assert "[P0] Fix Bridge Smoke Tests" in out
    assert out.count("Opened!") == len(mod.ISSUES)
    assert "All issue creation pages opened!" in out


def test_main_reports_manual_url_when_browser_fails(monkeypatch, capsys):
    def boom(url):
        raise OSError("no browser")

    sleeps = []
    monkeypatch.setattr(mod.webbrowser, "open", boom)
    monkeypatch.setattr(mod.time, "sleep", lambda s: sleeps.append(s))
    mod.main()
    out = capsys.readouterr().out
    assert out.count("Error: no browser") == len(mod.ISSUES)
    assert out.count("Manual URL: " + mod.BASE_URL) == len(mod.ISSUES)
    assert "Opened!" not in out
    assert sleeps == []


def test_dunder_main_runs_with_patched_browser(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    monkeypatch.setattr("time.sleep", lambda s: None)
    runpy.run_path(
        str(REPO_ROOT / "scripts" / "open_github_issues.py"), run_name="__main__"
    )
    assert len(opened) == 5
    assert "Done!" in capsys.readouterr().out
