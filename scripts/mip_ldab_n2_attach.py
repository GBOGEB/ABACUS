#!/usr/bin/env python3
"""Attach the ABACUS LDAB telemetry block to a MIP N2 verifier summary.

The canonical MIP kit (``scripts/mip_verify_self_index.py``, copied unchanged
from GBOGEB/CODEX and pinned by ``MIP/kit/KIT_MANIFEST.json``) does not emit
``ldab_telemetry``. ABACUS's N2 consumer job, the everred spine census and the
MCW receipt adapters read that block, so this repo-local step rebuilds it on
the same exact SHA and adds it to the kit verifier's sanitized summary.

Inputs are produced in a temporary directory only; nothing is written to the
source checkout. The function fails closed on any SHA or inventory mismatch.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SURFACE_CONFIG = ROOT / "MIP" / "mip_surface.json"
LANE = "repo_self_assess_debug_ldab"
NESTED_PATH = "integration/codespace_jyperter"
ROOT_SAMPLE_LIMIT = 20


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def root_debug_receipt(emitter: ModuleType, sha: str) -> dict[str, Any]:
    """Root debug lane with the complete candidate inventory.

    The kit emitter samples at most 20 paths. Its own ``classify`` is run with
    an unbounded ``sample`` so the full list comes from the kit's needles, not
    a copy of them, and the bounded sample is checked to be its prefix.
    """
    files = emitter.iter_files()
    bounded = emitter.classify(files, None)[LANE]
    original_sample = emitter.sample
    emitter.sample = lambda paths, limit=None: [p.as_posix() for p in paths]
    try:
        full = emitter.classify(files, None)[LANE]["sample_paths"]
    finally:
        emitter.sample = original_sample
    if (
        len(full) != bounded["signals"]
        or full[:ROOT_SAMPLE_LIMIT] != bounded["sample_paths"]
    ):
        raise SystemExit("root LDAB inventory does not match the kit emitter sample")
    return {
        "repo": {"sha": sha},
        "assessments": {
            LANE: {
                "status": bounded["status"],
                "signals": bounded["signals"],
                "sample_paths": bounded["sample_paths"],
                "all_candidate_paths": full,
            }
        },
    }


def _run(script: Path, output: Path) -> dict[str, Any]:
    subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return json.loads(output.read_text(encoding="utf-8"))


def nested_inputs(
    surface: dict[str, Any], tmp: Path
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    rows = [
        row
        for row in surface.get("nested_surfaces", [])
        if isinstance(row, dict) and row.get("path") == NESTED_PATH
    ]
    if not rows:
        return None, None
    row = rows[0]
    nested = _run(ROOT / row["emitter"], tmp / "nested.json")
    diagnostic = None
    if row.get("diagnostic"):
        diagnostic = _run(ROOT / row["diagnostic"], tmp / "nested-diagnostic.json")
    return nested, diagnostic


def attach(
    summary: dict[str, Any], surface: dict[str, Any], tmp: Path
) -> dict[str, Any]:
    sha = _git_head()
    if summary.get("verification") != "PASS" or summary.get("head_sha") != sha:
        raise SystemExit("kit verifier summary is not a PASS for the current HEAD")
    emitter = _load("mip_repo_self_index", SCRIPTS / "mip_repo_self_index.py")
    telemetry = _load("mip_ldab_telemetry", SCRIPTS / "mip_ldab_telemetry.py")
    root = root_debug_receipt(emitter, sha)
    root_status = summary.get("root_self_index", {}).get("assessments", {}).get(LANE)
    if root_status != str(root["assessments"][LANE]["status"]).upper():
        raise SystemExit("root LDAB status differs from the kit verifier summary")
    nested, diagnostic = nested_inputs(surface, tmp)
    summary["ldab_telemetry"] = telemetry.summarize(
        root,
        nested,
        diagnostic,
        sha,
        os.environ.get("GITHUB_REPOSITORY", "GBOGEB/ABACUS"),
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    surface = json.loads(SURFACE_CONFIG.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="mip-ldab-n2-") as temp:
        attach(summary, surface, Path(temp))
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["ldab_telemetry"]["claims"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
