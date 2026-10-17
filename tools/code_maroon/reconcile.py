"""CODE_MAROON review/security debt reconciler.

Consumes a normalized snapshot and optional SARIF files. Review summaries are
metadata, not findings. Manifestations are never equated with causal roots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = "code-maroon.snapshot.v1"
STATUSES = {"OPEN_ACTIVE", "CLOSED_IMPLEMENTED", "DEFERRED_OWNER", "IMPLEMENTED_UNRESOLVED"}
IMPLEMENTATION_STATES = {"IMPLEMENTED", "NOT_IMPLEMENTED", "NOT_APPLICABLE"}
THREAD_STATES = {"OPEN", "RESOLVED"}
DISPOSITIONS = {"ACTIVE", "CLOSED", "DEFERRED"}


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("snapshot must be an object")
    return data


def _validate(snapshot: dict) -> None:
    if snapshot.get("schema") != SCHEMA:
        raise ValueError("unsupported schema")
    if snapshot.get("authority_transfer") is not False:
        raise ValueError("authority_transfer must remain false")
    if snapshot.get("merge_authorized") is not False:
        raise ValueError("merge_authorized must remain false")

    manifestations = snapshot.get("manifestations")
    roots = snapshot.get("roots")
    if not isinstance(manifestations, list) or not isinstance(roots, list):
        raise ValueError("manifestations and roots must be lists")

    root_ids = [row.get("root_id") for row in roots]
    if any(not isinstance(root_id, str) or not root_id for root_id in root_ids):
        raise ValueError("invalid root identity")
    if len(root_ids) != len(set(root_ids)):
        raise ValueError("duplicate root declaration")
    declared = set(root_ids)

    thread_comment_pairs = set()
    for row in manifestations:
        if row.get("status") not in STATUSES:
            raise ValueError("invalid manifestation status")
        if row.get("root_id") not in declared:
            raise ValueError("manifestation references undeclared root")
        if row.get("implementation_state") not in IMPLEMENTATION_STATES:
            raise ValueError("invalid implementation state")
        if row.get("thread_state") not in THREAD_STATES:
            raise ValueError("invalid thread state")
        if row.get("disposition") not in DISPOSITIONS:
            raise ValueError("invalid disposition")
        if row.get("status") == "CLOSED_IMPLEMENTED" and (
            row["implementation_state"] != "IMPLEMENTED"
            or row["thread_state"] != "RESOLVED"
            or row["disposition"] != "CLOSED"
        ):
            raise ValueError("closed implementation state mismatch")
        if row.get("status") == "IMPLEMENTED_UNRESOLVED" and (
            row["implementation_state"] != "IMPLEMENTED"
            or row["thread_state"] != "OPEN"
        ):
            raise ValueError("implemented unresolved state mismatch")
        pair = (row.get("thread_id"), row.get("comment_id"))
        if pair in thread_comment_pairs:
            raise ValueError("duplicate manifestation identity")
        thread_comment_pairs.add(pair)

    # A completed implementation with an open review thread is allowed;
    # an active, unimplemented failure within a CLOSED root is not.
    active_failure_roots = {
        row["root_id"]
        for row in manifestations
        if row["status"] == "OPEN_ACTIVE"
        or (
            row["disposition"] == "ACTIVE"
            and row["implementation_state"] != "IMPLEMENTED"
        )
    }
    grouped = Counter(row["root_id"] for row in manifestations)
    for root in roots:
        if root.get("status") not in STATUSES:
            raise ValueError("invalid root status")
        if root.get("manifestations") != grouped[root["root_id"]]:
            raise ValueError("root manifestation count mismatch")
        if (
            root["status"] == "CLOSED_IMPLEMENTED"
            and root["root_id"] in active_failure_roots
        ):
            raise ValueError("closed root contains active manifestation")


def _summary(snapshot: dict) -> dict:
    manifestations = snapshot["manifestations"]
    roots = snapshot["roots"]
    return {
        "manifestations_total": len(manifestations),
        "implemented": sum(row["implementation_state"] == "IMPLEMENTED" for row in manifestations),
        "closed": sum(row["thread_state"] == "RESOLVED" for row in manifestations),
        "deferred": sum(row["disposition"] == "DEFERRED" for row in manifestations),
        "outstanding": sum(row["thread_state"] != "RESOLVED" for row in manifestations),
        "failing_active": sum(
            row["disposition"] == "ACTIVE"
            and row["implementation_state"] != "IMPLEMENTED"
            for row in manifestations
        ),
        "roots_total": len(roots),
        "roots_closed": sum(row["status"] == "CLOSED_IMPLEMENTED" for row in roots),
        "roots_deferred": sum(row["status"] == "DEFERRED_OWNER" for row in roots),
        "roots_open": sum(row["status"] == "OPEN_ACTIVE" for row in roots),
    }


def _sarif_results(path: Path) -> list[dict]:
    data = _load(path)
    if data.get("version") not in {"2.1.0", "2.1.0-csd.2.beta.2020-03-11"}:
        raise ValueError(f"{path}: unsupported SARIF version")
    results = []
    for run_index, run in enumerate(data.get("runs", [])):
        tool = run.get("tool", {}).get("driver", {}).get("name", "UNKNOWN")
        for result_index, result in enumerate(run.get("results", [])):
            rule = result.get("ruleId") or "UNKNOWN_RULE"
            locations = result.get("locations") or []
            physical = (
                locations[0].get("physicalLocation", {})
                if locations
                else {}
            )
            artifact = physical.get("artifactLocation", {}).get("uri")
            region = physical.get("region", {})
            fingerprints = result.get("partialFingerprints") or {}
            stable_fp = (
                fingerprints.get("primaryLocationLineHash")
                or fingerprints.get("primaryLocationStartColumnFingerprint")
            )
            results.append(
                {
                    "tool": tool,
                    "rule_id": rule,
                    "artifact": artifact,
                    "line": region.get("startLine"),
                    "stable_fingerprint": stable_fp,
                    "run_index": run_index,
                    "result_index": result_index,
                }
            )
    return results


def _sarif_rollup(paths: list[Path]) -> dict:
    findings = []
    for path in paths:
        findings.extend(_sarif_results(path))

    exact_keys = [
        (
            row["tool"],
            row["rule_id"],
            row["artifact"],
            row["line"],
            row["stable_fingerprint"],
        )
        for row in findings
    ]
    stable_keys = [
        (
            row["tool"],
            row["rule_id"],
            row["stable_fingerprint"],
        )
        for row in findings
        if row["stable_fingerprint"]
    ]
    return {
        "findings_total": len(findings),
        "exact_manifestations": len(set(exact_keys)),
        "stable_fingerprint_groups": len(set(stable_keys)),
        "by_tool": dict(Counter(row["tool"] for row in findings)),
        "note": (
            "SARIF fingerprint groups are dedupe candidates, not accepted causal "
            "roots. CODE_MAROON root_id remains the governed root identity."
        ),
    }


def reconcile(snapshot: dict, sarif_paths: list[Path] | None = None) -> dict:
    _validate(snapshot)
    calculated = _summary(snapshot)
    declared = snapshot.get("summary")
    if declared != calculated:
        raise ValueError(
            f"declared summary mismatch: declared={declared!r} calculated={calculated!r}"
        )

    by_source = Counter(row["source"] for row in snapshot["manifestations"])
    root_manifestations = defaultdict(list)
    for row in snapshot["manifestations"]:
        root_manifestations[row["root_id"]].append(
            {
                "pr": row["pr"],
                "thread_id": row["thread_id"],
                "comment_id": row["comment_id"],
                "status": row["status"],
                "path": row["path"],
            }
        )

    receipt = {
        "schema": "code-maroon.receipt.v1",
        "cohort": snapshot.get("cohort"),
        "observed_at": snapshot.get("observed_at"),
        "authority_transfer": False,
        "merge_authorized": False,
        "summary": calculated,
        "by_source": dict(by_source),
        "outstanding_roots": [
            root
            for root in snapshot["roots"]
            if root["status"] != "CLOSED_IMPLEMENTED"
        ],
        "root_manifestations": dict(root_manifestations),
        "control_events": snapshot.get("control_events", []),
    }
    if sarif_paths:
        receipt["sarif"] = _sarif_rollup(sarif_paths)
    return receipt


def emit(receipt: dict, out: Path) -> str:
    out.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    (out / "code_maroon_receipt.json").write_bytes(raw)
    (out / "code_maroon_receipt.sha256").write_text(digest + "\n", encoding="ascii")

    s = receipt["summary"]
    lines = [
        "# CODE_MAROON snapshot",
        "",
        "| KPI | Count |",
        "|---|---:|",
        f"| Total manifestations | {s['manifestations_total']} |",
        f"| Implemented | {s['implemented']} |",
        f"| Closed/resolved | {s['closed']} |",
        f"| Deferred | {s['deferred']} |",
        f"| Outstanding | {s['outstanding']} |",
        f"| Active failing | {s['failing_active']} |",
        f"| Canonical roots | {s['roots_total']} |",
        f"| Closed roots | {s['roots_closed']} |",
        f"| Deferred roots | {s['roots_deferred']} |",
        f"| Open roots | {s['roots_open']} |",
        "",
        "Manifestations are comments/scanner observations; roots are deduplicated repair units.",
        "Resolved comments remain in the historical total. Review summaries are not findings.",
        "",
        "## Outstanding roots",
        "",
    ]
    for root in receipt["outstanding_roots"]:
        lines.append(
            f"- {root['root_id']} — {root['status']} — "
            f"{root['manifestations']} manifestation(s), PRs {root['prs']}"
        )
    lines += ["", f"Receipt SHA-256: {digest}", ""]
    (out / "code_maroon_receipt.md").write_text("\n".join(lines), encoding="utf-8")
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("CODE_MAROON/snapshot_20261016.json"),
    )
    parser.add_argument("--sarif", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    receipt = reconcile(_load(args.snapshot), args.sarif)
    digest = emit(receipt, args.out)
    print(
        json.dumps(
            {
                **receipt["summary"],
                "sha256": digest,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
