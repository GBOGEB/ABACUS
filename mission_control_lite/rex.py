"""Read-only first-red / root-candidate / REX registry and MIP wave metrics.

This index does not confirm causal roots, waive security, or authorize merge.
"""
from __future__ import annotations

import hashlib
import json


def fingerprint(repository, producer, code, source_path, signature):
    """Stable manifestation fingerprint; do not include run IDs or timestamps."""
    fields = [repository, producer, code, source_path, signature]
    if not all(isinstance(x, str) and x for x in fields):
        raise ValueError("missing fingerprint field")
    return hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()


def build_index(events, roots, rex):
    """Validate and join distinct events, root hypotheses and REX references."""
    if not all(isinstance(x, list) for x in (events, roots, rex)):
        raise ValueError("expected arrays")
    by_root = {}
    by_rex = {}
    for row in roots:
        rid = row["root_id"]
        if rid in by_root:
            raise ValueError("duplicate root")
        by_root[rid] = row
    for row in rex:
        rid = row["rex_id"]
        if rid in by_rex:
            raise ValueError("duplicate REX")
        by_rex[rid] = row
    seen = set()
    output = []
    for event in events:
        eid = event["event_id"]
        if eid in seen:
            raise ValueError("duplicate event")
        seen.add(eid)
        for field in ("repository", "source_sha", "run_id", "job_id",
                      "topic_id", "fingerprint", "manifestation"):
            if not event.get(field):
                raise ValueError("event provenance missing: " + field)
        rid = event.get("root_candidate_id")
        if rid is not None and rid not in by_root:
            raise ValueError("unknown root reference")
        root = by_root.get(rid)
        rex_id = root.get("rex_id") if root else None
        if rex_id is not None and rex_id not in by_rex:
            raise ValueError("unknown REX reference")
        output.append({"event": event, "root_candidate": root,
                       "rex": by_rex.get(rex_id),
                       "root_confirmed": False, "merge_admission": "HOLD"})
    return {"schema": "mcl.first_red_rex.index.v1", "events": output,
            "event_count": len(output), "root_candidates": len(by_root),
            "rex_entries": len(by_rex), "verified_root_closures": 0,
            "authority_transfer": False, "merge_admission": "HOLD"}


def wave_delta(previous, current):
    """Compare comparable fingerprint sets; missing evidence stays unknown."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise ValueError("missing wave")
    keys = ("repository", "scanner_config_sha256", "coverage_scope")
    if any(not previous.get(k) or previous[k] != current.get(k) for k in keys):
        raise ValueError("incomparable wave scope")
    a, b = previous.get("fingerprints"), current.get("fingerprints")
    if not isinstance(a, list) or not isinstance(b, list):
        raise ValueError("fingerprint census missing")
    if len(a) != len(set(a)) or len(b) != len(set(b)):
        raise ValueError("duplicate fingerprints")
    coverage = {}
    for key in ("covered_lines", "total_lines", "covered_branches", "total_branches"):
        p, c = previous.get(key), current.get(key)
        if p is None or c is None:
            coverage[key] = None
        elif not isinstance(p, int) or not isinstance(c, int) or min(p, c) < 0:
            raise ValueError("invalid coverage count")
        else:
            coverage[key] = {"before": p, "after": c}
    for prefix in ("", "branch_"):
        n, d = prefix + "covered_lines", prefix + "total_lines"
        if prefix:
            n, d = "covered_branches", "total_branches"
        if coverage[n] and coverage[d]:
            if any(coverage[n][s] > coverage[d][s] or coverage[d][s] == 0
                   for s in ("before", "after")):
                raise ValueError("invalid coverage denominator")
    before, after = set(a), set(b)
    def rate(n, d, side):
        if coverage[n] is None or coverage[d] is None:
            return None
        return coverage[n][side] / coverage[d][side]
    l0, l1 = rate("covered_lines", "total_lines", "before"), rate("covered_lines", "total_lines", "after")
    b0, b1 = rate("covered_branches", "total_branches", "before"), rate("covered_branches", "total_branches", "after")
    return {"schema": "mcl.wave.delta.v1",
            "opened": sorted(after - before), "resolved_candidates": sorted(before - after),
            "persistent": sorted(before & after),
            "net_open_change": len(after) - len(before),
            "line_coverage_before": l0, "line_coverage_after": l1,
            "line_coverage_delta_pp": None if l0 is None or l1 is None else 100 * (l1 - l0),
            "branch_coverage_delta_pp": None if b0 is None or b1 is None else 100 * (b1 - b0),
            "root_closure_credit": 0, "merge_admission": "HOLD"}
