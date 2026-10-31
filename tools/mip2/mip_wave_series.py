"""Read-only chronological MIP wave rollup; never confers admission authority.

Consumes the canonical #1990 producer's *actual input bytes*, pulse and
backlog JSON. All outcomes remain source-reported until independently
authenticated against GitHub's native run/job/artifact bytes.
"""

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "abacus.mip.wave-series.v1"
PULSE_SCHEMA = "abacus.mip.wave-pulse.v1"
BACKLOG_SCHEMA = "abacus.mip.backlog-delta.v1"
STATES = ("OPEN", "REPAIRED", "VERIFIED", "REOPENED", "DEFERRED", "ROOT_CLOSED")
LIMIT = 2_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def is_sha(value, length=40):
    return (
        isinstance(value, str)
        and len(value) == length
        and all(c in "0123456789abcdef" for c in value)
    )


def read_json(path):
    require(path.is_file() and not path.is_symlink(), "missing or linked input: " + str(path))
    require(0 < path.stat().st_size <= LIMIT, "invalid input size: " + str(path))
    raw = path.read_bytes()
    obj = json.loads(raw)
    require(isinstance(obj, dict), "object required: " + str(path))
    return obj, raw


def checked_coverage(source, published, base, head):
    require(isinstance(published, dict), "missing coverage result")
    before = source.get("coverage", {}).get("before")
    after = source.get("coverage", {}).get("after")
    status = published.get("status")
    if before is None or after is None:
        require(status == "UNKNOWN", "missing coverage cannot be measured")
        return {"status": "UNKNOWN", "delta_pp": None}
    require(isinstance(before, dict) and isinstance(after, dict), "invalid coverage evidence")
    keys = ("scope", "config_id", "source_sha", "covered_lines", "total_lines",
            "covered_branches", "total_branches")
    for item in (before, after):
        require(all(k in item for k in keys), "incomplete coverage record")
        require(is_sha(item["source_sha"]), "bad coverage SHA")
        for k in keys[3:]:
            require(type(item[k]) is int and item[k] >= 0, "invalid coverage integer")
        require(item["covered_lines"] <= item["total_lines"], "covered lines exceed total")
        require(item["covered_branches"] <= item["total_branches"], "covered branches exceed total")
    require(before["source_sha"] == base and after["source_sha"] == head,
            "coverage not bound to wave base/head")
    comparable = all(
        before[k] == after[k]
        for k in ("scope", "config_id", "total_lines", "total_branches")
    )
    if not comparable:
        require(status == "INCOMPARABLE", "incomparable source claimed improvement")
        return {"status": "INCOMPARABLE", "delta_pp": None}
    total = after["total_lines"] + after["total_branches"]
    require(total > 0, "zero eligible coverage denominator")
    added_lines = after["covered_lines"] - before["covered_lines"]
    added_branches = after["covered_branches"] - before["covered_branches"]
    delta = round(100 * (added_lines + added_branches) / total, 8)
    require(status == "COMPARABLE", "comparable coverage misclassified")
    require(published.get("scope") == after["scope"], "coverage scope mismatch")
    require(published.get("config_id") == after["config_id"], "coverage config mismatch")
    require(published.get("before_sha") == base and published.get("after_sha") == head,
            "published coverage SHA mismatch")
    require(published.get("delta_lines") == added_lines, "line delta mismatch")
    require(published.get("delta_branches") == added_branches, "branch delta mismatch")
    require(published.get("delta_pp") == delta, "coverage delta mismatch")
    return {
        "status": "COMPARABLE", "delta_pp": delta,
        "delta_lines": added_lines, "delta_branches": added_branches,
        "scope": after["scope"], "config_id": after["config_id"],
        "eligible_lines": total if after["total_branches"] == 0 else after["total_lines"],
        "eligible_branches": after["total_branches"],
    }


def load_wave(folder):
    folder = Path(folder)
    source, raw = read_json(folder / "wave-input.json")
    pulse, _ = read_json(folder / "mip_wave_pulse.json")
    backlog, _ = read_json(folder / "mip_backlog_delta.json")
    require(source.get("schema") == PULSE_SCHEMA, "wrong source schema")
    require(pulse.get("schema") == PULSE_SCHEMA, "wrong pulse schema")
    require(backlog.get("schema") == BACKLOG_SCHEMA, "wrong backlog schema")
    for key in ("repository", "head_sha", "wave_id"):
        require(source.get(key) == pulse.get(key) == backlog.get(key),
                "wave input/outputs disagree: " + key)
    require(source.get("base_sha") == pulse.get("base_sha"), "base mismatch")
    base, head = source["base_sha"], source["head_sha"]
    require(is_sha(base) and is_sha(head), "invalid wave SHA")
    require(source.get("repository") == "GBOGEB/ABACUS", "unsupported native producer")
    require(pulse.get("input_sha256") == hashlib.sha256(raw).hexdigest(),
            "producer input bytes do not match receipt")
    roots = source.get("roots")
    require(isinstance(roots, list), "missing roots")
    mapping = {}
    counts = {s.lower(): 0 for s in STATES}
    manifestations = 0
    fingerprints = set()
    for item in roots:
        require(isinstance(item, dict), "invalid root record")
        rid = item.get("root_id")
        state = item.get("status")
        require(isinstance(rid, str) and rid and rid not in mapping,
                "duplicate/missing root id")
        require(state in STATES and bool(item.get("owner")), "bad root status or owner")
        fps = item.get("fingerprints", [])
        require(isinstance(fps, list) and all(isinstance(x, str) and x for x in fps),
                "bad fingerprint list")
        if state == "ROOT_CLOSED":
            admission = source.get("admission", {})
            proof = item.get("closure_proof", {})
            require(isinstance(admission, dict) and admission.get("merge_admitted") is True,
                    "root closure requires source-admitted state")
            require(isinstance(proof, dict) and is_sha(proof.get("main_sha")),
                    "root closure requires exact-main SHA")
            require(proof["main_sha"] == admission.get("verified_main_sha"),
                    "root closure main SHA disagrees with source admission")
            require(bool(proof.get("native_run_url"))
                    and is_sha(proof.get("artifact_sha256"), 64),
                    "root closure needs native run and 64-hex digest")
        mapping[rid] = state
        counts[state.lower()] += 1
        manifestations += len(fps)
        fingerprints.update((rid, fp) for fp in fps)
    expected = backlog.get("distinct_root_counts")
    require(expected == counts == pulse.get("root_counts"), "root census mismatch")
    require(backlog.get("fingerprint_manifestations") == manifestations,
            "manifestation total mismatch")
    require(backlog.get("formal_verified_closures") == counts["root_closed"],
            "closure count mismatch")
    require(counts["root_closed"] == 0 or pulse.get("merge_admitted") is True,
            "closure claimed without source admission")
    tests = source.get("tests")
    require(isinstance(tests, dict) and pulse.get("tests") == tests,
            "source-reported tests mismatch")
    for key in ("passed", "failed", "skipped"):
        require(type(tests.get(key)) is int and tests[key] >= 0, "invalid test count")
    first_reds = source.get("first_reds", [])
    require(isinstance(first_reds, list) and pulse.get("first_reds") == first_reds,
            "first-red receipts mismatch")
    for item in first_reds:
        require(item.get("root_id") in mapping and bool(item.get("fingerprint")),
                "unowned first red")
        require(item.get("classification") in ("new", "inherited", "repaired"),
                "invalid first-red classification")
    workers = source.get("workers", [])
    require(isinstance(workers, list) and pulse.get("worker_count") == len(workers),
            "worker total mismatch")
    cov = checked_coverage(source, pulse.get("coverage"), base, head)
    return {
        "wave_id": source["wave_id"], "repository": source["repository"],
        "base_sha": base, "head_sha": head, "root_states": mapping,
        "root_counts": counts, "fingerprints": fingerprints,
        "manifestations": manifestations, "first_reds": first_reds,
        "coverage": cov, "tests": tests, "worker_records": len(workers),
        "source_input_sha256": pulse["input_sha256"],
        "source_reported_closures": counts["root_closed"],
    }


def rollup(folders, classification):
    require(classification in ("SYNTHETIC", "OPERATIONAL_UNVERIFIED"),
            "classification required")
    require(isinstance(folders, list) and bool(folders), "no waves")
    require(len(folders) <= 100, "too many waves")
    snapshots = [load_wave(f) for f in folders]
    seen_wave_ids = set()
    history = []
    previous = None
    seen_signatures = set()
    for wave in snapshots:
        require(wave["wave_id"] not in seen_wave_ids, "duplicate wave ID")
        seen_wave_ids.add(wave["wave_id"])
        if previous is not None:
            require(wave["repository"] == previous["repository"],
                    "cross-repository denominator pooling forbidden")
            require(wave["base_sha"] == previous["head_sha"],
                    "non-contiguous exact-SHA series")
        old = previous["root_states"] if previous else {}
        new = wave["root_states"]
        discovered = sorted(set(new) - set(old)) if previous else sorted(new)
        vanished = sorted(set(old) - set(new)) if previous else []
        reopened = sorted(
            rid for rid in new.keys() & old.keys()
            if old[rid] == "ROOT_CLOSED" and new[rid] != "ROOT_CLOSED"
        )
        closed = sorted(
            rid for rid in new.keys() & old.keys()
            if old[rid] != "ROOT_CLOSED" and new[rid] == "ROOT_CLOSED"
        )
        fresh = wave["fingerprints"] - seen_signatures
        repeat = wave["fingerprints"] & seen_signatures
        seen_signatures.update(wave["fingerprints"])
        cov = wave["coverage"]
        history.append({
            "wave_id": wave["wave_id"], "base_sha": wave["base_sha"],
            "head_sha": wave["head_sha"],
            "root_counts": wave["root_counts"],
            "root_ids_added": discovered if previous else [],
            "root_ids_disappeared_without_closure_credit": vanished,
            "source_claimed_closure_transitions": closed,
            "reopened_after_claimed_closure": reopened,
            "fingerprint_manifestations": wave["manifestations"],
            "distinct_root_fingerprints": len(wave["fingerprints"]),
            "first_seen_fingerprint_pairs": len(fresh),
            "repeated_fingerprint_pairs": len(repeat),
            "first_red_classifications": {
                key: sum(x["classification"] == key for x in wave["first_reds"])
                for key in ("new", "inherited", "repaired")
            },
            "coverage": cov, "tests_source_reported": wave["tests"],
            "worker_records_source_reported": wave["worker_records"],
            "native_receipt_verified": None,
            "security_matched_delta": None,
            "coverage_gain_credited": 0,
            "formal_root_closure_delta_credited": 0,
            "source_input_sha256": wave["source_input_sha256"],
        })
        previous = wave
    return {
        "schema": SCHEMA, "repository": snapshots[0]["repository"],
        "classification": classification, "wave_count": len(history),
        "quality": "SYNTHETIC_ONLY" if classification == "SYNTHETIC"
        else "SOURCE_BOUND_NOT_INDEPENDENTLY_ATTESTED",
        "waves": history,
        "cumulative": {
            "unique_seen_root_ids": len(set().union(*(set(w["root_states"]) for w in snapshots))),
            "unique_seen_root_fingerprint_pairs": len(seen_signatures),
            "admissible_coverage_gain_pp": None,
            "native_authenticated_receipts": None,
            "verified_root_closure": None,
            "process_stability_m2": "HOLD",
            "process_capability_m3": "HOLD",
            "bradley_terry": "NOT_ASSESSABLE",
            "pca": "NOT_ASSESSABLE",
            "cross_repository_coverage": "NOT_AGGREGATED",
            "merge_admission": "HOLD",
        },
    }


def as_markdown(report):
    lines = [
        "# MIP wave-series report — " + report["classification"],
        "",
        "All wave figures are source-reported. ZERO formal closure or"
        " coverage credit is granted by this reader.",
        "",
        "| Wave | Root census | Fingerprint pairs (new/repeat) |"
        " First-reds (new/inherited/repaired) | Coverage change | Authenticated |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for w in report["waves"]:
        reds = w["first_red_classifications"]
        cov = w["coverage"]
        cv = (str(cov["delta_pp"]) + " pp") if cov["status"] == "COMPARABLE" else cov["status"]
        lines.append(
            "| " + w["wave_id"] + " | " + str(sum(w["root_counts"].values()))
            + " | " + str(w["first_seen_fingerprint_pairs"]) + "/"
            + str(w["repeated_fingerprint_pairs"]) + " | "
            + "/".join(str(reds[s]) for s in ("new", "inherited", "repaired"))
            + " | " + cv + " | UNKNOWN |"
        )
    lines.extend([
        "",
        "M2 stability: HOLD. M3 capability: HOLD. PCA and Bradley–Terry:"
        " NOT_ASSESSABLE until independent, matched observations.",
        "Cross-repository percentages cannot be combined. Every new repository"
        " needs its own canonical producer and native receipts.",
        "No admission, security waiver or authority transfer.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave-dir", action="append", required=True)
    parser.add_argument("--classification", required=True,
                        choices=("SYNTHETIC", "OPERATIONAL_UNVERIFIED"))
    parser.add_argument("--output-dir", required=True)
    opts = parser.parse_args()
    report = rollup(opts.wave_dir, opts.classification)
    target = Path(opts.output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "mip_wave_series.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (target / "mip_wave_series.md").write_text(as_markdown(report), encoding="utf-8")
    print(json.dumps({
        "waves": report["wave_count"], "classification": report["classification"],
        "merge_admission": "HOLD", "native_verified": None,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
