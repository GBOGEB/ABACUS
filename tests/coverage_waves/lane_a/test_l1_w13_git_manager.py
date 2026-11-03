"""Lane A wave 13: DMAIC_V3.integrations.git_manager with mocked git."""

import json
import sys
import types

import pytest

from DMAIC_V3.integrations import git_manager as gm


class FakeGit:
    """Route ``subprocess.run`` calls by git sub-command."""

    def __init__(self, responses=None, version_rc=0):
        self.responses = dict(responses or {})
        self.version_rc = version_rc
        self.calls = []

    def __call__(self, cmd, cwd=None, capture_output=None, text=None, **kw):
        self.calls.append((list(cmd), cwd, kw))
        sub = cmd[1]
        if sub == "--version":
            return types.SimpleNamespace(
                returncode=self.version_rc, stdout="git 2", stderr=""
            )
        resp = self.responses.get(sub, (0, "", ""))
        if isinstance(resp, BaseException):
            raise resp
        rc, out, err = resp
        return types.SimpleNamespace(returncode=rc, stdout=out, stderr=err)

    def subcalls(self, name):
        return [c[0] for c in self.calls if c[0][1] == name]


def _manager(monkeypatch, tmp_path, **kw):
    fake = FakeGit(**kw)
    monkeypatch.setattr("subprocess.run", fake)
    return gm.GitManager(tmp_path), fake


def test_git_availability(monkeypatch, tmp_path):
    mgr, _ = _manager(monkeypatch, tmp_path)
    assert mgr.git_available is True
    mgr2, _ = _manager(monkeypatch, tmp_path, version_rc=1)
    assert mgr2.git_available is False

    def missing(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr("subprocess.run", missing)
    assert gm.GitManager(tmp_path).git_available is False


def test_run_git_paths(monkeypatch, tmp_path):
    err = gm.subprocess.CalledProcessError(1, ["git"], stderr="bad ref")
    mgr, fake = _manager(
        monkeypatch,
        tmp_path,
        responses={"ok": (0, "out", "err"), "cpe": err, "boom": OSError("io")},
    )
    assert mgr._run_git(["ok"]) == (True, "outerr")
    assert fake.calls[-1][1] == tmp_path
    assert fake.calls[-1][2]["check"] is True
    assert mgr._run_git(["cpe"]) == (False, "bad ref")
    assert mgr._run_git(["boom"]) == (False, "io")
    mgr.git_available = False
    assert mgr._run_git(["ok"]) == (False, "Git not available")


def test_unavailable_git_short_circuits(monkeypatch, tmp_path, capsys):
    mgr, _ = _manager(monkeypatch, tmp_path, version_rc=1)
    assert mgr.commit_iteration(1) is False
    assert "Git not available" in capsys.readouterr().out
    assert mgr.create_baseline_tag(1) is False
    assert mgr.generate_diff_report(1, 2) == {"error": "Git not available"}
    assert mgr.get_changes_since_iteration(1) == []
    assert mgr.get_iteration_log(1) == {"error": "Git not available"}
    out = tmp_path / "h.json"
    mgr.save_git_history(out)
    assert not out.exists()
    status = mgr.get_status()
    assert (status.branch, status.clean) == ("unknown", False)
    assert mgr.list_baselines() == []


def test_commit_stages_existing_files_and_commits(monkeypatch, tmp_path, capsys):
    (tmp_path / "DMAIC_V3_OUTPUT").mkdir()
    (tmp_path / "planning_matrix.json").write_bytes(b"{}")
    mgr, fake = _manager(monkeypatch, tmp_path, responses={"commit": (0, "1 file", "")})
    assert mgr.commit_iteration(3, phase="measure") is True
    added = [c[2] for c in fake.subcalls("add")]
    assert added == ["DMAIC_V3_OUTPUT/", "planning_matrix.json"]
    message = fake.subcalls("commit")[0][3]
    assert message.startswith("DMAIC V3.3 - Iteration 3 - measure complete\n\n")
    out = capsys.readouterr().out
    assert "Committed: DMAIC V3.3 - Iteration 3 - measure complete" in out


def test_commit_message_variants(monkeypatch, tmp_path, capsys):
    mgr, fake = _manager(
        monkeypatch, tmp_path, responses={"commit": (1, "nothing to commit", "")}
    )
    assert mgr.commit_iteration(2) is True
    first = fake.subcalls("commit")[0][3]
    assert first.startswith("DMAIC V3.3 - Iteration 2 complete")
    assert "No changes to commit" in capsys.readouterr().out

    mgr2, fake2 = _manager(monkeypatch, tmp_path, responses={"commit": (1, "", "no")})
    assert mgr2.commit_iteration(2, message="custom") is False
    assert fake2.subcalls("commit")[0][3].startswith("custom\n\nTimestamp: ")
    assert "Commit failed: no" in capsys.readouterr().out


def test_create_baseline_tag(monkeypatch, tmp_path, capsys):
    mgr, fake = _manager(monkeypatch, tmp_path)
    assert mgr.create_baseline_tag(4) is True
    assert mgr.create_baseline_tag(4, version="v3.3.0") is True
    names = [c[3] for c in fake.subcalls("tag")]
    assert names == ["iteration4-baseline", "v3.3.0-iteration4"]
    mgr2, _ = _manager(monkeypatch, tmp_path, responses={"tag": (1, "", "exists")})
    assert mgr2.create_baseline_tag(4) is False
    assert "Tag creation failed: exists" in capsys.readouterr().out


def test_generate_diff_report(monkeypatch, tmp_path):
    stat = " a.py | 3 ++-\n b.py | 1 +\n weird line\n 2 files changed\n"
    mgr, fake = _manager(monkeypatch, tmp_path, responses={"diff": (0, stat, "")})
    report = mgr.generate_diff_report(1, 2)
    assert report["files_changed"] == [
        {"file": "a.py", "changes": "3 ++-"},
        {"file": "b.py", "changes": "1 +"},
    ]
    assert report["summary"] == " 2 files changed"
    assert (report["from_iteration"], report["to_iteration"]) == (1, 2)
    assert fake.subcalls("diff")[0][3:] == [
        "iteration1-baseline",
        "iteration2-baseline",
    ]
    mgr2, _ = _manager(monkeypatch, tmp_path, responses={"diff": (1, "", "nope")})
    assert mgr2.generate_diff_report(1, 2) == {"error": "Diff failed: nope"}


def test_changes_since_iteration(monkeypatch, tmp_path):
    mgr, _ = _manager(monkeypatch, tmp_path, responses={"diff": (0, "a\n\n b \n", "")})
    assert mgr.get_changes_since_iteration(1) == ["a", "b"]
    mgr2, _ = _manager(monkeypatch, tmp_path, responses={"diff": (1, "", "x")})
    assert mgr2.get_changes_since_iteration(1) == []


LOG = "h1|ann|100|Iteration 1 | part two\n\nshort|line\nh2|bob|200|msg\n"


def test_iteration_log(monkeypatch, tmp_path):
    mgr, fake = _manager(monkeypatch, tmp_path, responses={"log": (0, LOG, "")})
    log = mgr.get_iteration_log(1)
    assert log["commit_count"] == 2
    assert log["commits"][0]["message"] == "Iteration 1 | part two"
    assert log["commits"][1]["author"] == "bob"
    assert "Iteration 1" in fake.subcalls("log")[0]
    mgr2, _ = _manager(monkeypatch, tmp_path, responses={"log": (1, "", "bad")})
    assert mgr2.get_iteration_log(1) == {"error": "Log failed: bad"}


def test_save_git_history(monkeypatch, tmp_path, capsys):
    out = tmp_path / "hist.json"
    mgr, _ = _manager(monkeypatch, tmp_path, responses={"log": (0, LOG, "")})
    mgr.save_git_history(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["total_commits"] == 2
    assert data["commits"][0]["commit_hash"] == "h1"
    assert "Saved history" in capsys.readouterr().out

    other = tmp_path / "none.json"
    mgr2, _ = _manager(monkeypatch, tmp_path, responses={"log": (1, "", "")})
    mgr2.save_git_history(other)
    assert not other.exists()


@pytest.mark.parametrize(
    "rev,status,branch,clean",
    [
        ((0, "main\n", ""), (0, "", ""), "main", True),
        ((0, "dev\n", ""), (0, " M f\n", ""), "dev", False),
        ((0, "  \n", ""), (1, "", ""), "unknown", False),
    ],
)
def test_get_status(monkeypatch, tmp_path, rev, status, branch, clean):
    responses = {"rev-parse": rev, "status": status}
    mgr, _ = _manager(monkeypatch, tmp_path, responses=responses)
    result = mgr.get_status()
    assert (result.branch, result.clean) == (branch, clean)


def test_list_baselines(monkeypatch, tmp_path):
    out = "baseline-1\n\nbaseline-2\n"
    mgr, _ = _manager(monkeypatch, tmp_path, responses={"tag": (0, out, "")})
    assert mgr.list_baselines() == [
        {"tag": "baseline-1", "name": "baseline-1"},
        {"tag": "baseline-2", "name": "baseline-2"},
    ]


def test_main_runs_all_actions(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    responses = {
        "commit": (0, "ok", ""),
        "diff": (0, "f | 1 +\n 1 file\n", ""),
        "log": (0, LOG, ""),
    }
    _, fake = _manager(monkeypatch, tmp_path, responses=responses)
    hist = tmp_path / "h.json"
    argv = ["git_manager.py", "--commit", "1", "--tag", "1", "--diff", "1", "2"]
    argv += ["--changes", "1", "--log", "1", "--history", str(hist)]
    monkeypatch.setattr(sys, "argv", argv)
    gm.main()
    out = capsys.readouterr().out
    assert '"from_iteration": 1' in out
    assert '"commit_count": 2' in out
    assert hist.exists()
    assert fake.subcalls("tag")
    assert fake.subcalls("commit")


def test_main_no_actions(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _, fake = _manager(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["git_manager.py"])
    gm.main()
    assert capsys.readouterr().out == ""
    # one probe from the fixture manager, one from main()'s own manager
    assert [c[0][1] for c in fake.calls] == ["--version", "--version"]
