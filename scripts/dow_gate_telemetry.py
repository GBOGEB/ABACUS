"""Read-only exact-SHA DOW remaining-gates and dependency-impact census.

The input directory contains native GitHub API response snapshots collected by CI.
Absence, pagination gaps, skipped jobs and unmatched SHA are never zero/PASS.
Existing EVERRED, LDAB, coverage, REX and BD producers remain authoritative.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import deque
from pathlib import Path
from typing import Any

import yaml

SHA = re.compile(r"^[0-9a-f]{40}$")
DOW_NAME = "DOW + Recursive DMAIC - Unified CD Pipeline"
REQUIRED_SECURITY = (
    "Security Scan — Ruff", "Semgrep", "OSV-Scanner", "DELTA_1 CodeQL",
)
GATE_WORKFLOWS = {
    "full_ci": ("CI/CD Test Suite",),
    "security": REQUIRED_SECURITY,
    "canonical_b0_producer": ("MIP B0 Test Admission and Coverage Evidence",),
    "python_matrix": ("CI - ABACUS Matrix",),
}
STATUS = {
    "success": "PASS",
    "failure": "FAIL",
    "timed_out": "FAIL",
    "action_required": "HOLD",
    "cancelled": "CANCELLED",
    "skipped": "SKIPPED",
    "neutral": "NEUTRAL",
    "queued": "QUEUED",
    "waiting": "QUEUED",
    "requested": "QUEUED",
    "pending": "QUEUED",
    "in_progress": "RUNNING",
}
DOW_JOB_LABELS = {
    "lint-and-validate": "Full repository lint / TestPilot",
    "ci-ubuntu": "DOW Ubuntu",
    "ci-rhel-8": "DOW RHEL 8",
    "ci-rhel-9": "DOW RHEL 9",
    "dmaic-full-cycle": "DMAIC full cycle",
    "build-artifacts": "DMAIC artifact build",
    "release": "Version-tag release",
}


def require_sha(value: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("A full lowercase 40-character SHA is required")
    return value


def load(directory: Path, name: str) -> dict[str, Any] | None:
    path = directory / name
    if not path.is_file():
        return None
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(name + " is not a JSON object")
    return result


def run_state(run: dict[str, Any]) -> str:
    state = run.get("status")
    if state == "completed":
        return STATUS.get(run.get("conclusion"), "UNKNOWN")
    return STATUS.get(state, "UNKNOWN")


def select_runs(payload: dict[str, Any] | None, sha: str) -> tuple[dict[str, dict], bool]:
    """Choose newest native run by identity; missing pages cannot prove absence."""
    if payload is None:
        return {}, False
    rows = payload.get("workflow_runs")
    total = payload.get("total_count")
    if not isinstance(rows, list) or type(total) is not int or total < 0:
        raise ValueError("Workflow run pagination / denominator invalid")
    if total < len(rows) and payload.get("source_complete") is not False:
        raise ValueError("Workflow run pagination / denominator invalid")
    good: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed workflow run")
        if row.get("head_sha") != sha:
            raise ValueError("Mixed-SHA workflow run in exact-head census")
        name = row.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Workflow identity absent")
        if type(row.get("id")) is not int or type(row.get("run_attempt", 1)) is not int:
            raise ValueError("Run ID or attempt absent")
        if not str(row.get("html_url", "")).startswith("https://github.com/"):
            raise ValueError("Native workflow URL absent")
        old = good.get(name)
        rank = (row.get("created_at", ""), row["id"], row.get("run_attempt", 1))
        if old is None or rank > (
            old.get("created_at", ""), old["id"], old.get("run_attempt", 1)
        ):
            good[name] = row
    return good, payload.get("source_complete") is not False and len(rows) == total


def workflow_gate(runs: dict[str, dict], names: tuple[str, ...],
                  complete: bool) -> dict[str, Any]:
    selected = [runs.get(name) for name in names]
    found = [row for row in selected if row is not None]
    states = [run_state(row) for row in found]
    if "FAIL" in states:
        status = "FAIL"
    elif "HOLD" in states:
        status = "HOLD"
    elif "RUNNING" in states or "QUEUED" in states:
        status = "NONTERMINAL"
    elif len(found) == len(names) and all(s == "PASS" for s in states):
        status = "PASS"
    elif len(found) < len(names):
        status = "UNKNOWN" if not complete else "NOT_OBSERVED"
    elif any(s in ("SKIPPED", "CANCELLED", "NEUTRAL") for s in states):
        status = "NOT_PROVED"
    else:
        status = "UNKNOWN"
    return {
        "status": status, "required": list(names), "observed_count": len(found),
        "required_count": len(names),
        "native_runs": [{
            "name": row["name"], "run_id": row["id"],
            "run_attempt": row.get("run_attempt", 1),
            "status": run_state(row), "url": row["html_url"],
            "sha": row["head_sha"],
        } for row in found],
    }


def workflow_dag(source: str) -> dict[str, dict]:
    document = yaml.safe_load(source)
    if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
        raise ValueError("DOW workflow jobs absent")
    jobs = document["jobs"]
    dag: dict[str, dict] = {}
    for name, spec in jobs.items():
        if not isinstance(spec, dict):
            raise ValueError("Malformed job " + name)
        needs = spec.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        if not isinstance(needs, list) or any(n not in jobs for n in needs):
            raise ValueError("Unknown workflow dependency")
        dag[name] = {"name": spec.get("name", name), "needs": needs}
    for target in dag:
        visited = set()
        work = deque(dag[target]["needs"])
        while work:
            item = work.popleft()
            if item == target:
                raise ValueError("Cycle in DOW dependency graph")
            if item in visited:
                continue
            visited.add(item)
            work.extend(dag[item]["needs"])
    return dag


def affected(dag: dict[str, dict], source: str) -> list[str]:
    if source not in dag:
        raise ValueError("Unknown DOW job: " + source)
    result: set[str] = set()
    queue = deque([source])
    while queue:
        key = queue.popleft()
        for name, spec in dag.items():
            if key in spec["needs"] and name not in result:
                result.add(name)
                queue.append(name)
    return sorted(result)


def job_census(payload: dict[str, Any] | None, run: dict | None,
               dag: dict[str, dict]) -> dict[str, Any]:
    if run is None or payload is None:
        return {"jobs": {name: {"status": "UNKNOWN", "job_id": None,
                 "url": None, "needs": spec["needs"],
                 "downstream_count": len(affected(dag, name)),
                 "downstream": affected(dag, name)}
                 for name, spec in dag.items()}, "completeness": "UNKNOWN"}
    rows = payload.get("jobs")
    total = payload.get("total_count")
    if not isinstance(rows, list) or type(total) is not int or total < 0:
        raise ValueError("DOW job census has invalid denominator")
    if total < len(rows) and payload.get("source_complete") is not False:
        raise ValueError("DOW job census has invalid denominator")
    chosen: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            raise ValueError("Invalid job ID")
        if row.get("run_id") not in (None, run["id"]):
            raise ValueError("Foreign run job in DOW census")
        name = row.get("name")
        if not isinstance(name, str):
            raise ValueError("Unnamed job")
        current = chosen.get(name)
        if current is None or row["id"] > current["id"]:
            chosen[name] = row
    complete = payload.get("source_complete") is not False and total == len(rows)
    # The API's page can be complete while GitHub has not instantiated jobs.
    # A queued workflow is not evidence that unlisted dependent jobs are absent.
    terminal_run = run_state(run) in {"PASS", "FAIL", "SKIPPED", "CANCELLED"}
    result = {}
    for key, spec in dag.items():
        row = chosen.get(spec["name"])
        result[key] = {
            "status": run_state(row) if row else (
                "NOT_OBSERVED" if complete and terminal_run else "UNKNOWN"
            ),
            "job_id": row["id"] if row else None,
            "url": row.get("html_url") if row else None,
            "needs": spec["needs"],
            "downstream_count": len(affected(dag, key)),
            "downstream": affected(dag, key),
        }
    return {"jobs": result, "completeness": "COMPLETE" if complete else "PARTIAL"}


def coverage(data: dict[str, Any] | None, sha: str, kind: str,
             base_sha: str | None = None) -> dict[str, Any]:
    if data is None:
        return {"status": "UNKNOWN", "numerator": None, "denominator": None}
    rows = data.get("receipts")
    if not isinstance(rows, list):
        raise ValueError("Coverage evidence receipts must be a list")
    matches = [r for r in rows if r.get("sha") == sha and r.get("kind") == kind]
    if kind == "diff":
        matches = [r for r in matches if r.get("base_sha") == base_sha]
    if len(matches) != 1:
        return {"status": "UNKNOWN", "numerator": None, "denominator": None}
    receipt = matches[0]
    num, den = receipt.get("covered"), receipt.get("eligible")
    if (type(num) is not int or type(den) is not int
            or den <= 0 or not 0 <= num <= den
            or not all(receipt.get(k) for k in ("scope_id", "config_sha256",
                                                "run_id", "artifact_id"))):
        raise ValueError("Coverage receipt has invalid units or provenance")
    return {"status": "MEASURED", "numerator": num, "denominator": den,
            "percent": round(100 * num / den, 6),
            "scope_id": receipt["scope_id"],
            "config_sha256": receipt["config_sha256"],
            "run_id": receipt["run_id"], "artifact_id": receipt["artifact_id"]}


def build(*, main_sha: str, head_sha: str, main_branch: dict | None,
          main_runs: dict | None, head_runs: dict | None,
          dow_jobs: dict | None, workflow: str,
          coverage_data: dict | None = None) -> dict[str, Any]:
    require_sha(main_sha)
    require_sha(head_sha)
    if main_branch is not None and main_branch.get("commit", {}).get("sha") != main_sha:
        raise ValueError("Main ref drift: branch and requested SHA differ")
    dag = workflow_dag(workflow)
    main_index, main_complete = select_runs(main_runs, main_sha)
    head_index, head_complete = select_runs(head_runs, head_sha)
    dow_run = main_index.get(DOW_NAME)
    jobs = job_census(dow_jobs, dow_run, dag)
    gates = {key: workflow_gate(head_index, names, head_complete)
             for key, names in GATE_WORKFLOWS.items()}
    for key in dag:
        gates[key] = jobs["jobs"][key]
    for gate, sha, kind, base in (
        ("canonical_main_coverage", main_sha, "canonical", None),
        ("changed_line_coverage", head_sha, "diff", main_sha),
    ):
        gates[gate] = coverage(coverage_data, sha, kind, base)
    gates["bd_distinct_roots"] = {"status": "UNKNOWN", "opened": None,
                                  "closed": None, "reopened": None,
                                  "reason": "Needs exact-source native BD/LDAB/REX root receipts"}
    gates["crew_ldb_rex"] = {"status": "UNKNOWN", "authenticated_launches": None,
                             "accepted_returns": None, "debug_sessions": None,
                             "reason": "No authenticated joined execution input"}
    gates["governance_owner"] = {
        "status": "DEFERRED_OWNER_ACTION",
        "protected_observed": main_branch.get("protected") if main_branch else None,
        "independent_review": None, "rule_change": False,
    }
    leverage = sorted(
        ({"job_id": key, "name": DOW_JOB_LABELS.get(key, key),
          "status": jobs["jobs"][key]["status"],
          "potential_descendants": jobs["jobs"][key]["downstream_count"]}
         for key in dag if jobs["jobs"][key]["downstream_count"] > 0),
        key=lambda r: (-r["potential_descendants"], r["job_id"]),
    )
    measured = sum(1 for x in gates.values()
                   if x["status"] not in ("UNKNOWN", "NOT_OBSERVED"))
    return {
        "schema": "abacus.dow.remaining-gates.v1",
        "authority": "READ_ONLY_DIAGNOSTIC_NO_MERGE_CREDIT",
        "source": {"repo": "GBOGEB/ABACUS", "main_sha": main_sha,
                   "head_sha": head_sha, "main_branch_verified": main_branch is not None,
                   "main_run_census_complete": main_complete,
                   "head_run_census_complete": head_complete,
                   "dow_job_census": jobs["completeness"],
                   "dow_run_id": dow_run["id"] if dow_run else None,
                   "dow_run_url": dow_run["html_url"] if dow_run else None},
        "gates": gates, "critical_nodes": leverage,
        "observation_completeness": {
            "observed_gate_count": measured, "total_gate_count": len(gates),
            "ratio": round(measured / len(gates), 4),
            "unknown_gate_count": len(gates) - measured,
            "meaning": "Evidence classification only; not a pass rate",
        },
        "admission": {"merge_authorized": False, "release_authorized": False,
                      "review_satisfied": None},
    }


def markdown(report: dict[str, Any]) -> str:
    lines = ["# DOW remaining-gates telemetry", "",
             "READ ONLY. No admission, merge, worker or security approval.",
             "", "Main: " + report["source"]["main_sha"],
             "PR head: " + report["source"]["head_sha"], "",
             "| Gate | Status | Measured detail |",
             "| --- | --- | --- |"]
    for key, gate in report["gates"].items():
        details = []
        if gate.get("job_id") is not None:
            details.append("job " + str(gate["job_id"]))
        if gate.get("denominator") is not None:
            details.append(str(gate["numerator"]) + "/" + str(gate["denominator"]))
        if gate.get("closed") is not None:
            details.append("closed roots " + str(gate["closed"]))
        if gate.get("downstream_count"):
            details.append("potential descendants " + str(gate["downstream_count"]))
        lines.append("| " + key + " | " + gate["status"] + " | " + ", ".join(details) + " |")
    lines.extend(["", "## Highest dependency fan-out", "",
                  "| Node | Native status | Potential descendants |",
                  "| --- | --- | ---: |"])
    for node in report["critical_nodes"]:
        lines.append("| " + node["job_id"] + " | " + node["status"]
                     + " | " + str(node["potential_descendants"]) + " |")
    n = report["observation_completeness"]
    lines.extend(["", "Evidence classified: " + str(n["observed_gate_count"])
                  + "/" + str(n["total_gate_count"])
                  + " gates; missing/unknown are not zero.", ""])
    return "\n".join(lines)


def mermaid(report: dict[str, Any]) -> str:
    mapping = report["gates"]
    status = {k: mapping[k]["status"] for k in DOW_JOB_LABELS if k in mapping}
    ids = {key: "J" + str(i) for i, key in enumerate(status)}
    lines = ["flowchart LR"]
    for key, node in ids.items():
        title = DOW_JOB_LABELS[key].replace('"', "'")
        lines.append('    ' + node + '["' + title + ' / ' + status[key] + '"]')
    for key in ids:
        for dependency in mapping[key]["needs"]:
            if dependency in ids:
                lines.append("    " + ids[dependency] + " --> " + ids[key])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    r = build(main_sha=args.main_sha, head_sha=args.head_sha,
              main_branch=load(args.snapshot_dir, "branch.json"),
              main_runs=load(args.snapshot_dir, "main-runs.json"),
              head_runs=load(args.snapshot_dir, "head-runs.json"),
              dow_jobs=load(args.snapshot_dir, "dow-jobs.json"),
              workflow=args.workflow.read_text(encoding="utf-8"),
              coverage_data=load(args.snapshot_dir, "coverage.json"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "remaining-gates.json").write_text(
        json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "remaining-gates.md").write_text(
        markdown(r), encoding="utf-8")
    (args.output_dir / "remaining-gates.mmd").write_text(
        mermaid(r), encoding="utf-8")
    print(json.dumps(r["observation_completeness"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
