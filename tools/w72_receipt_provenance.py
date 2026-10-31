"""W72 checkout-bound green-proof receipt. Observational and fail-closed.

This is a repository-local utility. It does not dispatch work, change an
approval/merge decision, or automatically close any first-red/root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "abacus.w72.checkout-proof.v1"
MAX_EVENT_BYTES = 512_000


def strict_sha(value: Any, description: str) -> str:
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise ValueError(f"invalid {description} SHA")
    return value


def resolved_head(event_name: str, event_payload: dict, context_sha: str) -> str:
    """Derive expected checkout identity from trusted event shape, not GITHUB_SHA.

    On pull_request, GITHUB_SHA is a temporary merge commit and cannot be used
    as the identity of actions/checkout(ref=github.event.pull_request.head.sha).
    """
    context_sha = strict_sha(context_sha, "context")
    if event_name == "pull_request":
        pull = event_payload.get("pull_request")
        if not isinstance(pull, dict):
            raise ValueError("pull_request event missing pull_request object")
        head = pull.get("head")
        if not isinstance(head, dict):
            raise ValueError("pull_request event missing head")
        return strict_sha(head.get("sha"), "PR head")
    if event_name in ("workflow_dispatch", "push"):
        return context_sha
    raise ValueError("unsupported event prevents source proof")


def checkout_sha(repo_root: Path) -> str:
    value = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    return strict_sha(value, "checked-out")


def receipt(
    *,
    observed_sha: str,
    event_name: str,
    payload: dict,
    context_sha: str,
    run_id: int,
    run_attempt: int,
    job_id: str,
    junit: dict,
    junit_bytes: bytes,
) -> dict:
    actual = strict_sha(observed_sha, "checkout")
    expected = resolved_head(event_name, payload, context_sha)
    if actual != expected:
        raise ValueError("source checkout mismatch: PR head != git rev-parse HEAD")
    if event_name != "pull_request" and actual != context_sha:
        raise ValueError("non-PR event SHA mismatch")
    if type(run_id) is not int or run_id < 1:
        raise ValueError("positive native GITHUB_RUN_ID required")
    if type(run_attempt) is not int or run_attempt < 1:
        raise ValueError("positive native GITHUB_RUN_ATTEMPT required")
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", job_id):
        raise ValueError("invalid GITHUB_JOB")
    counts = junit.get("counts")
    if not isinstance(counts, dict) or any(
        type(counts.get(k)) is not int
        for k in ("collected", "passed", "failed", "errors", "skipped")
    ):
        raise ValueError("missing exact JUnit case counts")
    if counts["collected"] < 1 or counts["failed"] or counts["errors"]:
        raise ValueError("non-green JUnit cannot prove successful clean clone")
    if counts["collected"] != sum(
        counts[k] for k in ("passed", "failed", "errors", "skipped")
    ):
        raise ValueError("nonreconciling JUnit counts")
    if counts["passed"] < 1 or len(junit.get("cases", [])) != counts["collected"]:
        raise ValueError("zero test execution or lost cases")
    return {
        "schema": SCHEMA,
        "status": "PASS_SOURCE_BOUND_TEST_PROOF",
        "source_sha": actual,
        "checkout_sha": actual,
        "expected_head_sha": expected,
        "event_context_sha": strict_sha(context_sha, "event context"),
        "context_sha_may_be_synthetic_merge": event_name == "pull_request",
        "source_checkout_matched": True,
        "repository": "GBOGEB/ABACUS",
        "run_id": run_id,
        "run_attempt": run_attempt,
        "job_key": job_id,
        "test_selection": "DMAIC_V3/tests",
        "test_counts": dict(counts),
        "junit_sha256": hashlib.sha256(junit_bytes).hexdigest(),
        "testcase_output_sha256": hashlib.sha256(canonical(junit)).hexdigest(),
        "junit_case_identity_complete": junit.get("case_identity_census_complete")
        is True,
        "unmaterialized_pytest_subtests": junit.get(
            "unmaterialized_pytest_unittest_subtests", 0
        ),
        "authority_transfer": False,
        "merge_authorized": False,
        "security_waiver": False,
        "crew_launch_authenticated": None,
        "rex_accepted": None,
        "root_closures": None,
        "scope": "W72 clean-clone; exact checkout; unit test population only",
    }


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def run(
    *,
    root: Path,
    event_file: Path,
    junit_file: Path,
    output: Path,
    cases_output: Path,
    environment: dict[str, str] | None = None,
) -> dict:
    from tools.w72_testcase_telemetry import parse_junit

    env = dict(os.environ if environment is None else environment)
    if event_file.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("event payload exceeds bounded limit")
    event = json.loads(event_file.read_text(encoding="utf-8"))
    if not isinstance(event, dict):
        raise ValueError("invalid event JSON")
    observed = checkout_sha(root)
    parsed = parse_junit(junit_file.read_bytes())
    record = receipt(
        observed_sha=observed,
        event_name=env["GITHUB_EVENT_NAME"],
        payload=event,
        context_sha=env["GITHUB_SHA"],
        run_id=int(env["GITHUB_RUN_ID"]),
        run_attempt=int(env["GITHUB_RUN_ATTEMPT"]),
        job_id=env["GITHUB_JOB"],
        junit=parsed,
        junit_bytes=junit_file.read_bytes(),
    )
    record["python_version"] = __import__("platform").python_version()
    # Prefer deterministic file bytes without wall-clock timestamps.
    output.parent.mkdir(parents=True, exist_ok=True)
    cases_output.parent.mkdir(parents=True, exist_ok=True)
    cases_output.write_bytes(canonical(parsed))
    output.write_bytes(canonical(record))
    return record


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--event", type=Path, required=True)
    p.add_argument("--junit", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cases-out", type=Path, required=True)
    opts = p.parse_args()
    record = run(
        root=opts.repo,
        event_file=opts.event,
        junit_file=opts.junit,
        output=opts.out,
        cases_output=opts.cases_out,
    )
    print(
        json.dumps(
            {
                "schema": record["schema"],
                "status": record["status"],
                "source_sha": record["source_sha"],
                "test_counts": record["test_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
