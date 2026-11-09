"""Read-only W31 Safety provenance. Scanner findings are not target-runtime findings.

All security decisions remain fail-closed. This module cannot waive Safety, attest
a reviewer, or grant merge admission. Supplied metadata is source-reported unless
its artifact bytes are independently compared.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SHA40 = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
CVE = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _positive(value, name):
    require(type(value) is int and value > 0, "invalid " + name)


def _scan(report, expected_scope):
    require(isinstance(report, dict), "missing " + expected_scope + " report")
    require(report.get("scope") == expected_scope, "foreign vulnerability scope")
    exit_code = report.get("exit_code")
    packages = report.get("installed_packages")
    require(type(exit_code) is int and exit_code >= 0, "invalid Safety exit")
    require(
        type(packages) is int and packages >= 0, "unknown installed package denominator"
    )
    findings = report.get("findings")
    require(isinstance(findings, list), "missing findings denominator")
    seen = set()
    for item in findings:
        require(isinstance(item, dict), "invalid finding")
        name, version, cve = (item.get(k) for k in ("package", "version", "cve"))
        require(
            all(isinstance(v, str) and v.strip() for v in (name, version, cve)),
            "finding identity missing",
        )
        require(bool(CVE.fullmatch(cve)), "invalid CVE identity")
        ident = (name.casefold(), version, cve)
        require(ident not in seen, "duplicate scanner manifestation")
        seen.add(ident)
    require(
        len({x[0] for x in seen}) <= packages,
        "findings exceed installed package population",
    )
    require(exit_code != 0 or not findings, "Safety falsely green with findings")
    return {
        "scope": expected_scope,
        "exit_code": exit_code,
        "installed_packages": packages,
        "finding_occurrences": len(findings),
        "distinct_cves": len({x[2] for x in seen}),
        "fingerprints": sorted([list(x) for x in seen]),
        "gate_result": "FAIL" if exit_code != 0 else "SCANNER_EXIT_ZERO_ONLY",
    }, seen


def summarize(payload, *, archive_bytes=None):
    require(isinstance(payload, dict), "invalid evidence envelope")
    sha = payload.get("exact_sha")
    require(
        isinstance(sha, str) and bool(SHA40.fullmatch(sha)), "invalid exact source SHA"
    )
    for key in ("run_id", "run_attempt", "job_id"):
        _positive(payload.get(key), key)
    scanner, scanner_items = _scan(payload.get("scanner"), "scanner_environment")
    application_raw = payload.get("application_runtime")
    application, app_items = (
        _scan(application_raw, "application_runtime")
        if application_raw is not None
        else (None, None)
    )
    claimed = payload.get("scanner_artifact_sha256")
    require(
        claimed is None
        or (isinstance(claimed, str) and bool(DIGEST.fullmatch(claimed))),
        "invalid declared artifact digest",
    )
    artifact_match = None
    if archive_bytes is not None:
        require(
            type(archive_bytes) is bytes and len(archive_bytes) > 0,
            "missing artifact bytes",
        )
        require(claimed is not None, "missing declared digest for artifact")
        require(
            hashlib.sha256(archive_bytes).hexdigest() == claimed,
            "artifact SHA256 mismatch",
        )
        artifact_match = True
    return {
        "schema": "abacus.cbd.safety-domain-provenance.v1",
        "exact_sha": sha,
        "run_id": payload["run_id"],
        "run_attempt": payload["run_attempt"],
        "job_id": payload["job_id"],
        "scanner_environment": scanner,
        "application_runtime": application,
        "scanner_only_occurrences": (
            len(scanner_items - app_items) if app_items is not None else None
        ),
        "shared_occurrences": (
            len(scanner_items & app_items) if app_items is not None else None
        ),
        "application_runtime_observed": app_items is not None,
        "artifact_hash_matched_only": artifact_match,
        "independent_artifact_content_assessment": None,
        "security_review_approval": None,
        "causal_roots_closed": None,
        "security_waiver": False,
        "merge_admission": "HOLD",
        "evidence_class": (
            "HASH_MATCH_ONLY" if artifact_match else "SOURCE_REPORTED_UNVERIFIED"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    blob = args.artifact.read_bytes() if args.artifact else None
    result = summarize(
        json.loads(args.evidence.read_text(encoding="utf-8")), archive_bytes=blob
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
