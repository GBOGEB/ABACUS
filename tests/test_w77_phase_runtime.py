from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w72 = load_module("w72_semantic_census", TOOLS / "w72_semantic_census.py")
w77_probe = load_module(
    "w77_instrumented_semantic_census",
    TOOLS / "w77_instrumented_semantic_census.py",
)
w77_stability = load_module(
    "w77_phase_stability", TOOLS / "w77_phase_stability.py"
)


def test_instrumented_census_preserves_w72_semantics() -> None:
    receipts, row, telemetry = w77_probe.build_instrumented(ROOT, "TEST-W77")
    baseline_receipts, baseline_row = w72.measure(ROOT, "TEST-W77")
    assert receipts == baseline_receipts
    assert row == baseline_row
    assert telemetry["work_counters"]["scanned_text_files"] > 0
    assert telemetry["work_counters"]["scanned_text_bytes"] > 0
    assert telemetry["work_counters"]["consumer_candidate_checks"] > 0
    assert telemetry["work_counters"]["graph_nodes"] > 0
    assert telemetry["phase_timing_ns"]["consumer_scan"]["cpu_ns"] > 0


def synthetic_receipts() -> list[dict]:
    rows = []
    for sha_index in range(5):
        sha = f"sha-{sha_index}"
        for repeat in (1, 2, 3):
            features = {
                feature: float(sha_index + 1) * float(feature_index + 1)
                for feature_index, feature in enumerate(w77_stability.CANDIDATES)
            }
            rows.append(
                {
                    "source_sha": sha,
                    "repeat": repeat,
                    "execution_state": "PASS",
                    "semantic_parity_with_w72": True,
                    "feature_row_sha256": f"hash-{sha_index}",
                    "work_counters": {
                        "semantic_entities": 10 + sha_index,
                        "graph_edges": 20 + sha_index,
                    },
                    "runtime_sensitive_features": features,
                }
            )
    return rows


def test_stable_phase_features_can_only_enable_next_pca_step() -> None:
    result = w77_stability.evaluate(synthetic_receipts())
    assert set(result["eligible_runtime_features"]) == set(
        w77_stability.CANDIDATES
    )
    assert result["pca_next_step_permitted"] is True
    assert result["pca_fit_performed"] is False
    assert result["global_allocation_authority"] is False


def test_unbalanced_phase_panel_fails_closed() -> None:
    rows = synthetic_receipts()[:-1]
    try:
        w77_stability.validate(rows)
    except ValueError as exc:
        assert "exactly 15" in str(exc)
    else:
        raise AssertionError("unbalanced W77 panel must fail closed")
