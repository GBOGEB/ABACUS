"""Lane A wave 14: DMAIC_V3.core.handover_bridge caching, provenance and parsing."""

import json
from types import SimpleNamespace

import pytest

from DMAIC_V3.core import handover_bridge as hb


@pytest.fixture
def bridge():
    return hb.HandoverBridge(config=None, state_manager=None)


class Counter:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.result


def test_idempotent_phase_caches():
    func = Counter({"a": 1})
    phase = hb.IdempotentPhase("p", None)
    assert phase.execute(func, 1) == {"a": 1}
    assert phase.execute(func, 2) == {"a": 1}
    assert func.calls == 1


def test_run_lifecycle_and_cache_reset(bridge):
    func = Counter("r")
    run_id = bridge.begin_run("abcdef1234567890")
    assert run_id.endswith("_abcdef12")
    assert bridge.wrap_phase("p", func, 1, k=2) == "r"
    assert bridge.wrap_phase("p", func, 1, k=2) == "r"
    assert func.calls == 1
    bridge.wrap_phase("p", func, 2, k=2)
    assert func.calls == 2
    bridge.begin_run()
    bridge.wrap_phase("p", func, 1, k=2)
    assert func.calls == 3
    bridge.finish_run("success", {"m": 1})
    events = [e["event"] for e in bridge.get_provenance_trail()]
    assert events == ["run_started", "run_started", "run_finished"]


def test_wrap_phase_unserializable_args(bridge):
    func = Counter(5)
    token = object()
    assert bridge.wrap_phase("p", func, token, opt=token) == 5
    assert bridge.wrap_phase("p", func, token, opt=token) == 5
    assert func.calls == 1


def test_logging_and_saving(bridge, tmp_path):
    bridge.begin_run("x")
    bridge.log_action("p1", "act", {"d": 1})
    rec = bridge.record_phase("p1", 1, "success", "ih", "oh", {"q": 0.5})
    assert rec["outputs_hash"] == "oh"
    assert bridge.get_metrics_history()[0]["metrics"] == {"q": 0.5}
    bridge.save_provenance(tmp_path / "prov.json")
    bridge.save_metrics(tmp_path / "met.json")
    prov = json.loads((tmp_path / "prov.json").read_text(encoding="utf-8"))
    assert [e["event"] for e in prov] == ["run_started", "action", "phase"]
    met = json.loads((tmp_path / "met.json").read_text(encoding="utf-8"))
    assert met[0]["phase"] == "p1"


def test_make_idempotent_and_recent_runs(bridge):
    func = Counter(9)
    wrapped = bridge.make_idempotent("deco")(func)
    assert wrapped(1) == 9 and wrapped(1) == 9
    assert func.calls == 1
    for i in range(12):
        bridge.log_action("p", str(i), {})
    assert len(bridge.get_recent_runs(5)) == 5
    assert bridge.get_recent_runs(5)[-1]["action"] == "11"
    assert len(bridge.get_recent_runs(50)) == 12


def test_should_stop_iteration(bridge):
    assert bridge.should_stop_iteration([], []) == (False, "No history available")
    hist = [{"quality_score": 0.5}, {"quality_score": 0.505}]
    stop, reason = bridge.should_stop_iteration(
        hist, [{"type": "max_iterations", "value": 2}]
    )
    assert stop and reason == "Max iterations reached: 2"
    stop, reason = bridge.should_stop_iteration(hist, [{"type": "convergence"}])
    assert stop and reason.startswith("Converged")
    far = [{"quality_score": 0.1}, {"quality_score": 0.9}]
    rules = [{"type": "max_iterations"}, {"type": "convergence"}, {"type": "other"}]
    assert bridge.should_stop_iteration(far, rules) == (False, "Continue iteration")
    one = [{"quality_score": 0.1}]
    assert bridge.should_stop_iteration(one, [{"type": "convergence"}])[0] is False


def test_analyze_convergence(bridge):
    assert bridge.analyze_convergence([]) == {
        "converged": False,
        "reason": "No history",
    }
    assert bridge.analyze_convergence([{}])["reason"] == "Insufficient data"
    res = bridge.analyze_convergence(
        [{"quality_score": 0.1}, {"quality_score": 0.3}, {"quality_score": 0.5}]
    )
    assert res["converged"] is False
    assert res["avg_change"] == pytest.approx(0.2)
    assert res["final_score"] == 0.5
    flat = bridge.analyze_convergence([{"quality_score": 1}, {"quality_score": 1}])
    assert flat["converged"] is True


@pytest.mark.parametrize(
    "result,status,metrics",
    [
        ((True, {"metrics": {"a": 1}}), "success", {"a": 1}),
        ((False, ["list"]), "failed", {}),
        ({"metrics": {"b": 2}}, "success", {"b": 2}),
        ("plain", "success", {}),
    ],
)
def test_idempotent_phase_executor(bridge, result, status, metrics):
    calls = []

    def execute(iteration):
        calls.append(iteration)
        return result

    phase = SimpleNamespace(execute=execute)
    ex = hb.IdempotentPhaseExecutor(phase, bridge, "improve")
    assert ex.execute(3, note="x") == result
    assert ex.execute(3, note="y") == result
    assert calls == [3]
    rec = bridge.get_provenance_trail()[-1]
    assert (rec["status"], rec["metrics"], rec["iteration"]) == (status, metrics, 3)


def test_integrate_phase4_missing_file(tmp_path, capsys):
    phase = SimpleNamespace()
    assert hb.integrate_phase4_opportunities(phase, tmp_path / "none.md") is phase
    assert not hasattr(phase, "opportunities")
    assert "Opportunities file not found" in capsys.readouterr().out


def test_integrate_phase4_opportunities(tmp_path):
    doc = tmp_path / "opps.md"
    doc.write_text(
        "# Intro\n- stray bullet\n"
        "## OPP-1: Reduce complexity hotspots\n"
        "**Priority:** HIGH\n"
        "- split functions\n"
        "- add tests\n"
        "### OPP-2\n"
        "- document modules\n",
        encoding="utf-8",
    )
    phase = hb.integrate_phase4_opportunities(SimpleNamespace(), doc)
    opps = phase.opportunities
    assert [o["id"] for o in opps] == ["OPP-1", "OPP-2"]
    assert opps[0]["priority"] == "HIGH"
    assert opps[0]["actions"] == ["split functions", "add tests"]
    assert opps[1] == {
        "id": "OPP-2",
        "title": "",
        "priority": "MEDIUM",
        "actions": ["document modules"],
        "success_criteria": [],
    }
    recs = [{"issue_type": "high_complexity"}, {"issue_type": "naming"}, {}]
    merged = phase.integrate_opportunities_with_recommendations(recs)
    assert merged[0]["related_recommendations"] == [{"issue_type": "high_complexity"}]
    assert merged[1]["related_recommendations"] == []
