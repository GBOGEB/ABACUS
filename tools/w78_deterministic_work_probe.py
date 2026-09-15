#!/usr/bin/env python3
"""Emit deterministic algorithmic-work vectors for exact historical ABACUS states."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import w72_semantic_census as w72
import w77_instrumented_semantic_census as w77

SCHEMA_VERSION = "MC2-W78-DETERMINISTIC-WORK-PROBE-0.1.0"
WORK_FEATURES = (
    "scanned_text_files",
    "scanned_text_bytes",
    "consumer_candidate_checks",
    "consumer_hits",
    "consumer_files_with_hits",
    "semantic_entities",
    "semantic_references",
    "lineage_paths",
    "graph_nodes",
    "graph_edges",
)
SEMANTIC_WORK_FEATURES = (
    "consumer_hits",
    "consumer_files_with_hits",
    "semantic_entities",
    "semantic_references",
    "lineage_paths",
    "graph_nodes",
    "graph_edges",
)


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def probe(root: Path, source_sha: str, repeat: int, label: str) -> dict:
    receipts, feature_row, telemetry = w77.build_instrumented(root, source_sha)
    baseline_receipts, baseline_row = w72.measure(root, source_sha)
    if receipts != baseline_receipts or feature_row != baseline_row:
        raise RuntimeError("W78 semantic parity failure against canonical W72")

    counters = telemetry["work_counters"]
    work_vector = {name: int(counters[name]) for name in WORK_FEATURES}
    semantic_work_vector = {
        name: int(counters[name]) for name in SEMANTIC_WORK_FEATURES
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": "GBOGEB/ABACUS",
        "source_sha": source_sha,
        "matrix_label": label,
        "repeat": repeat,
        "probe": "w72_exact_source_deterministic_algorithmic_work",
        "semantic_parity_with_w72": True,
        "feature_row": feature_row,
        "feature_row_sha256": canonical_sha256(feature_row),
        "work_vector": work_vector,
        "work_vector_sha256": canonical_sha256(work_vector),
        "semantic_work_vector": semantic_work_vector,
        "semantic_work_vector_sha256": canonical_sha256(semantic_work_vector),
        "execution_state": "PASS",
        "authority": "derived_operational_analysis",
        "pca_fit_performed": False,
        "global_allocation_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--repeat", required=True, type=int)
    parser.add_argument("--matrix-label", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    receipt = probe(
        Path(args.root).resolve(),
        args.source_sha,
        args.repeat,
        args.matrix_label,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
