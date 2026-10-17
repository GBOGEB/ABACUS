"""Fail-closed W+1 matched-growth adapter; descriptive only, not a CI admission gate."""

from __future__ import annotations
import argparse
import json
from pathlib import Path


def validate(ledger: dict, pulse: dict) -> dict:
    if ledger.get("schema") != "code-purple.matched-growth-ledger.v1":
        raise ValueError("schema mismatch")
    if (
        ledger.get("authority_transfer") is not False
        or ledger.get("merge_authorized") is not False
        or ledger.get("admission") != "HOLD"
    ):
        raise ValueError("authority promotion forbidden")
    if (
        pulse.get("authority_transfer") is not False
        or pulse.get("merge_authorized") is not False
    ):
        raise ValueError("source authority invalid")
    a, b = ledger["cohorts"]
    keys = (
        "source_sha",
        "run_total",
        "run_pass",
        "run_fail",
        "run_cancelled",
        "first_red_manifestations",
    )
    if (
        a["pulse"] != "N"
        or b["pulse"] != "N+1"
        or any(a[k] != b[k] for k in keys)
        or a["changed_lines"] != b["changed_lines"]
        or a["governance"] != b["governance"]
    ):
        raise ValueError("not a matched frozen cohort")
    for row in (a, b):
        if row["run_pass"] + row["run_fail"] + row["run_cancelled"] != row["run_total"]:
            raise ValueError("run denominator mismatch")
        cc = row["changed_lines"]
        if not (
            isinstance(cc["covered"], int)
            and isinstance(cc["eligible"], int)
            and 0 <= cc["covered"] <= cc["eligible"]
            and cc["eligible"] > 0
        ):
            raise ValueError("coverage denominator mismatch")
        if not (0 <= row["governance"]["classified"] <= row["governance"]["total"]):
            raise ValueError("governance denominator mismatch")
    m = pulse["metrics"]
    if (
        m["head_sha"] != a["source_sha"]
        or m["merge_checkout_sha"] != a["changed_lines"]["execution_sha"]
    ):
        raise ValueError("checkout/source sha mismatch")
    for field, source_field in (
        ("run_total", "workflow_total"),
        ("run_pass", "workflows"),
    ):
        if field == "run_pass":
            if a[field] != m[source_field]["PASS"]:
                raise ValueError("pass tally mismatch")
        elif a[field] != m[source_field]:
            raise ValueError("workflow tally mismatch")
    if (
        a["changed_lines"]["covered"] != m["coverage_numerator"]
        or a["changed_lines"]["eligible"] != m["coverage_denominator"]
    ):
        raise ValueError("source B9 count mismatch")
    if ledger["separate_local_extensions"]["new_regression_checks"] != 13:
        raise ValueError("unexpected new regression denominator")
    if any(
        ledger["matched_native_changes"][k] != 0
        for k in (
            "workflows_denominator",
            "workflows_passed",
            "coverage_eligible",
            "coverage_covered",
            "coverage_pp",
        )
    ):
        raise ValueError("false matched-native growth claim")
    return {
        "status": "PASS_CONSISTENCY_ONLY",
        "source_sha": a["source_sha"],
        "native_numerator_delta": 0,
        "native_denominator_delta": 0,
        "authority_transfer": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--growth", type=Path, default=Path("docs/code-purple-w1/growth-ledger.json")
    )
    p.add_argument(
        "--pulse", type=Path, default=Path("docs/code-purple-w1/pulse_telemetry.json")
    )
    x = p.parse_args()
    print(
        json.dumps(
            validate(json.loads(x.growth.read_text()), json.loads(x.pulse.read_text())),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
