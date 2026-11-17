"""Behaviour tests for tools/everred_v3/scripts/four_plane_preflight.py.

The real ``four_planes`` and ``yaml_control`` modules validate the real
workflow/federation YAML. ``runtime_probe`` is replaced by an in-memory stub so
no socket, subprocess, compiler or debugger is ever touched.
"""

import importlib.util
import json
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/four_plane_preflight.py"
SCRIPT = REPO_ROOT / REL
REPO = "GBOGEB/ABACUS"
SHA = "c" * 40
EXEC_SHA = "d" * 40

fp = load("tools/everred_v3/src/four_planes.py", name="abn_w4_fpp_four_planes")
_saved_path = list(sys.path)
yc = load(
    "tools/everred_v3/src/yaml_control.py",
    name="abn_w4_fpp_yaml_control",
    deps={"four_planes": fp},
)
sys.path[:] = _saved_path


def _observe_host(source, *, port_probe=False):
    ports = [dict(port=4242, state="OBSERVED_CLOSED")] if port_probe else []
    data = dict(
        os_family="OTHER",
        os_release="stub",
        kernel="0",
        architecture="stub64",
        ports=ports,
        evidence_status="LOCAL_HOST_OBSERVED_NOT_REMOTE_RHEL_PROOF",
    )
    return fp.runtime_receipt(source, data, trust="LOCAL_OBSERVED")


def _observe_lldb():
    return {"lldb_cli": "UNAVAILABLE", "real_step_count": None}


def _observe_docker():
    return {"docker_cli": "UNAVAILABLE", "daemon": "UNKNOWN", "containers": None}


def _probe_unavailable(source):
    return {}, {"status": "UNAVAILABLE", "real_step_count": None}


def _stub_runtime_probe():
    stub = types.ModuleType("runtime_probe")
    stub.observe_host = _observe_host
    stub.observe_lldb_availability = _observe_lldb
    stub.observe_docker_availability = _observe_docker
    stub.probe_debug_target = _probe_unavailable
    return stub


DEPS = {
    "four_planes": fp,
    "yaml_control": yc,
    "runtime_probe": _stub_runtime_probe(),
}

_saved_path = list(sys.path)
mod = load(REL, name="abn_w4_four_plane_preflight", deps=DEPS)
sys.path[:] = _saved_path


def _probe_steps(steps):
    def probe(source):
        dbg = dict(
            tool="LLDB",
            session_id="local-stub",
            binary_build_id="b" * 64,
            verified_step_count=steps,
            breakpoints=["square"],
            frames=[],
        )
        receipt = fp.diagnostic_receipt(source, dbg, trust="LOCAL_OBSERVED")
        return receipt, {"status": "LOCAL_PROBE_OBSERVED", "real_step_count": steps}

    return probe


@pytest.fixture
def outcomes(monkeypatch):
    seen = []
    real = mod.evaluate_dispatch

    def spy(plan, observed):
        seen.append(dict(observed))
        return real(plan, observed)

    monkeypatch.setattr(mod, "evaluate_dispatch", spy)
    return seen


def test_execute_default_has_single_host_receipt(outcomes, monkeypatch):
    def forbidden(source):
        raise AssertionError("debug probe must not run unless requested")

    monkeypatch.setattr(mod, "probe_debug_target", forbidden)
    result = mod.execute(REPO, SHA, 7)

    assert result["schema"] == "abacus.everred.four_plane.preflight.v1"
    assert result["source_binding"] == {
        "repository": REPO,
        "source_sha": SHA,
        "run_id": 7,
        "job_id": None,
        "executed_sha": None,
    }
    assert result["debugger_execution"] == {
        "status": "NOT_REQUESTED",
        "real_step_count": None,
    }
    assert len(result["receipts"]) == 1
    host = result["receipts"][0]
    assert host["plane"] == "runtime"
    assert host["data"]["ports"][0]["port"] == 4242
    assert result["joined_census"]["observation_count"] == 1
    assert result["plan"]["task_count"] == len(result["dispatch_preview"]["tasks"])
    assert result["plan"]["task_count"] > 0
    assert result["federation"]
    assert result["claims"]["admission"] == "HOLD"
    assert result["docker_availability"]["docker_cli"] == "UNAVAILABLE"
    assert result["debugger_availability"]["lldb_cli"] == "UNAVAILABLE"
    assert outcomes == [{"YAML_PREFLIGHT": "PASS", "RUNTIME_HOST": "PASS"}]
    body = {k: v for k, v in result.items() if k != "result_digest"}
    assert result["result_digest"] == fp.fingerprint(body)


def test_execute_is_deterministic(outcomes):
    first = mod.execute(REPO, SHA, 7)
    second = mod.execute(REPO, SHA, 7)
    assert first["result_digest"] == second["result_digest"]


def test_execute_with_real_debug_steps_marks_lldb_pass(outcomes, monkeypatch):
    monkeypatch.setattr(mod, "probe_debug_target", _probe_steps(1))
    result = mod.execute(REPO, SHA, 9, probe_lldb=True, job_id=3, executed_sha=EXEC_SHA)
    assert len(result["receipts"]) == 2
    assert result["receipts"][1]["plane"] == "diagnostic"
    assert result["joined_census"]["observation_count"] == 2
    assert result["joined_census"]["groups"][0]["job_ids"] == [3]
    assert result["source_binding"]["executed_sha"] == EXEC_SHA
    assert outcomes[-1]["DEBUG_LLDB"] == "PASS"
    assert result["debugger_execution"]["real_step_count"] == 1


def test_execute_with_zero_debug_steps_does_not_claim_pass(outcomes, monkeypatch):
    monkeypatch.setattr(mod, "probe_debug_target", _probe_steps(0))
    result = mod.execute(REPO, SHA, 9, probe_lldb=True)
    assert len(result["receipts"]) == 2
    assert "DEBUG_LLDB" not in outcomes[-1]


def test_execute_with_unavailable_probe_keeps_one_receipt(outcomes):
    result = mod.execute(REPO, SHA, 9, probe_lldb=True)
    assert len(result["receipts"]) == 1
    assert result["debugger_execution"]["status"] == "UNAVAILABLE"
    assert "DEBUG_LLDB" not in outcomes[-1]


def test_execute_writes_output_file(tmp_path):
    dest = tmp_path / "deep" / "dir" / "pre.json"
    result = mod.execute(REPO, SHA, 5, output=str(dest))
    written = json.loads(dest.read_text(encoding="utf-8"))
    assert written == result
    assert dest.read_bytes().endswith(b"\n")


@pytest.mark.parametrize(
    "repo, sha, run_id",
    [("not a repo", SHA, 1), (REPO, "abc", 1), (REPO, SHA, 0)],
)
def test_execute_rejects_invalid_source(repo, sha, run_id):
    with pytest.raises(fp.EvidenceError):
        mod.execute(repo, sha, run_id)


def _argv(tmp_path, *extra):
    out = tmp_path / "cli.json"
    base = ["--repo", REPO, "--sha", SHA, "--run-id", "11", "--output", str(out)]
    return out, base + list(extra)


def test_main_prints_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "probe_debug_target", _probe_steps(1))
    out, args = _argv(
        tmp_path, "--job-id", "4", "--executed-sha", EXEC_SHA, "--probe-lldb"
    )
    monkeypatch.setattr(sys, "argv", ["prog"] + args)
    mod.main()
    summary = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert summary["result_digest"] == written["result_digest"]
    assert summary["joined_observations"] == 2
    assert summary["runtime_os"] == "OTHER"
    assert summary["debugger_session_status"] == "LOCAL_PROBE_OBSERVED"
    assert summary["admission"] == "HOLD"
    assert summary["plan_tasks"] == written["plan"]["task_count"]
    assert written["source_binding"]["job_id"] == 4


def test_main_requires_repo(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--sha", SHA, "--run-id", "1"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2
    assert "--repo" in capsys.readouterr().err


def test_script_entry_point_runs_main(tmp_path, monkeypatch, capsys):
    out, args = _argv(tmp_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)] + args)
    spec = importlib.util.spec_from_file_location("__main__", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    saved = {key: sys.modules.get(key) for key in DEPS}
    sys.modules.update(DEPS)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_path
        for key, previous in saved.items():
            if previous is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = previous
    summary = json.loads(capsys.readouterr().out)
    assert summary["debugger_session_status"] == "NOT_REQUESTED"
    assert summary["joined_observations"] == 1
    assert out.is_file()
