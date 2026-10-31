"""Behaviour tests for MIP/G3CS_CONVERGENCE_V2/observatory/w10/trigger_events.py."""

import copy
import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

te = load("MIP/G3CS_CONVERGENCE_V2/observatory/w10/trigger_events.py")

SHA_A = "a" * 40


def make_graph():
    def edge(src, dst, kind):
        return {
            "from": src,
            "to": dst,
            "type": kind,
            "authority_transfer": False,
            "admission_credit": False,
        }

    return {
        "schema": "codepurple.spine.w11.typed-dag.v1",
        "admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        "edges": [
            edge("a", "b", "CONSUMES"),
            edge("b", "c", "MEASURES"),
            edge("a", "c", "OWNS"),
        ],
    }


def make_step(step_id, src="a", dst="b", kind="CONSUMES", **over):
    step = {
        "step_id": step_id,
        "from": src,
        "to": dst,
        "type": kind,
        "fired": True,
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:00:05Z",
        "conclusion": "success",
        "first_red_signature": None,
    }
    step.update(over)
    return step


def make_packet():
    return {
        "schema": te.SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "governance": {
            "merge_admission": "HOLD",
            "security_waiver": False,
            "authority_transfer": False,
            "accepted_rex": None,
            "crew_worker_id": None,
        },
        "waves": [
            {
                "wave_id": "N+1",
                "source_sha": SHA_A,
                "run_id": 10,
                "attempt": 1,
                "source_clock": "EXACT_PR_HEAD",
                "jobs": [
                    {
                        "job_id": 100,
                        "steps": [
                            make_step(1),
                            make_step(
                                2,
                                "b",
                                "c",
                                "MEASURES",
                                conclusion="failure",
                                first_red_signature="boom",
                            ),
                            make_step(
                                3, "a", "c", "OWNS", fired=False, conclusion="skipped"
                            ),
                        ],
                    }
                ],
            },
            {
                "wave_id": "N+2",
                "source_sha": "b" * 40,
                "run_id": 11,
                "attempt": 1,
                "source_clock": "SERIAL_MAIN",
                "jobs": [{"job_id": 200, "steps": [make_step(1)]}],
            },
        ],
    }


def test_fail_and_positive():
    te.fail(True, "x")
    with pytest.raises(ValueError, match="x"):
        te.fail(False, "x")
    assert te.positive(3, "n") == 3
    for bad in (0, -1, True, 1.0, None):
        with pytest.raises(ValueError, match="n requires positive integer"):
            te.positive(bad, "n")


def test_parse_utc():
    dt = te.parse_utc("2026-01-02T03:04:05Z")
    assert (dt.year, dt.hour, dt.utcoffset().total_seconds()) == (2026, 3, 0)
    for bad in (None, "2026-01-02 03:04:05", "2026-01-02T03:04:05+00:00"):
        with pytest.raises(ValueError, match="canonical UTC"):
            te.parse_utc(bad)
    with pytest.raises(ValueError, match="invalid UTC timestamp"):
        te.parse_utc("2026-13-02T03:04:05Z")


def test_graph_edges_returns_typed_pairs():
    pairs = te.graph_edges(make_graph())
    assert pairs == {("a", "b", "CONSUMES"), ("b", "c", "MEASURES"), ("a", "c", "OWNS")}


def test_graph_edges_rejects_cycle():
    g = make_graph()
    g["edges"].append(dict(g["edges"][0], **{"from": "c", "to": "a"}))
    with pytest.raises(ValueError):
        te.graph_edges(g)


def test_graph_edges_provider_absent(monkeypatch):
    monkeypatch.setattr(te.importlib.util, "spec_from_file_location", lambda *a: None)
    with pytest.raises(ValueError, match="provider absent"):
        te.graph_edges(make_graph())


def test_reduce_events_happy_path():
    out = te.reduce_events(make_packet(), make_graph())
    assert out["schema"] == "codepurple.spine.w12.trigger-census.v1"
    assert out["design_graph_nodes"] == 3
    assert out["design_graph_edges"] == 3
    assert out["wave_clusters_reported"] == 2
    assert out["observed_step_events"] == 4
    assert out["fired_step_events"] == 3
    assert out["fired_by_type"] == {"CONSUMES": 2, "MEASURES": 1}
    assert out["observed_edge_latencies_seconds"] == [5.0, 5.0, 5.0]
    first = out["wave_receipts"][0]
    assert first["failed_steps"] == 1
    assert first["jobs_observed"] == 1
    assert first["native_authentication"] == "SOURCE_REPORTED_UNVERIFIED"
    assert out["merge_admission"] == "HOLD"
    assert out["p95_edge_latency_seconds"] is None


def _mutate(path_fn):
    packet = make_packet()
    path_fn(packet)
    return packet


def _step(p):
    return p["waves"][0]["jobs"][0]["steps"][0]


def _wave(p):
    return p["waves"][0]


CASES = [
    (lambda p: p.update(schema="x"), "unsupported event schema"),
    (lambda p: p.update(repository="GBOGEB/CODEX"), "owner mismatch"),
    (lambda p: p["governance"].update(merge_admission="GO"), "unsafe event authority"),
    (lambda p: p["governance"].update(accepted_rex="r"), "unverified REX"),
    (lambda p: p.update(waves={}), "waves must be list"),
    (lambda p: p["waves"].append(1), "wave must be object"),
    (lambda p: _wave(p).update(wave_id="W1"), "invalid N\\+i wave label"),
    (lambda p: p["waves"][1].update(wave_id="N+1"), "duplicate wave ID"),
    (lambda p: _wave(p).update(source_sha="XYZ"), "invalid source SHA"),
    (lambda p: _wave(p).update(run_id=0), "native run"),
    (lambda p: _wave(p).update(attempt="1"), "native attempt"),
    (lambda p: p["waves"][1].update(run_id=10), "duplicate run/attempt"),
    (lambda p: _wave(p).update(source_clock="LOCAL"), "unknown source clock"),
    (lambda p: _wave(p).update(jobs=[]), "native job identities required"),
    (lambda p: _wave(p)["jobs"].append("j"), "job must be object"),
    (lambda p: _wave(p)["jobs"].append({"job_id": -2}), "native job"),
    (
        lambda p: _wave(p)["jobs"].append({"job_id": 100, "steps": []}),
        "duplicate native job",
    ),
    (lambda p: _wave(p)["jobs"][0].update(steps=None), "steps must be list"),
    (lambda p: _wave(p)["jobs"][0]["steps"].append(5), "event must be object"),
    (lambda p: _step(p).update(step_id=0), "step ID"),
    (lambda p: _step(p).update(step_id=2), "duplicate job step event"),
    (lambda p: _step(p).update(type="DERIVES"), "forged typed trigger edge"),
    (lambda p: _step(p).update(fired=1), "fired requires boolean"),
    (lambda p: _step(p).update(started_at="bad"), "canonical UTC"),
    (
        lambda p: _step(p).update(completed_at="2025-01-01T00:00:00Z"),
        "negative observed edge duration",
    ),
    (lambda p: _step(p).update(conclusion="cancelled"), "conclusion absent"),
    (lambda p: _step(p).update(fired=False), "unfired event cannot count"),
    (
        lambda p: _wave(p)["jobs"][0]["steps"][2].update(
            fired=True, conclusion="success"
        ),
        "cannot be declared an executed mutation",
    ),
    (
        lambda p: _step(p).update(conclusion="failure", first_red_signature=""),
        "invalid first-red signature",
    ),
    (
        lambda p: _step(p).update(first_red_signature="sig"),
        "first-red signature without failed event",
    ),
]


@pytest.mark.parametrize("mutator,message", CASES)
def test_reduce_events_rejections(mutator, message):
    packet = _mutate(mutator)
    with pytest.raises(ValueError, match=message):
        te.reduce_events(packet, make_graph())


def test_reduce_events_rejects_non_dict_packet():
    with pytest.raises(ValueError, match="unsupported event schema"):
        te.reduce_events([], make_graph())


def test_reduce_events_missing_governance_is_unsafe():
    packet = make_packet()
    del packet["governance"]
    with pytest.raises(ValueError, match="unsafe event authority"):
        te.reduce_events(packet, make_graph())


def test_main_writes_report(tmp_path, monkeypatch):
    events = tmp_path / "events.json"
    graph = tmp_path / "graph.json"
    out = tmp_path / "deep" / "census.json"
    events.write_text(json.dumps(make_packet()), encoding="utf-8")
    graph.write_text(json.dumps(copy.deepcopy(make_graph())), encoding="utf-8")
    argv = ["x", "--events", str(events), "--graph", str(graph), "--output", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    te.main()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["fired_step_events"] == 3
    assert report["wave_receipts"][1]["wave_id"] == "N+2"
