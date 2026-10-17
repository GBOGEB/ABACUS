"""Conservative source-observation adapters for existing MCL, LDAB, BD evidence.

This tool does not authenticate GitHub artifacts, execute peers, or prove repairs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
INPUT_SCHEMA = "mcw.federation.input.v1"
SOURCES = {
    "MCL": "mcl.coverage.pulse.v1",
    "LDAB": "mip.ldab.telemetry.v1",
    "CENSUS": "bd.ldab.joined.census.v1",
}


def require(test, reason):
    if not test:
        raise ValueError(reason)


def integer(value, field):
    require(type(value) is int and value >= 0, "invalid " + field)
    return value


def load(root, relative):
    require(isinstance(relative, str) and bool(relative), "missing input path")
    path = Path(relative)
    require(not path.is_absolute() and ".." not in path.parts, "unsafe input path")
    base = Path(root).resolve()
    target = (base / path).resolve()
    require(target.is_relative_to(base) and target.is_file(), "input outside root or absent")
    raw = target.read_bytes()
    require(bool(raw), "empty source receipt")
    value = json.loads(raw)
    require(isinstance(value, dict), "source receipt must be JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def _ldab(obj):
    sc = obj.get("source_census")
    runtime = obj.get("runtime")
    require(isinstance(sc, dict) and isinstance(runtime, dict), "missing LDAB census/runtime")
    require(sc.get("combined_candidates") is None and
            sc.get("combined_is_disjoint") is False and
            sc.get("candidate_files_are_not_sessions") is True,
            "invalid nested-count contract")
    counts = {}
    for location in ("root", "nested"):
        val = sc.get(location)
        if val is None and location == "nested":
            counts[location] = None
            continue
        require(isinstance(val, dict) and
                val.get("evidence_level") == "SOURCE_DISCOVERY_ONLY" and
                val.get("live_runtime_inferred") is False,
                "source discovery claims runtime")
        total = integer(val.get("candidate_file_count"), location + " count")
        sample = integer(val.get("sample_count"), location + " sample")
        require(sample <= total, "LDAB sample exceeds census")
        counts[location] = total
    for field in ("abacus_native_debug_sessions", "authenticated_port_leases",
                  "active_runner_workers", "ldab_verified_repairs",
                  "debug_probe_steps"):
        require(runtime.get(field) is None, "unauthorized runtime assertion")
    require(runtime.get("proof_state") == "UNKNOWN_NO_RUNTIME_RECEIPT",
            "unexpected runtime proof state")
    require(obj.get("security_waiver") is False,
            "LDAB security waiver asserted")
    diagnostic = obj.get("diagnostic_execution")
    require(isinstance(diagnostic, dict) and
            diagnostic.get("diagnostic_scope") == "FEDERATION_CONTRACT_ONLY" and
            diagnostic.get("state") in ("NOT_EXECUTED", "EXECUTED_PASS"),
            "invalid LDAB diagnostic scope")
    if diagnostic["state"] == "EXECUTED_PASS":
        require(counts["nested"] is not None and
                diagnostic.get("diagnostic") == "nested_debug_ldab" and
                diagnostic.get("contract_checks_total") is not None and
                integer(diagnostic.get("contract_checks_total"),
                        "LDAB diagnostic total") > 0 and
                diagnostic.get("contract_checks_passed") ==
                diagnostic["contract_checks_total"] and
                diagnostic.get("contract_checks_failed") == 0 and
                diagnostic.get("source_contract") ==
                "integration/codespace_jyperter/tests/test_smoke_federation.py" and
                isinstance(diagnostic.get("source_contract_sha256"), str) and
                re.fullmatch(r"[0-9a-f]{64}",
                             diagnostic["source_contract_sha256"]),
                "forged LDAB executed contract diagnostic")
    return {"root_candidate_files": counts["root"],
            "nested_candidate_files": counts["nested"],
            "deduplicated_candidate_files": None,
            "nested_contract_diagnostic": diagnostic["state"],
            "native_debugger_sessions": None}


def _bd(obj):
    metrics = obj.get("metrics")
    roots = obj.get("roots")
    unlinked = obj.get("unlinked_debug_receipts")
    require(isinstance(metrics, dict) and isinstance(roots, list) and
            isinstance(unlinked, list), "invalid BD joins")
    require(obj.get("security_waiver") is False and
            obj.get("security_disposition") == "INDEPENDENT_REVIEW_REQUIRED" and
            type(obj.get("formal_credit_delta")) is int and
            obj.get("formal_credit_delta") == 0 and
            type(obj.get("engineering_credit_delta")) is int and
            obj["engineering_credit_delta"] == 0,
            "BD guard unexpectedly promoted")
    unique = integer(metrics.get("full_bandit_unique"), "full Bandit unique")
    for item in roots:
        require(isinstance(item, dict) and isinstance(item.get("root_id"), str)
                and item["root_id"].startswith(("BD-", "CI-")),
                "invalid candidate root ID")
        require(item.get("disposition") != "VERIFIED_CLOSED",
                "unverified BD closure asserted")
    require(len({x["root_id"] for x in roots}) == len(roots), "duplicate candidate roots")
    require(metrics.get("active_workers") is None and
            metrics.get("changed_line_coverage") is None,
            "BD source count asserted live workers/coverage")
    return {"bandit_unique_fingerprints": unique,
            "root_candidate_groups": len(roots),
            "unlinked_debug_receipts": len(unlinked),
            "active_workers": None,
            "verified_closed_roots": None}


def _mcl(obj):
    totals = obj.get("totals")
    require(isinstance(totals, dict), "missing MCL coverage totals")
    covered = integer(totals.get("covered_lines"), "covered lines")
    total = integer(totals.get("num_statements"), "total statements")
    covered_branch = integer(totals.get("covered_branches"), "covered branches")
    branch_total = integer(totals.get("num_branches"), "total branches")
    require(total > 0 and covered <= total and covered_branch <= branch_total,
            "invalid MCL coverage")
    require(obj.get("merge_admission") == "HOLD" and
            obj.get("verified_root_closures") == 0,
            "MCL promoted admission/closure")
    require(type(obj.get("tests_passed")) is int and obj["tests_passed"] > 0,
            "MCL test count missing")
    require(obj.get("comparison", {}).get("status") in
            ("UNKNOWN", "COMPARABLE", "INCOMPARABLE"),
            "missing MCL comparison disposition")
    return {"focused_tests_reported_pass": obj["tests_passed"],
            "focused_test_denominator": None,
            "line_percent_reported": round(100 * covered / total, 4),
            "branch_percent_reported": (round(100 * covered_branch / branch_total, 4)
                                        if branch_total else None),
            "line_scope": obj.get("scope_id"),
            "comparison_status": obj["comparison"]["status"],
            "verified_root_closures": None}


def adapt(source, family, repository, source_sha, digest, wave_id):
    require(family in SOURCES, "unknown producer family")
    require(source.get("schema") == SOURCES[family], "producer schema mismatch")
    require(isinstance(repository, str) and repository.count("/") == 1 and
            all(repository.split("/")), "bad repository")
    require(isinstance(source_sha, str) and HEX40.fullmatch(source_sha),
            "invalid exact SHA")
    if family == "CENSUS":
        scope = source.get("scope")
        require(isinstance(scope, dict) and
                scope.get("repository") == repository and
                scope.get("head_sha") == source_sha,
                "BD source identity mismatch")
    else:
        require(source.get("repository") == repository and
                source.get("source_sha") == source_sha,
                "source identity mismatch")
    require(source.get("merge_admission") == "HOLD" and
            source.get("authority_transfer") is False if family != "MCL"
            else source.get("merge_admission") == "HOLD",
            "source authority mismatch")
    normalized = {"MCL": _mcl, "LDAB": _ldab, "CENSUS": _bd}[family](source)
    return {"id": "source-" + family.lower() + "-" + wave_id,
            "repository": repository, "source_sha": source_sha,
            "family": family,
            "source_observation": {"schema": SOURCES[family],
                                   "local_sha256": digest,
                                   "evidence_grade": "UNAUTHENTICATED_SOURCE_BYTES",
                                   "metrics": normalized}}


def build(root, mapping, repository, source_sha, wave_id):
    require(isinstance(wave_id, str) and bool(wave_id) and
            re.fullmatch(r"[A-Za-z0-9_-]{1,64}", wave_id), "invalid wave ID")
    require(isinstance(mapping, dict) and bool(mapping), "missing adapters")
    nodes = []
    for family, relative in sorted(mapping.items()):
        obj, digest = load(root, relative)
        nodes.append(adapt(obj, family, repository, source_sha, digest, wave_id))
    return {"schema": INPUT_SCHEMA, "wave_id": wave_id, "nodes": nodes,
            "edges": [], "producer_trust": "UNAUTHENTICATED_SOURCE_BYTES_ONLY"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--wave-id", required=True)
    parser.add_argument("--mcl")
    parser.add_argument("--ldab")
    parser.add_argument("--bd")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    mapping = {family: value for family, value in
               (("MCL", args.mcl), ("LDAB", args.ldab), ("CENSUS", args.bd))
               if value is not None}
    result = build(args.artifact_root, mapping, args.repository,
                   args.source_sha, args.wave_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"wave_id": args.wave_id, "source_only": len(result["nodes"]),
                      "merge_admission": "HOLD"}))


if __name__ == "__main__":
    main()
