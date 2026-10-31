"""Redacted A10 block census; never expose confidential matching terms."""

import argparse
import json
import re
from pathlib import Path

BLOCK = re.compile(r"^\s*BLOCK\s+(.+?)\s+\(([^()]*)\)\s*$")


def summarize(log: str) -> dict:
    findings = []
    for line in log.splitlines():
        match = BLOCK.search(re.sub(r"^.*?Z\s+", "", line))
        if match:
            path, reason = match.groups()
            if reason not in {
                "restricted term in content",
                "tender folder",
                "tender-like name",
                "binary document that cannot be inspected (fail closed)",
            }:
                reason = "OTHER_REVIEW_REQUIRED"
            findings.append({"path": path, "reason_code": reason, "match_text": None})
    return {
        "schema": "a10.redacted.origin.v1",
        "blocked_files": findings,
        "verified_clearance": False,
        "security_waiver": False,
        "admission": "HOLD",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(
        json.dumps(summarize(args.log.read_text()), sort_keys=True, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
