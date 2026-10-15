"""Fail-closed MIP wave comparison. No merge or root-closure authority."""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "abacus.mip.wave-pulse.v1"
SHA_LEN = 40


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_sha(value):
    return isinstance(value, str) and len(value) == SHA_LEN and all(c in "0123456789abcdef" for c in value)


def valid_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def coverage_delta(before, after):
    if before is None or after is None:
        return {"status": "UNKNOWN", "reason": "missing comparable evidence"}
    required = ("scope", "config_id", "source_sha", "scope_manifest_sha256",
                "covered_lines", "total_lines", "covered_branches", "total_branches")
    for record in (before, after):
        require(all(k in record for k in required), "incomplete coverage evidence")
        require(valid_sha(record["source_sha"]), "coverage SHA invalid")
        require(valid_digest(record["scope_manifest_sha256"]),
                "missing or invalid eligibility scope fingerprint")
        for key in required[4:]:
            require(type(record[key]) is int and record[key] >= 0, "invalid coverage count")
        require(record["covered_lines"] <= record["total_lines"] and
                record["covered_branches"] <= record["total_branches"], "coverage exceeds denominator")
    if any(before[k] != after[k] for k in ("scope", "config_id", "scope_manifest_sha256",
                                                 "total_lines", "total_branches")):
        return {"status": "INCOMPARABLE", "reason": "scope/config/denominator mismatch"}
    denominator = after["total_lines"] + after["total_branches"]
    require(denominator > 0, "zero coverage denominator")
    added_lines = after["covered_lines"] - before["covered_lines"]
    added_branches = after["covered_branches"] - before["covered_branches"]
    return {"status": "COMPARABLE", "before_sha": before["source_sha"],
            "after_sha": after["source_sha"], "scope": after["scope"],
            "config_id": after["config_id"],
            "scope_manifest_sha256": after["scope_manifest_sha256"],
            "before_covered": before["covered_lines"] + before["covered_branches"],
            "after_covered": after["covered_lines"] + after["covered_branches"],
            "eligible": denominator, "delta_lines": added_lines,
            "delta_branches": added_branches,
            "before_percent": round(100 * (before["covered_lines"] + before["covered_branches"]) / denominator, 8),
            "after_percent": round(100 * (after["covered_lines"] + after["covered_branches"]) / denominator, 8),
            "delta_pp": round(100 * (added_lines + added_branches) / denominator, 8)}


def pulse(data):
    require(data.get("schema") == SCHEMA, "unsupported schema")
    for key in ("repository", "base_sha", "head_sha", "wave_id"):
        require(bool(data.get(key)), "missing " + key)
    for key in ("base_sha", "head_sha"):
        require(valid_sha(data[key]), "invalid " + key)
    require(data["repository"] == "GBOGEB/ABACUS", "unexpected repository")
    roots = data.get("roots")
    require(isinstance(roots, list), "missing root census")
    seen = set()
    statuses = {"OPEN", "REPAIRED", "VERIFIED", "REOPENED", "DEFERRED", "ROOT_CLOSED"}
    counts = {key.lower(): 0 for key in statuses}
    occurrences = 0
    for root in roots:
        rid = root.get("root_id")
        require(isinstance(rid, str) and bool(rid) and rid not in seen, "missing/duplicate root ID")
        seen.add(rid)
        state = root.get("status")
        require(state in statuses, "invalid root status")
        require(bool(root.get("owner")), "missing root owner")
        fps = root.get("fingerprints", [])
        require(isinstance(fps, list) and all(isinstance(x, str) and x for x in fps), "invalid fingerprints")
        occurrences += len(fps)
        if state == "ROOT_CLOSED":
            proof = root.get("closure_proof", {})
            require(data.get("admission", {}).get("merge_admitted") is True, "root closure requires merge admission")
            require(valid_sha(proof.get("main_sha")), "exact-main SHA required")
            require(proof["main_sha"] == data.get("admission", {}).get("verified_main_sha"),
                    "root closure SHA not bound to verified main")
            require(bool(proof.get("native_run_url")) and bool(proof.get("artifact_sha256")),
                    "native closure evidence absent")
        counts[state.lower()] += 1
    workers = data.get("workers", [])
    require(isinstance(workers, list), "invalid workers")
    for worker in workers:
        require(worker.get("root_id") in seen and worker.get("job_id") and worker.get("run_id"),
                "worker must bind to root and native run/job")
    before = data.get("coverage", {}).get("before")
    after = data.get("coverage", {}).get("after")
    if before is not None:
        require(isinstance(before, dict) and before.get("source_sha") == data["base_sha"],
                "coverage baseline SHA does not match wave base")
    if after is not None:
        require(isinstance(after, dict) and after.get("source_sha") == data["head_sha"],
                "coverage candidate SHA does not match wave head")
    measured = coverage_delta(before, after)
    hours = data.get("worker_hours")
    yield_metric = {"status": "UNKNOWN"}
    if measured["status"] == "COMPARABLE" and type(hours) in (int, float) and hours > 0:
        yield_metric = {"status": "MEASURED", "new_lines_per_hour": round(measured["delta_lines"] / hours, 6),
                        "new_branches_per_hour": round(measured["delta_branches"] / hours, 6)}
    tests = data.get("tests", {})
    require(isinstance(tests, dict), "tests must be object")
    for key in ("passed", "failed", "skipped"):
        require(type(tests.get(key)) is int and tests[key] >= 0, "invalid test count")
    findings = data.get("first_reds", [])
    require(isinstance(findings, list), "first_reds not a list")
    for item in findings:
        require(item.get("root_id") in seen and item.get("fingerprint") and
                item.get("classification") in ("new", "inherited", "repaired"),
                "unattributed first-red")
    backlog = {"schema": "abacus.mip.backlog-delta.v1",
               "repository": data["repository"], "head_sha": data["head_sha"],
               "wave_id": data["wave_id"], "distinct_root_counts": counts,
               "fingerprint_manifestations": occurrences,
               "formal_verified_closures": counts["root_closed"],
               "closure_disposition": "EXACT_MAIN_PROVEN" if counts["root_closed"] else "NO_CLOSURE_CREDIT"}
    report = {"schema": SCHEMA, "repository": data["repository"], "base_sha": data["base_sha"],
              "head_sha": data["head_sha"], "wave_id": data["wave_id"],
              "coverage": measured, "coverage_yield": yield_metric, "tests": tests,
              "worker_count": len(workers), "first_reds": findings,
              "root_counts": counts, "merge_admitted": data.get("admission", {}).get("merge_admitted") is True,
              "disposition": "P0_HOLD" if not data.get("admission", {}).get("merge_admitted") else "POST_ADMISSION_RECHECK"}
    return report, backlog


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    source = Path(args.input).read_bytes()
    report, backlog = pulse(json.loads(source))
    report["input_sha256"] = hashlib.sha256(source).hexdigest()
    folder = Path(args.output_dir)
    write_json(folder / "mip_wave_pulse.json", report)
    write_json(folder / "mip_backlog_delta.json", backlog)
    print(json.dumps({"result": report["disposition"], "roots": backlog["distinct_root_counts"],
                      "coverage_status": report["coverage"]["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
