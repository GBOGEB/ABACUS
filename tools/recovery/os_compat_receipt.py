"""Validate native OS-compatibility receipts without inventing an executed job."""

import argparse
import json
from pathlib import Path

REQUIRED = (
    "repository",
    "commit_sha",
    "run_id",
    "job_id",
    "os_release",
    "runner",
    "image_digest",
    "conclusion",
)


def validate(row: object) -> dict:
    if not isinstance(row, dict):
        raise ValueError("receipt must be JSON object")
    missing = [k for k in REQUIRED if not row.get(k)]
    result = row.get("conclusion")
    if result not in ("success", "failure", "cancelled", "skipped", "unknown"):
        missing.append("valid_conclusion")
    if result == "success" and not str(row.get("image_digest", "")).startswith(
        "sha256:"
    ):
        missing.append("sha256_image_digest")
    return {
        "schema": "os.compat.receipt.validation.v1",
        "complete": not missing,
        "missing": sorted(set(missing)),
        "native_pass": not missing and result == "success",
        "admission": "HOLD",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("receipt", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.write_text(
        json.dumps(
            validate(json.loads(a.receipt.read_text())), sort_keys=True, indent=2
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
