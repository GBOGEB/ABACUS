"""MIP B-1 fail-closed worker admission and telemetry producer.

Consumes native exact-SHA JUnit and explicit signed-off evidence metadata.
A PASS workflow alone does not prove a particular test executed.
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SCHEMA = "mip.bminus1.admission.v1"
STAGES = ("IMPLEMENTED", "VERIFIED", "ROOT_RESOLVED", "INTEGRATION_ELIGIBLE", "MERGE_ADMITTED")

def _cases(junit: Path):
    root = ET.parse(junit).getroot()
    cases = {}
    for case in root.iter("testcase"):
        key = (case.get("classname", "") + "::" + case.get("name", "")).strip(":")
        if not key or key in cases:
            raise ValueError("missing or duplicate testcase identifier")
        status = ("failed" if case.find("failure") is not None or case.find("error") is not None else
                  "skipped" if case.find("skipped") is not None else "passed")
        cases[key] = status
    return cases

def evaluate(manifest: dict, junit: Path) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("worker manifest must be an object")
    sha = manifest.get("exact_sha")
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("exact_sha must be a full lowercase hexadecimal commit")
    required = manifest.get("required_tests")
    if not isinstance(required, list) or not required or len(set(required)) != len(required):
        raise ValueError("nonempty unique required_tests required")
    if not all(isinstance(t, str) and t for t in required):
        raise ValueError("invalid test identifier")
    cases = _cases(junit)
    observed = {t: cases.get(t, "missing") for t in required}
    counts = {s: sum(x == s for x in observed.values()) for s in ("passed", "failed", "skipped", "missing")}
    records = manifest.get("first_reds", [])
    if not isinstance(records, list):
        raise ValueError("first_reds must be an array")
    owned, overflow, bad_records = set(), [], []
    for record in records:
        if not isinstance(record, dict):
            bad_records.append("invalid_record")
            continue
        fingerprint, owner = record.get("fingerprint"), record.get("owner")
        if not isinstance(fingerprint, str) or not fingerprint or fingerprint in owned or not isinstance(owner, str) or not owner:
            bad_records.append("duplicate_or_unowned")
        else:
            owned.add(fingerprint)
        if record.get("disposition") != "RESOLVED":
            overflow.append({"fingerprint": fingerprint, "owner": owner, "disposition": record.get("disposition", "UNKNOWN"),
                             "origin_run": record.get("origin_run"), "origin_job": record.get("origin_job")})
    evidence = manifest.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    source_ok = bool(manifest.get("code_committed") and manifest.get("tests_committed"))
    exact = evidence.get("commit_sha") == sha and bool(evidence.get("run_id") and evidence.get("job_id"))
    tests_ok = counts["passed"] == len(required)
    producer_ok = bool(evidence.get("producer_schema_valid") is True and evidence.get("negative_controls_passed") is True)
    implemented = source_ok
    verified = implemented and exact and tests_ok and producer_ok and not bad_records
    root_resolved = verified and bool(evidence.get("root_fix_native_proof") is True) and not overflow
    integration = root_resolved and bool(evidence.get("security_controls_pass") is True and evidence.get("all_required_checks_pass") is True)
    admitted = integration and bool(evidence.get("eligible_review") is True and evidence.get("effective_branch_protection") is True and evidence.get("merge_sha"))
    decisions = dict(zip(STAGES, (implemented, verified, root_resolved, integration, admitted)))
    return {"schema": SCHEMA, "worker_id": manifest.get("worker_id"), "exact_sha": sha,
            "required_tests": required, "executed_tests": observed, "test_counts": counts,
            "all_junit_case_counts": {s: sum(x == s for x in cases.values()) for s in ("passed", "failed", "skipped")},
            "root_id": manifest.get("root_id"), "owner": manifest.get("owner"),
            "evidence_references": {k: evidence.get(k) for k in ("commit_sha", "run_id", "job_id", "artifact_uri")},
            "first_red_count": len(records), "overflow": overflow, "invalid_first_reds": bad_records,
            "decisions": decisions, "highest_stage": next((s for s in reversed(STAGES) if decisions[s]), "UNVERIFIED"),
            "root_closure": "VERIFIED" if root_resolved else "NOT_ESTABLISHED",
            "merge_admission": "ADMITTED" if admitted else "HOLD", "security_waiver": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("mip_bminus1_admission.json"))
    a = parser.parse_args()
    report = evaluate(json.loads(a.manifest.read_text()), a.junit)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"stage": report["highest_stage"], "counts": report["test_counts"], "overflow": len(report["overflow"])}))
    if not report["decisions"]["VERIFIED"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
