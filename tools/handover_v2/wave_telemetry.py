#!/usr/bin/env python3
"""Read-only per-pulse and federation telemetry from verified V2 capsules.

No GitHub calls, side effects, authority transfer, or invented runtime receipts.
Existing V2 capsules, BD/LDAB joins and Mission Control remain authoritative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "handover.pulse.telemetry.v1"


def canonical(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def validate_ratio(metric: dict) -> dict:
    """Keep counts exact; refuse missing or fake numerators."""
    n, d = metric.get("numerator"), metric.get("denominator")
    require(type(n) is int and type(d) is int and d > 0 and 0 <= n <= d,
            "invalid ratio numerator/denominator")
    return {"covered": n, "eligible": d, "percent": round(100 * n / d, 4),
            "unit": metric.get("basis", {}).get("unit_definition")}


def comparable(before: dict, after: dict) -> tuple[bool, str]:
    if before.get("state") != "MEASURED" or after.get("state") != "MEASURED":
        return False, "both observations require current source-bound MEASURED evidence"
    b, a = before.get("basis", {}), after.get("basis", {})
    keys = ("scope_id", "unit_definition", "instrumentor", "instrumentor_version",
            "configuration_sha256", "selection")
    if any(b.get(k) != a.get(k) for k in keys):
        return False, "scope/instrumentor/configuration/test selection differs"
    if not b.get("configuration_sha256") or not b.get("instrumentor_version"):
        return False, "instrumentor version/configuration digest missing"
    if sorted(b.get("paths", [])) != sorted(a.get("paths", [])):
        return False, "source path scope differs"
    if before.get("source_sha") == after.get("source_sha"):
        return False, "different source SHAs required for independent waves"
    return True, "source scope and instrumentor identity match"


def _classify_metrics(state: dict) -> dict:
    result = {"current": {}, "historical": {}, "unknown": {}}
    head = state["subject"]["head_sha"]
    seen = set()
    for metric in state.get("metrics", []):
        status = metric.get("state")
        mid = metric.get("id")
        require(isinstance(mid, str) and bool(mid), "metric identifier required")
        require(mid not in seen, "duplicate metric identifier")
        seen.add(mid)
        if status == "UNKNOWN":
            require(metric.get("numerator") is None and metric.get("denominator") is None
                    and metric.get("value") is None,
                    "UNKNOWN cannot contain numeric values")
            result["unknown"][mid] = {"reason": metric.get("missing_reason")}
        elif status in ("MEASURED", "HISTORICAL"):
            if status == "MEASURED":
                require(metric.get("source_sha") == head, "current metric source mismatch")
            value = (validate_ratio(metric) if metric.get("measure_type") == "RATIO"
                     else {"value": metric.get("value"), "unit": metric.get("unit")})
            result["current" if status == "MEASURED" else "historical"][mid] = {
                **value, "scope_id": metric.get("basis", {}).get("scope_id"),
                "source_sha": metric.get("source_sha"),
                "config_sha256": metric.get("basis", {}).get("configuration_sha256"),
            }
        else:
            raise ValueError("unsupported metric state")
    return result


def summarize_state(state: dict, manifest_root: str) -> dict:
    subject = state.get("subject", {})
    repo, head = subject.get("repository"), subject.get("head_sha")
    require(isinstance(repo, str) and "/" in repo, "repository identity missing")
    require(isinstance(head, str) and bool(SHA.fullmatch(head)), "exact SHA required")
    require(isinstance(manifest_root, str) and bool(DIGEST.fullmatch(manifest_root)),
            "verified capsule manifest root required")
    gates = state.get("gates", [])
    blockers = state.get("blockers", [])
    unknowns = state.get("unknowns", [])
    current_gates = [g for g in gates if g.get("scope") in ("MAIN", "EXACT_HEAD")]
    require(len({g.get("id") for g in current_gates}) == len(current_gates),
            "duplicate current gate id")
    gate_statuses = {name: sorted(g["id"] for g in current_gates
                             if g.get("status") == name)
                     for name in ("PASS", "FAIL", "PENDING", "UNKNOWN")}
    required = [g for g in current_gates if g.get("required_for_admission")]
    required_ok = bool(required) and all(g.get("status") == "PASS" and
                                          g.get("source_sha") == head for g in required)
    root_cases = [b for b in blockers if b.get("classification") in ("ROOT", "GOVERNANCE", "ENVIRONMENT")]
    unique_roots = {b.get("root_cause_fingerprint") for b in root_cases}
    rooted_fingerprints = all(isinstance(f, str) and bool(DIGEST.fullmatch(f)) for f in unique_roots)
    metrics = _classify_metrics(state)
    uids = [u["id"] for u in unknowns]
    require(len(uids) == len(set(uids)), "duplicate UNKNOWN id")
    for row in unknowns:
        require(bool(row.get("owner") and row.get("acquisition") and row.get("reason")),
                "UNKNOWN requires owner, reason and acquisition")
    auth = state.get("authority", {})
    admission = "HOLD"
    if (required_ok and auth.get("merge_decision") == "ADMIT" and
            auth.get("independent_approval") == "ESTABLISHED" and
            auth.get("effective_branch_protection") == "VERIFIED"):
        admission = "CANDIDATE_ONLY_REQUIRES_LIVE_AUTHORITY"
    evidence_dimensions = {
        "exact_sha": True,
        "current_coverage_lines": any("line" in x.lower() for x in metrics["current"]),
        "current_coverage_branches": any("branch" in x.lower() for x in metrics["current"]),
        "current_governance": any(g["status"] == "PASS" and g.get("source_sha") == head
                                  and "governance" in g["id"].lower() for g in current_gates),
        "current_security": any(g["status"] == "PASS" and g.get("source_sha") == head
                                and "security" in g["id"].lower() for g in current_gates),
        "fingerprinted_root_census": rooted_fingerprints and bool(root_cases),
        "independent_approval": auth.get("independent_approval") == "ESTABLISHED",
        "federated_receipt": False,
    }
    receipt = {
        "schema": SCHEMA,
        "repo": repo,
        "source_sha": head,
        "captured_at_utc": state.get("snapshot", {}).get("captured_at_utc"),
        "capsule_manifest_root_sha256": manifest_root,
        "provenance": "LOCAL_CAPSULE_BYTES_VERIFIED_NOT_REMOTE_REAUTHENTICATED",
        "metrics": metrics,
        "gates": {"total_current": len(current_gates), "required": len(required),
                  "required_all_pass": required_ok, "by_status": gate_statuses},
        "unknowns": {"count": len(uids), "ids": sorted(uids)},
        "roots": {"root_classified_rows": len(root_cases),
                  "fingerprinted_count": len(unique_roots) if rooted_fingerprints else None,
                  "closed_count": None, "root_burndown": "UNVERIFIED"},
        "depth": {"verified_dimensions": sum(evidence_dimensions.values()),
                  "eligible_dimensions": len(evidence_dimensions),
                  "dimensions": evidence_dimensions},
        "fanout": {"authenticated_worker_launches": None,
                   "worker_hours": None, "rollout_disposition": "UNVERIFIED"},
        "pca": {"status": "WITHHELD_REQUIRES_COMPARABLE_INDEPENDENT_SERIES"},
        "bt": {"status": "WITHHELD_REQUIRES_NATIVE_PAIRWISE_OBSERVATIONS"},
        "rex": {"verified_root_closure_returns": None},
        "lldb_ldab": {"authenticated_sessions": None},
        "three_p_star": {"admission_promotion": "NOT_ESTABLISHED"},
        "admission": admission,
        "authority_transfer": False,
        "security_waiver": False,
    }
    receipt["receipt_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    return receipt


def compare_states(before: dict, after: dict, before_root: str,
                   after_root: str) -> dict:
    require(before["subject"]["repository"] == after["subject"]["repository"],
            "cross-repository differences are federation, not per-repo improvement")
    bp = summarize_state(before, before_root)
    ap = summarize_state(after, after_root)
    before_unknown = set(bp["unknowns"]["ids"])
    after_unknown = set(ap["unknowns"]["ids"])
    deltas = []
    bmetrics = {x["id"]: x for x in before["metrics"]}
    for item in after["metrics"]:
        prev = bmetrics.get(item["id"])
        if prev is None or item.get("measure_type") != "RATIO":
            continue
        ok, reason = comparable(prev, item)
        row = {"metric_id": item["id"], "comparable": ok, "reason": reason,
               "covered_delta": None, "eligible_delta": None,
               "percentage_point_delta": None}
        if ok:
            b = validate_ratio(prev)
            a = validate_ratio(item)
            row.update({"covered_delta": a["covered"] - b["covered"],
                        "eligible_delta": a["eligible"] - b["eligible"],
                        "percentage_point_delta": round(a["percent"] - b["percent"], 4)})
        deltas.append(row)
    return {"schema": "handover.wave.delta.v1", "repository": ap["repo"],
            "before_sha": bp["source_sha"], "after_sha": ap["source_sha"],
            "before_manifest_root": before_root, "after_manifest_root": after_root,
            "unknowns_before": len(before_unknown), "unknowns_after": len(after_unknown),
            "unknown_ids_no_longer_open": sorted(before_unknown - after_unknown),
            "unknown_ids_new": sorted(after_unknown - before_unknown),
            "unknown_net_reduction": len(before_unknown) - len(after_unknown),
            "note": "UNKNOWN disappearance is not root closure; verify acquired evidence separately",
            "metric_deltas": deltas, "root_burndown": None,
            "main_coverage_uplift": None, "authority_transfer": False}


def federate(pulses: list[dict], target_repos: list[str]) -> dict:
    require(len(target_repos) == len(set(target_repos)) and bool(target_repos),
            "federation must declare a nonempty disjoint target set")
    require(len({p.get("repo") for p in pulses}) == len(pulses),
            "only one current pulse per repository is allowed")
    for p in pulses:
        require(p.get("schema") == SCHEMA and p.get("repo") in target_repos,
                "unknown or unscoped federation pulse")
        require(p.get("authority_transfer") is False and
                p.get("security_waiver") is False,
                "federation may not transfer authority or waive security")
    included = sorted(p["repo"] for p in pulses)
    unobserved = sorted(set(target_repos) - set(included))
    receipts = {p["repo"]: {"source_sha": p["source_sha"],
                           "capsule_manifest_root_sha256": p["capsule_manifest_root_sha256"],
                           "depth": p["depth"], "unknowns": p["unknowns"],
                           "admission": p["admission"]} for p in pulses}
    output = {
        "schema": "handover.federation.rollup.v1",
        "target_repositories": sorted(target_repos),
        "verified_local_capsules": len(included),
        "target_count": len(target_repos),
        "breadth_percent": round(100 * len(included) / len(target_repos), 4),
        "unobserved_repositories": unobserved,
        "per_repo": receipts,
        "comparable_federation_coverage_delta": None,
        "worker_fanout_executed": None,
        "verified_cross_repo_rex_closure": None,
        "pca_promotion": "WITHHELD",
        "bt_promotion": "WITHHELD",
        "three_p_star_promotion": "WITHHELD",
        "child_engineering_authority_transfer": False,
        "security_waiver": False,
        "rollout_status": "OBSERVATION_ONLY",
    }
    output["receipt_sha256"] = hashlib.sha256(canonical(output)).hexdigest()
    return output


def load_capsule(path: Path) -> tuple[dict, dict]:
    from build_handover import capsule_verify
    return capsule_verify(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    one = subs.add_parser("pulse")
    one.add_argument("--capsule", type=Path, required=True)
    one.add_argument("--out", type=Path, required=True)
    two = subs.add_parser("compare")
    two.add_argument("--before", type=Path, required=True)
    two.add_argument("--after", type=Path, required=True)
    two.add_argument("--out", type=Path, required=True)
    many = subs.add_parser("federate")
    many.add_argument("--capsules", type=Path, nargs="*", default=[])
    many.add_argument("--repositories", nargs="+", required=True)
    many.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "pulse":
        state, manifest = load_capsule(args.capsule)
        result = summarize_state(state, manifest["manifest_root_sha256"])
    elif args.action == "compare":
        a, am = load_capsule(args.before)
        b, bm = load_capsule(args.after)
        result = compare_states(a, b, am["manifest_root_sha256"],
                                bm["manifest_root_sha256"])
    else:
        receipts = []
        for item in args.capsules:
            s, m = load_capsule(item)
            receipts.append(summarize_state(s, m["manifest_root_sha256"]))
        result = federate(receipts, args.repositories)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical(result))
    print(json.dumps({"schema": result["schema"], "out": str(args.out),
                      "status": "LOCAL_CAPSULE_VERIFIED_NOT_REMOTE_ADMITTED"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
