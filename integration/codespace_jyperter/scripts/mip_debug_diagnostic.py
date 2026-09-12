#!/usr/bin/env python3
"""Emit a sanitized exact-SHA diagnostic receipt for codespace_jyperter.

The diagnostic binds operational federation health to the existing smoke
contract while keeping inherited repository-name drift observational rather
than mutating the global topology inside this local N2 pulse.  It persists no
local paths, remotes, branches, or raw runner state and is intentionally
stdlib-only for execution in the dedicated MIP N2 workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SURFACE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SURFACE_ROOT.parents[1]
DEFAULT_OUTPUT = SURFACE_ROOT / "MIP" / "receipts" / "nested_debug_diagnostic.json"
SURFACE_PATH = "integration/codespace_jyperter"
SOURCE_CONTRACT = f"{SURFACE_PATH}/tests/test_smoke_federation.py"
INTEGRATION_MEMBER = "GBOGEB/codespace_jyperter"
GLOBAL_MEMBER_ALIASES = (INTEGRATION_MEMBER, "GBOGEB/CODESPACES_jyperter")


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_receipt() -> dict[str, Any]:
    parent_sha = git("rev-parse", "HEAD")
    integration_manifest = SURFACE_ROOT / "federation" / "manifest.yaml"
    federation_spec = REPO_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"
    global_manifest = REPO_ROOT / "federation" / "manifest.yaml"
    smoke_contract = SURFACE_ROOT / "tests" / "test_smoke_federation.py"

    integration_text = (
        integration_manifest.read_text(encoding="utf-8", errors="ignore")
        if integration_manifest.is_file()
        else ""
    )
    global_text = (
        global_manifest.read_text(encoding="utf-8", errors="ignore")
        if global_manifest.is_file()
        else ""
    )
    detected_global_member = next(
        (name for name in GLOBAL_MEMBER_ALIASES if name in global_text),
        None,
    )

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    federation = importlib.import_module("integration.codespace_jyperter.src.federation")
    assimilated = federation.assimilate(
        context={"session": "mip-debug-diagnostic", "parent_sha": parent_sha}
    )

    checks = {
        "integration_manifest_exists": integration_manifest.is_file(),
        "federation_spec_exists": federation_spec.is_file(),
        "global_manifest_exists": global_manifest.is_file(),
        "smoke_contract_exists": smoke_contract.is_file(),
        "integration_manifest_has_federation": "federation" in integration_text,
        "integration_manifest_lists_self": INTEGRATION_MEMBER in integration_text,
        "global_manifest_registers_notebook_surface": detected_global_member is not None,
        "assimilate_returns_mapping": isinstance(assimilated, dict),
        "assimilate_repo": assimilated.get("repo") == INTEGRATION_MEMBER,
        "assimilate_plane": assimilated.get("plane") == "auxiliary",
        "assimilate_status": assimilated.get("status") == "ok",
        "assimilate_manifest_found": assimilated.get("manifest_found") is True,
        "assimilate_spec_found": assimilated.get("spec_found") is True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)

    return {
        "schema_version": "0.1",
        "program": "MIP",
        "diagnostic": "nested_debug_ldab",
        "verification": "PASS" if not failed else "FAIL",
        "repository": "GBOGEB/ABACUS",
        "surface": SURFACE_PATH,
        "parent_sha": parent_sha,
        "source_contract": SOURCE_CONTRACT,
        "source_contract_sha256": file_digest(smoke_contract) if smoke_contract.is_file() else None,
        "checks": checks,
        "failed_checks": failed,
        "observations": {
            "integration_member_name": INTEGRATION_MEMBER,
            "global_member_name_detected": detected_global_member,
            "global_member_name_aligned": detected_global_member == INTEGRATION_MEMBER,
            "global_member_name_drift_class": (
                "NONE"
                if detected_global_member == INTEGRATION_MEMBER
                else "INHERITED_TOPOLOGY_ALIAS"
            ),
        },
        "raw_receipt_retention": "transient_runner_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the codespace_jyperter exact-SHA debug diagnostic receipt."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    receipt = build_receipt()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "diagnostic": receipt["diagnostic"],
                "verification": receipt["verification"],
                "parent_sha": receipt["parent_sha"],
                "checks": len(receipt["checks"]),
                "failed_checks": receipt["failed_checks"],
                "global_member_name_drift_class": receipt["observations"][
                    "global_member_name_drift_class"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if receipt["verification"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
