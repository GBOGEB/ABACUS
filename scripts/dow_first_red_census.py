"""Produce source-bound DOW pre-commit failure receipts without relaxing admission.

Consumes one exact GitHub Actions step log and workflow YAML. This is an
observation/census producer, not a repair, waiver, review or merge authority.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ANSI = re.compile(r"\x1b\[[0-9;]*m")
PREFIX = re.compile(r"^\d{4}-\d\d-\d\dT[^ ]+Z ")
HOOK = re.compile(r"^(?P<label>.*?)\.{3,}(?P<result>Passed|Failed|Skipped)\s*$")
HOOK_ID = re.compile(r"^- hook id:\s*(?P<id>\S+)")
FIXING = re.compile(r"^(?:Fixing|Rewriting)\s+(.+?)\s*$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def clean_line(raw: str) -> str:
    return PREFIX.sub("", ANSI.sub("", raw)).strip()


def downstream_jobs(jobs: dict[str, Any], source: str) -> list[dict[str, str]]:
    """Report potential dependency reach, not inferred skipped/executed jobs."""
    if source not in jobs:
        raise ValueError(f"Unknown source job: {source}")
    edges: dict[str, set[str]] = defaultdict(set)
    for name, spec in jobs.items():
        dependencies = spec.get("needs", [])
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        for need in dependencies:
            if need not in jobs:
                raise ValueError(f"Unknown dependency {need!r} in {name!r}")
            edges[need].add(name)
    visited: set[str] = set()
    frontier = [source]
    while frontier:
        next_job = frontier.pop(0)
        for target in sorted(edges[next_job]):
            if target not in visited:
                visited.add(target)
                frontier.append(target)
    return [{"job_id": name, "job_name": str(jobs[name].get("name", name))}
            for name in sorted(visited)]


def census(log: str, workflow: str, *, source_sha: str, run_id: str,
           run_attempt: str) -> dict[str, Any]:
    if not SHA.fullmatch(source_sha):
        raise ValueError("Expected a full 40-character source SHA")
    document = yaml.safe_load(workflow)
    jobs = document["jobs"]
    observations: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    hooks_seen = 0
    for raw in log.splitlines():
        line = clean_line(raw)
        status = HOOK.match(line)
        if status:
            hooks_seen += 1
            if current is not None and current["result"] == "Failed":
                observations.append(current)
            current = {"label": status.group("label").strip(),
                       "result": status.group("result"), "hook_id": None,
                       "modified_files": []}
            continue
        if current is None:
            continue
        ident = HOOK_ID.match(line)
        if ident:
            current["hook_id"] = ident.group("id")
        changed = FIXING.match(line)
        if changed and current["result"] == "Failed":
            current["modified_files"].append(changed.group(1))
    if current is not None and current["result"] == "Failed":
        observations.append(current)
    # Preserve UNKNOWN when an empty/incomplete log cannot establish zero failures.
    complete = hooks_seen > 0
    for item in observations:
        item["modified_files"] = sorted(set(item["modified_files"]))
    descendants = downstream_jobs(jobs, "lint-and-validate")
    return {
        "schema": "abacus.dow.precommit.census.v1",
        "source": {"sha": source_sha, "run_id": run_id,
                   "run_attempt": run_attempt},
        "producer": "scripts/dow_first_red_census.py",
        "observation": {
            "status": "PARSED" if complete else "UNKNOWN_INCOMPLETE_LOG",
            "hooks_seen": hooks_seen,
            "failed_hook_signatures": len(observations) if complete else None,
            "first_red": observations[0]["hook_id"] if observations else None,
            "failed_hooks": observations,
            "unique_modified_files": len({p for o in observations
                                          for p in o["modified_files"]}) if complete else None,
        },
        "graph": {"upstream_job": "lint-and-validate",
                  "potentially_downstream": descendants,
                  "potential_downstream_count": len(descendants),
                  "observed_downstream_skipped": None},
        "admission": {"merge_authorized": False, "waiver": False,
                      "crew_launch_verified": None, "root_cause_closed_count": None},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = census(args.log.read_text(encoding="utf-8", errors="replace"),
                    args.workflow.read_text(encoding="utf-8"),
                    source_sha=os.environ["DOW_SOURCE_SHA"],
                    run_id=os.environ["DOW_RUN_ID"],
                    run_attempt=os.environ["DOW_RUN_ATTEMPT"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": report["observation"]["status"],
                      "failed_hooks": report["observation"]["failed_hook_signatures"],
                      "potential_downstream_count": report["graph"]["potential_downstream_count"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
