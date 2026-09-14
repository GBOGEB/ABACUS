from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
INPUT = ROOT / "architecture/w79/W79_W78_INPUT.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w79 = load_module("w79_deterministic_work_pca", TOOLS / "w79_deterministic_work_pca.py")


def load_input() -> dict:
    return json.loads(INPUT.read_text(encoding="utf-8"))


def test_governed_w78_input_hashes_and_lineage_validate() -> None:
    source = load_input()
    rows = w79.validate_input(source)
    assert len(rows) == 15
    assert source["source_w78"]["workflow_run_id"] == 34777543492
    assert source["source_w78"]["artifact_id"] == 10323323552
    assert source["source_w78"]["deterministic_replay_consistency"] == "PASS_15_OF_15"


def test_real_w79_pca_retains_only_deterministic_complexity_pc1() -> None:
    result = w79.evaluate(
        load_input(),
        source_input_sha256=w79.file_sha256(INPUT),
    )
    full = result["full_work_pca"]
    semantic = result["semantic_work_pca"]
    assert full["retained_pcs"] == [1]
    assert semantic["retained_pcs"] == [1]
    assert full["components"][0]["eigenvalue"] == 9.089865
    assert full["components"][0]["explained_variance_ratio"] == 0.908987
    assert full["components"][0]["pa95_threshold"] == 3.074261
    assert semantic["components"][0]["eigenvalue"] == 6.341341
    assert semantic["components"][0]["explained_variance_ratio"] == 0.905906
    assert semantic["components"][0]["pa95_threshold"] == 2.564523
    assert result["timing_pca_reopened"] is False
    assert result["global_allocation_authority"] is False
    assert result["child_engineering_promotion_authority"] is False
    assert result["engineering_compliance_release_authority"] is False


def test_tampered_deterministic_row_fails_closed() -> None:
    source = copy.deepcopy(load_input())
    source["rows"][0]["values"][-1] += 1
    try:
        w79.validate_input(source)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered W78 work vector must fail closed")


def test_w78_permission_and_replay_gates_fail_closed() -> None:
    source = copy.deepcopy(load_input())
    source["source_w78"]["w79_multivariate_analysis_permitted"] = False
    try:
        w79.validate_input(source)
    except ValueError as exc:
        assert "did not permit" in str(exc)
    else:
        raise AssertionError("missing W79 permission must fail closed")

    source = copy.deepcopy(load_input())
    source["source_w78"]["deterministic_replay_consistency"] = "WITHHELD"
    try:
        w79.validate_input(source)
    except ValueError as exc:
        assert "PASS_15_OF_15" in str(exc)
    else:
        raise AssertionError("unproven deterministic replay must fail closed")


def test_forged_w78_lineage_fails_closed() -> None:
    source = copy.deepcopy(load_input())
    source["source_w78"]["artifact_id"] = 99999999
    try:
        w79.validate_input(source)
    except ValueError as exc:
        assert "governed lineage mismatch" in str(exc)
    else:
        raise AssertionError("forged W78 provenance must fail closed")


def test_rehashed_forged_row_payload_fails_closed() -> None:
    source = copy.deepcopy(load_input())
    row = source["rows"][0]
    row["values"][-1] += 1
    work = dict(zip(source["work_features"], row["values"]))
    semantic = {
        feature: work[feature] for feature in source["semantic_work_features"]
    }
    row["work_sha256"] = w79.canonical_sha256(work)
    row["semantic_sha256"] = w79.canonical_sha256(semantic)
    try:
        w79.validate_input(source)
    except ValueError as exc:
        assert "governed input payload mismatch" in str(exc)
    else:
        raise AssertionError("rehashed forged W78 payload must fail closed")
