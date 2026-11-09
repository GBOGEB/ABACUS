"""ABACUS-owned, stage-only GitHub Actions identity and custody receipt.

NO DISPATCH: this module never authorizes, dispatches, or mutates a repository.
The environment must originate from the ABACUS-native GitHub Actions runner.
Calling validate() with user-supplied values does not authenticate any user.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

REPO = "GBOGEB/ABACUS"
SHA = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_ACTORS = frozenset({"GBOGEB"})


class StageRejected(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StageRejected(message)


def validate(runtime: dict[str, str], expected_sha: str) -> dict:
    """Validate provider context shape and pin a read-only stage receipt.

    Only GitHub can attest provenance of its GITHUB_* values in a native run.
    This pure function intentionally makes no independent auth claim.
    """
    require(
        isinstance(expected_sha, str) and bool(SHA.fullmatch(expected_sha)),
        "invalid requested SHA",
    )
    repo = runtime.get("GITHUB_REPOSITORY")
    actor = runtime.get("GITHUB_ACTOR")
    sha = runtime.get("GITHUB_SHA")
    run = runtime.get("GITHUB_RUN_ID", "")
    attempt = runtime.get("GITHUB_RUN_ATTEMPT", "")
    require(repo == REPO, "wrong source authority")
    require(actor in ALLOWED_ACTORS, "actor is not stage allowlisted")
    require(
        runtime.get("GITHUB_EVENT_NAME") == "workflow_dispatch",
        "not native manual stage",
    )
    require(runtime.get("GITHUB_REF") == "refs/heads/main", "non-main stage forbidden")
    require(
        isinstance(sha, str) and bool(SHA.fullmatch(sha)) and sha == expected_sha,
        "stale, unbound, or invalid exact head",
    )
    require(run.isdecimal() and int(run) > 0, "native run ID missing")
    require(attempt.isdecimal() and int(attempt) > 0, "native attempt missing")
    request = {
        "schema": "abacus.missioncontrol.stage-only.v1",
        "repository": repo,
        "actor": actor,
        "event": "workflow_dispatch",
        "head_sha": sha,
        "run_id": int(run),
        "run_attempt": int(attempt),
        "operation": "STAGE_ONLY",
    }
    digest = hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema": "abacus.missioncontrol.stage-receipt.v1",
        "request": request,
        "request_sha256": digest,
        "run_url": f"https://github.com/{REPO}/actions/runs/{run}",
        "provider_binding": "GITHUB_ACTIONS_CONTEXT_REQUIRES_INDEPENDENT_NATIVE_READBACK",
        "state": "STAGED_ONLY_NO_WORKER_DISPATCH",
        "worker_launch_id": None,
        "native_worker_job_id": None,
        "accepted_rex_receipt": None,
        "merge_admission": "HOLD",
        "coverage_delta": None,
        "bd_root_closures": None,
        "authority_transfer": False,
        "security_waiver": False,
        "mutation_enabled": False,
    }


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--expected-sha", required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    receipt = validate(dict(os.environ), args.expected_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("STAGED_ONLY_NO_WORKER_DISPATCH", receipt["run_url"])


if __name__ == "__main__":
    main()
