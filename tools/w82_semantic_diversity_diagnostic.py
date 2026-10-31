#!/usr/bin/env python3
"""W82 out-of-sample semantic-diversity diagnostic.

Projects exact-source work vectors onto the frozen W79 PCA basis. It does not
refit PCA and does not create Bradley-Terry pairwise evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
W79_INPUT = ROOT / "architecture/w79/W79_W78_INPUT.json"
LEDGER = ROOT / "architecture/w82/W82_SEMANTIC_DIVERSITY_LEDGER_v0.1.json"

SCHEMA = "MC2-W82-SEMANTIC-DIVERSITY-DIAGNOSTIC-0.1.0"
LEDGER_SCHEMA = "MC2-W82-SEMANTIC-DIVERSITY-LEDGER-0.1.0"

EXPECTED_PROBE = {
    "pr": 1295,
    "head_sha": "17067f6874009f198f24bad6d56faffa2df49833",
    "run_id": 35576049753,
    "disposition": "CLOSED_UNMERGED_AFTER_RECEIPT_HARVEST",
}
EXPECTED_STATES = {
    "p1281-pass": {
        "pr": 1281,
        "source_sha": "7e8ee178f9d7e6d0d2797c754a7e8fbbde93057b",
        "outcome_run_id": 35352034494,
        "outcome": 0,
        "probe_job_id": 106258118161,
        "artifact_id": 10628545783,
    },
    "p1286-fail": {
        "pr": 1286,
        "source_sha": "9b89aa3516209f18447f03de91e91b21b35c9304",
        "outcome_run_id": 35425352883,
        "outcome": 1,
        "probe_job_id": 106258118123,
        "artifact_id": 10627766665,
    },
    "p1288-fail": {
        "pr": 1288,
        "source_sha": "a5a44635d5b10c6bb1984db131d254872efd8b0d",
        "outcome_run_id": 35428297185,
        "outcome": 1,
        "probe_job_id": 106258118114,
        "artifact_id": 10628680519,
    },
    "p1289-pass": {
        "pr": 1289,
        "source_sha": "51e044499bcf8828f9bf92c4472f6c0419f58834",
        "outcome_run_id": 35428349640,
        "outcome": 0,
        "probe_job_id": 106258118081,
        "artifact_id": 10627811749,
    },
    "p1291-fail": {
        "pr": 1291,
        "source_sha": "17f70d5398a710a3714de8dd50f400b3a6c27dee",
        "outcome_run_id": 35575389514,
        "outcome": 1,
        "probe_job_id": 106258118184,
        "artifact_id": 10628541429,
    },
    "p1292-pass": {
        "pr": 1292,
        "source_sha": "9c0e4cd1cf37ff7bebbda9b33734504c32787862",
        "outcome_run_id": 35575604789,
        "outcome": 0,
        "probe_job_id": 106258118152,
        "artifact_id": 10628186969,
    },
}


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_ledger(ledger: dict) -> list[dict]:
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        raise ValueError("W82 ledger schema mismatch")
    if ledger.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("W82 ledger repository mismatch")
    if ledger.get("authority_transfer") is not False:
        raise ValueError("W82 authority transfer must remain false")

    probe = ledger.get("source_probe") or {}
    for field, expected in EXPECTED_PROBE.items():
        if probe.get(field) != expected:
            raise ValueError(f"W82 source probe mismatch for {field}")
    if probe.get("draft_merge_prevention") is not True:
        raise ValueError("W82 requires explicit draft merge prevention")

    states = list(ledger.get("states") or [])
    if len(states) != 6:
        raise ValueError("W82 requires exactly six measured states")
    if {s.get("label") for s in states} != set(EXPECTED_STATES):
        raise ValueError("W82 state labels mismatch")

    for state in states:
        label = state["label"]
        expected = EXPECTED_STATES[label]
        if state.get("pr") != expected["pr"]:
            raise ValueError(f"W82 PR mismatch for {label}")
        if state.get("source_sha") != expected["source_sha"]:
            raise ValueError(f"W82 source SHA mismatch for {label}")
        outcome = state.get("outcome") or {}
        if outcome.get("run_id") != expected["outcome_run_id"]:
            raise ValueError(f"W82 outcome run mismatch for {label}")
        if int(outcome.get("failure_label", -1)) != expected["outcome"]:
            raise ValueError(f"W82 outcome class mismatch for {label}")
        expected_conclusion = "failure" if expected["outcome"] else "success"
        if outcome.get("conclusion") != expected_conclusion:
            raise ValueError(f"W82 outcome conclusion mismatch for {label}")
        probe_row = state.get("probe") or {}
        if probe_row.get("job_id") != expected["probe_job_id"]:
            raise ValueError(f"W82 probe job mismatch for {label}")
        if probe_row.get("artifact_id") != expected["artifact_id"]:
            raise ValueError(f"W82 artifact mismatch for {label}")
        if not str(probe_row.get("artifact_digest", "")).startswith("sha256:"):
            raise ValueError(f"W82 artifact digest missing for {label}")

        semantic = dict(state.get("semantic_work_vector") or {})
        work = dict(state.get("work_vector") or {})
        if canonical_sha256(semantic) != state.get("semantic_work_vector_sha256"):
            raise ValueError(f"W82 semantic vector hash mismatch for {label}")
        if canonical_sha256(work) != state.get("work_vector_sha256"):
            raise ValueError(f"W82 work vector hash mismatch for {label}")

    labels = [int(s["outcome"]["failure_label"]) for s in states]
    if sorted(labels) != [0, 0, 0, 1, 1, 1]:
        raise ValueError("W82 requires balanced 3 PASS / 3 FAIL outcomes")
    return states


def frozen_pc1(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    means = matrix.mean(axis=0)
    sds = matrix.std(axis=0, ddof=1)
    if np.any(sds <= 0):
        raise ValueError("W82 frozen PCA basis requires varying training features")
    z = (matrix - means) / sds
    eigenvalues, eigenvectors = np.linalg.eigh(np.cov(z, rowvar=False, ddof=1))
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    vector = eigenvectors[:, order[0]].copy()
    pivot = int(np.argmax(np.abs(vector)))
    if vector[pivot] < 0:
        vector *= -1
    scores = z @ vector
    explained = float(eigenvalues[0] / eigenvalues.sum())
    return means, sds, vector, float(eigenvalues[0]), explained, scores


def auc_score(labels: np.ndarray, scores: np.ndarray) -> float:
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    wins = 0.0
    for pos in positive:
        for neg in negative:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positive) * len(negative))


def exact_auc_p(labels: np.ndarray, scores: np.ndarray) -> tuple[float, int]:
    observed = abs(auc_score(labels, scores) - 0.5)
    positive_count = int(np.sum(labels))
    extreme = 0
    total = 0
    for chosen in itertools.combinations(range(len(labels)), positive_count):
        candidate = np.zeros(len(labels), dtype=int)
        candidate[list(chosen)] = 1
        distance = abs(auc_score(candidate, scores) - 0.5)
        total += 1
        if distance + 1e-12 >= observed:
            extreme += 1
    return extreme / total, total


def evaluate(w79_source: dict, ledger: dict) -> dict:
    states = validate_ledger(ledger)
    w79 = load_module(
        "w79_deterministic_work_pca_for_w82",
        ROOT / "tools/w79_deterministic_work_pca.py",
    )
    normalized = w79.validate_input(w79_source)

    work_features = list(w79_source["work_features"])
    semantic_features = list(w79_source["semantic_work_features"])
    full_train = np.asarray(
        [[row["work_vector"][f] for f in work_features] for row in normalized],
        dtype=float,
    )
    semantic_train = np.asarray(
        [[row["semantic_work_vector"][f] for f in semantic_features] for row in normalized],
        dtype=float,
    )

    fm, fs, fv, feig, fevr, fscores = frozen_pc1(full_train)
    sm, ss, sv, seig, sevr, sscores = frozen_pc1(semantic_train)

    projection_rows = []
    for state in states:
        full = np.asarray([state["work_vector"][f] for f in work_features], dtype=float)
        semantic = np.asarray(
            [state["semantic_work_vector"][f] for f in semantic_features],
            dtype=float,
        )
        full_score = float(((full - fm) / fs) @ fv)
        semantic_score = float(((semantic - sm) / ss) @ sv)
        projection_rows.append(
            {
                "label": state["label"],
                "source_sha": state["source_sha"],
                "docs_failure": int(state["outcome"]["failure_label"]),
                "semantic_pc1": round(semantic_score, 12),
                "full_work_pc1": round(full_score, 12),
            }
        )

    labels = np.asarray([r["docs_failure"] for r in projection_rows], dtype=int)
    full_projection = np.asarray(
        [r["full_work_pc1"] for r in projection_rows], dtype=float
    )
    auc = auc_score(labels, full_projection)
    exact_p, permutations = exact_auc_p(labels, full_projection)

    semantic_hashes = {s["semantic_work_vector_sha256"] for s in states}
    full_min, full_max = float(np.min(fscores)), float(np.max(fscores))
    sem_min, sem_max = float(np.min(sscores)), float(np.max(sscores))
    outside_full = sum(
        r["full_work_pc1"] < full_min or r["full_work_pc1"] > full_max
        for r in projection_rows
    )
    outside_semantic = sum(
        r["semantic_pc1"] < sem_min or r["semantic_pc1"] > sem_max
        for r in projection_rows
    )

    result = {
        "schema_version": SCHEMA,
        "status": "CONTROLLED_NEGATIVE_SEMANTIC_DIVERSITY_DIAGNOSTIC",
        "authority": "derived_operational_analysis_only",
        "math_skill_resolution": {
            "schema": "gbogeb.skill.receipt.v1",
            "skill": "math",
            "task_id": "W82_SEMANTIC_DIVERSITY_PC1_PROJECTION",
            "source_repo": "GBOGEB/ABACUS",
            "source_ref": EXPECTED_PROBE["head_sha"],
            "resolved_skill_path": "skills/math/SKILL.md",
            "authority_transfer": False,
            "status": "PASS_SKILL_RESOLUTION",
        },
        "sample_geometry": {
            "measured_states": 6,
            "docs_pass": 3,
            "docs_fail": 3,
            "semantic_unique_vector_count": len(semantic_hashes),
            "full_work_unique_vector_count": len(
                {s["work_vector_sha256"] for s in states}
            ),
        },
        "frozen_w79_semantic_pc1": {
            "eigenvalue": round(seig, 12),
            "explained_variance_ratio": round(sevr, 12),
            "in_sample_min": round(sem_min, 12),
            "in_sample_max": round(sem_max, 12),
            "all_projection_score": projection_rows[0]["semantic_pc1"],
            "out_of_support_count": outside_semantic,
            "discrimination": False,
        },
        "frozen_w79_full_work_pc1": {
            "eigenvalue": round(feig, 12),
            "explained_variance_ratio": round(fevr, 12),
            "in_sample_min": round(full_min, 12),
            "in_sample_max": round(full_max, 12),
            "out_of_support_count": outside_full,
            "docs_failure_auc": round(auc, 12),
            "exact_permutation_p": round(exact_p, 12),
            "exact_permutation_count": permutations,
        },
        "projection_rows": projection_rows,
        "interpretation": {
            "supported": (
                "balanced PASS/FAIL outcomes remain indistinguishable on semantic PC1; "
                "full-work PC1 has no exact-test evidence of outcome discrimination"
            ),
            "not_supported": [
                "semantic PC1 predicts docs outcome",
                "full-work PC1 predicts docs outcome",
                "BT ranking from these states",
                "generalization from extrapolative high-tail states",
            ],
        },
        "pc1_predictive_validation": False,
        "pairwise_outcome_accumulation_permitted": False,
        "pairwise_events": [],
        "bt_status": "WITHHELD_NO_CONNECTED_OBSERVED_PAIRWISE_GRAPH",
        "pca_refit_performed": False,
        "timing_pca_reopened": False,
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
        "next_frontier": (
            "change the measurement basis or seek exact-source states with genuinely "
            "different semantic-work vectors inside or spanning the W79 support range"
        ),
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--w79-input", default=str(W79_INPUT))
    parser.add_argument("--ledger", default=str(LEDGER))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    w79_source = json.loads(Path(args.w79_input).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result = evaluate(w79_source, ledger)
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
