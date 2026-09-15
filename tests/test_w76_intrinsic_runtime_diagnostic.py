from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "w76_intrinsic_runtime_diagnostic.py"
PANEL = ROOT / "architecture" / "w76" / "W76_INTRINSIC_RUNTIME_PANEL.json"
RECEIPT = ROOT / "architecture" / "w76" / "W76_INTRINSIC_RUNTIME_RECEIPT.json"

spec = importlib.util.spec_from_file_location("w76_intrinsic_runtime_diagnostic", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_panel_hash_and_balance_are_valid() -> None:
    panel = load(PANEL)
    rows = module.validate_panel(panel)
    assert len(rows) == 15
    assert len({row["source_sha"] for row in rows}) == 5


def test_w76_withholds_pca_when_no_runtime_candidate_is_stable() -> None:
    result = module.evaluate(load(PANEL))
    assert result["eligible_runtime_features"] == []
    assert result["pca_fit_permitted"] is False
    assert result["pca_status"] == "WITHHELD_NO_STABLE_RUNTIME_FEATURE_SET"
    assert result["best_candidate"] == "log_seconds_per_consumer_edge"


def test_measured_metrics_match_governed_receipt() -> None:
    result = module.evaluate(load(PANEL))
    receipt = load(RECEIPT)
    for feature, expected in receipt["candidate_metrics"].items():
        observed = result["candidate_metrics"][feature]
        assert observed["icc_one_way_single_measure"] == expected[
            "icc_one_way_single_measure"
        ]
        assert observed["rank_stability"] == expected["rank_stability"]


def test_static_work_counters_cannot_grant_runtime_axis_credit() -> None:
    receipt = load(RECEIPT)
    counters = receipt["deterministic_work_counters"]
    assert counters["pca_eligibility_by_themselves"] is False
    assert receipt["pca"]["fit_performed"] is False
    assert receipt["global_allocation_authority"] is False


def test_unbalanced_panel_fails_closed() -> None:
    panel = load(PANEL)
    panel["rows"] = panel["rows"][:-1]
    try:
        module.validate_panel(panel)
    except ValueError as exc:
        assert "exactly 15" in str(exc)
    else:
        raise AssertionError("unbalanced W76 panel must fail closed")


def test_undefined_candidate_metrics_rank_below_defined_metrics() -> None:
    panel = load(PANEL)
    for row in panel["rows"]:
        row["probe_execute_seconds"] = float(row["work_counters"]["consumer_edges"])
    panel["panel_sha256"] = module.canonical_rows_sha256(panel["rows"])

    result = module.evaluate(panel)
    constant = result["candidate_metrics"]["seconds_per_consumer_edge"]
    assert constant["icc_one_way_single_measure"] is None
    assert constant["rank_stability"]["median_spearman_rho"] is None
    assert constant["stability_gate_pass"] is False
    assert result["best_candidate"] != "seconds_per_consumer_edge"
    assert result["best_candidate"] != "log_seconds_per_consumer_edge"
