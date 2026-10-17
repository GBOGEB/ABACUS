#!/usr/bin/env python3
"""Read-only bootstrap / LLDB / LDAB / BD evidence correlation.

Unknown is null, and proposed work never counts as completed execution.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
FP = re.compile(r"^[0-9a-f]{64}$")
PLATFORMS = ("ubuntu", "rhel8", "rhel9", "ubi9")
STAGES = (
    ("YAML_PREFLIGHT", ()),
    ("GITHUB_RECEIPT", ("YAML_PREFLIGHT",)),
    ("DEBUG_LLDB", ("YAML_PREFLIGHT",)),
    ("RUNTIME_HOST", ("YAML_PREFLIGHT",)),
    ("LDAB_CORRELATION", ("GITHUB_RECEIPT", "DEBUG_LLDB")),
    ("JOINED_CENSUS", ("GITHUB_RECEIPT", "LDAB_CORRELATION", "RUNTIME_HOST")),
    ("KPI_PULSE", ("JOINED_CENSUS",)),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def scoped(item, repository, sha):
    require(isinstance(item, dict), "receipt must be object")
    require(item.get("repository") == repository and item.get("source_sha") == sha,
            "receipt repository/SHA mismatch")
    require(type(item.get("run_id")) is int and item["run_id"] > 0,
            "native run ID required")
    require(type(item.get("job_id")) is int and item["job_id"] > 0,
            "native job ID required")
    return item


def summarize(payload):
    require(isinstance(payload, dict) and payload.get("schema") ==
            "code-purple.bootstrap-ldab.input.v1", "invalid input schema")
    repository, sha = payload.get("repository"), payload.get("source_sha")
    require(isinstance(repository, str) and repository == "GBOGEB/ABACUS",
            "unexpected repository")
    require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid source SHA")
    receipts = payload.get("receipts")
    require(isinstance(receipts, list), "receipts array required")
    result = {"schema": "code-purple.bootstrap-ldab.census.v1",
              "repository": repository, "source_sha": sha,
              "authority": "READ_ONLY", "merge_admission": "HOLD",
              "security_waiver": False, "authority_transfer": False,
              "stage_order": [{"id": k, "needs": list(v)} for k, v in STAGES],
              "bootstrap": {"passed": None, "failed": None, "skipped": None,
                            "runner": None, "run_id": None, "job_id": None},
              "lldb": {"launches": None, "dap_success": None, "failures": None},
              "ldab": {"matched": None, "unmatched": None},
              "bd": {"opened": None, "closed": None, "reopened": None},
              "compatibility": {p: {"status": "UNKNOWN", "run_id": None,
                                    "job_id": None, "runner": None}
                                for p in PLATFORMS}}
    observed = set()
    groups = {}
    for item in receipts:
        require(isinstance(item, dict), "receipt must be object")
        if item.get("kind") == "proposal":
            continue
        scoped(item, repository, sha)
        kind = item.get("kind")
        require(kind in ("bootstrap", "lldb", "ldab", "bd", "compatibility"),
                "unknown receipt kind")
        key = (kind, item["run_id"], item["job_id"])
        require(key not in observed, "duplicate native job receipt")
        observed.add(key)
        groups.setdefault(kind, []).append(item)
    boots = groups.get("bootstrap", [])
    require(len(boots) <= 1, "multiple bootstrap jobs require a scoped aggregate")
    if boots:
        b = boots[0]
        require(isinstance(b.get("runner"), str) and b["runner"], "runner required")
        for k in ("passed", "failed", "skipped"):
            require(type(b.get(k)) is int and b[k] >= 0, "invalid bootstrap count")
        result["bootstrap"] = {k: b[k] for k in ("passed", "failed", "skipped", "runner", "run_id", "job_id")}
    ll = groups.get("lldb", [])
    if ll:
        for b in ll:
            require(b.get("native") is True, "LLDB must be native")
            require(b.get("status") in ("DAP_PASS", "DAP_FAIL", "LAUNCH_FAIL"),
                    "invalid LLDB status")
        result["lldb"] = {"launches": len(ll),
                          "dap_success": sum(x["status"] == "DAP_PASS" for x in ll),
                          "failures": sum(x["status"] != "DAP_PASS" for x in ll)}
    debug_ids = {(x["run_id"], x["job_id"]) for x in ll}
    ld = groups.get("ldab", [])
    if ld:
        matched = 0
        for b in ld:
            require(isinstance(b.get("root_id"), str) and b["root_id"], "root ID required")
            require(isinstance(b.get("fingerprint"), str) and FP.fullmatch(b["fingerprint"]),
                    "fingerprint required")
            link = b.get("debug_job")
            require(isinstance(link, dict), "debug linkage required")
            if (link.get("run_id"), link.get("job_id")) in debug_ids:
                matched += 1
        result["ldab"] = {"matched": matched, "unmatched": len(ld) - matched}
    bd = groups.get("bd", [])
    if bd:
        roots = set()
        counts = {"opened": 0, "closed": 0, "reopened": 0}
        for b in bd:
            require(b.get("native") is True and b.get("verified") is True,
                    "BD transitions require verified native receipt")
            require(b.get("transition") in counts, "invalid root transition")
            require(isinstance(b.get("root_id"), str) and b["root_id"], "root ID required")
            require(isinstance(b.get("fingerprint"), str) and FP.fullmatch(b["fingerprint"]),
                    "BD fingerprint required")
            require(b["root_id"] not in roots, "duplicate BD root")
            roots.add(b["root_id"])
            counts[b["transition"]] += 1
        result["bd"] = counts
    for b in groups.get("compatibility", []):
        platform = b.get("platform")
        require(platform in PLATFORMS, "unknown platform")
        require(result["compatibility"][platform]["status"] == "UNKNOWN",
                "duplicate OS receipt")
        require(b.get("native") is True and b.get("status") in ("PASS", "FAIL"),
                "OS requires native terminal result")
        require(isinstance(b.get("runner"), str) and b["runner"], "runner required")
        result["compatibility"][platform] = {k: b[k] for k in ("status", "run_id", "job_id", "runner")}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
