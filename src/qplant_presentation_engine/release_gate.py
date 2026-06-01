"""Release gate: verify CI evidence and produce release_readiness.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

REPORTS_DIRNAME = "reports"
RTM_DIRNAME = "rtm"

RTM_COVERAGE_THRESHOLD = 1.0


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _check_rtm_coverage(rtm_dir: Path) -> Tuple[bool, float, str]:
    """Return (passed, coverage_ratio, message)."""
    summary_path = rtm_dir / "rtm_summary.json"
    summary = _read_json(summary_path)
    if not summary:
        return False, 0.0, f"rtm_summary.json not found at {summary_path}"
    coverage_ratio = float(summary.get("coverage_ratio", 0.0))
    passed = coverage_ratio >= RTM_COVERAGE_THRESHOLD
    msg = (
        f"RTM coverage {coverage_ratio:.2%} >= {RTM_COVERAGE_THRESHOLD:.2%}"
        if passed
        else f"RTM coverage {coverage_ratio:.2%} < required {RTM_COVERAGE_THRESHOLD:.2%}"
    )
    return passed, coverage_ratio, msg


def _check_governance(reports_dir: Path) -> Tuple[bool, str]:
    """Return (passed, message)."""
    snapshot = _read_json(reports_dir / "governance_snapshot.json")
    if not snapshot:
        return False, "governance_snapshot.json not found"
    passed = bool(snapshot.get("governance_passed"))
    return passed, "Governance passed" if passed else "Governance not passed"


def _check_dmaic(reports_dir: Path) -> Tuple[bool, str]:
    """Return (passed, message)."""
    snapshot = _read_json(reports_dir / "dmaic_snapshot.json")
    if not snapshot:
        return False, "dmaic_snapshot.json not found"
    phase_status = snapshot.get("phase_status", {})
    phases = ("define", "measure", "analyze", "improve", "control")
    incomplete = [
        phase
        for phase in phases
        if not bool((phase_status.get(phase) or {}).get("complete"))
    ]
    if incomplete:
        return False, f"DMAIC phases incomplete: {', '.join(incomplete)}"
    return True, "DMAIC all phases complete"


def _check_runtime_evidence(reports_dir: Path) -> Tuple[bool, str]:
    """Return (passed, message)."""
    for candidate in ("runtime_status.json", "runtime_publish_status.json"):
        path = reports_dir / candidate
        if path.exists():
            data = _read_json(path)
            status = data.get("runtime_status", "")
            if status == "ok":
                return True, f"Runtime evidence present and status=ok ({candidate})"
            return False, f"Runtime evidence found ({candidate}) but status={status!r}"
    return False, "No runtime evidence found (runtime_status.json or runtime_publish_status.json)"


def evaluate_release_gate(
    reports_dir: Optional[Path] = None,
    rtm_dir: Optional[Path] = None,
    release_readiness_path: Optional[Path] = None,
    ci_status_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Evaluate all release gate checks and write ci_status.json and release_readiness.json."""
    resolved_reports = reports_dir or (Path.cwd() / REPORTS_DIRNAME)
    resolved_rtm = rtm_dir or (Path.cwd() / RTM_DIRNAME)

    rtm_passed, coverage_ratio, rtm_msg = _check_rtm_coverage(resolved_rtm)
    governance_passed, governance_msg = _check_governance(resolved_reports)
    dmaic_passed, dmaic_msg = _check_dmaic(resolved_reports)
    runtime_passed, runtime_msg = _check_runtime_evidence(resolved_reports)

    all_passed = rtm_passed and governance_passed and dmaic_passed and runtime_passed

    checks: Dict[str, Any] = {
        "rtm_coverage": {
            "passed": rtm_passed,
            "coverage_ratio": coverage_ratio,
            "message": rtm_msg,
        },
        "governance": {
            "passed": governance_passed,
            "message": governance_msg,
        },
        "dmaic": {
            "passed": dmaic_passed,
            "message": dmaic_msg,
        },
        "runtime_evidence": {
            "passed": runtime_passed,
            "message": runtime_msg,
        },
    }

    release_readiness: Dict[str, Any] = {
        "artifact": "release_readiness",
        "generated_at": _utc_timestamp(),
        "release_ready": all_passed,
        "checks": checks,
    }

    ci_status: Dict[str, Any] = {
        "artifact": "ci_status",
        "generated_at": _utc_timestamp(),
        "ci_passed": all_passed,
        "checks": {k: bool(v["passed"]) for k, v in checks.items()},
    }

    resolved_release_path = release_readiness_path or (resolved_reports / "release_readiness.json")
    resolved_ci_path = ci_status_path or (resolved_reports / "ci_status.json")
    _write_json(resolved_release_path, release_readiness)
    _write_json(resolved_ci_path, ci_status)

    return release_readiness


def main() -> int:
    """CLI entry point: run release gate and exit non-zero if not ready."""
    result = evaluate_release_gate()
    print(json.dumps(result, indent=2))
    return 0 if result.get("release_ready") else 1


if __name__ == "__main__":
    sys.exit(main())
