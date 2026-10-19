#!/usr/bin/env python3
"""Verify MIP self-index exact-SHA binding, repeatability and lane maturity.

This is part of the canonical MIP kit (hosted in GBOGEB/CODEX, pinned by
digest in every federated repository). Repository-specific behaviour comes
only from ``MIP/mip_surface.json``: the health probe, nested surfaces, the
shareable skill path and the ``required_green`` ratchet.

Raw receipts are generated only in a temporary directory. The durable output is
an intentionally sanitized summary that excludes local paths, remotes, branch
names, dirty-file details, and generated raw receipt payloads.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_EMITTER = ROOT / "scripts" / "mip_repo_self_index.py"
SURFACE_CONFIG = ROOT / "MIP" / "mip_surface.json"
KIT_MANIFEST = ROOT / "MIP" / "kit" / "KIT_MANIFEST.json"

INDEX_LANE = "repo_self_index"
HEALTH_LANE = "repo_self_assess_codz_health_selfheal"
PRODUCE_LANE = "repo_self_produce"
DEBUG_LANE = "repo_self_assess_debug_ldab"
RUNNERS_LANE = "repo_self_assess_runners_mcp"
LANES = (INDEX_LANE, DEBUG_LANE, RUNNERS_LANE, HEALTH_LANE, PRODUCE_LANE)

# Lane maturity: 0 missing/red, 1 seeded (heuristic signal only),
# 2 executable (an executed check passed on this exact SHA),
# 3 converged (executable and green on >= 3 distinct SHAs; needs history).
MATURITY_MAX_PER_LANE = 3


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def load_surface(config_path: Path = SURFACE_CONFIG) -> dict[str, Any]:
    """Load the repo-local surface config.

    A repository without ``MIP/mip_surface.json`` gets the neutral default (no
    nested surfaces, no shareable skill, nothing required GREEN), which is the
    pre-kit behaviour of this verifier.
    """
    if not config_path.is_file():
        return {"program": "MIP"}
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"MIP surface config is not valid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("program") != "MIP":
        raise SystemExit("MIP surface config must be an object with program=MIP")
    required_green = value.get("required_green", [])
    if not isinstance(required_green, list):
        raise SystemExit("MIP surface config: required_green must be a list")
    unknown = sorted(set(required_green) - set(LANES))
    if unknown:
        raise SystemExit("unknown required_green lanes: " + ", ".join(unknown))
    nested = value.get("nested_surfaces", [])
    if not isinstance(nested, list) or any(
        not isinstance(item, dict) or not item.get("path") or not item.get("emitter")
        for item in nested
    ):
        raise SystemExit(
            "MIP surface config: nested_surfaces must be a list of objects with path and emitter"
        )
    return value


def run_emitter(script: Path, output: Path) -> dict[str, Any]:
    subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        cwd=ROOT,
        check=True,
    )
    return json.loads(output.read_text(encoding="utf-8"))


def normalized(receipt: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(receipt)
    value.pop("generated_at", None)
    if "repo" in value:
        for key in ("root", "remote", "branch", "dirty_summary"):
            value["repo"].pop(key, None)
    if "surface" in value:
        for key in (
            "parent_repo_root",
            "parent_remote",
            "parent_branch",
            "dirty_summary",
        ):
            value["surface"].pop(key, None)
    return value


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status_map(receipt: dict[str, Any]) -> dict[str, str]:
    return {
        lane: str(details.get("status", "unknown")).upper()
        for lane, details in receipt.get("assessments", {}).items()
    }


def verify_pair(
    emitter: Path,
    first_path: Path,
    second_path: Path,
    actual_sha: str,
    sha_container: str,
    sha_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = run_emitter(emitter, first_path)
    second = run_emitter(emitter, second_path)

    first_sha = first.get(sha_container, {}).get(sha_key)
    second_sha = second.get(sha_container, {}).get(sha_key)
    if first_sha != actual_sha or second_sha != actual_sha:
        raise SystemExit(
            f"self-index SHA mismatch: runtime={actual_sha} "
            f"first={first_sha} second={second_sha}"
        )

    n1 = normalized(first)
    n2 = normalized(second)
    if n1 != n2:
        raise SystemExit(
            "normalized self-index output is not repeatable across two invocations"
        )
    return first, n1


def validate_health_selfheal(
    root_receipt: dict[str, Any],
    root_assessments: dict[str, str],
    actual_sha: str,
) -> dict[str, Any]:
    details = root_receipt.get("assessments", {}).get(HEALTH_LANE, {})
    evidence = details.get("evidence") if isinstance(details, dict) else None

    checks = {
        "root_health_green": root_assessments.get(HEALTH_LANE) == "GREEN",
        "evidence_present": isinstance(evidence, dict),
        "verification": isinstance(evidence, dict)
        and evidence.get("verification") == "PASS",
        "exact_sha": isinstance(evidence, dict)
        and evidence.get("exact_sha") == actual_sha,
        "execution_context": isinstance(evidence, dict)
        and evidence.get("execution_context") == "transient_controlled_fixture",
        "return_state": isinstance(evidence, dict)
        and evidence.get("return_state") == "IMPROVED",
        "delta": isinstance(evidence, dict)
        and type(evidence.get("delta")) is int
        and evidence.get("delta") < 0,
        "checkout_unchanged": isinstance(evidence, dict)
        and evidence.get("source_checkout_unchanged") is True,
        "retention": isinstance(evidence, dict)
        and evidence.get("raw_receipt_retention") == "transient_runner_only",
        "no_promotion_authority": isinstance(evidence, dict)
        and evidence.get("promotion_authority") is False,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise SystemExit("health/self-heal validation failed: " + ", ".join(failed))

    assert isinstance(evidence, dict)
    return {
        "verification": "PASS",
        "exact_sha": actual_sha,
        **{
            key: evidence.get(key)
            for key in (
                "execution_context",
                "source_primitive",
                "repair_class",
                "before_metric",
                "after_metric",
                "delta",
                "metric_direction",
                "return_state",
                "source_checkout_unchanged",
                "raw_receipt_retention",
                "promotion_authority",
            )
        },
    }


def validate_shareable_skill(
    skill_root: Path,
    summary: dict[str, Any],
    temp_root: Path,
    actual_sha: str,
    root_assessments: dict[str, str],
) -> dict[str, Any]:
    entrypoint = skill_root / "SKILL.md"
    agent = skill_root / "agents" / "openai.yaml"
    contract = skill_root / "references" / "receipt-contract.md"
    validator = skill_root / "scripts" / "validate_receipt.py"
    required = [entrypoint, agent, contract, validator]
    skill_text = entrypoint.read_text(encoding="utf-8") if entrypoint.is_file() else ""
    agent_text = agent.read_text(encoding="utf-8") if agent.is_file() else ""
    checks = {
        "entrypoint_exists": entrypoint.is_file(),
        "agent_metadata_exists": agent.is_file(),
        "receipt_contract_exists": contract.is_file(),
        "validator_exists": validator.is_file(),
        "frontmatter_name": "name: mip-repo-self-index" in skill_text,
        "frontmatter_description": "description:" in skill_text,
        "agent_display_name": "MIP Repo Self Index" in agent_text,
        "root_self_produce_green": root_assessments.get(PRODUCE_LANE) == "GREEN",
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise SystemExit(
            "shareable skill package validation failed: " + ", ".join(failed)
        )

    candidate = temp_root / "skill-producer-summary.json"
    candidate.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    completed = subprocess.run(
        [sys.executable, str(validator), str(candidate), "--expected-sha", actual_sha],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    validator_result = json.loads(completed.stdout.strip())
    if validator_result.get("verification") != "PASS":
        raise SystemExit("shareable skill validator did not report PASS")

    package_hashes = {
        str(path.relative_to(ROOT)): file_digest(path) for path in required
    }
    return {
        "path": str(skill_root.relative_to(ROOT)),
        "name": "mip-repo-self-index",
        "verification": "PASS",
        "validated_head_sha": actual_sha,
        "validator": str(validator.relative_to(ROOT)),
        "package_files": sorted(package_hashes),
        "package_file_sha256": package_hashes,
        "package_digest_sha256": digest(package_hashes),
        "validator_result": validator_result,
        "raw_receipt_retention": "transient_runner_only",
    }


def verify_nested_surfaces(
    surfaces: list[dict[str, Any]], tmp: Path, actual_sha: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nested_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    for index, surface in enumerate(surfaces):
        path = str(surface["path"])
        emitter = ROOT / surface["emitter"]
        if not emitter.is_file():
            raise SystemExit(
                f"declared nested surface emitter is missing: {surface['emitter']}"
            )
        receipt, norm = verify_pair(
            emitter,
            tmp / f"nested-{index}-1.json",
            tmp / f"nested-{index}-2.json",
            actual_sha,
            "surface",
            "parent_sha",
        )
        assessments = status_map(receipt)
        nested_rows.append(
            {
                "path": path,
                "runs": 2,
                "normalized_equal": True,
                "digest_sha256": digest(norm),
                "file_count": receipt.get("census", {}).get("file_count"),
                "assessments": assessments,
            }
        )
        if not surface.get("diagnostic"):
            continue
        diagnostic = run_emitter(
            ROOT / surface["diagnostic"], tmp / f"nested-{index}-diagnostic.json"
        )
        if diagnostic.get("parent_sha") != actual_sha:
            raise SystemExit(
                "nested diagnostic SHA mismatch: "
                f"runtime={actual_sha} diagnostic={diagnostic.get('parent_sha')}"
            )
        if diagnostic.get("verification") != "PASS":
            failed = ", ".join(diagnostic.get("failed_checks", [])) or "unknown"
            raise SystemExit(f"nested diagnostic failed: {failed}")
        if assessments.get(DEBUG_LANE) != "GREEN":
            raise SystemExit(
                "nested diagnostic exists and passes but debug/LDAB assessment is not GREEN"
            )
        diagnostic_rows.append(
            {
                "surface": path,
                "diagnostic": diagnostic.get("diagnostic"),
                "verification": diagnostic.get("verification"),
                "parent_sha": diagnostic.get("parent_sha"),
                "source_contract": diagnostic.get("source_contract"),
                "source_contract_sha256": diagnostic.get("source_contract_sha256"),
                "passed_checks": sorted(
                    name
                    for name, passed in diagnostic.get("checks", {}).items()
                    if passed
                ),
                "raw_receipt_retention": diagnostic.get("raw_receipt_retention"),
            }
        )
    return nested_rows, diagnostic_rows


def lane_maturity(
    assessments: dict[str, str],
    *,
    health_executed: bool,
    skill_executed: bool,
    diagnostic_executed: bool,
) -> dict[str, int]:
    """Score each lane 0-2 from what this run actually executed.

    Level 3 (converged across distinct SHAs) is assigned by the history roll-up,
    never by a single run.
    """

    def heuristic(lane: str) -> int:
        return 1 if assessments.get(lane) in {"GREEN", "AMBER"} else 0

    executed = {
        DEBUG_LANE: diagnostic_executed,
        RUNNERS_LANE: False,
        HEALTH_LANE: health_executed,
        PRODUCE_LANE: skill_executed,
    }
    scores = {INDEX_LANE: 2}
    for lane, ran in executed.items():
        scores[lane] = (
            2 if ran and assessments.get(lane) == "GREEN" else heuristic(lane)
        )
    return scores


def kit_identity() -> dict[str, Any] | None:
    if not KIT_MANIFEST.is_file():
        return None
    manifest = json.loads(KIT_MANIFEST.read_text(encoding="utf-8"))
    return {
        "kit_version": manifest.get("kit_version"),
        "kit_digest_sha256": manifest.get("kit_digest_sha256"),
        "source": manifest.get("source"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify exact-SHA MIP self-index evidence."
    )
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    surface = load_surface()
    required_green = list(surface.get("required_green", []))

    actual_sha = git("rev-parse", "HEAD")
    expected_sha = os.environ.get("EXPECTED_SHA", actual_sha).strip()
    if expected_sha != actual_sha:
        raise SystemExit(
            f"checkout SHA mismatch: expected={expected_sha} actual={actual_sha}"
        )

    with tempfile.TemporaryDirectory(prefix="mip-n2-") as temp:
        tmp = Path(temp)
        root_receipt, root_norm = verify_pair(
            ROOT_EMITTER,
            tmp / "root-1.json",
            tmp / "root-2.json",
            actual_sha,
            "repo",
            "sha",
        )
        root_assessments = status_map(root_receipt)

        summary: dict[str, Any] = {
            "schema_version": "0.1",
            "program": "MIP",
            "verification": "PASS",
            "repository": os.environ.get(
                "GITHUB_REPOSITORY", surface.get("repository", ROOT.name)
            ),
            "head_sha": actual_sha,
            "surface_role": surface.get("role"),
            "surface_config_sha256": (
                file_digest(SURFACE_CONFIG) if SURFACE_CONFIG.is_file() else None
            ),
            "kit": kit_identity(),
            "root_self_index": {
                "runs": 2,
                "normalized_equal": True,
                "digest_sha256": digest(root_norm),
                "file_count": root_receipt.get("census", {}).get("file_count"),
                "assessments": root_assessments,
            },
            "raw_receipt_retention": "transient_runner_only",
        }

        health_evidence = (
            root_receipt.get("assessments", {}).get(HEALTH_LANE, {}).get("evidence")
        )
        health_executed = False
        if health_evidence is not None or HEALTH_LANE in required_green:
            summary["health_selfheal"] = validate_health_selfheal(
                root_receipt, root_assessments, actual_sha
            )
            health_executed = True

        nested_rows, diagnostic_rows = verify_nested_surfaces(
            list(surface.get("nested_surfaces", [])), tmp, actual_sha
        )
        if nested_rows:
            summary["nested_surfaces"] = nested_rows
            # Backwards-compatible single-surface keys for existing consumers.
            summary["nested_surface"] = nested_rows[0]
        if diagnostic_rows:
            summary["nested_diagnostics"] = diagnostic_rows
            summary["nested_diagnostic"] = diagnostic_rows[0]

        skill_executed = False
        skill_path = surface.get("shareable_skill")
        if skill_path and (ROOT / skill_path).is_dir():
            summary["shareable_skill"] = validate_shareable_skill(
                ROOT / skill_path, summary, tmp, actual_sha, root_assessments
            )
            skill_executed = True
        elif PRODUCE_LANE in required_green:
            raise SystemExit(
                "repo_self_produce is required GREEN but no shareable skill is declared"
            )

        not_green = sorted(
            lane
            for lane in required_green
            if lane != INDEX_LANE and root_assessments.get(lane) != "GREEN"
        )
        if not_green:
            raise SystemExit(
                "required_green lanes are not GREEN: " + ", ".join(not_green)
            )

        maturity = lane_maturity(
            root_assessments,
            health_executed=health_executed,
            skill_executed=skill_executed,
            diagnostic_executed=bool(diagnostic_rows),
        )
        summary["required_green"] = sorted(required_green)
        summary["lane_maturity"] = maturity
        summary["maturity_score"] = sum(maturity.values())
        summary["maturity_max"] = MATURITY_MAX_PER_LANE * len(LANES)

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
