#!/usr/bin/env python3
"""W83 exact outcome discrimination check for the harvested typed-basis probe."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

SCHEMA = "MC2-W83-TYPED-BASIS-OUTCOME-DIAGNOSTIC-0.1.0"
LEDGER_SCHEMA = "MC2-W83-TYPED-BASIS-OUTCOME-LEDGER-0.1.0"

EXPECTED_LABELS = {
    "p1281-pass": 0,
    "p1286-fail": 1,
    "p1288-fail": 1,
    "p1289-pass": 0,
    "p1291-fail": 1,
    "p1292-pass": 0,
}
EXPECTED_AGGREGATE = {
    "run_id": 35577332406,
    "aggregate_job_id": 106262300145,
    "aggregate_artifact_id": 10628574063,
    "aggregate_artifact_digest": "sha256:c6415796547132f65b1e67b44fea36e5740bd20c8c774ba967d02b17e4d5a348",
}
EXPECTED_FEATURES = [
    "workflow_governance_composition.keep_rules",
    "workflow_governance_composition.pr_domain_rules",
    "workflow_governance_composition.rule_count",
]


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _hypergeom_prob(a: int, r1: int, c1: int, n: int) -> float:
    return (
        math.comb(c1, a)
        * math.comb(n - c1, r1 - a)
        / math.comb(n, r1)
    )


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    r1 = a + b
    c1 = a + c
    n = a + b + c + d
    lo = max(0, r1 - (n - c1))
    hi = min(r1, c1)
    observed = _hypergeom_prob(a, r1, c1, n)
    total = 0.0
    for candidate in range(lo, hi + 1):
        p = _hypergeom_prob(candidate, r1, c1, n)
        if p <= observed + 1e-15:
            total += p
    return min(1.0, total)


def mutual_information_bits(table: list[list[int]]) -> float:
    n = sum(sum(row) for row in table)
    row_totals = [sum(row) for row in table]
    col_totals = [sum(table[r][c] for r in range(len(table))) for c in range(2)]
    value = 0.0
    for r, row in enumerate(table):
        for c, count in enumerate(row):
            if count == 0:
                continue
            pxy = count / n
            px = row_totals[r] / n
            py = col_totals[c] / n
            value += pxy * math.log2(pxy / (px * py))
    return value


def validate(ledger: dict) -> list[dict]:
    if ledger.get("schema_version") != LEDGER_SCHEMA:
        raise ValueError("W83 ledger schema mismatch")
    if ledger.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("W83 repository mismatch")
    source = ledger.get("source_probe") or {}
    for key, expected in EXPECTED_AGGREGATE.items():
        if source.get(key) != expected:
            raise ValueError(f"W83 aggregate lineage mismatch: {key}")
    if ledger.get("variable_features") != EXPECTED_FEATURES:
        raise ValueError("W83 variable feature set drift")
    if ledger.get("recent_semantic_composition_unique_count") != 1:
        raise ValueError("W83 recent semantic composition must remain saturated")
    if ledger.get("recent_consumer_graph_unique_count") != 1:
        raise ValueError("W83 recent consumer graph must remain saturated")

    rows = list(ledger.get("rows") or [])
    if len(rows) != 6:
        raise ValueError("W83 requires exactly six recent outcome rows")
    labels = {row.get("label") for row in rows}
    if labels != set(EXPECTED_LABELS):
        raise ValueError("W83 recent label set mismatch")
    for row in rows:
        expected = EXPECTED_LABELS[row["label"]]
        if row.get("outcome", {}).get("failure_label") != expected:
            raise ValueError(f"W83 outcome mismatch for {row['label']}")
        if row.get("outcome", {}).get("conclusion") != ("failure" if expected else "success"):
            raise ValueError(f"W83 conclusion mismatch for {row['label']}")
        vector = row.get("vector") or {}
        if set(vector) != {"keep_rules", "pr_domain_rules", "rule_count"}:
            raise ValueError("W83 compact vector schema drift")
        probe = row.get("w83_probe") or {}
        if int(probe.get("artifact_id", 0)) <= 0:
            raise ValueError("W83 probe artifact ID missing")
        if not str(probe.get("artifact_digest", "")).startswith("sha256:"):
            raise ValueError("W83 probe digest missing")
    return rows


def evaluate(ledger: dict) -> dict:
    rows = validate(ledger)
    grouped: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    for row in rows:
        v = row["vector"]
        key = (int(v["keep_rules"]), int(v["pr_domain_rules"]), int(v["rule_count"]))
        grouped[key].append(row)
    if len(grouped) != 2:
        raise ValueError("W83 expected exactly two observed governance vectors")

    ordered = sorted(grouped.items())
    summaries = []
    table = []
    for key, group in ordered:
        fail = sum(int(row["outcome"]["failure_label"]) for row in group)
        passed = len(group) - fail
        summaries.append({
            "vector": {
                "keep_rules": key[0],
                "pr_domain_rules": key[1],
                "rule_count": key[2],
            },
            "state_count": len(group),
            "pass_count": passed,
            "failure_count": fail,
            "pass_fraction": passed / len(group),
            "labels": sorted(row["label"] for row in group),
        })
        table.append([passed, fail])

    a, b = table[0]
    c, d = table[1]
    odds_ratio = (a * d) / (b * c) if b and c else None
    fisher_p = fisher_two_sided(a, b, c, d)
    mi = mutual_information_bits(table)
    discriminates = fisher_p <= 0.05 and mi > 0.0

    result = {
        "schema_version": SCHEMA,
        "status": "CONTROLLED_NEGATIVE_TYPED_BASIS_OUTCOME_DIAGNOSTIC",
        "authority": "derived_operational_analysis_only",
        "measurement_basis": "typed_semantic_and_governance_composition_exact_source",
        "source_probe_run_id": EXPECTED_AGGREGATE["run_id"],
        "source_probe_aggregate_artifact_id": EXPECTED_AGGREGATE["aggregate_artifact_id"],
        "source_probe_aggregate_artifact_digest": EXPECTED_AGGREGATE["aggregate_artifact_digest"],
        "sample_geometry": {
            "state_count": 6,
            "outcome_pass": 3,
            "outcome_fail": 3,
            "unique_recent_typed_vectors": 2,
            "unique_recent_semantic_composition": 1,
            "unique_recent_consumer_graph_distribution": 1,
            "variable_feature_count": 3,
            "variable_features": EXPECTED_FEATURES,
        },
        "vector_groups": summaries,
        "contingency_table_rows_are_vectors_cols_are_pass_fail": table,
        "exact_inference": {
            "odds_ratio": odds_ratio,
            "fisher_exact_two_sided_p": fisher_p,
            "mutual_information_bits": mi,
            "interpretation": "both observed vectors have identical 0.5 pass fractions",
        },
        "typed_basis_diversity_signal_present": True,
        "outcome_discrimination_supported": discriminates,
        "pca_fit_performed": False,
        "pc1_predictive_validation": False,
        "pairwise_outcome_accumulation_permitted": False,
        "pairwise_events": [],
        "bt_status": "WITHHELD_NO_CONNECTED_OBSERVED_PAIRWISE_GRAPH",
        "timing_pca_reopened": False,
        "global_allocation_authority": False,
        "engineering_compliance_release_authority": False,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "next_frontier": (
            "seek exact-source outcome states with genuinely varying non-governance "
            "semantic-composition or consumer-graph vectors; do not fit PCA or BT "
            "from the two-vector governance-only contrast"
        ),
    }
    result["source_ledger_sha256"] = canonical_sha256(ledger)
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result = evaluate(ledger)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
