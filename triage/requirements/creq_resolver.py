#!/usr/bin/env python3
"""Resolve global CReq requirements with a repository-local overlay.

Fail-safe rule: an incomplete local override never shadows its global parent.
The global requirement remains effective until the full approval hierarchy is APPROVED.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

GLOBAL_ID = re.compile(r"^CReq_\d{3}$")
LOCAL_ID = re.compile(r"^CReq_[A-Z0-9]+_\d{3}$")
REQUIRED_APPROVALS = (
    "local_repo_owner",
    "parent_cADR_or_cOCD_authority",
    "global_CReq_authority",
)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_global(registry):
    ids = []
    for req in registry["requirements"]:
        if not GLOBAL_ID.match(req["id"]):
            raise ValueError(f"invalid global id {req['id']}")
        ids.append(req["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate global id")
    return {req["id"]: req for req in registry["requirements"]}


def approval_complete(item):
    approvals = {entry["role"]: entry["state"] for entry in item.get("approval_chain", [])}
    return item.get("approval_state") == "APPROVED" and all(
        approvals.get(role) == "APPROVED" for role in REQUIRED_APPROVALS
    )


def resolve(global_registry, overlay):
    global_map = validate_global(global_registry)
    effective = []
    warnings = []
    seen = set()

    for item in overlay.get("requirements", []):
        local_id = item["id"]
        if not LOCAL_ID.match(local_id):
            raise ValueError(f"invalid local id {local_id}")
        if local_id in seen:
            raise ValueError(f"duplicate local id {local_id}")
        seen.add(local_id)

        parent = item.get("overrides") or item.get("parent_global_requirement")
        if parent and parent not in global_map:
            raise ValueError(f"{local_id}: unknown global parent {parent}")

        if item.get("mode", "addition") == "override":
            if approval_complete(item):
                effective.append({
                    "effective_id": local_id,
                    "scope": overlay["repo"],
                    "source": "approved_local_override",
                    "replaces": parent,
                    "title": item["title"],
                })
            else:
                effective.append({
                    "effective_id": parent,
                    "scope": overlay["repo"],
                    "source": "global_fallback",
                    "blocked_override": local_id,
                    "title": global_map[parent]["title"],
                })
                warnings.append(f"{local_id} override blocked: approval chain incomplete")
        else:
            effective.append({
                "effective_id": local_id,
                "scope": overlay["repo"],
                "source": "local_addition",
                "parent_global_requirement": parent,
                "title": item["title"],
            })

    resolved_parents = {
        row.get("replaces") or row.get("parent_global_requirement") or row.get("effective_id")
        for row in effective
        if row.get("source") in ("approved_local_override", "local_addition", "global_fallback")
    }
    for global_id, requirement in global_map.items():
        if global_id not in resolved_parents:
            effective.append({
                "effective_id": global_id,
                "scope": overlay["repo"],
                "source": "global",
                "title": requirement["title"],
            })

    effective.sort(key=lambda row: row["effective_id"])
    receipt = {
        "schema_version": "creq-resolution/0.1.0",
        "repo": overlay["repo"],
        "effective_requirements": effective,
        "warnings": warnings,
        "status": "PASS",
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["sha256"] = hashlib.sha256(canonical).hexdigest()
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--global-registry", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = resolve(load(args.global_registry), load(args.overlay))
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"CReq resolution: {receipt['status']}")
    print(f"repo={receipt['repo']} effective={len(receipt['effective_requirements'])} warnings={len(receipt['warnings'])}")
    for warning in receipt["warnings"]:
        print("WARN:", warning)
    print("sha256=" + receipt["sha256"])


if __name__ == "__main__":
    main()
