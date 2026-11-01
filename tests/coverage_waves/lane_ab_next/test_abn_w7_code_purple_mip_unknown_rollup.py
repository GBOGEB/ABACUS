"""Gap tests for scripts/code_purple_mip_unknown_rollup.py (guards and main)."""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "scripts/code_purple_mip_unknown_rollup.py", name="abn_w7_mip_unknown_rollup"
)


def _backlog():
    items = [
        {
            "id": f"U{i:02d}",
            "evidence_state": "UNKNOWN",
            "dmaic_phase": "MEASURE",
            "owner": "team",
            "acceptance_target": "target",
            "title": "title",
            "age": {"first_observed": "2026-10-01"},
        }
        for i in range(1, 17)
    ]
    return {
        "schema": "code-purple.mip.unknown-backlog.v1",
        "source_repository": "GBOGEB/ABACUS",
        "reference_head": "a" * 40,
        "items": items,
    }


def test_non_dict_row_rejected():
    data = _backlog()
    data["items"][3] = "row"
    with pytest.raises(ValueError, match="invalid backlog row"):
        mod.rollup(data, "2026-10-10")


def test_future_observation_rejected():
    with pytest.raises(ValueError, match="future observation"):
        mod.rollup(_backlog(), "2026-09-30")


def test_verified_without_measured_value_rejected():
    data = _backlog()
    data["items"][0].update(
        evidence_state="VERIFIED_PASS",
        proof_reference="https://github.com/GBOGEB/ABACUS/pull/1",
    )
    with pytest.raises(ValueError, match="requires measured value"):
        mod.rollup(data, "2026-10-10")


def test_unknown_with_value_rejected():
    data = _backlog()
    data["items"][0]["measurement_value"] = 3
    with pytest.raises(ValueError, match="UNKNOWN cannot claim a value"):
        mod.rollup(data, "2026-10-10")


def test_main_writes_rollup(tmp_path, monkeypatch):
    data = _backlog()
    data["items"][0].update(
        evidence_state="VERIFIED_PASS",
        proof_reference="https://github.com/GBOGEB/ABACUS/pull/1",
        measurement_value=1.0,
        overflow=True,
    )
    data["items"][1].update(evidence_state="PENDING", measurement_value=2)
    src = tmp_path / "in.json"
    out = tmp_path / "out" / "kpi.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    argv = ["rollup", "--input", str(src), "--output", str(out)]
    monkeypatch.setattr(sys, "argv", argv + ["--as-of", "2026-10-11"])
    mod.main()
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["states"]["VERIFIED_PASS"] == 1
    assert result["states"]["PENDING"] == 1
    assert result["evidence_completeness_pct"] == 6.25
    assert result["overflow_count"] == 1
    assert result["aged"][0]["age_days"] == 10
