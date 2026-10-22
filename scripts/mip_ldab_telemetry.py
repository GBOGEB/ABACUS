#!/usr/bin/env python3
"""Sanitized LDAB discovery, diagnostic and runtime-evidence separation.

The MIP self-index counts source surfaces. It does not execute LLDB/DAP, inspect
ports, or establish completed remediations. Unknown operational facts stay null.
"""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONTRACT = "integration/codespace_jyperter/tests/test_smoke_federation.py"
_LANE = "repo_self_assess_debug_ldab"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _path(value: Any) -> str:
    _require(isinstance(value, str) and bool(value), "invalid source path")
    path = value.replace("\\", "/")
    parts = path.split("/")
    _require(
        not path.startswith("/")
        and not re.match(r"^[A-Za-z]:", path)
        and all(part not in ("", ".", "..") for part in parts),
        "unsafe or non-normalized source path",
    )
    _require(
        str(PurePosixPath(path)) == path and not path.startswith("~"),
        "non-canonical source path",
    )
    return path


def _candidate_class(path: str) -> str:
    """Versioned lexical triage; never treat file names as executed tools."""
    tokens = set(re.split(r"[^a-z0-9]+", path.lower())) - {""}
    if tokens.intersection({
        "debug", "lldb", "dap", "diagnostic", "diagnostics", "observability"
    }):
        return "explicit_debug"
    if tokens.intersection({
        "log", "logs", "logger", "logging", "trace", "tracing", "traceability"
    }):
        return "telemetry_logs_trace"
    return "lexical_incidental"


def _source_census(receipt: dict[str, Any], location: str) -> dict[str, Any]:
    _require(isinstance(receipt, dict), location + " receipt absent")
    assessments = receipt.get("assessments")
    _require(isinstance(assessments, dict), location + " assessments absent")
    lane = assessments.get(_LANE)
    _require(isinstance(lane, dict), location + " LDAB lane absent")
    count = lane.get("signals")
    samples = lane.get("sample_paths")
    _require(
        type(count) is int and count >= 0
        and isinstance(samples, list)
        and len(samples) <= count,
        location + " LDAB denominator invalid",
    )
    paths = [_path(path) for path in samples]
    _require(
        len(paths) == len(set(paths)) and (count == 0) == (len(paths) == 0),
        location + " LDAB sample conflicts with denominator",
    )
    status = lane.get("status")
    if location == "root":
        # Kit 1.1.0: root GREEN needs an executed diagnostic on HEAD, so
        # signals without one are AMBER and a proven repo may have none.
        # Only RED still follows from file presence: no signals at all.
        consistent = not (status == "red" and count > 0)
    else:
        consistent = (status == "green") == (count > 0)
    _require(
        status in ("green", "amber", "red") and consistent,
        location + " LDAB source status mismatch",
    )
    full = lane.get("all_candidate_paths")
    full_paths = None
    inventory = None
    if full is not None:
        _require(
            isinstance(full, list) and len(full) == count,
            location + " full source inventory denominator mismatch",
        )
        full_paths = [_path(value) for value in full]
        _require(
            full_paths == sorted(set(full_paths))
            and full_paths[:len(paths)] == paths,
            location + " full source inventory order/sample mismatch",
        )
        counts = {
            "explicit_debug": 0,
            "telemetry_logs_trace": 0,
            "lexical_incidental": 0,
        }
        inventory = []
        for path in full_paths:
            classification = _candidate_class(path)
            counts[classification] += 1
            inventory.append({"path": path, "source_class": classification})
        _require(sum(counts.values()) == count, "source triage count mismatch")
    else:
        counts = None

    return {
        "candidate_file_count": count,
        "inventory_complete": full_paths is not None,
        "source_taxonomy": "ldab.lexical.v1",
        "source_class_counts": counts,
        "full_source_inventory": inventory,
        "sample_paths": paths,
        "sample_count": len(paths),
        "sample_truncated": count > len(paths),
        "sample_limit": 20 if location == "root" else 12,
        "sample_is_complete": count == len(paths),
        "producer_assessment": status.upper(),
        "evidence_level": "SOURCE_DISCOVERY_ONLY",
        "live_runtime_inferred": False,
    }


def summarize(
    root: dict[str, Any],
    nested: dict[str, Any] | None,
    diagnostic: dict[str, Any] | None,
    expected_sha: str,
    repository: str = "GBOGEB/ABACUS",
) -> dict[str, Any]:
    """Require same-head source and test provenance; never assert live runtime."""
    _require(
        isinstance(expected_sha, str) and _SHA.fullmatch(expected_sha) is not None,
        "expected full lowercase SHA missing",
    )
    _require(repository == "GBOGEB/ABACUS", "unexpected repository identity")
    _require(
        isinstance(root, dict) and root.get("repo", {}).get("sha") == expected_sha,
        "root source SHA mismatch",
    )
    root_census = _source_census(root, "root")
    nested_census = None
    execution = {
        "diagnostic": "nested_debug_ldab",
        "diagnostic_scope": "FEDERATION_CONTRACT_ONLY",
        "state": "NOT_EXECUTED",
        "contract_checks_total": None,
        "contract_checks_passed": None,
        "contract_checks_failed": None,
        "source_contract": None,
        "source_contract_sha256": None,
    }
    if nested is not None:
        _require(
            isinstance(nested, dict)
            and nested.get("surface", {}).get("parent_sha") == expected_sha
            and nested.get("surface", {}).get("path")
            == "integration/codespace_jyperter",
            "nested source identity mismatch",
        )
        nested_census = _source_census(nested, "nested")
        _require(isinstance(diagnostic, dict), "nested executed diagnostic missing")
        checks = diagnostic.get("checks")
        _require(
            diagnostic.get("diagnostic") == "nested_debug_ldab"
            and diagnostic.get("repository") == repository
            and diagnostic.get("parent_sha") == expected_sha
            and diagnostic.get("source_contract") == _CONTRACT
            and isinstance(diagnostic.get("source_contract_sha256"), str)
            and _SHA256.fullmatch(diagnostic["source_contract_sha256"]) is not None,
            "nested diagnostic identity or contract mismatch",
        )
        _require(
            isinstance(checks, dict) and len(checks) > 0
            and all(type(value) is bool for value in checks.values()),
            "nested diagnostic check denominator invalid",
        )
        failed = sorted(name for name, result in checks.items() if not result)
        _require(
            not failed and diagnostic.get("failed_checks") == []
            and diagnostic.get("verification") == "PASS",
            "nested executed federation diagnostic failed",
        )
        execution = {
            "diagnostic": "nested_debug_ldab",
            "diagnostic_scope": "FEDERATION_CONTRACT_ONLY",
            "state": "EXECUTED_PASS",
            "contract_checks_total": len(checks),
            "contract_checks_passed": len(checks),
            "contract_checks_failed": 0,
            "source_contract": _CONTRACT,
            "source_contract_sha256": diagnostic["source_contract_sha256"],
        }
    else:
        _require(diagnostic is None, "orphan nested diagnostic receipt")

    return {
        "schema": "mip.ldab.telemetry.v1",
        "repository": repository,
        "source_sha": expected_sha,
        "source_census": {
            "root": root_census,
            "nested": nested_census,
            "combined_candidates": None,
            "combined_is_disjoint": False,
            "candidate_files_are_not_sessions": True,
        },
        "diagnostic_execution": execution,
        "runtime": {
            "abacus_native_debug_sessions": None,
            "authenticated_port_leases": None,
            "active_runner_workers": None,
            "ldab_verified_repairs": None,
            "debug_probe_steps": None,
            "proof_state": "UNKNOWN_NO_RUNTIME_RECEIPT",
        },
        "claims": {
            "source_discovery": "OBSERVED",
            "nested_contract_diagnostic": execution["state"],
            "native_lldb_dap": "UNKNOWN",
            "docker_port": "UNKNOWN",
            "worker_repair": "UNKNOWN",
        },
        "raw_receipt_retention": "transient_runner_only",
        "authority_transfer": False,
        "security_waiver": False,
        "merge_admission": "HOLD",
    }


def stable_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
