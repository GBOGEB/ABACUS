"""Gap tests for tools/w77_instrumented_semantic_census.py (outputs, main)."""

import hashlib
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

w72 = load("tools/w72_semantic_census.py", name="abn_w7_w72_semantic_census")
mod = load(
    "tools/w77_instrumented_semantic_census.py",
    name="abn_w7_w77_instrumented_census",
    deps={"w72_semantic_census": w72},
)


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "a.md").write_bytes(b"mentions BBB here\n")
    (root / "docs" / "b.md").write_bytes(b"plain\n")
    monkeypatch.setattr(w72, "manifest_bindings", lambda r: {"AAA": "docs/a.md"})
    monkeypatch.setattr(
        w72,
        "indexed_bindings",
        lambda r: {"AAA": "docs/a.md", "BBB": "docs/b.md"},
    )
    monkeypatch.setattr(
        w72,
        "parse_id_records",
        lambda path, key: {"CCC": None, "DDD": "docs/missing.md#anchor"},
    )
    monkeypatch.setattr(w72, "gap_bindings", lambda r: {})
    monkeypatch.setattr(w72, "semantic_refs", lambda r: {"AAA", "ZZZ"})
    return root


def test_build_instrumented_skips_empty_paths_and_unknown_refs(fake_root):
    receipts, row, telemetry = mod.build_instrumented(fake_root, "SHA-X")
    lineage = receipts["E_lineage_evidence"]["findings"]["unlineaged_ids"]
    assert lineage == ["CCC", "DDD"]
    unresolved = receipts["B_reference_gap"]["findings"]["unresolved_references"]
    assert unresolved == ["ZZZ"]
    assert telemetry["work_counters"]["lineage_paths"] == 3
    assert telemetry["work_counters"]["graph_edges"] == 4
    evidence = receipts["C_consumer_penetration"]["findings"]["consumer_evidence"]
    assert evidence == {"BBB": ["docs/a.md"]}
    assert row["source_sha"] == "SHA-X"


def _telemetry():
    timing = {"cpu_ns": 2_000_000_000, "wall_ns": 4_000_000_000}
    return {
        "phase_timing_ns": {
            "source_parse": dict(timing),
            "consumer_scan": dict(timing),
            "graph_lineage": dict(timing),
            "receipt_emit": dict(timing),
        },
        "work_counters": {
            "scanned_text_bytes": 2 * 1024 * 1024,
            "consumer_candidate_checks": 0,
            "semantic_entities": 4,
            "graph_edges": 8,
            "emitted_receipts": 2,
        },
    }


def test_seconds_and_normalized_features():
    assert mod.seconds(1_500_000_000) == 1.5
    features = mod.normalized_features(_telemetry())
    assert features["parse_cpu_seconds_per_entity"] == 0.5
    assert features["scan_cpu_seconds_per_mib"] == 1.0
    assert features["scan_cpu_seconds_per_candidate_check"] == 2.0
    assert features["graph_cpu_seconds_per_edge"] == 0.25
    assert features["emit_cpu_seconds_per_receipt"] == 1.0
    assert features["scan_wall_seconds_per_mib"] == 2.0
    assert features["graph_wall_seconds_per_edge"] == 0.5


def test_write_outputs_hashes_feature_row(tmp_path):
    out = tmp_path / "out"
    probe = {"schema_version": mod.PROBE_SCHEMA}
    mod.write_outputs(out, {"A_lane": {"x": 1}}, {"rate": 0.5}, probe)
    assert json.loads((out / "A_lane.json").read_text(encoding="utf-8")) == {"x": 1}
    digest = hashlib.sha256((out / "FEATURE_ROW.json").read_bytes()).hexdigest()
    written = json.loads((out / "W77_PROBE_RECEIPT.json").read_text(encoding="utf-8"))
    assert written["feature_row_sha256"] == digest
    assert probe["feature_row_sha256"] == digest


def _patch_main(monkeypatch, tmp_path, baseline_row):
    receipts = {"A_lane": {"total": 1}}
    monkeypatch.setattr(
        mod,
        "build_instrumented",
        lambda root, sha: (receipts, {"row": 1}, _telemetry()),
    )
    monkeypatch.setattr(w72, "measure", lambda root, sha: (receipts, baseline_row))
    argv = ["w77", "--root", str(tmp_path), "--source-sha", "abc", "--repeat", "2"]
    argv += ["--matrix-label", "ubuntu", "--out", str(tmp_path / "out")]
    monkeypatch.setattr(sys, "argv", argv)


def test_main_parity_pass_writes_probe(tmp_path, monkeypatch, capsys):
    _patch_main(monkeypatch, tmp_path, {"row": 1})
    mod.main()
    probe = json.loads(capsys.readouterr().out)
    assert probe["execution_state"] == "PASS"
    assert probe["repeat"] == 2
    assert probe["matrix_label"] == "ubuntu"
    assert probe["runtime_sensitive_features"]["graph_cpu_seconds_per_edge"] == 0.25
    assert (tmp_path / "out" / "W77_PROBE_RECEIPT.json").exists()


def test_main_parity_failure_raises(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path, {"row": 2})
    with pytest.raises(RuntimeError, match="semantic parity failure"):
        mod.main()
    assert not (tmp_path / "out").exists()
