"""W31: synthetic fail-closed repair-episode and graph tests for W81.

All synthetic receipts are generated under tmp_path. No GitHub outcome, model
authority, merge admission, or independent review is manufactured by tests.
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from tools import w81_repair_outcome_block as w81

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "architecture/w81/W81_REPAIR_OUTCOME_CONTRACT.json"
WORK_INPUT = ROOT / "architecture/w79/W79_W78_INPUT.json"
SCHEMA = "MC2-W78-DETERMINISTIC-WORK-PROBE-0.1.0"


@pytest.mark.parametrize(
    ("edges", "expected"),
    [
        ([], 0),
        ([("a", "b")], 1),
        ([("a", "b"), ("b", "c")], 1),
        ([("a", "b"), ("c", "d")], 2),
        ([("a", "b"), ("b", "a"), ("a", "b")], 1),
        ([("a", "b"), ("b", "c"), ("d", "e"), ("e", "f")], 2),
    ],
)
def test_episode_graph_connected_component_geometry(edges, expected):
    events = [
        {"winner_source_sha": winner, "loser_source_sha": loser}
        for winner, loser in edges
    ]
    assert w81.components(events) == expected


def project_receipt():
    return {
        "schema_version": SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "execution_state": "PASS",
        "semantic_parity_with_w72": True,
        "semantic_work_vector": {"f1": 1.0, "f2": 2.0},
    }


def test_projection_has_frozen_deterministic_score_without_refit():
    r = project_receipt()
    score = w81.project(
        r,
        ["f1", "f2"],
        np.array([0.0, 0.0]),
        np.array([1.0, 2.0]),
        np.array([0.6, 0.8]),
    )
    assert score == pytest.approx(1.4)
    assert r == project_receipt()


@pytest.mark.parametrize(
    ("invalid_field", "replacement", "error"),
    [
        ("schema_version", "other", "W78-compatible"),
        ("repository", "foreign/repo", "repository mismatch"),
        ("execution_state", "FAIL", "semantic parity"),
        ("semantic_parity_with_w72", False, "semantic parity"),
        ("semantic_work_vector", {"f1": 2}, "feature set mismatch"),
        (
            "semantic_work_vector",
            {"f1": 2, "f2": 3, "extra": 1},
            "feature set mismatch",
        ),
    ],
)
def test_projection_rejects_fabricated_or_noncomparable_receipts(
    invalid_field, replacement, error
):
    r = project_receipt()
    r[invalid_field] = replacement
    with pytest.raises(ValueError, match=error):
        w81.project(
            r,
            ["f1", "f2"],
            np.array([0.0, 0.0]),
            np.array([1.0, 1.0]),
            np.array([1.0, 0.0]),
        )


def synthetic_scene(tmp_path):
    contract = copy.deepcopy(json.loads(CONTRACT.read_text(encoding="utf-8")))
    source = json.loads(WORK_INPUT.read_text(encoding="utf-8"))
    features = list(source["semantic_work_features"])
    # The values are intentionally synthetic. Frozen W79 training remains unchanged.
    synthetic_vector = {key: float(i + 1) for i, key in enumerate(features)}
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    receipt_paths = {}
    for episode in contract["episodes"]:
        for side in ("failure", "repair"):
            label = episode[f"{side}_label"]
            payload = {
                "schema_version": SCHEMA,
                "repository": "GBOGEB/ABACUS",
                "execution_state": "PASS",
                "semantic_parity_with_w72": True,
                "semantic_work_vector": synthetic_vector,
                "matrix_label": label,
                "source_sha": episode[f"{side}_source_sha"],
            }
            path = receipts / f"W81_{label}_WORK_RECEIPT.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            receipt_paths[label] = path
    verification = {
        "result": "PASS",
        "primary_frontier": {"result": "EXHAUSTED_NO_ACTIONS_EVIDENCE"},
    }
    contract_file = tmp_path / "contract.json"
    verify_file = tmp_path / "verification.json"
    contract_file.write_text(json.dumps(contract), encoding="utf-8")
    verify_file.write_text(json.dumps(verification), encoding="utf-8")
    return contract, verification, contract_file, verify_file, receipts, receipt_paths


def call_cli(monkeypatch, contract_file, verify_file, receipts, output):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "w81_repair_outcome_block.py",
            "--contract",
            str(contract_file),
            "--verification",
            str(verify_file),
            "--receipts-dir",
            str(receipts),
            "--out",
            str(output),
        ],
    )
    return w81.main()


def test_cli_persists_two_disconnected_observed_episodes_without_authority(
    tmp_path, monkeypatch
):
    _, _, cfile, vfile, receipts, _ = synthetic_scene(tmp_path)
    output = tmp_path / "result.json"
    assert call_cli(monkeypatch, cfile, vfile, receipts, output) == 0
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["episode_count"] == 2
    assert record["pair_graph_component_count"] == 2
    assert len(record["pair_rows"]) == 2
    assert all(math.isfinite(x["failure_pc1"]) for x in record["pair_rows"])
    assert all(x["causal_effect_claimed"] is False for x in record["pair_rows"])
    assert record["pairwise_outcome_accumulation_permitted"] is False
    assert record["pc1_predictive_validation"] is False
    assert record["bt_status"] == "WITHHELD"
    assert "PAIR_GRAPH_DISCONNECTED" in record["bt_withhold_reasons"]
    assert "PAIR_COUNT_BELOW_MODEL_FIT_MINIMUM" in record["bt_withhold_reasons"]
    assert record["formal_credit_delta"] == 0
    assert record["authority_transfer"] is False
    assert record["global_allocation_authority"] is False


@pytest.mark.parametrize(
    ("corruption", "message"),
    [
        ("verification_fail", "verification PASS"),
        ("frontier_not_exhausted", "not exhausted"),
        ("promote_pc1", "negative predictive validation"),
        ("missing_episode", "labels mismatch"),
        ("foreign_source_sha", "source SHA mismatch"),
        ("foreign_repository", "repository mismatch"),
        ("lost_parity", "semantic parity"),
        ("missing_feature", "feature set mismatch"),
    ],
)
def test_cli_fails_closed_on_authority_and_lineage_tampering(
    tmp_path, monkeypatch, corruption, message
):
    contract, verification, cfile, vfile, receipts, paths = synthetic_scene(tmp_path)
    label = contract["episodes"][0]["failure_label"]
    if corruption == "verification_fail":
        verification["result"] = "UNKNOWN"
    elif corruption == "frontier_not_exhausted":
        verification["primary_frontier"]["result"] = "UNKNOWN"
    elif corruption == "promote_pc1":
        contract["source_w80"]["pc1_predictive_validation"] = True
    elif corruption == "missing_episode":
        paths[label].unlink()
    else:
        row = json.loads(paths[label].read_text(encoding="utf-8"))
        if corruption == "foreign_source_sha":
            row["source_sha"] = "f" * 40
        elif corruption == "foreign_repository":
            row["repository"] = "untrusted/example"
        elif corruption == "lost_parity":
            row["semantic_parity_with_w72"] = False
        else:
            row["semantic_work_vector"].pop(next(iter(row["semantic_work_vector"])))
        paths[label].write_text(json.dumps(row), encoding="utf-8")
    cfile.write_text(json.dumps(contract), encoding="utf-8")
    vfile.write_text(json.dumps(verification), encoding="utf-8")
    output = tmp_path / "result.json"
    with pytest.raises(ValueError, match=message):
        call_cli(monkeypatch, cfile, vfile, receipts, output)
    assert not output.exists()
