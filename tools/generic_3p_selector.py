#!/usr/bin/env python3
"""Adaptive selector for the TRIAGE generic 3P method family."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STATES = ["S0_UNKNOWN", "S1_DISCOVERED", "S2_CLASSIFIED", "S3_PROOF_CANDIDATE", "S4_REINTRODUCED", "S5_REENTRY_PENDING", "S6_TERMINAL"]


def _clip(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def select_method(item: dict[str, object]) -> dict[str, object]:
    state = str(item.get("state", "S0_UNKNOWN"))
    if state not in STATES:
        state = "S0_UNKNOWN"
    weights = item.get("semantic_weights", {})
    if not isinstance(weights, dict):
        weights = {}
    w = {key: _clip(weights.get(key, 0.0)) for key in ["E", "C", "V", "L", "I", "A"]}
    reentry = bool(weights.get("R", item.get("cross_repo_reentry", False)))
    aht = _clip(item.get("aht_pressure", 0.0))
    low_yield = _clip(item.get("low_yield_pressure", 0.0))
    rework = _clip(item.get("rework_pressure", 0.0))
    dov_gap = _clip(item.get("dov_gap", 1.0))

    # Process signals can raise semantic weights without changing item identity.
    w["L"] = max(w["L"], min(1.0, aht * low_yield))
    w["V"] = max(w["V"], rework)

    chain: list[str] = []
    reasons: list[str] = []

    if state == "S6_TERMINAL" and dov_gap <= 0.05:
        return {"state": state, "weights": w, "reentry": reentry, "chain": [], "decision": "STOP", "reasons": ["terminal_and_DoV_gap_closed"]}

    if w["E"] >= 0.55:
        chain.append("3PE"); reasons.append("evidence_space_uncertainty")
    if w["L"] >= 0.55:
        chain.append("3PL"); reasons.append("search_or_evidence_path_inefficiency")
    if w["C"] >= 0.55 or w["A"] >= 0.65:
        chain.append("3PC"); reasons.append("classification_authority_or_consumer_ambiguity")
    if w["V"] >= 0.55 or w["I"] >= 0.55 or rework >= 0.35:
        chain.append("3PV"); reasons.append("proof_information_loss_or_rework_pressure")

    # Progression biases prevent needless exploration late in the lifecycle.
    if state in {"S3_PROOF_CANDIDATE", "S4_REINTRODUCED"} and "3PV" not in chain:
        chain.append("3PV"); reasons.append("progression_requires_same_boundary_proof")
    if state == "S5_REENTRY_PENDING":
        reentry = True
    if reentry:
        chain.append("3PR"); reasons.append("cross_repo_or_parent_reentry_required")

    if not chain:
        if state in {"S0_UNKNOWN", "S1_DISCOVERED"}:
            chain = ["3PE"] ; reasons.append("default_early_stage_exploration")
        elif state == "S2_CLASSIFIED":
            chain = ["3PV"] ; reasons.append("classified_item_needs_proof_before_terminal_disposition")
        else:
            chain = ["3PC"] ; reasons.append("default_control_discrimination")

    # Stable unique chain preserving order.
    seen: set[str] = set()
    chain = [x for x in chain if not (x in seen or seen.add(x))]
    return {
        "state": state,
        "weights": w,
        "reentry": reentry,
        "chain": chain,
        "decision": "EXECUTE",
        "reasons": reasons,
        "signals": {"aht_pressure": aht, "low_yield_pressure": low_yield, "rework_pressure": rework, "dov_gap": dov_gap},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    items = payload.get("items", []) if isinstance(payload, dict) else []
    decisions = []
    for item in items:
        if isinstance(item, dict):
            decisions.append({"item_id": item.get("item_id"), **select_method(item)})
    result = {"schema_version": "TRIAGE-3P-SELECTOR-1.0.0", "item_count": len(decisions), "decisions": decisions}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
