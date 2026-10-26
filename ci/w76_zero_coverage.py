#!/usr/bin/env python3
"""W76 source-bound zero-covered-asset reduction receipt.

This is a local, READ-ONLY measurement producer, not a merge/admission gate.
Baseline provenance is pinned to GitHub run/artifact and per-file git blobs.
An unknown file is not zero-covered, and a changed denominator is never uplift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "codepurple.zero-asset.pulse.v1"
BASELINE = "codepurple.zero-asset.baseline.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\Z")
RAN = re.compile(r"(?m)^Ran ([0-9]+) tests in [0-9.]+s\s*$")
OK = re.compile(r"(?m)^OK(?: \(skipped=([0-9]+)\))?\s*$")


def ensure_count(n, label):
    if type(n) is not int or n < 0:
        raise ValueError("invalid count: " + label)
    return n


def verify_path(name):
    if (not isinstance(name, str) or not NAME.fullmatch(name)
            or any(segment in (".", "..", ".git") for segment in name.split("/"))):
        raise ValueError("unsafe or noncanonical production path")
    return name


def parse_terminal(log_bytes):
    if not isinstance(log_bytes, bytes):
        raise ValueError("unittest log must be bytes")
    text = log_bytes.decode("utf-8")
    runs = RAN.findall(text)
    oks = OK.findall(text)
    if len(runs) != 1 or len(oks) != 1:
        raise ValueError("absent or ambiguous passing unittest terminal result")
    executed = int(runs[0])
    skipped = int(oks[0]) if oks[0] else 0
    if executed <= 0 or skipped >= executed:
        raise ValueError("no positive passing tests")
    return {"executed": executed, "passed": executed-skipped,
            "failed": 0, "skipped": skipped}


def measure(baseline, coverage, source_sha, get_blob, test_counts):
    if not isinstance(baseline, dict) or baseline.get("schema") != BASELINE:
        raise ValueError("invalid baseline identity")
    if (baseline.get("source_repository") != "GBOGEB/ABACUS"
            or not isinstance(source_sha, str) or not SHA40.fullmatch(source_sha)
            or not isinstance(baseline.get("observed_pr_head_sha"), str)
            or not SHA40.fullmatch(baseline["observed_pr_head_sha"])):
        raise ValueError("source identity not established")
    if (baseline.get("acceptance", {}).get("authority_transfer") is not False
            or baseline["acceptance"].get("merge_authorized") is not False
            or baseline["acceptance"].get("qps_owner_accepted") is not False):
        raise ValueError("unsupported admission authority")
    meta = coverage.get("meta", {}) if isinstance(coverage, dict) else {}
    if (meta.get("branch_coverage") is not True or
            meta.get("version") != baseline.get("coverage_tool_version")):
        raise ValueError("branch mode or coverage version drift")
    measured = coverage.get("files")
    if not isinstance(measured, dict):
        raise ValueError("missing coverage source-file census")
    selected = baseline.get("files")
    if not isinstance(selected, list) or not selected:
        raise ValueError("missing baseline target roster")
    if not isinstance(test_counts, dict) or test_counts.get("failed") != 0:
        raise ValueError("missing reconciled terminal passing tests")
    if not (type(test_counts.get("passed")) is int and test_counts["passed"] > 0
            and type(test_counts.get("executed")) is int
            and test_counts["executed"] ==
            test_counts["passed"] + ensure_count(test_counts.get("skipped"), "skipped")):
        raise ValueError("unreconciled test totals")
    seen, rows = set(), []
    for record in selected:
        if not isinstance(record, dict):
            raise ValueError("invalid baseline member")
        name = verify_path(record.get("path"))
        if name in seen:
            raise ValueError("duplicate baseline production path")
        seen.add(name)
        expected = record.get("source_blob_sha")
        if not isinstance(expected, str) or not SHA40.fullmatch(expected):
            raise ValueError("invalid baseline blob identity")
        if get_blob(name) != expected:
            raise ValueError("production source bytes changed: " + name)
        statements = ensure_count(record.get("eligible_statements"), name)
        branches = ensure_count(record.get("eligible_branches"), name)
        if (statements == 0 or record.get("baseline_covered_statements") != 0
                or record.get("baseline_covered_branches") != 0):
            raise ValueError("baseline must contain executable zero-covered assets")
        # Coverage.py emits POSIX paths on Linux and backslash paths on
        # Windows. Normalize only to the pinned roster, and reject ambiguous
        # aliases rather than selecting one silently or counting false ZERO.
        paths = [key for key in measured if isinstance(key, str)
                 and key.replace("\\", "/") == name]
        if len(paths) > 1:
            raise ValueError("duplicate normalized coverage production path")
        entry = measured[paths[0]] if paths else None
        if entry is None:
            rows.append({"path": name, "status": "UNKNOWN_MISSING_COVERAGE",
                         "source_blob_sha": expected,
                         "eligible_statements": statements,
                         "eligible_branches": branches,
                         "covered_statements": None, "covered_branches": None})
            continue
        summary = entry.get("summary") if isinstance(entry, dict) else None
        if not isinstance(summary, dict):
            raise ValueError("invalid instrumented module record")
        cs = ensure_count(summary.get("covered_lines"), name + ".covered_lines")
        cb = ensure_count(summary.get("covered_branches"), name + ".covered_branches")
        ns = ensure_count(summary.get("num_statements"), name + ".num_statements")
        nb = ensure_count(summary.get("num_branches"), name + ".num_branches")
        if cs > ns or cb > nb:
            raise ValueError("coverage numerator exceeds denominator")
        if (ns, nb) != (statements, branches):
            rows.append({"path": name, "status": "INCOMPARABLE_DENOMINATOR",
                         "source_blob_sha": expected,
                         "eligible_statements": statements,
                         "eligible_branches": branches,
                         "measured_statements": ns, "measured_branches": nb,
                         "covered_statements": cs, "covered_branches": cb})
            continue
        rows.append({"path": name, "status": "RECOVERED" if cs > 0 else "ZERO_COVERED",
                     "source_blob_sha": expected,
                     "eligible_statements": statements, "eligible_branches": branches,
                     "covered_statements": cs, "covered_branches": cb})
    comparable = [row for row in rows if row["status"] in ("RECOVERED", "ZERO_COVERED")]
    recovered = sum(row["status"] == "RECOVERED" for row in comparable)
    remaining = sum(row["status"] == "ZERO_COVERED" for row in comparable)
    cs = sum(row["covered_statements"] for row in comparable)
    ns = sum(row["eligible_statements"] for row in comparable)
    cb = sum(row["covered_branches"] for row in comparable)
    nb = sum(row["eligible_branches"] for row in comparable)
    return {
        "schema": SCHEMA, "repository": "GBOGEB/ABACUS",
        "source_sha": source_sha, "source_blobs_matched": True,
        "observed_pr_head_sha": baseline["observed_pr_head_sha"],
        "historical_event_merge_sha": baseline.get("event_merge_sha"),
        "historical_checkout_sha": baseline.get("checkout_sha"),
        "historical_artifact_id": baseline.get("coverage_artifact_id"),
        "scope": "TEN_PINNED_EXECUTABLE_FILES_NOT_BROAD_REPOSITORY",
        "tests": test_counts, "candidate_coverage_tool_version": meta["version"],
        "targeted_executable_assets": len(rows),
        "eligible_targeted_assets": len(comparable),
        "recovered_zero_covered_assets": recovered,
        "still_zero_covered_assets": remaining,
        "unknown_or_incomparable_assets": len(rows)-len(comparable),
        "matched_statement_coverage": {
            "baseline_covered": 0, "candidate_covered": cs, "eligible": ns},
        "matched_branch_coverage": {
            "baseline_covered": 0, "candidate_covered": cb, "eligible": nb},
        "zero_covered_global_baseline": baseline["baseline_population"][
            "executable_zero_covered_files"],
        "zero_covered_global_current": None,
        "files": rows,
        "authority_transfer": False,
        "merge_authorized": False, "owner_acceptance": "DEFER",
        "native_artifact_bytes_verified": False,
        "worker_hours": None, "real_worker_capacity": None,
        "m1": "STRUCTURAL_RECEIPT", "m2": "HOLD", "m3": "HOLD",
        "pca": "NOT_ASSESSABLE", "bt": "NOT_ASSESSABLE",
    }


def exact_checkout_sha(repo):
    """Accept only a detached Git HEAD; no shell execution or symbolic guessing."""
    dotgit = repo / ".git"
    if not dotgit.is_dir() or (dotgit / "HEAD").is_symlink():
        raise ValueError("Git checkout identity unavailable: HOLD")
    head = (dotgit / "HEAD").read_text(encoding="ascii").strip()
    if not SHA40.fullmatch(head):
        raise ValueError("detached exact Git HEAD required: HOLD")
    return head


def source_blob_sha(repo, path):
    """Compute the canonical Git blob object ID from the checked-out bytes."""
    name = verify_path(path)
    target = repo / name
    if (not target.is_file() or target.is_symlink()
            or not target.resolve().is_relative_to(repo.resolve())):
        raise ValueError("unsafe or missing production source: " + name)
    data = target.read_bytes()
    # Git object IDs are SHA-1 object names, NOT a security signature.
    # nosemgrep: python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data,
        usedforsecurity=False,
    ).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--coverage-json", type=Path, required=True)
    parser.add_argument("--unittest-log", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    repo = opts.repository_root.resolve()
    if exact_checkout_sha(repo) != opts.expected_head:
        raise SystemExit("EXACT_HEAD_SOURCE_MISMATCH")
    base_bytes, cov_bytes, log_bytes = (
        opts.baseline.read_bytes(), opts.coverage_json.read_bytes(),
        opts.unittest_log.read_bytes())
    baseline, coverage = json.loads(base_bytes), json.loads(cov_bytes)

    def source_blob(path):
        # The historical baseline binds the exact immutable source Git blob.
        # This compares real working bytes to that source ID without spawning
        # a subprocess or granting any external execution authority.
        return source_blob_sha(repo, path)

    receipt = measure(baseline, coverage, opts.expected_head, source_blob,
                      parse_terminal(log_bytes))
    opts.out.mkdir(parents=True, exist_ok=True)
    for key, raw in (("baseline", base_bytes), ("coverage", cov_bytes),
                     ("unittest_log", log_bytes)):
        receipt[key + "_sha256"] = hashlib.sha256(raw).hexdigest()
    encoded = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    (opts.out / "zero_asset_pulse.json").write_bytes(encoded)
    manifest = {"schema": "codepurple.zero-asset.evidence-files.v1",
                "source_sha": opts.expected_head,
                "sha256": {"zero_asset_pulse.json": hashlib.sha256(encoded).hexdigest(),
                           "coverage.json": hashlib.sha256(cov_bytes).hexdigest(),
                           "unittest.log": hashlib.sha256(log_bytes).hexdigest(),
                           "baseline.json": hashlib.sha256(base_bytes).hexdigest()}}
    (opts.out / "evidence_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"head": opts.expected_head, "tests": receipt["tests"],
                      "recovered": receipt["recovered_zero_covered_assets"],
                      "eligible": receipt["targeted_executable_assets"],
                      "covered_statements": receipt["matched_statement_coverage"],
                      "covered_branches": receipt["matched_branch_coverage"],
                      "merge_authorized": False}, sort_keys=True))
    if receipt["recovered_zero_covered_assets"] != receipt["targeted_executable_assets"]:
        raise SystemExit("ZERO_ASSET_RECOVERY_INCOMPLETE_HOLD")


if __name__ == "__main__":
    main()
