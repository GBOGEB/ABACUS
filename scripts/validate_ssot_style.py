#!/usr/bin/env python3
"""Validate the SSOT style contract and score artifact QA readiness."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "ssot" / "ssot_style.json"
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
REQUIRED_ARTIFACTS = {"excel", "pptx", "pdf", "html", "markdown", "graphs"}
REQUIRED_HTML_GATES = {
    "playwright_navigation",
    "no_console_errors",
    "internal_links_resolve",
}


def load_manifest(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _require(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def validate_manifest(manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    _require(bool(manifest.get("version")), "version is required", errors)
    _require(bool(manifest.get("owner")), "owner is required", errors)
    _require(bool(manifest.get("purpose")), "purpose is required", errors)

    scope = manifest.get("scope", {})
    _require(scope.get("primary_repo") == "GBOGEB/ABACUS", "primary_repo must be GBOGEB/ABACUS", errors)
    bridge_repos = set(scope.get("bridge_repos", []))
    _require("GBOGEB/CODEX" in bridge_repos, "CODEX bridge repo is required", errors)
    _require("controlled-evidence-repo" in bridge_repos, "controlled evidence bridge repo is required", errors)

    palette = manifest.get("palette", {}).get("tokens", {})
    _require(bool(palette), "palette tokens are required", errors)
    for name, value in palette.items():
        _require(isinstance(value, str) and bool(HEX_RE.match(value)), f"palette token {name} must be #RRGGBB", errors)

    artifacts = manifest.get("artifact_contract", {})
    missing_artifacts = REQUIRED_ARTIFACTS - set(artifacts)
    _require(not missing_artifacts, f"missing artifact contract(s): {sorted(missing_artifacts)}", errors)
    html_gates = set(artifacts.get("html", []))
    missing_html_gates = REQUIRED_HTML_GATES - html_gates
    _require(not missing_html_gates, f"missing required HTML QA gate(s): {sorted(missing_html_gates)}", errors)

    probes = manifest.get("awake_probes", [])
    _require(bool(probes), "awake_probes must not be empty", errors)
    for probe in probes:
        for field in ("id", "path", "kind", "weight"):
            _require(field in probe, f"awake probe missing {field}: {probe}", errors)
        if "weight" in probe:
            _require(isinstance(probe["weight"], int) and probe["weight"] > 0, f"probe weight must be positive: {probe}", errors)

    return errors


def score_awake_probes(manifest: Dict[str, Any], root: Path = ROOT) -> Dict[str, Any]:
    probes = manifest.get("awake_probes", [])
    rows = []
    total_weight = 0
    awake_weight = 0
    by_kind: Dict[str, Dict[str, int]] = {}

    for probe in probes:
        weight = int(probe.get("weight", 0))
        total_weight += weight
        path = root / probe.get("path", "")
        awake = path.exists()
        if awake:
            awake_weight += weight
        kind = probe.get("kind", "unknown")
        by_kind.setdefault(kind, {"awake": 0, "total": 0})
        by_kind[kind]["total"] += 1
        by_kind[kind]["awake"] += int(awake)
        rows.append(
            {
                "id": probe.get("id"),
                "kind": kind,
                "path": probe.get("path"),
                "weight": weight,
                "awake": awake,
            }
        )

    score = round((awake_weight / total_weight) * 100, 1) if total_weight else 0.0
    return {
        "awake_score": score,
        "awake_weight": awake_weight,
        "total_weight": total_weight,
        "by_kind": by_kind,
        "probes": rows,
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _probe_depth(kind: str, path: Path) -> Tuple[int, int, List[str]]:
    if not path.exists():
        return 0, 3, ["missing"]

    text = _read_text(path)
    signals: List[str] = ["exists"]
    depth = 1

    if kind == "graph":
        for label, patterns in {
            "topology": ("nodes:", "lineage:"),
            "dependencies": ("depends_on:", "repositories:"),
            "objectives": ("objectives:",),
        }.items():
            if any(pattern in text for pattern in patterns):
                depth += 1
                signals.append(label)
    elif kind == "playwright":
        for label, patterns in {
            "browser": ("sync_playwright", "chromium"),
            "console_errors": ("console", "pageerror"),
            "layout": ("overflow", "scrollWidth"),
        }.items():
            if any(pattern in text for pattern in patterns):
                depth += 1
                signals.append(label)
    elif kind == "dow" and path.suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {}
        if payload.get("status") == "ok":
            depth += 1
            signals.append("status_ok")
        if payload.get("components", {}).get("dow_agents", 0) > 0:
            depth += 1
            signals.append("agents")
        if payload.get("pipeline", {}).get("orchestrator"):
            depth += 1
            signals.append("orchestrator")
    elif kind in {"dow", "keb"}:
        for label, patterns in {
            "tests": ("def test_", "unittest", "pytest"),
            "bidirectional": ("bidirectional", "cross_sut", "schedule_task"),
            "runtime": ("async", "start(", "stop("),
        }.items():
            if any(pattern in text for pattern in patterns):
                depth += 1
                signals.append(label)
    elif kind == "html":
        for label, patterns in {
            "document": ("<html", "<!doctype"),
            "pca_bt": ("PCA", "BT", "Bradley"),
            "scripted": ("<script", "data-tab"),
        }.items():
            if any(pattern.lower() in text.lower() for pattern in patterns):
                depth += 1
                signals.append(label)
    elif kind == "style":
        for label, patterns in {
            "palette": ("colours:", "palette", "hex:"),
            "typography": ("Aptos", "font"),
            "validation": ("validation:", "render_qa"),
        }.items():
            if any(pattern in text for pattern in patterns):
                depth += 1
                signals.append(label)

    return min(depth, 4), 4, signals


def score_penetration(manifest: Dict[str, Any], root: Path = ROOT) -> Dict[str, Any]:
    rows = []
    depth_total = 0
    max_total = 0
    by_kind: Dict[str, Dict[str, int]] = {}
    for probe in manifest.get("awake_probes", []):
        kind = probe.get("kind", "unknown")
        path = root / probe.get("path", "")
        depth, max_depth, signals = _probe_depth(kind, path)
        depth_total += depth
        max_total += max_depth
        by_kind.setdefault(kind, {"depth": 0, "max_depth": 0})
        by_kind[kind]["depth"] += depth
        by_kind[kind]["max_depth"] += max_depth
        rows.append(
            {
                "id": probe.get("id"),
                "kind": kind,
                "depth": depth,
                "max_depth": max_depth,
                "signals": signals,
            }
        )

    score = round((depth_total / max_total) * 100, 1) if max_total else 0.0
    return {
        "penetration_score": score,
        "depth": depth_total,
        "max_depth": max_total,
        "by_kind": by_kind,
        "probes": rows,
    }


def score_artifact_contract(manifest: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = manifest.get("artifact_contract", {})
    gate_counts = {name: len(gates) for name, gates in artifacts.items()}
    total_gates = sum(gate_counts.values())
    required_present = len(REQUIRED_ARTIFACTS & set(artifacts))
    score = round((required_present / len(REQUIRED_ARTIFACTS)) * 100, 1)
    return {
        "contract_score": score,
        "artifact_count": len(artifacts),
        "total_gate_count": total_gates,
        "gate_counts": gate_counts,
    }


def build_report(manifest_path: Path = DEFAULT_MANIFEST, root: Path = ROOT) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)
    errors = validate_manifest(manifest)
    awake = score_awake_probes(manifest, root=root)
    penetration = score_penetration(manifest, root=root)
    contract = score_artifact_contract(manifest)
    return {
        "manifest": str(manifest_path.relative_to(root) if manifest_path.is_relative_to(root) else manifest_path),
        "valid": not errors,
        "errors": errors,
        "artifact_contract": contract,
        "awake": awake,
        "penetration": penetration,
        "pca_focus_axes": manifest.get("scoring", {}).get("pca_focus_axes", []),
        "bt_priority_rule": manifest.get("scoring", {}).get("bt_priority_rule", ""),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = build_report(args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
