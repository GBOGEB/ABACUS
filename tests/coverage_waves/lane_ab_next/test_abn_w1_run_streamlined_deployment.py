"""Behaviour tests for run_streamlined_deployment.py (subprocess is faked)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("run_streamlined_deployment.py", name="abn_run_streamlined_deployment")


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRun:
    """Records commands and answers them from a prefix table."""

    def __init__(self, table, default=None):
        self.table = table
        self.default = default or _Result(1, "", "unknown command")
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        for prefix, answer in self.table.items():
            if cmd.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        return self.default


def _report(tmp_path):
    return json.loads((tmp_path / "streamlined_deployment_report.json").read_bytes())


def _rankings(tmp_path, payload):
    folder = tmp_path / "ABACUS-v031"
    folder.mkdir(exist_ok=True)
    (folder / "artifact_rankings.json").write_bytes(payload)


def test_log_uses_known_and_unknown_icons(capsys):
    mod.log("hello")
    mod.log("done", "SUCCESS")
    mod.log("odd", "WEIRD")
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["[INFO] hello", "[OK] done", "      odd"]


def test_run_returns_status_and_output(monkeypatch):
    fake = _FakeRun({"echo": _Result(0, "out", "err")})
    monkeypatch.setattr(mod.subprocess, "run", fake)

    assert mod.run("echo hi", cwd="here") == (True, "out", "err")
    cmd, kwargs = fake.calls[0]
    assert cmd == "echo hi"
    assert kwargs["cwd"] == "here"
    assert kwargs["timeout"] == 120
    assert kwargs["capture_output"] is True


def test_run_nonzero_return_is_failure(monkeypatch):
    monkeypatch.setattr(mod.subprocess, "run", _FakeRun({}, _Result(2, "", "bad")))
    assert mod.run("anything") == (False, "", "bad")


def test_run_exception_is_reported(monkeypatch):
    fake = _FakeRun({"boom": OSError("no shell")})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    assert mod.run("boom") == (False, "", "no shell")


def test_main_happy_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake = _FakeRun(
        {
            "git status": _Result(0, " 7\n"),
            "git branch": _Result(0, "feature/x\n"),
            "python run_direct_improvements.py": _Result(0, "ok"),
            "git add -A": _Result(0),
            "git remote": _Result(0, "https://example.invalid/repo.git\n"),
        }
    )
    monkeypatch.setattr(mod.subprocess, "run", fake)
    rankings = [
        {"metrics": {"overall_score": 0.9}},
        {"metrics": {"overall_score": 0.6}},
        {"metrics": {"overall_score": 0.2}},
    ]
    _rankings(tmp_path, json.dumps(rankings).encode())
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_bytes(b"on: push\n")

    assert mod.main() == 0

    results = _report(tmp_path)["results"]
    assert results["git_modified"] == "7"
    assert results["git_branch"] == "feature/x"
    assert results["improvement_iterations"] == 3
    assert results["total_artifacts"] == 3
    assert results["avg_score"] == pytest.approx(1.7 / 3)
    assert results["low_scoring"] == 1
    assert results["cicd_configs"] == 1
    assert results["remote_url"] == "https://example.invalid/repo.git"
    assert results["ready_to_push"] is True

    commits = [c for c, _ in fake.calls if c.startswith("git add -A")]
    assert len(commits) == 3
    assert "iteration 3" in commits[-1]
    improve = [k for c, k in fake.calls if c.startswith("python run_direct")]
    assert all(k["cwd"] == "ABACUS-v031" for k in improve)

    out = capsys.readouterr().out
    assert "Quality target achieved!" in out
    assert "Ready to Push:       Yes" in out
    assert "DEPLOYMENT COMPLETE!" in out


def test_main_all_failures(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    long_err = "EEE" + "".join("x" for _ in range(200))
    fake = _FakeRun({}, _Result(1, "", long_err))
    monkeypatch.setattr(mod.subprocess, "run", fake)

    assert mod.main() == 0

    results = _report(tmp_path)["results"]
    assert results == {
        "improvement_iterations": 1,
        "cicd_configs": 0,
        "ready_to_push": False,
    }
    assert not any(c.startswith("git add -A") for c, _ in fake.calls)
    out = capsys.readouterr().out
    assert "Iteration 1 failed: EEE" in out
    assert long_err[:101] not in out
    assert long_err[:100] in out
    assert "No remote configured" in out
    assert "Git Branch:          N/A" in out
    assert "Average Score:       0.000" in out
    assert "Ready to Push:       No" in out


def test_main_stops_iterating_on_second_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    answers = iter([_Result(0, "ok"), _Result(1, "", "broke")])

    def fake(cmd, **kwargs):
        if cmd.startswith("python run_direct"):
            return next(answers)
        return _Result(1)

    monkeypatch.setattr(mod.subprocess, "run", fake)
    mod.main()
    assert _report(tmp_path)["results"]["improvement_iterations"] == 2


def test_main_low_quality_scores(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRun({}, _Result(1)))
    _rankings(tmp_path, json.dumps([{"metrics": {}}, {}]).encode())

    mod.main()

    results = _report(tmp_path)["results"]
    assert results["avg_score"] == 0
    assert results["low_scoring"] == 2
    assert "Target: 0.500, Current: 0.000" in capsys.readouterr().out


def test_main_empty_rankings_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRun({}, _Result(1)))
    _rankings(tmp_path, b"[]")

    mod.main()

    results = _report(tmp_path)["results"]
    assert results["total_artifacts"] == 0
    assert results["avg_score"] == 0


def test_main_non_list_rankings_are_ignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRun({}, _Result(1)))
    _rankings(tmp_path, b'{"metrics": {}}')

    mod.main()

    assert "total_artifacts" not in _report(tmp_path)["results"]


def test_main_invalid_rankings_json_is_logged(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", _FakeRun({}, _Result(1)))
    _rankings(tmp_path, b"{not json")

    mod.main()

    assert "Error reading rankings" in capsys.readouterr().out
    assert "total_artifacts" not in _report(tmp_path)["results"]


def test_main_block_exits_with_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", _FakeRun({}, _Result(1)))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "run_streamlined_deployment.py"), run_name="__main__"
        )

    assert exc.value.code == 0
    assert (tmp_path / "streamlined_deployment_report.json").is_file()
