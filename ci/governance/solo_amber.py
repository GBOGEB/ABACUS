"""Evaluate a solo-maintainer exception request without granting merge authority.

This producer does not edit GitHub rules, forge a successful check, or approve a PR.
"""

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "abacus.solo-amber.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_CARRY = {
    "formatting",
    "documentation",
    "telemetry",
    "ci_infrastructure",
}
HARD_BLOCK = {
    "security",
    "confidentiality",
    "provenance",
    "governance",
    "correctness",
    "data_integrity",
    "release",
}
STATES = {"success", "failure", "pending", "cancelled", "skipped"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc(value):
    require(isinstance(value, str), "timestamp must be text")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    require(timestamp.tzinfo is not None, "timestamp has no timezone")
    require(timestamp.utcoffset() == timedelta(0), "timestamp must be UTC")
    return timestamp


def link(value, section):
    require(isinstance(value, str), "missing " + section)
    parsed = urlparse(value)
    require(
        parsed.scheme == "https"
        and parsed.hostname == "github.com"
        and parsed.path.startswith("/GBOGEB/ABACUS/" + section + "/"),
        "invalid repository " + section + " URL",
    )


def coverage_metric(pulses):
    require(isinstance(pulses, list), "pulses must be an array")
    result = []
    seen = set()
    for pulse in pulses:
        require(isinstance(pulse, dict), "invalid pulse")
        wave = pulse.get("wave_id")
        head = pulse.get("head_sha")
        require(isinstance(wave, str) and wave, "missing wave ID")
        require(isinstance(head, str) and SHA.fullmatch(head), "invalid pulse SHA")
        require((wave, head) not in seen, "duplicate wave/SHA")
        seen.add((wave, head))
        cv = pulse.get("coverage", {})
        require(isinstance(cv, dict), "invalid coverage")
        status = cv.get("status", "UNKNOWN")
        require(
            status in {"COMPARABLE", "INCOMPARABLE", "UNKNOWN"},
            "invalid coverage status",
        )
        delta = None
        if status == "COMPARABLE":
            require(
                type(cv.get("delta_pp")) in (float, int),
                "missing comparable delta",
            )
            delta = cv["delta_pp"]
        tests = pulse.get("tests", {})
        require(isinstance(tests, dict), "invalid pulse tests")
        for field in ("passed", "failed", "skipped"):
            require(
                type(tests.get(field)) is int and tests[field] >= 0,
                "invalid pulse test count",
            )
        roots = pulse.get("root_counts", {})
        require(isinstance(roots, dict), "invalid roots")
        for key, count in roots.items():
            require(type(count) is int and count >= 0, "invalid root count")
        result.append(
            {
                "wave_id": wave,
                "head_sha": head,
                "coverage_status": status,
                "coverage_delta_pp": delta,
                "tests": tests,
                "root_counts": roots,
                "first_red_count": len(pulse.get("first_reds", [])),
                "worker_count": pulse.get("worker_count"),
                "evidence_level": "SUBMITTED_NOT_INDEPENDENTLY_VERIFIED",
            }
        )
    return result


def assess(record):
    require(isinstance(record, dict), "record must be object")
    require(record.get("schema") == SCHEMA, "unsupported schema")
    require(record.get("repository") == "GBOGEB/ABACUS", "unexpected repo")
    sha = record.get("head_sha")
    require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid head SHA")
    require(type(record.get("pr_number")) is int, "invalid PR number")
    require(record["pr_number"] > 0, "invalid PR number")
    decision = record.get("decision", {})
    require(isinstance(decision, dict), "missing decision")
    require(decision.get("intent") == "REQUEST_AMBER", "intent not explicit")
    require(decision.get("actor") == "GBOGEB", "unauthorized identity")
    require(
        decision.get("acknowledge_solo_not_independent") is True,
        "self-review is not independent",
    )
    require(
        isinstance(decision.get("reason"), str)
        and len(decision["reason"].strip()) >= 20,
        "missing decision rationale",
    )
    at = utc(decision.get("recorded_at_utc"))
    checks = record.get("checks")
    require(isinstance(checks, list) and checks, "check census missing")
    seen = set()
    carried = []
    hard = []
    unresolved = []
    states = {state: 0 for state in STATES}
    for check in checks:
        require(isinstance(check, dict), "malformed check")
        name = check.get("name")
        require(isinstance(name, str) and name, "check name missing")
        require(name not in seen, "duplicate check name")
        seen.add(name)
        state = check.get("state")
        require(state in STATES, "invalid check state")
        states[state] += 1
        require(check.get("head_sha") == sha, "check head SHA mismatch")
        link(check.get("run_url"), "actions/runs")
        if state == "success":
            require(check.get("exception") is None, "waiving a success")
            continue
        category = check.get("category")
        if category in HARD_BLOCK:
            hard.append({"name": name, "category": category, "state": state})
            continue
        if category not in ALLOWED_CARRY:
            unresolved.append({"name": name, "reason": "unclassified"})
            continue
        exception = check.get("exception")
        if not isinstance(exception, dict):
            unresolved.append({"name": name, "reason": "no exception"})
            continue
        link(exception.get("issue_url"), "issues")
        require(
            isinstance(exception.get("root_id"), str)
            and exception["root_id"].strip(),
            "missing root ID",
        )
        require(
            isinstance(exception.get("owner"), str)
            and exception["owner"].strip(),
            "missing carry owner",
        )
        for field in ("reason", "impact", "mitigation"):
            require(
                isinstance(exception.get(field), str)
                and len(exception[field].strip()) >= 10,
                "missing " + field,
            )
        require(exception.get("risk") == "low", "non-low risk cannot carry")
        expires = utc(exception.get("expires_at_utc"))
        if expires <= at:
            unresolved.append({"name": name, "reason": "expired"})
            continue
        carried.append(
            {
                "name": name,
                "state": state,
                "category": category,
                "root_id": exception["root_id"],
                "issue_url": exception["issue_url"],
                "owner": exception["owner"],
                "expires_at_utc": exception["expires_at_utc"],
                "risk": "low",
                "reason": exception["reason"],
                "impact": exception["impact"],
                "mitigation": exception["mitigation"],
            }
        )
    state = "RED_HOLD" if hard else "UNKNOWN_HOLD" if unresolved else (
        "AMBER_REQUESTED" if carried else "GREEN_EVIDENCE_ONLY"
    )
    return {
        "schema": SCHEMA,
        "repository": record["repository"],
        "pr_number": record["pr_number"],
        "head_sha": sha,
        "decision": state,
        "reviewer": "GBOGEB",
        "review_independence": "SOLO_MAINTAINER_NOT_INDEPENDENT",
        "requires_manual_ruleset_action": state == "AMBER_REQUESTED",
        "merge_admitted": False,
        "checks": states,
        "total_checks": len(checks),
        "carried_count": len(carried),
        "hard_blockers": hard,
        "unresolved": unresolved,
        "carryover": carried,
        "pulses": coverage_metric(record.get("pulses", [])),
        "proof": "INPUT_DECLARATIONS_ONLY_NOT_NATIVE_VERIFICATION",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.input).read_bytes()
    result = assess(json.loads(source))
    result["input_sha256"] = hashlib.sha256(source).hexdigest()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "carried": result["carried_count"],
                "pulses": len(result["pulses"]),
                "merge_admitted": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
