"""Fail-closed Safety CLI outcome census; exit status is not a vulnerability count."""

import argparse
import json
from pathlib import Path


def classify(exit_code: int, report: object) -> dict:
    findings = None
    if isinstance(report, dict):
        v = report.get("vulnerabilities")
        if isinstance(v, list):
            findings = len(v)
    return {
        "schema": "safety.exit.census.v1",
        "exit_code": exit_code,
        "finding_count": findings,
        "failure_class": (
            "SUCCESS"
            if exit_code == 0 and findings == 0
            else (
                "SCAN_OR_POLICY_FAILURE_UNCLASSIFIED"
                if exit_code != 0
                else "NONTERMINAL_REVIEW_REQUIRED"
            )
        ),
        "admission": "HOLD",
        "security_waiver": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--exit-code", required=True, type=int)
    p.add_argument("--report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    report = json.loads(a.report.read_text()) if a.report else None
    a.out.write_text(
        json.dumps(classify(a.exit_code, report), sort_keys=True, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
