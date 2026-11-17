"""Gap tests for tools/generic_3p_selector.py (fallbacks, defaults, main)."""

import json
import sys

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/generic_3p_selector.py", name="abn_w7_generic_3p_selector")


def test_clip_non_numeric_returns_zero():
    assert mod._clip("abc") == 0.0
    assert mod._clip(None) == 0.0
    assert mod._clip(2) == 1.0


def test_unknown_state_and_non_dict_weights_fall_back():
    result = mod.select_method({"state": "BOGUS", "semantic_weights": [1, 2]})
    assert result["state"] == "S0_UNKNOWN"
    assert result["chain"] == ["3PE"]
    assert result["reasons"] == ["default_early_stage_exploration"]
    assert all(value == 0.0 for value in result["weights"].values())


def test_proof_candidate_appends_progression_proof():
    result = mod.select_method({"state": "S3_PROOF_CANDIDATE"})
    assert result["chain"] == ["3PV"]
    assert result["reasons"] == ["progression_requires_same_boundary_proof"]


def test_reentry_pending_forces_reentry():
    result = mod.select_method({"state": "S5_REENTRY_PENDING"})
    assert result["reentry"] is True
    assert result["chain"] == ["3PR"]


def test_classified_defaults_to_proof():
    result = mod.select_method({"state": "S2_CLASSIFIED"})
    assert result["chain"] == ["3PV"]
    assert result["reasons"] == [
        "classified_item_needs_proof_before_terminal_disposition"
    ]


def test_terminal_with_open_gap_defaults_to_control():
    result = mod.select_method({"state": "S6_TERMINAL", "dov_gap": 0.5})
    assert result["decision"] == "EXECUTE"
    assert result["chain"] == ["3PC"]
    assert result["reasons"] == ["default_control_discrimination"]


def test_main_writes_decisions_skipping_non_dict_items(tmp_path, monkeypatch):
    src = tmp_path / "in.json"
    out = tmp_path / "nested" / "out.json"
    payload = {
        "items": [
            {"item_id": "A", "state": "S2_CLASSIFIED"},
            "not-a-dict",
            {"item_id": "B", "state": "S6_TERMINAL", "dov_gap": 0.0},
        ]
    }
    src.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["sel", "--input", str(src), "--out", str(out)])
    assert mod.main() == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["schema_version"] == "TRIAGE-3P-SELECTOR-1.0.0"
    assert result["item_count"] == 2
    assert [d["item_id"] for d in result["decisions"]] == ["A", "B"]
    assert result["decisions"][1]["decision"] == "STOP"


def test_main_non_dict_payload_yields_no_decisions(tmp_path, monkeypatch):
    src = tmp_path / "in.json"
    out = tmp_path / "out.json"
    src.write_text("[1, 2]", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["sel", "--input", str(src), "--out", str(out)])
    assert mod.main() == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["item_count"] == 0
    assert result["decisions"] == []
