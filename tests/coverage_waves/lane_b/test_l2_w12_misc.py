"""Lane-B wave 12: QPLANT load-test runner and locustfile, alert handler, self-test.

Locust is not a CI dependency, so a minimal ``locust`` stub (HttpUser, task,
tag, between) is injected; the tests then drive each user task against a
recording HTTP client and check endpoints, headers, weights and payloads.
"""

import json
import os
import sys
import types
from datetime import datetime as real_datetime

import pytest

from ._l2_loader import REPO_ROOT, load

# ------------------------------------------------------------------ stubs


def _task(weight=1):
    def deco(fn):
        fn.locust_task_weight = weight
        return fn

    return deco


def _tag(*tags):
    def deco(fn):
        fn.locust_tag_set = set(tags)
        return fn

    return deco


class _HttpUser:
    pass


LOCUST = types.SimpleNamespace(
    HttpUser=_HttpUser,
    task=_task,
    tag=_tag,
    between=lambda lo, hi: ("between", lo, hi),
)

lts = load("qplant/load_testing/load_test_scenarios.py")
lf = load("qplant/load_testing/locustfile.py", deps={"locust": LOCUST})
ah = load("production/monitoring/alert_handler.py")
st = load("self_optimization/self_test.py")

FIXED = real_datetime(2026, 1, 2, 3, 4, 5)


class _Frozen(real_datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED


# --------------------------------------------------------- load scenarios


class _Run:
    def __init__(self, mod, code=0, exc=None):
        self.mod = mod
        self.code = code
        self.exc = exc
        self.calls = []

    def __call__(self, cmd, cwd):
        self.calls.append((list(cmd), cwd))
        if self.exc:
            raise self.exc
        return types.SimpleNamespace(returncode=self.code)


def test_scenarios_table_is_consistent():
    assert set(lts.SCENARIOS) == {
        "smoke_test",
        "normal_load",
        "peak_load",
        "stress_test",
        "endurance_test",
    }
    for spec in lts.SCENARIOS.values():
        assert spec["spawn_rate"] <= spec["users"]
        assert spec["run_time"].endswith("m")
    assert lts.SCENARIOS["stress_test"]["tags"] == ["stress"]


def test_run_scenario_unknown(capsys):
    assert lts.run_scenario("nope") == 1
    out = capsys.readouterr().out
    assert "Unknown scenario: nope" in out
    assert "smoke_test, normal_load" in out


def test_run_scenario_builds_locust_command(tmp_path, monkeypatch, capsys):
    runner = _Run(lts, code=7)
    monkeypatch.setattr(lts.subprocess, "run", runner)
    monkeypatch.setattr(lts, "datetime", _Frozen)
    report_dir = str(tmp_path / "rep")
    assert lts.run_scenario("smoke_test", "http://h:1", report_dir) == 7
    assert (tmp_path / "rep").is_dir()
    ((cmd, cwd),) = runner.calls
    stem = report_dir + "/load_test_smoke_test_20260102_030405"
    assert cmd == [
        "locust",
        "-f",
        "locustfile.py",
        "--host",
        "http://h:1",
        "--headless",
        "--users",
        "10",
        "--spawn-rate",
        "2",
        "--run-time",
        "2m",
        "--html",
        stem + ".html",
        "--csv",
        stem,
    ]
    assert cwd == str(REPO_ROOT / "qplant" / "load_testing")
    out = capsys.readouterr().out
    assert "Running scenario: smoke_test" in out
    assert "Users: 10, Spawn: 2/s, Duration: 2m" in out


def test_run_scenario_appends_tags(tmp_path, monkeypatch):
    runner = _Run(lts)
    monkeypatch.setattr(lts.subprocess, "run", runner)
    assert lts.run_scenario("stress_test", report_dir=str(tmp_path)) == 0
    cmd = runner.calls[0][0]
    assert cmd[-2:] == ["--tags", "stress"]
    assert cmd[cmd.index("--host") + 1] == "http://localhost:8000"


def test_run_scenario_locust_missing(tmp_path, monkeypatch, capsys):
    runner = _Run(lts, exc=FileNotFoundError("locust"))
    monkeypatch.setattr(lts.subprocess, "run", runner)
    assert lts.run_scenario("peak_load", report_dir=str(tmp_path)) == 1
    assert "Locust not installed" in capsys.readouterr().out


def _main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["load_test_scenarios.py", *argv])
    return lts.main()


def test_main_list(monkeypatch, capsys):
    assert _main(monkeypatch, "--list") is None
    out = capsys.readouterr().out
    assert out.startswith("Available Load Test Scenarios:")
    assert "endurance_test" in out and "Users: 150, Duration: 60m" in out


def test_main_export_json(tmp_path, monkeypatch, capsys):
    target = tmp_path / "s.json"
    _main(monkeypatch, "--export-json", str(target))
    assert json.loads(target.read_text()) == lts.SCENARIOS
    assert "Scenarios exported to" in capsys.readouterr().out


def test_main_scenario_exits_with_runner_code(monkeypatch):
    seen = []

    def fake(name, host):
        seen.append((name, host))
        return 3

    monkeypatch.setattr(lts, "run_scenario", fake)
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--scenario", "smoke_test", "--host", "http://x")
    assert exc.value.code == 3
    assert seen == [("smoke_test", "http://x")]


def test_main_without_args_prints_help(monkeypatch, capsys):
    _main(monkeypatch)
    assert "QPLANT Load Test Runner" in capsys.readouterr().out


# -------------------------------------------------------------- locustfile


class _Client:
    def __init__(self):
        self.calls = []

    def get(self, path, headers):
        self.calls.append(("GET", path, None, headers))

    def post(self, path, json, headers):
        self.calls.append(("POST", path, json, headers))


FAKE_RANDOM = types.SimpleNamespace(
    choice=lambda seq: seq[-1],
    uniform=lambda lo, hi: hi,
    randint=lambda lo, hi: lo,
)


def _user(cls, monkeypatch, key=None):
    if key is None:
        monkeypatch.delenv("QPLANT_API_KEY", raising=False)
    else:
        monkeypatch.setenv("QPLANT_API_KEY", key)
    monkeypatch.setattr(lf, "random", FAKE_RANDOM)
    user = cls()
    user.client = _Client()
    user.on_start()
    return user


def test_user_classes_wait_times():
    assert issubclass(lf.QPLANTAPIUser, _HttpUser)
    assert lf.QPLANTAPIUser.wait_time == ("between", 1, 3)
    assert lf.StressTestUser.wait_time == ("between", 0.1, 0.5)


def test_on_start_default_and_env_key(monkeypatch):
    assert _user(lf.QPLANTAPIUser, monkeypatch).headers == {
        "X-API-Key": "qplant_TEST_KEY"
    }
    assert _user(lf.StressTestUser, monkeypatch, "k-1").headers == {"X-API-Key": "k-1"}


@pytest.mark.parametrize(
    "task, weight, tags, path",
    [
        ("get_health", 10, {"read", "config"}, "/api/v1/health"),
        ("get_config_summary", 8, {"read", "config"}, "/api/v1/config"),
        ("get_compressor_specs", 6, {"read", "config"}, "/api/v1/compressors/specs"),
        (
            "get_config_section",
            5,
            {"read", "config"},
            "/api/v1/config/pressure_parameters",
        ),
        ("visualization_catalog", 1, {"read"}, "/api/v1/visualizations/catalog"),
        ("build_status", 1, {"read"}, "/api/v1/build/status"),
    ],
)
def test_read_tasks(monkeypatch, task, weight, tags, path):
    user = _user(lf.QPLANTAPIUser, monkeypatch, "k-2")
    fn = getattr(lf.QPLANTAPIUser, task)
    assert fn.locust_task_weight == weight
    assert fn.locust_tag_set == tags
    fn(user)
    assert user.client.calls == [("GET", path, None, {"X-API-Key": "k-2"})]


def test_leak_rate_tasks(monkeypatch):
    user = _user(lf.QPLANTAPIUser, monkeypatch)
    lf.QPLANTAPIUser.calculate_leak_rate(user)
    lf.QPLANTAPIUser.calculate_leak_rate_batch(user)
    single, batch = user.client.calls
    assert single[:2] == ("POST", "/api/v1/leak-rate")
    assert single[2] == {
        "leak_rate_mbar_l_s": 1e-3,
        "temperature_k": 300,
        "pressure_bar_abs": 15,
    }
    assert batch[:2] == ("POST", "/api/v1/leak-rate/batch")
    assert batch[2]["he_price_eur_kg"] == 120.0
    assert batch[2]["items"] == [single[2]] * 3
    assert lf.QPLANTAPIUser.calculate_leak_rate.locust_task_weight == 4


def test_compressor_and_monte_carlo_tasks(monkeypatch):
    user = _user(lf.QPLANTAPIUser, monkeypatch)
    lf.QPLANTAPIUser.compressor_reliability(user)
    lf.QPLANTAPIUser.monte_carlo(user)
    rel, mc = user.client.calls
    assert rel[1] == "/api/v1/compressors/reliability"
    assert rel[2] == {
        "total_units": 4,
        "required_units": 3,
        "mtbf_hours": 8760,
        "mttr_hours": 8,
        "has_vfd": False,
    }
    assert mc[1] == "/api/v1/monte-carlo"
    assert mc[2]["he_price_min"] < mc[2]["he_price_mode"] < mc[2]["he_price_max"]
    assert mc[2]["n_simulations"] == 1000
    assert lf.QPLANTAPIUser.monte_carlo.locust_tag_set == {"compute", "monte-carlo"}


def test_stress_user_tasks(monkeypatch):
    user = _user(lf.StressTestUser, monkeypatch)
    for name in ("rapid_health", "rapid_config", "rapid_leak_rate"):
        fn = getattr(lf.StressTestUser, name)
        assert fn.locust_tag_set == {"stress"}
        fn(user)
    assert [c[:2] for c in user.client.calls] == [
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/config"),
        ("POST", "/api/v1/leak-rate"),
    ]
    assert user.client.calls[2][2]["pressure_bar_abs"] == 1.013
    weights = [
        getattr(lf.StressTestUser, n).locust_task_weight
        for n in ("rapid_health", "rapid_config", "rapid_leak_rate")
    ]
    assert weights == [5, 3, 2]


# ------------------------------------------------------------ alert handler


@pytest.fixture
def alert_ws(tmp_path, monkeypatch):
    (tmp_path / "production" / "logs").mkdir(parents=True)
    (tmp_path / "production" / "monitoring").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ah, "datetime", _Frozen)
    return tmp_path


def test_trigger_alert_creates_log_and_history(alert_ws):
    ah.trigger_alert("Disk", "warning", "90% full")
    log = (alert_ws / "production/logs/alerts.log").read_text().splitlines()
    alert = {
        "timestamp": "2026-01-02T03:04:05",
        "rule": "Disk",
        "severity": "warning",
        "message": "90% full",
    }
    assert [json.loads(x) for x in log] == [alert]
    hist = json.loads(
        (alert_ws / "production/monitoring/alerts_history.json").read_text()
    )
    assert hist == [alert]


def test_trigger_alert_appends_and_keeps_last_100(alert_ws):
    hist_path = alert_ws / "production/monitoring/alerts_history.json"
    hist_path.write_text(json.dumps([{"rule": i} for i in range(100)]))
    ah.trigger_alert("New", "info", "m")
    hist = json.loads(hist_path.read_text())
    assert len(hist) == 100
    assert hist[0] == {"rule": 1}
    assert hist[-1]["rule"] == "New"


def test_trigger_alert_requires_log_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        ah.trigger_alert("x", "info", "m")


# ---------------------------------------------------------------- self test

PHASES = [
    "phase0_init",
    "phase1_define",
    "phase2_measure",
    "phase3_analyze",
    "phase4_improve",
    "phase5_control",
]


class _Version(tuple):
    major = property(lambda self: self[0])
    minor = property(lambda self: self[1])


def _dmaic(root, phases=PHASES):
    (root / "DMAIC_V3" / "phases").mkdir(parents=True)
    (root / "DMAIC_V3" / "full_pipeline_orchestrator.py").write_text("")
    for name in phases:
        (root / "DMAIC_V3" / "phases" / (name + ".py")).write_text("")


@pytest.fixture
def st_ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_self_test_all_pass(st_ws, monkeypatch):
    monkeypatch.setattr(
        st, "sys", types.SimpleNamespace(version_info=_Version((3, 12)))
    )
    _dmaic(st_ws)
    assert st.self_test() == {
        "python_version": "3.12",
        "dependencies_installed": True,
        "output_dirs_writable": True,
        "dmaic_phases_executable": True,
    }
    assert (st_ws / "DMAIC_V3_OUTPUT").is_dir()


def test_self_test_old_python_and_missing_orchestrator(st_ws, monkeypatch):
    monkeypatch.setattr(
        st, "sys", types.SimpleNamespace(version_info=_Version((3, 11)))
    )
    (st_ws / "DMAIC_V3_OUTPUT").mkdir()
    res = st.self_test()
    assert res["python_version"] == "3.11"
    assert res["dmaic_phases_executable"] is False


def test_self_test_missing_phase_module(st_ws):
    _dmaic(st_ws, PHASES[:3])
    assert st.self_test()["dmaic_phases_executable"] is False


def test_self_test_missing_deps_and_unwritable_output(st_ws, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)

    def boom(path):
        raise OSError("read-only")

    monkeypatch.setattr(os, "makedirs", boom)
    res = st.self_test()
    assert res["dependencies_installed"] is False
    assert res["output_dirs_writable"] is False
