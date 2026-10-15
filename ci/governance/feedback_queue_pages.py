"""Bounded double-pass read-only GitHub queue census.

No API pages are omitted silently. Two matching sweeps increase confidence in
pagination completeness but are not an atomic GitHub transaction. Status
changes between the sweeps return UNKNOWN, never an approval or skip decision.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from urllib.parse import quote

SCHEMA = "abacus.feedback.queue-pages.v1"
PAGE_SIZE = 100
MAX_PAGES = 20
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def canonical(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def parse_row(raw, sha):
    if not isinstance(raw, dict):
        raise ValueError("malformed GitHub Actions run")
    ident = raw.get("id")
    if type(ident) is not int or ident <= 0:
        raise ValueError("missing positive numeric run ID")
    if raw.get("status") != "queued":
        raise ValueError("non-queued run returned by queued query")
    if sha is not None and raw.get("head_sha") != sha:
        raise ValueError("unexpected head SHA in source-scoped queue")
    name, event = raw.get("name"), raw.get("event")
    if not isinstance(name, str) or not name or not isinstance(event, str) or not event:
        raise ValueError("run name or event missing")
    return {"id": ident, "name": name, "event": event,
            "head_sha": raw.get("head_sha"), "created_at": raw.get("created_at")}


def one_sweep(get, repo, sha, max_pages):
    endpoint = "/repos/" + repo + "/actions/runs?status=queued&per_page=100"
    if sha:
        endpoint += "&head_sha=" + quote(sha, safe="")
    rows, count = [], None
    for page in range(1, max_pages + 1):
        doc = get(endpoint + "&page=" + str(page))
        if not isinstance(doc, dict) or type(doc.get("total_count")) is not int:
            raise ValueError("GitHub queue count missing")
        if doc["total_count"] < 0:
            raise ValueError("negative queue count")
        if count is None:
            count = doc["total_count"]
            if count > PAGE_SIZE * max_pages:
                raise ValueError("queue exceeds bounded pagination budget")
        if doc["total_count"] != count:
            raise ValueError("population changed during pagination")
        part = doc.get("workflow_runs")
        if not isinstance(part, list) or len(part) > PAGE_SIZE:
            raise ValueError("invalid workflow page")
        rows.extend(parse_row(v, sha) for v in part)
        if len(rows) >= count:
            break
        if len(part) != PAGE_SIZE:
            raise ValueError("missing records before population exhausted")
    if len(rows) != count:
        raise ValueError("page total does not match queue count")
    ids = {r["id"] for r in rows}
    if len(ids) != len(rows):
        raise ValueError("duplicate run across pages")
    return sorted(rows, key=lambda r: r["id"]), max(1, math.ceil(count / PAGE_SIZE))


def inspect(get, repository="GBOGEB/ABACUS", sha=None, max_pages=MAX_PAGES):
    if not isinstance(repository, str) or "/" not in repository:
        raise ValueError("repository identity is required")
    if sha is not None and (not isinstance(sha, str) or not FULL_SHA.fullmatch(sha)):
        raise ValueError("source must be a lowercase 40-character SHA")
    if type(max_pages) is not int or max_pages < 1 or max_pages > MAX_PAGES:
        raise ValueError("invalid bounded page limit")
    # Intentionally retain explicit UNKNOWN rather than treating a failed or
    # moving API read as an empty (green) queue.
    try:
        before, pages1 = one_sweep(get, repository, sha, max_pages)
        after, pages2 = one_sweep(get, repository, sha, max_pages)
    except (ValueError, RuntimeError, OSError) as exc:
        return {"schema": SCHEMA, "repository": repository, "head_sha": sha,
                "state": "UNKNOWN", "reason": type(exc).__name__ + ": " + str(exc),
                "count": None, "runs": None, "digest_sha256": None,
                "authority_transfer": False, "skip_authorized": False}
    if before != after or pages1 != pages2:
        return {"schema": SCHEMA, "repository": repository, "head_sha": sha,
                "state": "UNKNOWN", "reason": "DOUBLE_SWEEP_DRIFT",
                "count": None, "runs": None, "digest_sha256": None,
                "authority_transfer": False, "skip_authorized": False}
    digest = hashlib.sha256((canonical(after) + "\n").encode()).hexdigest()
    return {"schema": SCHEMA, "repository": repository, "head_sha": sha,
            "state": "CENSUS_CONSISTENT_NOT_ATOMIC", "reason": None,
            "count": len(after), "runs": after, "pages_per_pass": pages1,
            "digest_sha256": digest, "authority_transfer": False,
            "skip_authorized": False, "open_pr_linkage": "NOT_CHECKED"}
