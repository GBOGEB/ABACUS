"""Fail-closed static Python/Matplotlib constraint guard for MIP recovery.

This is a quick preflight on requirement syntax and release floors, not a
substitute for per-interpreter pip resolution, security scanning, or admission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement

SCHEMA = "abacus.mip.python-dependency-guard.v1"
PYTHON_LANES = ("3.10", "3.11", "3.12")
MATPLOTLIB_LINE = re.compile(r"^\s*matplotlib(?=\s|[<>=!~;@\[])", re.I)


def _matplotlib_lines(source: str) -> tuple[list[Requirement], list[str]]:
    requirements = []
    errors = []
    for line_number, line in enumerate(source.splitlines(), 1):
        if not MATPLOTLIB_LINE.match(line):
            continue
        try:
            requirement = Requirement(line.split(" #", 1)[0].strip())
        except InvalidRequirement:
            errors.append(f"line {line_number}: invalid matplotlib requirement")
            continue
        if requirement.name.lower() != "matplotlib":
            errors.append(f"line {line_number}: unexpected package")
        elif requirement.marker is None or requirement.url is not None:
            errors.append(f"line {line_number}: missing marker or direct URL")
        else:
            requirements.append(requirement)
    return requirements, errors


def audit(source: str) -> dict:
    """Compare all supported Python lanes without assigning root-closure credit."""
    requirements, syntax_errors = _matplotlib_lines(source)
    observations = []
    for lane in PYTHON_LANES:
        environment = default_environment()
        environment["python_version"] = lane
        environment["python_full_version"] = lane + ".0"
        active = [
            requirement
            for requirement in requirements
            if requirement.marker.evaluate(environment=environment)
        ]
        problems = list(syntax_errors)
        if len(active) != 1:
            problems.append(
                f"expected one active matplotlib requirement, got {len(active)}"
            )
        else:
            spec = active[0].specifier
            if lane == "3.10":
                if not (
                    spec.contains("3.10.9")
                    and not spec.contains("3.10.8")
                    and not spec.contains("3.11.0")
                ):
                    problems.append("Python 3.10 requires guarded 3.10.9..<3.11 range")
            elif not (spec.contains("3.11.2") and not spec.contains("3.10.9")):
                problems.append("Python 3.11+ requires guarded >=3.11.2 floor")
        observations.append(
            {
                "python_version": lane,
                "status": "FAIL" if problems else "PASS",
                "active_requirement": str(active[0]) if len(active) == 1 else "UNKNOWN",
                "findings": problems,
            }
        )

    passed = sum(row["status"] == "PASS" for row in observations)
    failed = len(PYTHON_LANES) - passed
    return {
        "schema": SCHEMA,
        "evidence_class": "STATIC_REQUIREMENT_POLICY_ONLY",
        "matplotlib_policy": "py310: 3.10.9..<3.11; py311_plus: >=3.11.2",
        "lanes": len(PYTHON_LANES),
        "static_pass": passed,
        "static_fail": failed,
        "pass_pct": round(100 * passed / len(PYTHON_LANES), 6),
        "observations": observations,
        "native_pip_resolution": "UNKNOWN",
        "security_disposition": "UNKNOWN",
        "distinct_bd_roots_open": "UNKNOWN",
        "distinct_bd_roots_closed": "UNKNOWN",
        "coverage_gain": "UNKNOWN",
        "authenticated_worker_dispatch": "UNKNOWN",
        "accepted_rex": "UNKNOWN",
        "merge_admission": "HOLD",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", default="DMAIC_V3/requirements.txt")
    parser.add_argument("--out", help="Optional JSON static-policy receipt")
    args = parser.parse_args()
    raw = Path(args.requirements).read_bytes()
    result = audit(raw.decode("utf-8"))
    result["requirements_sha256"] = hashlib.sha256(raw).hexdigest()
    result["producer_python"] = f"{sys.version_info.major}.{sys.version_info.minor}"
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 1 if result["static_fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
