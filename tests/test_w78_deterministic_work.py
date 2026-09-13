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


w78_probe = load_module(
    "w78_deterministic_work_probe",
    TOOLS / "w78_deterministic_work_probe.py",
)
w78 = load_module("w78_work_diversity", TOOLS / "w78_work_diversity.py")


def synthetic_receipts(distinct: bool = True) -> list[dict]:
    rows = []
    for index in range(15):
        work_vector = {
            feature: (
                (index + 1) * (feature_index + 2)
                if distinct
                else feature_index + 2
            )
            for feature_index, feature in enumerate(w78_probe.WORK_FEATURES)
        }
        semantic_vector = {
            feature: work_vector[feature]
            for feature in w78_probe.SEMANTIC_WORK_FEATURES
        }
        work_hash = w78_probe.canonical_sha256(work_vector)
        semantic_hash = w78_probe.canonical_sha256(semantic_vector)
        feature_row = {
            "source_sha": f"sha-{index:02d}",
            "total_population": index + 1,
        }
        feature_hash = w78_probe.canonical_sha256(feature_row)
        for repeat in (1, 2):
            rows.append(
                {
                    "source_sha": f"sha-{index:02d}",
                    "matrix_label": f"s{index:02d}",
                    "repeat": repeat,
                    "execution_state": "PASS",
                    "semantic_parity_with_w72": True,
                    "feature_row": feature_row,
                    "feature_row_sha256": feature_hash,
                    "work_vector": work_vector,
                    "work_vector_sha256": work_hash,
                    "semantic_work_vector": semantic_vector,
                    "semantic_work_vector_sha256": semantic_hash,
                }
            )
    return rows


def test_deterministic_probe_preserves_w72_semantics() -> None:
    result = w78_probe.probe(ROOT, "TEST-W78", 1, "local")
    assert result["semantic_parity_with_w72"] is True
    assert result["execution_state"] == "PASS"
    assert set(result["work_vector"]) == set(w78_probe.WORK_FEATURES)
    assert result["work_vector"]["scanned_text_files"] > 0
    assert result["work_vector"]["scanned_text_bytes"] > 0
    assert result["pca_fit_performed"] is False


def test_identical_replays_collapse_without_loss() -> None:
    rows = synthetic_receipts()
    collapsed = w78.validate(rows)
    assert len(collapsed) == 15


def test_replay_mismatch_fails_closed() -> None:
    rows = synthetic_receipts()
    rows[1]["work_vector"] = dict(rows[1]["work_vector"])
    rows[1]["work_vector"]["scanned_text_files"] += 1
    rows[1]["work_vector_sha256"] = w78_probe.canonical_sha256(
        rows[1]["work_vector"]
    )
    try:
        w78.validate(rows)
    except ValueError as exc:
        assert "deterministic replay mismatch" in str(exc)
    else:
        raise AssertionError("W78 replay mismatch must fail closed")


def test_low_diversity_panel_withholds_later_analysis() -> None:
    result = w78.evaluate(synthetic_receipts(distinct=False))
    assert result["distinct_work_state_count"] == 1
    assert result["w79_multivariate_analysis_permitted"] is False
    assert result["pca_fit_performed"] is False
    assert result["global_allocation_authority"] is False


def test_diversity_gate_is_not_pca_authority() -> None:
    result = w78.evaluate(synthetic_receipts(distinct=True))
    assert result["distinct_work_state_count"] == 15
    assert result["pca_fit_performed"] is False
    assert result["global_allocation_authority"] is False
