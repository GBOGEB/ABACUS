"""Origin-independent EVERRED revision/cycle deltas; descriptive, not admission."""

from __future__ import annotations

import math
import re
from collections import defaultdict

SHA = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "abacus.everred.temporal-vector.v1"
GATES = ("required_checks", "security", "independent_review", "effective_protection")


def _int(value):
    return type(value) is int and value >= 0


def _metric(metric, sha):
    if not isinstance(metric, dict) or metric.get("state") not in (
        "MEASURED",
        "UNKNOWN",
    ):
        raise ValueError("metric state must be MEASURED or UNKNOWN")
    if metric["state"] == "UNKNOWN":
        if metric.get("value") is not None:
            raise ValueError("UNKNOWN metric cannot carry a numeric value")
        return
    value = metric.get("value")
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("measured value must be finite numeric, not bool")
    if not isinstance(metric.get("unit"), str) or not metric["unit"]:
        raise ValueError("measured metric requires unit")
    basis = metric.get("basis")
    if not isinstance(basis, dict) or not basis:
        raise ValueError("measured metric requires nonempty comparability basis")
    if any(v is None or v == "UNKNOWN" for v in basis.values()):
        raise ValueError("measured comparability basis cannot be UNKNOWN")
    source = metric.get("source")
    if (
        not isinstance(source, dict)
        or source.get("sha") != sha
        or not _int(source.get("run_id"))
        or source["run_id"] == 0
        or not _int(source.get("job_id"))
        or source["job_id"] == 0
    ):
        raise ValueError("measured metric requires exact-source SHA, run and job")


def _gate(state):
    g = state.get("admission")
    if not isinstance(g, dict):
        raise ValueError("explicit four-way admission observations required")
    if any(g.get(k) not in ("PASS", "RED", "UNKNOWN") for k in GATES):
        raise ValueError("invalid/missing non-compensatory admission gate")
    return (
        "ELIGIBLE_FOR_AUTHORITY_REVIEW"
        if all(g[k] == "PASS" for k in GATES)
        else "HOLD"
    )


def _delta(left, right):
    if left is None or right is None:
        return {"status": "UNKNOWN", "reason": "MISSING_COORDINATE", "delta": None}
    if left["state"] != "MEASURED" or right["state"] != "MEASURED":
        return {"status": "UNKNOWN", "reason": "MISSING_OBSERVATION", "delta": None}
    if left["unit"] != right["unit"] or left["basis"] != right["basis"]:
        return {
            "status": "UNKNOWN",
            "reason": "INCOMPARABLE_UNIT_OR_BASIS",
            "delta": None,
        }
    return {
        "status": "COMPARABLE",
        "unit": left["unit"],
        "delta": right["value"] - left["value"],
    }


def analyze(payload):
    """Return per-repository D*x with UNKNOWN masks and no global ordinal fiction.

    Ordinals and ancestry come from the caller's verified revision ledger; this
    pure kernel validates order but cannot establish Git ancestry by itself.
    """
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("incorrect temporal contract schema")
    origin = payload.get("origin_ordinal")
    if type(origin) is not int:
        raise ValueError("origin must be an integer (arbitrary N index)")
    states = payload.get("states")
    if not isinstance(states, list):
        raise ValueError("states array required")
    chains = defaultdict(list)
    seen = set()
    for state in states:
        if not isinstance(state, dict):
            raise ValueError("invalid state")
        repo, sha = state.get("repository"), state.get("sha")
        j, c = state.get("revision_ordinal"), state.get("recovery_cycle")
        if (
            not isinstance(repo, str)
            or "/" not in repo
            or not isinstance(sha, str)
            or not SHA.fullmatch(sha)
            or not _int(j)
            or not _int(c)
        ):
            raise ValueError("invalid repository, SHA, revision or recovery cycle")
        if (repo, sha) in seen or (repo, j) in seen:
            raise ValueError("duplicate revision identity")
        seen.update(((repo, sha), (repo, j)))
        metrics = state.get("coordinates")
        if not isinstance(metrics, dict):
            raise ValueError("coordinates mapping required")
        for key, metric in metrics.items():
            if not isinstance(key, str) or not key:
                raise ValueError("coordinate name must be nonempty")
            _metric(metric, sha)
        admission = _gate(state)
        chains[repo].append((j, c, sha, metrics, admission))
    result = {}
    for repo, seq in sorted(chains.items()):
        seq.sort(key=lambda x: x[0])
        if any(b[1] < a[1] for a, b in zip(seq, seq[1:])):
            raise ValueError("recovery cycle cannot go backwards")
        deltas, matrix = [], []
        for i, (a, b) in enumerate(zip(seq, seq[1:])):
            # D is the sparse first-difference matrix, separate from clock spacing.
            matrix.append(
                [{"column": i, "coefficient": -1}, {"column": i + 1, "coefficient": 1}]
            )
            keys = sorted(set(a[3]) | set(b[3]))
            deltas.append(
                {
                    "from_sha": a[2],
                    "to_sha": b[2],
                    "revision_span": b[0] - a[0],
                    "cycle_transition": [a[1], b[1]],
                    "coordinates": {k: _delta(a[3].get(k), b[3].get(k)) for k in keys},
                    "admission_transition": [a[4], b[4]],
                }
            )
        result[repo] = {
            "indices": [
                {
                    "sha": s[2],
                    "revision_ordinal": s[0],
                    "k": s[0] - origin,
                    "recovery_cycle": s[1],
                    "admission": s[4],
                }
                for s in seq
            ],
            "difference_matrix_sparse": matrix,
            "deltas": deltas,
        }
    return {
        "schema": SCHEMA + ".result",
        "origin_ordinal": origin,
        "repositories": result,
        "authority_transfer": False,
        "merge_authorized": False,
        "clock_contract": "Per-repository ordinals, separate logical recovery cycles; ancestry requires upstream verification",
    }
