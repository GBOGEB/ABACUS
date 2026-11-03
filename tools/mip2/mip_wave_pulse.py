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
    return (
        isinstance(value, str)
        and len(value) == SHA_LEN
        and all(c in "0123456789abcdef" for c in value)
    )


def valid_digest(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def canonical_coverage_record(
    report, source_sha, scope, config_id, selected_paths=None
):
    """Derive a cohort fingerprint from actual Coverage.py eligible IDs."""
    require(valid_sha(source_sha), "coverage source SHA invalid")
    require(isinstance(report, dict), "canonical coverage report absent")
    require(
        report.get("meta", {}).get("branch_coverage") is True,
        "branch coverage required",
    )
    files = report.get("files")
    require(isinstance(files, dict) and bool(files), "canonical files absent")
    paths = sorted(files) if selected_paths is None else sorted(selected_paths)
    require(bool(paths) and len(set(paths)) == len(paths), "invalid selected paths")
    require(all(path in files for path in paths), "selected path missing")
    require(isinstance(scope, str) and bool(scope), "scope missing")
    require(isinstance(config_id, str) and bool(config_id), "config missing")
    manifest = []
    totals = dict.fromkeys(
        ("covered_lines", "total_lines", "covered_branches", "total_branches"), 0
    )
    for path in paths:
        item = files[path]
        summary = item.get("summary")
        require(isinstance(summary, dict), "file coverage summary missing")
        used = item.get("executed_lines")
        missing = item.get("missing_lines")
        used_arcs = item.get("executed_branches")
        missing_arcs = item.get("missing_branches")
        require(
            all(
                isinstance(values, list)
                for values in (used, missing, used_arcs, missing_arcs)
            ),
            "invalid line or branch identities",
        )

        def arc(value):
            require(
                isinstance(value, list)
                and len(value) == 2
                and all(type(n) is int for n in value),
                "invalid branch identity",
            )
            return tuple(value)

        arcs_used = [arc(value) for value in used_arcs]
        arcs_missing = [arc(value) for value in missing_arcs]
        require(all(type(n) is int for n in used + missing), "invalid line identity")
        require(
            len(set(used + missing)) == len(used) + len(missing),
            "overlapping or duplicate line identities",
        )
        require(
            len(set(arcs_used + arcs_missing)) == len(arcs_used) + len(arcs_missing),
            "overlapping or duplicate branch identities",
        )
        counts = {
            "covered_lines": len(used),
            "total_lines": len(used) + len(missing),
            "covered_branches": len(arcs_used),
            "total_branches": len(arcs_used) + len(arcs_missing),
        }
        for source, target in (
            ("covered_lines", "covered_lines"),
            ("total_lines", "num_statements"),
            ("covered_branches", "covered_branches"),
            ("total_branches", "num_branches"),
        ):
            require(
                summary.get(target) == counts[source],
                "file summary and eligible IDs disagree",
            )
            totals[source] += counts[source]
        manifest.append(
            [
                path,
                sorted(used + missing),
                sorted([list(a) for a in arcs_used + arcs_missing]),
            ]
        )
    material = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "scope": scope,
        "config_id": config_id,
        "source_sha": source_sha,
        "scope_manifest_sha256": hashlib.sha256(material).hexdigest(),
        **totals,
    }


def coverage_delta(before, after):
    if before is None or after is None:
        return {"status": "UNKNOWN", "reason": "missing comparable evidence"}
    required = (
        "scope",
        "config_id",
        "source_sha",
        "scope_manifest_sha256",
        "covered_lines",
        "total_lines",
        "covered_branches",
        "total_branches",
    )
    for record in (before, after):
        require(all(k in record for k in required), "incomplete coverage evidence")
        require(valid_sha(record["source_sha"]), "coverage SHA invalid")
        require(
            valid_digest(record["scope_manifest_sha256"]),
            "missing or invalid eligibility scope fingerprint",
        )
        for key in required[4:]:
            require(
                type(record[key]) is int and record[key] >= 0, "invalid coverage count"
            )
        require(
            record["covered_lines"] <= record["total_lines"]
            and record["covered_branches"] <= record["total_branches"],
            "coverage exceeds denominator",
        )
    if any(
        before[k] != after[k]
        for k in (
            "scope",
            "config_id",
            "scope_manifest_sha256",
            "total_lines",
            "total_branches",
        )
    ):
        return {"status": "INCOMPARABLE", "reason": "scope/config/denominator mismatch"}
    denominator = after["total_lines"] + after["total_branches"]
    require(denominator > 0, "zero coverage denominator")
    added_lines = after["covered_lines"] - before["covered_lines"]
    added_branches = after["covered_branches"] - before["covered_branches"]
    return {
        "status": "COMPARABLE",
        "before_sha": before["source_sha"],
        "after_sha": after["source_sha"],
        "scope": after["scope"],
        "config_id": after["config_id"],
        "scope_manifest_sha256": after["scope_manifest_sha256"],
        "before_covered": before["covered_lines"] + before["covered_branches"],
        "after_covered": after["covered_lines"] + after["covered_branches"],
        "eligible": denominator,
        "delta_lines": added_lines,
        "delta_branches": added_branches,
        "before_percent": round(
            100 * (before["covered_lines"] + before["covered_branches"]) / denominator,
            8,
        ),
        "after_percent": round(
            100 * (after["covered_lines"] + after["covered_branches"]) / denominator, 8
        ),
        "delta_pp": round(100 * (added_lines + added_branches) / denominator, 8),
    }


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
        require(
            isinstance(rid, str) and bool(rid) and rid not in seen,
            "missing/duplicate root ID",
        )
        seen.add(rid)
        state = root.get("status")
        require(state in statuses, "invalid root status")
        require(bool(root.get("owner")), "missing root owner")
        fps = root.get("fingerprints", [])
        require(
            isinstance(fps, list) and all(isinstance(x, str) and x for x in fps),
            "invalid fingerprints",
        )
        occurrences += len(fps)
        if state == "ROOT_CLOSED":
            proof = root.get("closure_proof", {})
            require(
                data.get("admission", {}).get("merge_admitted") is True,
                "root closure requires merge admission",
            )
            require(valid_sha(proof.get("main_sha")), "exact-main SHA required")
            require(
                proof["main_sha"] == data.get("admission", {}).get("verified_main_sha"),
                "root closure SHA not bound to verified main",
            )
            require(
                bool(proof.get("native_run_url"))
                and bool(proof.get("artifact_sha256")),
                "native closure evidence absent",
            )
        counts[state.lower()] += 1
    workers = data.get("workers", [])
    require(isinstance(workers, list), "invalid workers")
    worker_keys = set()
    for worker in workers:
        require(isinstance(worker, dict), "worker must be an object")
        require(worker.get("root_id") in seen, "worker root not registered")
        require(
            type(worker.get("job_id")) is int
            and worker["job_id"] > 0
            and type(worker.get("run_id")) is int
            and worker["run_id"] > 0,
            "worker requires positive native run/job IDs",
        )
        key = (worker["root_id"], worker["run_id"], worker["job_id"])
        require(key not in worker_keys, "duplicate worker receipt")
        worker_keys.add(key)
        if "source_sha" in worker:
            require(
                worker["source_sha"] == data["head_sha"],
                "worker SHA not bound to current head",
            )
    before = data.get("coverage", {}).get("before")
    after = data.get("coverage", {}).get("after")
    if before is not None:
        require(
            isinstance(before, dict) and before.get("source_sha") == data["base_sha"],
            "coverage baseline SHA does not match wave base",
        )
    if after is not None:
        require(
            isinstance(after, dict) and after.get("source_sha") == data["head_sha"],
            "coverage candidate SHA does not match wave head",
        )
    measured = coverage_delta(before, after)
    hours = data.get("worker_hours")
    yield_metric = {"status": "UNKNOWN"}
    if measured["status"] == "COMPARABLE" and type(hours) in (int, float) and hours > 0:
        yield_metric = {
            "status": "MEASURED",
            "new_lines_per_hour": round(measured["delta_lines"] / hours, 6),
            "new_branches_per_hour": round(measured["delta_branches"] / hours, 6),
        }
    tests = data.get("tests", {})
    require(isinstance(tests, dict), "tests must be object")
    for key in ("passed", "failed", "skipped"):
        require(type(tests.get(key)) is int and tests[key] >= 0, "invalid test count")
    findings = data.get("first_reds", [])
    require(isinstance(findings, list), "first_reds not a list")
    root_fingerprints = {
        root["root_id"]: set(root.get("fingerprints", [])) for root in roots
    }
    for item in findings:
        require(isinstance(item, dict), "first-red must be an object")
        rid = item.get("root_id")
        require(
            rid in seen
            and item.get("fingerprint")
            and item["fingerprint"] in root_fingerprints[rid]
            and item.get("classification") in ("new", "inherited", "repaired"),
            "unattributed first-red",
        )
    backlog = {
        "schema": "abacus.mip.backlog-delta.v1",
        "repository": data["repository"],
        "head_sha": data["head_sha"],
        "wave_id": data["wave_id"],
        "distinct_root_counts": counts,
        "fingerprint_manifestations": occurrences,
        "declared_root_closures": counts["root_closed"],
        "formal_verified_closures": 0,
        "closure_disposition": (
            "UNVERIFIED_DECLARED_CLOSURE"
            if counts["root_closed"]
            else "NO_CLOSURE_CREDIT"
        ),
        "closure_authority": "UNAUTHENTICATED_INPUT_NEVER_COUNTS_AS_NATIVE_PROOF",
    }
    report = {
        "schema": SCHEMA,
        "repository": data["repository"],
        "base_sha": data["base_sha"],
        "head_sha": data["head_sha"],
        "wave_id": data["wave_id"],
        "coverage": measured,
        "coverage_yield": yield_metric,
        "tests": tests,
        "worker_count": len(workers),
        "first_reds": findings,
        "root_counts": counts,
        "merge_admitted": False,
        "declared_merge_admitted": data.get("admission", {}).get("merge_admitted")
        is True,
        "worker_receipt_trust": "INPUT_DECLARED_NOT_NATIVE",
        "tests_receipt_trust": "INPUT_DECLARED_NOT_JUNIT",
        "coverage_causal_proof": "UNKNOWN_NO_STABLE_OBLIGATION_MAP",
        "disposition": "P0_HOLD",
    }
    return report, backlog


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


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
    print(
        json.dumps(
            {
                "result": report["disposition"],
                "roots": backlog["distinct_root_counts"],
                "coverage_status": report["coverage"]["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
