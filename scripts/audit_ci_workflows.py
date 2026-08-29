#!/usr/bin/env python3
"""Inventory and govern ABACUS GitHub Actions without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "ci/governance/workflow_policy.json"
DEFAULT_WORKFLOWS = ROOT / ".github/workflows"


@dataclass(frozen=True)
class Workflow:
    file: str
    name: str
    events: tuple[str, ...]
    jobs: tuple[str, ...]
    commands: tuple[str, ...]


def _normalise_command(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def parse_workflow(path: Path) -> Workflow:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    name = path.name
    for line in lines:
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
            break

    events: list[str] = []
    on_index = next((i for i, line in enumerate(lines) if line.startswith("on:")), None)
    if on_index is not None:
        inline = lines[on_index].split(":", 1)[1].strip()
        if inline:
            events.append(inline)
        for line in lines[on_index + 1 :]:
            if line and not line.startswith((" ", "\t")):
                break
            match = re.match(r"^  ([A-Za-z_][\w-]*):", line)
            if match:
                events.append(match.group(1))

    jobs: list[str] = []
    in_jobs = False
    for line in lines:
        if line == "jobs:":
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith((" ", "\t")):
            in_jobs = False
        if in_jobs:
            match = re.match(r"^  ([A-Za-z0-9_.${}-]+):\s*(?:#.*)?$", line)
            if match:
                jobs.append(match.group(1))

    commands: list[str] = []
    in_run = False
    run_indent = 0
    for line in lines:
        match = re.match(r"^(\s*)run:\s*(.*)$", line)
        if match:
            in_run = True
            run_indent = len(match.group(1))
            inline = match.group(2).strip()
            if inline and inline not in {"|", ">"}:
                commands.append(_normalise_command(inline))
            continue
        if not in_run:
            continue
        indentation = len(line) - len(line.lstrip())
        if line.strip() and indentation <= run_indent:
            in_run = False
        elif line.strip() and not line.lstrip().startswith("#"):
            commands.append(_normalise_command(line))

    return Workflow(
        file=path.name,
        name=name,
        events=tuple(dict.fromkeys(events)),
        jobs=tuple(dict.fromkeys(jobs)),
        commands=tuple(dict.fromkeys(commands)),
    )


def classify(filename: str, policy: dict) -> tuple[dict | None, list[int]]:
    matches = [i for i, rule in enumerate(policy["rules"]) if re.search(rule["pattern"], filename)]
    if not matches:
        return None, []
    return policy["rules"][matches[0]], matches


def audit(workflow_dir: Path, policy: dict) -> dict:
    workflows = [parse_workflow(path) for path in sorted(workflow_dir.glob("*.y*ml"))]
    records: list[dict] = []
    unclassified: list[str] = []
    multiple_matches: dict[str, list[int]] = {}
    command_owners: dict[str, list[str]] = defaultdict(list)

    for workflow in workflows:
        rule, matches = classify(workflow.file, policy)
        if rule is None:
            unclassified.append(workflow.file)
            continue
        if len(matches) > 1:
            multiple_matches[workflow.file] = matches
        for command in workflow.commands:
            if re.search(r"\b(pytest|ruff|flake8|pylint|mypy|black|bandit|semgrep|osv-scanner|pre-commit)\b", command, re.I):
                command_owners[command].append(workflow.file)
        records.append(
            {
                "file": workflow.file,
                "name": workflow.name,
                "cluster": rule["cluster"],
                "lifecycle": rule["lifecycle"],
                "order": policy["lifecycle_order"][rule["lifecycle"]],
                "disposition": rule["disposition"],
                "replacement": rule.get("replacement"),
                "events": list(workflow.events),
                "jobs": list(workflow.jobs),
                "job_count": len(workflow.jobs),
            }
        )

    records.sort(key=lambda row: (row["order"], row["cluster"], row["file"]))
    files = {workflow.file for workflow in workflows}
    missing_canonical = [
        data["canonical"]
        for data in policy["clusters"].values()
        if data.get("canonical") and data["canonical"] not in files
    ]
    repeated = [
        {"command": command, "workflows": owners, "count": len(owners)}
        for command, owners in command_owners.items()
        if len(owners) > 1
    ]
    repeated.sort(key=lambda row: (-row["count"], row["command"]))

    return {
        "policy_id": policy["policy_id"],
        "policy_sha256": hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest(),
        "workflow_count": len(workflows),
        "classified_count": len(records),
        "unclassified": unclassified,
        "multiple_matches": multiple_matches,
        "missing_canonical": missing_canonical,
        "cluster_counts": dict(sorted(Counter(row["cluster"] for row in records).items())),
        "lifecycle_counts": dict(sorted(Counter(row["lifecycle"] for row in records).items())),
        "disposition_counts": dict(sorted(Counter(row["disposition"] for row in records).items())),
        "repeated_quality_commands": repeated,
        "workflows": records,
    }


def render_markdown(report: dict, policy: dict) -> str:
    baseline = policy["baseline_snapshot"]
    lines = [
        "# ABACUS CI workflow rationalisation",
        "",
        f"Policy: `{report['policy_id']}`  ",
        f"Policy SHA-256: `{report['policy_sha256']}`",
        "",
        "## Outcome",
        "",
        f"The repository currently contains **{report['workflow_count']} workflow definitions**. "
        f"All **{report['classified_count']}** are assigned to one primary functional cluster and lifecycle stage.",
        "",
        "The observed baseline that motivated this control was PR #681 with "
        f"{baseline['pr_681_check_runs']} check runs ({baseline['pr_681_queued']} queued, "
        f"{baseline['pr_681_skipped']} skipped) and main with {baseline['main_check_runs']} check runs.",
        "",
        "## Execution order",
        "",
        "| Order | Lifecycle | Purpose |",
        "|---:|---|---|",
    ]
    purpose = {
        "pr_fast": "Always-fast structural and unit evidence",
        "pr_domain": "Path-relevant domain, integration and security evidence",
        "post_merge": "Build, release, publication and reporting",
        "scheduled": "Comprehensive, maintenance and monitoring work",
        "manual": "Diagnostic or migration comparison only",
        "retire": "Remove after replacement evidence is accepted",
    }
    for lifecycle, order in sorted(policy["lifecycle_order"].items(), key=lambda item: item[1]):
        lines.append(f"| {order} | `{lifecycle}` | {purpose[lifecycle]} |")

    lines += ["", "## Cluster ownership", "", "| Cluster | Canonical workflow | Definitions | Intent |", "|---|---|---:|---|"]
    for cluster, data in policy["clusters"].items():
        canonical = f"`{data['canonical']}`" if data.get("canonical") else "—"
        lines.append(f"| `{cluster}` | {canonical} | {report['cluster_counts'].get(cluster, 0)} | {data['intent']} |")

    lines += [
        "",
        "## Immediate consolidation decisions",
        "",
        "- `security-scan.yml` is the PR/push security owner; standalone `bandit.yml` becomes manual comparison only.",
        "- `bridge-ci.yml` is the bridge owner; legacy `ci.yml` becomes manual comparison only.",
        "- `ci-codex.yml` is retired from automatic ABACUS execution. Cross-repo truth travels only through a versioned manifest/hash contract.",
        "- Full regression, bootstrap/statistics, bridge and DMAIC suites use path-scoped PR triggers; `ci-abacus.yml` remains the fast general gate.",
        "- Auto-merge, branch analysis and reporting remain separate because they have different permissions, events and side effects.",
        "",
        "## Workflow inventory",
        "",
        "| Order | Cluster | Workflow | Events | Jobs | Decision | Replacement |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for row in report["workflows"]:
        replacement = f"`{row['replacement']}`" if row.get("replacement") else "—"
        lines.append(
            f"| {row['order']} | `{row['cluster']}` | `{row['file']}` | "
            f"{', '.join(row['events']) or 'none'} | {row['job_count']} | "
            f"`{row['disposition']}` | {replacement} |"
        )

    lines += ["", "## Repeated quality/test commands", ""]
    if report["repeated_quality_commands"]:
        for row in report["repeated_quality_commands"][:20]:
            lines.append(f"- `{row['command']}` — {', '.join(f'`{x}`' for x in row['workflows'])}")
    else:
        lines.append("No repeated quality/test commands detected.")

    lines += [
        "",
        "## Control rule",
        "",
        "A workflow change fails CI governance when a definition is unclassified, a canonical owner is missing, "
        "or the generated report no longer matches the policy. This report is derived; "
        "`ci/governance/workflow_policy.json` is the SSOT.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--workflow-dir", type=Path, default=DEFAULT_WORKFLOWS)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    report = audit(args.workflow_dir, policy)
    markdown = render_markdown(report, policy)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")

    errors = []
    if report["unclassified"]:
        errors.append(f"unclassified workflows: {', '.join(report['unclassified'])}")
    if policy["quality_gates"]["allow_multiple_rule_matches"] is False and report["multiple_matches"]:
        errors.append(f"multiple policy matches: {report['multiple_matches']}")
    if policy["quality_gates"]["require_existing_canonical"] and report["missing_canonical"]:
        errors.append(f"missing canonical workflows: {', '.join(report['missing_canonical'])}")
    if errors:
        print("CI governance failed: " + "; ".join(errors), file=sys.stderr)
        return 1
    print(json.dumps({key: report[key] for key in ("workflow_count", "cluster_counts", "lifecycle_counts", "disposition_counts")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
