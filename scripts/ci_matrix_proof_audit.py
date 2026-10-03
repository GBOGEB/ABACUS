#!/usr/bin/env python3
"""Validate per-version Python proof manifests and classify intentional skips."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED = {
    "3.10": {
        "canonical_coverage": "CLASSIFIED_ROLE_SKIP",
        "functional_compatibility": "EXECUTED_PASS",
        "phase0": "CLASSIFIED_ROLE_SKIP",
        "qps_w08": "CLASSIFIED_ROLE_SKIP",
        "recursive_build": "EXECUTED_PASS",
    },
    "3.11": {
        "canonical_coverage": "CLASSIFIED_ROLE_SKIP",
        "functional_compatibility": "EXECUTED_PASS",
        "phase0": "CLASSIFIED_ROLE_SKIP",
        "qps_w08": "CLASSIFIED_ROLE_SKIP",
        "recursive_build": "EXECUTED_PASS",
    },
    "3.12": {
        "canonical_coverage": "EXECUTED_PASS",
        "functional_compatibility": "CLASSIFIED_ROLE_SKIP",
        "phase0": "EXECUTED_PASS",
        "qps_w08": "EXECUTED_PASS",
        "recursive_build": "EXECUTED_PASS",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def expected_versions(mode: str, secondary: str) -> list[str]:
    if mode == "full":
        return ["3.10", "3.11", "3.12"]
    if mode == "sampled":
        return sorted({"3.12", secondary})
    if mode == "sentinel":
        return ["3.12"]
    raise ValueError(f"unknown mode: {mode}")


def audit(directory: Path, mode: str, secondary: str) -> dict[str, Any]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for version in expected_versions(mode, secondary):
        path = directory / f"python-{version}-proof.json"
        if not path.exists():
            errors.append(f"{version}:MISSING_SUMMARY")
            continue
        payload = load_json(path)
        checks = payload.get("checks", {})
        for name, expected in EXPECTED[version].items():
            actual = checks.get(name)
            if actual != expected:
                errors.append(f"{version}:{name}:{actual or 'MISSING'}")
        artifact = checks.get("artifact_upload")
        if artifact not in {"EXECUTED_PASS", "OPTIONAL_NO_PAYLOAD"}:
            errors.append(f"{version}:artifact_upload:{artifact or 'MISSING'}")
        rows.append(
            {
                "python": version,
                "proof_role": payload.get("proof_role"),
                "checks": checks,
            }
        )
    return {
        "schema": "abacus-python-proof-audit/1.0.0",
        "mode": mode,
        "secondary": secondary,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "versions": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--secondary", default="3.10")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = audit(args.dir, args.mode, args.secondary)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
