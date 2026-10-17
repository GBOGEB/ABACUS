"""Unlock Yield: native-verified dependent gates / eligible gates.

No offline JSON input can claim authenticated closure by itself.
"""

from model_readiness import reverse_pressure


def evaluate(payload=None, *, native_verifier=None):
    unknown = dict(
        status="UNKNOWN",
        yield_pct=None,
        numerator=None,
        denominator=None,
        admission="HOLD",
        causal_effect=False,
    )
    if payload is None:
        return dict(unknown, reason="NO_COMPARABLE_EVIDENCE")
    if payload.get("schema") != "abacus.everred.unlock-yield.v1":
        raise ValueError("unsupported unlock schema")
    if (
        payload.get("authority_transfer") is not False
        or payload.get("security_waiver") is not False
    ):
        raise ValueError("authority boundary")
    import re

    sha_pattern = r"[0-9a-f]{40}"
    before, after = payload.get("before_sha"), payload.get("after_sha")
    if (
        not all(
            isinstance(s, str) and re.fullmatch(sha_pattern, s) for s in (before, after)
        )
        or before == after
    ):
        raise ValueError("source identity")
    graph = payload.get("blocking_dag")
    if not isinstance(graph, dict) or graph.get("source_sha") != after:
        raise ValueError("source-bound DAG missing")
    pressure = reverse_pressure(graph)
    if pressure["decision"] != "STRUCTURAL_DIAGNOSTIC_ONLY":
        raise ValueError("unconfirmed dependency DAG")
    impacts = {
        r["root_id"]: set(r["reachable_mandatory_gates"])
        for r in pressure["root_impacts"]
    }
    gates = impacts.get(payload.get("root_id"))
    items = payload.get("dependencies")
    if (
        not gates
        or not isinstance(items, list)
        or not items
        or payload.get("complete_denominator") is not True
    ):
        raise ValueError("eligible denominator unknown")
    if {x.get("gate_id") for x in items} != gates or len(items) != len(gates):
        raise ValueError("missing or duplicate eligible dependencies")
    repo = payload.get("repository")
    config = payload.get("config_digest")
    if not isinstance(repo, str) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo
    ):
        raise ValueError("repository missing")
    if not isinstance(config, str) or not re.fullmatch(r"[0-9a-f]{64}", config):
        raise ValueError("configuration missing")
    for item in items:
        for side, sha in (("before", before), ("after", after)):
            row = item.get(side)
            if not isinstance(row, dict) or row.get("source_sha") != sha:
                raise ValueError("source receipt mismatch")
            if (
                row.get("repository") != repo
                or row.get("gate_id") != item["gate_id"]
                or row.get("config_digest") != config
            ):
                raise ValueError("unbound receipt")
            run, job = row.get("run_id"), row.get("job_id")
            if (
                type(run) is not int
                or type(job) is not int
                or min(run, job) <= 0
                or row.get("evidence_url")
                != f"https://github.com/{repo}/actions/runs/{run}/job/{job}"
            ):
                raise ValueError("invalid native job")
            if row.get("result") not in ("BLOCKED", "READY"):
                raise ValueError("unqualified disposition")
    if native_verifier is None:
        return dict(unknown, reason="NATIVE_VERIFIER_MISSING", denominator=len(items))
    if not callable(native_verifier) or not all(
        native_verifier(x[y]) is True for x in items for y in ("before", "after")
    ):
        return dict(
            unknown, reason="NATIVE_AUTHENTICATION_FAILED", denominator=len(items)
        )
    opened = [
        x["gate_id"]
        for x in items
        if x["before"]["result"] == "BLOCKED" and x["after"]["result"] == "READY"
    ]
    return dict(
        status="VERIFIED_ASSOCIATION_NOT_CAUSAL_PROOF",
        yield_pct=round(100 * len(opened) / len(items), 2),
        numerator=len(opened),
        denominator=len(items),
        unblocked_gates=sorted(opened),
        admission="HOLD",
        causal_effect=False,
    )
