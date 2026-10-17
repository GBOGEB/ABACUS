"""N+2 read-only B-series stability adapter for five native historical flights.

Never turns a constant detection count into a Six Sigma, coverage, or
engineering-root closure claim. It consumes the canonical B0 metric provider.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import b_series_nplus1_metrics as nplus1
import b_series_temporal_metrics as core

SCHEMA = "abacus.bseries.nplus2-fingerprint-stability.v1"
LEDGER = "abacus.bseries.b1-fingerprint-ledger.v1"
PULSES = ["N-2", "N-1", "N", "N+1", "N+2"]


def _expected_fingerprint(item):
    if not isinstance(item, dict):
        raise core.EvidenceError("invalid fingerprint atom")
    path, line = item.get("path"), item.get("line")
    pats, source = item.get("patterns"), item.get("text")
    if (
        not isinstance(path, str)
        or not path.startswith(".github/workflows/")
        or type(line) is not int
        or line <= 0
        or not isinstance(pats, list)
        or not pats
        or any(not isinstance(x, str) or not x for x in pats)
        or pats != sorted(set(pats))
        or not isinstance(source, str)
        or not source
    ):
        raise core.EvidenceError("invalid native finding fingerprint")
    return json.dumps([path, line, pats, source], separators=(",", ":"))


def _finite_fraction(num, denom):
    if type(num) is not int or type(denom) is not int or denom <= 0:
        raise core.EvidenceError("invalid B1 scan denominator")
    if num < 0:
        raise core.EvidenceError("negative B1 detection")
    return round(num / denom, 6)


def extend(observed, prior, fingerprint):
    rows = core.validate(observed)
    old_rows = core.validate(prior)
    if (
        observed.get("extension")
        != "N_PLUS_2_FINGERPRINT_STABILITY_SCOPE_DRIFT"
        or observed.get("versioned_from")
        != "docs/ci/B_SERIES_NATIVE_NPLUS1_20261017.json"
        or observed.get("fingerprint_ledger_path")
        != "docs/ci/B_SERIES_B1_FINGERPRINT_CENSUS_20261017.json"
    ):
        raise core.EvidenceError("unbound N+2 lineage")
    if len(rows) != 5 or [x["pulse"] for x in rows] != PULSES:
        raise core.EvidenceError("N+2 pulse identity/order mismatch")
    if len(old_rows) != 4 or [x["pulse"] for x in old_rows] != PULSES[:4]:
        raise core.EvidenceError("prior four-pulse source mismatch")
    for i, original in enumerate(old_rows):
        for field, value in original.items():
            if rows[i].get(field) != value:
                raise core.EvidenceError(
                    f"frozen prior pulse {i} changed: {field}"
                )
    if not isinstance(fingerprint, dict) or fingerprint.get("schema") != LEDGER:
        raise core.EvidenceError("unqualified fingerprint ledger")
    if fingerprint.get("authority_transfer") is not False:
        raise core.EvidenceError("authority transfer in fingerprint ledger")
    atoms = fingerprint.get("baseline_unguarded_fingerprints")
    if not isinstance(atoms, list) or len(atoms) != 139:
        raise core.EvidenceError("fingerprint baseline incomplete")
    keys = [_expected_fingerprint(atom) for atom in atoms]
    if len(set(keys)) != len(keys):
        raise core.EvidenceError("duplicate B1 fingerprint atoms")
    comparisons = fingerprint.get("comparison")
    if not isinstance(comparisons, list) or len(comparisons) != 5:
        raise core.EvidenceError("incomplete native B1 comparisons")
    scan_files = []
    densities = []
    repeats = []
    for row, reference in zip(rows, comparisons):
        for key in ("pulse", "run_id", "source_sha"):
            if row.get(key) != reference.get(key):
                raise core.EvidenceError("native source/attempt mismatch")
        if row.get("b1_job_id") != reference.get("b1_job_id"):
            raise core.EvidenceError("B1 job identity mismatch")
        scanner, workflow = row.get("b1_scanner_blob_sha"), row.get(
            "b0_workflow_blob_sha"
        )
        ceiling = row.get("b1_max_unguarded")
        if (
            not isinstance(scanner, str)
            or not core.SHA.fullmatch(scanner)
            or not isinstance(workflow, str)
            or not core.SHA.fullmatch(workflow)
            or type(ceiling) is not int
            or ceiling <= 0
            or row.get("b1_source_config_identity")
            != f"{scanner}:{workflow}:{ceiling}"
        ):
            raise core.EvidenceError("B1 source-config identity cannot bind")
        for a, b in (
            ("b1_scanned_files", "scanned_files"),
            ("b1_allowed_count", "allowed_findings"),
            ("b1_unguarded", "unguarded_findings"),
            ("b1_finding_count", "total_findings"),
            ("b1_baseline_fingerprint_intersection", "baseline_intersection"),
            ("b1_new_fingerprints", "new_fingerprints"),
            ("b1_missing_fingerprints", "missing_fingerprints"),
        ):
            if row.get(a) != reference.get(b):
                raise core.EvidenceError(f"native B1 census mismatch: {a}")
        scanned = row["b1_scanned_files"]
        _finite_fraction(row["b1_unguarded"], scanned)
        if (
            type(row["b1_allowed_count"]) is not int
            or type(row["b1_finding_count"]) is not int
            or row["b1_allowed_count"] + row["b1_unguarded"]
            != row["b1_finding_count"]
        ):
            raise core.EvidenceError("B1 findings do not reconcile")
        intersect = row["b1_baseline_fingerprint_intersection"]
        new = row["b1_new_fingerprints"]
        missing = row["b1_missing_fingerprints"]
        if any(type(x) is not int or x < 0 for x in (intersect, new, missing)):
            raise core.EvidenceError("invalid fingerprint intersection")
        if (
            intersect + missing != len(keys)
            or intersect + new != row["b1_unguarded"]
        ):
            raise core.EvidenceError("B1 fingerprint population does not join")
        repeats.append(round(intersect / (len(keys) + new), 6))
        scan_files.append(scanned)
        densities.append(_finite_fraction(row["b1_unguarded"], scanned))
    identity = {row.get("b1_source_config_identity") for row in rows}
    if len(identity) != 1:
        raise core.EvidenceError("scanner configuration identity drift")
    # Consume the existing qualified four-pulse estimator, without rewriting it.
    four = nplus1.extend(prior)
    qualified = [
        {**row, "b1_config_fingerprint": row["b1_source_config_identity"]}
        for row in rows
    ]
    candidate = core.build({**observed, "observations": qualified})
    durations = [row["b0_test_duration_seconds"] for row in rows]
    median = statistics.median(durations)
    mad = statistics.median(abs(x - median) for x in durations)
    b1_clocks = [core._timestamp(row["b1_observation_at"]) for row in rows]
    intervals = [
        (b1_clocks[i] - b1_clocks[i - 1]).total_seconds() / 3600
        for i in range(1, len(rows))
    ]
    if any(not math.isfinite(x) or x <= 0 for x in intervals):
        raise core.EvidenceError("nonmonotonic B1 clocks")
    raw = [row["b1_unguarded"] for row in rows]
    velocities = [
        (raw[i] - raw[i - 1]) / intervals[i - 1]
        for i in range(1, len(rows))
    ]
    scope_identical = len(set(scan_files)) == 1
    candidate["schema"] = SCHEMA
    candidate["legacy_engine_metrics"] = candidate.pop("three_pulse_metrics")
    candidate["prior_four_pulse"] = {
        "last_run": prior["observations"][-1]["run_id"],
        "duration_median_seconds": four["four_pulse_metrics"][
            "duration_median_seconds"
        ],
        "duration_mad_seconds": four["four_pulse_metrics"][
            "duration_mad_seconds"
        ],
    }
    candidate["five_pulse_metrics"] = {
        "native_run_pass_fraction": [
            sum(x["job_success"] == x["job_total"] for x in rows),
            len(rows),
        ],
        "native_job_success_fraction": [
            sum(x["job_success"] for x in rows),
            sum(x["job_total"] for x in rows),
        ],
        "b1_fingerprint_jaccard_to_baseline": repeats,
        "b1_unique_reference_fingerprints": len(keys),
        "b1_new_fingerprints": [x["b1_new_fingerprints"] for x in rows],
        "b1_missing_fingerprints": [x["b1_missing_fingerprints"] for x in rows],
        "b1_scanned_workflow_files": scan_files,
        "b1_findings_per_scanned_file": densities,
        "b1_findings_per_scanned_file_unit": "findings/file, NOT coverage",
        "b1_finding_counts": raw,
        "b1_raw_velocity_findings_per_hour": [
            round(x, 6) for x in velocities
        ],
        "b1_scope_status": (
            "IDENTICAL_SCANNED_FILE_COUNTS_ONLY"
            if scope_identical
            else "SCANNED_WORKFLOW_DENOMINATOR_DRIFT"
        ),
        "b1_interpretation": (
            "PERSISTENT_FINGERPRINTS_WITH_SCOPE_DRIFT"
            if not scope_identical
            else "PERSISTENT_FINGERPRINTS_NO_DETECTED_ARRIVALS"
        ),
        "duration_median_seconds": round(median, 3),
        "duration_mad_seconds": round(mad, 3),
        "test_population_velocity": None,
        "matched_statement_coverage_delta": None,
        "matched_branch_coverage_delta": None,
        "main_coverage_delta": None,
        "root_closure_credit": None,
        "six_sigma_capability": None,
        "global_workflow_denominator": None,
    }
    candidate["forecast"] = {
        "origin_run": rows[-1]["run_id"],
        "next_pulse": "N+3",
        "target": "B1_UNGUARDED_SAME_SCANNER_AND_SCOPE",
        "model": "PERSISTENCE_NPLUS2",
        "point_estimate": raw[-1],
        "generated_after_origin": True,
        "pre_registered_actual": None,
        "forecast_error": None,
        "forecast_calibration": None,
        "status": "CONDITIONAL_UNCALIBRATED",
    }
    candidate["assurance"] = {
        "fingerprint_set_comparison": "NATIVE_JOB_LOG_OBSERVATION",
        "independent_github_reauthentication": False,
        "frozen_four_pulse_identity_preserved": True,
        "source_config_equal": True,
        "scope_count_equal": scope_identical,
        "six_sigma_claim_permitted": False,
    }
    candidate["merge_admission"] = "HOLD"
    candidate["authority_transfer"] = False
    candidate["formal_root_closures"] = None
    return candidate


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--observed", type=Path, required=True)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--fingerprints", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    result = extend(
        json.loads(args.observed.read_text(encoding="utf-8")),
        json.loads(args.prior.read_text(encoding="utf-8")),
        json.loads(args.fingerprints.read_text(encoding="utf-8")),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["five_pulse_metrics"]["b1_interpretation"],
        "pulses": 5,
        "admission": "HOLD",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
