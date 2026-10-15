"""Source-bound coverage growth and N+1 telemetry; never grants admission."""

from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "abacus.everred.spine.v1"
SHA = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def integer(value):
    return type(value) is int and value >= 0


def percentage(covered, eligible):
    return round(100 * covered / eligible, 4) if eligible else None


def _identity(value):
    require(isinstance(value, dict), "invalid source identity")
    require(isinstance(value.get("repository"), str), "missing repository")
    require(bool(value["repository"]), "empty repository")
    require(
        isinstance(value.get("sha"), str) and SHA.fullmatch(value["sha"]),
        "missing exact SHA",
    )
    require(integer(value.get("run_id")) and value["run_id"] > 0, "missing native run")
    require(
        integer(value.get("artifact_id")) and value["artifact_id"] > 0,
        "missing artifact ID",
    )
    for key in ("artifact_sha256", "workflow_sha256", "config_sha256"):
        require(
            isinstance(value.get(key), str) and DIGEST.fullmatch(value[key]),
            "invalid identity: " + key,
        )


def _module(path, item):
    require(isinstance(item, dict), "invalid coverage file")
    summary = item.get("summary")
    require(isinstance(summary, dict), "missing module coverage summary")
    names = ("num_statements", "missing_lines", "num_branches", "missing_branches")
    require(
        all(integer(summary.get(k)) for k in names), "invalid module coverage counts"
    )
    statements = summary["num_statements"]
    missing_lines = summary["missing_lines"]
    branches = summary["num_branches"]
    missing_branches = summary["missing_branches"]
    require(
        statements > 0 and missing_lines <= statements, "invalid eligible statements"
    )
    require(missing_branches <= branches, "invalid eligible branches")
    return {
        "path": path,
        "statements": {
            "covered": statements - missing_lines,
            "eligible": statements,
        },
        "branches": {
            "covered": branches - missing_branches,
            "eligible": branches,
        },
    }


def coverage_snapshot(raw, receipt, identity):
    """Validate producer bytes and independent per-module denominators."""
    _identity(identity)
    require(
        isinstance(raw, dict) and isinstance(receipt, dict),
        "coverage receipt must be an object",
    )
    require(
        receipt.get("schema") == "bandit.coverage.receipt.v1",
        "unrecognized coverage contract",
    )
    require(
        receipt.get("exact_head_sha") == identity["sha"],
        "coverage head differs from native run",
    )
    require(
        str(receipt.get("producer_run_id")) == str(identity["run_id"]),
        "coverage run mismatch",
    )
    require(
        all(integer(receipt.get(k)) for k in ("tests", "failures", "errors")),
        "JUnit counters missing",
    )
    require(
        receipt["tests"] > 0 and receipt["failures"] == 0 and receipt["errors"] == 0,
        "failing or empty JUnit evidence",
    )
    scope = receipt.get("source_scope")
    require(isinstance(scope, list) and scope, "missing coverage source scope")
    require(
        all(
            isinstance(p, str)
            and p
            and not p.startswith("/")
            and ".." not in p.split("/")
            for p in scope
        ),
        "unsafe source scope",
    )
    require(scope == sorted(set(scope)), "source scope not canonical")
    files = raw.get("files")
    meta = raw.get("meta")
    require(
        isinstance(files, dict) and isinstance(meta, dict),
        "missing Coverage.py files or metadata",
    )
    version = meta.get("version")
    require(isinstance(version, str) and version, "missing instrumentor version")
    normalized = {}
    for path, item in files.items():
        require(isinstance(path, str), "invalid coverage path")
        key = path.replace("\\", "/").removeprefix("./")
        require(key not in normalized, "duplicate normalized coverage path")
        normalized[key] = item
    require(all(path in normalized for path in scope), "source-matched module absent")
    modules = [_module(path, normalized[path]) for path in scope]
    totals = {
        family: {
            kind: sum(m[family][kind] for m in modules)
            for kind in ("covered", "eligible")
        }
        for family in ("statements", "branches")
    }
    advertised = receipt.get("selected_modules_totals")
    require(isinstance(advertised, dict), "missing producer totals")
    for family, prefix in (("statements", "lines"), ("branches", "branches")):
        for kind in ("covered", "eligible"):
            name = kind + "_" + prefix
            require(
                advertised.get(name) == totals[family][kind],
                "producer totals conflict with raw coverage",
            )
    return {
        "schema": SCHEMA + ".coverage",
        "source": dict(identity),
        "scope": scope,
        "tool_version": version,
        "tests_executed": receipt["tests"],
        "modules": modules,
        "totals": totals,
        "state": "MEASURED_SOURCE_BOUND_NOT_ADMISSION",
        "changed_line_coverage": None,
        "old_debt_resolved": None,
    }


def compare_coverage(before, after, *, goal_pct=90):
    """Report changing denominator without inventing old-debt closure."""
    for item in (before, after):
        require(
            isinstance(item, dict) and item.get("schema") == SCHEMA + ".coverage",
            "invalid coverage snapshot",
        )
        _identity(item.get("source"))
    require(
        type(goal_pct) in (int, float) and 0 < goal_pct <= 100, "invalid coverage goal"
    )
    a, b = before["source"], after["source"]
    require(a["repository"] == b["repository"], "cross-repository coverage")
    scope_equal = before["scope"] == after["scope"]
    profile_equal = (
        scope_equal
        and before["tool_version"] == after["tool_version"]
        and a["workflow_sha256"] == b["workflow_sha256"]
        and a["config_sha256"] == b["config_sha256"]
    )
    families = {}
    for family in ("statements", "branches"):
        old, new = before["totals"][family], after["totals"][family]
        for record in (old, new):
            require(
                integer(record.get("covered"))
                and integer(record.get("eligible"))
                and record["covered"] <= record["eligible"],
                "invalid coverage family totals",
            )
        eligible_delta = new["eligible"] - old["eligible"]
        covered_delta = new["covered"] - old["covered"]
        old_rate = percentage(old["covered"], old["eligible"])
        new_rate = percentage(new["covered"], new["eligible"])
        required = (
            max(0, int(-(-goal_pct * new["eligible"] // 100)) - new["covered"])
            if new["eligible"]
            else None
        )
        families[family] = {
            "before": dict(old),
            "after": dict(new),
            "eligible_net_delta": eligible_delta,
            "covered_net_delta": covered_delta,
            "uncovered_net_delta": eligible_delta - covered_delta,
            "before_pct": old_rate,
            "after_pct": new_rate,
            "delta_percentage_points": (
                round(new_rate - old_rate, 4)
                if old_rate is not None and new_rate is not None
                else None
            ),
            "additional_covered_for_goal": required,
            "goal_pct": goal_pct,
            "new_source_obligations": None,
            "retired_source_obligations": None,
            "previously_uncovered_now_covered": None,
        }
    same_sha = a["sha"] == b["sha"]
    same_result = all(
        families[key]["eligible_net_delta"] == 0
        and families[key]["covered_net_delta"] == 0
        for key in families
    )
    if not profile_equal:
        status = "PROFILE_CHANGED_DESCRIPTIVE_ONLY"
    elif same_sha and same_result:
        status = "SAME_SOURCE_METRIC_RECONFIRMED"
    elif same_sha:
        status = "SAME_SOURCE_METRIC_DRIFT"
    elif any(x["eligible_net_delta"] != 0 for x in families.values()):
        status = "SOURCE_DENOMINATOR_EVOLVED"
    else:
        status = "SOURCE_DENOMINATOR_UNCHANGED"
    return {
        "schema": SCHEMA + ".coverage-delta",
        "status": status,
        "profile_comparable": profile_equal,
        "before_sha": a["sha"],
        "after_sha": b["sha"],
        "families": families,
        "causal_coverage_gain_credited": False,
        "exact_arc_mapping_verified": False,
        "admission": "HOLD",
    }


def ldab_snapshot(report, repository, head_sha, *, artifact_sha256):
    """Keep a discovery census separate from authenticated runtime sessions."""
    require(isinstance(report, dict), "LDAB summary must be an object")
    require(
        isinstance(artifact_sha256, str) and DIGEST.fullmatch(artifact_sha256),
        "missing LDAB artifact hash",
    )
    ldab = report.get("ldab_telemetry")
    require(
        isinstance(ldab, dict) and ldab.get("schema") == "mip.ldab.telemetry.v1",
        "unrecognized LDAB producer",
    )
    require(
        report.get("repository") == repository
        and report.get("head_sha") == head_sha
        and ldab.get("source_sha") == head_sha
        and ldab.get("repository") == repository,
        "stale or mismatched LDAB evidence",
    )
    require(report.get("verification") == "PASS", "LDAB producer not verified")
    source = ldab.get("source_census")
    runtime = ldab.get("runtime")
    require(
        isinstance(source, dict) and isinstance(runtime, dict), "LDAB surfaces missing"
    )
    root = source.get("root")
    require(
        isinstance(root, dict)
        and integer(root.get("candidate_file_count"))
        and root.get("inventory_complete") is True
        and root.get("evidence_level") == "SOURCE_DISCOVERY_ONLY",
        "invalid root LDAB discovery census",
    )
    require(
        runtime.get("abacus_native_debug_sessions") is None
        and runtime.get("authenticated_port_leases") is None
        and runtime.get("ldab_verified_repairs") is None,
        "source discovery cannot claim runtime proof",
    )
    return {
        "schema": SCHEMA + ".ldab",
        "repository": repository,
        "source_sha": head_sha,
        "artifact_sha256": artifact_sha256,
        "root_candidate_files": root["candidate_file_count"],
        "nested_candidate_files": (
            source.get("nested", {}).get("candidate_file_count")
            if isinstance(source.get("nested"), dict)
            else None
        ),
        "native_debug_sessions": None,
        "authenticated_port_leases": None,
        "verified_repairs": None,
        "state": "SOURCE_DISCOVERY_VERIFIED_RUNTIME_UNKNOWN",
    }


def _material_producer(producer):
    """Strip volatile receipt IDs, never convert missing evidence to zero."""
    if not isinstance(producer, dict):
        return {"state": "UNKNOWN_PRODUCER"}
    state = producer.get("state")
    if state == "MEASURED_SOURCE_BOUND_NOT_ADMISSION":
        binding = producer.get("source") or {}
        return {
            "state": state,
            "source_sha": binding.get("sha"),
            "workflow_sha256": binding.get("workflow_sha256"),
            "config_sha256": binding.get("config_sha256"),
            "tool_version": producer.get("tool_version"),
            "scope": producer.get("scope"),
            "totals": producer.get("totals"),
            "modules": producer.get("modules"),
        }
    if state == "SOURCE_DISCOVERY_VERIFIED_RUNTIME_UNKNOWN":
        return {
            k: producer.get(k)
            for k in (
                "state",
                "source_sha",
                "root_candidate_files",
                "nested_candidate_files",
                "native_debug_sessions",
                "authenticated_port_leases",
                "verified_repairs",
            )
        }
    return {
        "state": state,
        "source_sha": producer.get("source_sha"),
        "reason": producer.get("reason"),
    }


def _material_ci(census):
    """Compare latest observed conclusion by workflow, not volatile run IDs."""
    require(isinstance(census, dict), "invalid workflow census")
    rows = census.get("matched_runs")
    require(isinstance(rows, list), "native run window missing")
    latest = {}
    for row in rows:
        require(isinstance(row, dict), "invalid native workflow record")
        name, event = row.get("name"), row.get("event")
        require(isinstance(name, str) and name, "missing workflow identity")
        if name == "EVERRED V3 Governed Control Plane":
            continue  # A new observation must not alter its own comparison.
        require(isinstance(event, str), "missing workflow event")
        key = (name, event)
        if key not in latest:  # Native producer enumerates newest first.
            latest[key] = {
                "workflow": name,
                "event": event,
                "status": row.get("status"),
                "conclusion": row.get("conclusion"),
            }
    return {
        "window_complete": census.get("current_window_complete"),
        "workflow_states": [latest[k] for k in sorted(latest)],
    }


def _material_state(pulse):
    """Logical exact-head snapshot; excludes new run/attempt/ZIP identities."""
    require(
        isinstance(pulse, dict) and pulse.get("schema") == SCHEMA,
        "invalid spine snapshot",
    )
    items = pulse.get("observations", [])
    require(isinstance(items, list), "observations must be a list")
    observations = []
    for observation in items:
        require(isinstance(observation, dict), "invalid observation")
        if "ci" in observation:
            producers = observation.get("producers", {})
            require(isinstance(producers, dict), "invalid producer observations")
            observations.append(
                {
                    "pr_number": observation.get("pr_number"),
                    "source_sha": observation.get("source_sha"),
                    "ci": _material_ci(observation["ci"]),
                    "coverage": _material_producer(producers.get("coverage")),
                    "ldab": _material_producer(producers.get("ldab")),
                }
            )
        else:
            observations.append({k: v for k, v in observation.items() if k != "id"})
    return {
        "schema": SCHEMA,
        "repository": pulse.get("repository"),
        "main_sha": pulse.get("main_sha"),
        "active_heads": pulse.get("active_heads"),
        "inventory_complete": pulse.get("inventory_complete"),
        "history_census_complete": pulse.get("history_census_complete"),
        "run_window_scope": pulse.get("run_window_scope"),
        "observations": observations,
    }


def _sha256_object(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def state_fingerprint(pulse):
    """Material observed state, not workflow-run self-observation churn."""
    return _sha256_object(_material_state(pulse))


def receipt_fingerprint(pulse):
    """Separate digest tracks new run/artifact evidence even at a stable N."""
    require(isinstance(pulse, dict), "invalid receipt input")
    return _sha256_object(
        {
            k: v
            for k, v in pulse.items()
            if k
            not in (
                "observed_at",
                "comparison",
                "state_digest",
                "coverage_transitions",
            )
        }
    )


def compare_pulses(before, after):
    require(
        isinstance(before, dict) and before.get("schema") == SCHEMA,
        "invalid previous spine",
    )
    require(
        isinstance(after, dict) and after.get("schema") == SCHEMA,
        "invalid current spine",
    )
    require(
        before.get("repository") == after.get("repository"), "spine repository mismatch"
    )
    require(
        before.get("inventory_complete") is True
        and after.get("inventory_complete") is True,
        "cannot assert stable with incomplete inventory",
    )
    old_hash, new_hash = state_fingerprint(before), state_fingerprint(after)
    heads_match = before.get("main_sha") == after.get("main_sha") and (
        before.get("active_heads") == after.get("active_heads")
    )
    if heads_match and old_hash == new_hash:
        state = "N_PLUS_1_EQUALS_N_OBSERVED_STATE"
    elif heads_match:
        state = "SAME_HEADS_EVIDENCE_CHANGED"
    else:
        state = "SOURCE_REVISION_OR_PR_SET_CHANGED"
    return {
        "state": state,
        "old_digest": old_hash,
        "new_digest": new_hash,
        "source_heads_identical": heads_match,
        "material_state_changed": old_hash != new_hash,
        "new_evidence_receipts": (
            receipt_fingerprint(before) != receipt_fingerprint(after)
        ),
        "stability_scope": "CURRENT_EXACT_HEAD_LATEST_100_RUNS_PER_HEAD",
        "full_history_claim": False,
        "unknowns_resolved_implicitly": False,
        "merge_authorized": False,
    }
