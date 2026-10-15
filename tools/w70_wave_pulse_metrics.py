#!/usr/bin/env python3
"""W70 pulse metrics: exact-source census, observable coverage, no inferred credit.

Artifact input is producer data, not independent GitHub run authentication.
Comparability is explicit; missing baseline / population stays UNKNOWN (null).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "abacus.w70.pulse.metrics/v1"
LANES = (
    "A_registry_gap", "B_reference_gap", "C_consumer_penetration",
    "D_graph_orphan_drop", "E_lineage_evidence",
)
SHA = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SCOPE_FILE = "tools/w70_wave_pulse_metrics.py"


def insist(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, *, positive=False):
    return type(value) is int and (value > 0 if positive else value >= 0)


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def pct(covered, eligible):
    return round(100.0 * covered / eligible, 2) if eligible else None


def source_metrics(coverage, scope_digest):
    """Count actual instrumented lines/branches; reject invented/mixed scope."""
    insist(isinstance(coverage, dict), "coverage JSON missing")
    files = coverage.get("files")
    insist(isinstance(files, dict) and len(files) == 1,
           "coverage must include exactly one owned source file")
    name, details = next(iter(files.items()))
    insist(name.replace("\\", "/").endswith(SCOPE_FILE),
           "coverage source scope mismatch")
    totals = details.get("summary", {})
    lines = totals.get("num_statements")
    covered = totals.get("covered_lines")
    branches = totals.get("num_branches")
    covered_branches = totals.get("covered_branches")
    insist(all(integer(x) for x in (lines, covered, branches, covered_branches))
           and lines > 0 and branches > 0
           and covered <= lines and covered_branches <= branches,
           "invalid line/branch coverage numerators or denominators")
    insist(isinstance(scope_digest, str) and DIGEST.fullmatch(scope_digest),
           "invalid instrumented-source digest")
    version = coverage.get("meta", {}).get("version")
    insist(isinstance(version, str) and version.strip(), "coverage tool version missing")
    return {
        "source_file": SCOPE_FILE, "source_sha256": scope_digest,
        "tool": "coverage.py", "tool_version": version,
        "test_selection": "test_w70_wave_pulse_metrics.py",
        "line": {"covered": covered, "eligible": lines, "pct": pct(covered, lines)},
        "branch": {"covered": covered_branches, "eligible": branches,
                   "pct": pct(covered_branches, branches)},
    }


def verify_lanes(feature, lane_records, sha):
    insist(isinstance(feature, dict) and feature.get("source_sha") == sha,
           "feature row exact SHA mismatch")
    insist(isinstance(lane_records, dict) and set(lane_records) == set(LANES),
           "all five lane receipts required")
    total, open_ = 0, 0
    lanes = {}
    for lane in LANES:
        data = lane_records[lane]
        counts = data.get("totals", {}) if isinstance(data, dict) else {}
        population, backlog, closed = (
            counts.get("total_population"), counts.get("backlog_open"),
            counts.get("backlog_closed"),
        )
        insist(data.get("source_sha") == sha and data.get("lane") == lane,
               "lane SHA or identity mismatch")
        insist(all(integer(v) for v in (population, backlog, closed))
               and backlog + closed == population, "invalid debt lane census")
        lanes[lane] = {"population": population, "open": backlog, "closed": closed}
        total += population
        open_ += backlog
    insist(feature.get("total_population") == total
           and feature.get("total_open_backlog") == open_,
           "A-E feature aggregate mismatches lane receipts")
    return lanes, {"measured_lane_population_sum": total,
                   "open_manifestations_sum": open_,
                   "closed_manifestations_sum": total - open_,
                   "unique_confirmed_roots": None}


def compare(previous, current):
    """Comparable coverage only with identical source scope and measurement tool."""
    result = {"baseline_receipt_sha256": None, "comparable": False,
              "reason": "NO_BASELINE", "line_delta_pp": None,
              "branch_delta_pp": None, "debt_delta": None}
    if previous is None:
        return result
    insist(isinstance(previous, dict) and previous.get("schema") == SCHEMA,
           "invalid baseline receipt schema")
    checksum = previous.get("receipt_sha256")
    insist(isinstance(checksum, str)
           and checksum == sha256(stable({k: v for k, v in previous.items()
                                           if k != "receipt_sha256"}).encode()),
           "baseline digest mismatch")
    result["baseline_receipt_sha256"] = checksum
    if previous.get("repository") != current["repository"]:
        result["reason"] = "DIFFERENT_REPOSITORY"
        return result
    first, second = previous.get("coverage", {}), current["coverage"]
    keys = ("source_file", "source_sha256", "tool", "tool_version", "test_selection")
    if not isinstance(first, dict) or any(first.get(k) != second.get(k) for k in keys):
        result["reason"] = "INSTRUMENTED_SCOPE_OR_TOOL_CHANGED"
        return result
    if any(first.get(unit, {}).get("eligible") != second[unit]["eligible"]
           for unit in ("line", "branch")):
        result["reason"] = "ELIGIBLE_DENOMINATOR_CHANGED"
        return result
    result["comparable"] = True
    result["reason"] = "SAME_SOURCE_SCOPE_AND_TOOL"
    for unit in ("line", "branch"):
        result[unit + "_delta_pp"] = round(
            second[unit]["pct"] - first[unit]["pct"], 2)
    # Population membership is not evidenced by a mere equal count.
    result["debt_delta"] = None
    return result


def build(feature, lane_records, coverage, *, repo, sha, run_id,
          attempt, scope_digest, previous=None):
    insist(isinstance(repo, str) and REPO.fullmatch(repo), "invalid repository")
    insist(isinstance(sha, str) and SHA.fullmatch(sha), "invalid commit SHA")
    insist(integer(run_id, positive=True) and integer(attempt, positive=True),
           "invalid workflow run/attempt")
    lanes, debt = verify_lanes(feature, lane_records, sha)
    cov = source_metrics(coverage, scope_digest)
    body = {
        "schema": SCHEMA, "repository": repo, "source_sha": sha,
        "run_id": run_id, "run_attempt": attempt, "wave": "W70",
        "pulse_id": f"W70:{run_id}:{attempt}",
        "measurement_contract": "W70-AE-and-focused-coverage/v1",
        "lanes": lanes, "debt": debt, "coverage": cov,
        "coverage_delta": None, "native_run_authenticated": None,
        "integrated_main_verified": None,
        "formal_credit_delta": 0, "authority_transfer": False,
        "security_waiver": False, "admission": "HOLD",
    }
    body["coverage_delta"] = compare(previous, body)
    return {**body, "receipt_sha256": sha256(stable(body).encode())}


def summary(record):
    cov = record["coverage"]
    delta = record["coverage_delta"]
    return ("## W70 exact-SHA measured pulse\n\n"
            f"- Head: `{record['source_sha']}` · Run: {record['run_id']} "
            f"attempt {record['run_attempt']}\n"
            f"- A–E measured population sum: {record['debt']['measured_lane_population_sum']} "
            f"(**not distinct root count**)\n"
            f"- Open manifestations sum: {record['debt']['open_manifestations_sum']}\n"
            f"- Owned-module line coverage: {cov['line']['covered']}/"
            f"{cov['line']['eligible']} = **{cov['line']['pct']}%**\n"
            f"- Owned-module branch coverage: {cov['branch']['covered']}/"
            f"{cov['branch']['eligible']} = **{cov['branch']['pct']}%**\n"
            f"- Scope-matched baseline: {delta['reason']} · "
            f"line gain: {delta['line_delta_pp']} pp; "
            f"branch gain: {delta['branch_delta_pp']} pp\n"
            "- Native run authentication / merge admission / QPS credit: "
            "**UNKNOWN / HOLD / ZERO**\n")


def checked_out_head(workspace=None):
    """Read an exact detached Git checkout without executing a subprocess.

    The native W70 workflow checks out a commit SHA, not a symbolic branch.
    Git worktree pointers are supported; unresolved or symbolic heads fail closed.
    """
    root = workspace if workspace is not None else Path.cwd()
    dotgit = root / ".git"
    if dotgit.is_file():
        pointer = dotgit.read_text(encoding="utf-8").strip()
        insist(pointer.startswith("gitdir: "), "invalid Git worktree pointer")
        location = Path(pointer[len("gitdir: "):])
        gitdir = location if location.is_absolute() else root / location
    else:
        gitdir = dotgit
    try:
        actual = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError("checked-out Git HEAD unavailable") from exc
    insist(bool(SHA.fullmatch(actual)), "detached exact-SHA checkout required")
    return actual


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lane-dir", required=True, type=Path)
    p.add_argument("--coverage", required=True, type=Path)
    p.add_argument("--source-path", type=Path, default=Path(__file__))
    p.add_argument("--sha", required=True)
    p.add_argument("--repo", default="GBOGEB/ABACUS")
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--baseline", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--summary", type=Path)
    args = p.parse_args()
    actual = checked_out_head()
    insist(actual == args.sha, "checked-out HEAD differs from pulse SHA")
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    rows = {lane: read(args.lane_dir / (lane + ".json")) for lane in LANES}
    receipt = build(
        read(args.lane_dir / "FEATURE_ROW.json"), rows, read(args.coverage),
        repo=args.repo, sha=args.sha, run_id=args.run_id, attempt=args.attempt,
        scope_digest=sha256(args.source_path.read_bytes()),
        previous=read(args.baseline) if args.baseline else None,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(summary(receipt))
    print(summary(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
