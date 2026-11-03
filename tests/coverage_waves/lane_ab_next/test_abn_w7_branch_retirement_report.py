"""Gap tests for scripts/branch_retirement_report.py: gh/git paths and main()."""

import json
import types
from datetime import datetime, timezone

from tests.coverage_waves.lane_b._l2_loader import load

brr = load("scripts/branch_retirement_report.py", name="abn_w7_branch_retirement")


def _done(stdout="", returncode=0, stderr=""):
    return types.SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def test_run_delegates_to_subprocess(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs, cmd=cmd)
        return _done("x")

    monkeypatch.setattr(brr.subprocess, "run", fake_run)
    assert brr.run(["git", "status"], cwd=tmp_path, check=False).stdout == "x"
    assert seen["cmd"] == ["git", "status"]
    assert seen["cwd"] == tmp_path
    assert seen["check"] is False
    assert seen["text"] is True


def test_has_command_uses_which(monkeypatch):
    monkeypatch.setattr(brr.shutil, "which", lambda name: "/bin/gh" if name else None)
    assert brr.has_command("gh") is True
    assert brr.has_command("") is False


def test_fetch_prs_failure_and_success(monkeypatch, tmp_path):
    monkeypatch.setattr(brr, "has_command", lambda name: True)
    monkeypatch.setattr(brr, "run", lambda cmd, cwd, check=True: _done("", 1))
    assert brr.fetch_prs(tmp_path, "o/r") == {}

    items = [
        {"number": "5", "headRefName": "feat/a", "state": "OPEN", "mergedAt": None},
        {"number": 6, "headRefName": ""},
        {
            "number": 7,
            "title": "T",
            "state": "MERGED",
            "headRefName": "feat/b",
            "baseRefName": "main",
            "url": "u",
            "updatedAt": "d",
            "mergedAt": "m",
        },
    ]
    monkeypatch.setattr(
        brr, "run", lambda cmd, cwd, check=True: _done(json.dumps(items))
    )
    prs = brr.fetch_prs(tmp_path, "o/r")
    assert sorted(prs) == ["feat/a", "feat/b"]
    assert prs["feat/a"].number == 5 and prs["feat/a"].title == ""
    assert prs["feat/b"].merged_at == "m" and prs["feat/b"].base == "main"


def test_rev_count_and_commit_age(monkeypatch, tmp_path):
    answers = {"rev-list": "12", "log": "2026-01-01T00:00:00Z"}
    monkeypatch.setattr(brr, "optional_git", lambda repo, *a: answers[a[0]])
    assert brr.rev_count(tmp_path, "a..b") == 12
    now = datetime(2026, 1, 11, tzinfo=timezone.utc)
    assert brr.commit_age(tmp_path, "ref", now) == ("2026-01-01T00:00:00Z", 10)
    answers["rev-list"] = "fatal"
    assert brr.rev_count(tmp_path, "a..b") is None


def test_classify_protected_branch_name(tmp_path):
    result = brr.classify(
        "release/1.0", "r", "main", "b", tmp_path, None, set(), 60, 1, False
    )
    assert result == ("KEEP", "protected branch naming policy")


class FakeGit:
    """Route optional_git/run calls to canned answers."""

    def __init__(self, remote, base_ok=True, fetch_rc=0, refs=""):
        self.remote = remote
        self.base_ok = base_ok
        self.fetch_rc = fetch_rc
        self.refs = refs

    def optional_git(self, repo, *args):
        head = args[0]
        if head == "remote":
            return self.remote
        if head == "symbolic-ref":
            return "origin/main"
        if head == "rev-parse":
            return "deadbeef" if self.base_ok else ""
        if head == "for-each-ref":
            return self.refs
        if head == "log":
            return "2020-01-01T00:00:00+00:00"
        if head == "rev-list":
            return "3"
        return ""

    def run(self, cmd, cwd, check=True):
        if cmd[:2] == ["git", "fetch"]:
            return _done("", self.fetch_rc, "network down")
        return _done("", 1)


def _args(**overrides):
    values = dict(
        base=None, no_fetch=False, protect_pr=[], stale_days=60, force_stale=True
    )
    values.update(overrides)
    return types.SimpleNamespace(**values)


def _install(monkeypatch, fake, prs=None):
    monkeypatch.setattr(brr, "optional_git", fake.optional_git)
    monkeypatch.setattr(brr, "run", fake.run)
    monkeypatch.setattr(brr, "fetch_prs", lambda repo, slug: prs or {})


def test_build_records_non_github_remote_fetch_failure(monkeypatch, tmp_path):
    fake = FakeGit("ssh://example.org/x.git", fetch_rc=1, refs="origin/feat sha1\n")
    _install(monkeypatch, fake)
    records, warnings = brr.build_records(tmp_path, _args())
    assert any("not a GitHub URL" in w for w in warnings)
    assert any("network down" in w for w in warnings)
    assert len(records) == 1
    rec = records[0]
    assert (rec.ahead, rec.behind) == (3, 3)
    assert rec.classification == "DELETE"
    assert rec.delete_command == "git push --delete origin -- feat"


def test_build_records_github_without_prs_and_no_base(monkeypatch, tmp_path):
    fake = FakeGit(
        "git@github.com:GBOGEB/ABACUS.git", base_ok=False, refs="origin/x s\n"
    )
    _install(monkeypatch, fake)
    records, warnings = brr.build_records(tmp_path, _args(force_stale=False))
    assert any("PR metadata was not available" in w for w in warnings)
    assert any("is unavailable" in w for w in warnings)
    assert records[0].ahead is None and records[0].behind is None
    assert records[0].classification == "CHERRY-PICK THEN DELETE"
    assert records[0].delete_command == ""


def test_write_markdown_without_warnings_or_records(monkeypatch, tmp_path):
    path = tmp_path / "r.md"
    brr.write_markdown([], [], path, tmp_path, _args(base="trunk"))
    text = path.read_text(encoding="utf-8")
    assert "- None." in text
    assert "Base branch: `trunk`" in text
    assert "No remote branches were available in this checkout." in text


def test_main_writes_all_outputs(monkeypatch, tmp_path, capsys):
    (tmp_path / ".git").mkdir()
    pr = brr.PullRequest(9, "t", "OPEN", "feat", "main", "u", "d", None)
    fake = FakeGit("https://github.com/GBOGEB/ABACUS", refs="origin/feat s9\n")
    _install(monkeypatch, fake, prs={"feat": pr})
    rc = brr.main(["--repo", str(tmp_path), "--output-dir", "out", "--no-fetch"])
    assert rc == 0
    out_dir = tmp_path / "out"
    report = (out_dir / "branch-retirement-report.md").read_text(encoding="utf-8")
    assert "open PR #9" in report
    csv_text = (out_dir / "branch-retirement-inventory.csv").read_text(encoding="utf-8")
    assert "#9" in csv_text
    script = (out_dir / "branch-delete-commands.sh").read_text(encoding="utf-8")
    assert "No delete commands generated." in script
    printed = capsys.readouterr().out
    assert printed.count("Wrote ") == 3
