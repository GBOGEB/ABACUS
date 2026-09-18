#!/usr/bin/env python3
"""W80 independent observed-outcome validation for W79 deterministic PC1."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

SCHEMA = "MC2-W80-OBSERVED-OUTCOME-VALIDATION-0.1.1"
LEDGER_SCHEMA = "MC2-W80-OBSERVED-VALIDATION-OUTCOME-0.1.0"
RUN_RECEIPT_SCHEMA = "MC2-W80-GITHUB-ACTIONS-RUN-RECEIPT-0.1.0"
EXPECTED_LEDGER_CANONICAL_SHA256 = (
    "f28c2f8d65694ff7f99a3122700008b647cad9b644ea22bec153cd8004106ec5"
)
EXPECTED_W79_INPUT_CANONICAL_SHA256 = (
    "6a40340a96d45491e0f946bbfda5f62f883c80b0a6e91ca2406fc0716165aad4"
)
EXPECTED_RUN_RECEIPT_SHA256 = "1412820d9ccfb3eda94ce5deddfe0f25d68d3f7ba032b11a870490a4a0ecfb01"
CORE_WORKFLOWS = [
    "CI - ABACUS Matrix",
    "DELTA_1 CodeQL",
    "Format Check",
    "Security Scan — Ruff",
    "Validate Docs (Markdown/YAML/JSON)",
    "YAML Validation",
    "qps-canonicalization",
]
DOCS_WORKFLOW = "Validate Docs (Markdown/YAML/JSON)"

MIN_COVERED_STATES = 10
MIN_COVERAGE_FRACTION = 2.0 / 3.0
SPEARMAN_ABS_MIN = 0.50
EXACT_P_MAX = 0.05
LOOCV_R2_MIN = 0.0
AUC_DISTANCE_FROM_CHANCE_MIN = 0.25
MIN_PC1_RANGE_COVERAGE = 0.70

ROOT = Path(__file__).resolve().parents[1]
RUN_RECEIPT_PATH = ROOT / "architecture/w80/W80_GITHUB_ACTIONS_RUN_RECEIPT.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_governed_run_receipt() -> dict:
    if file_sha256(RUN_RECEIPT_PATH) != EXPECTED_RUN_RECEIPT_SHA256:
        raise ValueError("W80 governed Actions run receipt payload mismatch")
    receipt = json.loads(RUN_RECEIPT_PATH.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != RUN_RECEIPT_SCHEMA:
        raise ValueError("W80 Actions run receipt schema mismatch")
    if receipt.get("repository_id") != 1054507184:
        raise ValueError("W80 Actions run receipt repository ID mismatch")
    if receipt.get("repository_full_name") != "GBOGEB/ABACUS":
        raise ValueError("W80 Actions run receipt repository mismatch")
    if int(receipt.get("source_state_count", 0)) != 11:
        raise ValueError("W80 Actions run receipt source-state count mismatch")
    if int(receipt.get("run_count", 0)) != 77:
        raise ValueError("W80 Actions run receipt run count mismatch")
    return receipt


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def average_ranks(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0 + 1.0
        ranks[order[i:j]] = rank
        i = j
    return ranks


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a - a.mean()
    b = b - b.mean()
    denominator = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
    if denominator == 0:
        raise ValueError("correlation requires non-constant inputs")
    return float(np.sum(a * b) / denominator)


def spearman_rho(a: np.ndarray, b: np.ndarray) -> float:
    return correlation(average_ranks(a), average_ranks(b))


def exact_multiset_spearman_p(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    observed = abs(spearman_rho(a, b))
    unique, counts = np.unique(np.asarray(b, dtype=float), return_counts=True)
    if len(unique) < 2:
        raise ValueError("exact Spearman test requires at least two outcome values")
    if len(a) > 12:
        raise ValueError("exact W80 multiset permutation is bounded to n<=12")

    rank_a = average_ranks(np.asarray(a, dtype=float))
    extreme = 0
    total = 0
    n = len(a)

    def recurse(level: int, available: tuple[int, ...], assigned: np.ndarray):
        nonlocal extreme, total
        if level == len(unique) - 1:
            candidate = assigned.copy()
            for idx in available:
                candidate[idx] = unique[level]
            rho = abs(correlation(rank_a, average_ranks(candidate)))
            total += 1
            if rho + 1e-12 >= observed:
                extreme += 1
            return

        count = int(counts[level])
        for chosen in itertools.combinations(available, count):
            chosen_set = set(chosen)
            candidate = assigned.copy()
            for idx in chosen:
                candidate[idx] = unique[level]
            remainder = tuple(idx for idx in available if idx not in chosen_set)
            recurse(level + 1, remainder, candidate)

    recurse(0, tuple(range(n)), np.zeros(n, dtype=float))
    return extreme / total, total


def loocv_linear_r2(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    predictions = np.empty(len(x), dtype=float)
    for held_out in range(len(x)):
        keep = np.arange(len(x)) != held_out
        design = np.column_stack([np.ones(int(np.sum(keep))), x[keep]])
        beta, *_ = np.linalg.lstsq(design, y[keep], rcond=None)
        predictions[held_out] = beta[0] + beta[1] * x[held_out]
    ss_total = float(np.sum((y - y.mean()) ** 2))
    if ss_total == 0:
        raise ValueError("LOOCV R2 requires outcome variance")
    ss_residual = float(np.sum((y - predictions) ** 2))
    r2 = 1.0 - ss_residual / ss_total
    mae = float(np.mean(np.abs(y - predictions)))
    rmse = float(np.sqrt(np.mean((y - predictions) ** 2)))
    return r2, mae, rmse


def auc_score(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    if len(positive) == 0 or len(negative) == 0:
        raise ValueError("AUC requires both outcome classes")
    wins = 0.0
    for pos in positive:
        for neg in negative:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positive) * len(negative))


def exact_auc_p(labels: np.ndarray, scores: np.ndarray) -> tuple[float, int]:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
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


def validate_ledger(
    ledger: dict,
    w79_source: dict,
    w79_module,
    run_receipt: dict,
) -> list[dict]:
    if canonical_sha256(ledger) != EXPECTED_LEDGER_CANONICAL_SHA256:
        raise ValueError("W80 governed outcome ledger payload mismatch")
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        raise ValueError("W80 outcome ledger schema mismatch")
    if ledger.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("W80 outcome ledger repository mismatch")
    if (
        ledger.get("source_w79_input_canonical_sha256")
        != EXPECTED_W79_INPUT_CANONICAL_SHA256
    ):
        raise ValueError("W80 source W79 input identity mismatch")

    normalized_w79 = w79_module.validate_input(w79_source)
    expected_population = {
        (row["matrix_label"], row["source_sha"]) for row in normalized_w79
    }
    states = list(ledger.get("states") or [])
    actual_population = {
        (state.get("label"), state.get("source_sha")) for state in states
    }
    if actual_population != expected_population:
        raise ValueError("W80 outcome population must exactly match W79 source states")

    outcome_block = ledger.get("outcome_block") or {}
    if outcome_block.get("core_workflows") != CORE_WORKFLOWS:
        raise ValueError("W80 core validation workflow contract drift")
    if outcome_block.get("cancelled_policy") != "missing_not_failure":
        raise ValueError("cancelled validation must remain missing, not failure")
    if outcome_block.get("missing_state_policy") != "missing_not_zero":
        raise ValueError("missing source-state validation must remain missing, not zero")

    receipt_runs = list(run_receipt.get("runs") or [])
    receipt_by_id = {int(run["run_id"]): run for run in receipt_runs}
    if len(receipt_by_id) != len(receipt_runs):
        raise ValueError("W80 Actions run receipt contains duplicate run IDs")

    observed = []
    missing = []
    seen_run_ids: set[int] = set()
    for state in states:
        status = state.get("status")
        runs = list(state.get("runs") or [])
        if status == "NO_ACTIONS_EVIDENCE":
            if runs:
                raise ValueError("missing state cannot carry synthetic validation runs")
            missing.append(state)
            continue
        if status != "OBSERVED":
            raise ValueError("unknown W80 outcome state")
        if len(runs) != len(CORE_WORKFLOWS):
            raise ValueError("observed W80 state requires the complete seven-workflow core")
        names = [run.get("name") for run in runs]
        if sorted(names) != sorted(CORE_WORKFLOWS) or len(set(names)) != len(names):
            raise ValueError("W80 observed workflow names must match the core exactly")
        for run in runs:
            run_id = int(run.get("run_id", 0))
            if run_id <= 0 or run_id in seen_run_ids:
                raise ValueError("W80 validation run IDs must be positive and unique")
            seen_run_ids.add(run_id)
            if run.get("event") not in {"push", "pull_request"}:
                raise ValueError("W80 validation event must be push or pull_request")
            if run.get("conclusion") not in {"success", "failure", "cancelled"}:
                raise ValueError("W80 validation conclusion outside governed classes")
            authoritative = receipt_by_id.get(run_id)
            if authoritative is None:
                raise ValueError(f"W80 run {run_id} missing from Actions producer receipt")
            expected_binding = {
                "repository_id": 1054507184,
                "repository_full_name": "GBOGEB/ABACUS",
                "source_sha": state["source_sha"],
                "workflow_name": run["name"],
                "event": run["event"],
                "conclusion": run["conclusion"],
            }
            for field, expected in expected_binding.items():
                if authoritative.get(field) != expected:
                    raise ValueError(
                        f"W80 authoritative run binding mismatch for {run_id}:{field}"
                    )
        observed.append(state)

    if int(ledger.get("population_target_count", 0)) != 15:
        raise ValueError("W80 target population must remain 15 W79 states")
    if int(ledger.get("covered_state_count", 0)) != len(observed):
        raise ValueError("W80 covered-state count mismatch")
    if int(ledger.get("missing_state_count", 0)) != len(missing):
        raise ValueError("W80 missing-state count mismatch")
    if len(observed) != 11 or len(missing) != 4:
        raise ValueError("W80 governed outcome ledger must preserve 11 observed / 4 missing")
    if seen_run_ids != set(receipt_by_id):
        raise ValueError("W80 Actions producer receipt and ledger run sets differ")
    return normalized_w79


def semantic_pc1(w79_source: dict, normalized_w79: list[dict]) -> dict:
    features = list(w79_source["semantic_work_features"])
    matrix = np.asarray(
        [
            [float(row["semantic_work_vector"][feature]) for feature in features]
            for row in normalized_w79
        ],
        dtype=float,
    )
    means = matrix.mean(axis=0)
    sds = matrix.std(axis=0, ddof=1)
    if np.any(sds <= 0):
        raise ValueError("W80 semantic PC1 requires varying W79 semantic features")
    z = (matrix - means) / sds
    eigenvalues, eigenvectors = np.linalg.eigh(np.cov(z, rowvar=False, ddof=1))
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    vector = eigenvectors[:, order[0]]
    pivot = int(np.argmax(np.abs(vector)))
    if vector[pivot] < 0:
        vector *= -1
    scores = z @ vector
    return {
        "eigenvalue": float(eigenvalues[0]),
        "explained_variance_ratio": float(eigenvalues[0] / eigenvalues.sum()),
        "scores": {
            row["source_sha"]: float(score)
            for row, score in zip(normalized_w79, scores)
        },
    }


def evaluate(w79_source: dict, ledger: dict) -> dict:
    w79_module = load_module(
        "w79_deterministic_work_pca_for_w80",
        ROOT / "tools/w79_deterministic_work_pca.py",
    )
    run_receipt = load_governed_run_receipt()
    normalized_w79 = validate_ledger(
        ledger,
        w79_source,
        w79_module,
        run_receipt,
    )
    pc1 = semantic_pc1(w79_source, normalized_w79)

    outcome_rows = []
    missing_rows = []
    for state in ledger["states"]:
        if state["status"] == "NO_ACTIONS_EVIDENCE":
            missing_rows.append(
                {"label": state["label"], "source_sha": state["source_sha"]}
            )
            continue

        conclusions = {run["name"]: run["conclusion"] for run in state["runs"]}
        success = sum(value == "success" for value in conclusions.values())
        failure = sum(value == "failure" for value in conclusions.values())
        cancelled = sum(value == "cancelled" for value in conclusions.values())
        executed = success + failure
        if executed < 6:
            raise ValueError("W80 observed state has insufficient executed core validators")
        docs = conclusions[DOCS_WORKFLOW]
        if docs not in {"success", "failure"}:
            raise ValueError("W80 docs outcome must be an observed success/failure")
        outcome_rows.append(
            {
                "label": state["label"],
                "source_sha": state["source_sha"],
                "semantic_pc1_score": pc1["scores"][state["source_sha"]],
                "executed_core_validators": executed,
                "cancelled_core_validators": cancelled,
                "core_success_count": success,
                "core_failure_count": failure,
                "core_pass_fraction": success / executed,
                "docs_validation_failure": 1 if docs == "failure" else 0,
                "run_ids": [int(run["run_id"]) for run in state["runs"]],
            }
        )

    x = np.asarray([row["semantic_pc1_score"] for row in outcome_rows], dtype=float)
    pass_fraction = np.asarray(
        [row["core_pass_fraction"] for row in outcome_rows], dtype=float
    )
    docs_failure = np.asarray(
        [row["docs_validation_failure"] for row in outcome_rows], dtype=int
    )

    rho = spearman_rho(x, pass_fraction)
    spearman_p, spearman_permutations = exact_multiset_spearman_p(x, pass_fraction)
    cv_r2, cv_mae, cv_rmse = loocv_linear_r2(x, pass_fraction)
    docs_auc = auc_score(docs_failure, x)
    auc_p, auc_permutations = exact_auc_p(docs_failure, x)

    coverage_fraction = len(outcome_rows) / int(ledger["population_target_count"])
    full_pc1 = np.asarray(list(pc1["scores"].values()), dtype=float)
    observed_pc1 = x
    missing_pc1 = np.asarray(
        [pc1["scores"][row["source_sha"]] for row in missing_rows],
        dtype=float,
    )
    full_pc1_min = float(np.min(full_pc1))
    full_pc1_max = float(np.max(full_pc1))
    observed_pc1_min = float(np.min(observed_pc1))
    observed_pc1_max = float(np.max(observed_pc1))
    full_pc1_range = full_pc1_max - full_pc1_min
    if full_pc1_range <= 0:
        raise ValueError("W80 PC1 population range must be positive")
    pc1_range_coverage = (observed_pc1_max - observed_pc1_min) / full_pc1_range
    range_gate = pc1_range_coverage >= MIN_PC1_RANGE_COVERAGE

    primary_gate = (
        len(outcome_rows) >= MIN_COVERED_STATES
        and coverage_fraction >= MIN_COVERAGE_FRACTION
        and range_gate
        and abs(rho) >= SPEARMAN_ABS_MIN
        and spearman_p <= EXACT_P_MAX
        and cv_r2 > LOOCV_R2_MIN
    )
    secondary_gate = (
        abs(docs_auc - 0.5) >= AUC_DISTANCE_FROM_CHANCE_MIN
        and auc_p <= EXACT_P_MAX
    )
    predictive_validation = primary_gate and secondary_gate

    result = {
        "schema_version": SCHEMA,
        "status": (
            "OUTCOME_VALIDATION_SUPPORTED_DIAGNOSTIC_ONLY"
            if predictive_validation
            else "OUTCOME_VALIDATION_NOT_SUPPORTED"
        ),
        "authority": "derived_operational_analysis",
        "measurement_basis": "independent_observed_validation_outcomes_not_elapsed_time",
        "source_w79_input_canonical_sha256": EXPECTED_W79_INPUT_CANONICAL_SHA256,
        "source_outcome_ledger_canonical_sha256": EXPECTED_LEDGER_CANONICAL_SHA256,
        "source_actions_run_receipt_sha256": EXPECTED_RUN_RECEIPT_SHA256,
        "semantic_pc1": {
            "eigenvalue": round(pc1["eigenvalue"], 6),
            "explained_variance_ratio": round(
                pc1["explained_variance_ratio"], 6
            ),
            "role": "deterministic_complexity_axis",
        },
        "outcome_coverage": {
            "target_states": int(ledger["population_target_count"]),
            "observed_states": len(outcome_rows),
            "missing_states": len(missing_rows),
            "coverage_fraction": round(coverage_fraction, 6),
            "missing_state_policy": "missing_not_zero",
            "pc1_full_min": round(full_pc1_min, 6),
            "pc1_full_max": round(full_pc1_max, 6),
            "pc1_observed_min": round(observed_pc1_min, 6),
            "pc1_observed_max": round(observed_pc1_max, 6),
            "pc1_range_coverage_fraction": round(pc1_range_coverage, 6),
            "range_restriction_warning": not range_gate,
            "missing_pc1_mean": round(float(np.mean(missing_pc1)), 6),
            "observed_pc1_mean": round(float(np.mean(observed_pc1)), 6),
            "missing_rows": missing_rows,
        },
        "primary_outcome": {
            "name": "core_validation_pass_fraction",
            "cancelled_policy": "excluded_as_missing",
            "spearman_rho": round(rho, 6),
            "exact_permutation_p": round(spearman_p, 6),
            "exact_permutation_count": spearman_permutations,
            "loocv_linear_r2": round(cv_r2, 6),
            "loocv_mae": round(cv_mae, 6),
            "loocv_rmse": round(cv_rmse, 6),
        },
        "secondary_outcome": {
            "name": "docs_validation_failure",
            "positive_count": int(np.sum(docs_failure)),
            "negative_count": int(len(docs_failure) - np.sum(docs_failure)),
            "auc": round(docs_auc, 6),
            "exact_permutation_p": round(auc_p, 6),
            "exact_permutation_count": auc_permutations,
        },
        "predeclared_gate": {
            "minimum_observed_states": MIN_COVERED_STATES,
            "minimum_coverage_fraction": MIN_COVERAGE_FRACTION,
            "minimum_absolute_spearman": SPEARMAN_ABS_MIN,
            "maximum_exact_p": EXACT_P_MAX,
            "minimum_loocv_r2_strictly_greater_than": LOOCV_R2_MIN,
            "minimum_auc_distance_from_chance": AUC_DISTANCE_FROM_CHANCE_MIN,
            "minimum_pc1_range_coverage_fraction": MIN_PC1_RANGE_COVERAGE,
            "pc1_range_gate_pass": range_gate,
            "primary_gate_pass": primary_gate,
            "secondary_gate_pass": secondary_gate,
        },
        "outcome_rows": outcome_rows,
        "pc1_predictive_validation": predictive_validation,
        "pairwise_outcome_accumulation_permitted": predictive_validation,
        "pairwise_events": [],
        "bt_status": (
            "READY_FOR_GENUINE_OBSERVED_PAIRWISE_ACCUMULATION"
            if predictive_validation
            else "WITHHELD_PC1_NOT_VALIDATED_AGAINST_OBSERVED_OUTCOMES"
        ),
        "timing_pca_reopened": False,
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
        "next_step": (
            "expand independent outcomes into the low-complexity PC1 tail or bind "
            "a comparable repair/work outcome block; do not create BT pairs from "
            "range-restricted, unvalidated PC1"
        ),
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--w79-input",
        default=str(ROOT / "architecture/w79/W79_W78_INPUT.json"),
    )
    parser.add_argument(
        "--outcome-ledger",
        default=str(ROOT / "architecture/w80/W80_OBSERVED_VALIDATION_LEDGER.json"),
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    w79_source = json.loads(Path(args.w79_input).read_text(encoding="utf-8"))
    ledger = json.loads(Path(args.outcome_ledger).read_text(encoding="utf-8"))
    result = evaluate(w79_source, ledger)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
