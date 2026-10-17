"""CODE PURPLE operating DAG, non-authoritative BD decision card projection."""
from model_readiness import bt_readiness, pca_readiness, reverse_pressure
from unlock_yield import evaluate as unlock_yield

STAGES = ("Mission", "Wave", "Pulse", "Receipt", "Reallocate", "Recurse")
SCHEMA = "abacus.everred.mission-guidance.v1"


def project(bd, *, pca_panel=None, bt_pairs=None, blocking_dag=None,
            unlock_inputs=None, native_verifier=None):
    if not isinstance(bd, dict) or not isinstance(bd.get("families"), list):
        raise ValueError("missing canonical BD queue")
    pca = pca_readiness(pca_panel) if pca_panel is not None else None
    bt = bt_readiness(bt_pairs) if bt_pairs is not None else None
    reverse = reverse_pressure(blocking_dag) if blocking_dag is not None else None
    impact = {}
    if reverse and reverse["decision"] == "STRUCTURAL_DIAGNOSTIC_ONLY":
        impact = {x["root_id"]: x["reachable_mandatory_gates"]
                  for x in reverse.get("root_impacts", [])}
    root_cards = {}
    for f in bd["families"]:
        root_id, priority = f["id"], f["severity"]
        if root_id in root_cards or priority not in ("P0", "P1", "P2", "P3"):
            raise ValueError("duplicate root or unsupported priority")
        candidate = impact.get(root_id)
        proof = unlock_yield((unlock_inputs or {}).get(root_id),
                             native_verifier=native_verifier)
        # P0 hard safety/governance gating is never displaced by a ranking.
        hard_gate = priority == "P0" or f.get("hard_gate") is True
        root_cards[root_id] = {
            "p": priority,
            "priority_policy": "P0_HARD_GATE_FIRST" if hard_gate else "PRIORITY_NOT_BT",
            "pca_readiness": pca["decision"] if pca else "UNQUALIFIED",
            "pca_component": None,
            "bt_readiness": bt["decision"] if bt else "WITHHELD",
            "bt_rank": None,
            "reverse_pressure": len(candidate) if candidate is not None else None,
            "unlock_yield_pct": proof["yield_pct"],
            "unlock_numerator": proof["numerator"],
            "unlock_denominator": proof["denominator"],
            "unlock_status": proof["status"],
            "why_this_ranks": f["justification"],
            "what_it_unblocks": ", ".join(candidate) if candidate is not None
                                else "UNKNOWN: no confirmed causal edges",
            "next_action": f["remediation"],
            "dov": f["dov"],
            "admission": "HOLD",
        }
    return {
        "schema": SCHEMA,
        "stages": list(STAGES),
        "cards": root_cards,
        "method": "Mission -> Wave -> Pulse -> Receipt -> Reallocate -> Recurse",
        "merge_authorized": False,
        "authority_transfer": False,
        "security_waiver": False,
        "source": "EVERRED canonical root and native evidence only",
    }
