"""W35 W81 repair-outcome behavioral scout: separate from W34 B0 recovery.

Synthetic exact-source receipts are test fixtures ONLY, never treated as
accepted GitHub verification or causal engineering-root closure. No mutation of
W81 production sources, release decisions, security rules or reference assets.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import w81_repair_outcome_block as w81  # noqa: E402


def receipt(label: str, source_sha: str, number: int) -> dict:
    return {
        "matrix_label": label,
        "source_sha": source_sha,
        "schema_version": "MC2-W78-DETERMINISTIC-WORK-PROBE-0.1.0",
        "repository": "GBOGEB/ABACUS",
        "execution_state": "PASS",
        "semantic_parity_with_w72": True,
        "semantic_work_vector": {"consumer": float(number), "graph": float(number * 2)},
    }


@pytest.mark.parametrize("change,expected", [
    ({"schema_version": "W79"}, "W78-compatible"),
    ({"repository": "GBOGEB/CODEX"}, "repository mismatch"),
    ({"execution_state": "QUEUED"}, "exact-source semantic parity"),
    ({"semantic_parity_with_w72": False}, "exact-source semantic parity"),
    ({"semantic_parity_with_w72": "true"}, "exact-source semantic parity"),
    ({"semantic_work_vector": {"consumer": 2.}}, "feature set mismatch"),
    ({"semantic_work_vector": {"consumer": 2., "graph": 3., "extra": 4.}}, "feature set mismatch"),
])
def test_projection_fails_closed_on_invalid_exact_source_receipt(
    change: dict, expected: str,
) -> None:
    row = receipt("F0", "a" * 40, 2)
    row.update(change)
    with pytest.raises(ValueError, match=expected):
        w81.project(row, ["consumer", "graph"], np.zeros(2), np.ones(2),
                    np.asarray([1., 0.]))


def test_projection_positive_preserves_frozen_pca_and_does_not_mutate_receipt() -> None:
    row = receipt("F0", "a" * 40, 2)
    prior = json.dumps(row, sort_keys=True)
    score = w81.project(row, ["consumer", "graph"], np.asarray([1., 0.]),
                        np.asarray([2., 4.]), np.asarray([1., 0.]))
    assert score == pytest.approx(.5)
    assert json.dumps(row, sort_keys=True) == prior


@pytest.mark.parametrize("events,expected", [
    ([], 0),
    ([("a", "b")], 1),
    ([("a", "b"), ("c", "d")], 2),
    ([("a", "b"), ("b", "c"), ("c", "a")], 1),
    ([("a", "b"), ("c", "d"), ("b", "c")], 1),
])
def test_component_count_measures_unique_undirected_pair_graph(
    events: list[tuple[str, str]], expected: int,
) -> None:
    rows = [{"winner_source_sha": a, "loser_source_sha": b} for a, b in events]
    assert w81.components(rows) == expected


def test_missing_optional_module_is_a_hard_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="unable to load"):
        w81.load_module("w81_missing", tmp_path / "never_created.py")


def test_frozen_semantic_basis_is_not_refitted_on_repair_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"semantic_work_vector": {"graph": float(i), "consumer": float(2 * i + 1)}}
        for i in range(1, 7)
    ]
    fake = SimpleNamespace(validate_input=lambda source: rows)
    monkeypatch.setattr(w81, "load_module", lambda name, path: fake)
    features, means, standard_deviations, vector = w81.frozen_semantic_basis(
        {"semantic_work_features": ["graph", "consumer"]}
    )
    assert features == ["graph", "consumer"]
    assert means == pytest.approx([3.5, 8.0])
    assert np.all(np.isfinite(standard_deviations))
    assert np.all(standard_deviations > 0)
    assert np.linalg.norm(vector) == pytest.approx(1.)
    assert vector[np.argmax(np.abs(vector))] > 0


def synthetic_w81(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    directory = tmp_path / "source-receipts"
    directory.mkdir()
    contract = {
        "repair_episode_semantics": "synthetic-only-no-authority",
        "source_w80": {"pc1_predictive_validation": False},
        "promotion_guards": {"minimum_pair_count_for_any_model_fit": 3},
        "episodes": [
            {"episode_id": "E1", "failure_label": "F1", "repair_label": "R1",
             "failure_source_sha": "a" * 40, "repair_source_sha": "b" * 40},
            {"episode_id": "E2", "failure_label": "F2", "repair_label": "R2",
             "failure_source_sha": "c" * 40, "repair_source_sha": "d" * 40},
        ],
    }
    verification = {
        "result": "PASS",
        "primary_frontier": {"result": "EXHAUSTED_NO_ACTIONS_EVIDENCE"},
    }
    content = {
        "F1": receipt("F1", "a" * 40, 1),
        "R1": receipt("R1", "b" * 40, 2),
        "F2": receipt("F2", "c" * 40, 3),
        "R2": receipt("R2", "d" * 40, 4),
    }
    for label, obj in content.items():
        (directory / f"W81_{label}_WORK_RECEIPT.json").write_text(
            json.dumps(obj), encoding="utf-8"
        )
    source = tmp_path / "w79_source.json"
    source.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(w81, "W79_INPUT", source)
    monkeypatch.setattr(
        w81, "frozen_semantic_basis",
        lambda source: (["consumer", "graph"], np.zeros(2), np.ones(2),
                        np.asarray([1., 0.]))
    )
    return {
        "contract": contract,
        "verification": verification,
        "directory": directory,
        "receipts": content,
        "contract_path": tmp_path / "contract.json",
        "verification_path": tmp_path / "verification.json",
        "out": tmp_path / "w81_output.json",
    }


def execute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: dict) -> int:
    data["contract_path"].write_text(json.dumps(data["contract"]), encoding="utf-8")
    data["verification_path"].write_text(json.dumps(data["verification"]), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "w81", "--contract", str(data["contract_path"]),
        "--verification", str(data["verification_path"]),
        "--receipts-dir", str(data["directory"]),
        "--out", str(data["out"]),
    ])
    return w81.main()


def test_full_w81_cli_preserves_held_bradley_terry_and_zero_transfer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    data = synthetic_w81(tmp_path, monkeypatch)
    assert execute(tmp_path, monkeypatch, data) == 0
    result = json.loads(data["out"].read_text(encoding="utf-8"))
    assert json.loads(capsys.readouterr().out) == result
    assert result["episode_count"] == 2
    assert result["pair_graph_component_count"] == 2
    assert result["bt_status"] == "WITHHELD"
    assert set(result["bt_withhold_reasons"]) == {
        "W80_PC1_PREDICTIVE_VALIDATION_FALSE",
        "PAIR_COUNT_BELOW_MODEL_FIT_MINIMUM",
        "PAIR_GRAPH_DISCONNECTED",
    }
    assert all(row["causal_effect_claimed"] is False for row in result["pair_rows"])
    assert all(event["bt_admitted"] is False for event in result["observed_pairwise_candidate_events"])
    assert result["formal_credit_delta"] == 0
    assert result["pca_refit_performed"] is False
    assert result["timing_pca_reopened"] is False
    assert result["pairwise_outcome_accumulation_permitted"] is False
    assert result["engineering_compliance_release_authority"] is False
    assert result["authority_transfer"] is False


@pytest.mark.parametrize("case,expected", [
    ("verification_fail", "authoritative GitHub outcome verification PASS"),
    ("verification_missing", "authoritative GitHub outcome verification PASS"),
    ("frontier_not_exhausted", "low-PC1 frontier is not exhausted"),
    ("pc1_true", "negative predictive validation"),
    ("missing_receipt", "work receipt labels mismatch"),
    ("unexpected_receipt", "work receipt labels mismatch"),
    ("failure_sha_changed", "source SHA mismatch"),
    ("repair_sha_changed", "source SHA mismatch"),
    ("receipt_state_red", "exact-source semantic parity"),
    ("receipt_parity_false", "exact-source semantic parity"),
    ("receipt_repo_other", "repository mismatch"),
    ("receipt_features_mismatch", "feature set mismatch"),
])
def test_cli_rejects_unqualified_or_forged_repair_evidence_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, expected: str,
) -> None:
    data = synthetic_w81(tmp_path, monkeypatch)
    if case == "verification_fail":
        data["verification"]["result"] = "FAIL"
    elif case == "verification_missing":
        data["verification"].pop("result")
    elif case == "frontier_not_exhausted":
        data["verification"]["primary_frontier"]["result"] = "NOT_EXHAUSTED"
    elif case == "pc1_true":
        data["contract"]["source_w80"]["pc1_predictive_validation"] = True
    elif case == "missing_receipt":
        (data["directory"] / "W81_F1_WORK_RECEIPT.json").unlink()
    elif case == "unexpected_receipt":
        (data["directory"] / "W81_U_WORK_RECEIPT.json").write_text(
            json.dumps(receipt("U", "f" * 40, 9)), encoding="utf-8")
    else:
        changed = dict(data["receipts"]["F1" if case.startswith("failure") else "R1"])
        if case == "failure_sha_changed" or case == "repair_sha_changed":
            changed["source_sha"] = "f" * 40
        elif case == "receipt_state_red":
            changed["execution_state"] = "FAIL"
        elif case == "receipt_parity_false":
            changed["semantic_parity_with_w72"] = False
        elif case == "receipt_repo_other":
            changed["repository"] = "GBOGEB/CODEX"
        elif case == "receipt_features_mismatch":
            changed["semantic_work_vector"] = {"graph": 3.0}
        label = changed["matrix_label"]
        (data["directory"] / f"W81_{label}_WORK_RECEIPT.json").write_text(
            json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match=expected):
        execute(tmp_path, monkeypatch, data)
    assert not data["out"].exists()
