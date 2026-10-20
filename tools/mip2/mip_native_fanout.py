"""Measure native GitHub Actions fan-out without claiming worker dispatch.

Accepts complete, saved REST API run and job-list responses. Output is read-only
CI metadata: neither Crew authentication nor accepted REX or merge authority.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = "abacus.mip.native-fanout.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
WORKER_PREFIX = "DAB proposal worker "
CONCLUSIONS = frozenset({
    "success", "failure", "cancelled", "timed_out", "neutral",
    "skipped", "action_required", "stale", "startup_failure",
})


def require(value: bool, reason: str) -> None:
    """Fail closed on unknown identity and incomplete measurements."""
    if not value:
        raise ValueError(reason)


def instant(value: object) -> dt.datetime:
    """Parse a real timezone-qualified GitHub timestamp."""
    require(isinstance(value, str) and bool(value), "missing timestamp")
    try:
        when = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid timestamp") from error
    require(when.tzinfo is not None, "timestamp timezone missing")
    return when

def nearest_rank(values: list[float], quantile: float) -> float:
    """Exact nearest-rank percentile, never extrapolating missing jobs."""
    require(bool(values), "empty percentile population")
    ordered = sorted(values)
    return round(ordered[math.ceil(quantile * len(ordered)) - 1], 3)


def observe(run: dict, collection: dict) -> dict:
    """Measure completed native jobs with full API enumeration."""
    require(isinstance(run, dict) and isinstance(collection, dict), "invalid API response")
    require(run.get("repository", {}).get("full_name") == "GBOGEB/ABACUS", "repository mismatch")
    sha = run.get("head_sha")
    require(isinstance(sha, str) and SHA.fullmatch(sha) is not None, "invalid SHA")
    rid = run.get("id")
    require(type(rid) is int and rid > 0, "invalid run ID")
    require(run.get("status") == "completed", "nonterminal run is not an outcome")
    require(run.get("conclusion") in CONCLUSIONS, "run conclusion missing")
    attempt = run.get("run_attempt")
    require(type(attempt) is int and attempt > 0, "invalid run attempt")
    jobs = collection.get("jobs")
    count = collection.get("total_count")
    require(isinstance(jobs, list) and type(count) is int and count == len(jobs), "truncated jobs")
    seen = set()
    selected = []
    for job in jobs:
        require(isinstance(job, dict), "invalid job")
        jid = job.get("id")
        require(type(jid) is int and jid > 0 and jid not in seen, "duplicate job identity")
        seen.add(jid)
        require(job.get("run_id") == rid, "job-run mismatch")
        require(job.get("head_sha") in (None, sha), "job SHA mismatch")
        require(job.get("run_attempt") in (None, attempt), "job attempt mismatch")
        if not str(job.get("name", "")).startswith(WORKER_PREFIX):
            continue
        require(job.get("status") == "completed", "nonterminal worker")
        require(job.get("conclusion") in CONCLUSIONS, "missing worker conclusion")
        start, end = instant(job.get("started_at")), instant(job.get("completed_at"))
        require(end > start, "nonpositive worker duration")
        created = job.get("created_at")
        delay = None
        if created is not None:
            created_at = instant(created)
            require(start >= created_at, "negative created-to-start duration")
            delay = (start - created_at).total_seconds()
        selected.append({
            "job_id": jid,
            "name": job["name"],
            "conclusion": job.get("conclusion"),
            "start": start,
            "end": end,
            "duration_seconds": (end - start).total_seconds(),
            "created_to_start_seconds": delay,
        })
    require(bool(selected), "no DAB worker observations")
    events = []
    for row in selected:
        events.append((row["start"], 1))
        events.append((row["end"], -1))
    events.sort(key=lambda item: (item[0], item[1]))
    previous, concurrency, peak, idle = events[0][0], 0, 0, 0.0
    for when, delta in events:
        span = (when - previous).total_seconds()
        if concurrency == 0:
            idle += span
        concurrency += delta
        require(concurrency >= 0, "invalid worker intervals")
        peak = max(peak, concurrency)
        previous = when
    require(concurrency == 0, "unclosed worker interval")
    wall = (events[-1][0] - events[0][0]).total_seconds()
    total = sum(item["duration_seconds"] for item in selected)
    require(wall > 0 and total > 0, "nonmeasurable fanout")
    outcomes = {name: sum(
        job["conclusion"] == name for job in selected
    ) for name in sorted(CONCLUSIONS)}
    ids = sorted(job["job_id"] for job in selected)
    delays = [job["created_to_start_seconds"] for job in selected
              if job["created_to_start_seconds"] is not None]
    complete_delay = len(delays) == len(selected)
    return {
        "schema": SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "head_sha": sha,
        "run_id": rid,
        "run_attempt": attempt,
        "run_conclusion": run["conclusion"],
        "run_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{rid}",
        "source_kind": "NATIVE_GITHUB_API_METADATA",
        "evidence_level": "RUN_JOB_METADATA_NOT_ARTIFACT_BYTES",
        "worker_kind": "DAB_PROPOSAL_ONLY",
        "worker_count": len(selected),
        "successful_workers": sum(row["conclusion"] == "success" for row in selected),
        "failed_workers": outcomes["failure"],
        "non_success_workers": len(selected) - outcomes["success"],
        "worker_conclusions": outcomes,
        "worker_job_ids": ids,
        "worker_job_ids_sha256": hashlib.sha256(
            ",".join(str(job_id) for job_id in ids).encode("ascii")
        ).hexdigest(),
        "summed_job_seconds": round(total, 3),
        "first_to_last_seconds": round(wall, 3),
        "idle_gap_seconds": round(idle, 3),
        "active_span_seconds": round(wall - idle, 3),
        "peak_concurrency": peak,
        "overlap_factor": round(total / wall, 4),
        "execution_p95_seconds": nearest_rank(
            [job["duration_seconds"] for job in selected], 0.95
        ),
        "queue_observation_count": len(delays),
        "created_to_start_p95_seconds": (
            nearest_rank(delays, 0.95) if complete_delay else None
        ),
        "queue_qualification": (
            "COMPLETE_JOB_METADATA" if complete_delay else "INCOMPLETE_JOB_METADATA"
        ),
        "authenticated_crew_dispatches": None,
        "root_closures": None,
        "coverage_gain_pp": None,
        "merge_admission": "HOLD",
    }

def validate_observation(row: dict) -> None:
    """Reverse-check locally constructed observations before any comparison."""
    require(isinstance(row, dict), "invalid fanout observation")
    require(row.get("schema") == SCHEMA, "native fanout receipt required")
    require(row.get("repository") == "GBOGEB/ABACUS", "repository mismatch")
    require(row.get("worker_kind") == "DAB_PROPOSAL_ONLY", "worker type mismatch")
    require(row.get("source_kind") == "NATIVE_GITHUB_API_METADATA",
            "source kind mismatch")
    sha = row.get("head_sha")
    require(isinstance(sha, str) and SHA.fullmatch(sha) is not None, "invalid SHA")
    rid = row.get("run_id")
    require(type(rid) is int and rid > 0, "invalid run ID")
    require(row.get("run_url") ==
            f"https://github.com/GBOGEB/ABACUS/actions/runs/{rid}",
            "forged run URL")
    require(type(row.get("run_attempt")) is int and
            row["run_attempt"] > 0, "invalid run attempt")
    require(row.get("run_conclusion") in CONCLUSIONS, "invalid run conclusion")
    integer_fields = ("worker_count", "successful_workers", "failed_workers",
                      "non_success_workers", "peak_concurrency",
                      "queue_observation_count")
    for field in integer_fields:
        require(type(row.get(field)) is int and row[field] >= 0,
                "invalid count: " + field)
    count = row["worker_count"]
    require(count > 0 and 1 <= row["peak_concurrency"] <= count,
            "invalid worker census")
    require(0 <= row["successful_workers"] <= count and
            row["failed_workers"] <= row["non_success_workers"] and
            row["non_success_workers"] == count - row["successful_workers"],
            "inconsistent worker outcomes")
    conclusions = row.get("worker_conclusions")
    require(isinstance(conclusions, dict) and
            set(conclusions) == CONCLUSIONS and
            all(type(value) is int and value >= 0
                for value in conclusions.values()) and
            sum(conclusions.values()) == count and
            conclusions["success"] == row["successful_workers"] and
            conclusions["failure"] == row["failed_workers"],
            "invalid conclusion census")
    ids = row.get("worker_job_ids")
    require(isinstance(ids, list) and
            all(type(i) is int and i > 0 for i in ids) and
            ids == sorted(set(ids)) and len(ids) == count,
            "invalid worker job IDs")
    fingerprint = hashlib.sha256(
        ",".join(str(i) for i in ids).encode("ascii")
    ).hexdigest()
    require(row.get("worker_job_ids_sha256") == fingerprint,
            "invalid worker identity digest")
    for field in ("summed_job_seconds", "first_to_last_seconds",
                  "idle_gap_seconds", "active_span_seconds",
                  "overlap_factor", "execution_p95_seconds"):
        value = row.get(field)
        require(type(value) in (int, float) and math.isfinite(value) and
                value >= 0, "invalid duration: " + field)
    wall = row["first_to_last_seconds"]
    require(wall > 0 and row["summed_job_seconds"] > 0 and
            row["idle_gap_seconds"] <= wall and
            abs(row["active_span_seconds"] -
                (wall - row["idle_gap_seconds"])) < 0.01 and
            abs(row["overlap_factor"] -
                row["summed_job_seconds"] / wall) < 0.001,
            "inconsistent duration census")
    observed = row["queue_observation_count"]
    require(observed <= count, "invalid queue population")
    p95 = row.get("created_to_start_p95_seconds")
    if observed == count:
        require(type(p95) in (int, float) and math.isfinite(p95) and
                p95 >= 0 and
                row.get("queue_qualification") == "COMPLETE_JOB_METADATA",
                "incomplete queue evidence")
    else:
        require(p95 is None and
                row.get("queue_qualification") == "INCOMPLETE_JOB_METADATA",
                "unknown queue latency must remain null")
    require(row.get("merge_admission") == "HOLD" and
            row.get("authenticated_crew_dispatches") is None and
            row.get("root_closures") is None and
            row.get("coverage_gain_pp") is None,
            "unverified operational credit")


def compare(before: dict, after: dict) -> dict:
    """Only compare like-for-like, separately SHA-bound native observations."""
    for row in (before, after):
        validate_observation(row)
    require(before["run_id"] != after["run_id"], "distinct runs required")
    fields = ("worker_count", "successful_workers", "non_success_workers",
              "summed_job_seconds", "first_to_last_seconds",
              "idle_gap_seconds", "peak_concurrency", "overlap_factor",
              "execution_p95_seconds")
    queue_delta = (
        round(after["created_to_start_p95_seconds"] -
              before["created_to_start_p95_seconds"], 4)
        if before["created_to_start_p95_seconds"] is not None and
        after["created_to_start_p95_seconds"] is not None else None
    )
    return {
        "schema": "abacus.mip.native-fanout-comparison.v1",
        "before": before,
        "after": after,
        "delta": {
            field: round(after[field] - before[field], 4)
            for field in fields
        } | {"created_to_start_p95_seconds": queue_delta},
        "matched_population": "DAB_PROPOSAL_WORKERS",
        "causal_explanation": None,
        "operational_root_closure": None,
        "authenticated_crew_dispatches": None,
        "admission": "HOLD",
    }


def render_markdown(report: dict) -> str:
    """Emit concise wave metrics with audit links and explicit missing credit."""
    a, b, change = (report["before"], report["after"], report["delta"])
    lines = [
        "# MIP native fan-out: per-wave comparison", "",
        "> GitHub API metadata only; not a Crew dispatch, merge, root closure,",
        "> security attestation or proof of artifact bytes.", "",
        "| Metric | Previous wave | Current wave | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    labels = {
        "worker_count": "DAB proposal jobs",
        "successful_workers": "Successful jobs",
        "non_success_workers": "Non-success jobs",
        "summed_job_seconds": "Summed job seconds",
        "first_to_last_seconds": "Fan-out elapsed seconds",
        "idle_gap_seconds": "Idle-gap seconds",
        "peak_concurrency": "Peak parallel jobs",
        "overlap_factor": "Job-time / elapsed ratio",
        "execution_p95_seconds": "Execution p95 (seconds)",
        "created_to_start_p95_seconds": "Created-to-start p95 (seconds)",
    }
    for field, label in labels.items():
        delta = change[field]
        shown_delta = f"{delta:+g}" if delta is not None else "UNKNOWN"
        first, latest = a.get(field), b.get(field)
        lines.append(
            f"| {label} | {first if first is not None else 'UNKNOWN'} | "
            f"{latest if latest is not None else 'UNKNOWN'} | {shown_delta} |"
        )
    lines.extend([
        "", f"Before: {a['run_url']} @ \\u0060{a['head_sha']}\\u0060",
        f"After: {b['run_url']} @ \\u0060{b['head_sha']}\\u0060",
        "", "First-red causality: UNKNOWN. Coverage and BD-root closure: UNKNOWN.",
        "No main admission or CODEX-to-ABACUS transport authority is granted.", "",
    ])
    return "\n".join(lines).replace("\\u0060", "`")


def render_html(report: dict) -> str:
    """Make an offline, responsive and dependency-free operational review."""
    a, b = report["before"], report["after"]
    fields = (
        ("worker_count", "Proposal jobs", ""),
        ("successful_workers", "Successful jobs", ""),
        ("non_success_workers", "Non-success jobs", ""),
        ("execution_p95_seconds", "Execution p95", " s"),
        ("first_to_last_seconds", "Fan-out elapsed", " s"),
        ("idle_gap_seconds", "Idle gaps", " s"),
        ("peak_concurrency", "Peak concurrency", ""),
        ("overlap_factor", "Overlap factor", "x"),
    )
    cards = []
    for key, label, unit in fields:
        first, latest = a[key], b[key]
        delta = report["delta"][key]
        cards.append(
            "<section class='metric'><small>" + html.escape(label) + "</small>"
            + f"<strong>{latest:g}{unit}</strong>"
            + f"<span>Before {first:g}{unit} · Δ {delta:+g}{unit}</span></section>"
        )
    max_elapsed = max(a["first_to_last_seconds"], b["first_to_last_seconds"], 1)
    bars = []
    for row, title in ((a, "Previous wave"), (b, "Current wave")):
        value = row["first_to_last_seconds"]
        width = 100 * value / max_elapsed
        idle = 100 * row["idle_gap_seconds"] / value
        bars.append(
            "<div class='measure'><div class='line'><b>" + title + "</b>"
            + f"<span>{value:g}s · idle {row['idle_gap_seconds']:g}s</span></div>"
            + f"<div class='track' style='width:{width:.2f}%'>"
            + f"<div class='idle' style='width:{idle:.2f}%'></div>"
            + "</div></div>"
        )
    latest_p95 = b["created_to_start_p95_seconds"]
    p95_label = str(latest_p95) + "s" if latest_p95 is not None else "UNKNOWN"
    links = "".join(
        "<a href='" + html.escape(row["run_url"], quote=True) + "'>"
        + label + " run " + str(row["run_id"]) + "</a>"
        for label, row in (("Previous", a), ("Current", b))
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>MIP native fan-out review</title><style>"
        ":root{color-scheme:light dark;font:16px system-ui,sans-serif}"
        "body{max-width:1100px;margin:auto;padding:clamp(16px,4vw,44px)}"
        "h1{font-size:clamp(24px,3vw,38px)}.metrics{display:grid;"
        "grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px}"
        ".metric{border:1px solid #7775;border-radius:12px;padding:16px}"
        ".metric small,.metric span{display:block;color:gray}.metric strong"
        "{font-size:1.6rem;display:block;margin:8px 0}.measure{margin:22px 0}"
        ".line{display:flex;justify-content:space-between;gap:10px}"
        ".track{background:#3986c9;height:18px;min-width:3px;border-radius:6px}"
        ".idle{background:#d79543;height:100%;border-radius:6px}"
        ".links{display:flex;flex-wrap:wrap;gap:18px}a{color:inherit}"
        "</style><h1>MIP native fan-out · wave comparison</h1>"
        "<p>Read-only GitHub Actions job metadata. No Crew dispatch, root "
        "closure, security clearance or merge admission is inferred.</p>"
        "<div class='metrics'>" + "".join(cards) + "</div>"
        "<p>Created-to-start p95 (current wave): " + p95_label
        + ". Missing job timestamps mean UNKNOWN, not zero. "
        "This is not complete workflow queue time.</p><h2>Elapsed time"
        " and idle gaps</h2>" + "".join(bars)
        + "<p>Blue: active time; amber: no proposal job active inside the"
        " observed span. Scheduling cause remains UNKNOWN.</p>"
        "<div class='links'>" + links + "</div></html>"
    )


def main() -> None:
    """Write synchronized JSON, Markdown and static HTML surfaces."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-run", type=Path, required=True)
    parser.add_argument("--previous-jobs", type=Path, required=True)
    parser.add_argument("--current-run", type=Path, required=True)
    parser.add_argument("--current-jobs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    inputs = {
        "previous_run": args.previous_run,
        "previous_jobs": args.previous_jobs,
        "current_run": args.current_run,
        "current_jobs": args.current_jobs,
    }
    sources = {}
    hashes = {}
    for name, path in inputs.items():
        raw = path.read_bytes()
        require(bool(raw), "empty API input")
        sources[name] = json.loads(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    report = compare(
        observe(sources["previous_run"], sources["previous_jobs"]),
        observe(sources["current_run"], sources["current_jobs"]),
    )
    report["api_input_sha256"] = hashes
    report["api_input_integrity"] = "HASHED_LOCAL_INPUT_NOT_SIGNED_AUTHORITY"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, body in (
        ("mip_native_fanout.json", json.dumps(report, indent=2, sort_keys=True) + "\n"),
        ("mip_native_fanout.md", render_markdown(report)),
        ("mip_native_fanout.html", render_html(report)),
    ):
        (args.output_dir / name).write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
