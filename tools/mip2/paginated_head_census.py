"""Fail-closed pagination and event-amplification census for one exact GitHub head.

An API observation is not a signed artifact, an independent test population,
a causal-root closure, or a merge authority. Never silently truncate >100 runs.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import quote

SCHEMA = "abacus.github.head-run-pages.v1"
OUTPUT = "abacus.mip.paginated-head-census.v1"
REPO = "GBOGEB/ABACUS"
API = "https://api.github.com/repos/GBOGEB/ABACUS/actions/runs"
PAGE_SIZE = 100
MAX_PAGES = 50
SHA = re.compile(r"[0-9a-f]{40}\Z")
EVENT = re.compile(r"[a-z][a-z0-9_]*\Z")
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
OPEN = {"queued", "pending", "in_progress", "requested", "waiting"}
TERMINAL = {"success", "failure", "cancelled", "skipped", "neutral",
            "timed_out", "action_required", "startup_failure"}


def _positive(value):
    return type(value) is int and value > 0


def _require(value, message):
    if not value:
        raise ValueError(message)


def _utc_timestamp(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValueError("invalid canonical UTC timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ValueError("invalid canonical UTC timestamp") from error


def analyze_head_pages(doc):
    """Return complete *observed-run* census, never infer terminal admission.

    Each page must match exact source SHA, URL and its declared total count.
    Event-type accounting is kept separate from workflow-ID and run counts.
    """
    _require(isinstance(doc, dict), "input must be object")
    _require(doc.get("schema") == SCHEMA, "wrong source schema")
    _require(doc.get("repository") == REPO, "foreign repository")
    _require(doc.get("source_role") == "OBSERVED_DEFAULT_BRANCH_HEAD",
             "unsupported source identity role")
    sha = doc.get("source_sha")
    _require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid exact head SHA")
    cutoff = doc.get("created_cutoff_utc")
    cutoff_time = _utc_timestamp(cutoff) if cutoff is not None else None
    pages = doc.get("pages")
    _require(isinstance(pages, list) and pages, "missing API pages")
    _require(len(pages) <= MAX_PAGES, "page-count cap exceeded")
    _require(isinstance(pages[0], dict), "invalid first API page")
    total = pages[0].get("total_count")
    _require(_positive(total) and total <= MAX_PAGES * PAGE_SIZE,
             "invalid or excessive native total")
    expected_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    _require(len(pages) == expected_pages, "truncated or excess API page count")

    families = defaultdict(list)
    event_counts = Counter()
    status_counts = Counter()
    conclusions = Counter()
    run_seen = set()
    total_read = 0
    for page_number, page in enumerate(pages, 1):
        _require(isinstance(page, dict), "API page must be object")
        _require(type(page.get("page")) is int and page["page"] == page_number,
                 "out-of-order API pagination")
        _require(page.get("total_count") == total and
                 type(page.get("total_count")) is int,
                 "unstable API total denominator")
        expected_url = (f"{API}?head_sha={sha}&per_page={PAGE_SIZE}"
                        f"&page={page_number}")
        if cutoff is not None:
            expected_url += "&created=" + quote("<=" + cutoff, safe="")
        _require(page.get("api_url") == expected_url, "unbound API page URL")
        rows = page.get("runs")
        expected_length = min(PAGE_SIZE, total - PAGE_SIZE * (page_number - 1))
        _require(isinstance(rows, list) and len(rows) == expected_length,
                 "missing or excess native rows within page")
        for row in rows:
            _require(isinstance(row, dict), "nonobject native run")
            rid, wf, attempt = (row.get("id"), row.get("workflow_id"),
                                row.get("run_attempt"))
            _require(all(_positive(x) for x in (rid, wf, attempt)),
                     "invalid native run/workflow/attempt identity")
            _require(rid not in run_seen, "duplicate native run identity")
            run_seen.add(rid)
            _require(row.get("head_sha") == sha, "mixed head SHA in API cohort")
            if cutoff is not None:
                timestamp = _utc_timestamp(row.get("created_at"))
                _require(timestamp <= cutoff_time,
                         "native run created after frozen UTC cutoff")
            event = row.get("event")
            _require(isinstance(event, str) and EVENT.fullmatch(event),
                     "invalid GitHub triggering event")
            status, conclusion = row.get("status"), row.get("conclusion")
            _require(isinstance(status, str), "missing native status")
            if status == "completed":
                _require(conclusion in TERMINAL, "nonqualifying terminal conclusion")
                conclusions[conclusion] += 1
            else:
                _require(status in OPEN, "unrecognized nonterminal run state")
                _require(conclusion is None, "premature terminal result claimed")
            families[wf].append((rid, event, status, conclusion))
            event_counts[event] += 1
            status_counts[status] += 1
            total_read += 1
    _require(total_read == total, "incomplete total run census")

    manifest = []
    for wf, runs in families.items():
        events = Counter(row[1] for row in runs)
        manifest.append({
            "workflow_id": wf,
            "observed_run_count": len(runs),
            "repeat_excess": len(runs) - 1,
            "event_counts": dict(sorted(events.items())),
            "nonterminal": sum(row[2] != "completed" for row in runs),
            "terminal_success": sum(row[3] == "success" for row in runs),
            "terminal_failure": sum(row[3] in {"failure", "timed_out",
                                                   "action_required", "startup_failure"}
                                    for row in runs),
            "run_ids": sorted(row[0] for row in runs),
        })
    manifest.sort(key=lambda x: (-x["observed_run_count"], x["workflow_id"]))
    terminal = status_counts["completed"]
    repeat_excess = total - len(families)
    _require(sum(x["repeat_excess"] for x in manifest) == repeat_excess,
             "repeat-run accounting mismatch")
    return {
        "schema": OUTPUT,
        "repository": REPO,
        "source_sha": sha,
        "source_role": "OBSERVED_DEFAULT_BRANCH_HEAD",
        "created_cutoff_utc": cutoff,
        "snapshot_population": (
            "FROZEN_CREATION_WINDOW_STATUS_AS_OBSERVED" if cutoff is not None
            else "UNFILTERED_NONATOMIC_STATUS_OBSERVATION"
        ),
        "page_size": PAGE_SIZE,
        "pages_qualified_structurally": expected_pages,
        "observed_run_count": total,
        "distinct_workflow_ids": len(families),
        "repeat_run_excess": repeat_excess,
        "repeat_run_fraction": round(repeat_excess / total, 6),
        "event_counts": dict(sorted(event_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "conclusion_counts": dict(sorted(conclusions.items())),
        "terminal_run_count": terminal,
        "terminal_success_fraction": (
            round(conclusions["success"] / terminal, 6) if terminal else None
        ),
        "native_testcase_count": None,
        "queue_latency_p95": None,
        "independent_causal_root_count": None,
        "artifact_byte_attestation": "NOT_PROVEN_BY_API_STRUCTURAL_CENSUS",
        "source_readback_completeness": "ALL_DECLARED_PAGES_VALIDATED",
        "admission": "HOLD",
        "manifest": manifest,
    }
