"""Gap tests for scripts/cbd_e2e_stage.py.

Targets the error paths of ``command``/``git_value``, the stage tool selection,
the isolated ``replay`` flow and the CLI ``main`` dispatch. Every subprocess
call is replaced by an in-memory fake.
"""

import json
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/cbd_e2e_stage.py", name="abn_w7_cbd_e2e_stage")

GOOD_SHA = "a" * 40


def test_command_timeout_records_partial_output(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise mod.subprocess.TimeoutExpired(cmd="x", timeout=1, output=b"partial")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    result = mod.command(["prog", 1], tmp_path)
    assert result["returncode"] is None
    assert result["timed_out"] is True
    assert result["status"] == "FAIL"
    assert result["output"].startswith("partial")
    assert result["argv"] == ["prog", "1"]


def test_command_oserror_records_exception_type(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    result = mod.command(["nope"], tmp_path)
    assert result["returncode"] is None
    assert result["timed_out"] is False
    assert "FileNotFoundError" in result["output"]
    assert result["status"] == "FAIL"


@pytest.mark.parametrize("use_timeout", [False, True])
def test_git_value_errors_return_none(monkeypatch, tmp_path, use_timeout):
    def fake_run(*args, **kwargs):
        if use_timeout:
            raise mod.subprocess.TimeoutExpired(cmd="git", timeout=15)
        raise OSError("no git")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod.git_value(tmp_path, "rev-parse", "HEAD") is None


def _make_owned(repo):
    for name in mod.OWNED + mod.PARENT_TESTS:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# x\n")


def test_tools_for_stage_missing_files_returns_none(tmp_path):
    assert mod.tools_for_stage(tmp_path, "pre-commit") is None


def test_tools_for_stage_precommit_uses_owned_tests_only(tmp_path):
    _make_owned(tmp_path)
    pre = dict(mod.tools_for_stage(tmp_path, "pre-commit"))
    push = dict(mod.tools_for_stage(tmp_path, "pre-push"))
    assert set(pre) == {"compile", "black", "isort", "pytest"}
    assert "tests/test_cbd_e2e_stage.py" in pre["pytest"]
    assert not any("native_job" in a for a in pre["pytest"])
    assert any("native_job" in a for a in push["pytest"])


def _cmd_result(status):
    return {"status": status, "returncode": 0 if status == "PASS" else 1}


def test_replay_success_runs_checkout_stage(monkeypatch, tmp_path):
    calls = []

    def fake_command(argv, cwd, timeout=None):
        calls.append(list(argv))
        return _cmd_result("PASS")

    def fake_run_stage(target, stage, expected):
        assert stage == "checkout"
        assert expected == GOOD_SHA
        return {"status": "PASS", "source": {"head_sha": GOOD_SHA}}

    monkeypatch.setattr(mod, "command", fake_command)
    monkeypatch.setattr(mod, "run_stage", fake_run_stage)
    result = mod.replay(tmp_path, GOOD_SHA)
    assert result["stage"] == "replay"
    assert result["status"] == "PASS"
    assert [s["name"] for s in result["clone_steps"]] == ["init", "fetch", "checkout"]
    assert result["remote_github_fresh_clone_proven"] is False
    assert "fetch" in calls[1]
    assert "FETCH_HEAD" in calls[2]


def test_replay_init_failure_skips_later_steps(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "command", lambda *a, **k: _cmd_result("FAIL"))
    result = mod.replay(tmp_path, GOOD_SHA)
    assert result["status"] == "FAIL"
    assert result["source"] == {}
    assert [s["name"] for s in result["clone_steps"]] == ["init"]
    assert result["clone_steps"][0]["returncode"] == 1


def test_replay_checkout_failure_holds(monkeypatch, tmp_path):
    seq = iter(["PASS", "PASS", "FAIL"])
    monkeypatch.setattr(mod, "command", lambda *a, **k: _cmd_result(next(seq)))
    result = mod.replay(tmp_path, GOOD_SHA)
    assert result["status"] == "FAIL"
    assert [s["status"] for s in result["clone_steps"]] == ["PASS", "PASS", "FAIL"]


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["cbd_e2e_stage.py"] + argv)
    return mod.main()


def _stage(sha, tests):
    return {
        "schema": "abacus.cbd.e2e.stage.v1",
        "stage": "pre-push",
        "status": "PASS",
        "source": {"head_sha": sha, "head_tree_sha": "b" * 40},
        "tests_executed": tests,
        "clock": {"elapsed_process_ms": 1.0},
        "checks": [{"name": n, "status": "PASS"} for n in ("black", "isort", "pytest")],
    }


def test_main_compare_pass_writes_absolute_receipt(monkeypatch, tmp_path, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps(_stage(GOOD_SHA, 5)), encoding="utf-8")
    after.write_text(json.dumps(_stage(GOOD_SHA, 5)), encoding="utf-8")
    receipt = tmp_path / "out" / "r.json"
    rc = _run_main(
        monkeypatch,
        [
            "--stage",
            "compare",
            "--repo",
            str(tmp_path),
            "--before",
            str(before),
            "--after",
            str(after),
            "--receipt",
            str(receipt),
        ],
    )
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS"
    assert printed["sha"] is None
    assert json.loads(receipt.read_text(encoding="utf-8"))["status"] == "PASS"


def test_main_compare_requires_before_and_after(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as info:
        _run_main(monkeypatch, ["--stage", "compare", "--repo", str(tmp_path)])
    assert info.value.code == 2
    assert "compare needs --before and --after" in capsys.readouterr().err


def test_main_replay_rejects_short_sha(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit):
        _run_main(
            monkeypatch,
            ["--stage", "replay", "--repo", str(tmp_path), "--expected-sha", "abc"],
        )
    assert "40-character" in capsys.readouterr().err


def test_main_replay_writes_relative_receipt_under_repo(monkeypatch, tmp_path, capsys):
    fake = types.SimpleNamespace(calls=[])

    def fake_replay(repo, sha):
        fake.calls.append((repo, sha))
        return {"status": "FAIL", "source": {}, "tests_executed": None}

    monkeypatch.setattr(mod, "replay", fake_replay)
    rc = _run_main(
        monkeypatch,
        [
            "--stage",
            "replay",
            "--repo",
            str(tmp_path),
            "--expected-sha",
            GOOD_SHA,
            "--receipt",
            "rel/receipt.json",
        ],
    )
    assert rc == 1
    assert fake.calls == [(tmp_path.resolve(), GOOD_SHA)]
    assert (tmp_path.resolve() / "rel" / "receipt.json").is_file()
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"


def test_main_default_stage_calls_run_stage(monkeypatch, tmp_path, capsys):
    seen = []

    def fake_run_stage(repo, stage, expected):
        seen.append((stage, expected))
        return {"status": "PASS", "source": {"head_sha": GOOD_SHA}, "tests_executed": 3}

    monkeypatch.setattr(mod, "run_stage", fake_run_stage)
    rc = _run_main(
        monkeypatch,
        [
            "--stage",
            "pre-commit",
            "--repo",
            str(tmp_path),
            "--receipt",
            str(tmp_path / "r.json"),
        ],
    )
    assert rc == 0
    assert seen == [("pre-commit", None)]
    out = json.loads(capsys.readouterr().out)
    assert out["sha"] == GOOD_SHA
    assert out["tests_executed"] == 3
