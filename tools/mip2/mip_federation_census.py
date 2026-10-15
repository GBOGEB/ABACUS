"""Fail-closed, read-only federation breadth census across MIP control lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "abacus.mip.federation-manifest.v1"
DOMAINS = (
    "MISSION_CONTROL",
    "MIP",
    "DMAIC",
    "PCA_BT",
    "REX",
    "LDAB_LLDB",
    "CENSUS",
    "THREE_P",
)
REPOSITORIES = ("GBOGEB/ABACUS", "GBOGEB/CODEX")
SHA = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")


def require(condition: bool, reason: str) -> None:
    """Reject incomplete or contradictory observations."""
    if not condition:
        raise ValueError(reason)


def evidence_path(root: Path, name: str) -> Path:
    """Accept only readable local files under the evidence root."""
    require(isinstance(name, str) and bool(name), "missing evidence path")
    path = (root / name).resolve()
    require(
        path.is_relative_to(root) and path.is_file(),
        "evidence path escapes root or is missing",
    )
    return path


def evaluate(manifest: dict, artifact_root: Path) -> dict:
    """Describe federation breadth, without inventing operational proof."""
    require(isinstance(manifest, dict), "manifest must be object")
    require(manifest.get("schema") == SCHEMA, "invalid federation schema")
    repos = manifest.get("repositories")
    require(isinstance(repos, list) and repos, "missing repositories")
    seen_repo = set()
    seen_receipts = set()
    sources = {}
    for item in repos:
        require(isinstance(item, dict), "invalid repository record")
        repo = item.get("repository")
        sha = item.get("head_sha")
        require(repo in REPOSITORIES and repo not in seen_repo, "invalid repository")
        require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid head SHA")
        seen_repo.add(repo)
        evidence = item.get("evidence", [])
        require(isinstance(evidence, list), "invalid evidence list")
        source_slots = {}
        for record in evidence:
            require(isinstance(record, dict), "invalid evidence record")
            domain = record.get("domain")
            require(domain in DOMAINS, "invalid evidence domain")
            require(record.get("repository") == repo, "cross-repo evidence")
            require(record.get("head_sha") == sha, "mixed-head evidence")
            run = record.get("run_id")
            job = record.get("job_id")
            require(
                type(run) is int and run > 0 and type(job) is int and job > 0,
                "missing native run/job identity",
            )
            key = (repo, domain, run, job)
            require(key not in seen_receipts, "duplicate native receipt")
            seen_receipts.add(key)
            digest = record.get("artifact_sha256")
            require(
                isinstance(digest, str) and DIGEST.fullmatch(digest),
                "invalid artifact digest",
            )
            path = evidence_path(artifact_root.resolve(), record.get("path"))
            raw = path.read_bytes()
            require(
                bool(raw) and hashlib.sha256(raw).hexdigest() == digest,
                "artifact digest mismatch",
            )
            receipt = json.loads(raw)
            require(isinstance(receipt, dict), "invalid artifact object")
            require(
                receipt.get("repository") == repo
                and receipt.get("head_sha") == sha,
                "artifact provenance mismatch",
            )
            source_slots[domain] = source_slots.get(domain, 0) + 1
        sources[repo] = {"head_sha": sha, "receipt_counts": source_slots}
    cells = []
    for repo in REPOSITORIES:
        for domain in DOMAINS:
            source = sources.get(repo)
            count = (
                source["receipt_counts"][domain]
                if source and domain in source["receipt_counts"]
                else "UNKNOWN"
            )
            cells.append(
                {
                    "repository": repo,
                    "domain": domain,
                    "head_sha": source["head_sha"] if source else "UNKNOWN",
                    "locally_hash_verified_receipts": count,
                    "native_runner_authenticated": "UNKNOWN",
                    "accepted_rex": "UNKNOWN",
                    "root_closure_verified": "UNKNOWN",
                }
            )
    return {
        "schema": "abacus.mip.federation-census.v1",
        "evidence_class": "LOCAL_HASH_ONLY_NOT_RUNTIME_AUTHORITY",
        "repositories": sorted(seen_repo),
        "repository_breadth": len(seen_repo),
        "domain_breadth": len(DOMAINS),
        "total_domain_slots": len(REPOSITORIES) * len(DOMAINS),
        "filled_receipt_slots": sum(
            type(cell["locally_hash_verified_receipts"]) is int
            and cell["locally_hash_verified_receipts"] > 0
            for cell in cells
        ),
        "authenticated_fanout": "UNKNOWN",
        "federation_main_coverage_delta": "UNKNOWN",
        "merged_root_closures": "UNKNOWN",
        "merge_admission": "HOLD",
        "cells": cells,
    }


def markdown(data: dict) -> str:
    """Render all breadth slots, including unobserved/UNKNOWN cells."""
    lines = [
        "# Mission Control-wide federation census",
        "",
        "> LOCAL HASH PROVENANCE ONLY. Not an authenticated REX return or merge.",
        "",
        "| Repository | Domain | Local receipts | Runner | REX | Closure |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for cell in data["cells"]:
        count = cell["locally_hash_verified_receipts"]
        lines.append(
            f"| {cell['repository']} | {cell['domain']} | "
            f"{count} | "
            f"{cell['native_runner_authenticated']} | "
            f"{cell['accepted_rex']} | {cell['root_closure_verified']} |"
        )
    lines.extend(
        [
            "",
            "A local receipt count is not operational fan-out or native approval.",
            "Missing repositories remain UNKNOWN, not zero.",
            "PCA/BT maturity requires independent statistical samples.",
            "3P retained checks do not imply a federated runner launch.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """Produce deterministic plain-text and JSON census artifacts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    data = evaluate(json.loads(args.input.read_text()), args.artifact_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "mip_federation_census.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "mip_federation_census.md").write_text(
        markdown(data), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
