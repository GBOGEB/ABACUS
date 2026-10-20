#!/usr/bin/env python3
"""Execute V3.1 read-only host preflight, YAML DAG validation and census.

Native GitHub source/job binding is incomplete until run/job API corroboration.
This CLI never merges, mutates source, or claims active self-hosted RHEL/Docker.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

from four_planes import Source, federated_join, fingerprint  # noqa: E402
from runtime_probe import (  # noqa: E402
    observe_docker_availability,
    observe_host,
    observe_lldb_availability,
    probe_debug_target,
)
from yaml_control import (  # noqa: E402
    evaluate_dispatch,
    load_yaml,
    validate_federation_policy,
    validate_plan,
)


def execute(
    repo: str,
    sha: str,
    run_id: int,
    *,
    probe_lldb: bool = False,
    output=None,
    job_id=None,
    executed_sha=None,
) -> dict:
    src = Source(repo, sha, run_id, job_id, executed_sha)
    plan = load_yaml((BASE / "config/workflow-groups.yaml").read_text())
    federation = load_yaml((BASE / "config/federation-bindings.yaml").read_text())
    plan_info = validate_plan(plan)
    policy_info = validate_federation_policy(federation)
    host = observe_host(src, port_probe=True)
    lldb_version = observe_lldb_availability()
    docker_version = observe_docker_availability()
    debugger_receipt = None
    debugger_execution = {"status": "NOT_REQUESTED", "real_step_count": None}
    if probe_lldb:
        debugger_receipt, debugger_execution = probe_debug_target(src)
    receipts = [host] + ([debugger_receipt] if debugger_receipt else [])
    joined = federated_join(receipts)
    outcomes = {"YAML_PREFLIGHT": "PASS", "RUNTIME_HOST": "PASS"}
    # Availability is not evidence of a *debugger session* completing.
    if debugger_execution.get("real_step_count", 0):
        outcomes["DEBUG_LLDB"] = "PASS"
    dispatch = evaluate_dispatch(plan, outcomes)
    result = {
        "schema": "abacus.everred.four_plane.preflight.v1",
        "source_binding": src.binding(),
        "plan": plan_info,
        "federation": policy_info,
        "debugger_availability": lldb_version,
        "docker_availability": docker_version,
        "debugger_execution": debugger_execution,
        "receipts": receipts,
        "joined_census": joined,
        "dispatch_preview": dispatch,
        "claims": {
            "self_hosted_rhel_verified": None,
            "docker_running_verified": None,
            "ldab_roots_confirmed": None,
            "debugger_sessions_verified": None,
            "admission": "HOLD",
            "current_healthy_ports": None,
            "remote_worker_count": None,
        },
    }
    result["result_digest"] = fingerprint(result)
    if output:
        dest = Path(output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--job-id", type=int)
    p.add_argument("--executed-sha")
    p.add_argument("--probe-lldb", action="store_true")
    p.add_argument("--output", default=str(BASE / "data/four_plane_preflight.json"))
    a = p.parse_args()
    r = execute(
        a.repo,
        a.sha,
        a.run_id,
        probe_lldb=a.probe_lldb,
        output=a.output,
        job_id=a.job_id,
        executed_sha=a.executed_sha,
    )
    print(
        json.dumps(
            {
                "result_digest": r["result_digest"],
                "plan_tasks": r["plan"]["task_count"],
                "joined_observations": r["joined_census"]["observation_count"],
                "runtime_os": r["receipts"][0]["data"]["os_family"],
                "debugger_session_status": r["debugger_execution"]["status"],
                "admission": r["claims"]["admission"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
