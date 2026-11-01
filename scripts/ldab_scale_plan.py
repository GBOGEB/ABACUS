#!/usr/bin/env python3
"""Disjoint-lane worker plan, port leases and measurement for DAB/LDAB at scale.

Design rules (taken from ABACUS docs/ci/BANDIT_DISJOINT_SCALE_WAVE.md and
governance/dab/DAB_FULL_RED_GATES.json):
  * ownership is by canonical FILE: every file belongs to exactly one lane;
  * protected findings (E999) put their whole file on HOLD, never dispatched;
  * batches obey the policy caps (LOW 12 findings/3 files/one family,
    MEDIUM 4 findings/1 file);
  * proposal workers are read-only and scale 1..N; mutation stays single-writer;
  * missing evidence is null/UNKNOWN, never zero.

Subcommands: plan | lane-scan | reduce | verify
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import socket
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = "ldab.scale.plan.v1"
LINE_RE = re.compile(r"^(?P<path>.+?)\|(?P<line>\d+)\|(?P<code>[A-Z]\d{3})$")
FMT = "%(path)s|%(row)d|%(code)s"
SCAN_ARGS = ["--exit-zero", "--max-line-length=120", "--jobs=1", f"--format={FMT}"]
SCAN_CMD = [
    "flake8",
    "--exit-zero",
    "--max-line-length=120",
    f"--format={FMT}",
]  # identity string
ARGV_CHUNK = 200
CONTAINER_PORT = 4711  # lldb-server port used by CODEX qps_docker_remote_lldb_probe.py
HOLD = "HOLD"


# ---------------------------------------------------------------- parsing
def norm_path(raw: str) -> str:
    p = PurePosixPath(raw.replace("\\", "/"))
    parts = [x for x in p.parts if x not in (".", "")]
    if p.is_absolute() or ".." in parts or not parts:
        raise ValueError(f"unsafe path: {raw!r}")
    return "/".join(parts)


def parse_raw(text: str) -> list[tuple[str, int, str]]:
    out = []
    for ln in text.splitlines():
        if not ln.strip():
            continue
        m = LINE_RE.match(ln.strip())
        if not m:
            raise ValueError(f"unparseable finding line: {ln!r}")
        out.append((norm_path(m["path"]), int(m["line"]), m["code"]))
    return sorted(out)


def risk_for(code: str, policy: dict) -> str:
    if code in policy.get("protected_holds", {}):
        return "HIGH_OR_PROTECTED"
    if code in policy["batch_policy"]["LOW_MECHANICAL"]["families"]:
        return "LOW_MECHANICAL"
    return "MEDIUM"


# ---------------------------------------------------------------- planning
def assign_owners(weights: dict[str, int], workers: int) -> dict[str, int]:
    """Deterministic LPT: heaviest file first onto the lightest lane."""
    load = [0] * workers
    owner: dict[str, int] = {}
    for path in sorted(weights, key=lambda p: (-weights[p], p)):
        lane = min(range(workers), key=lambda i: (load[i], i))
        owner[path] = lane
        load[lane] += weights[path]
    return owner


def make_batches(rows: list[tuple[str, int, str]], policy: dict) -> list[dict]:
    bp = policy["batch_policy"]
    batches: list[dict] = []

    def flush(kind, fam, cur):
        if cur:
            batches.append(
                {
                    "risk": kind,
                    "family": fam,
                    "findings": len(cur),
                    "files": sorted({r[0] for r in cur}),
                    "items": [list(r) for r in cur],
                }
            )

    low_rows = [r for r in rows if risk_for(r[2], policy) == "LOW_MECHANICAL"]
    cfg = bp["LOW_MECHANICAL"]
    for fam in sorted({r[2] for r in low_rows}):  # one family per batch
        cur: list = []
        for r in (x for x in low_rows if x[2] == fam):
            files = {c[0] for c in cur}
            if cur and (
                len(cur) >= cfg["max_findings"]
                or (r[0] not in files and len(files) >= cfg["max_files"])
            ):
                flush("LOW_MECHANICAL", fam, cur)
                cur = []
            cur.append(r)
        flush("LOW_MECHANICAL", fam, cur)

    cfg = bp["MEDIUM"]
    med = [r for r in rows if risk_for(r[2], policy) == "MEDIUM"]
    for path in sorted({r[0] for r in med}):  # medium: exactly one file per batch
        cur = []
        for r in (x for x in med if x[0] == path):
            if len(cur) >= cfg["max_findings"]:
                flush("MEDIUM", None, cur)
                cur = []
            cur.append(r)
        flush("MEDIUM", None, cur)
    return batches


def lease_for(sha: str, worker_id: str) -> dict:
    """A lease is an intent record. host_port stays null until Docker reports it."""
    return {
        "port_lease_id": hashlib.sha256(f"{sha}|{worker_id}".encode()).hexdigest()[:16],
        "container_port": CONTAINER_PORT,
        "docker_publish": f"127.0.0.1::{CONTAINER_PORT}",  # Docker picks a free host port
        "observe_with": "docker port <container_id> 4711/tcp",
        "host_binding": "127.0.0.1",
        "host_port": None,
        "authenticated": False,
    }


def build_plan(findings, sha: str, workers: int, policy: dict) -> dict:
    if not 1 <= workers <= 256:  # GitHub Actions matrix ceiling
        raise ValueError("workers must be 1..256")
    by_file: dict[str, list] = defaultdict(list)
    for f in findings:
        by_file[f[0]].append(f)
    hold_files = sorted(
        p
        for p, rs in by_file.items()
        if any(risk_for(r[2], policy) == "HIGH_OR_PROTECTED" for r in rs)
    )
    live = {p: len(rs) for p, rs in by_file.items() if p not in set(hold_files)}
    owner = assign_owners(live, workers)
    lanes = []
    for i in range(workers):
        wid = f"W{i:02d}"
        files = sorted(p for p, o in owner.items() if o == i)
        rows = [r for p in files for r in by_file[p]]
        lanes.append(
            {
                "worker_id": wid,
                "mode": "READ_ONLY_PROPOSAL",
                "files": files,
                "file_count": len(files),
                "findings": len(rows),
                "batches": make_batches(rows, policy),
                "port_lease": lease_for(sha, wid),
            }
        )
    total = len(findings)
    hold_n = sum(len(by_file[p]) for p in hold_files)
    loads = [ln["findings"] for ln in lanes]
    mean = sum(loads) / workers if workers else 0
    plan = {
        "schema": SCHEMA,
        "exact_sha": sha,
        "scan_command": " ".join(SCAN_CMD),
        "workers": workers,
        "total_findings": total,
        "hold_findings": hold_n,
        "hold_files": hold_files,
        "lanes": lanes,
        "mutation_writer": {
            "count": 1,
            "note": "controller applies accepted proposals serially",
        },
        "metrics": {
            "imbalance_max_over_mean": round(max(loads) / mean, 4) if mean else None,
            "lane_findings": loads,
        },
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }
    plan["checks"] = check_plan(plan)
    return plan


def check_plan(plan: dict) -> dict:
    seen: dict[str, str] = {}
    dup = []
    for lane in plan["lanes"]:
        for p in lane["files"]:
            if p in seen:
                dup.append(p)
            seen[p] = lane["worker_id"]
    overlap_hold = sorted(set(seen) & set(plan["hold_files"]))
    lane_sum = sum(ln["findings"] for ln in plan["lanes"])
    batch_sum = sum(b["findings"] for ln in plan["lanes"] for b in ln["batches"])
    return {
        "disjoint_ownership": not dup and not overlap_hold,
        "sum_lanes_plus_hold_equals_total": lane_sum + plan["hold_findings"]
        == plan["total_findings"],
        "batched_equals_lane_findings": batch_sum == lane_sum,
        "duplicate_files": dup,
    }


# ---------------------------------------------------------------- execution
def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_scan(files: list[str], cwd: Path) -> list[tuple[str, int, str]]:
    """Run Flake8 in-process (no subprocess) on `files` relative to `cwd`."""
    if not files:
        return []
    from flake8.main import cli  # imported lazily: only scan commands need flake8

    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="utf-8", write_through=True)
    prev = os.getcwd()
    os.chdir(cwd)
    try:
        with contextlib.redirect_stdout(out):
            try:
                cli.main(SCAN_ARGS + files)
            except SystemExit as exc:
                if exc.code not in (0, None):
                    raise RuntimeError(f"flake8 failed rc={exc.code}") from exc
    finally:
        os.chdir(prev)
    out.flush()
    return parse_raw(raw.getvalue().decode("utf-8"))


def lane_scan(plan: dict, worker_id: str, repo: Path) -> dict:
    lane = next(ln for ln in plan["lanes"] if ln["worker_id"] == worker_id)
    start = time.time()
    t0 = now()
    found: list = []
    owned = lane["files"]
    for i in range(0, len(owned), ARGV_CHUNK):  # keep argv bounded
        end = i + ARGV_CHUNK
        found += run_scan(owned[i:end], repo)
    stray = sorted({f[0] for f in found} - set(lane["files"]))
    return {
        "worker_id": worker_id,
        "exact_sha": plan["exact_sha"],
        "start": t0,
        "end": now(),
        "seconds": round(time.time() - start, 3),
        "runner_id": os.environ.get("RUNNER_NAME") or socket.gethostname(),
        "owned_file_count": lane["file_count"],
        "findings": len(found),
        "by_code": dict(sorted(Counter(f[2] for f in found).items())),
        "findings_rows": [list(f) for f in found],
        "stray_paths": stray,
    }


def reduce_lanes(plan: dict, results: list[dict]) -> dict:
    ids = [r["worker_id"] for r in results]
    expected = [ln["worker_id"] for ln in plan["lanes"]]
    got = sum(r["findings"] for r in results)
    want = plan["total_findings"] - plan["hold_findings"]
    secs = [r["seconds"] for r in results]
    return {
        "schema": "ldab.scale.reduce.v1",
        "exact_sha": plan["exact_sha"],
        "all_lanes_reported": sorted(ids) == sorted(expected),
        "sum_of_lanes": got,
        "expected_non_hold": want,
        "reconciled": got == want,
        "stray_path_lanes": [r["worker_id"] for r in results if r["stray_paths"]],
        "critical_path_seconds": max(secs) if secs else None,
        "sum_lane_seconds": round(sum(secs), 3) if secs else None,
        "parallel_efficiency": (
            round(sum(secs) / (len(secs) * max(secs)), 4)
            if secs and max(secs) > 0
            else None
        ),
    }


def verify(
    plan: dict, results: list[dict], after_raw: str | None, after_command: str | None
) -> dict:
    """Ownership + delta check for repair runs. Deltas are UNKNOWN unless scan identity matches."""
    owned = {p: ln["worker_id"] for ln in plan["lanes"] for p in ln["files"]}
    violations, touched = [], defaultdict(list)
    for r in results:
        for p in r.get("changed_paths", []):
            p = norm_path(p)
            touched[p].append(r["worker_id"])
            if owned.get(p) != r["worker_id"]:
                violations.append(
                    {"worker_id": r["worker_id"], "path": p, "owner": owned.get(p)}
                )
    collisions = {p: w for p, w in touched.items() if len(set(w)) > 1}
    out = {
        "schema": "ldab.scale.verify.v1",
        "ownership_violations": violations,
        "write_collisions": collisions,
        "proposal_valid": not violations and not collisions,
    }
    comparable = after_raw is not None and after_command == plan["scan_command"]
    if not comparable:
        out.update(
            opened=None,
            resolved=None,
            net=None,
            delta_status="UNKNOWN_scan_identity_missing_or_mismatch",
        )
        return out
    before = Counter(
        (p, c)
        for lane in plan["lanes"]
        for b in lane["batches"]
        for p, _, c in map(tuple, b["items"])
    )
    hold = set(plan["hold_files"])  # HOLD files are out of scope on both sides
    after = Counter((p, c) for p, _, c in parse_raw(after_raw) if p not in hold)
    opened = sum(max(0, after[k] - before[k]) for k in after)
    resolved = sum(max(0, before[k] - after[k]) for k in before)
    out.update(
        opened=opened,
        resolved=resolved,
        net=resolved - opened,
        delta_status="COMPARABLE_count_by_file_and_code",
    )
    return out


# ---------------------------------------------------------------- CLI
def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _dump(o, p):
    Path(p).write_text(json.dumps(o, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("plan")
    a.add_argument("--raw", required=True)
    a.add_argument("--sha", required=True)
    a.add_argument("--workers", type=int, default=8)
    a.add_argument("--policy", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--matrix-out")
    b = sub.add_parser("lane-scan")
    b.add_argument("--plan", required=True)
    b.add_argument("--worker", required=True)
    b.add_argument("--repo", default=".")
    b.add_argument("--out", required=True)
    c = sub.add_parser("reduce")
    c.add_argument("--plan", required=True)
    c.add_argument("--results", nargs="+", required=True)
    c.add_argument("--out", required=True)
    d = sub.add_parser("verify")
    d.add_argument("--plan", required=True)
    d.add_argument("--results", nargs="+", required=True)
    d.add_argument("--after-raw")
    d.add_argument("--after-command")
    d.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "plan":
        plan = build_plan(
            parse_raw(Path(args.raw).read_text()),
            args.sha,
            args.workers,
            _load(args.policy),
        )
        _dump(plan, args.out)
        if args.matrix_out:
            _dump(
                {
                    "include": [
                        {"worker": ln["worker_id"], "files": ln["file_count"]}
                        for ln in plan["lanes"]
                    ]
                },
                args.matrix_out,
            )
        print(
            json.dumps(
                {
                    "checks": plan["checks"],
                    "metrics": plan["metrics"],
                    "total": plan["total_findings"],
                    "hold": plan["hold_findings"],
                },
                indent=2,
            )
        )
        return (
            0
            if all(v for k, v in plan["checks"].items() if k != "duplicate_files")
            else 2
        )
    if args.cmd == "lane-scan":
        _dump(lane_scan(_load(args.plan), args.worker, Path(args.repo)), args.out)
        return 0
    res = [_load(p) for p in args.results]
    if args.cmd == "reduce":
        rep = reduce_lanes(_load(args.plan), res)
        _dump(rep, args.out)
        print(json.dumps(rep, indent=2))
        return (
            0
            if rep["reconciled"]
            and rep["all_lanes_reported"]
            and not rep["stray_path_lanes"]
            else 2
        )
    rep = verify(
        _load(args.plan),
        res,
        Path(args.after_raw).read_text() if args.after_raw else None,
        args.after_command,
    )
    _dump(rep, args.out)
    print(json.dumps(rep, indent=2))
    return 0 if rep["proposal_valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
