"""Source-bound, fail-closed conversion of coverage.py JSON to matched deltas.

A manifest is a declaration, not proof of GitHub's actual runner or source.
The output is engineering telemetry, NEVER merge admission or root closure.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SNAPSHOT_SCHEMA = "cbd.measured-source-coverage.v1"


class EvidenceError(ValueError):
    """Bad or noncomparable source data."""


def read_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvidenceError("expected an object")
    return data


def positive_int(value, label):
    if type(value) is not int or value <= 0:
        raise EvidenceError(f"{label} must be a positive integer")
    return value


def valid_path(value):
    if (not isinstance(value, str) or "\\" in value or not value
            or PurePosixPath(value).is_absolute() or ".." in value.split("/")
            or value.startswith("./")):
        raise EvidenceError("module must be a stable relative repository path")
    return value


def validate_manifest(manifest):
    if manifest.get("schema") != "cbd.native-checkout-declaration.v1":
        raise EvidenceError("unknown manifest schema")
    if manifest.get("repository") != "GBOGEB/ABACUS":
        raise EvidenceError("unexpected repository")
    head = manifest.get("head_sha")
    if not isinstance(head, str) or not SHA40.fullmatch(head):
        raise EvidenceError("invalid head_sha")
    if manifest.get("checkout_sha") != head:
        raise EvidenceError("head/checkout mismatch")
    positive_int(manifest.get("run_id"), "run_id")
    positive_int(manifest.get("run_attempt"), "run_attempt")
    positive_int(manifest.get("job_id"), "job_id")
    sources = manifest.get("source_sha256")
    if not isinstance(sources, dict) or not sources:
        raise EvidenceError("missing source checksums")
    for path, sha in sources.items():
        valid_path(path)
        if not isinstance(sha, str) or not SHA256.fullmatch(sha):
            raise EvidenceError(f"invalid source checksum: {path}")
    return sources


def _coverage_counts(summary, path):
    if not isinstance(summary, dict):
        raise EvidenceError(f"missing coverage summary for {path}")
    output = {}
    for label in ("covered_lines", "num_statements", "covered_branches", "num_branches"):
        v = summary.get(label)
        if type(v) is not int or v < 0:
            raise EvidenceError(f"{path}: {label} missing or negative")
        output[label] = v
    if output["num_statements"] == 0:
        raise EvidenceError(f"{path}: zero statement denominator")
    if output["covered_lines"] > output["num_statements"] or output["covered_branches"] > output["num_branches"]:
        raise EvidenceError(f"{path}: numerator exceeds denominator")
    return output


def make_snapshot(coverage, manifest, modules):
    sources = validate_manifest(manifest)
    if not isinstance(coverage.get("files"), dict):
        raise EvidenceError("missing coverage.py files map")
    if not modules or len(modules) != len(set(modules)):
        raise EvidenceError("modules required and must be unique")
    rows = {}
    for path in sorted(modules):
        valid_path(path)
        if path not in sources or path not in coverage["files"]:
            raise EvidenceError(f"coverage or checksum missing for {path}")
        counts = _coverage_counts(coverage["files"][path].get("summary"), path)
        rows[path] = {"sha256": sources[path], **counts}
    return {
        "schema": SNAPSHOT_SCHEMA,
        "repository": manifest["repository"],
        "head_sha": manifest["head_sha"],
        "checkout_sha": manifest["checkout_sha"],
        "run_id": manifest["run_id"],
        "run_attempt": manifest["run_attempt"],
        "job_id": manifest["job_id"],
        "scope": "EXPLICIT_MATCHED_MODULES_ONLY",
        "authority": "DECLARED_INPUT_NOT_NATIVE_AUTHENTICATION",
        "modules": rows,
        "merge_admission": "HOLD",
        "formal_root_closure": 0,
    }


def _validate_snapshot(data):
    if data.get("schema") != SNAPSHOT_SCHEMA or data.get("scope") != "EXPLICIT_MATCHED_MODULES_ONLY":
        raise EvidenceError("incompatible snapshot schema/scope")
    modules = data.get("modules")
    if not isinstance(modules, dict) or not modules:
        raise EvidenceError("modules must be a non-empty mapping")
    if any(not isinstance(row, dict) for row in modules.values()):
        raise EvidenceError("invalid module row")
    manifest = {k: data.get(k) for k in ("repository", "head_sha", "checkout_sha", "run_id", "run_attempt", "job_id")}
    manifest["schema"] = "cbd.native-checkout-declaration.v1"
    manifest["source_sha256"] = {p: v.get("sha256") for p, v in modules.items()}
    validate_manifest(manifest)
    if data.get("authority") != "DECLARED_INPUT_NOT_NATIVE_AUTHENTICATION" or data.get("merge_admission") != "HOLD" or data.get("formal_root_closure") != 0:
        raise EvidenceError("admission/authority invariant violated")
    for p, v in data["modules"].items():
        _coverage_counts(v, p)
    return data["modules"]


def pct(numerator, denominator):
    return round(100 * numerator / denominator, 6) if denominator else None


def compare(before, after):
    a = _validate_snapshot(before)
    b = _validate_snapshot(after)
    if before["repository"] != after["repository"] or set(a) != set(b):
        raise EvidenceError("source-scope mismatch")
    out = {}
    regression = False
    improved = False
    for path in sorted(a):
        old, new = a[path], b[path]
        if old["sha256"] != new["sha256"]:
            raise EvidenceError(f"source changed; unmatched module: {path}")
        row = {"source_sha256": old["sha256"]}
        for kind, nkey, dkey in (("statement", "covered_lines", "num_statements"), ("branch", "covered_branches", "num_branches")):
            if old[dkey] != new[dkey]:
                raise EvidenceError(f"denominator drift in {path}: {kind}")
            old_pct, new_pct = pct(old[nkey], old[dkey]), pct(new[nkey], new[dkey])
            delta = (round(new_pct - old_pct, 6) if old_pct is not None else None)
            if delta is not None:
                regression |= new[nkey] < old[nkey]
                improved |= new[nkey] > old[nkey]
            row[kind] = {"before": [old[nkey], old[dkey]], "after": [new[nkey], new[dkey]],
                         "before_percent": old_pct, "after_percent": new_pct,
                         "delta_percentage_points": delta,
                         "delta_covered_items": new[nkey] - old[nkey],
                         "denominator_status": "MEASURED" if old[dkey] else "NOT_APPLICABLE"}
        out[path] = row
    if (before["run_id"] == after["run_id"]
            and after["run_attempt"] < before["run_attempt"]):
        raise EvidenceError("attempt rollback for identical native run")
    same_declared_attempt = (
        before["run_id"] == after["run_id"]
        and before["run_attempt"] == after["run_attempt"]
    )
    if same_declared_attempt and any(
        a[path][key] != b[path][key]
        for path in a for key in ("covered_lines", "covered_branches")
    ):
        raise EvidenceError(
            "same run/attempt cannot establish a temporal coverage delta"
        )
    state = "REGRESSION" if regression else ("IMPROVED" if improved else "UNCHANGED")
    return {"schema": "cbd.matched-coverage-delta.v1", "repository": before["repository"],
            "before_head": before["head_sha"], "after_head": after["head_sha"],
            "before_run": [before["run_id"], before["run_attempt"], before["job_id"]],
            "after_run": [after["run_id"], after["run_attempt"], after["job_id"]],
            "status": state, "modules": out, "merge_admission": "HOLD",
            "formal_root_closure": 0, "security_waiver": False,
            "declared_run_attempt_relation": (
                "SAME_DECLARED_RUN_ATTEMPT" if same_declared_attempt
                else "DISTINCT_DECLARED_RUN_ATTEMPTS_NOT_AUTHENTICATED"
            ), "accepted_matched_main_delta": None,
            "authority": "DECLARED_INPUT_NOT_NATIVE_AUTHENTICATION"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("snapshot", help="convert coverage.py JSON and exact-checkout declaration")
    p.add_argument("--coverage", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--module", action="append", required=True)
    p.add_argument("--out", required=True)
    q = sub.add_parser("compare", help="compare identical source hashes and denominators")
    q.add_argument("--before", required=True)
    q.add_argument("--after", required=True)
    q.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = make_snapshot(read_json(args.coverage), read_json(args.manifest), args.module)
        else:
            result = compare(read_json(args.before), read_json(args.after))
    except (EvidenceError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        parser.exit(2, f"HOLD: invalid or unmatched evidence: {exc}\n")
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.get("status", "SNAPSHOT_ONLY"),
                      "output": args.out, "merge_admission": "HOLD"}, sort_keys=True))
    return 1 if result.get("status") == "REGRESSION" else 0


if __name__ == "__main__":
    raise SystemExit(main())
