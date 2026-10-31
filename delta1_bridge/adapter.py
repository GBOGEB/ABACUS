"""Uniform federation status / assimilate adapter for the DELTA_1 federation.

Every federation repo should be able to answer the same three questions the
same way, regardless of its internal layout:

  * Who am I?            -> repo identity + federation plane/role
  * Is my metrics feed valid? -> shared DMAIC metrics schema validation
  * Am I wired in?       -> federation manifest / spec presence

cryoplant-project already exposes ``src/federation.py:assimilate()`` and CODEX
exposes ``src/bridge_adapter.py``; ABACUS references the same convention via a
registration stub. This adapter generalises that single contract so the three
repos share one implementation instead of three divergent ones.

Pure read-only: it inspects files on disk, never writes governed SSOT and never
performs network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schema import load_and_validate_metrics

# Managed-step trace vocabulary shared with CODEX src/bridge_adapter.py.
GREEK_TRACE_SEQUENCE: tuple[str, ...] = (
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lambda",
    "mu",
)


@dataclass(frozen=True)
class RepoDescriptor:
    """Static description of a federation member repo."""

    repo: str  # e.g. "GBOGEB/CODEX"
    plane: str  # governance | runtime | auxiliary
    role: str  # short human description
    metrics_relpaths: tuple[str, ...]  # candidate metrics JSON locations
    manifest_relpaths: tuple[str, ...]  # candidate federation manifest/spec locations
    marker_relpaths: tuple[str, ...] = ()  # files that identify this repo on disk


# Known DELTA_1 members. Metrics/manifest locations reflect what each repo
# actually publishes today (see their READMEs and dmaic-commit-metrics.yml).
KNOWN_REPOS: tuple[RepoDescriptor, ...] = (
    RepoDescriptor(
        repo="GBOGEB/CODEX",
        plane="governance",
        role="Governance plane + KEB semantic-provenance runtime",
        metrics_relpaths=("docs/api/metrics.json",),
        manifest_relpaths=(
            ".mesh/MESH_DOCK.yaml",
            "federation/manifest.yaml",
            "src/bridge_adapter.py",
        ),
        marker_relpaths=("src/bridge_adapter.py", "KEB/governance/GLOSSARY.yml"),
    ),
    RepoDescriptor(
        repo="GBOGEB/ABACUS",
        plane="runtime",
        role="DOW analytical runtime (12-Cluster DMAIC)",
        metrics_relpaths=("docs/api/dmaic_metrics.json", "docs/api/metrics.json"),
        manifest_relpaths=(
            "federation/manifest.yaml",
            "runtime/federation/codex-abacus-federation.yaml",
        ),
        marker_relpaths=("DMAIC_V3", "12CLUSTER_ARCHITECTURE_BOOK.md"),
    ),
    RepoDescriptor(
        repo="GBOGEB/cryoplant-project",
        plane="auxiliary",
        role="QPS engineering SSOT (OCD/ADR authority)",
        metrics_relpaths=("docs/api/metrics.json", "docs/api/dmaic_metrics.json"),
        manifest_relpaths=(
            "federation/manifest.yaml",
            "runtime/federation/cryoplant-federation.yaml",
        ),
        marker_relpaths=("src/federation.py", "ocd-adr"),
    ),
)


def _first_existing(root: Path, relpaths: tuple[str, ...]) -> Path | None:
    for rel in relpaths:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def detect_repo(repo_root: str | Path) -> RepoDescriptor | None:
    """Best-effort identification of which federation repo lives at repo_root."""
    root = Path(repo_root).resolve()
    best: tuple[int, RepoDescriptor] | None = None
    for desc in KNOWN_REPOS:
        hits = sum(1 for rel in desc.marker_relpaths if (root / rel).exists())
        if hits and (best is None or hits > best[0]):
            best = (hits, desc)
    return best[1] if best else None


def federation_status(
    repo_root: str | Path = ".", descriptor: RepoDescriptor | None = None
) -> dict[str, Any]:
    """Return a uniform federation status dict for the repo at ``repo_root``.

    Keys: status (ok|degraded|error|unknown), repo, plane, role,
    metrics (schema validation result), manifest_found, manifest_path,
    details (list[str]).
    """
    root = Path(repo_root).resolve()
    desc = descriptor or detect_repo(root)
    details: list[str] = []

    if desc is None:
        return {
            "status": "unknown",
            "repo": None,
            "plane": None,
            "role": None,
            "metrics": None,
            "manifest_found": False,
            "manifest_path": None,
            "details": [f"could not identify a known DELTA_1 repo at {root}"],
        }

    # Metrics feed (shared schema).
    metrics_path = _first_existing(root, desc.metrics_relpaths)
    if metrics_path is not None:
        metrics = load_and_validate_metrics(metrics_path)
        if metrics["valid"]:
            details.append(f"metrics OK: {metrics_path.relative_to(root)}")
        else:
            details.append(
                f"metrics INVALID: {metrics_path.relative_to(root)} "
                f"({len(metrics['issues'])} issue(s))"
            )
    else:
        metrics = {
            "path": None,
            "found": False,
            "valid": False,
            "issues": ["no metrics JSON found"],
            "data": None,
        }
        details.append("metrics MISSING")

    # Federation manifest/spec presence.
    manifest_path = _first_existing(root, desc.manifest_relpaths)
    manifest_found = manifest_path is not None
    if manifest_found:
        details.append(f"manifest OK: {manifest_path.relative_to(root)}")
    else:
        details.append("manifest MISSING")

    # Aggregate status.
    if metrics["valid"] and manifest_found:
        status = "ok"
    elif metrics["found"] or manifest_found:
        status = "degraded"
    else:
        status = "error"

    return {
        "status": status,
        "repo": desc.repo,
        "plane": desc.plane,
        "role": desc.role,
        "metrics": metrics,
        "manifest_found": manifest_found,
        "manifest_path": (
            str(manifest_path.relative_to(root)) if manifest_found else None
        ),
        "details": details,
    }


def assimilate(
    context: dict[str, Any] | None = None, repo_root: str | Path = "."
) -> dict[str, Any]:
    """Compatibility entry point matching cryoplant-project's assimilate().

    Returns the same ``federation_status`` payload augmented with the caller
    context, so existing smoke tests expecting an ``assimilate()`` call can be
    pointed at this shared implementation.
    """
    result = federation_status(repo_root=repo_root)
    result["context"] = context or {}
    return result
