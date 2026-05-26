#!/usr/bin/env python3
"""Build dynamic tracker metadata consumed by docs/FINAL_HANDOVER.html."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.tuple_metadata import default_status_schema, validate_tracker_payload  # noqa: E402


def _load_phase2_manifest() -> dict:
    manifest = ROOT_DIR / "docs" / "api" / "phase2_reconstruction_manifest.json"
    if not manifest.exists():
        return {"manifest_version": "missing", "component_count": 0}
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return {
        "manifest_version": payload.get("manifest_version", "unknown"),
        "component_count": len(payload.get("component_map", [])),
        "artifact_count": len(payload.get("artifacts", [])),
    }


def _ci_status() -> str:
    raw = os.getenv("GITHUB_JOB_STATUS", "").lower().strip()
    if raw == "success":
        return "validated"
    if raw in {"failure", "cancelled"}:
        return "blocked"
    return "in_progress"


def _current_branch() -> str:
    return os.getenv("GITHUB_REF_NAME") or os.getenv("BRANCH_NAME") or "local"


def _reviewed_branches(current_branch: str) -> list[str]:
    reviewed = [b.strip() for b in os.getenv("ABACUS_REVIEWED_BRANCHES", "main,develop").split(",") if b.strip()]
    if current_branch not in reviewed:
        reviewed.append(current_branch)
    return sorted(set(reviewed))


def build_payload() -> dict:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    current_branch = _current_branch()
    reviewed_branches = _reviewed_branches(current_branch)
    ci_status = _ci_status()
    phase2 = _load_phase2_manifest()

    branches = []
    for name in reviewed_branches:
        branches.append(
            {
                "name": name,
                "reviewed": name in {"main", "develop"},
                "status": "validated" if name in {"main", "develop"} else ci_status,
            }
        )

    run_repository = os.getenv("GITHUB_REPOSITORY", "GBOGEB/ABACUS")
    run_id = os.getenv("GITHUB_RUN_ID", "0")

    return {
        "generated_at": now,
        "status_schema": list(default_status_schema()),
        "ci_pipeline": {
            "workflow": os.getenv("GITHUB_WORKFLOW", "local"),
            "run_id": os.getenv("GITHUB_RUN_ID", "local"),
            "run_number": os.getenv("GITHUB_RUN_NUMBER", "0"),
            "event": os.getenv("GITHUB_EVENT_NAME", "manual"),
            "sha": os.getenv("GITHUB_SHA", "local"),
            "branch": current_branch,
            "status": ci_status,
            "run_url": f"https://github.com/{run_repository}/actions/runs/{run_id}",
        },
        "modules": [
            {"name": "E6 Modules", "status": "in_progress", "link": "../README.md"},
            {"name": "HTML Tools", "status": "validated", "link": "FINAL_HANDOVER.html"},
            {"name": "Python Tools", "status": "in_progress", "link": "tools/index.html"},
            {
                "name": "Phase-2 Reconstruction",
                "status": "validated" if phase2.get("component_count", 0) else "in_progress",
                "link": "api/phase2_reconstruction_manifest.json",
            },
        ],
        "branches": branches,
        "tuple_metadata": [
            {
                "tuple_id": "tuple-ci-validation",
                "source": ".github/workflows/ci.yml",
                "validation_log": "CI job: Validate tuple metadata tracker payload",
                "downstream_consumer": "docs/FINAL_HANDOVER.html",
                "status": ci_status,
            },
            {
                "tuple_id": "tuple-artifact-export",
                "source": "scripts/validate_tuple_metadata.py",
                "validation_log": "validated tuple metadata artifact",
                "downstream_consumer": "DMAIC_V3_OUTPUT/tuple_metadata.validated.json",
                "status": "validated" if ci_status == "validated" else "in_progress",
            },
            {
                "tuple_id": "tuple-reconstruction-manifest",
                "source": "scripts/validate_reconstruction_manifest.py",
                "validation_log": f"phase2 components: {phase2.get('component_count', 0)}",
                "downstream_consumer": "DMAIC_V3_OUTPUT/reconstruction_manifest.validated.json",
                "status": "validated" if phase2.get("component_count", 0) else "in_progress",
            },
        ],
        "integration_bridges": [
            {
                "repository": "GBOGEB/CODEX",
                "bridge": ".github/workflows/ci-codex.yml",
                "shared_source": "docs/workflows + contract tooling",
            },
            {
                "repository": "GBOGEB/morris.js",
                "bridge": "docs dashboards",
                "shared_source": "HTML visualization patterns",
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FINAL_HANDOVER tracker metadata")
    parser.add_argument("--output", default="docs/api/final_handover_tracker.json")
    args = parser.parse_args()

    payload = build_payload()
    errors = validate_tracker_payload(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    output = ROOT_DIR / args.output if not Path(args.output).is_absolute() else Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[OK] Wrote tracker metadata: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
