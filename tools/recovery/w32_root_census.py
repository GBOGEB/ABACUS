"""W32 immutable exact-head first-red/root census.

A failed job is a manifestation, not automatically a distinct causal root.
Missing first-red evidence is UNKNOWN, never a successful or closed root.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")
_STATES = frozenset({"queued", "in_progress", "completed"})
_DONE = frozenset({"success", "failure", "cancelled", "skipped", "timed_out"})


def _need(predicate: bool, message: str) -> None:
    if not predicate:
        raise ValueError(message)


def summarize(payload: dict) -> dict:
    _need(isinstance(payload, dict), "invalid observation envelope")
    head = payload.get("exact_head")
    _need(isinstance(head, str) and bool(_SHA.fullmatch(head)), "invalid exact head")
    jobs = payload.get("jobs")
    _need(isinstance(jobs, list), "jobs census unavailable")
    seen: set[tuple[int, int, int]] = set()
    roots: dict[str, set[tuple[int, int, int]]] = defaultdict(set)
    groups: dict[str, set[str]] = defaultdict(set)
    counts: Counter[str] = Counter()
    failed_unknown = 0
    failed_observed = 0
    for job in jobs:
        _need(isinstance(job, dict), "invalid job record")
        _need(job.get("head_sha") == head, "cross-head job not admitted")
        run, attempt, jobid = (job.get(k) for k in ("run_id", "attempt", "job_id"))
        _need(all(type(v) is int and v > 0 for v in (run, attempt, jobid)),
              "invalid run / attempt / job ID")
        identity = (run, attempt, jobid)
        _need(identity not in seen, "duplicate run / attempt / job identity")
        seen.add(identity)
        state = job.get("status")
        conclusion = job.get("conclusion")
        _need(state in _STATES, "unknown job state")
        if state == "completed":
            _need(conclusion in _DONE, "terminal job missing conclusion")
            counts[conclusion] += 1
        else:
            _need(conclusion is None, "nonterminal conclusion falsely asserted")
            counts["nonterminal"] += 1
        root = job.get("root_id")
        family = job.get("source_family")
        _need(isinstance(family, str) and bool(family.strip()), "missing source family")
        if state == "completed" and conclusion in {"failure", "timed_out"}:
            failed_observed += 1
            if root is None:
                failed_unknown += 1
            else:
                _need(isinstance(root, str) and bool(root.strip()), "malformed root")
                roots[root].add(identity)
                groups[root].add(family)
        else:
            _need(root is None, "root claimed on non-failed observation")
    previous = payload.get("previous_root_ids", [])
    _need(isinstance(previous, list) and
          all(isinstance(v, str) and bool(v) for v in previous),
          "invalid prior root IDs")
    _need(len(previous) == len(set(previous)), "duplicate prior root IDs")
    missing_old = sorted(set(previous) - set(roots))
    report_roots = {
        key: {"manifestations": len(ids), "source_families": sorted(groups[key])}
        for key, ids in sorted(roots.items())
    }
    return {
        "schema": "abacus.w32.root-census.v1",
        "exact_head": head,
        "job_identities": len(seen),
        "terminal": len(seen) - counts["nonterminal"],
        "nonterminal": counts["nonterminal"],
        "successful_jobs": counts["success"],
        "failed_jobs": failed_observed,
        "cancelled_jobs": counts["cancelled"],
        "skipped_jobs": counts["skipped"],
        "unknown_first_red_count": failed_unknown,
        "root_count": len(roots),
        "root_manifestations": sum(len(v) for v in roots.values()),
        "root_amplification": (
            round(sum(len(v) for v in roots.values()) / len(roots), 4)
            if roots else None
        ),
        "roots": report_roots,
        "prior_roots_not_observed_here": missing_old,
        "formal_roots_closed": None,
        "matched_coverage_delta": None,
        "security_waiver": False,
        "merge_admission": "HOLD",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args(argv)
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
