"""N+1 read-only B-series adapter; consumes, never replaces, the canonical engine."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

import b_series_temporal_metrics as core

OUT_SCHEMA = "abacus.bseries.nplus1-matched-scanner-projection.v1"


def _datetime(value):
    return core._timestamp(value)


def extend(doc):
    rows = core.validate(doc)
    if doc.get("extension") != "N_PLUS_1_ADDITIVE_NATIVE_SOURCE_MATCHED_B1":
        raise core.EvidenceError("wrong N+1 evidence extension")
    if doc.get("versioned_from") != "docs/ci/B_SERIES_NATIVE_PULSES_20261017.json":
        raise core.EvidenceError("frozen N-2 to N source not referenced")
    if len(rows) != 4 or [x["pulse"] for x in rows] != [
        "N-2", "N-1", "N", "N+1"
    ]:
        raise core.EvidenceError("unexpected four-pulse order")
    identities, clocks = set(), []
    for row in rows:
        scanner = row.get("b1_scanner_blob_sha")
        workflow = row.get("b0_workflow_blob_sha")
        ceiling = row.get("b1_max_unguarded")
        if (
            not isinstance(scanner, str)
            or not core.SHA.fullmatch(scanner)
            or not isinstance(workflow, str)
            or not core.SHA.fullmatch(workflow)
            or type(ceiling) is not int
            or ceiling <= 0
        ):
            raise core.EvidenceError("missing B1 source/configuration binding")
        fingerprint = f"{scanner}:{workflow}:{ceiling}"
        if row.get("b1_source_config_identity") != fingerprint:
            raise core.EvidenceError("B1 fingerprint does not match source blobs")
        identities.add(fingerprint)
        t = _datetime(row.get("b1_observation_at"))
        if t > _datetime(row["observation_at"]):
            raise core.EvidenceError("B1 sample timestamp after B0 completion")
        clocks.append(t)
    if len(identities) != 1:
        raise core.EvidenceError("B1 scanner/workflow configuration drift")
    if clocks != sorted(clocks) or len(set(clocks)) != 4:
        raise core.EvidenceError("B1 sample clocks not strictly increasing")
    values = [row["b1_unguarded"] for row in rows]
    deltas = [
        (clocks[i] - clocks[i - 1]).total_seconds() / 3600.0
        for i in range(1, len(clocks))
    ]
    if any(not math.isfinite(h) or h <= 0 for h in deltas):
        raise core.EvidenceError("nonpositive B1 clock delta")
    velocities = [
        (values[i] - values[i - 1]) / deltas[i - 1]
        for i in range(1, len(values))
    ]
    accelerations = [
        (velocities[i] - velocities[i - 1])
        / ((deltas[i - 1] + deltas[i]) / 2)
        for i in range(1, len(velocities))
    ]
    durations = [row["b0_test_duration_seconds"] for row in rows]
    med = statistics.median(durations)
    mad = statistics.median(abs(x - med) for x in durations)
    base_report = core.build(doc)
    frozen_three = core.build({**doc, "observations": rows[:3]})
    base_report["historical_engine_metrics"] = base_report.pop(
        "three_pulse_metrics"
    )
    base_report["schema"] = OUT_SCHEMA
    base_report["hierarchy"]["workflow"]["run_sample"] = 4
    base_report["four_pulse_metrics"] = {
        "sampled_run_success": [4, 4],
        "native_b0_jobs": [sum(x["job_success"] for x in rows),
                           sum(x["job_total"] for x in rows)],
        "b1_source_config_identity": next(iter(identities)),
        "b1_scope": "SAME_SCANNER_SOURCE_AND_WORKFLOW_SOURCE_ONLY",
        "b1_raw_unguarded_counts": values,
        "b1_intervals_hours": [round(x, 6) for x in deltas],
        "b1_velocity_findings_per_hour": [round(x, 6) for x in velocities],
        "b1_acceleration_findings_per_hour2": [
            round(x, 6) for x in accelerations
        ],
        "b1_trend": "FLAT_UNGUARDED_FINDING_COUNT",
        "test_count_velocity": None,
        "test_count_population": "UNMATCHED_PR_HEADS",
        "duration_median_seconds": med,
        "duration_mad_seconds": round(mad, 3),
        "duration_prior_three_median_seconds": frozen_three[
            "three_pulse_metrics"
        ]["duration_median_seconds"],
        "accepted_matched_coverage_uplift": None,
        "source_root_closure": None,
        "global_ci_share": None,
    }
    base_report["forecast"] = {
        "target": "NEXT_CONFIG_MATCHED_B1_UNGUARDED_COUNT",
        "origin_run": rows[-1]["run_id"],
        "point_estimate": values[-1],
        "model": "ONE_STEP_PERSISTENCE_REQUIRES_UNCHANGED_SOURCE_CONFIG",
        "state": "PROSPECTIVE_UNCALIBRATED_SOURCE_CONDITIONAL",
        "prediction_interval": None,
        "actual": None,
        "error": None,
    }
    base_report["merge_admission"] = "HOLD"
    base_report["authority_transfer"] = False
    return base_report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    result = extend(json.loads(args.input.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "DESCRIPTIVE_FOUR_PULSE_SOURCE_MATCHED_B1",
        "pulses": 4, "admission": "HOLD"
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
