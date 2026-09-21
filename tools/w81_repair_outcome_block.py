#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
W79_INPUT = ROOT / "architecture/w79/W79_W78_INPUT.json"
W79_TOOL = ROOT / "tools/w79_deterministic_work_pca.py"

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def frozen_semantic_basis(source: dict) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    w79 = load_module("w79_for_w81", W79_TOOL)
    rows = w79.validate_input(source)
    features = list(source["semantic_work_features"])
    matrix = np.asarray(
        [[float(row["semantic_work_vector"][f]) for f in features] for row in rows],
        dtype=float,
    )
    means = matrix.mean(axis=0)
    sds = matrix.std(axis=0, ddof=1)
    z = (matrix - means) / sds
    eigenvalues, eigenvectors = np.linalg.eigh(np.cov(z, rowvar=False, ddof=1))
    order = np.argsort(eigenvalues)[::-1]
    vector = eigenvectors[:, order[0]]
    pivot = int(np.argmax(np.abs(vector)))
    if vector[pivot] < 0:
        vector *= -1
    return features, means, sds, vector

def project(receipt: dict, features: list[str], means: np.ndarray, sds: np.ndarray, vector: np.ndarray) -> float:
    if receipt.get("schema_version") != "MC2-W78-DETERMINISTIC-WORK-PROBE-0.1.0":
        raise ValueError("W81 requires W78-compatible exact-source work receipts")
    if receipt.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("W81 work receipt repository mismatch")
    if receipt.get("execution_state") != "PASS" or receipt.get("semantic_parity_with_w72") is not True:
        raise ValueError("W81 work receipt did not pass exact-source semantic parity")
    vec = receipt.get("semantic_work_vector") or {}
    if set(vec) != set(features):
        raise ValueError("W81 semantic work feature set mismatch")
    x = np.asarray([float(vec[f]) for f in features], dtype=float)
    return float(((x - means) / sds) @ vector)

def components(events: list[dict]) -> int:
    nodes = set()
    graph = {}
    for event in events:
        a, b = event["winner_source_sha"], event["loser_source_sha"]
        nodes.update((a, b))
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    seen=set()
    count=0
    for node in nodes:
        if node in seen:
            continue
        count += 1
        stack=[node]
        seen.add(node)
        while stack:
            cur=stack.pop()
            for nxt in graph.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return count

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--verification", required=True)
    ap.add_argument("--receipts-dir", required=True)
    ap.add_argument("--out", required=True)
    args=ap.parse_args()

    contract=json.loads(Path(args.contract).read_text(encoding="utf-8"))
    verification=json.loads(Path(args.verification).read_text(encoding="utf-8"))
    if verification.get("result") != "PASS":
        raise ValueError("W81 requires authoritative GitHub outcome verification PASS")
    if verification["primary_frontier"]["result"] != "EXHAUSTED_NO_ACTIONS_EVIDENCE":
        raise ValueError("W81 primary low-PC1 frontier is not exhausted as declared")
    if contract["source_w80"]["pc1_predictive_validation"] is not False:
        raise ValueError("W81 contract must preserve W80 negative predictive validation")

    source=json.loads(W79_INPUT.read_text(encoding="utf-8"))
    features, means, sds, vector=frozen_semantic_basis(source)

    receipts={}
    for p in Path(args.receipts_dir).glob("W81_*_WORK_RECEIPT.json"):
        r=json.loads(p.read_text(encoding="utf-8"))
        receipts[r["matrix_label"]]=r

    expected_labels={
        x[k]
        for x in contract["episodes"]
        for k in ("failure_label","repair_label")
    }
    if set(receipts) != expected_labels:
        raise ValueError(f"W81 work receipt labels mismatch: {sorted(receipts)}")

    scores={label: project(r, features, means, sds, vector) for label,r in receipts.items()}
    events=[]
    pair_rows=[]
    for episode in contract["episodes"]:
        fail=episode["failure_label"]
        repair=episode["repair_label"]
        if receipts[fail]["source_sha"] != episode["failure_source_sha"]:
            raise ValueError(f"{fail} source SHA mismatch")
        if receipts[repair]["source_sha"] != episode["repair_source_sha"]:
            raise ValueError(f"{repair} source SHA mismatch")
        pair_rows.append({
            "episode_id": episode["episode_id"],
            "failure_source_sha": episode["failure_source_sha"],
            "repair_source_sha": episode["repair_source_sha"],
            "failure_pc1": round(scores[fail], 6),
            "repair_pc1": round(scores[repair], 6),
            "delta_pc1_repair_minus_failure": round(scores[repair]-scores[fail], 6),
            "machine_outcome": "NAMED_RED_TO_GREEN",
            "causal_effect_claimed": False,
        })
        events.append({
            "episode_id": episode["episode_id"],
            "winner_source_sha": episode["repair_source_sha"],
            "loser_source_sha": episode["failure_source_sha"],
            "basis": "OBSERVED_NAMED_RED_TO_GREEN_REPAIR_EPISODE",
            "bt_admitted": False,
        })

    component_count=components(events)
    pair_count=len(events)
    guards=contract["promotion_guards"]
    reasons=[]
    if contract["source_w80"]["pc1_predictive_validation"] is False:
        reasons.append("W80_PC1_PREDICTIVE_VALIDATION_FALSE")
    if pair_count < int(guards["minimum_pair_count_for_any_model_fit"]):
        reasons.append("PAIR_COUNT_BELOW_MODEL_FIT_MINIMUM")
    if component_count != 1:
        reasons.append("PAIR_GRAPH_DISCONNECTED")

    result={
        "schema_version":"MC2-W81-REPAIR-OUTCOME-BLOCK-0.1.0",
        "status":"MEASURED_REPAIR_OUTCOME_BLOCK_BT_WITHHELD",
        "authority":"derived_operational_analysis",
        "measurement_basis":"exact_source_deterministic_work_plus_authoritative_machine_red_to_green_episodes",
        "repair_episode_semantics":contract["repair_episode_semantics"],
        "primary_low_pc1_frontier":"EXHAUSTED_NO_ACTIONS_EVIDENCE",
        "episode_count":pair_count,
        "pair_rows":pair_rows,
        "observed_pairwise_candidate_events":events,
        "pair_graph_component_count":component_count,
        "pairwise_outcome_accumulation_permitted":False,
        "bt_status":"WITHHELD",
        "bt_withhold_reasons":reasons,
        "pc1_predictive_validation":False,
        "pca_refit_performed":False,
        "timing_pca_reopened":False,
        "global_allocation_authority":False,
        "engineering_compliance_release_authority":False,
        "authority_transfer":False,
        "formal_credit_delta":0,
        "next_step":"acquire additional independently observed repair episodes and/or new low-PC1 outcomes; do not fit BT until eligibility gates pass",
    }
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
