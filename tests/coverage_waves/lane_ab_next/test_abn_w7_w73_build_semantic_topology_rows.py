"""Gap tests for tools/w73_build_semantic_topology_rows.py (fail paths, main)."""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/w73_build_semantic_topology_rows.py", name="abn_w7_w73_topology")

SHA_A = "a" * 40
SHA_B = "b" * 40


def _receipt(**overrides):
    base = {
        "schema_version": mod.EXPECTED_SCHEMA,
        "lane": "C_consumer_penetration",
        "source_sha": SHA_A,
        "totals": {"total_population": 2, "backlog_open": 0},
        "findings": {"consumer_evidence": {"e1": ["f1"], "e2": ["f1", "f2"]}},
    }
    base.update(overrides)
    return base


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_bounded_rejects_out_of_range_and_nonfinite():
    with pytest.raises(ValueError, match="outside"):
        mod.bounded(1.5)
    with pytest.raises(ValueError, match="outside"):
        mod.bounded(float("nan"))
    assert mod.bounded(0.1234567) == 0.123457


@pytest.mark.parametrize(
    "overrides, message",
    [
        (dict(schema_version="OTHER"), "incompatible schema"),
        (dict(lane="A_other"), "not a C_consumer_penetration"),
        (dict(source_sha="xyz"), "invalid source_sha"),
        (dict(totals={"total_population": 0}), "invalid population"),
        (dict(totals={"total_population": 2, "backlog_open": 3}), "invalid population"),
        (dict(findings={}), "missing consumer_evidence"),
        (dict(findings={"consumer_evidence": {"e1": "f1"}}), "must be lists"),
    ],
)
def test_topology_row_fail_paths(tmp_path, overrides, message):
    path = _write(tmp_path, "r.json", _receipt(**overrides))
    with pytest.raises(ValueError, match=message):
        mod.topology_row(path)


def test_topology_row_without_downstream_edges(tmp_path):
    payload = _receipt(
        totals={"total_population": 2, "backlog_open": 2},
        findings={"consumer_evidence": {"e1": [], "e2": [""]}},
    )
    path = _write(tmp_path, "r.json", payload)
    with pytest.raises(ValueError, match="no downstream evidence"):
        mod.topology_row(path)


def test_main_writes_sorted_rows(tmp_path, monkeypatch, capsys):
    first = _write(tmp_path, "b.json", _receipt(source_sha=SHA_B))
    second = _write(tmp_path, "a.json", _receipt(source_sha=SHA_A))
    out = tmp_path / "rows.json"
    argv = ["w73", str(first), str(second), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert [row["source_sha"] for row in rows] == [SHA_A, SHA_B]
    assert rows[0]["row_id"] == "SEM-W73-" + SHA_A[:12]
    assert rows[0]["consumer_penetration_rate"] == 1.0
    assert rows[0]["consumer_edge_density"] == 0.75
    summary = json.loads(capsys.readouterr().out)
    assert summary == {"rows": 2, "distinct_source_shas": 2}


def test_main_rejects_duplicate_source_sha(tmp_path, monkeypatch):
    first = _write(tmp_path, "a.json", _receipt())
    second = _write(tmp_path, "b.json", _receipt())
    out = tmp_path / "rows.json"
    argv = ["w73", str(first), str(second), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="duplicate source_sha"):
        mod.main()
    assert not out.exists()
