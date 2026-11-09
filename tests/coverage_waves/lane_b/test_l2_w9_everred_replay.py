"""Lane-B wave 9: everred_v3 replay manifest checks and merge-tree preview.

Git and the isolated test runner are faked through the module's ``subprocess``
attribute; nothing is executed.
"""

import hashlib
import json
import pathlib
import sys
import types

import pytest

from ._l2_loader import load

fake_fcntl = types.SimpleNamespace(LOCK_EX=2, LOCK_UN=8, flock=lambda fd, op: None)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})
rp = load("tools/everred_v3/src/replay.py", deps={"everred": ev})

TimeoutExpired = rp.subprocess.TimeoutExpired
BASE, CONSUMER, REPAIR, TREE, COMMIT = (c * 40 for c in "abcde")


def _manifest(**overrides):
    m = {
        "schema": "abacus.everred.replay.v1",
        "main_base_sha": BASE,
        "consumer_head_sha": CONSUMER,
        "repair_head_sha": REPAIR,
        "repository": "GBOGEB/ABACUS",
        "root_id": "root-001",
        "test_profile": "unittest",
    }
    m.update(overrides)
    return m


def _proc(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class FakeRunner:
    """Scripted stand-in for subprocess.run that records every call."""

    def __init__(self, **responses):
        self.calls = []
        self.responses = {
            "cat-file": _proc(),
            "merge-base": _proc(),
            "merge-tree": _proc(stdout=TREE + "\nextra\n"),
            "commit-tree": _proc(stdout=COMMIT + "\n"),
            "worktree": _proc(),
            "tests": _proc(stdout="Ran 3 tests\nOK\n"),
        }
        self.responses.update(responses)
        self.make_tests_dir = True

    def __call__(self, cmd, **kwargs):
        self.calls.append((list(cmd), kwargs))
        if cmd[0] == "git":
            sub = cmd[3]
            if sub == "worktree" and cmd[4] == "add" and self.make_tests_dir:
                pathlib.Path(cmd[6], "tests").mkdir()
            response = self.responses[sub]
        else:
            response = self.responses["tests"]
        if isinstance(response, BaseException):
            raise response
        return response


def _install(monkeypatch, runner):
    fake = types.SimpleNamespace(run=runner, TimeoutExpired=TimeoutExpired)
    monkeypatch.setattr(rp, "subprocess", fake)
    return runner


# --- check_manifest -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "manifest",
    [
        _manifest(),
        _manifest(test_profile="pytest-focused", test_path="tests/unit/test_x.py"),
    ],
)
def test_check_manifest_accepts(manifest):
    assert rp.check_manifest(manifest) is manifest


@pytest.mark.parametrize(
    "manifest,message",
    [
        ([], "invalid replay manifest"),
        (_manifest(schema="v0"), "invalid replay manifest"),
        (_manifest(main_base_sha="x"), "missing immutable main_base_sha"),
        (_manifest(consumer_head_sha=None), "missing immutable consumer_head_sha"),
        (_manifest(repair_head_sha="F" * 40), "missing immutable repair_head_sha"),
        (_manifest(repair_head_sha=BASE), "replay snapshots must be distinct"),
        (_manifest(repository="ABACUS"), "repository identity missing"),
        (_manifest(repository=1), "repository identity missing"),
        (_manifest(root_id="r1"), "root identity missing"),
        (_manifest(root_id=12345), "root identity missing"),
        (_manifest(test_profile="nose"), "unsupported test profile"),
        (_manifest(test_profile="pytest-focused"), "unsafe test path"),
        (
            _manifest(test_profile="pytest-focused", test_path="/tests/x.py"),
            "unsafe test path",
        ),
        (
            _manifest(test_profile="pytest-focused", test_path="tests/../x.py"),
            "unsafe test path",
        ),
        (
            _manifest(test_profile="pytest-focused", test_path="tests//x.py"),
            "unsafe test path",
        ),
        (
            _manifest(test_profile="pytest-focused", test_path="tests/./x.py"),
            "unsafe test path",
        ),
        (
            _manifest(test_profile="pytest-focused", test_path="src/test_x.py"),
            "unsafe test path",
        ),
    ],
)
def test_check_manifest_rejections(manifest, message):
    with pytest.raises(ev.InvalidEvidence, match=message):
        rp.check_manifest(manifest)


# --- Preview.git ----------------------------------------------------------------------------------


def test_preview_git_invocation_and_failure(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner(**{"status": _proc(1, "", "E" * 400)}))
    preview = rp.Preview(tmp_path)
    assert preview.checkout == str(tmp_path.resolve())
    assert preview.git("cat-file", "-e", "x").returncode == 0
    cmd, kwargs = runner.calls[0]
    assert cmd == ["git", "-C", preview.checkout, "cat-file", "-e", "x"]
    assert kwargs == {"capture_output": True, "text": True, "timeout": 90}
    assert preview.git("status", ok=False).returncode == 1
    with pytest.raises(ev.InvalidEvidence, match=r"^git status: E{320}$"):
        preview.git("status")


# --- Preview.plan ---------------------------------------------------------------------------------


def test_plan_merge_preview(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner())
    m = _manifest()
    plan = rp.Preview(tmp_path).plan(m)
    assert plan == {
        "schema": "abacus.everred.replay.receipt.v1",
        "repository": "GBOGEB/ABACUS",
        "root_id": "root-001",
        "main_base_sha": BASE,
        "consumer_head_sha": CONSUMER,
        "repair_head_sha": REPAIR,
        "integration_tree_sha": TREE,
        "status": "MERGE_PREVIEW_ONLY",
        "test_profile": "unittest",
        "manifest_sha256": hashlib.sha256(ev.stable_json(m).encode()).hexdigest(),
        "native_consumer_ci": "UNKNOWN",
        "merge_authorized": False,
    }
    subs = [c[0][3:] for c in runner.calls]
    assert subs[:3] == [
        ["cat-file", "-e", f"{s}^{{commit}}"] for s in (BASE, CONSUMER, REPAIR)
    ]
    assert subs[3:5] == [
        ["merge-base", "--is-ancestor", BASE, CONSUMER],
        ["merge-base", "--is-ancestor", BASE, REPAIR],
    ]
    assert subs[5] == [
        "merge-tree",
        "--write-tree",
        f"--merge-base={BASE}",
        CONSUMER,
        REPAIR,
    ]


@pytest.mark.parametrize(
    "merge_tree,detail",
    [
        (_proc(1, "conflict-out", "conflict-err"), "conflict-err"),
        (_proc(1, "conflict-out", ""), "conflict-out"),
        (_proc(0, "  \n", ""), "  \n"),
    ],
)
def test_plan_conflict(tmp_path, monkeypatch, merge_tree, detail):
    _install(monkeypatch, FakeRunner(**{"merge-tree": merge_tree}))
    plan = rp.Preview(tmp_path).plan(_manifest())
    assert plan["status"] == "CONFLICT"
    assert plan["integration_tree_sha"] is None
    assert plan["detail"] == detail
    assert plan["merge_authorized"] is False
    assert "test_profile" not in plan


def test_plan_rejects_missing_commit(tmp_path, monkeypatch):
    _install(monkeypatch, FakeRunner(**{"cat-file": _proc(128, "", "bad object")}))
    with pytest.raises(ev.InvalidEvidence, match="git cat-file: bad object"):
        rp.Preview(tmp_path).plan(_manifest())


def test_plan_rejects_non_ancestral_base(tmp_path, monkeypatch):
    _install(monkeypatch, FakeRunner(**{"merge-base": _proc(1)}))
    with pytest.raises(ev.InvalidEvidence, match="declared base not ancestral"):
        rp.Preview(tmp_path).plan(_manifest())


def test_plan_rejects_invalid_tree(tmp_path, monkeypatch):
    _install(monkeypatch, FakeRunner(**{"merge-tree": _proc(0, "nottree\n")}))
    with pytest.raises(ev.InvalidEvidence, match="invalid merged tree object"):
        rp.Preview(tmp_path).plan(_manifest())


def test_plan_validates_manifest_first(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner())
    with pytest.raises(ev.InvalidEvidence, match="invalid replay manifest"):
        rp.Preview(tmp_path).plan({})
    assert runner.calls == []


# --- Preview.execute ------------------------------------------------------------------------------


def _worktree_paths(runner):
    adds = [c[0] for c in runner.calls if c[0][3:5] == ["worktree", "add"]]
    removes = [c[0] for c in runner.calls if c[0][3:5] == ["worktree", "remove"]]
    return adds, removes


def test_execute_returns_conflict_plan_without_worktree(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner(**{"merge-tree": _proc(1, "", "x")}))
    assert rp.Preview(tmp_path).execute(_manifest())["status"] == "CONFLICT"
    assert all(c[0][3] != "worktree" for c in runner.calls)


def test_execute_without_tests_dir(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner())
    runner.make_tests_dir = False
    plan = rp.Preview(tmp_path).execute(_manifest())
    assert plan["status"] == "ISOLATED_PREVIEW_NO_TESTS"
    assert "test_returncode" not in plan
    adds, removes = _worktree_paths(runner)
    tmp = adds[0][6]
    assert adds[0][3:] == ["worktree", "add", "--detach", tmp, COMMIT]
    assert removes[0][3:] == ["worktree", "remove", "--force", tmp]
    assert not pathlib.Path(tmp).exists()
    commit = [c[0][3:] for c in runner.calls if c[0][3] == "commit-tree"][0]
    assert commit == [
        "commit-tree",
        TREE,
        "-p",
        CONSUMER,
        "-m",
        "EVERRED ephemeral replay - never push",
    ]


@pytest.mark.parametrize(
    "profile,result,status",
    [
        ("unittest", _proc(0, "Ran 3 tests\n", "OK\n"), "ISOLATED_PREVIEW_PASS"),
        ("unittest", _proc(1, "", "FAILED (failures=1)"), "ISOLATED_PREVIEW_RED"),
        ("unittest", _proc(5, "Ran 0 tests\n", ""), "ISOLATED_PREVIEW_NO_TESTS"),
        ("pytest-focused", _proc(5, "", "no tests ran"), "ISOLATED_PREVIEW_NO_TESTS"),
        (
            "pytest-focused",
            _proc(0, "collected 0 items", ""),
            "ISOLATED_PREVIEW_NO_TESTS",
        ),
        ("pytest-focused", _proc(0, "1 passed", ""), "ISOLATED_PREVIEW_PASS"),
    ],
)
def test_execute_runs_isolated_tests(tmp_path, monkeypatch, profile, result, status):
    runner = _install(monkeypatch, FakeRunner(tests=result))
    m = _manifest(test_profile=profile, test_path="tests/test_x.py")
    plan = rp.Preview(tmp_path).execute(m)
    output = result.stdout + result.stderr
    assert plan["status"] == status
    assert plan["test_returncode"] == result.returncode
    assert plan["test_output_sha256"] == hashlib.sha256(output.encode()).hexdigest()
    assert plan["test_output_tail"] == output[-1200:]
    test_cmd, kwargs = [c for c in runner.calls if c[0][0] != "git"][0]
    adds, removes = _worktree_paths(runner)
    tmp = adds[0][6]
    if profile == "unittest":
        assert test_cmd == [
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-q",
        ]
    else:
        assert test_cmd == ["python3", "-m", "pytest", "-q", "tests/test_x.py"]
    assert kwargs["cwd"] == tmp
    assert kwargs["timeout"] == 180
    assert kwargs["env"]["HOME"] == tmp
    assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert len(removes) == 1
    assert not pathlib.Path(tmp).exists()


def test_execute_truncates_output_tail(tmp_path, monkeypatch):
    _install(monkeypatch, FakeRunner(tests=_proc(0, "x" * 2000, "END")))
    plan = rp.Preview(tmp_path).execute(_manifest())
    assert len(plan["test_output_tail"]) == 1200
    assert plan["test_output_tail"].endswith("END")


def test_execute_timeout(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner(tests=TimeoutExpired(["python3"], 180)))
    plan = rp.Preview(tmp_path).execute(_manifest())
    assert plan["status"] == "ISOLATED_PREVIEW_TIMEOUT"
    assert "test_returncode" not in plan
    adds, removes = _worktree_paths(runner)
    assert len(removes) == 1 and not pathlib.Path(adds[0][6]).exists()


def test_execute_cleans_up_when_worktree_add_fails(tmp_path, monkeypatch):
    runner = _install(monkeypatch, FakeRunner(worktree=_proc(1, "", "locked")))
    runner.make_tests_dir = False
    with pytest.raises(ev.InvalidEvidence, match="git worktree: locked"):
        rp.Preview(tmp_path).execute(_manifest())
    adds, removes = _worktree_paths(runner)
    assert len(removes) == 1 and not pathlib.Path(adds[0][6]).exists()


# --- main CLI -------------------------------------------------------------------------------------


def _run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["replay.py", *argv])
    rp.main()


def test_main_plan_prints_and_writes(tmp_path, monkeypatch, capsys):
    runner = _install(monkeypatch, FakeRunner())
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps(_manifest()))
    out = tmp_path / "receipt.json"
    _run_main(
        monkeypatch,
        "--checkout",
        str(tmp_path),
        "--manifest",
        str(manifest),
        "--output",
        str(out),
    )
    printed = capsys.readouterr().out
    written = out.read_text()
    assert printed == written + "\n"
    receipt = json.loads(written)
    assert receipt["status"] == "MERGE_PREVIEW_ONLY"
    assert receipt["provenance"] == "LOCAL_PREVIEW_NOT_NATIVE_CI"
    assert all(c[0][0] == "git" and c[0][3] != "worktree" for c in runner.calls)


def test_main_execute_isolated_without_output(tmp_path, monkeypatch, capsys):
    _install(monkeypatch, FakeRunner())
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps(_manifest()))
    _run_main(
        monkeypatch,
        "--checkout",
        str(tmp_path),
        "--manifest",
        str(manifest),
        "--execute-isolated",
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "ISOLATED_PREVIEW_PASS"
    assert receipt["provenance"] == "LOCAL_PREVIEW_NOT_NATIVE_CI"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["m.json"]


def test_main_requires_arguments(monkeypatch):
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, "--checkout", ".")
