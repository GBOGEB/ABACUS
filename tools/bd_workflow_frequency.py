#!/usr/bin/env python3
"""Measure workflow-frequency amplification from GitHub Actions run metadata.

This is an operational BD signal only. It does not grant engineering, release,
compliance, or negotiation credit.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"

def api_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))

def fetch_runs(repo: str, token: str, limit: int) -> list[dict]:
    runs: list[dict] = []
    pages = max(1, (limit + 99) // 100)
    for page in range(1, pages + 1):
        payload = api_json(
            f"{API}/repos/{repo}/actions/runs?per_page=100&page={page}", token
        )
        batch = payload.get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100 or len(runs) >= limit:
            break
    return runs[:limit]

def parse_family(value: str) -> tuple[str, list[str]]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("family must be NAME=path1,path2")
    name, raw_paths = value.split("=", 1)
    paths = [p.strip() for p in raw_paths.split(",") if p.strip()]
    if not name.strip() or not paths:
        raise argparse.ArgumentTypeError("family requires a name and >=1 path")
    return name.strip(), paths

def ratio(num: int, den: int) -> float:
    return round(num / den, 6) if den else 0.0

def metrics_for_family(name: str, paths: list[str], runs: list[dict]) -> dict:
    selected = [r for r in runs if r.get("path") in paths]
    total = len(selected)
    input_tuples = {
        (
            r.get("path") or "",
            r.get("event") or "",
            r.get("head_sha") or "",
            r.get("head_branch") or "",
        )
        for r in selected
    }
    workflow_sha = {
        (r.get("path") or "", r.get("head_sha") or "")
        for r in selected
        if r.get("head_sha")
    }
    family_shas = {r.get("head_sha") for r in selected if r.get("head_sha")}
    skipped = sum(1 for r in selected if r.get("conclusion") == "skipped")
    per_workflow = []
    for path in paths:
        rows = [r for r in selected if r.get("path") == path]
        conclusions = Counter((r.get("conclusion") or "unknown") for r in rows)
        unique_sha = {r.get("head_sha") for r in rows if r.get("head_sha")}
        per_workflow.append(
            {
                "path": path,
                "invocations": len(rows),
                "unique_head_shas": len(unique_sha),
                "same_sha_repeat_invocations": max(0, len(rows) - len(unique_sha)),
                "same_sha_repeat_rate": ratio(
                    max(0, len(rows) - len(unique_sha)), len(rows)
                ),
                "conclusions": dict(sorted(conclusions.items())),
                "latest_run_number": max(
                    (int(r.get("run_number") or 0) for r in rows), default=0
                ),
            }
        )
    same_sha_repeat_invocations = max(0, total - len(workflow_sha))
    family_sha_fanout_invocations = max(0, total - len(family_shas))
    unique_input_count = len(input_tuples)
    return {
        "family": name,
        "workflow_paths": paths,
        "total_invocations": total,
        "unique_input_tuples": unique_input_count,
        "unique_input_tuple_ratio": ratio(unique_input_count, total),
        "invocations_per_unique_input": round(total / unique_input_count, 6)
        if unique_input_count
        else 0.0,
        "observable_noop_invocations": skipped,
        "observable_noop_rate": ratio(skipped, total),
        "same_sha_repeat_invocations": same_sha_repeat_invocations,
        "same_sha_repeat_rate": ratio(same_sha_repeat_invocations, total),
        "family_sha_fanout_invocations": family_sha_fanout_invocations,
        "family_sha_fanout_rate": ratio(family_sha_fanout_invocations, total),
        "per_workflow": per_workflow,
    }

def render_markdown(payload: dict) -> str:
    lines = [
        "# BD Workflow Frequency Telemetry",
        "",
        f"- Repository: `{payload['repository']}`",
        f"- Sampled runs: **{payload['sampled_runs']}**",
        f"- Generated: `{payload['generated_at']}`",
        "",
        "| Family | Invocations | Unique input ratio | Observable no-op | Same-SHA repeat | Family SHA fan-out |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for fam in payload["families"]:
        lines.append(
            "| {family} | {total_invocations} | {unique_input_tuple_ratio:.1%} | "
            "{observable_noop_rate:.1%} | {same_sha_repeat_rate:.1%} | "
            "{family_sha_fanout_rate:.1%} |".format(**fam)
        )
    lines += [
        "",
        "## Measurement contract",
        "",
        "- `input tuple` = `(workflow_path, event, head_sha, head_branch)` from GitHub run metadata.",
        "- `observable no-op` = GitHub run conclusion `skipped`; a successful semantic no-op is not inferred.",
        "- `same-SHA repeat` = repeated invocation of the same workflow path on the same head SHA.",
        "- `family SHA fan-out` = invocations beyond one run per distinct head SHA across the configured family.",
        "- Metrics are operational BD evidence only; they do not grant engineering or release credit.",
        "",
    ]
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--family", action="append", type=parse_family, required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    if not args.repo or "/" not in args.repo:
        raise SystemExit("--repo or GITHUB_REPOSITORY must be owner/name")
    if not 1 <= args.limit <= 1000:
        raise SystemExit("--limit must be between 1 and 1000")
    runs = fetch_runs(args.repo, token, args.limit)
    payload = {
        "schema_version": "1.0",
        "repository": args.repo,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sampled_runs": len(runs),
        "measurement_contract": {
            "input_tuple": ["workflow_path", "event", "head_sha", "head_branch"],
            "observable_noop": "conclusion == skipped",
            "same_sha_repeat": "repeat of (workflow_path, head_sha)",
            "family_sha_fanout": "runs beyond one per distinct head_sha in family",
            "authority": "operational_bd_only",
        },
        "families": [
            metrics_for_family(name, paths, runs) for name, paths in args.family
        ],
    }
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(render_markdown(payload))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
