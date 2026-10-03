#!/usr/bin/env python3
"""Evaluate the MIP v2 federated closed-loop control state.

The controller is intentionally fail-closed on authority and exact-SHA evidence.
Missing external evidence is represented as WAIT, not as a code failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "MIP" / "V2_FEDERATED_CONTROL_SCOPE.json"
V1_ACCEPTANCE_PATH = ROOT / "MIP" / "N2_CROSS_REPO_ACCEPTANCE_20260912.json"
V1_CLEANUP_PATH = ROOT / "MIP" / "FINAL_CLEANUP_20260912.json"
DOW_CONTRACT_PATH = ROOT / "governance" / "qps_triage" / "DOW_CONTRACT_v1.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _gate_map() -> dict[str, str]:
    return {f"V2-G{index}": "NOT_RUN" for index in range(1, 11)}


def validate_baseline() -> tuple[dict[str, Any], dict[str, str]]:
    scope = load_json(SCOPE_PATH)
    v1_acceptance = load_json(V1_ACCEPTANCE_PATH)
    v1_cleanup = load_json(V1_CLEANUP_PATH)
    dow = load_json(DOW_CONTRACT_PATH)

    if scope.get("scope_id") != "mip_v2_federated_closed_loop_control":
        raise SystemExit("wrong MIP v2 scope id")
    if scope.get("fixed_goalpost", {}).get("gate_count") != 10:
        raise SystemExit("MIP v2 denominator must remain fixed at 10")
    if v1_acceptance.get("fixed_goalpost", {}).get("closed_gate_count") != 8:
        raise SystemExit("v1 acceptance is not 8/8")
    if v1_acceptance.get("fixed_goalpost", {}).get("status") != "PASS":
        raise SystemExit("v1 acceptance is not PASS")
    if v1_cleanup.get("fixed_tranche", {}).get("status") != "CONTROL":
        raise SystemExit("v1 cleanup is not in CONTROL")
    if v1_cleanup.get("broader_global_dov") != "WITHHELD":
        raise SystemExit("global DoV boundary changed unexpectedly")
    if dow.get("schema") != "qps-triage-dow-contract/1.0.0":
        raise SystemExit("unexpected DOW contract schema")
    if dow.get("repo") != "GBOGEB/ABACUS":
        raise SystemExit("unexpected DOW authority repository")
    if dow.get("authority", {}).get("final_qps_disposition") is not False:
        raise SystemExit("DOW authority ceiling is not fail-closed")

    bindings = scope.get("contract_bindings", {})
    if bindings.get("keb", {}).get("schema") != "qps-triage-keb-contract/1.0.0":
        raise SystemExit("unexpected KEB binding schema")
    if bindings.get("child", {}).get("schema") != "qps-triage-child-contract/1.1.0":
        raise SystemExit("unexpected child binding schema")

    gates = _gate_map()
    gates["V2-G1"] = "PASS"
    gates["V2-G2"] = "PASS"
    gates["V2-G3"] = "PASS"
    return scope, gates


def validate_keb_receipt(receipt: dict[str, Any]) -> tuple[bool, list[str]]:
    required = {
        "producer_repo",
        "producer_pr",
        "producer_head_sha",
        "source_object_ids",
        "contract_version",
        "workflow_or_validator",
        "executed_steps",
        "result",
        "receipt_sha256",
        "downstream_consumer",
        "child_reentry_target",
    }
    errors = sorted(required - set(receipt))
    if receipt.get("producer_repo") != "GBOGEB/CODEX":
        errors.append("producer_repo")
    if receipt.get("downstream_consumer") != "GBOGEB/ABACUS":
        errors.append("downstream_consumer")
    if receipt.get("child_reentry_target") != "GBOGEB/cryoplant-project":
        errors.append("child_reentry_target")
    result = receipt.get("result")
    if result not in {"PASS", "FAIL", "DEFER"}:
        errors.append("result")
    sha = str(receipt.get("producer_head_sha", ""))
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha.lower()):
        errors.append("producer_head_sha")
    digest = str(receipt.get("receipt_sha256", ""))
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
        errors.append("receipt_sha256")
    if result == "PASS":
        steps = receipt.get("executed_steps")
        if type(steps) is not int or steps <= 0:
            errors.append("executed_steps")
    return not errors, sorted(set(errors))


def dow_disposition(
    receipt: dict[str, Any], challenge: dict[str, Any], head_sha: str
) -> tuple[dict[str, Any], bool]:
    challenge_result = challenge.get("result")
    challenge_name = challenge.get("challenge_or_execution")
    challenge_steps = challenge.get("executed_steps")
    if challenge_result not in {"PASS", "FAIL", "DEFER"}:
        return {}, False
    if not isinstance(challenge_name, str) or not challenge_name:
        return {}, False
    if challenge_result == "PASS" and (
        type(challenge_steps) is not int or challenge_steps <= 0
    ):
        return {}, False

    if receipt.get("result") == "PASS" and challenge_result == "PASS":
        disposition = "ACCEPT"
    elif receipt.get("result") == "FAIL" or challenge_result == "FAIL":
        disposition = "REJECT"
    else:
        disposition = "DEFER"

    reason = str(challenge.get("reason") or challenge_result).strip()
    value = {
        "schema_version": "0.1",
        "consumer_repo": "GBOGEB/ABACUS",
        "consumer_head_sha": head_sha,
        "producer_repo": receipt["producer_repo"],
        "producer_pr": receipt["producer_pr"],
        "producer_head_sha": receipt["producer_head_sha"],
        "producer_receipt_sha256": receipt["receipt_sha256"],
        "challenge_or_execution": challenge_name,
        "executed_steps": challenge_steps,
        "disposition": disposition,
        "reason": reason,
        "child_reentry_target": "GBOGEB/cryoplant-project",
        "authority_transfer": false_value(),
    }
    value["receipt_sha256"] = canonical_digest(value)
    return value, True


def false_value() -> bool:
    """Make the authority boundary explicit in emitted receipts."""
    return False

def build_coverage_pressure(
    census: dict[str, Any],
    head_sha: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Project measured DAB coverage evidence into a fail-closed MIP queue."""

    errors: list[str] = []
    accepted_schemas = {
        "abacus-coverage-dab/1.0.0",
        "abacus-post-b0-coverage-dab/1.0.0",
    }
    census_schema = str(census.get("schema", ""))
    if census_schema not in accepted_schemas:
        errors.append("schema")

    census_sha = str(census.get("exact_sha", ""))
    if census_sha != head_sha:
        errors.append("exact_sha")

    rows = census.get("rows")
    if not isinstance(rows, list):
        errors.append("rows")
        rows = []

    if errors:
        return {
            "status": "WITHHELD",
            "errors": sorted(set(errors)),
            "controller_head_sha": head_sha,
            "census_head_sha": census_sha or "MISSING",
            "priority_queue": [],
            "zero_coverage_disposition_queue": [],
            "expected_gain": "WITHHELD",
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        }

    by_path = {
        str(row.get("path")): row
        for row in rows
        if isinstance(row, dict) and row.get("path")
    }
    preferred = census.get("pressure_order")
    if not isinstance(preferred, list):
        preferred = []

    ordered_paths: list[str] = []
    seen: set[str] = set()
    for value in preferred:
        path = str(value)
        if path in by_path and path not in seen:
            ordered_paths.append(path)
            seen.add(path)
    for path in sorted(by_path):
        if path not in seen:
            ordered_paths.append(path)

    queue: list[dict[str, Any]] = []
    for path in ordered_paths:
        row = by_path[path]
        if row.get("source_class") != "ACTIVE_SOURCE":
            continue
        missed = int(row.get("missed_statements", 0) or 0)
        if missed <= 0:
            continue
        queue.append(
            {
                "path": path,
                "evidence_class": row.get("evidence_class", "MEASURED"),
                "source_class": row.get("source_class"),
                "disposition": row.get("disposition"),
                "test_state": row.get("test_state", "NO_TEST"),
                "existing_test_surface": row.get("existing_test_surface", []),
                "existing_test_surface_evidence": row.get(
                    "existing_test_surface_evidence", "NONE_MEASURED"
                ),
                "statements": int(row.get("statements", 0) or 0),
                "missed_statements": missed,
                "coverage_pct": row.get("coverage_pct"),
                "criticality": row.get("criticality", "WITHHELD"),
                "criticality_source": row.get("criticality_source", "WITHHELD"),
                "skip_dependencies": row.get("skip_dependencies", []),
                "warning_dependencies": row.get("warning_dependencies", []),
                "maximum_statement_gain": missed,
                "expected_gain": "WITHHELD",
                "authority_transfer": False,
                "formal_credit_delta": 0,
                "engineering_credit_delta": 0,
            }
        )
        if len(queue) >= max(0, limit):
            break

    zero_coverage = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("source_class") != "ACTIVE_SOURCE":
            continue
        statements = int(row.get("statements", 0) or 0)
        covered = int(row.get("covered_statements", 0) or 0)
        if statements <= 0 or covered != 0:
            continue
        zero_coverage.append(
            {
                "path": str(row.get("path", "")),
                "current_disposition": row.get("disposition", "UNKNOWN"),
                "required_disposition": "ADMIT|QUARANTINE|DELETE|UNKNOWN",
                "evidence_class": row.get("evidence_class", "MEASURED"),
                "authority_transfer": False,
                "formal_credit_delta": 0,
                "engineering_credit_delta": 0,
            }
        )

    return {
        "status": "MEASURED",
        "controller_head_sha": head_sha,
        "census_head_sha": census_sha,
        "census_schema": census_schema,
        "measurement": census.get("measurement", {}),
        "active_source": census.get("active_source", {}),
        "priority_queue": queue,
        "zero_coverage_disposition_queue": sorted(
            zero_coverage,
            key=lambda row: row["path"],
        ),
        "expected_gain": "WITHHELD",
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


TEST_PRESSURE_ORDER = {
    "TEST_FAILING": 0,
    "TEST_BLOCKED_CONFIG": 1,
    "TEST_BLOCKED_DEPENDENCY": 2,
    "TEST_BLOCKED_SOURCE_MISSING": 3,
    "TEST_NOT_IMPLEMENTED": 4,
    "TEST_EXISTS_UNCOLLECTED": 5,
    "NO_TEST": 6,
    "TEST_GREEN": 9,
}


def build_test_pressure(
    census: dict[str, Any],
    head_sha: str,
    limit: int = 50,
) -> dict[str, Any]:
    """Project measured test outcomes into the same fail-closed MIP queue."""

    errors: list[str] = []
    if census.get("schema") != "abacus-test-evidence-census/1.0.0":
        errors.append("schema")
    census_sha = str(census.get("exact_sha", ""))
    if census_sha != head_sha:
        errors.append("exact_sha")

    rows = census.get("rows")
    if not isinstance(rows, list):
        errors.append("rows")
        rows = []

    if errors:
        return {
            "status": "WITHHELD",
            "errors": sorted(set(errors)),
            "controller_head_sha": head_sha,
            "census_head_sha": census_sha or "MISSING",
            "priority_queue": [],
            "outcomes": census.get("outcomes", {}),
            "states": census.get("states", {}),
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        }

    pressure_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("test_state") or "NO_TEST")
        if state == "TEST_GREEN":
            continue
        pressure_rows.append(
            {
                "test": str(row.get("test", "")),
                "outcome": str(row.get("outcome", "")),
                "test_state": state,
                "test_state_source": row.get("test_state_source", "derived"),
                "xfail": bool(row.get("xfail", False)),
                "evidence_class": "MEASURED",
                "authority_transfer": False,
                "formal_credit_delta": 0,
                "engineering_credit_delta": 0,
            }
        )

    pressure_rows.sort(
        key=lambda row: (
            TEST_PRESSURE_ORDER.get(row["test_state"], 8),
            row["test"],
        )
    )
    queue = pressure_rows[: max(0, limit)]

    return {
        "status": "MEASURED",
        "controller_head_sha": head_sha,
        "census_head_sha": census_sha,
        "outcomes": census.get("outcomes", {}),
        "states": census.get("states", {}),
        "skip_count": int(census.get("skip_count", 0) or 0),
        "xfail_count": int(census.get("xfail_count", 0) or 0),
        "uncategorized_skips": census.get("uncategorized_skips", []),
        "priority_queue": queue,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


def validate_child_feedback(
    feedback: dict[str, Any], dow_receipt: dict[str, Any]
) -> tuple[bool, list[str]]:
    required = {
        "parent_repo",
        "parent_head_sha",
        "parent_receipt_sha256",
        "disposition",
        "reason",
    }
    errors = sorted(required - set(feedback))
    if feedback.get("parent_repo") != "GBOGEB/ABACUS":
        errors.append("parent_repo")
    if feedback.get("parent_head_sha") != dow_receipt.get("consumer_head_sha"):
        errors.append("parent_head_sha")
    if feedback.get("parent_receipt_sha256") != dow_receipt.get("receipt_sha256"):
        errors.append("parent_receipt_sha256")
    if feedback.get("disposition") not in {"ACCEPT", "REJECT", "DEFER"}:
        errors.append("disposition")
    return not errors, sorted(set(errors))


def evaluate(
    keb_receipt: dict[str, Any] | None = None,
    challenge: dict[str, Any] | None = None,
    child_feedback: dict[str, Any] | None = None,
    head_sha: str | None = None,
) -> dict[str, Any]:
    scope, gates = validate_baseline()
    gates["V2-G4"] = "PASS"
    current_head = head_sha or git_head()
    summary: dict[str, Any] = {
        "schema_version": "0.1",
        "program": "MIP",
        "scope_id": scope["scope_id"],
        "controller_head_sha": current_head,
        "gate_count": 10,
        "gate_observations": gates,
        "global_project_dov": "WITHHELD",
        "authority_transfer": False,
    }

    if keb_receipt is None:
        summary.update(
            {
                "controller_state": "WAIT_KEB_RECEIPT",
                "next_action": "Provide a real KEB exact-SHA receipt with digest and positive runtime evidence when result=PASS.",
            }
        )
        return summary

    valid_keb, keb_errors = validate_keb_receipt(keb_receipt)
    if not valid_keb:
        gates["V2-G5"] = "FAIL"
        summary.update(
            {
                "controller_state": "REPAIR_OR_WITHDRAW",
                "first_red": "KEB_RECEIPT_CONTRACT",
                "errors": keb_errors,
                "next_action": "Repair or explicitly DEFER the first KEB receipt contract failure, then rerun the same gate.",
            }
        )
        return summary

    gates["V2-G5"] = "PASS"
    summary["keb_receipt"] = {
        key: keb_receipt[key]
        for key in (
            "producer_repo",
            "producer_pr",
            "producer_head_sha",
            "executed_steps",
            "result",
            "receipt_sha256",
        )
    }

    if challenge is None:
        summary.update(
            {
                "controller_state": "WAIT_DOW_CHALLENGE",
                "next_action": "Execute the smallest DOW challenge that can test the producer claim.",
            }
        )
        return summary

    dow_receipt, valid_challenge = dow_disposition(keb_receipt, challenge, current_head)
    if not valid_challenge:
        gates["V2-G6"] = "FAIL"
        summary.update(
            {
                "controller_state": "REPAIR_OR_WITHDRAW",
                "first_red": "DOW_CHALLENGE_CONTRACT",
                "next_action": "Repair or DEFER the DOW challenge contract and rerun the same gate.",
            }
        )
        return summary

    gates["V2-G6"] = "PASS"
    summary["dow_receipt"] = dow_receipt

    if child_feedback is None:
        summary.update(
            {
                "controller_state": "WAIT_CHILD_REENTRY",
                "next_action": "Dispatch the sanitized DOW receipt to cryoplant child authority for ACCEPT/REJECT/DEFER.",
            }
        )
        return summary

    valid_child, child_errors = validate_child_feedback(child_feedback, dow_receipt)
    if not valid_child:
        gates["V2-G7"] = "FAIL"
        summary.update(
            {
                "controller_state": "REPAIR_OR_WITHDRAW",
                "first_red": "CHILD_REENTRY_CONTRACT",
                "errors": child_errors,
                "next_action": "Repair or explicitly DEFER child re-entry identity binding, then rerun.",
            }
        )
        return summary

    gates["V2-G7"] = "PASS"
    gates["V2-G8"] = "PASS"
    child_disposition = child_feedback["disposition"]
    summary["child_feedback"] = {
        "disposition": child_disposition,
        "reason": child_feedback["reason"],
    }
    if child_disposition == "ACCEPT":
        state = "REPEAT_DISTINCT_SHA"
        next_action = "Repeat the same invariant on a later distinct exact SHA before v2 CONTROL promotion."
    elif child_disposition == "DEFER":
        state = "ROUTE_FIRST_RED"
        next_action = "Route the child's bounded DEFER reason to the first-red owner; do not create formal credit."
    else:
        state = "REPAIR_OR_WITHDRAW"
        next_action = "Repair or withdraw the rejected producer/challenge claim before any new execution."
    summary["controller_state"] = state
    summary["next_action"] = next_action
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--keb-receipt", type=Path)
    parser.add_argument("--challenge", type=Path)
    parser.add_argument("--child-feedback", type=Path)
    parser.add_argument("--coverage-census", type=Path)
    parser.add_argument("--coverage-limit", type=int, default=20)
    parser.add_argument("--test-evidence-census", type=Path)
    parser.add_argument("--test-pressure-limit", type=int, default=50)
    args = parser.parse_args(argv)

    keb = load_json(args.keb_receipt) if args.keb_receipt else None
    challenge = load_json(args.challenge) if args.challenge else None
    child = load_json(args.child_feedback) if args.child_feedback else None
    result = evaluate(keb, challenge, child)
    if args.coverage_census:
        coverage_census = load_json(args.coverage_census)
        result["coverage_pressure"] = build_coverage_pressure(
            coverage_census,
            result["controller_head_sha"],
            limit=args.coverage_limit,
        )
    if args.test_evidence_census:
        test_census = load_json(args.test_evidence_census)
        result["test_pressure"] = build_test_pressure(
            test_census,
            result["controller_head_sha"],
            limit=args.test_pressure_limit,
        )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    expected_sha = os.environ.get("EXPECTED_SHA")
    if expected_sha and result["controller_head_sha"] != expected_sha:
        raise SystemExit("controller exact-SHA mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
