"""Coverage obligations across revisions: old-debt gain != changing denominator.

Credits a formerly missed line/arc only for a source file with the exact
same Git blob, compatible instruments and a matching obligation identity.
Changed source remains unattributed until an independent semantic map exists.
"""

from __future__ import annotations

import hashlib
import json
import re

SHA = re.compile(r"^[0-9a-f]{40}$")
HEX = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "abacus.everred.coverage-obligations.v1"
PROFILE = (
    "tool_version",
    "config_digest",
    "test_selection",
    "exclusions",
    "instrumentation",
)
FAMILIES = ("statements", "branches")


def demand(ok, reason):
    if not ok:
        raise ValueError(reason)


def valid_path(path):
    demand(isinstance(path, str) and bool(path), "missing coverage path")
    value = path.replace("\\", "/")
    demand(
        not value.startswith("/") and not re.match(r"^[a-zA-Z]:", value),
        "absolute coverage path prohibited",
    )
    parts = value.split("/")
    demand(all(x and x not in (".", "..") for x in parts), "unsafe coverage path")
    return "/".join(parts)


def _ints(items, field, *, positive=True):
    demand(isinstance(items, list), "invalid " + field)
    result = set()
    for value in items:
        demand(type(value) is int, "noninteger " + field)
        demand(value >= 1 if positive else True, "invalid " + field)
        demand(value not in result, "duplicate " + field)
        result.add(value)
    return result


def _arcs(items, field):
    demand(isinstance(items, list), "invalid " + field)
    result = set()
    for pair in items:
        demand(isinstance(pair, list) and len(pair) == 2, "invalid arc shape")
        a, b = pair
        demand(type(a) is int and type(b) is int, "noninteger arc")
        demand((a, b) not in result, "duplicate arc")
        result.add((a, b))
    return result


def _file(raw, blob):
    demand(isinstance(raw, dict), "coverage file must be object")
    demand(isinstance(blob, str) and SHA.fullmatch(blob), "Git blob ID missing")
    summary = raw.get("summary")
    demand(isinstance(summary, dict), "missing file coverage summary")
    executed_lines = _ints(raw.get("executed_lines"), "executed_lines")
    missing_lines = _ints(raw.get("missing_lines"), "missing_lines")
    executed_arcs = _arcs(raw.get("executed_branches"), "executed_branches")
    missing_arcs = _arcs(raw.get("missing_branches"), "missing_branches")
    demand(not (executed_lines & missing_lines), "contradictory statement coverage")
    demand(not (executed_arcs & missing_arcs), "contradictory arc coverage")
    demand(
        summary.get("num_statements") == len(executed_lines) + len(missing_lines)
        and type(summary.get("num_statements")) is int,
        "statement denominator mismatch",
    )
    demand(
        summary.get("num_branches") == len(executed_arcs) + len(missing_arcs)
        and type(summary.get("num_branches")) is int,
        "branch denominator mismatch",
    )
    return {
        "git_blob_sha": blob,
        "statements": {
            "executed": sorted(executed_lines),
            "missing": sorted(missing_lines),
        },
        "branches": {
            "executed": [list(x) for x in sorted(executed_arcs)],
            "missing": [list(x) for x in sorted(missing_arcs)],
        },
    }


def snapshot(report, manifest):
    demand(
        isinstance(report, dict) and isinstance(manifest, dict),
        "invalid snapshot inputs",
    )
    demand(manifest.get("schema") == SCHEMA + ".manifest", "bad manifest schema")
    repo, sha = manifest.get("repository"), manifest.get("source_sha")
    demand(isinstance(repo, str) and "/" in repo, "invalid repository")
    demand(isinstance(sha, str) and SHA.fullmatch(sha), "invalid source SHA")
    for field in ("run_id", "job_id"):
        value = manifest.get(field)
        demand(type(value) is int and value > 0, "invalid " + field)
    digest = manifest.get("coverage_artifact_sha256")
    demand(isinstance(digest, str) and HEX.fullmatch(digest), "invalid coverage digest")
    profile = manifest.get("profile")
    demand(isinstance(profile, dict), "missing coverage comparability profile")
    demand(
        all(isinstance(profile.get(k), str) and profile[k] for k in PROFILE),
        "incomplete coverage profile",
    )
    demand(profile["instrumentation"] == "branch", "branch mode required")
    files = report.get("files")
    blobs = manifest.get("file_blobs")
    demand(
        isinstance(files, dict) and isinstance(blobs, dict), "coverage files missing"
    )
    demand(bool(files), "empty coverage scope")
    demand(isinstance(report.get("meta"), dict), "missing Coverage.py metadata")
    demand(
        report["meta"].get("version") == profile["tool_version"],
        "instrumentor version mismatch",
    )
    normalized_files = {valid_path(p): v for p, v in files.items()}
    normalized_blobs = {valid_path(p): v for p, v in blobs.items()}
    demand(
        len(normalized_files) == len(files) and len(normalized_blobs) == len(blobs),
        "duplicate normalized path",
    )
    demand(set(normalized_files) == set(normalized_blobs), "source blob scope mismatch")
    selected = {
        p: _file(normalized_files[p], normalized_blobs[p])
        for p in sorted(normalized_files)
    }
    totals = {}
    for family in FAMILIES:
        totals[family] = {
            "covered": sum(len(x[family]["executed"]) for x in selected.values()),
            "eligible": sum(
                len(x[family]["executed"]) + len(x[family]["missing"])
                for x in selected.values()
            ),
        }
    return {
        "schema": SCHEMA + ".snapshot",
        "source": {
            "repository": repo,
            "sha": sha,
            "run_id": manifest["run_id"],
            "job_id": manifest["job_id"],
            "coverage_artifact_sha256": digest,
        },
        "profile": {k: profile[k] for k in PROFILE},
        "files": selected,
        "totals": totals,
        "native_artifact_bytes_authenticated": False,
        "semantic_source_mapping_verified": False,
        "merge_authorized": False,
    }


def _set(family, data, key):
    values = data[family][key]
    return {tuple(v) if isinstance(v, list) else v for v in values}


def compare(before, after):
    for snap in (before, after):
        demand(
            isinstance(snap, dict) and snap.get("schema") == SCHEMA + ".snapshot",
            "invalid obligation snapshot",
        )
    l, r = before["source"], after["source"]
    demand(l["repository"] == r["repository"], "cross-repository comparison")
    profile_ok = before["profile"] == after["profile"]
    all_left, all_right = before["files"], after["files"]
    intersection = set(all_left) & set(all_right)
    new_files = set(all_right) - set(all_left)
    retired_files = set(all_left) - set(all_right)
    unchanged = {
        path
        for path in intersection
        if all_left[path]["git_blob_sha"] == all_right[path]["git_blob_sha"]
    }
    modified = intersection - unchanged
    families = {}
    for family in FAMILIES:
        old = before["totals"][family]
        new = after["totals"][family]
        gain, regress, new_on_stable, retired_on_stable = set(), set(), set(), set()
        if profile_ok:
            for path in sorted(unchanged):
                previous = all_left[path]
                current = all_right[path]
                old_eligible = _set(family, previous, "executed") | _set(
                    family, previous, "missing"
                )
                new_eligible = _set(family, current, "executed") | _set(
                    family, current, "missing"
                )
                if old_eligible != new_eligible:
                    raise ValueError(
                        "unchanged blob has inconsistent eligible obligations"
                    )
                for obligation in _set(family, previous, "missing") & _set(
                    family, current, "executed"
                ):
                    gain.add((path, obligation))
                for obligation in _set(family, previous, "executed") & _set(
                    family, current, "missing"
                ):
                    regress.add((path, obligation))
        percent_old = (
            round(100 * old["covered"] / old["eligible"], 4)
            if old["eligible"]
            else None
        )
        percent_new = (
            round(100 * new["covered"] / new["eligible"], 4)
            if new["eligible"]
            else None
        )
        stable_eligible = (
            sum(
                len(_set(family, all_left[path], "executed"))
                + len(_set(family, all_left[path], "missing"))
                for path in unchanged
            )
            if profile_ok
            else None
        )
        families[family] = {
            "source_matched_eligible_obligations": stable_eligible,
            "source_matched_scope_percent_before": (
                round(100 * stable_eligible / old["eligible"], 4)
                if stable_eligible is not None and old["eligible"]
                else None
            ),
            "source_matched_scope_percent_after": (
                round(100 * stable_eligible / new["eligible"], 4)
                if stable_eligible is not None and new["eligible"]
                else None
            ),
            "eligible_before": old["eligible"],
            "eligible_after": new["eligible"],
            "eligible_net_delta": new["eligible"] - old["eligible"],
            "covered_before": old["covered"],
            "covered_after": new["covered"],
            "covered_net_delta": new["covered"] - old["covered"],
            "uncovered_before": old["eligible"] - old["covered"],
            "uncovered_after": new["eligible"] - new["covered"],
            "rate_before": percent_old,
            "rate_after": percent_new,
            "rate_delta_points_descriptive": (
                round(percent_new - percent_old, 4)
                if percent_old is not None and percent_new is not None
                else None
            ),
            "previously_uncovered_now_covered_verified": (
                len(gain) if profile_ok else None
            ),
            "previously_covered_now_uncovered_verified": (
                len(regress) if profile_ok else None
            ),
            "true_gain_obligation_keys": [
                {"path": path, "obligation": list(ob) if isinstance(ob, tuple) else ob}
                for path, ob in sorted(gain)
            ],
            "regression_obligation_keys": [
                {"path": path, "obligation": list(ob) if isinstance(ob, tuple) else ob}
                for path, ob in sorted(regress)
            ],
            "old_debt_credit_on_changed_blobs": None,
        }
    return {
        "schema": SCHEMA + ".delta",
        "repository": l["repository"],
        "before_sha": l["sha"],
        "after_sha": r["sha"],
        "profile_compatible": profile_ok,
        "source_scope_equal": set(all_left) == set(all_right),
        "unchanged_blob_files": sorted(unchanged),
        "changed_blob_files": sorted(modified),
        "added_files": sorted(new_files),
        "retired_files": sorted(retired_files),
        "families": families,
        "status": (
            "PROFILE_CHANGED_NO_OLD_DEBT_CREDIT"
            if not profile_ok
            else (
                "PARTIALLY_ATTRIBUTABLE"
                if modified or new_files or retired_files
                else "FULLY_STABLE_SOURCE_BLOB_MAPPING"
            )
        ),
        "source_code_churn_semantically_resolved": False,
        "independent_native_receipt_verification": False,
        "security_waiver": False,
        "authority_transfer": False,
        "merge_admission": "HOLD",
    }


def source_digest(blob):
    demand(isinstance(blob, bytes), "artifact must be bytes")
    return hashlib.sha256(blob).hexdigest()


def parse_artifact(raw_bytes, manifest):
    """Verify exact supplied bytes; native origin must be proven separately."""
    demand(
        source_digest(raw_bytes) == manifest.get("coverage_artifact_sha256"),
        "coverage ZIP member digest mismatch",
    )
    return snapshot(json.loads(raw_bytes), manifest)
