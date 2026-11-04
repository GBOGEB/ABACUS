#!/usr/bin/env python3
"""Join governed Bandit, CI and debugger observations without authority transfer.

Inputs are evidence manifests, not claims of live workers or a security waiver.
This tool never contacts GitHub or changes repository state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
FP = re.compile(r"[0-9a-f]{64}\Z")
LANES = ("B2-source", "B3-subprocess", "B4-files-secrets", "B5-tests")


def need_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} requires a non-empty string")
    return value


def need_sha(value, field):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError(f"{field} requires a lowercase exact SHA")
    return value


def need_integer(value, field, *, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{field} requires integer >= {minimum}")
    return value


def need_url(value, field):
    need_text(value, field)
    if not value.startswith("https://github.com/"):
        raise ValueError(f"{field} requires a GitHub evidence URL")
    return value


def safe_path(value):
    need_text(value, "source_path")
    raw = value.replace("\\", "/")
    if (
        raw.startswith("/")
        or (len(raw) >= 2 and raw[1] == ":")
        or any(part == ".." for part in raw.split("/"))
    ):
        raise ValueError("Unsafe source_path")
    path = "/".join(part for part in raw.split("/") if part and part != ".")
    if not path:
        raise ValueError("Empty normalized source_path")
    return path


def digest(parts):
    data = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:24]


def collect_disjoint(disjoint, sha):
    if (
        not isinstance(disjoint, dict)
        or disjoint.get("schema") != "bandit.disjoint.census.v1"
    ):
        raise ValueError("Unsupported disjoint Bandit schema")
    if need_sha(disjoint.get("exact_sha"), "disjoint.exact_sha") != sha:
        raise ValueError("Disjoint census SHA differs from source head")
    lanes = disjoint.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != set(LANES):
        raise ValueError("Disjoint census requires exactly four known lanes")
    owners, rows, fingerprints = {}, [], set()
    for lane in LANES:
        block = lanes[lane]
        if not isinstance(block, dict) or not isinstance(block.get("items"), list):
            raise ValueError(f"Invalid items for {lane}")
        current_paths = set()
        for item in block["items"]:
            if not isinstance(item, dict):
                raise ValueError("Invalid Bandit item")
            path = safe_path(item.get("path"))
            fp = item.get("fingerprint")
            if not isinstance(fp, str) or not FP.fullmatch(fp):
                raise ValueError("Invalid Bandit fingerprint")
            need_text(item.get("rule"), "Bandit rule")
            need_integer(item.get("line"), "Bandit line")
            if fp in fingerprints:
                raise ValueError("Duplicate Bandit fingerprint")
            fingerprints.add(fp)
            if path in owners and owners[path] != lane:
                raise ValueError("File has multiple disjoint owners")
            owners[path] = lane
            current_paths.add(path)
            rows.append((fp, path, item["rule"], item["line"], lane))
        if block.get("findings") != len(block["items"]) or block.get("files") != len(
            current_paths
        ):
            raise ValueError(f"Denominator mismatch in {lane}")
    if disjoint.get("total_unique") != len(rows):
        raise ValueError("Full Bandit total does not reconcile")
    return sorted(rows), owners


def join(bundle):
    """Return a byte-stable, observation-only root/cross-repository report."""
    if not isinstance(bundle, dict) or bundle.get("schema") != "bd.ldab.input.v1":
        raise ValueError("Unsupported join input schema")
    scope = bundle.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("Missing source scope")
    repo = need_text(scope.get("repository"), "scope.repository")
    sha = need_sha(scope.get("head_sha"), "scope.head_sha")
    config = need_text(scope.get("scan_configuration"), "scope.scan_configuration")
    run = need_integer(scope.get("run_id"), "scope.run_id")
    job = need_integer(scope.get("job_id"), "scope.job_id")
    url = need_url(scope.get("evidence_url"), "scope.evidence_url")
    rows, owners = collect_disjoint(bundle.get("bandit_disjoint"), sha)
    roots, by_fp = {}, {}
    for fp, path, rule, line, lane in rows:
        root = "BD-" + digest([repo, config, fp])
        by_fp[fp] = root
        roots[root] = {
            "root_id": root,
            "category": "BANDIT",
            "fingerprint": fp,
            "source_path": path,
            "rule_or_error_code": rule,
            "line": line,
            "owner_lane": lane,
            "observations": [
                {
                    "repository": repo,
                    "source_sha": sha,
                    "run_id": run,
                    "job_id": job,
                    "evidence_url": url,
                    "source": "bandit_disjoint",
                    "scan_configuration": config,
                }
            ],
            "disposition": "OPEN_UNREVIEWED",
        }

    ci = bundle.get("ci_failures", [])
    debugger = bundle.get("debug_receipts", [])
    if not isinstance(ci, list) or not isinstance(debugger, list):
        raise ValueError("CI and debug observations require arrays")
    unmatched_debug = []
    for obs in ci:
        if not isinstance(obs, dict):
            raise ValueError("Invalid CI observation")
        obs_repo = need_text(obs.get("repository"), "CI.repository")
        obs_sha = need_sha(obs.get("source_sha"), "CI.source_sha")
        signature = need_text(obs.get("signature"), "CI.signature")
        code = need_text(obs.get("rule_or_error_code"), "CI.rule_or_error_code")
        this_run = need_integer(obs.get("run_id"), "CI.run_id")
        this_job = need_integer(obs.get("job_id"), "CI.job_id")
        this_url = need_url(obs.get("evidence_url"), "CI.evidence_url")
        path = (
            safe_path(obs["source_path"])
            if obs.get("source_path") is not None
            else None
        )
        fp = obs.get("related_bandit_fingerprint")
        if fp is not None:
            if fp not in by_fp or obs_repo != repo or obs_sha != sha:
                raise ValueError("CI linkage lacks same-head Bandit evidence")
            root = by_fp[fp]
        else:
            root = "CI-" + digest([obs_repo, path, code, signature])
            roots.setdefault(
                root,
                {
                    "root_id": root,
                    "category": "CI",
                    "fingerprint": None,
                    "source_path": path,
                    "rule_or_error_code": code,
                    "line": None,
                    "owner_lane": (
                        owners.get(path)
                        if obs_repo == repo and obs_sha == sha
                        else None
                    ),
                    "observations": [],
                    "disposition": "UNCLASSIFIED_FIRST_RED",
                },
            )
        roots[root]["observations"].append(
            {
                "repository": obs_repo,
                "source_sha": obs_sha,
                "run_id": this_run,
                "job_id": this_job,
                "evidence_url": this_url,
                "source": "ci_failure",
                "signature": signature,
            }
        )

    for obs in debugger:
        if not isinstance(obs, dict):
            raise ValueError("Invalid debugger observation")
        obs_repo = need_text(obs.get("repository"), "debug.repository")
        obs_sha = need_sha(obs.get("source_sha"), "debug.source_sha")
        steps = need_integer(
            obs.get("real_probe_steps"), "debug.real_probe_steps", minimum=0
        )
        receipt = {
            "repository": obs_repo,
            "source_sha": obs_sha,
            "run_id": need_integer(obs.get("run_id"), "debug.run_id"),
            "job_id": need_integer(obs.get("job_id"), "debug.job_id"),
            "evidence_url": need_url(obs.get("evidence_url"), "debug.evidence_url"),
            "session_id": obs.get("session_id"),
            "real_probe_steps": steps,
            "runner_id": obs.get("runner_id"),
            "port_lease_id": obs.get("port_lease_id"),
            "container_id": obs.get("container_id"),
            "image_digest": obs.get("image_digest"),
            "host_binding": obs.get("host_binding"),
            "source": "debug_receipt",
            "proof_level": (
                "REPORTED_UNVERIFIED"
                if steps > 0 and obs.get("session_id") and obs.get("runner_id")
                else "PARTIAL"
            ),
        }
        fp = obs.get("related_bandit_fingerprint")
        if fp is not None:
            if fp not in by_fp or obs_repo != repo or obs_sha != sha:
                raise ValueError("Debug linkage lacks same-head Bandit evidence")
            roots[by_fp[fp]]["observations"].append(receipt)
        else:
            # Cross-repository LLDB must not inherit ABACUS authority by proximity.
            unmatched_debug.append(receipt)

    comparable = None
    previous = bundle.get("previous")
    if previous is not None:
        if not isinstance(previous, dict):
            raise ValueError("Invalid historical comparison manifest")
        if (
            previous.get("scan_configuration") != config
            or previous.get("repository") != repo
        ):
            raise ValueError("Historical scan configuration/repository mismatch")
        prev_sha = need_sha(previous.get("head_sha"), "previous.head_sha")
        if prev_sha == sha:
            raise ValueError("Historical comparison SHA shall differ")
        old_rows, _ = collect_disjoint(previous.get("bandit_disjoint"), prev_sha)
        before = {x[0] for x in old_rows}
        after = set(by_fp)
        comparable = {
            "before_sha": prev_sha,
            "after_sha": sha,
            "before_unique": len(before),
            "after_unique": len(after),
            "new": len(after - before),
            "resolved": len(before - after),
            "net_reduction": len(before) - len(after),
            "scan_configuration": config,
            "status": "FINGERPRINT_DELTA_ONLY_REVIEW_REQUIRED",
        }
    for item in roots.values():
        item["observations"].sort(
            key=lambda o: (
                o["repository"],
                o["source_sha"],
                o["run_id"],
                o["job_id"],
                o["source"],
                o["evidence_url"],
            )
        )
    return {
        "schema": "bd.ldab.joined.census.v1",
        "scope": dict(sorted(scope.items())),
        "metrics": {
            "full_bandit_unique": len(rows),
            "assigned_files": len(owners),
            "duplicate_file_owners": 0,
            "ci_observations": len(ci),
            "debug_receipts": len(debugger),
            "debug_reported_sessions": sum(
                o["proof_level"] == "REPORTED_UNVERIFIED" for o in unmatched_debug
            )
            + sum(
                o.get("proof_level") == "REPORTED_UNVERIFIED"
                for root in roots.values()
                for o in root["observations"]
            ),
            "comparable_delta": comparable,
            "changed_line_coverage": None,
            "active_workers": None,
        },
        "roots": [roots[k] for k in sorted(roots)],
        "unlinked_debug_receipts": sorted(
            unmatched_debug,
            key=lambda o: (
                o["repository"],
                o["source_sha"],
                o["run_id"],
                o["job_id"],
            ),
        ),
        "merge_admission": "HOLD",
        "security_disposition": "INDEPENDENT_REVIEW_REQUIRED",
        "authority_transfer": False,
        "security_waiver": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = join(json.loads(args.input.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
