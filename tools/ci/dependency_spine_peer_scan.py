#!/usr/bin/env python3
"""Fail-closed native peer census for QPS Dependency SPINE W+1.

This is a nonauthoritative operational probe, not a reusable SSOT, an updater,
a cross-repository scanner, or an admission decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SCHEMA = "qps.dependency_spine.peer_census.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)")
ECO = re.compile(r"^\s*-\s*package-ecosystem:\s*['\"]?([a-zA-Z0-9_-]+)")
DIR = re.compile(r"^\s*directory:\s*['\"]?([^\s'\"#]+)")
ALLOWED = frozenset(
    {
        "GBOGEB/ABACUS",
        "GBOGEB/CODEX",
        "GBOGEB/pipeline-automation-hub",
        "GBOGEB/gg_MATH",
    }
)


def canonical(data: dict) -> bytes:
    return (
        json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    sha = result.stdout.strip().lower() if result.returncode == 0 else ""
    return sha if SHA.fullmatch(sha) else ""


def parse_config(text: str) -> list[dict]:
    items: list[dict] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = ECO.match(line)
        if m:
            items.append({"ecosystem": m.group(1), "directory": None})
            continue
        m = DIR.match(line)
        if m and items and items[-1]["directory"] is None:
            items[-1]["directory"] = m.group(1)
    return items


def parse_actions(text: str, filename: str) -> list[dict]:
    rows = []
    for index, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        match = USES.match(line)
        if match:
            ref = match.group(1)
            rows.append(
                {
                    "file": filename,
                    "line": index,
                    "ref": ref,
                    "kind": (
                        "local"
                        if ref.startswith("./")
                        else "container" if ref.startswith("docker://") else "external"
                    ),
                }
            )
    return rows


def observe(
    root: Path, repo: str, expected_sha: str, *, observed_sha: str | None = None
) -> dict:
    if repo not in ALLOWED:
        raise ValueError("REPOSITORY_NOT_IN_FLEET")
    if not SHA.fullmatch(expected_sha):
        raise ValueError("BAD_EXPECTED_SHA")
    actual = observed_sha if observed_sha is not None else git_head(root)
    if actual != expected_sha:
        raise ValueError("EXACT_HEAD_MISMATCH")
    directory = root / ".github" / "workflows"
    files = (
        sorted(
            p
            for p in directory.iterdir()
            if p.is_file() and p.suffix in {".yaml", ".yml"}
        )
        if directory.is_dir()
        else []
    )
    actions = [
        ref
        for path in files
        for ref in parse_actions(path.read_text(encoding="utf-8"), path.name)
    ]
    cfg = next(
        (
            p
            for p in (
                root / ".github" / "dependabot.yml",
                root / ".github" / "dependabot.yaml",
            )
            if p.is_file()
        ),
        None,
    )
    ecosystems = parse_config(cfg.read_text(encoding="utf-8")) if cfg else []
    return {
        "schema": SCHEMA,
        "repo": repo,
        "head_sha": expected_sha,
        "exact_head_verified": True,
        "source_scope": "ROOT_DEPENDABOT_AND_TOP_LEVEL_ACTIONS_WORKFLOWS",
        "workflow_count": len(files),
        "workflow_filenames": [p.name for p in files],
        "action_references": actions,
        "action_reference_count": len(actions),
        "distinct_reference_count": len({x["ref"] for x in actions}),
        "checkout_refs": sorted(
            {x["ref"] for x in actions if x["ref"].startswith("actions/checkout@")}
        ),
        "dependabot_present": cfg is not None,
        "dependabot_path": cfg.relative_to(root).as_posix() if cfg else None,
        "dependabot_ecosystems": ecosystems,
        "measurement": {
            "configuration_presence": int(cfg is not None),
            "reference_upgrade_coverage_pct": None,
            "native_upgrade_success_pct": None,
            "compatibility_pass_pct": None,
            "branch_statement_coverage_pct": None,
            "cross_repository_consumption_pct": None,
        },
        "runtime_proof": "NATIVE_SCAN_JOB_ONLY_NOT_DEPENDABOT_UPGRADE_PROOF",
        "governance": {
            "authority_transfer": False,
            "remote_dispatch_authorized": False,
            "mutation_enabled": False,
            "merge_admission": "HOLD",
            "qps_engineering_credit_delta": 0,
            "formal_credit_delta": 0,
        },
    }


def build(out: Path, root: Path, repo: str, expected_sha: str) -> dict:
    observation = observe(root, repo, expected_sha)
    out.mkdir(parents=True, exist_ok=True)
    data = canonical(observation)
    (out / "PEER_CENSUS.json").write_bytes(data)
    manifest = {
        "schema": "qps.dependency_spine.peer_sha256.v1",
        "repo": repo,
        "head_sha": expected_sha,
        "files": {"PEER_CENSUS.json": digest(data)},
        "qualified_status": "LEXICAL_CENSUS_ONLY",
    }
    (out / "PEER_SHA256.json").write_bytes(canonical(manifest))
    return observation


def verify(out: Path, repo: str, expected_sha: str) -> None:
    manifest = json.loads((out / "PEER_SHA256.json").read_text(encoding="utf-8"))
    data = (out / "PEER_CENSUS.json").read_bytes()
    receipt = json.loads(data)
    if manifest.get("schema") != "qps.dependency_spine.peer_sha256.v1":
        raise ValueError("MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("files") != {"PEER_CENSUS.json": digest(data)}:
        raise ValueError("DIGEST_MISMATCH")
    if not all(
        x == expected_sha for x in (manifest.get("head_sha"), receipt.get("head_sha"))
    ):
        raise ValueError("HEAD_IDENTITY_MISMATCH")
    if manifest.get("repo") != repo or receipt.get("repo") != repo:
        raise ValueError("REPO_IDENTITY_MISMATCH")
    g = receipt.get("governance")
    if g != {
        "authority_transfer": False,
        "remote_dispatch_authorized": False,
        "mutation_enabled": False,
        "merge_admission": "HOLD",
        "qps_engineering_credit_delta": 0,
        "formal_credit_delta": 0,
    }:
        raise ValueError("GOVERNANCE_PROMOTION_FORBIDDEN")
    if (
        receipt.get("runtime_proof")
        != "NATIVE_SCAN_JOB_ONLY_NOT_DEPENDABOT_UPGRADE_PROOF"
    ):
        raise ValueError("RUNTIME_PROMOTION_FORBIDDEN")
    if manifest.get("qualified_status") != "LEXICAL_CENSUS_ONLY":
        raise ValueError("QUALIFICATION_PROMOTION_FORBIDDEN")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--expected-sha", required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = build(a.out, a.root.resolve(), a.repo, a.expected_sha)
    verify(a.out, a.repo, a.expected_sha)
    print(
        json.dumps(
            {
                "status": "PASS_READONLY_LEXICAL",
                "repo": a.repo,
                "head_sha": a.expected_sha,
                "workflow_count": result["workflow_count"],
                "action_reference_count": result["action_reference_count"],
                "dependabot_present": result["dependabot_present"],
                "formal_credit_delta": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
