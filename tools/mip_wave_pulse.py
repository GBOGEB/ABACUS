"""Fail-closed MIP wave measurements. Inputs are evidence, never merge authority."""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
ALLOWED = {"NEW", "INHERITED", "REPAIRED", "REOPENED", "DEFERRED"}
REQUIRED_ROOT = {"root_id", "owner", "state", "fingerprint"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(value, label):
    require(isinstance(value, str) and SHA.fullmatch(value), "invalid " + label)


def coverage_delta(before, after):
    if before is None or after is None:
        return {"disposition": "UNKNOWN", "reason": "missing comparable coverage"}
    for obj in (before, after):
        require(isinstance(obj, dict), "coverage must be object")
        for field in ("scope", "config_id", "source_sha", "lines_covered", "lines_total",
                      "branches_covered", "branches_total"):
            require(field in obj, "coverage missing " + field)
        sha(obj["source_sha"], "coverage source_sha")
        for f in ("lines_covered", "lines_total", "branches_covered", "branches_total"):
            require(type(obj[f]) is int and obj[f] >= 0, "invalid " + f)
        require(obj["lines_total"] > 0 and obj["branches_total"] > 0, "zero coverage denominator")
        require(obj["lines_covered"] <= obj["lines_total"] and obj["branches_covered"] <= obj["branches_total"], "coverage exceeds denominator")
    compatible = (before["scope"] == after["scope"] and
                  before["config_id"] == after["config_id"] and
                  before["lines_total"] == after["lines_total"] and
                  before["branches_total"] == after["branches_total"])
    if not compatible:
        return {"disposition": "INCOMPARABLE", "reason": "scope/config/denominator mismatch"}
    def pct(obj):
        return 100 * (obj["lines_covered"] + obj["branches_covered"]) / (obj["lines_total"] + obj["branches_total"])
    return {
        "disposition": "COMPARABLE", "scope": after["scope"], "config_id": after["config_id"],
        "before_source_sha": before["source_sha"], "after_source_sha": after["source_sha"],
        "before_percent": round(pct(before), 8), "after_percent": round(pct(after), 8),
        "delta_percentage_points": round(pct(after) - pct(before), 8),
        "new_lines": after["lines_covered"] - before["lines_covered"],
        "new_branches": after["branches_covered"] - before["branches_covered"],
        "same_source": before["source_sha"] == after["source_sha"],
    }


def build(data, artifact_root):
    require(data.get("schema") == "abacus.mip.wave-input.v1", "schema mismatch")
    for field in ("repository", "head_sha", "base_sha", "wave_id"):
        require(bool(data.get(field)), "missing " + field)
    sha(data["head_sha"], "head_sha")
    sha(data["base_sha"], "base_sha")
    require(data["repository"] == "GBOGEB/ABACUS", "unexpected repository")
    roots = data.get("roots", [])
    require(isinstance(roots, list) and isinstance(data.get("jobs", []), list), "roots/jobs must be arrays")
    root_ids = set()
    occurrences = Counter()
    states = Counter()
    for item in roots:
        require(isinstance(item, dict) and REQUIRED_ROOT <= item.keys(), "invalid root record")
        require(item["root_id"] not in root_ids, "duplicate root_id")
        root_ids.add(item["root_id"])
        require(item["state"] in ALLOWED, "invalid root state")
        require(bool(item["owner"] and item["fingerprint"]), "missing attribution")
        occurrences[item["fingerprint"]] += int(item.get("manifestations", 1))
        require(type(item.get("manifestations", 1)) is int and item.get("manifestations", 1) > 0, "invalid manifestations")
        states[item["state"]] += 1
    jobs = []
    hours = 0.0
    for item in data["jobs"]:
        require(isinstance(item, dict) and all(k in item for k in ("run_id", "job_id", "head_sha", "duration_seconds", "result")), "incomplete job")
        sha(item["head_sha"], "job head_sha")
        require(item["head_sha"] == data["head_sha"], "mixed-head native jobs")
        seconds = item["duration_seconds"]
        require(isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and seconds >= 0, "invalid duration")
        hours += seconds / 3600
        require(str(item["run_id"]).isdigit() and str(item["job_id"]).isdigit(), "invalid native IDs")
        jobs.append({"run_id": str(item["run_id"]), "job_id": str(item["job_id"]), "result": item["result"], "duration_seconds": seconds})
    hashes = {}
    root = Path(artifact_root).resolve()
    for label, relative in data.get("artifacts", {}).items():
        require(isinstance(relative, str) and bool(relative), "invalid artifact path")
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and path.is_file(), "artifact absent/outside root")
        raw = path.read_bytes()
        require(bool(raw), "empty artifact")
        hashes[label] = {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    metric = coverage_delta(data.get("coverage_before"), data.get("coverage_after"))
    useful = None
    if metric["disposition"] == "COMPARABLE" and hours > 0:
        useful = round((metric["new_lines"] + metric["new_branches"]) / hours, 6)
    # Closures are never inferred from branch receipts or candidate root states.
    proposed_close = [x["root_id"] for x in roots if x["state"] == "REPAIRED"]
    closure = data.get("closure", {})
    admitted = (closure.get("merge_admitted") is True and
                closure.get("main_verified") is True and
                closure.get("merge_commit_sha") == closure.get("verified_main_sha") and
                bool(closure.get("native_evidence_refs")))
    if admitted:
        sha(closure["verified_main_sha"], "verified_main_sha")
        require(closure["verified_main_sha"] != data["base_sha"], "unchanged main is not a closure")
    approved = set(closure.get("individually_verified_root_ids", [])) if admitted else set()
    require(approved <= set(proposed_close), "closed root lacks repaired status")
    closed = sorted(approved)
    backlog = {
        "schema": "abacus.mip.backlog-delta.v1", "wave_id": data["wave_id"],
        "distinct_root_count": len(roots), "states": dict(sorted(states.items())),
        "recurrence_by_fingerprint": dict(sorted(occurrences.items())),
        "candidate_repaired_root_ids": sorted(proposed_close),
        "verified_closed_root_ids": closed,
        "verified_closed_count": len(closed),
        "formal_baseline_roots": data.get("formal_baseline_roots"),
        "reopened_root_ids": sorted(x["root_id"] for x in roots if x["state"] == "REOPENED"),
        "closure_disposition": "EXACT_MAIN_PROVEN" if admitted else "HOLD_UNKNOWN",
    }
    pulse = {
        "schema": "abacus.mip.wave-pulse.v1", "repository": data["repository"],
        "base_sha": data["base_sha"], "head_sha": data["head_sha"], "wave_id": data["wave_id"],
        "jobs": jobs, "worker_hours_observed": round(hours, 6),
        "first_reds": data.get("first_reds", []), "artifact_hashes": hashes,
        "coverage": metric, "coverage_units_per_worker_hour": useful,
        "required_tests": data.get("required_tests", []), "tests": data.get("tests", []),
        "formal_root_closure_count": len(closed),
        "disposition": "MEASURED_NOT_MERGE_AUTHORIZED",
    }
    return pulse, backlog


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--artifact-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    pulse, backlog = build(json.loads(args.input.read_text()), args.artifact_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, report in (("mip_wave_pulse.json", pulse), ("mip_backlog_delta.json", backlog)):
        (args.output_dir / name).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"wave_id": pulse["wave_id"], "coverage": pulse["coverage"]["disposition"],
                      "verified_closed_roots": backlog["verified_closed_count"], "disposition": pulse["disposition"]}))


if __name__ == "__main__":
    main()
