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
REQUIRED_FEDERATION_REPOS = {
    "GBOGEB/ABACUS",
    "GBOGEB/CODEX",
    "GBOGEB/cryoplant-project",
}
REQUIRED_FEDERATION_LANES = {
    "excel",
    "pptx",
    "pdf",
    "html",
    "graphs",
    "ci",
    "dow",
    "keb",
}
REQUIRED_FEDERATION_METHODS = {
    "DMAIC",
    "PCA_REVERSED_P5_TO_P1",
    "BT_PRIORITY",
}
REQUIRED_BLOCKING_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure", "stale"}
REQUIRED_MANUAL_REVIEW_CONCLUSIONS = {"cancelled"}
REQUIRED_PENDING_STATUSES = {"queued", "in_progress", "requested", "waiting", "pending"}
REQUIRED_REPAIR_PRS = {"GBOGEB/ABACUS": {754, 756}, "GBOGEB/CODEX": {298, 300}}
REQUIRED_ALL_CLEAR_REQUIREMENTS = {
    "no_blocking_conclusions",
    "no_unwaived_cancelled_checks",
    "no_pending_required_checks",
    "no_unresolved_material_reviews",
    "repaired_sha_retested",
    "downstream_return_receipt_accepted",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_BASELINE_SHA256 = {
    "GBOGEB/ABACUS": "8735c00c95c880578148639238ea4dcdcf25779d22e382e0c5dde4d0b39498f5",
    "GBOGEB/CODEX": "b6f2c4451ba9de761c4c97a89978aeb436e51f63d7ce8ab8571697797ae8bbf4",
    "GBOGEB/cryoplant-project": "1209db158f25f393a7c33963bb149ada5485b29238afd8fd4345af678d04b80f",
}


def load_manifest(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _require(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def _string_set(value: Any, field_name: str, errors: List[str]) -> set[str]:
    """Validate a manifest contract field that must be a list of strings."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field_name} must be a list of strings")
        return set()
    return set(value)


def _format_missing(values: set[Any]) -> str:
    return ", ".join(str(value) for value in sorted(values))


def _mapping(value: Any, field_name: str, errors: List[str]) -> Dict[str, Any]:
    """Return a mapping or record a deterministic validation error."""
    if not isinstance(value, dict):
        errors.append(f"{field_name} must be an object")
        return {}
    return value


def _repair_pr_set(value: Any, field_name: str, errors: List[str]) -> set[int]:
    if isinstance(value, int):
        return {value}
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        errors.append(f"{field_name} must be an integer or list of integers")
        return set()
    return set(value)


def validate_manifest(manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    _require(bool(manifest.get("version")), "version is required", errors)
    _require(bool(manifest.get("owner")), "owner is required", errors)
    _require(bool(manifest.get("purpose")), "purpose is required", errors)

    scope = manifest.get("scope", {})
    _require(scope.get("primary_repo") == "GBOGEB/ABACUS", "primary_repo must be GBOGEB/ABACUS", errors)
    bridge_repos = _string_set(scope.get("bridge_repos", []), "scope.bridge_repos", errors)
    _require("GBOGEB/CODEX" in bridge_repos, "CODEX bridge repo is required", errors)
    _require("controlled-evidence-repo" in bridge_repos, "controlled evidence bridge repo is required", errors)

    palette = manifest.get("palette", {}).get("tokens", {})
    _require(bool(palette), "palette tokens are required", errors)
    for name, value in palette.items():
        _require(isinstance(value, str) and bool(HEX_RE.match(value)), f"palette token {name} must be #RRGGBB", errors)

    artifacts = manifest.get("artifact_contract", {})
    missing_artifacts = REQUIRED_ARTIFACTS - set(artifacts)
    _require(not missing_artifacts, f"missing artifact contract(s): {_format_missing(missing_artifacts)}", errors)
    html_gates = _string_set(artifacts.get("html", []), "artifact_contract.html", errors)
    missing_html_gates = REQUIRED_HTML_GATES - html_gates
    _require(not missing_html_gates, f"missing required HTML QA gate(s): {_format_missing(missing_html_gates)}", errors)

    wave = _mapping(manifest.get("federation_wave", {}), "federation_wave", errors)
    _require(wave.get("id") == "SSOT-STYLE-W04", "federation_wave id must be SSOT-STYLE-W04", errors)
    repos = _string_set(wave.get("repos", []), "federation_wave.repos", errors)
    missing_repos = REQUIRED_FEDERATION_REPOS - repos
    _require(not missing_repos, f"missing federation repo(s): {_format_missing(missing_repos)}", errors)
    lanes = _string_set(wave.get("artifact_lanes", []), "federation_wave.artifact_lanes", errors)
    missing_lanes = REQUIRED_FEDERATION_LANES - lanes
    _require(not missing_lanes, f"missing federation artifact lane(s): {_format_missing(missing_lanes)}", errors)
    methods = _string_set(wave.get("methods", []), "federation_wave.methods", errors)
    missing_methods = REQUIRED_FEDERATION_METHODS - methods
    _require(not missing_methods, f"missing federation method(s): {_format_missing(missing_methods)}", errors)
    _require(
        wave.get("no_credit_without_child_disposition") is True,
        "federation wave must block credit without child disposition",
        errors,
    )
    _validate_handoff_check_policy(wave, errors)
    _validate_lineage_binding(manifest, errors)

    probes = manifest.get("awake_probes", [])
    _require(bool(probes), "awake_probes must not be empty", errors)
    for probe in probes:
        for field in ("id", "path", "kind", "weight"):
            _require(field in probe, f"awake probe missing {field}: {probe}", errors)
        if "weight" in probe:
            _require(isinstance(probe["weight"], int) and probe["weight"] > 0, f"probe weight must be positive: {probe}", errors)

    return errors


def _validate_handoff_check_policy(wave: Dict[str, Any], errors: List[str]) -> None:
    policy = _mapping(
        wave.get("handoff_check_policy", {}),
        "federation_wave.handoff_check_policy",
        errors,
    )
    repair_links = _mapping(
        policy.get("linked_repair_prs", {}),
        "federation_wave.handoff_check_policy.linked_repair_prs",
        errors,
    )
    for repo, required in REQUIRED_REPAIR_PRS.items():
        observed = _repair_pr_set(
            repair_links.get(repo, []),
            f"federation_wave.handoff_check_policy.linked_repair_prs.{repo}",
            errors,
        )
        missing = required - observed
        _require(
            not missing,
            f"linked repair PR(s) missing for {repo}: {_format_missing(missing)}",
            errors,
        )

    blocking = _string_set(
        policy.get("blocking_conclusions", []),
        "federation_wave.handoff_check_policy.blocking_conclusions",
        errors,
    )
    manual = _string_set(
        policy.get("manual_review_conclusions", []),
        "federation_wave.handoff_check_policy.manual_review_conclusions",
        errors,
    )
    pending = _string_set(
        policy.get("pending_statuses", []),
        "federation_wave.handoff_check_policy.pending_statuses",
        errors,
    )
    requirements = _string_set(
        policy.get("all_clear_requirements", []),
        "federation_wave.handoff_check_policy.all_clear_requirements",
        errors,
    )
    _require(
        REQUIRED_BLOCKING_CONCLUSIONS <= blocking,
        f"missing blocking conclusion(s): {_format_missing(REQUIRED_BLOCKING_CONCLUSIONS - blocking)}",
        errors,
    )
    _require(
        REQUIRED_MANUAL_REVIEW_CONCLUSIONS <= manual,
        f"missing manual-review conclusion(s): {_format_missing(REQUIRED_MANUAL_REVIEW_CONCLUSIONS - manual)}",
        errors,
    )
    _require(
        REQUIRED_PENDING_STATUSES <= pending,
        f"missing pending status(es): {_format_missing(REQUIRED_PENDING_STATUSES - pending)}",
        errors,
    )
    _require(
        REQUIRED_ALL_CLEAR_REQUIREMENTS <= requirements,
        f"missing all-clear requirement(s): {_format_missing(REQUIRED_ALL_CLEAR_REQUIREMENTS - requirements)}",
        errors,
    )
    feedback = _mapping(
        policy.get("repository_feedback", {}),
        "federation_wave.handoff_check_policy.repository_feedback",
        errors,
    )
    for field in ("from_codex", "to_codex"):
        _require(
            isinstance(feedback.get(field), str) and bool(feedback[field].strip()),
            f"repository_feedback.{field} must be a non-empty string",
            errors,
        )


def _validate_lineage_binding(manifest: Dict[str, Any], errors: List[str]) -> None:
    lineage = _mapping(manifest.get("lineage_binding", {}), "lineage_binding", errors)
    _require(lineage.get("contract_version") == "0.2.0", "lineage contract_version must be 0.2.0", errors)
    _require(lineage.get("status") == "pending_retest", "lineage status must be pending_retest", errors)
    inputs = _mapping(lineage.get("baseline_inputs", {}), "lineage_binding.baseline_inputs", errors)
    for repo in sorted(REQUIRED_FEDERATION_REPOS):
        binding = _mapping(inputs.get(repo, {}), f"lineage_binding.baseline_inputs.{repo}", errors)
        _require(bool(SHA_RE.fullmatch(str(binding.get("commit_sha", "")))), f"invalid commit SHA for {repo}", errors)
        _require(bool(SHA256_RE.fullmatch(str(binding.get("manifest_sha256", "")))), f"invalid manifest SHA256 for {repo}", errors)
        _require(binding.get("manifest_sha256") == REQUIRED_BASELINE_SHA256[repo], f"baseline manifest SHA256 mismatch for {repo}", errors)
        _require(bool(binding.get("manifest_path")), f"manifest path missing for {repo}", errors)


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
            "bidirectional": ("bidirectional", "cross_sut", "schedule_task", "DOW_TO_KEB", "KEB_TO_DOW"),
            "runtime": ("async", "start(", "stop(", "get_metrics"),
            "queue_feedback": ("queue_size", "tasks_executed", "feedback_loop"),
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
        "federation_wave": manifest.get("federation_wave", {}),
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
