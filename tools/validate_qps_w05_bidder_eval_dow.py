#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import yaml

REQUIRED = {
    "run_id",
    "artifact_id",
    "parent_repository",
    "parent_commit_sha",
    "correlation_id",
    "source_child_merge_sha",
    "input_hash",
    "snapshot_hash",
    "output_hash",
    "requested_operations",
    "executed_operations",
    "operation_status",
    "typed_findings",
    "child_disposition_placeholder",
    "authority_boundary",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    args = parser.parse_args()
    path = Path(args.receipt)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("receipt is not a mapping")
    missing = sorted(REQUIRED - set(data))
    if missing:
        raise SystemExit(f"missing required fields: {missing}")
    if data["correlation_id"] != "QPS-FED-W05-BIDDER-EVAL":
        raise SystemExit("wrong correlation id")
    if data["parent_repository"] != "GBOGEB/ABACUS":
        raise SystemExit("wrong parent repository")
    if data["requested_operations"] != data["executed_operations"]:
        raise SystemExit("requested/executed operation mismatch")
    if data["child_disposition_placeholder"] != "UNSET":
        raise SystemExit("parent must not self-disposition")
    if not data["typed_findings"]:
        raise SystemExit("no typed findings returned")
    for finding in data["typed_findings"]:
        if finding.get("qps_authority") is not False:
            raise SystemExit("parent finding incorrectly claims QPS authority")
        if finding.get("recommended_child_action") != "review_and_disposition_ACCEPT_REJECT_DEFER":
            raise SystemExit("missing governed child disposition contract")
    print("W05 DOW RECEIPT VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
