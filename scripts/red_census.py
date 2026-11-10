#!/usr/bin/env python3
"""RED census: classify every active GitHub Actions workflow by its default-branch history.

Report-only observer. Stdlib only (urllib + json). It never writes to a
repository; the optional ``--ledger-append`` is a local, single-writer helper
for the owner (see docs/ci/RED_CENSUS_README.md) and is never run from CI.

Classes (per active workflow, last N completed default-branch runs):

  EVERRED       every decisive run in the window is red
  GREEN_TO_RED  exactly one transition, newest run red (first_red_sha given)
  FLAKY         two or more red/green transitions in the window
  GREEN         newest decisive run green with at most one transition
  NO_MAIN_RUNS  no decisive completed run on the default branch
  STARTUP_FAILURE  the only failures in the window are runs that failed with
                zero jobs (native startup_failure, or failure + 0 jobs);
                such runs are non-decisive everywhere and never make a
                workflow EVERRED / GREEN_TO_RED
  GHOST         GitHub lists the workflow as active, but its path does not
                exist at the default-branch HEAD. GHOST is reported
                separately and never counted as EVERRED / GREEN_TO_RED.

Flags: STALE when the workflow file's latest default-branch commit is newer
than its newest default-branch run; PARTIAL when a paginated API total
exceeds what was fetched.

Conventions (docs/ci/EVERRED_QUEUE_VIEW_README.md): native REST inputs, no
wall-clock timestamp in deterministic output, explicit PARTIAL, and never sum
census counts with BD roots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCHEMA = "red.census.v1"
API = "https://api.github.com"
WINDOW = 10
PER_PAGE = 100
MAX_PAGES = 50

RED = {"failure", "timed_out"}
# A run that failed before any job was created (native conclusion
# "startup_failure", or "failure" with zero jobs, e.g. GitHub "Internal server
# error" at startup) is infrastructure noise: non-decisive, reported separately.
STARTUP = "STARTUP_FAILURE"
GREEN = {"success"}
# cancelled / skipped / neutral / action_required / stale are not decisive.

CLASSES = ("EVERRED", "GREEN_TO_RED", "FLAKY", "GREEN", "NO_MAIN_RUNS", "STARTUP_FAILURE", "GHOST")
RED_CLASSES = ("EVERRED", "GREEN_TO_RED")

LEDGER_SCHEMA_FIELDS = (
    "root_id",
    "family",
    "title",
    "repo",
    "workflows",
    "state",
    "evidence",
    "prev_hash",
    "row_hash",
)
LEDGER_STATES = ("ACTIVE", "READY", "HOLD", "BLOCKED", "BURNED")
GENESIS = "0" * 64
ROOT_SCOPE = "GBOGEB"
ROOT_TYPE = "ci-root"


# ---------------------------------------------------------------------------
# Transport: live REST or saved responses
# ---------------------------------------------------------------------------


def request_key(path: str, params: dict | None = None) -> str:
    """Stable key for a GET request: path plus sorted query string."""
    query = urllib.parse.urlencode(sorted((params or {}).items()))
    return f"GET {path}" + (f"?{query}" if query else "")


class NotFound(Exception):
    pass


class LiveClient:
    def __init__(self, token: str | None, record: dict | None = None):
        self.token = token
        self.record = record

    def get(self, path: str, params: dict | None = None):
        key = request_key(path, params)
        url = API + key[4:]
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "abacus-red-census",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        for attempt in range(3):
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    if self.record is not None:
                        self.record[key] = {"__status__": 404}
                    raise NotFound(key) from exc
                if exc.code in (429, 502, 503) and attempt < 2:
                    time.sleep(5)
                    continue
                raise
        if self.record is not None:
            self.record[key] = body
        return body


class OfflineClient:
    """Serves saved REST responses: {"GET /path?query": body | {"__status__": 404}}."""

    def __init__(self, responses: dict):
        self.responses = responses

    def get(self, path: str, params: dict | None = None):
        key = request_key(path, params)
        if key not in self.responses:
            raise KeyError(f"offline fixture has no response for {key}")
        body = self.responses[key]
        if isinstance(body, dict) and body.get("__status__") == 404:
            raise NotFound(key)
        return body


# ---------------------------------------------------------------------------
# Census
# ---------------------------------------------------------------------------


def paged(client, path: str, list_key: str, params: dict | None = None):
    """Explicit ``page=`` loop (Link-header pagination is unreliable behind proxies).

    Returns (records, api_total, partial).
    """
    records: list = []
    total = None
    page = 1
    while page <= MAX_PAGES:
        q = dict(params or {})
        q.update({"per_page": PER_PAGE, "page": page})
        body = client.get(path, q)
        batch = body.get(list_key)
        t = body.get("total_count")
        if not isinstance(batch, list):
            raise ValueError(f"invalid REST response for {path}: no {list_key} list")
        if type(t) is int:
            total = t
        records.extend(batch)
        if len(batch) < PER_PAGE or (total is not None and len(records) >= total):
            break
        page += 1
    if total is None:
        total = len(records)
    return records, total, total > len(records)


def classify(conclusions: list[str]) -> tuple[str, int | None]:
    """Classify newest-first conclusions. Returns (class, index of first red or None)."""
    seq = [
        "R" if c in RED else "G"
        for c in conclusions
        if c in RED or c in GREEN
    ]
    if not seq:
        if STARTUP in conclusions:
            return "STARTUP_FAILURE", None
        return "NO_MAIN_RUNS", None
    if all(s == "R" for s in seq):
        return "EVERRED", len(seq) - 1
    if all(s == "G" for s in seq):
        return "GREEN", None
    transitions = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    if transitions >= 2:
        return "FLAKY", None
    if seq[0] == "R":
        streak = 0
        while streak < len(seq) and seq[streak] == "R":
            streak += 1
        return "GREEN_TO_RED", streak - 1
    return "GREEN", None  # recovered: one red->green transition


def census_repo(client, repo: str, window: int = WINDOW) -> dict:
    meta = client.get(f"/repos/{repo}")
    branch = meta.get("default_branch") or "main"
    head = client.get(f"/repos/{repo}/commits/{branch}")
    head_sha = head.get("sha")

    workflows, wf_total, wf_partial = paged(
        client, f"/repos/{repo}/actions/workflows", "workflows"
    )
    try:
        listing = client.get(
            f"/repos/{repo}/contents/.github/workflows", {"ref": head_sha}
        )
        present = {item.get("path") for item in listing if isinstance(item, dict)}
        present_known = True
    except NotFound:
        present, present_known = set(), True

    rows = []
    skipped_dynamic = 0
    for wf in sorted(workflows, key=lambda w: (w.get("path") or "", w.get("id") or 0)):
        if wf.get("state") != "active":
            continue
        path = wf.get("path") or ""
        if not path.startswith(".github/workflows/"):
            skipped_dynamic += 1  # dynamic/... (Copilot, Dependabot, Pages)
            continue
        row = {
            "id": wf.get("id"),
            "name": wf.get("name") or "UNKNOWN",
            "path": path,
            "class": None,
            "flags": [],
            "window": [],
            "first_red_sha": None,
            "first_red_run_id": None,
            "last_run_id": None,
            "last_run_sha": None,
            "last_run_created_at": None,
            "file_last_commit_sha": None,
            "file_last_commit_at": None,
        }
        if present_known and path not in present:
            row["class"] = "GHOST"
            rows.append(row)
            continue

        body = client.get(
            f"/repos/{repo}/actions/workflows/{wf['id']}/runs",
            {
                "branch": branch,
                "status": "completed",
                "exclude_pull_requests": "true",
                "per_page": window,
                "page": 1,
            },
        )
        runs = [
            r
            for r in body.get("workflow_runs", [])
            if r.get("head_branch") == branch
            and r.get("event") not in ("pull_request", "pull_request_target")
        ]
        runs.sort(key=lambda r: (r.get("created_at") or "", r.get("id") or 0), reverse=True)
        runs = runs[:window]
        effective = []
        for r in runs:
            c = r.get("conclusion") or ""
            if c == "startup_failure":
                c = STARTUP
            elif c in RED:
                try:
                    jobs = client.get(
                        f"/repos/{repo}/actions/runs/{r['id']}/jobs",
                        {"filter": "all", "per_page": 1, "page": 1},
                    )
                    if jobs.get("total_count") == 0:
                        c = STARTUP
                except NotFound:
                    pass  # job list unavailable: keep the native conclusion
            effective.append(c)
        row["startup_failures"] = sum(1 for c in effective if c == STARTUP)
        row["window"] = [
            {
                "id": r.get("id"),
                "conclusion": r.get("conclusion") or "UNKNOWN",
                "effective": e or "UNKNOWN",
                "event": r.get("event") or "UNKNOWN",
                "head_sha": r.get("head_sha"),
                "created_at": r.get("created_at"),
            }
            for r, e in zip(runs, effective)
        ]
        cls, red_idx = classify(effective)
        row["class"] = cls
        if row["startup_failures"] and cls != "STARTUP_FAILURE":
            row["flags"].append("STARTUP_FAILURES")
        if cls in RED_CLASSES and red_idx is not None:
            decisive = [r for r, e in zip(runs, effective) if e in RED | GREEN]
            first = decisive[red_idx]
            row["first_red_sha"] = first.get("head_sha")
            row["first_red_run_id"] = first.get("id")
        if runs:
            row["last_run_id"] = runs[0].get("id")
            row["last_run_sha"] = runs[0].get("head_sha")
            row["last_run_created_at"] = runs[0].get("created_at")

        commits = client.get(
            f"/repos/{repo}/commits",
            {"path": path, "sha": branch, "per_page": 1, "page": 1},
        )
        if isinstance(commits, list) and commits:
            c = commits[0]
            row["file_last_commit_sha"] = c.get("sha")
            row["file_last_commit_at"] = (
                (c.get("commit") or {}).get("committer") or {}
            ).get("date")
        if (
            row["file_last_commit_at"]
            and row["last_run_created_at"]
            and row["file_last_commit_at"] > row["last_run_created_at"]
        ):
            row["flags"].append("STALE")
        if body.get("total_count", 0) > 0 and not runs:
            row["flags"].append("ONLY_NON_DEFAULT_EVENTS")
        rows.append(row)

    counts = {c: 0 for c in CLASSES}
    for r in rows:
        counts[r["class"]] += 1
    return {
        "repo": repo,
        "default_branch": branch,
        "head_sha": head_sha,
        "workflows_api_total": wf_total,
        "workflows_fetched": len(workflows),
        "partial": wf_partial,
        "skipped_non_file_workflows": skipped_dynamic,
        "window": window,
        "counts": counts,
        "stale_count": sum(1 for r in rows if "STALE" in r["flags"]),
        "startup_failure_runs": sum(r.get("startup_failures", 0) for r in rows),
        "workflows": rows,
    }


def build_report(client, repos: list[str], window: int = WINDOW, ledger=None) -> dict:
    report = {
        "schema": SCHEMA,
        "source": "GitHub REST actions/workflows + workflow runs (default branch, completed)",
        "note": "Counts are workflow classes, never to be summed with BD roots, queue counts or issues.",
        "repos": [census_repo(client, r, window) for r in sorted(repos)],
    }
    report["partial"] = any(r["partial"] for r in report["repos"])
    if ledger is not None:
        attach_ledger_roots(report, ledger)
    return report


def attach_ledger_roots(report: dict, rows: list[dict]) -> None:
    """Annotate each workflow with the ledger root_ids that cover it (evidence lookup, no minting)."""
    latest = latest_rows(rows)
    for repo_block in report["repos"]:
        for wf in repo_block["workflows"]:
            hits = {}
            for row in latest.values():
                if row["repo"] != repo_block["repo"]:
                    continue
                if any(member_file(m) == wf["path"] for m in row["workflows"]):
                    hits[row["root_id"]] = row["state"]
            wf["ledger_root_ids"] = sorted(hits)
            wf["ledger_root_states"] = {k: hits[k] for k in sorted(hits)}


def dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=True) + "\n"


def markdown_summary(report: dict) -> str:
    lines = ["# RED census", ""]
    if report.get("partial"):
        lines.append("**PARTIAL**: a paginated API total exceeded the fetched count; this is not a complete census.")
        lines.append("")
    for rb in report["repos"]:
        lines.append(f"## {rb['repo']} @ `{(rb['head_sha'] or 'UNKNOWN')[:12]}` ({rb['default_branch']})")
        lines.append("")
        lines.append(
            f"Workflows listed by API: {rb['workflows_api_total']} (fetched {rb['workflows_fetched']}"
            + (", PARTIAL" if rb["partial"] else "")
            + f"); window = last {rb['window']} completed default-branch runs."
        )
        lines.append("")
        lines.append("| Class | Workflows |")
        lines.append("|---|---|")
        for c in CLASSES:
            lines.append(f"| {c} | {rb['counts'][c]} |")
        lines.append(f"| STALE (flag) | {rb['stale_count']} |")
        lines.append(f"| startup-failure runs (excluded) | {rb['startup_failure_runs']} |")
        lines.append("")
        for c in ("EVERRED", "GREEN_TO_RED", "FLAKY", "STARTUP_FAILURE", "GHOST"):
            sel = [w for w in rb["workflows"] if w["class"] == c]
            if not sel:
                continue
            lines.append(f"### {c}")
            lines.append("")
            lines.append("| Workflow | Last run | First red SHA | Flags | Ledger roots |")
            lines.append("|---|---|---|---|---|")
            for w in sel:
                roots = w.get("ledger_root_ids")
                states = w.get("ledger_root_states") or {}
                roots_txt = (
                    ", ".join(f"{r[:12]} {states.get(r, '')}".strip() for r in roots)
                    if roots
                    else ("UNROOTED" if roots is not None else "-")
                )
                lines.append(
                    f"| `{w['path'].rsplit('/', 1)[-1]}` | {w['last_run_id'] or '-'} | "
                    f"{(w['first_red_sha'] or '-')[:12]} | {' '.join(w['flags']) or '-'} | {roots_txt} |"
                )
            lines.append("")
    lines.append("Report-only. GHOST and STARTUP_FAILURE (failed with zero jobs) are never counted as red. "
                 "Do not sum these counts with BD roots.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# BD ledger (append-only, hash-chained)
# ---------------------------------------------------------------------------


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def root_members(repo: str, workflows: list[str]) -> list[str]:
    """Normalized member set: repo-qualified workflow (or step-scoped) paths, sorted, unique."""
    return sorted({f"{repo}:{w}" for w in workflows})


def compute_root_id(repo: str, workflows: list[str]) -> str:
    return sha256_hex(
        canonical({"scope": ROOT_SCOPE, "type": ROOT_TYPE, "members": root_members(repo, workflows)})
    )


def compute_row_hash(row: dict) -> str:
    return sha256_hex(canonical({k: v for k, v in row.items() if k != "row_hash"}))


def member_file(member: str) -> str:
    """'.github/workflows/ci.yml#job/Step' -> '.github/workflows/ci.yml'."""
    return member.split("#", 1)[0]


def members_overlap(a: str, b: str) -> bool:
    """Members overlap when they name the same file and one scope contains the other.

    Scopes: whole file (no '#'), job ('#job-id') or step ('#job-id/Step name').
    A whole-file member covers every job and step of the file; a job member
    covers every step of that job.
    """
    fa, _, sa = a.partition("#")
    fb, _, sb = b.partition("#")
    if fa != fb:
        return False
    if not sa or not sb or sa == sb:
        return True
    ja, jb = sa.split("/", 1)[0], sb.split("/", 1)[0]
    return (sa == ja and ja == jb) or (sb == jb and ja == jb)


def load_ledger(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {n}: invalid JSON: {exc}") from exc
    return rows


def latest_rows(rows: list[dict]) -> dict:
    """Latest row per root_id (append-only: later rows supersede state)."""
    out: dict = {}
    for row in rows:
        out[row.get("root_id")] = row
    return out


def verify_ledger(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    prev = GENESIS
    for i, row in enumerate(rows, 1):
        missing = [k for k in LEDGER_SCHEMA_FIELDS if k not in row]
        if missing:
            errors.append(f"row {i}: missing fields {missing}")
            continue
        if row["state"] not in LEDGER_STATES:
            errors.append(f"row {i}: invalid state {row['state']!r}")
        if not isinstance(row["workflows"], list) or not row["workflows"]:
            errors.append(f"row {i}: workflows must be a non-empty list")
            continue
        if row["prev_hash"] != prev:
            errors.append(f"row {i}: prev_hash does not match previous row_hash (chain broken)")
        expected = compute_row_hash(row)
        if row["row_hash"] != expected:
            errors.append(f"row {i}: row_hash mismatch (row content altered)")
        rid = compute_root_id(row["repo"], row["workflows"])
        if row["root_id"] != rid:
            errors.append(f"row {i}: root_id is not sha256 of scope/type/members ({row['title']})")
        prev = row["row_hash"]

    # No two rows may share a member under different root_ids.
    seen: list[tuple[str, str, int]] = []  # (qualified member, root_id, row number)
    for i, row in enumerate(rows, 1):
        if not isinstance(row.get("workflows"), list):
            continue
        for m in root_members(row.get("repo", ""), row["workflows"]):
            for other, other_root, j in seen:
                if other_root != row.get("root_id") and members_overlap(m, other):
                    errors.append(
                        f"row {i}: member {m} overlaps {other} of row {j} with a different root_id"
                    )
            seen.append((m, row.get("root_id"), i))
    return errors


def append_row(path: Path, entry: dict) -> dict:
    """Single-writer helper: compute root_id/prev_hash/row_hash and append one row."""
    rows = load_ledger(path) if path.exists() else []
    errors = verify_ledger(rows)
    if errors:
        raise ValueError("refusing to append to an invalid ledger: " + "; ".join(errors))
    row = {k: entry[k] for k in ("family", "title", "repo", "workflows", "state", "evidence")}
    for opt in ("note",):
        if opt in entry:
            row[opt] = entry[opt]
    row["workflows"] = sorted(set(row["workflows"]))
    row["root_id"] = compute_root_id(row["repo"], row["workflows"])
    if row["root_id"] in latest_rows(rows) and entry.get("root_id") not in (None, row["root_id"]):
        raise ValueError("root_id mismatch")
    row["prev_hash"] = rows[-1]["row_hash"] if rows else GENESIS
    row["row_hash"] = compute_row_hash(row)
    trial = verify_ledger(rows + [row])
    if trial:
        raise ValueError("append would invalidate ledger: " + "; ".join(trial))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(canonical(row) + "\n")
    return row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("repos", nargs="*", help="owner/repo (e.g. GBOGEB/ABACUS)")
    ap.add_argument("--from-json", type=Path, help="offline: saved REST responses keyed by 'GET path?query'")
    ap.add_argument("--record", type=Path, help="live: also save every REST response to this file")
    ap.add_argument("--out", type=Path, help="deterministic census JSON output")
    ap.add_argument("--summary", type=Path, help="markdown summary (e.g. $GITHUB_STEP_SUMMARY), appended")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--ledger", type=Path, help="annotate workflows with ledger root_ids (read-only)")
    ap.add_argument("--verify-ledger", type=Path, nargs="?", const=Path("ledger/bd_ledger.jsonl"),
                    help="verify hash chain and member uniqueness; exit 1 on error")
    ap.add_argument("--ledger-append", type=Path, metavar="ENTRY_JSON",
                    help="single-writer, local only: append one row (family,title,repo,workflows,state,evidence[,note])")
    args = ap.parse_args(argv)

    if args.verify_ledger is not None and not args.repos and args.ledger_append is None:
        errors = verify_ledger(load_ledger(args.verify_ledger))
        for e in errors:
            print(f"LEDGER ERROR: {e}")
        print("ledger OK" if not errors else f"ledger INVALID ({len(errors)} errors)")
        return 1 if errors else 0

    if args.ledger_append is not None:
        target = args.ledger or Path("ledger/bd_ledger.jsonl")
        row = append_row(target, json.loads(args.ledger_append.read_text(encoding="utf-8")))
        print(row["row_hash"])
        return 0

    if not args.repos:
        ap.error("at least one repo is required for a census")
    if args.from_json:
        client = OfflineClient(json.loads(args.from_json.read_text(encoding="utf-8")))
        record = None
    else:
        record = {} if args.record else None
        client = LiveClient(os.environ.get("GITHUB_TOKEN"), record)
    ledger_rows = load_ledger(args.ledger) if args.ledger else None
    report = build_report(client, args.repos, args.window, ledger_rows)
    payload = dumps(report)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    if record is not None:
        args.record.write_text(dumps(record), encoding="utf-8")
    md = markdown_summary(report)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(md)
    print(sha256_hex(payload), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
