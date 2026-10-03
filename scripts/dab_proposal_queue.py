#!/usr/bin/env python3
"""Build a governed DAB repair proposal queue from an exact Flake8 census."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

FINDING_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<code>[A-Z]\d{3}) (?P<message>.*)$"
)
DEFAULT_POLICY = Path("governance/dab/DAB_FULL_RED_GATES.json")
DEFAULT_CONTRACT = Path("governance/proposals/PROPOSAL_COMPATIBILITY_CONTRACT.json")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def parse_findings(raw: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in raw.splitlines():
        match = FINDING_RE.match(line)
        if not match:
            continue
        findings.append(
            {
                "path": match.group("path"),
                "line": int(match.group("line")),
                "column": int(match.group("col")),
                "code": match.group("code"),
                "message": match.group("message"),
            }
        )
    return findings


def risk_for(code: str, policy: dict[str, Any]) -> str:
    protected = policy.get("protected_holds", {})
    if code in protected:
        return "HIGH_OR_PROTECTED"
    low = set(
        policy.get("batch_policy", {})
        .get("LOW_MECHANICAL", {})
        .get("families", [])
    )
    if code in low:
        return "LOW_MECHANICAL"
    return "MEDIUM"


def gate_status(total: int, policy: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    active = None
    for name in ("G1", "G2", "G3"):
        gate = policy["gates"][name]
        threshold = int(gate["static_total_exclusive_max"])
        static_pass = total < threshold
        result[name] = {
            "threshold_exclusive": threshold,
            "static_budget_pass": static_pass,
            "companion_proof": "REQUIRED",
            "status": "STATIC_PASS_COMPANION_PENDING" if static_pass else "OPEN",
        }
        if active is None and not static_pass:
            active = name
    result["active_gate"] = active or "G3_PLUS_CONTROL"
    return result


def _proposal(
    *,
    source_sha: str,
    family: str,
    risk: str,
    findings: list[dict[str, Any]],
    protected_holds: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    paths = sorted({item["path"] for item in findings})
    return {
        "schema_version": "abacus-proposal-envelope/1.0.0",
        "proposal_id": f"DAB-{source_sha[:12]}-{family}-{index:03d}",
        "method": "DAB",
        "source_sha": source_sha,
        "proposal_type": "STATIC_REPAIR",
        "risk_class": risk,
        "family": family,
        "scope": {
            "paths": paths,
            "finding_count": len(findings),
            "findings": findings,
        },
        "mutation_mode": "READ_ONLY_PROPOSAL",
        "worker_model": {
            "proposal_workers": "SCALABLE_READ_ONLY",
            "mutation_writer_count": 1,
        },
        "protected_holds": protected_holds,
        "evidence_receipts": ["reports/dab_flake8_census.json"],
        "admission": {
            "exact_head_required": True,
            "first_completed_attributable_red_only": True,
            "post_merge_recensus_required": True,
        },
        "coverage_growth": {
            "applicability": "NOT_APPLICABLE_MECHANICAL_ONLY"
            if risk == "LOW_MECHANICAL"
            else "REQUIRED_OR_JUSTIFIED",
            "baseline_receipt": "MIP_OR_MATRIX_EXACT_HEAD",
            "target": "NON_REGRESSION_AND_CHECK_SURFACE_GROWTH",
            "result": "PENDING",
        },
        "authority": {
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        },
    }


def build_queue(
    census: dict[str, Any],
    raw: str,
    policy: dict[str, Any],
    source_sha: str,
) -> dict[str, Any]:
    findings = parse_findings(raw)
    protected = policy.get("protected_holds", {})
    protected_receipt = {
        code: {
            "count": int(census.get("all_families", {}).get(code, 0) or 0),
            "disposition": rule.get("disposition", "HOLD"),
        }
        for code, rule in protected.items()
    }

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        risk = risk_for(str(finding["code"]), policy)
        if risk == "HIGH_OR_PROTECTED":
            continue
        grouped[(risk, str(finding["code"]))].append(finding)

    proposals: list[dict[str, Any]] = []
    index = 1
    for (risk, family), rows in sorted(grouped.items()):
        cfg = policy["batch_policy"][risk]
        max_findings = int(cfg["max_findings"])
        max_files = int(cfg["max_files"])
        rows = sorted(rows, key=lambda item: (item["path"], item["line"], item["column"]))
        batch: list[dict[str, Any]] = []
        batch_paths: set[str] = set()

        def flush() -> None:
            nonlocal index, batch, batch_paths
            if not batch:
                return
            proposals.append(
                _proposal(
                    source_sha=source_sha,
                    family=family,
                    risk=risk,
                    findings=batch,
                    protected_holds=protected_receipt,
                    index=index,
                )
            )
            index += 1
            batch = []
            batch_paths = set()

        for row in rows:
            path = str(row["path"])
            adds_file = path not in batch_paths
            if batch and (
                len(batch) >= max_findings
                or (adds_file and len(batch_paths) >= max_files)
            ):
                flush()
            batch.append(row)
            batch_paths.add(path)
        flush()

    return {
        "schema_version": "abacus-dab-proposal-queue/1.0.0",
        "source_sha": source_sha,
        "measurement": {
            "total": int(census.get("total", 0) or 0),
            "families": census.get("all_families", {}),
            "gate_status": gate_status(int(census.get("total", 0) or 0), policy),
        },
        "protected_holds": protected_receipt,
        "worker_model": {
            "proposal_workers": {"min": 2, "max": 8, "mode": "READ_ONLY"},
            "mutation_writer_count": 1,
            "parallel_proposals_allowed": True,
            "parallel_mutation_for_same_scope_allowed": False,
        },
        "proposals": proposals,
        "governance": policy.get("governance", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--source-sha")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    census = load_json(args.census)
    policy = load_json(args.policy)
    _ = load_json(args.contract)
    source_sha = args.source_sha or str(census.get("exact_sha") or git_head())
    if len(source_sha) != 40:
        raise SystemExit("DAB proposal queue requires an exact 40-character SHA")

    queue = build_queue(
        census,
        args.text.read_text(encoding="utf-8", errors="replace"),
        policy,
        source_sha,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(queue, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
