#!/usr/bin/env python3
"""Read-only, evidence-producing ABACUS issue mission for CODEX MissionControl.

The ABACUS-local runner owns source truth. CODEX may consume receipts but cannot
grant remote mutation, security review or engineering acceptance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import io
import json
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

REPO = "GBOGEB/ABACUS"
SHA = re.compile(r"^[0-9a-f]{40}$")
ROOT_LINKS = re.compile(r"Broken internal links\s*\|\s*(\d+)", re.I)
ROOT_MISSING = re.compile(r"Missing dashboards\s*\|\s*(\d+)", re.I)
# Paths are candidate ownership boundaries, NOT proven failing source files.
LOCKS = {
    1929: "scripts/bd_ldab_join_census.py",
    1861: "ci/governance/pr_feedback_gate.py",
    1862: "ci/governance/pr_feedback_gate.py",
    1878: "ci/governance/pr_feedback_gate.py",
    1879: "ci/governance/pr_feedback_gate.py",
}
API = "https://api.github.com"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def github_get(path, token):
    if not token:
        raise ValueError("read-only GitHub token required for live evidence")
    if not path.startswith("/repos/" + REPO + "/"):
        raise ValueError("GitHub endpoint outside authorized repository")
    connection = http.client.HTTPSConnection("api.github.com", timeout=25)
    try:
        connection.request(
            "GET",
            path,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ABACUS-MissionControl-Issue-Burndown",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"GitHub API HTTP {response.status}")
        return json.loads(response.read()), response.getheader("Link", "")
    finally:
        connection.close()


def next_link(link):
    for part in link.split(","):
        match = re.search(r'<([^>]+)>;\s*rel="next"', part)
        if match:
            url = match.group(1)
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "https" or parsed.netloc != "api.github.com":
                raise ValueError("untrusted GitHub pagination target")
            return parsed.path + ("?" + parsed.query if parsed.query else "")
    return None


def list_open_issues(token):
    path = "/repos/" + REPO + "/issues?state=open&per_page=100"
    issues, visited = [], set()
    for _ in range(20):
        if path in visited:
            raise ValueError("pagination cycle")
        visited.add(path)
        page, link = github_get(path, token)
        if not isinstance(page, list):
            raise ValueError("issues API returned non-list")
        issues += [x for x in page if not x.get("pull_request")]
        path = next_link(link)
        if not path:
            return issues
    raise ValueError("issue census truncated: 20 pages exceeded")


def latest_dashboard_bot_comment(number, token):
    """Read the newest count-bearing Actions comment; never trust user comments."""
    path = f"/repos/{REPO}/issues/{number}/comments?per_page=100"
    visited = set()
    latest = None
    for _ in range(20):
        if path in visited:
            raise ValueError("dashboard comment pagination cycle")
        visited.add(path)
        comments, link = github_get(path, token)
        if not isinstance(comments, list):
            raise ValueError("dashboard comments API returned non-list")
        for comment in comments:
            author = comment.get("user") or {}
            body = comment.get("body") or ""
            if (
                author.get("login") == "github-actions[bot]"
                and body.startswith("## 🚨 Dashboard Health Check Failed")
                and ROOT_LINKS.search(body)
                and ROOT_MISSING.search(body)
            ):
                latest = {
                    "body": body,
                    "id": comment.get("id"),
                    "created_at": comment.get("created_at"),
                }
        path = next_link(link)
        if not path:
            return latest
    raise ValueError("dashboard comment census truncated")


def collect_live(token):
    branch, _ = github_get("/repos/" + REPO + "/branches/main", token)
    main = branch["commit"]["sha"]
    runs, _ = github_get(
        "/repos/" + REPO + "/actions/runs?head_sha=" + main + "&per_page=100", token
    )
    issues = list_open_issues(token)
    for issue in issues:
        if "dashboard health check failure" in issue["title"].lower():
            comment = latest_dashboard_bot_comment(issue["number"], token)
            if comment is not None:
                issue["latest_dashboard_comment"] = comment
    return {
        "repository": REPO,
        "main_sha": main,
        "protected": branch.get("protected"),
        "issues": issues,
        "runs": runs.get("workflow_runs", []),
        "run_sample_truncated": runs.get("total_count", 0)
        > len(runs.get("workflow_runs", [])),
        "observation": "GITHUB_API",
    }


def evidence_route(issue):
    n = issue["number"]
    title = issue["title"].lower()
    body = (issue.get("body") or "").lower()
    words = title + " " + body[:1600]
    if "dashboard health check failure" in title:
        return "INCIDENT_DASHBOARD", "REPAIR_FIRST_RED", "P1"
    if n in (1860, 1944, 1846, 1738) or any(
        v in title for v in ("security", "semgrep", "bandit", "ghas")
    ):
        return "SECURITY_ADMISSION", "REVIEW_AND_REPAIR", "P0"
    if any(
        v in title
        for v in ("first red", "first-red", "false-green", "failed", "ci:", "gate:")
    ):
        return "CI_FIRST_RED", "REPAIR_FIRST_RED", "P1"
    if n in (633, 635, 636, 637, 1313):
        return "EXTERNAL_PROOF", "REQUEST_AND_VERIFY", "P1"
    if n in (1929, 1877, 1660, 1609, 1488, 1566):
        return "DEBT_CENSUS", "MEASURE_AND_REPAIR", "P1"
    if any(
        v in words for v in ("integrat", "federat", "bridge", "semantic", "runtime")
    ):
        return "INTEGRATION", "REPLAY_CONTRACT", "P2"
    return "PROCESS_CONTROL", "PROVE_OR_MONITOR", "P2"


def classify(issues, head):
    seen = set()
    rows = []
    dashboard = defaultdict(list)
    for item in issues:
        if not isinstance(item, dict) or item.get("state") != "open":
            raise ValueError("open issue row required")
        n = item.get("number")
        if type(n) is not int or n <= 0 or n in seen:
            raise ValueError("invalid or duplicate issue number")
        seen.add(n)
        url = item.get("html_url", "")
        if url != f"https://github.com/{REPO}/issues/{n}":
            raise ValueError("issue link does not match canonical repository")
        category, route, priority = evidence_route(item)
        body = item.get("body") or ""
        latest = item.get("latest_dashboard_comment")
        source = "ISSUE_BODY"
        if category == "INCIDENT_DASHBOARD" and latest is not None:
            if not isinstance(latest, dict) or not isinstance(latest.get("body"), str):
                raise ValueError("invalid dashboard comment observation")
            body = latest["body"]
            source = "DASHBOARD_BOT_COMMENT"
        signature = None
        if category == "INCIDENT_DASHBOARD":
            broken, missing = ROOT_LINKS.search(body), ROOT_MISSING.search(body)
            signature = (
                "DASHBOARD_LINK_COUNTS:"
                + (broken.group(1) if broken else "UNKNOWN")
                + ":"
                + (missing.group(1) if missing else "UNKNOWN")
            )
            dashboard[signature].append(n)
        lock = (
            ".github/workflows/dashboard-health.yml"
            if category == "INCIDENT_DASHBOARD"
            else LOCKS.get(n)
        )
        rows.append(
            {
                "id": f"ABACUS-ISSUE-{n}",
                "number": n,
                "title": item["title"],
                "url": url,
                "updated_at": item.get("updated_at"),
                "category": category,
                "route": route,
                "priority": priority,
                "root_candidate": signature,
                "file_lock_candidate": lock,
                "root_verified": False,
                "fix_verified": False,
                "source_class": source,
                "latest_dashboard_comment_id": (
                    latest.get("id") if source == "DASHBOARD_BOT_COMMENT" else None
                ),
                "target_main_sha": head,
                "disposition": "OPEN_UNPROVEN",
            }
        )
    for row in rows:
        if row["category"] == "INCIDENT_DASHBOARD":
            cohort = dashboard[row["root_candidate"]]
            row["cohort_issues"] = sorted(cohort)
            row["possible_duplicate"] = len(cohort) > 1
            # Identical counts are not proof of identical broken paths.
    return sorted(rows, key=lambda r: (r["priority"], r["number"]))


def plan_workers(rows, head):
    locks = defaultdict(list)
    unscoped = []
    for row in rows:
        lock = row["file_lock_candidate"]
        if lock:
            locks[lock].append(row)
        else:
            unscoped.append(row["number"])
    packets = []
    for i, path in enumerate(sorted(locks), 1):
        group = locks[path]
        packets.append(
            {
                "packet_id": f"ABACUS-MC-W{i:02d}",
                "repo": REPO,
                "expected_main_sha": head,
                "owner_lock": path,
                "issues": sorted(x["number"] for x in group),
                "routes": sorted(set(x["route"] for x in group)),
                "state": "STAGED_NOT_LAUNCHED",
                "dispatch_authorized": False,
                "worker_run_id": None,
                "repair_commit_sha": None,
                "test_run_id": None,
                "admission": "HOLD",
                "next_action": "Reproduce exact-current-main first-red; confirm file ownership and non-overlap before approved ABACUS-local execution.",
            }
        )
    return packets, sorted(unscoped)


def build(envelope):
    if envelope.get("repository") != REPO:
        raise ValueError("wrong repository authority")
    head = envelope.get("main_sha", "")
    if not SHA.fullmatch(head):
        raise ValueError("full 40-character main SHA required")
    if type(envelope.get("protected")) is not bool:
        raise ValueError("branch protection must be observed, not guessed")
    issues = envelope.get("issues")
    runs = envelope.get("runs")
    if not isinstance(issues, list) or not isinstance(runs, list):
        raise ValueError("issues and runs lists required")
    rows = classify(issues, head)
    packets, unscoped = plan_workers(rows, head)
    current_runs = [r for r in runs if r.get("head_sha") == head]
    results = Counter(
        str(r.get("conclusion") or r.get("status") or "UNKNOWN") for r in current_runs
    )
    categories = dict(sorted(Counter(r["category"] for r in rows).items()))
    dashboard_cohorts = {}
    for row in rows:
        if row["root_candidate"]:
            dashboard_cohorts.setdefault(row["root_candidate"], []).append(
                row["number"]
            )
    evidence = {
        "schema": "abacus.missioncontrol.issue_burndown.v1",
        "authority": {
            "repository": REPO,
            "main_sha": head,
            "main_protected": envelope["protected"],
            "remote_mutation_authorized": False,
            "security_waiver": False,
            "formal_credit_delta": 0,
        },
        "observation": envelope.get("observation", "FIXTURE"),
        "counts": {
            "open_issues": len(rows),
            "category_counts": categories,
            "dashboard_incidents": categories.get("INCIDENT_DASHBOARD", 0),
            "proven_fixes": 0,
            "issues_closed_by_mission": 0,
            "worker_packets_staged": len(packets),
            "worker_packets_launched": 0,
            "unscoped_issues": len(unscoped),
        },
        "current_main_workflows": {
            "observed": len(current_runs),
            "sample_truncated": bool(envelope.get("run_sample_truncated", False)),
            "status_counts": dict(sorted(results.items())),
            "not_a_required_checks_certificate": True,
        },
        "dashboard_cohorts_by_count_only": dict(sorted(dashboard_cohorts.items())),
        "issues": rows,
        "unscoped_issue_numbers": unscoped,
    }
    plan = {
        "schema": "abacus.missioncontrol.worker_plan.v1",
        "source_repo": REPO,
        "source_main_sha": head,
        "mode": "PLAN_ONLY",
        "mutation_enabled": False,
        "requires": [
            "ABACUS-local authenticated executor",
            "exact-head refresh",
            "nonoverlapping paths",
            "owner-approved action allowlist",
            "dry-run and negative tests",
            "terminal CI/security",
            "independent code/security review",
            "protected default branch",
        ],
        "packets": packets,
    }
    return evidence, plan


def emit(envelope, out):
    evidence, plan = build(envelope)
    out.mkdir(parents=True, exist_ok=True)
    headers = [
        "number",
        "priority",
        "category",
        "route",
        "file_lock_candidate",
        "root_candidate",
        "disposition",
        "url",
    ]
    buffer = io.StringIO(newline="")
    w = csv.DictWriter(
        buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n"
    )
    w.writeheader()
    for row in evidence["issues"]:
        w.writerow(row)
    counts = evidence["counts"]
    summary = [
        "# ABACUS — MissionControl horizontal issue burndown",
        "",
        f"- Source main: `{evidence['authority']['main_sha']}`",
        f"- Effective protected flag: `{evidence['authority']['main_protected']}`",
        f"- Open issues: **{counts['open_issues']}**",
        f"- Dashboard incidents: **{counts['dashboard_incidents']}** (same counts are not proof of duplicate root)",
        f"- Staged disjoint candidate locks: **{counts['worker_packets_staged']}**",
        f"- Unscoped issues requiring owner/path investigation: **{counts['unscoped_issues']}**",
        "- Worker executions, repair commits, independent reviews and verified closes: **0 credited**",
        "- Dispatch: **DENIED** pending ABACUS-local authorized executor and governed admission",
        "",
        "| Category | Open |",
        "|---|---:|",
    ]
    summary += [f"| {k} | {v} |" for k, v in counts["category_counts"].items()]
    summary += ["", "## Work packets"]
    for packet in plan["packets"]:
        summary.append(
            f"- {packet['packet_id']} — `{packet['owner_lock']}` "
            f"issues {packet['issues']}; STAGED only"
        )
    summary.append("")
    payloads = {
        "issue_census.json": json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        "work_packets.json": json.dumps(plan, indent=2, sort_keys=True) + "\n",
        "burndown.csv": buffer.getvalue(),
        "mission_summary.md": "\n".join(summary) + "\n",
    }
    for name, content in payloads.items():
        (out / name).write_bytes(content.encode("utf-8"))
    manifest = {
        "schema": "abacus.missioncontrol.issue_burndown.manifest.v1",
        "repository": REPO,
        "main_sha": evidence["authority"]["main_sha"],
        "sha256": {name: sha256(data) for name, data in sorted(payloads.items())},
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return evidence, plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture", type=Path, help="offline complete GitHub API observation envelope"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    envelope = (
        json.loads(args.fixture.read_text(encoding="utf-8"))
        if args.fixture
        else collect_live(os.environ.get("GITHUB_TOKEN", ""))
    )
    evidence, plan = emit(envelope, args.out)
    print(
        canonical(
            {
                "main_sha": evidence["authority"]["main_sha"],
                "open_issues": evidence["counts"]["open_issues"],
                "staged": len(plan["packets"]),
                "executed": 0,
                "security_waiver": False,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        print(f"mission burndown failed closed: {exc}", file=sys.stderr)
        sys.exit(2)
