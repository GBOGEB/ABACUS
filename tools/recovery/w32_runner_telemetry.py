"""W32 native runner pulse: exact-head queue/latency, artifacts and proof yield.

A green job without verified JUnit+coverage provenance is not proof. Missing
time is UNKNOWN, never imputed as zero. No scheduler or merge side effects.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def timestamp(raw):
    if raw is None:
        return None
    need(isinstance(raw, str) and bool(raw), "invalid native timestamp")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid native timestamp") from error
    need(value.tzinfo is not None and value.utcoffset() is not None,
         "timezone not bound")
    return value


def percentile_nearest(values, fraction):
    if not values:
        return None
    need(0.0 < fraction <= 1.0, "invalid percentile")
    return round(sorted(values)[math.ceil(fraction * len(values)) - 1], 3)


def _proof(cell):
    if cell.get("status") != "completed" or cell.get("conclusion") != "success":
        return False
    evidence = cell.get("evidence")
    if not isinstance(evidence, dict):
        return False
    if evidence.get("junit_identity_verified") is not True:
        return False
    if evidence.get("artifact_sha256_verified") is not True:
        return False
    cases = evidence.get("executed_cases")
    eligible = evidence.get("eligible_opportunities")
    covered = evidence.get("covered_opportunities")
    return (type(cases) is int and cases > 0 and
            type(eligible) is int and eligible > 0 and
            type(covered) is int and 0 <= covered <= eligible)


def summarize(payload):
    need(isinstance(payload, dict), "invalid pulse")
    sha = payload.get("exact_head")
    need(isinstance(sha, str) and bool(_SHA.fullmatch(sha)),
         "invalid exact head")
    rows = payload.get("cells")
    need(isinstance(rows, list), "missing cell population")
    seen = set()
    queued = []
    elapsed = []
    terminal = 0
    successful = 0
    failures = 0
    pending = 0
    unknown_queue = 0
    unknown_runtime = 0
    verified = 0
    families = set()
    per_family = {}
    for cell in rows:
        need(isinstance(cell, dict) and cell.get("head_sha") == sha,
             "missing or foreign head")
        ids = (cell.get("run_id"), cell.get("attempt"), cell.get("job_id"))
        need(all(type(x) is int and x > 0 for x in ids), "invalid native identity")
        need(ids not in seen, "duplicate native attempt")
        seen.add(ids)
        family, platform, interpreter = (
            cell.get("family"), cell.get("os"), cell.get("python")
        )
        need(all(isinstance(x, str) and bool(x.strip())
                 for x in (family, platform, interpreter)),
             "missing disjoint runner identity")
        families.add(family)
        if family not in per_family:
            per_family[family] = {"jobs": 0, "successful": 0,
                                  "failed": 0, "proof_verified": 0}
        f = per_family[family]
        f["jobs"] += 1
        state, conclusion = cell.get("status"), cell.get("conclusion")
        need(state in {"queued", "in_progress", "completed"}, "invalid runner state")
        if state == "completed":
            need(conclusion in {"success", "failure", "cancelled", "skipped",
                                "timed_out"}, "missing terminal conclusion")
            terminal += 1
            if conclusion == "success":
                successful += 1
                f["successful"] += 1
            if conclusion in {"failure", "timed_out"}:
                failures += 1
                f["failed"] += 1
        else:
            need(conclusion is None, "premature terminal claim")
            pending += 1
        created = timestamp(cell.get("created_at"))
        started = timestamp(cell.get("started_at"))
        completed = timestamp(cell.get("completed_at"))
        if started is not None and created is not None:
            delta = (started - created).total_seconds()
            need(delta >= 0.0, "negative queue latency")
            queued.append(delta)
        else:
            unknown_queue += 1
        if completed is not None and started is not None:
            need(state == "completed", "nonterminal has end timestamp")
            delta = (completed - started).total_seconds()
            need(delta >= 0.0, "negative execution time")
            elapsed.append(delta)
        else:
            unknown_runtime += 1
        if _proof(cell):
            verified += 1
            f["proof_verified"] += 1
    return {
        "schema": "abacus.w32.runner-telemetry.v1",
        "exact_head": sha,
        "observed_jobs": len(seen),
        "disjoint_families": len(families),
        "terminal": terminal,
        "successful": successful,
        "failed": failures,
        "nonterminal": pending,
        # A caller's bool cannot independently authenticate ZIP/JUnit bytes.
        # Preserve the old tally only as a SOURCE_REPORTED allegation.
        "source_reported_positive_claims": verified,
        "source_reported_claim_yield": (
            round(verified / terminal, 6) if terminal else None
        ),
        "verified_successful_evidence": None,
        "native_proof_yield": None,
        "independent_evidence_status": "UNVERIFIED_BYTES",
        "byte_verifier": "tools/recovery/w34_native_artifact_verify.py",
        "queue_p95_seconds": percentile_nearest(queued, 0.95),
        "execution_p95_seconds": percentile_nearest(elapsed, 0.95),
        "queue_sample_n": len(queued),
        "runtime_sample_n": len(elapsed),
        "unknown_queue_n": unknown_queue,
        "unknown_runtime_n": unknown_runtime,
        "family_metrics": dict(sorted(per_family.items())),
        "credible_process_variance": None,
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
