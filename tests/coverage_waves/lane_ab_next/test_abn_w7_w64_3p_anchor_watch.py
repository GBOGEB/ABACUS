"""Gap tests for tools/w64_3p_anchor_watch.py (edge statuses, main)."""

import json
import sys

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/w64_3p_anchor_watch.py", name="abn_w7_w64_anchor_watch")


def test_metric_status_nonpositive_sigma_is_warning():
    result = mod.metric_status(1.0, 0.0, 0.0)
    assert result["status"] == "WARNING"
    assert result["z_score"] is None
    assert result["reason"] == "nonpositive_sigma"
    assert result["reopen_analyze"] is False


def test_cosine_abs_degenerate_inputs():
    assert mod.cosine_abs([1.0], [1.0, 2.0]) == 0.0
    assert mod.cosine_abs([], []) == 0.0
    assert mod.cosine_abs([0.0, 0.0], [1.0, 1.0]) == 0.0
    assert mod.cosine_abs([1.0, 0.0], [-1.0, 0.0]) == 1.0


def test_pca_status_warning_band():
    anchor = {"loadings": [1.0, 0.0], "explained_variance": 0.5}
    current = {"loadings": [1.0, 0.0], "explained_variance": 0.57}
    result = mod.pca_status(current, anchor)
    assert result["status"] == "WARNING"
    assert result["reopen_analyze"] is False
    assert abs(result["explained_variance_delta"] - 0.07) < 1e-9


def test_main_writes_watch_report(tmp_path, monkeypatch):
    payload = {
        "metrics": [
            {"anchor_id": "m1", "current": 10.0, "center": 0.0, "sigma": 1.0},
            {
                "anchor_id": "m2",
                "current": 0.5,
                "center": 0.0,
                "sigma": 1.0,
                "history_z": [0.1],
            },
        ],
        "pca": [
            {
                "anchor_id": "p1",
                "current": {"loadings": [1.0, 0.0], "semantic_label": "x"},
                "anchor": {"loadings": [1.0, 0.0], "semantic_label": "x"},
                "prior_statuses": ["CONTROLLED"],
            }
        ],
    }
    src = tmp_path / "in.json"
    src.write_text(json.dumps(payload), encoding="utf-8")
    dest = tmp_path / "nested" / "out.json"
    monkeypatch.setattr(sys, "argv", ["w64", "--input", str(src), "--out", str(dest)])
    assert mod.main() == 0
    out = json.loads(dest.read_text(encoding="utf-8"))
    assert out["schema_version"] == "TRIAGE-3P-ANCHOR-WATCH-1.0.0"
    assert [m["status"] for m in out["metrics"]] == ["DRIFT", "CONTROLLED"]
    assert out["metrics"][0]["anchor_id"] == "m1"
    assert out["pca"][0]["status"] == "CONTROLLED"
    assert out["reopen_measure_analyze"] is True


def test_main_empty_payload_does_not_reopen(tmp_path, monkeypatch):
    src = tmp_path / "in.json"
    src.write_text("{}", encoding="utf-8")
    dest = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["w64", "--input", str(src), "--out", str(dest)])
    assert mod.main() == 0
    out = json.loads(dest.read_text(encoding="utf-8"))
    assert out["metrics"] == []
    assert out["pca"] == []
    assert out["reopen_measure_analyze"] is False
