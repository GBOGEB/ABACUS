"""Execute the admissible cold slice of the existing MCW artifact DAG.

This is a source/preview proof, never QPS engineering execution or release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SCHEMA = "mcw.artifact.dag.receipt.v1"
STAGES = ("CENSUS", "SSOT_PIN", "SOURCE_FREEZE", "NORMALIZE", "MODEL",
          "DERIVE", "RENDER", "TYPE_QA", "HASH_REPLAY", "RELEASE_REVIEW")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def require(test, message):
    if not test:
        raise ValueError(message)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def confined(root, path):
    require(isinstance(path, str) and bool(path) and "\\" not in path,
            "invalid source path")
    value = Path(path)
    require(not value.is_absolute() and ".." not in value.parts, "unsafe source path")
    target = (root / value).resolve()
    require(target.is_relative_to(root) and target.is_file(),
            "source outside checkout or absent")
    return target


def assess(root, head, catalog, style, preview_html, preview_receipt,
           style_status, child_reference, catalog_bytes=None, style_bytes=None):
    root = Path(root).resolve()
    require(isinstance(head, str) and HEX40.fullmatch(head), "invalid exact head")
    require(preview_receipt.get("source_sha") == head, "stale preview source")
    require(preview_receipt.get("repository") == "GBOGEB/ABACUS",
            "incorrect preview producer")
    require(preview_receipt.get("merge_admission") == "HOLD" and
            preview_receipt.get("binary_release_admitted") is False,
            "unauthorized preview promotion")
    require(tuple(preview_receipt.get("stages", ())) == STAGES,
            "cold DAG disagrees with canonical explorer")
    require(preview_receipt.get("html_sha256") == sha256(preview_html),
            "HTML bytes do not match receipt")
    require(catalog_bytes is not None and style_bytes is not None,
            "raw SSOT bytes required for cold provenance")
    require(preview_receipt.get("catalog_file_sha256") ==
            sha256(catalog_bytes), "catalog byte hash mismatch")
    require(preview_receipt.get("style_file_sha256") ==
            sha256(style_bytes), "style byte hash mismatch")
    require(preview_receipt.get("style_version") == style.get("version"),
            "style version mismatch")
    require(style_status.get("valid") is True, "invalid style SSOT")
    require(child_reference.get("schema") == "mcw.upstream.child.reference.v1"
            and child_reference.get("owner") == "GBOGEB/cryoplant-project"
            and child_reference.get("ref_kind") == "OPEN_PR_CANDIDATE"
            and child_reference.get("evidence_class") == "SOURCE_POINTER_ONLY"
            and child_reference.get("physical_evidence_bytes") == "NOT_VERIFIED"
            and child_reference.get("child_disposition") == "UNKNOWN",
            "child reference attempts authority escalation")
    require(HEX40.fullmatch(child_reference.get("commit_sha", "")),
            "invalid child commit")
    pins = child_reference.get("source_pins")
    require(isinstance(pins, list) and len(pins) > 0, "missing child pointers")
    seen = set()
    for pin in pins:
        require(isinstance(pin, dict) and HEX40.fullmatch(
            pin.get("git_blob_sha", "")), "invalid child Git blob pin")
        name = pin.get("path")
        require(isinstance(name, str) and not name.startswith("/")
                and ".." not in Path(name).parts and name not in seen,
                "unsafe or duplicate child pointer")
        seen.add(name)
    require(catalog.get("schema") == "mcw.artifact.catalog.v1",
            "wrong catalog schema")
    entries = preview_receipt.get("artifacts", [])
    require(len(entries) == len(catalog.get("artifacts", [])) > 0,
            "source catalog count mismatch")
    observations = []
    expected = {row["id"]: row for row in catalog["artifacts"]}
    require(len(expected) == len(entries), "duplicate catalog IDs")
    for row in entries:
        require(row.get("id") in expected and
                row.get("role") == expected[row["id"]]["role"],
                "artifact identity mismatch")
        observed = row.get("evidence", {})
        role = row["role"]
        if role == "repository_source":
            path = expected[row["id"]]["path"]
            file = confined(root, path)
            digest = sha256(file.read_bytes())
            require(observed.get("sha256") == digest and
                    observed.get("state") == "LOCAL_BYTES_VERIFIED",
                    "source byte mismatch: " + path)
            observations.append({"artifact_id": row["id"], "sha256": digest})
        elif role == "generated_output":
            require(observed.get("state") == "NOT_GENERATED_IN_COLD_VIEW" and
                    observed.get("sha256") is None,
                    "generated binary falsely claimed")
        elif role == "controlled_input":
            require(observed.get("state") in ("CONTROLLED_EXTERNAL_UNKNOWN",
                    "CONTROLLED_INPUT_NOT_MOUNTED") and
                    observed.get("sha256") is None, "controlled input falsely present")
        else:
            raise ValueError("unsupported artifact role")
    steps = []
    for i, stage in enumerate(STAGES):
        if i < 2:
            state = "PASS"
            why = ("source census verified" if i == 0
                   else "local SSOT hashes and candidate child pointers bound")
        elif i == 2:
            state, why = "BLOCKED", (
                "child physical evidence bytes and authorized disposition "
                "not supplied; no source freeze")
        elif stage == "RELEASE_REVIEW":
            state, why = "HOLD", "independent child and repository admission pending"
        else:
            state, why = "NOT_RUN", "prerequisite SOURCE_FREEZE is blocked"
        steps.append({"stage": stage, "status": state, "reason": why})
    return {"schema": SCHEMA, "repository": "GBOGEB/ABACUS",
            "source_sha": head, "upstream_owner": child_reference["owner"],
            "upstream_pr": child_reference["pr_number"],
            "upstream_candidate_sha": child_reference["commit_sha"],
            "upstream_source_pins": len(pins),
            "upstream_proof_grade": "GIT_POINTER_METADATA_ONLY",
            "observed_local_sources": observations,
            "preview_html_sha256": sha256(preview_html),
            "preview_gate": "PASS_COLD_SOURCE_ONLY",
            "stages": steps, "stage_pass": 2, "stage_blocked": 1,
            "stage_not_run": 6, "stage_hold": 1,
            "first_blocker": "SOURCE_FREEZE",
            "physical_evidence_verified": False,
            "qps_binary_generation": "NOT_EXECUTED",
            "child_engineering_credit": 0, "authority_transfer": False,
            "merge_admission": "HOLD"}


def main():
    parser = argparse.ArgumentParser()
    for name in ("root", "catalog", "style", "style-status", "html",
                 "receipt", "child-reference", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    actual = subprocess.check_output(
        ["git", "-C", str(args.root), "rev-parse", "HEAD"], text=True
    ).strip()
    require(actual == args.sha, "executed checkout SHA mismatch")
    result = assess(
        args.root, args.sha, json.loads(args.catalog.read_text()),
        json.loads(args.style.read_text()), args.html.read_bytes(),
        json.loads(args.receipt.read_text()),
        json.loads(args.style_status.read_text()),
        json.loads(args.child_reference.read_text()),
        args.catalog.read_bytes(), args.style.read_bytes()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"head": actual, "first_blocker": result["first_blocker"],
                      "pass": result["stage_pass"],
                      "merge_admission": "HOLD"}))


if __name__ == "__main__":
    main()
