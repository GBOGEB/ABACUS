#!/usr/bin/env python3
"""Local-first, fail-closed floating-code testflight and N+2 pulse controller.

This is a read-only decision aid. It neither triggers workers nor grants
merge, security, root-closure or engineering-acceptance authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from defusedxml import ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

FORECAST_SCHEMA = "codepurple.floating.testflight.forecast.v1"
OBS_SCHEMA = "codepurple.floating.testflight.observation.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_SELECTION = (
    "tests/test_coverage_dab_census.py "
    "tests/test_floating_evidence_join.py "
    "tests/test_mip_pulse_rollup.py "
    "tests/test_floating_testflight.py "
    "tools/triage/test_floating_anchor_census.py "
    "tests/test_mip_v3_frontier.py "
    "tests/test_mip_v3_temporal.py "
    "tests/test_floating_accelerator_receiver.py"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_stamp(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "UTC timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.utcoffset().total_seconds() == 0, "UTC offset required")
    return result


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "JSON object required")
    return value


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def source_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        capture_output=True, check=True,
    )
    head = result.stdout.strip()
    require(bool(HEX40.fullmatch(head)), "invalid git HEAD")
    return head


def check_head(root: Path, expected: str) -> str:
    require(bool(HEX40.fullmatch(expected)), "invalid expected head")
    observed = source_head(root)
    require(observed == expected, "checkout is not exact expected SHA")
    return observed


def fraction(covered: int | None, eligible: int | None) -> float | None:
    if type(covered) is not int or type(eligible) is not int or eligible <= 0:
        return None
    require(0 <= covered <= eligible, "invalid measured coverage fraction")
    return round(covered / eligible, 9)


def selection_hash(selection: str) -> str:
    return hashlib.sha256(" ".join(selection.split()).encode("utf-8")).hexdigest()


def forecast(head: str, pulse: int, selection: str, prior: dict | None = None,
             now: str | None = None) -> dict:
    require(bool(HEX40.fullmatch(head)), "head SHA required")
    require(type(pulse) is int and pulse >= 1, "positive pulse clock required")
    issued = now or stamp()
    parse_stamp(issued)
    previous = {"test_pass_fraction": None, "statement_fraction": None,
                "branch_fraction": None}
    prior_identity = None
    if prior is not None:
        require(prior.get("schema") == OBS_SCHEMA, "prior observation schema")
        require(parse_stamp(prior["observed_at"]) < parse_stamp(issued),
                "forecast cannot be issued before its baseline")
        require(prior.get("selection_sha256") == selection_hash(selection),
                "prior test selection differs")
        counts = prior.get("tests") or {}
        if prior.get("terminal") and counts.get("executed"):
            previous["test_pass_fraction"] = fraction(
                counts.get("passed"), counts.get("executed"))
        coverage = prior.get("coverage") or {}
        for family, key in (("statements", "statement_fraction"),
                            ("branches", "branch_fraction")):
            row = coverage.get(family) or {}
            previous[key] = fraction(row.get("covered"), row.get("eligible"))
        prior_identity = {
            "head_sha": prior.get("head_sha"),
            "observed_at": prior.get("observed_at"),
            "run_id": prior.get("run_id"),
            "run_attempt": prior.get("run_attempt"),
            "scope_sha256": coverage.get("scope_sha256"),
            "config_sha256": coverage.get("config_sha256"),
        }
    payload = {
        "schema": FORECAST_SCHEMA, "repository": "GBOGEB/ABACUS",
        "head_sha": head, "issued_at": issued,
        "issued_after_pulse": pulse - 1, "target_pulses": [pulse, pulse + 1],
        "selection_sha256": selection_hash(selection),
        "estimator": "persistence-v1" if prior is not None else "NOT_ESTIMABLE",
        "prediction": previous, "prior_observation": prior_identity,
        "scope": "FOCUSED_TESTFLIGHT_ONLY",
        "authority_transfer": False, "merge_admission": "HOLD",
    }
    payload["seal_sha256"] = digest(payload)
    return payload


def validate_forecast(value: dict) -> None:
    require(value.get("schema") == FORECAST_SCHEMA, "forecast schema")
    seal = value.get("seal_sha256")
    require(isinstance(seal, str) and seal == digest({
        k: v for k, v in value.items() if k != "seal_sha256"
    }), "forecast seal mismatch")


def read_junit(path: Path) -> dict | None:
    if not path.is_file():
        return None
    require(path.stat().st_size <= 64 * 1024 * 1024, "JUnit exceeds size cap")
    root = ET.parse(path).getroot()
    require(root.tag in ("testsuite", "testsuites"), "invalid JUnit root")
    cases = list(root.iter("testcase"))
    outcomes = {"executed": len(cases), "passed": 0, "failed": 0,
                "errors": 0, "skipped": 0}
    fingerprints = []
    for case in cases:
        case_id = (case.get("classname", "") + "::" + case.get("name", ""))[:220]
        if case.find("failure") is not None:
            outcomes["failed"] += 1
            fingerprints.append(case_id)
        elif case.find("error") is not None:
            outcomes["errors"] += 1
            fingerprints.append(case_id)
        elif case.find("skipped") is not None:
            outcomes["skipped"] += 1
        else:
            outcomes["passed"] += 1
    require(sum(outcomes[k] for k in ("passed", "failed", "errors", "skipped"))
            == outcomes["executed"], "JUnit counts do not reconcile")
    return {"counts": outcomes, "failure_fingerprints": sorted(set(fingerprints)),
            "failure_occurrences": len(fingerprints),
            "distinct_root_ids": None}


def measured_coverage(path: Path, root: Path) -> dict | None:
    if not path.is_file():
        return None
    payload = read(path)
    totals = payload.get("totals") or {}
    branch_mode = payload.get("meta", {}).get("branch_coverage") is True
    statements = {"covered": totals.get("covered_lines"),
                  "eligible": totals.get("num_statements")}
    branches = ({"covered": totals.get("covered_branches"),
                 "eligible": totals.get("num_branches")}
                if branch_mode else {"covered": None, "eligible": None})
    for row in (statements, branches):
        if row["covered"] is not None or row["eligible"] is not None:
            require(type(row["covered"]) is int
                    and type(row["eligible"]) is int
                    and 0 <= row["covered"] <= row["eligible"],
                    "invalid coverage numerator/denominator")
    files = payload.get("files", {})
    require(isinstance(files, dict), "coverage files must be mapped")
    scope_rows = []
    zero_files = []
    for name, info in sorted(files.items()):
        local = (root / name).resolve()
        require(local.is_relative_to(root.resolve()), "coverage path escapes root")
        if not local.is_file():
            return {"statements": statements, "branches": branches,
                    "scope_sha256": None, "config_sha256": None,
                    "zero_covered_paths": None, "status": "UNRESOLVED_SOURCE_PATH"}
        summary = info.get("summary") or {}
        eligible = summary.get("num_statements")
        covered = summary.get("covered_lines")
        require(type(eligible) is int and type(covered) is int
                and 0 <= covered <= eligible, "invalid file coverage")
        if eligible > 0 and covered == 0:
            zero_files.append(name)
        scope_rows.append([name, hashlib.sha256(local.read_bytes()).hexdigest(),
                           eligible, summary.get("num_branches")])
    config_rows = []
    for name in ("pyproject.toml", "pytest.ini"):
        file = root / name
        if file.is_file():
            config_rows.append([name, hashlib.sha256(file.read_bytes()).hexdigest()])
    config_rows.append(["coverage_version", payload.get("meta", {}).get("version")])
    return {"statements": statements, "branches": branches,
            "scope_sha256": digest(scope_rows),
            "config_sha256": digest(config_rows),
            "zero_covered_paths": zero_files, "status": "MEASURED"}


def positive_env_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    require(raw.isdecimal() and int(raw) > 0, "invalid " + name)
    return int(raw)


def observe(frozen: dict, junit: dict | None, coverage: dict | None,
            *, head: str, selection: str, now: str | None = None,
            run_id: int | None = None, run_attempt: int | None = None,
            job: str | None = None) -> dict:
    validate_forecast(frozen)
    require(frozen["head_sha"] == head, "forecast source SHA mismatch")
    require(frozen["selection_sha256"] == selection_hash(selection),
            "test selection changed after forecast")
    observed_at = now or stamp()
    require(parse_stamp(frozen["issued_at"]) < parse_stamp(observed_at),
            "observation must follow frozen forecast")
    counts = junit["counts"] if junit else None
    terminal = bool(counts and counts["executed"] > 0)
    state = ("UNKNOWN" if not terminal else "RED"
             if counts["failed"] or counts["errors"] else "GREEN_WITH_SKIPS"
             if counts["skipped"] else "GREEN")
    actual = {
        "test_pass_fraction": fraction(counts["passed"], counts["executed"])
        if terminal else None,
        "statement_fraction": fraction(
            (coverage or {}).get("statements", {}).get("covered"),
            (coverage or {}).get("statements", {}).get("eligible")),
        "branch_fraction": fraction(
            (coverage or {}).get("branches", {}).get("covered"),
            (coverage or {}).get("branches", {}).get("eligible")),
    }
    baseline = frozen.get("prior_observation") or {}
    cov = coverage or {}
    matched_baseline = bool(
        baseline.get("scope_sha256")
        and baseline.get("scope_sha256") == cov.get("scope_sha256")
        and baseline.get("config_sha256")
        and baseline.get("config_sha256") == cov.get("config_sha256")
    )
    forecast_errors = {
        key: (round(actual[key] - predicted, 9)
              if matched_baseline and predicted is not None
              and actual[key] is not None else None)
        for key, predicted in frozen["prediction"].items()
    }
    return {
        "schema": OBS_SCHEMA, "repository": "GBOGEB/ABACUS",
        "head_sha": head, "observed_at": observed_at,
        "pulse": frozen["target_pulses"][0],
        "selection_sha256": selection_hash(selection),
        "forecast_seal_sha256": frozen["seal_sha256"],
        "forecast_issued_at": frozen["issued_at"],
        "forecast_errors_signed": forecast_errors,
        "forecast_comparability": (
            "MATCHED_PRIOR_SCOPE" if matched_baseline
            else "WITHHELD_SCOPE_OR_PRIOR_MISMATCH"
        ),
        "tests": counts, "test_state": state, "terminal": terminal,
        "coverage": coverage,
        "first_red_fingerprints": (junit or {}).get("failure_fingerprints"),
        "first_red_occurrences": (junit or {}).get("failure_occurrences"),
        "verified_root_ids": None,
        "run_id": run_id, "run_attempt": run_attempt,
        "job_name": job, "job_id": None,
        "artifact_id": None, "zip_bytes_verified": None,
        "artifact_member_bytes_verified": None,
        "worker_hours": None, "worker_capacity": None,
        "federation_observed": None, "federation_eligible": None,
        "m1": "PARTIAL", "m2": "HOLD", "m3": "HOLD",
        "pca_bt": "NOT_QUALIFIED",
        "authority_transfer": False, "merge_admission": "HOLD",
    }


def compare(a: dict, b: dict) -> dict:
    require(a["schema"] == b["schema"] == OBS_SCHEMA, "observation schema")
    ax, bx = a.get("coverage") or {}, b.get("coverage") or {}
    reasons = []
    for key in ("scope_sha256", "config_sha256"):
        if not ax.get(key) or ax.get(key) != bx.get(key):
            reasons.append(key + "_MISMATCH")
    metrics = {}
    for family in ("statements", "branches"):
        old, new = ax.get(family) or {}, bx.get(family) or {}
        d = old.get("eligible")
        comparable = (not reasons and type(d) is int and d > 0
                      and new.get("eligible") == d)
        metrics[family] = {
            "covered_delta": new.get("covered") - old.get("covered")
            if comparable and type(new.get("covered")) is int
            and type(old.get("covered")) is int else None,
            "delta_pp": round(100 * (new["covered"] - old["covered"]) / d, 6)
            if comparable and type(new.get("covered")) is int
            and type(old.get("covered")) is int else None,
            "eligible": d if comparable else None,
        }
    return {"from_pulse": a["pulse"], "to_pulse": b["pulse"],
            "metrics": metrics,
            "population_comparable": not reasons and all(
                metrics[k]["delta_pp"] is not None
                for k in ("statements", "branches")),
            "reasons": reasons or None}


def control(observations: list[dict], target: float = 1.0) -> dict:
    require(0 < target <= 1, "target must be a fraction")
    require(len(observations) > 0, "at least one observation required")
    for row in observations:
        require(row.get("schema") == OBS_SCHEMA, "invalid pulse schema")
    require(all(a["pulse"] < b["pulse"]
                and parse_stamp(a["observed_at"]) < parse_stamp(b["observed_at"])
                for a, b in zip(observations, observations[1:])),
            "pulse clocks must strictly increase")
    identities = [(r["run_id"], r["run_attempt"]) for r in observations]
    confirmed = all(type(n) is int and n > 0 and type(attempt) is int
                    and attempt > 0 for n, attempt in identities)
    if confirmed:
        require(len(set(identities)) == len(identities),
                "native run/attempt identity reused")
    transitions = [compare(a, b) for a, b in zip(observations, observations[1:])]
    latest = observations[-1]
    stable_selection = len({
        item.get("selection_sha256") for item in observations[-4:]
    }) == 1
    if not latest["terminal"] or latest["test_state"] == "RED":
        state = "RESTART_FIRST_RED"
    elif transitions and not transitions[-1]["population_comparable"]:
        state = "REBASELINE_SCOPE_DRIFT"
    elif transitions and any(
            x["delta_pp"] is not None and x["delta_pp"] < 0
            for x in transitions[-1]["metrics"].values()):
        state = "RESTART_COVERAGE_REGRESSION"
    elif not confirmed or len(transitions) < 3 or not all(
            t["population_comparable"] for t in transitions[-3:]):
        state = "CONTINUE_MEASUREMENT"
    elif not stable_selection:
        state = "REBASELINE_TEST_SELECTION"
    else:
        latest_cov = latest["coverage"]
        saturated = all(fraction(latest_cov[part]["covered"],
                                 latest_cov[part]["eligible"]) is not None
                        and fraction(latest_cov[part]["covered"],
                                     latest_cov[part]["eligible"]) >= target
                        for part in ("statements", "branches"))
        healthy = all(r["terminal"] and r["test_state"] == "GREEN"
                      for r in observations[-4:])
        flat = all(all(abs(t["metrics"][part]["delta_pp"]) <= 0.05
                       for part in ("statements", "branches"))
                   for t in transitions[-3:])
        state = ("QUIET_WATCH_CANDIDATE" if saturated and healthy and flat
                 else "RERANK_UNCOVERED_OPPORTUNITIES" if flat
                 else "CONTINUE_MEASURED_IMPROVEMENT")
    return {
        "schema": "codepurple.floating.testflight.control.v1",
        "state": state, "pulse_count": len(observations),
        "transitions": transitions, "latest_sha": latest["head_sha"],
        "native_identities_structurally_present": confirmed,
        "native_identities_independently_verified": False,
        "test_selection_stable": stable_selection,
        "phase_two_authorized": False,
        "restart_on": ["new attributable first red", "new source SHA",
                       "population or instrumentor drift",
                       "branch or statement regression", "new verified consumer"],
        "merge_admission": "HOLD", "authority_transfer": False,
    }


def markdown_review(forecast_data: dict, observed: dict | None,
                    decision: dict | None) -> str:
    validate_forecast(forecast_data)
    rows = ["## CODE PURPLE floating-code testflight (review only)", "",
            "Forecast issued BEFORE selected tests were executed.",
            "No merger, root closure, QPS acceptance or cross-repo credit.", "",
            "| Field | Source-bound value |", "| --- | --- |",
            f"| Source SHA | `{forecast_data['head_sha']}` |",
            f"| Frozen forecast SHA-256 | `{forecast_data['seal_sha256']}` |",
            f"| Forecast UTC | {forecast_data['issued_at']} |",
            f"| Target pulses | {forecast_data['target_pulses']} |",
            f"| Method | {forecast_data['estimator']} |"]
    if observed:
        tests = observed.get("tests") or {}
        cov = observed.get("coverage") or {}
        predicted = forecast_data.get("prediction") or {}
        errors = observed.get("forecast_errors_signed") or {}
        rows.extend([
            f"| Forecast comparability | "
            f"{observed.get('forecast_comparability')} |",
            f"| Predicted test fraction | "
            f"{predicted.get('test_pass_fraction')} |",
            f"| Prediction signed error | "
            f"{errors.get('test_pass_fraction')} |",
            f"| Test state | {observed['test_state']} |",
            f"| Tests executed / pass / fail / error / skip | "
            f"{tests.get('executed', 'UNKNOWN')} / {tests.get('passed', 'UNKNOWN')} / "
            f"{tests.get('failed', 'UNKNOWN')} / {tests.get('errors', 'UNKNOWN')} / "
            f"{tests.get('skipped', 'UNKNOWN')} |",
            f"| Statements covered / eligible | "
            f"{(cov.get('statements') or {}).get('covered')} / "
            f"{(cov.get('statements') or {}).get('eligible')} |",
            f"| Branches covered / eligible | "
            f"{(cov.get('branches') or {}).get('covered')} / "
            f"{(cov.get('branches') or {}).get('eligible')} |",
            f"| Run / attempt / job ID | {observed.get('run_id')} / "
            f"{observed.get('run_attempt')} / UNKNOWN |",
            f"| Fingerprint occurrences / verified causal roots | "
            f"{observed.get('first_red_occurrences')} / UNKNOWN |",
            "| Artifact ZIP / member bytes | UNKNOWN pending independent validation |",
        ])
    if decision:
        rows.append(f"| Iteration decision | {decision['state']} |")
    rows.extend(["| Admission | HOLD |", "",
                 "The forecast is a pre-registered estimate or UNKNOWN, not "
                 "statistical certification. Native IDs and ZIP contents "
                 "require independent GitHub verification.", ""])
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("forecast")
    f.add_argument("--head", required=True)
    f.add_argument("--pulse", type=int, required=True)
    f.add_argument("--selection", default=DEFAULT_SELECTION)
    f.add_argument("--prior", type=Path)
    f.add_argument("--out", type=Path, required=True)
    o = sub.add_parser("observe")
    o.add_argument("--forecast", type=Path, required=True)
    o.add_argument("--junit", type=Path, required=True)
    o.add_argument("--coverage", type=Path, required=True)
    o.add_argument("--selection", default=DEFAULT_SELECTION)
    o.add_argument("--root", type=Path, default=Path.cwd())
    o.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("control")
    c.add_argument("observations", nargs="+", type=Path)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--target", type=float, default=1.0)
    r = sub.add_parser("review")
    r.add_argument("--forecast", type=Path, required=True)
    r.add_argument("--observation", type=Path)
    r.add_argument("--control", type=Path)
    r.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    if a.mode == "forecast":
        check_head(Path.cwd(), a.head)
        value = forecast(a.head, a.pulse, a.selection,
                         prior=read(a.prior) if a.prior else None)
        write_new(a.out, value)
    elif a.mode == "observe":
        frozen = read(a.forecast)
        check_head(a.root, frozen["head_sha"])
        value = observe(frozen, read_junit(a.junit),
                        measured_coverage(a.coverage, a.root),
                        head=frozen["head_sha"], selection=a.selection,
                        run_id=positive_env_int("GITHUB_RUN_ID"),
                        run_attempt=positive_env_int("GITHUB_RUN_ATTEMPT"),
                        job=os.environ.get("GITHUB_JOB"))
        write_new(a.out, value)
    elif a.mode == "control":
        write_new(a.out, control([read(path) for path in a.observations],
                                target=a.target))
    else:
        text = markdown_review(read(a.forecast),
                               read(a.observation) if a.observation else None,
                               read(a.control) if a.control else None)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("x", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
