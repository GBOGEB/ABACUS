#!/usr/bin/env python3
"""Read-only Ariana N-series/Rex projection; GitHub records retain authority.

This is an evaluator, not an execution scheduler or acceptance controller.
It does not mutate repository sources, dispatch jobs, or grant QPS/KEB credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import re
import sys
import zipfile


SCHEMA = "abacus.ariana.rex_nseries_projection.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
LANES = {"3.11", "3.12"}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def utc(value: str) -> datetime:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(date.tzinfo is not None, "UTC timestamps must be offset aware")
    return date


def fraction(part: dict) -> float:
    num = part["numerator"]
    den = part["denominator"]
    require(
        isinstance(num, int) and isinstance(den, int)
        and not isinstance(num, bool) and den > 0 and 0 <= num <= den,
        "invalid numerator or denominator",
    )
    return num / den


def wilson(k: int, n: int) -> dict | None:
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    denom = 1 + z * z / n
    middle = (p + z * z / (2 * n)) / denom
    radius = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {"lower": round(max(0, middle - radius), 6),
            "upper": round(min(1, middle + radius), 6)}


def validate_ledger(ledger: dict) -> None:
    require(ledger.get("schema") == SCHEMA, "unexpected REX schema")
    require(ledger.get("authority") == "DERIVED_REX_OBSERVATIONS_NOT_SSOT",
            "REX must remain derived analysis")
    parent = ledger["parent"]
    require(parent["repository"] == "GBOGEB/ABACUS", "source repo changed")
    require(SHA.fullmatch(parent["source_pr_head_sha"]) is not None,
            "source PR head must be an exact SHA")
    require(parent["merge_admission"] == "HOLD", "admission cannot be promoted")
    require(parent["qps_engineering_acceptance"] is None,
            "QPS authority cannot be imputed")
    points = ledger["checkpoints"]
    require(len(points) == 3, "exactly three G3P pulse slots required")
    require([p["index"] for p in points] == [-1, 0, 1],
            "N-1/N/N+1 order is invalid")
    require([p["label"] for p in points] == ["N-1", "N", "N+1"],
            "pulse labels changed")
    require(len({p["run_id"] for p in points}) == 3, "run IDs reused")
    require(len({p["source_sha"] for p in points}) == 3,
            "distinct exact-head source SHAs required")
    require([p["created_at"] for p in points] == sorted(
        p["created_at"] for p in points
    ), "pulses must be ordered by native creation time")

    artifact_ids = set()
    for point in points:
        require(SHA.fullmatch(point["source_sha"]) is not None,
                "source SHA missing")
        require(isinstance(point["run_attempt"], int)
                and point["run_attempt"] > 0, "missing run attempt")
        require(utc(point["created_at"]) <= utc(point["completed_at"]),
                "native completion precedes creation")
        require(set(point["python_jobs"]) == LANES,
                "native Python job identities incomplete")
        require(all(isinstance(job, int) and job > 0
                    for job in point["python_jobs"].values()),
                "invalid job ID")
        require(point["conclusion"] in {"success", "failure"},
                "unobserved run cannot be called terminal")
        tests = point["tests"]
        if tests is not None:
            require(set(tests) == LANES, "unmatched Python test lanes")
            for row in tests.values():
                require(
                    isinstance(row["total"], int)
                    and isinstance(row["passed"], int)
                    and isinstance(row["failures"], int)
                    and row["total"] > 0
                    and row["passed"] + row["failures"] <= row["total"],
                    "invalid tests numerator/denominator",
                )
        else:
            require(point["focused_coverage"] is None,
                    "no test collection cannot have measured coverage")
        coverage = point["focused_coverage"]
        if coverage is not None:
            require(tests is not None, "coverage without executed tests")
            require(SHA.fullmatch(point["source_sha"]) is not None,
                    "coverage without exact source")
            require(DIGEST.fullmatch(
                coverage["source_file_sha256"]) is not None,
                "coverage must bind source file digest")
            s = coverage["statement"]
            b = coverage["branch"]
            c = coverage["combined"]
            fraction(s)
            fraction(b)
            fraction(c)
            require(
                c["numerator"] == s["numerator"] + b["numerator"]
                and c["denominator"] == s["denominator"] + b["denominator"],
                "combined coverage scope is inconsistent",
            )
            require(coverage["changed_line"] is None,
                    "no artificial changed-line credit")
            require(len(point["artifacts"]) >= 2,
                    "focused coverage lacks durable source artifacts")
        for item in point["artifacts"]:
            require(item["id"] not in artifact_ids, "artifact ID reused")
            artifact_ids.add(item["id"])
            require(DIGEST.fullmatch(item["sha256"]) is not None,
                    "artifact digest missing")
        root = point["root"]
        require(root["distinct_roots"] in (0, 1),
                "root family must not equal manifestation count")
        if root["distinct_roots"] == 0:
            require(root["root_id"] is None, "unknown root marked closed")
        else:
            require(bool(root["root_id"]) and root["manifestation_jobs"],
                    "root has no observed job manifestations")
        if point["join"]["status"] == "PASS":
            require(point["conclusion"] == "success",
                    "false-green join conflicts with workflow")
            require(point["join"]["qps_engineering_acceptance"] is None,
                    "local join cannot claim QPS acceptance")
            require(point["join"]["remote_keb_or_qps_receipts"] is None,
                    "remote exchange is not authenticated")
            require(point["join"]["merge_admission"] == "HOLD",
                    "local join cannot grant merge")

    forecast_ids = set()
    run_index = {p["run_id"]: p for p in points}
    for forecast in ledger["forecasts"]:
        require(forecast["id"] not in forecast_ids, "forecast ID reused")
        forecast_ids.add(forecast["id"])
        target = run_index.get(forecast["target_run_id"])
        require(target is not None, "forecast target is not in pulse series")
        require(utc(forecast["frozen_at"]) < utc(target["created_at"]),
                "forecast written after target execution: hindsight leakage")
        require(forecast["milestone"] in target["milestones"],
                "milestone is not observed in target scope")
        require(type(forecast["expected"]) is bool,
                "directional forecast must be boolean")
        probability = forecast.get("probability")
        # None of the three archived forecast comments contained numeric p.
        # Changing JSON after execution cannot invent pre-registered Brier.
        require(probability is None, "historical probability was not preregistered")
        require(str(forecast["freeze_url"]).startswith("https://github.com/"),
                "forecast has no source citation")
    future = ledger["prospective"]
    require(future["checkpoint"] == "N+2" and future["run_id"] is None
            and future["observed"] is None, "future evidence was fabricated")
    require(future["probability"] is None,
            "low-sample prospective probability is not calibrated")
    require(future["source_precondition_sha"] == points[-1]["source_sha"],
            "future forecast must be pinned to latest verified head")
    require(future["forecast_admission"] == "HOLD_UNTIL_INDEPENDENT_GATES_PASS",
            "forecast cannot override review/CI/security gates")


def verify_archives(ledger: dict, directory: Path) -> list[int]:
    """Explicit optional byte replay: 3 GitHub artifacts, no network or extraction."""
    point = ledger["checkpoints"][-1]
    ids = []
    for item in point["artifacts"]:
        path = directory / f"github-actions-artifact-{item['id']}.zip"
        require(path.is_file(), f"missing archive: {path.name}")
        require(path.stat().st_size <= 10_000_000, "archive exceeds replay limit")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == item["sha256"], f"archive hash mismatch: {item['id']}")
        with zipfile.ZipFile(path) as archive:
            require(set(archive.namelist()) == set(item["contains"]),
                    f"unexpected artifact files: {item['id']}")
            require(all(info.file_size <= 10_000_000
                        for info in archive.infolist()), "oversized artifact member")
            require(archive.testzip() is None, "corrupt artifact member")
            member = ("two-lane-join.json" if item["lane"] == "join"
                      else "ariana-dow-receipt.json")
            receipt = json.loads(archive.read(member))
        if item["lane"] == "join":
            require(receipt["source_sha"] == point["source_sha"],
                    "join is bound to a different head")
            require(receipt["merge_admission"] == "HOLD"
                    and receipt["qps_engineering_acceptance"] is None
                    and receipt["remote_keb_or_qps_receipts"] is None,
                    "join falsely promotes remote acceptance")
            require(set(receipt["python_lanes"]) == LANES,
                    "joined Python lane populations do not match")
        else:
            require(receipt["producer"]["source_sha"] == point["source_sha"],
                    "native receipt head mismatch")
            require(receipt["producer"]["run_id"] == str(point["run_id"])
                    and receipt["producer"]["run_attempt"] == str(point["run_attempt"]),
                    "native receipt run/attempt mismatch")
            require(receipt["producer"]["python_version"] == item["lane"],
                    "native receipt Python lane mismatch")
            measured = receipt["native_test_receipt"]
            for field in ("total", "passed", "failures"):
                require(measured[field] == point["tests"][item["lane"]][field],
                        "native JUnit counters mismatch")
            scope = receipt["focused_coverage"]
            for kind, key in (("statements", "statement"),
                              ("branches", "branch"), ("combined", "combined")):
                require(scope[kind] == point["focused_coverage"][key],
                        "focused coverage numerators do not match")
            require(receipt["disposition"] == "LOCAL_TESTED_FEDERATION_HOLD",
                    "receipt falsely promotes remote engineering")
        ids.append(item["id"])
    return ids


def evaluate(ledger: dict, archive_dir: Path | None = None) -> dict:
    validate_ledger(ledger)
    points = ledger["checkpoints"]
    run_map = {p["run_id"]: p for p in points}
    scored = []
    probabilities = []
    for forecast in ledger["forecasts"]:
        point = run_map[forecast["target_run_id"]]
        actual = point["milestones"][forecast["milestone"]]
        hit = None if actual is None else actual == forecast["expected"]
        scored.append({
            "id": forecast["id"], "label": point["label"],
            "frozen_at": forecast["frozen_at"], "run_id": point["run_id"],
            "predicted": forecast["expected"], "actual": actual,
            "hit": hit, "freeze_url": forecast["freeze_url"],
        })
        if actual is not None and forecast["probability"] is not None:
            probabilities.append((forecast["probability"] - int(actual)) ** 2)
    considered = [p for p in scored if p["hit"] is not None]
    hits = sum(p["hit"] for p in considered)
    calibration_minimum = ledger["calibration"]["minimum_independent_comparable_forecasts"]
    archive_ids = verify_archives(ledger, archive_dir) if archive_dir else None
    series = []
    for point in points:
        tests = point["tests"]
        coverage = point["focused_coverage"]
        wall = (utc(point["completed_at"]) - utc(point["created_at"])).total_seconds()
        series.append({
            "label": point["label"], "run_id": point["run_id"],
            "head": point["source_sha"], "run_attempt": point["run_attempt"],
            "conclusion": point["conclusion"], "wall_seconds_including_queue": int(wall),
            "tested_per_lane": None if tests is None else tests["3.11"]["total"],
            "passed_per_lane": None if tests is None else tests["3.11"]["passed"],
            "local_first_red_root": point["root"]["root_id"],
            "distinct_roots": point["root"]["distinct_roots"],
            "job_manifestations": len(point["root"]["manifestation_jobs"]),
            "durable_artifacts": len(point["artifacts"]),
            "join": point["join"]["status"],
            "focused_statement": None if coverage is None else coverage["statement"],
            "focused_branch": None if coverage is None else coverage["branch"],
        })
    return {
        "schema": "abacus.ariana.rex_prediction_evaluation.v1",
        "input_projection_schema": SCHEMA,
        "lineage": {"repository": ledger["parent"]["repository"],
                    "issue": ledger["parent"]["issue"],
                    "source_pr": ledger["parent"]["source_pr"]},
        "series": series,
        "directional_forecasts": {
            "scored": scored, "hits": hits, "n": len(considered),
            "observed_hit_rate": hits / len(considered) if considered else None,
            "wilson_95": wilson(hits, len(considered)),
            "brier": (sum(probabilities) / len(probabilities)
                      if probabilities else None),
            "calibration": ("UNQUALIFIED_SMALL_N" if len(probabilities) < calibration_minimum
                            else "REQUIRES_INDEPENDENT_SCOPE_AUDIT"),
            "backfilled_probabilities": False,
        },
        "coverage_deltas": {
            "N_minus_1_to_N": None,
            "N_to_N_plus_1": None,
            "reason": "MISSING_EARLIER_DURABLE_K_D_AND_DIFFERENT_TEST_COHORT",
            "latest_focused_statement": points[-1]["focused_coverage"]["statement"],
            "latest_focused_branch": points[-1]["focused_coverage"]["branch"],
        },
        "rex": {
            "observed_source_first_red_roots_in_series": len({
                p["root"]["root_id"] for p in points
                if p["root"]["root_id"] is not None
            }),
            "repeat_observations_of_existing_root": (
                sum(p["root"]["distinct_roots"] for p in points)
                - len({p["root"]["root_id"] for p in points
                       if p["root"]["root_id"] is not None})
            ),
            "root_manifestations": sum(len(p["root"]["manifestation_jobs"])
                                       for p in points),
            "lesson_ids": [r["root_id"] for r in ledger["rex"]],
            "six_sigma_claim": "NOT_ESTABLISHED",
        },
        "archive_byte_replay": {"state": "VERIFIED" if archive_ids else "NOT_REPLAYED",
                                "artifact_ids": archive_ids},
        "prospective": ledger["prospective"],
        "governance": {
            "merge_admission": "HOLD", "accepted_N_delta": 0,
            "remote_keb_or_qps_acceptance": None,
            "security_and_independent_review": "NOT_INFERRED_FROM_LOCAL_CI",
        },
    }


def markdown(report: dict) -> str:
    body = [
        "# Ariana REX: N-1 -> N -> N+1 (derived, read-only)",
        "",
        "| Pulse | Native run | Result | Tests per lane | First-red root | Artifacts | Local join |",
        "|---|---:|---|---:|---|---:|---|",
    ]
    for row in report["series"]:
        test_count = "N/A" if row["tested_per_lane"] is None else (
            f"{row['passed_per_lane']}/{row['tested_per_lane']}")
        body.append(
            f"| {row['label']} | {row['run_id']} | {row['conclusion'].upper()} | "
            f"{test_count} | {row['local_first_red_root'] or 'NONE_LOCAL'} | "
            f"{row['durable_artifacts']} | {row['join']} |"
        )
    f = report["directional_forecasts"]
    body += [
        "",
        f"**Frozen milestone matches:** {f['hits']}/{f['n']} "
        f"(Wilson 95% {f['wilson_95']}); "
        "not a calibrated probability or a six-sigma claim.",
        "",
        "**Brier:** N/A; historical forecasts contained no numeric probability. "
        "No probability was retroactively assigned.",
        "",
        "**Matched coverage delta:** UNKNOWN before N+1. "
        "N+1 focused statements 208/209 and branches 39/42; "
        "28 -> 29 tests is test-set expansion, not comparable coverage growth.",
        "",
        f"**Native artifact byte replay:** {report['archive_byte_replay']['state']}.",
        "",
        "**N+2:** conditional same-source expectation of 29 tests per lane "
        "and 208/209 statements, 39/42 branches; no observed N+2. "
        "Independent governance/security/KEB/QPS gates remain HOLD.",
        "",
    ]
    return "\n".join(body)


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input", type=Path, required=True)
    cli.add_argument("--archives", type=Path)
    cli.add_argument("--format", choices=("json", "markdown"), default="json")
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    try:
        ledger = json.loads(args.input.read_text(encoding="utf-8"))
        report = evaluate(ledger, args.archives)
        result = (json.dumps(report, indent=2, sort_keys=True) + "\n"
                  if args.format == "json" else markdown(report))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding="utf-8")
        else:
            print(result)
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            json.JSONDecodeError) as exc:
        print(f"ARIANA_REX_FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
