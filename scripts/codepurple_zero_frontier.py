"""Fail-closed same-population statement/branch and zero-file comparison.

This supplementary offline receipt is not Mission Control #530's ZIP verifier,
#531's six-repository breadth producer or #533's lane viewer.  It cannot
approve merges, close roots, waive security, authenticate QPS, or dispatch work.

Usage:
  python scripts/codepurple_zero_frontier.py --baseline old-coverage.json \
    --candidate candidate-contexts.json \
    --manifest triage/W77_LEGACY12_SOURCE_BASELINE.json \
    --head <exact-PR-head-SHA> --out zero-frontier.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")


def _normalize(filename):
    if not isinstance(filename, str):
        raise ValueError("non-text coverage path")
    path = filename.replace("\\", "/")
    if (not path or path.startswith("/") or ":" in path or
            any(part in ("", ".", "..") for part in path.split("/"))):
        raise ValueError("noncanonical coverage path")
    return path


def _files(report):
    raw = report.get("files")
    if not isinstance(raw, dict):
        raise ValueError("coverage files missing")
    files = {}
    for original, value in raw.items():
        path = _normalize(original)
        if path in files:
            raise ValueError("ambiguous normalized coverage file aliases")
        files[path] = value
    return files


def _summary(value, path):
    summary = value.get("summary") if isinstance(value, dict) else None
    if not isinstance(summary, dict):
        raise ValueError("missing instrumented summary for " + path)
    keys = ("num_statements", "covered_lines", "num_branches",
            "covered_branches")
    for key in keys:
        count = summary.get(key)
        if type(count) is not int or count < 0:
            raise ValueError("invalid " + key + " for " + path)
    if (summary["covered_lines"] > summary["num_statements"] or
            summary["covered_branches"] > summary["num_branches"]):
        raise ValueError("coverage numerator exceeds eligible denominator")
    return summary


def _source_blob(path, root):
    relative = _normalize(path)
    target = root / relative
    if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("unavailable or unsafe production source: " + relative)
    raw = target.read_bytes()
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()


def compare(baseline, candidate, manifest, head_sha, source_root=None):
    if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
        raise ValueError("exact candidate PR source SHA required")
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise ValueError("invalid coverage inputs")
    a_meta, b_meta = baseline.get("meta", {}), candidate.get("meta", {})
    if (a_meta.get("branch_coverage") is not True or
            b_meta.get("branch_coverage") is not True or
            a_meta.get("version") != b_meta.get("version")):
        raise ValueError("instrumentation mode/version mismatch")
    if (manifest.get("schema") != "codepurple.w77.legacy12.breadth.v1" or
            manifest.get("base_repo") != "GBOGEB/ABACUS" or
            manifest.get("source_baseline_head") is None):
        raise ValueError("unqualified source/roster manifest")
    before, after = _files(baseline), _files(candidate)
    removed = sorted(set(before) - set(after))
    new = sorted(set(after) - set(before))
    mismatches = []
    counts = {"base_statements": 0, "new_statements": 0,
              "eligible_statements": 0, "base_branches": 0,
              "new_branches": 0, "eligible_branches": 0,
              "zero_before": 0, "zero_after": 0,
              "executable_before": 0, "executable_after": 0}
    for path in sorted(set(before) & set(after)):
        a, b = _summary(before[path], path), _summary(after[path], path)
        if ((a["num_statements"], a["num_branches"]) !=
                (b["num_statements"], b["num_branches"])):
            mismatches.append(path)
            continue
        counts["base_statements"] += a["covered_lines"]
        counts["new_statements"] += b["covered_lines"]
        counts["eligible_statements"] += a["num_statements"]
        counts["base_branches"] += a["covered_branches"]
        counts["new_branches"] += b["covered_branches"]
        counts["eligible_branches"] += a["num_branches"]
        for side, item in (("before", a), ("after", b)):
            if item["num_statements"]:
                counts["executable_" + side] += 1
                counts["zero_" + side] += int(item["covered_lines"] == 0)
    strict = not (removed or mismatches)
    roster = []
    seen = set()
    for item in manifest.get("targets", []):
        path = _normalize(item.get("path"))
        if path in seen:
            raise ValueError("duplicate pinned source target")
        seen.add(path)
        old = item.get("baseline", {})
        blob = item.get("git_blob_sha")
        if not isinstance(blob, str) or not SHA.fullmatch(blob):
            raise ValueError("source blob unqualified")
        if source_root is not None and _source_blob(path, Path(source_root)) != blob:
            raise ValueError("source identity mismatch at " + path)
        expected_s = old.get("statements", {})
        expected_b = old.get("branches", {})
        if (expected_s.get("covered") != 0 or expected_b.get("covered") != 0):
            raise ValueError("nonzero target inserted into baseline zero roster")
        first = before.get(path)
        last = after.get(path)
        if first is None or last is None:
            roster.append({"path": path, "status": "UNKNOWN_MISSING_SOURCE"})
            continue
        a, b = _summary(first, path), _summary(last, path)
        if ((a["num_statements"], a["num_branches"]) !=
                (expected_s.get("eligible"), expected_b.get("eligible")) or
                a["covered_lines"] != 0 or a["covered_branches"] != 0 or
                (b["num_statements"], b["num_branches"]) !=
                (a["num_statements"], a["num_branches"])):
            roster.append({"path": path, "status": "INCOMPARABLE"})
            continue
        roster.append({
            "path": path, "git_blob_sha": blob,
            "status": "RECOVERED" if b["covered_lines"] > 0 else "ZERO",
            "statements": {
                "base_covered": 0, "candidate_covered": b["covered_lines"],
                "eligible": b["num_statements"]},
            "branches": {
                "base_covered": 0, "candidate_covered": b["covered_branches"],
                "eligible": b["num_branches"]},
        })
    if len(roster) != 12:
        raise ValueError("pinned twelve-source roster incomplete")
    return {
        "schema": "codepurple.w77.zero-frontier-receipt.v1",
        "candidate_head_sha": head_sha,
        "baseline_head_sha": manifest["source_baseline_head"],
        "baseline_workflow_run": manifest.get("native_baseline_workflow_run_id"),
        "scope": "CROSS_HEAD_SAME_DENOMINATOR_DESCRIPTIVE_NOT_CAUSAL",
        "tool_version": a_meta["version"],
        "baseline_files": len(before),
        "candidate_files": len(after),
        "new_files_excluded": new,
        "removed_files": removed,
        "changed_denominator_files": mismatches,
        "global_cohort_comparable": strict,
        "matched": counts if strict else None,
        "global_zero_delta": (
            counts["zero_before"] - counts["zero_after"] if strict else None
        ),
        "target_roster": roster,
        "targeted_zero_recovered": sum(x["status"] == "RECOVERED" for x in roster),
        "targeted_incomparable_unknown": sum(
            x["status"] in ("INCOMPARABLE", "UNKNOWN_MISSING_SOURCE")
            for x in roster
        ),
        "merge_authorized": False,
        "security_waiver": False,
        "independent_approval": None,
        "accepted_root_closures": 0,
        "m1": "STRUCTURAL", "m2": "HOLD", "m3": "HOLD",
        "pca_bt": "NOT_ASSESSABLE", "worker_hours": None,
        "real_runner_capacity": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--head", required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    raw = [p.read_bytes() for p in (
        args.baseline, args.candidate, args.manifest)]
    data = compare(
        *[json.loads(value) for value in raw], args.head,
        source_root=args.root)
    data["input_sha256"] = {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in zip(
            ("baseline", "candidate", "manifest"), raw
        )
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "head": args.head,
        "targets_recovered": data["targeted_zero_recovered"],
        "matched_files": data["baseline_files"],
        "global_zero_delta": data["global_zero_delta"],
        "admission": "HOLD"
    }, sort_keys=True))
    if data["targeted_incomparable_unknown"]:
        raise SystemExit("target source/denominator unqualified: HOLD")
    if not data["global_cohort_comparable"]:
        raise SystemExit("global scope mismatch: HOLD")


if __name__ == "__main__":
    main()
