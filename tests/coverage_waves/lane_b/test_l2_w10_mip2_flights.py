"""Lane-B wave 10: MIP3 pre/postflight receipts and MIP2 local testflight."""

import json
import sys
import types

import pytest

from ._l2_loader import load

fl = load("tools/mip2/mip3_flight.py")
lt = load("tools/mip2/local_testflight.py")

HEAD = "f" * 40
REGISTRY = "tools/mip2/method_qualification_registry.json"
CORPUS = "tools/mip2/method_regression_corpus.json"


def _proc(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class FakeRun:
    """Record argv and answer from a per-program table."""

    def __init__(self, table=None, default=None):
        self.table = table or {}
        self.default = default if default is not None else _proc()
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        key = argv[0] if argv[0] == "git" else argv[-1]
        answer = self.table.get(key, self.default)
        if isinstance(answer, BaseException):
            raise answer
        return answer


def _clock(monkeypatch, mod):
    ticks = iter(x * 0.5 for x in range(1000))
    monkeypatch.setattr(mod.time, "monotonic", lambda: next(ticks))


# ------------------------------------------------------------------ cmd


def test_cmd_success_tails_output(monkeypatch):
    _clock(monkeypatch, fl)
    fake = FakeRun(default=_proc(3, "o" * 2500, "err"))
    monkeypatch.setattr(fl.subprocess, "run", fake)
    out = fl.cmd(["x"])
    assert out["exit_code"] == 3 and out["duration_s"] == 0.5
    assert len(out["stdout_tail"]) == 2000 and out["stderr_tail"] == "err"
    assert fake.calls[0][1]["timeout"] == 120 and fake.calls[0][1]["cwd"] == fl.ROOT


@pytest.mark.parametrize(
    "exc,name",
    [
        (OSError("nope"), "OSError"),
        (fl.subprocess.TimeoutExpired(["x"], 120), "TimeoutExpired"),
    ],
)
def test_cmd_errors(monkeypatch, exc, name):
    _clock(monkeypatch, fl)
    monkeypatch.setattr(fl.subprocess, "run", FakeRun(default=exc))
    assert fl.cmd(["x"]) == {"exit_code": None, "duration_s": 0.5, "error": name}


def test_tool_inventory(monkeypatch):
    monkeypatch.setattr(
        fl.shutil, "which", lambda n: "/bin/" + n if n == "black" else None
    )
    tools = fl.tool_inventory()
    assert len(tools) == len(fl.METHODS)
    by = {t["tool"]: t for t in tools}
    assert by["black"]["qualification"] == "DISCOVERED_ONLY"
    assert by["mypy"] == {
        "tool": "mypy",
        "present_on_path": False,
        "qualification": "NOT_FOUND_ON_PATH",
    }


def test_digest(tmp_path):
    p = tmp_path / "a"
    p.write_bytes(b"abc")
    assert fl.digest(p).startswith("ba7816bf")


# ---------------------------------------------------------------- junit


def _suite(tests=4, failures=0, errors=0, skipped=0):
    return '<testsuite tests="%s" failures="%s" errors="%s" skipped="%s"/>' % (
        tests,
        failures,
        errors,
        skipped,
    )


def _xml(tmp_path, text, name="j.xml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_junit_single_suite(tmp_path):
    assert fl.junit(_xml(tmp_path, _suite(5, 1, 0, 1))) == {
        "tests": 5,
        "failures": 1,
        "errors": 0,
        "skipped": 1,
    }


def test_junit_suites_are_summed(tmp_path):
    text = "<testsuites>" + _suite(2) + _suite(3, 0, 1, 0) + "</testsuites>"
    assert fl.junit(_xml(tmp_path, text))["tests"] == 5


@pytest.mark.parametrize(
    "text,match",
    [
        ("<report/>", "JUNIT_INVALID_ROOT"),
        ("<testsuites/>", "JUNIT_MISSING_SUITES"),
        ('<testsuite failures="0" errors="0" skipped="0"/>', "JUNIT_INVALID_TESTS"),
        (_suite("-1"), "JUNIT_INVALID_TESTS"),
        (_suite(1, 1, 1, 0), "JUNIT_INCONSISTENT_COUNTS"),
    ],
)
def test_junit_rejections(tmp_path, text, match):
    with pytest.raises(ValueError, match=match):
        fl.junit(_xml(tmp_path, text))


def test_junit_too_large():
    big = types.SimpleNamespace(stat=lambda: types.SimpleNamespace(st_size=2**26 + 1))
    with pytest.raises(ValueError, match="JUNIT_XML_TOO_LARGE"):
        fl.junit(big)


# ----------------------------------------------------------------- main


@pytest.fixture
def flight(tmp_path, monkeypatch):
    monkeypatch.setattr(fl, "ROOT", tmp_path)
    monkeypatch.setattr(fl.shutil, "which", lambda n: None)
    monkeypatch.setattr(fl.platform, "platform", lambda: "TestOS-1")
    _clock(monkeypatch, fl)
    fake = FakeRun({"git": _proc(0, HEAD + "\n")})
    monkeypatch.setattr(fl.subprocess, "run", fake)
    (tmp_path / "tools" / "mip2").mkdir(parents=True)
    for name in (REGISTRY, CORPUS):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    out = tmp_path / "receipt-out.json"

    def run(*extra):
        monkeypatch.setattr(
            sys, "argv", ["mip3_flight", "--output", str(out)] + list(extra)
        )
        rc = fl.main()
        return rc, json.loads(out.read_text(encoding="utf-8"))

    run.fake = fake
    run.root = tmp_path
    return run


def test_preflight_pass(flight, capsys):
    rc, data = flight("--phase", "preflight")
    assert rc == 0 and data["status"] == "PASS"
    assert data["head_sha"] == HEAD and data["environment"]["os"] == "TestOS-1"
    assert set(data["checks"]) == {"syntax", "contracts"}
    assert data["artifacts"][REGISTRY]["bytes"] == 2
    assert data["admission"] == "NOT_MERGE_AUTHORITY"
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
    assert flight.fake.calls[0][0] == ["git", "rev-parse", "HEAD"]


def test_preflight_hold_without_git_and_missing_artifact(flight):
    flight.fake.table["git"] = _proc(128, "", "fatal")
    (flight.root / CORPUS).unlink()
    rc, data = flight("--phase", "preflight")
    assert rc == 1 and data["status"] == "HOLD"
    assert data["head_sha"] is None
    assert data["artifacts"][CORPUS] == {"missing": True}


def test_preflight_hold_on_failed_check(flight):
    flight.fake.table["tools/mip2"] = _proc(1)
    rc, data = flight("--phase", "preflight")
    assert rc == 1 and data["checks"]["syntax"]["exit_code"] == 1


def _post_files(root, junit_text=None, receipt=None):
    if junit_text is not None:
        (root / "j.xml").write_text(junit_text, encoding="utf-8")
    if receipt is not None:
        (root / "r.json").write_text(receipt, encoding="utf-8")
    return ("--phase", "postflight", "--junit", "j.xml", "--receipt", "r.json")


def test_postflight_pass(flight):
    args = _post_files(
        flight.root, _suite(4), json.dumps({"status": "PASS", "head_sha": HEAD})
    )
    rc, data = flight(*args)
    assert rc == 0 and data["status"] == "PASS"
    assert data["junit"]["tests"] == 4
    assert data["local_flight"] == {
        "status": "PASS",
        "head_sha": HEAD,
        "sha_matches": True,
    }
    assert "sha256" in data["artifacts"]["junit"]
    assert "checks" in data and data["checks"] == {}


def test_postflight_hold_when_inputs_missing(flight):
    rc, data = flight(*_post_files(flight.root))
    assert rc == 1 and data["status"] == "HOLD"
    assert data["artifacts"]["junit"] == {"missing": True}
    assert "junit" not in data and "local_flight" not in data


def test_postflight_sha_mismatch(flight):
    args = _post_files(
        flight.root, _suite(4), json.dumps({"status": "PASS", "head_sha": "0" * 40})
    )
    rc, data = flight(*args)
    assert rc == 1 and data["local_flight"]["sha_matches"] is False


@pytest.mark.parametrize(
    "text,error",
    [
        ("<testsuite", "ParseError"),
        (
            '<!DOCTYPE x [<!ENTITY e "boom">]><testsuite tests="&e;"/>',
            "EntitiesForbidden",
        ),
        ("<report/>", "ValueError"),
    ],
)
def test_postflight_junit_errors(flight, text, error):
    rc, data = flight(*_post_files(flight.root, text, "{not json"))
    assert rc == 1
    assert data["junit_error"] == error
    assert data["local_flight"] == {"status": "INVALID"}


# ------------------------------------------------------- local_testflight


def test_command_pass_and_fail(monkeypatch):
    _clock(monkeypatch, lt)
    monkeypatch.setattr(lt.subprocess, "run", FakeRun(default=_proc(0, "secret")))
    ok = lt.command("syntax", ["x"])
    assert ok == {"name": "syntax", "status": "PASS", "exit_code": 0, "elapsed_s": 0.5}
    monkeypatch.setattr(lt.subprocess, "run", FakeRun(default=_proc(2)))
    assert lt.command("git-head", ["git"])["status"] == "FAIL"


def test_command_git_head_validation(monkeypatch):
    _clock(monkeypatch, lt)
    monkeypatch.setattr(lt.subprocess, "run", FakeRun(default=_proc(0, HEAD + "\n")))
    assert lt.command("git-head", ["git"])["head_sha"] == HEAD
    monkeypatch.setattr(lt.subprocess, "run", FakeRun(default=_proc(0, "not-a-sha")))
    bad = lt.command("git-head", ["git"])
    assert bad["status"] == "FAIL" and bad["error_type"] == "INVALID_GIT_SHA"
    assert "head_sha" not in bad


@pytest.mark.parametrize(
    "exc,name",
    [
        (OSError("x"), "OSError"),
        (lt.subprocess.TimeoutExpired(["x"], 180), "TimeoutExpired"),
    ],
)
def test_command_errors(monkeypatch, exc, name):
    _clock(monkeypatch, lt)
    monkeypatch.setattr(lt.subprocess, "run", FakeRun(default=exc))
    assert lt.command("syntax", ["x"]) == {
        "name": "syntax",
        "status": "ERROR",
        "elapsed_s": 0.5,
        "error_type": name,
    }


@pytest.fixture
def testflight(tmp_path, monkeypatch):
    _clock(monkeypatch, lt)
    fake = FakeRun({"git": _proc(0, HEAD + "\n")})
    monkeypatch.setattr(lt.subprocess, "run", fake)
    out = tmp_path / "local.json"

    def run(*extra):
        monkeypatch.setattr(sys, "argv", ["lt", "--output", str(out)] + list(extra))
        rc = lt.main()
        return rc, json.loads(out.read_text(encoding="utf-8"))

    run.fake = fake
    return run


def test_testflight_fast_pass(testflight, capsys):
    rc, data = testflight()
    assert rc == 0 and data["status"] == "PASS" and data["mode"] == "fast"
    assert data["head_sha"] == HEAD and data["expected_head_matches"] is True
    assert [c["name"] for c in data["checks"]] == ["syntax", "contracts", "git-head"]
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS" and len(printed["checks"]) == 3


def test_testflight_full_with_matching_expected_head(testflight):
    rc, data = testflight("--mode", "full", "--expected-head", HEAD)
    assert rc == 0 and data["expected_head_sha"] == HEAD
    assert data["checks"][2]["name"] == "seeded-methods"
    assert "--junitxml=mip2-local-junit.xml" in testflight.fake.calls[2][0]


def test_testflight_expected_head_mismatch(testflight):
    rc, data = testflight("--expected-head", "0" * 40)
    assert rc == 1 and data["status"] == "FAIL"
    assert data["expected_head_matches"] is False


def test_testflight_invalid_git(testflight):
    testflight.fake.table["git"] = _proc(0, "garbage")
    rc, data = testflight("--expected-head", HEAD)
    assert rc == 1 and data["head_sha"] is None
    assert data["expected_head_matches"] is False


def test_testflight_failed_step(testflight):
    testflight.fake.table["tools/mip2/validate_method_contracts.py"] = _proc(1)
    rc, data = testflight()
    assert rc == 1 and data["checks"][1]["status"] == "FAIL"
    assert data["qualification"] == "LOCAL_ONLY_NOT_MERGE_AUTHORITY"
