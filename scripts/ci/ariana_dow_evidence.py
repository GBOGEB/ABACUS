#!/usr/bin/env python3
"""Source-bound Ariana/DOW CI evidence; read-only KEB/QPS federation projection.

No remote execution, remote trust promotion, deployment, or secondary SSOT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml


SOURCE_PATH = Path("DMAIC_V3/core/dow_ariana_integration.py")
BRIDGE_PATH = Path("DMAIC_V3/core/test_system_bridge.py")
DOCK_PATH = Path(".mesh/MESH_DOCK.yaml")
RECEIVER_PATH = Path("architecture/w112/W112_GLOBAL_HIVE_GLOB_DOW_RECEIVER.yaml")
TEST_PATHS = (
    Path("DMAIC_V3/tests/test_dow_ariana_integration_runtime_coverage.py"),
    Path("tests/test_dow_ariana_changed_line_coverage.py"),
    Path("tests/test_ariana_ci_federation.py"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_checkout(root: Path, expected_sha: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("source SHA must be full 40-character lowercase hex")
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=10
    ).strip()
    if actual != expected_sha:
        raise ValueError(f"stale or unexpected checkout: {actual} != {expected_sha}")
    return actual


def validate_local_contract(root: Path) -> dict:
    required = (SOURCE_PATH, BRIDGE_PATH, DOCK_PATH, RECEIVER_PATH, *TEST_PATHS)
    missing = [str(p) for p in required if not (root / p).is_file()]
    if missing:
        raise ValueError(f"missing source-owned inputs: {', '.join(missing)}")
    with (root / DOCK_PATH).open(encoding="utf-8") as stream:
        dock = yaml.safe_load(stream)
    with (root / RECEIVER_PATH).open(encoding="utf-8") as stream:
        receiver = yaml.safe_load(stream)
    if not isinstance(dock, dict) or not isinstance(receiver, dict):
        raise ValueError("invalid DOW/KEB YAML structure")
    if dock.get("repo") != "GBOGEB/ABACUS":
        raise ValueError("ABACUS runtime ownership changed")
    if receiver.get("consumer") != "GBOGEB/ABACUS":
        raise ValueError("DOW receiver ownership changed")
    if receiver.get("producer", {}).get("repo") != "GBOGEB/CODEX":
        raise ValueError("KEB producer is not CODEX")
    namespace = receiver.get("namespace_invariant", {})
    status_keys = namespace.get("status_keys", [])
    action_monikers = namespace.get("action_monikers", [])
    if (
        not isinstance(status_keys, list)
        or not isinstance(action_monikers, list)
        or not status_keys
        or not action_monikers
        or not set(status_keys).isdisjoint(action_monikers)
        or namespace.get("intersection_must_be_empty") is not True
    ):
        raise ValueError("KEB status keys collide with action monikers")
    if "promote_QPS_engineering_truth" not in dock.get("authority", {}).get("must_not", []):
        raise ValueError("QPS engineering authority boundary not preserved")
    return {
        "runtime_owner": dock["repo"],
        "semantic_owner": receiver["producer"]["repo"],
        "engineering_owner": "GBOGEB/cryoplant-project",
        "local_sources_sha256": {
            str(p): digest(root / p)
            for p in (SOURCE_PATH, BRIDGE_PATH, DOCK_PATH, RECEIVER_PATH)
        },
        "namespace_status_key_count": len(status_keys),
        "namespace_action_moniker_count": len(action_monikers),
        "namespace_collision_count": 0,
    }


def read_junit(path: Path) -> dict | None:
    if not path.is_file():
        return None
    xml_root = ET.parse(path).getroot()
    cases = list(xml_root.iter("testcase"))
    total = len(cases)
    failures = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    if total == 0 or failures + errors + skipped > total:
        raise ValueError("empty or contradictory JUnit test population")
    return {
        "total": total,
        "passed": total - failures - errors - skipped,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "junit_sha256": digest(path),
    }


def read_focused_coverage(path: Path) -> dict | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = [
        value.get("summary", {})
        for name, value in data.get("files", {}).items()
        if Path(name).name == SOURCE_PATH.name
    ]
    if len(matches) != 1:
        raise ValueError("coverage source binding is missing or ambiguous")
    summary = matches[0]
    sl = int(summary["covered_lines"])
    sd = int(summary["num_statements"])
    bl = int(summary["covered_branches"])
    bd = int(summary["num_branches"])
    if sd < 1 or bd < 1 or sl < 0 or bl < 0 or sl > sd or bl > bd:
        raise ValueError("invalid measured statement/branch denominator")
    return {
        "scope": str(SOURCE_PATH),
        "statements": {"numerator": sl, "denominator": sd},
        "branches": {"numerator": bl, "denominator": bd},
        "combined": {"numerator": sl + bl, "denominator": sd + bd},
        "coverage_json_sha256": digest(path),
        "changed_line": None,
        "changed_line_reason": "PRODUCTION_SOURCE_UNCHANGED_IN_THIS_PR",
    }


def build_receipt(root: Path, expected_sha: str, junit: Path, coverage: Path) -> dict:
    source_sha = exact_checkout(root, expected_sha)
    local = validate_local_contract(root)
    tests = read_junit(junit)
    measured = read_focused_coverage(coverage)
    proven = (
        tests is not None
        and tests["total"] > 0
        and tests["failures"] == 0
        and tests["errors"] == 0
        and tests["skipped"] == 0
        and measured is not None
    )
    return {
        "schema": "abacus.ariana_dow_ci_federation_projection.v1",
        "producer": {
            "repository": "GBOGEB/ABACUS",
            "source_sha": source_sha,
            "run_id": os.getenv("GITHUB_RUN_ID") or None,
            "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT") or None,
            "job_id": os.getenv("GITHUB_JOB") or None,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        "local_contract": local,
        "native_test_receipt": tests,
        "focused_coverage": measured,
        "disposition": "LOCAL_TESTED_FEDERATION_HOLD" if proven else "EVIDENCE_WITHHELD",
        "federation": {
            "DOW": {"owner": "GBOGEB/ABACUS", "status": "SOURCE_BOUND_LOCAL"},
            "KEB": {
                "owner": "GBOGEB/CODEX",
                "contract": "federation/mesh/GLOBAL_ACTION_TAXONOMY_v1.yaml",
                "status": "DECLARED_ONLY_REMOTE_NOT_ATTESTED",
            },
            "QPS": {
                "owner": "GBOGEB/cryoplant-project",
                "status": "DECLARED_ONLY_REMOTE_NOT_ATTESTED",
            },
        },
        "dag": {
            "nodes": ["ABACUS_SOURCE", "DOW_TEST_BRIDGE", "KEB_SEMANTICS", "QPS_ENGINEERING"],
            "edges": [
                {"source": "ABACUS_SOURCE", "target": "DOW_TEST_BRIDGE",
                 "evidence": "NATIVE_LOCAL_TEST" if proven else "UNVERIFIED"},
                {"source": "DOW_TEST_BRIDGE", "target": "KEB_SEMANTICS",
                 "evidence": "DECLARED_NON_EXECUTED"},
                {"source": "KEB_SEMANTICS", "target": "QPS_ENGINEERING",
                 "evidence": "DECLARED_NON_EXECUTED"},
            ],
        },
        "sipoc": {
            "suppliers": ["ABACUS_source_owner", "CODEX_KEB_semantic_owner", "QPS_child_owner"],
            "inputs": ["exact_checkout", "local_DOW_bridge", "JUnit", "coverage_json"],
            "process": "source_preflight_then_real_tests_then_read_only_projection",
            "outputs": ["native_test_receipt", "focused_coverage", "DAG_projection"],
            "customers": ["ABACUS_DOW", "CODEX_KEB", "QPS_child_for_later_independent_review"],
        },
        "governance": {
            "merge_admission": "HOLD",
            "independent_review": None,
            "security_waiver": False,
            "authority_transfer": False,
            "remote_crew_dispatch": False,
            "keb_acceptance": None,
            "qps_engineering_acceptance": None,
            "global_federation_execution_verified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    try:
        if args.preflight:
            sha = exact_checkout(root, args.source_sha)
            contract = validate_local_contract(root)
            print(json.dumps({"source_sha": sha, "preflight": "PASS",
                              "contract": contract}, sort_keys=True))
            return 0
        if args.junit is None or args.coverage is None or args.out is None:
            parser.error("receipt requires --junit, --coverage, and --out")
        receipt = build_receipt(root, args.source_sha, args.junit, args.coverage)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(f"ARIANA_DOW_RECEIPT={receipt['disposition']} / {args.out}")
        if args.strict and receipt["disposition"] != "LOCAL_TESTED_FEDERATION_HOLD":
            return 1
        return 0
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, subprocess.SubprocessError) as error:
        print(f"ARIANA_DOW_FAIL_CLOSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
