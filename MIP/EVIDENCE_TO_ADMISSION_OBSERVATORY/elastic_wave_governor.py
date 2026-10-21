"""CODE PURPLE W33: evidence-only elastic scaling, local stops and re-entry.

This is a deterministic policy evaluator. It NEVER dispatches runners, starts
Crew workers, changes rules, approves, merges or promotes roots. Missing runner
capacity and unqualified evidence are UNKNOWN rather than zero-cost success.

Pulses are source-changing engineering attempts, not repeated status polls.
Three zero-gain *transitions* require four distinct qualified pulses. One
coverage-target attainment may stop local coverage work without stopping other
families or the programme. A plateau below target causes a source pivot.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
EVENT_KINDS = {
    "CRITICAL_FIRST_RED", "COVERAGE_REGRESSION", "NEW_ELIGIBLE_FRONTIER",
    "GOVERNANCE_REPAIRED", "QUEUE_RECOVERED", "CONTRACT_CHANGED",
}
REOPEN_KINDS = {"CRITICAL_FIRST_RED", "COVERAGE_REGRESSION",
                "NEW_ELIGIBLE_FRONTIER", "CONTRACT_CHANGED"}


class GovernorError(ValueError):
    """Invalid evidence or control configuration; no new scaling authority."""


def integer(x, name, floor=0):
    if type(x) is not int or x < floor:
        raise GovernorError(f"{name} must be an integer >= {floor}")
    return x


def sha(x, name):
    if not isinstance(x, str) or not SHA40.fullmatch(x):
        raise GovernorError(f"{name}: exact 40-character SHA required")
    return x


def number(x, name, *, minimum=0.0, maximum=None):
    if type(x) not in (int, float) or not math.isfinite(x) or x < minimum:
        raise GovernorError(f"{name}: finite value >= {minimum} required")
    if maximum is not None and x > maximum:
        raise GovernorError(f"{name}: value exceeds {maximum}")
    return float(x)


def source_path_safe(value):
    """Conservative cross-platform lexical path lease; NOT filesystem proof."""
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("/")
        and "\\" not in value
        and ":" not in value
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
        and all(part not in ("", ".", "..") for part in value.split("/"))
    )


def source_path_overlap(left, right):
    """Casefold and use segment boundaries, never raw startswith."""
    left, right = left.casefold(), right.casefold()
    return (
        left == right
        or left.startswith(right + "/")
        or right.startswith(left + "/")
    )


def checked_history(history):
    """Return a comparable terminal cohort or explicit incomparability.

    Do not treat unknown or nonterminal observations as zero-coverage waves.
    Run, source, episode and artifact identities cannot be replayed.
    """
    if not isinstance(history, list):
        raise GovernorError("history must be an array")
    if not history:
        return {"qualified": False, "reason": "NO_COMPLETED_SOURCE_CHANGING_PULSE",
                "zero_gain_transitions": 0, "growth_transitions": 0}
    seen = {"run_id": set(), "source_sha": set(), "source_slice": set(),
            "artifact_sha256": set(), "wave": set()}
    cohort, config, eligible = None, None, None
    previous = None
    plateau = 0
    growth = 0
    for pulse in history:
        if not isinstance(pulse, dict):
            raise GovernorError("pulse must be object")
        integer(pulse.get("wave"), "wave", 1)
        integer(pulse.get("run_id"), "run_id", 1)
        sha(pulse.get("source_sha"), "source_sha")
        digest = pulse.get("artifact_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise GovernorError("artifact_sha256 missing or invalid")
        if not isinstance(pulse.get("source_slice"), str) or not pulse["source_slice"]:
            raise GovernorError("unique source_slice required")
        integer(pulse.get("covered"), "covered")
        integer(pulse.get("eligible"), "eligible", 1)
        if pulse["covered"] > pulse["eligible"]:
            raise GovernorError("covered exceeds eligible")
        if (pulse.get("terminal") is not True or pulse.get("native_receipts_valid") is not True
                or pulse.get("attempted_new_behavior") is not True
                or pulse.get("failed_tests") != 0):
            return {"qualified": False, "reason": "INCOMPLETE_OR_FAILED_NATIVE_PULSE",
                    "zero_gain_transitions": 0, "growth_transitions": 0}
        for key in seen:
            value = pulse[key]
            if value in seen[key]:
                raise GovernorError(f"replayed {key}: polling is not another wave")
            seen[key].add(value)
        if (not isinstance(pulse.get("cohort_id"), str) or not pulse["cohort_id"]
                or not isinstance(pulse.get("configuration_id"), str)
                or not pulse["configuration_id"]):
            raise GovernorError("cohort_id/configuration_id required")
        if previous is not None:
            if pulse["wave"] != previous["wave"] + 1:
                raise GovernorError("pulse wave IDs must be consecutive")
            if (pulse["cohort_id"], pulse["configuration_id"], pulse["eligible"]) != (cohort, config, eligible):
                return {"qualified": False, "reason": "COHORT_OR_CONFIG_DRIFT",
                        "zero_gain_transitions": 0, "growth_transitions": 0}
            delta = pulse["covered"] - previous["covered"]
            plateau = plateau + 1 if delta == 0 else 0
            growth = growth + 1 if delta > 0 else 0
        else:
            cohort, config, eligible = (pulse["cohort_id"], pulse["configuration_id"],
                                        pulse["eligible"])
        previous = pulse
    return {"qualified": True, "reason": "COMPARABLE_TERMINAL_PULSES",
            "zero_gain_transitions": plateau, "growth_transitions": growth,
            "last_run_id": history[-1]["run_id"],
            "last_source_sha": history[-1]["source_sha"],
            "last_covered": history[-1]["covered"], "last_eligible": eligible,
            "observations": len(history)}


def family_result(family):
    family_id = family.get("id")
    paths = family.get("paths")
    if not isinstance(family_id, str) or not family_id:
        raise GovernorError("family id required")
    if not isinstance(paths, list) or not paths or any(
        not source_path_safe(path) for path in paths
    ):
        raise GovernorError(f"{family_id}: invalid source path lease")
    for idx, path in enumerate(paths):
        if any(source_path_overlap(path, older) for older in paths[:idx]):
            raise GovernorError(
                f"{family_id}: overlapping source path leases within family"
            )
    eligible = integer(family.get("eligible"), f"{family_id}.eligible", 1)
    covered = integer(family.get("covered"), f"{family_id}.covered")
    if covered > eligible:
        raise GovernorError(f"{family_id}: covered exceeds eligible")
    target = number(family.get("target_percent"), "target_percent", minimum=0.01, maximum=100)
    sha(family.get("source_sha"), "family.source_sha")
    history = checked_history(family.get("history", []))
    actual = 100.0 * covered / eligible
    missing_to_target = max(0, math.ceil(target * eligible / 100 - 1e-12) - covered)
    first_reds = family.get("first_reds")
    if not isinstance(first_reds, list) or any(not isinstance(s, str) or not s for s in first_reds):
        raise GovernorError("first_reds must be explicit array, not UNKNOWN")
    if family.get("native_observed") is not True:
        state = "NATIVE_EVIDENCE_UNKNOWN"
    elif first_reds:
        state = "FIRST_RED_REPAIR"
    elif actual >= target:
        state = "LOCAL_COVERAGE_TARGET"
    elif history["qualified"] and history["zero_gain_transitions"] >= 3:
        state = "LOCAL_PLATEAU_PIVOT"
    elif history["reason"] == "COHORT_OR_CONFIG_DRIFT":
        state = "REBASELINE"
    elif history["reason"] == "INCOMPLETE_OR_FAILED_NATIVE_PULSE":
        state = "REPAIR_NATIVE_RECEIPTS"
    else:
        state = "EXPAND_BEHAVIORAL_TESTS"
    local_stop = state in {"LOCAL_COVERAGE_TARGET", "LOCAL_PLATEAU_PIVOT"}
    return {"id": family_id, "paths": paths, "state": state, "stop_local_coverage": local_stop,
            "target_percent": target, "covered": covered, "eligible": eligible,
            "covered_percent": round(actual, 6), "uncovered": eligible-covered,
            "covered_opportunities_needed_for_target": missing_to_target,
            "first_reds": first_reds, "pulse_evidence": history,
            "source_sha": family["source_sha"]}


def _events(events, seen_keys, family_ids):
    if not isinstance(events, list) or not isinstance(seen_keys, list):
        raise GovernorError("events and seen_event_keys must be arrays")
    if any(not isinstance(x, str) for x in seen_keys):
        raise GovernorError("seen_event_keys invalid")
    seen = set(seen_keys)
    consumed = set()
    actionable, suppressed, withheld = [], [], []
    for event in events:
        if not isinstance(event, dict):
            raise GovernorError("event must be object")
        kind, family = event.get("kind"), event.get("family")
        if kind not in EVENT_KINDS or family not in family_ids:
            withheld.append({"family": family, "reason": "UNKNOWN_TRIGGER_KIND_OR_FAMILY"})
            continue
        source = sha(event.get("source_sha"), "event.source_sha")
        fingerprint = event.get("fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            withheld.append({"family": family, "reason": "MISSING_CAUSAL_FINGERPRINT"})
            continue
        key = "|".join((family, kind, source, fingerprint))
        if key in seen or key in consumed:
            suppressed.append({"family": family, "kind": kind,
                               "reason": "REPLAYED_EVENT_NOT_A_NEW_WAVE", "key": key})
            continue
        if kind in {"NEW_ELIGIBLE_FRONTIER", "COVERAGE_REGRESSION"}:
            amount = event.get("verified_opportunity_delta")
            if type(amount) is not int or (kind == "NEW_ELIGIBLE_FRONTIER" and amount <= 0) or (
                kind == "COVERAGE_REGRESSION" and amount >= 0
            ):
                withheld.append({"family": family, "reason": "MISSING_SIGNED_MATCHED_EVIDENCE"})
                continue
        if event.get("terminal_exact_head_evidence") is not True:
            withheld.append({"family": family, "reason": "NOT_NATIVE_EXACT_HEAD_VERIFIED"})
            continue
        actionable.append({"family": family, "kind": kind, "key": key,
                           "reopens_local_coverage": kind in REOPEN_KINDS,
                           "next_pilot": "ONE_TARGETED_TESTFLIGHT_OR_READ_ONLY_SCOUT"})
        consumed.add(key)
    return actionable, suppressed, withheld


def _capacity(doc, results, actionable):
    cap = doc.get("capacity")
    if not isinstance(cap, dict):
        raise GovernorError("capacity object required")
    previous = integer(cap.get("previous_observation_lanes"), "previous_observation_lanes", 1)
    ceiling = integer(cap.get("maximum_observation_lanes"), "maximum_observation_lanes", 1)
    if previous > ceiling:
        raise GovernorError("previous lanes exceed ceiling")
    soft = number(cap.get("queue_soft_seconds"), "queue_soft_seconds", minimum=1)
    hard = number(cap.get("queue_hard_seconds"), "queue_hard_seconds", minimum=soft)
    queue = cap.get("queue_p95_seconds")
    queue_complete = cap.get("queue_population_complete") is True
    if queue is not None:
        queue = number(queue, "queue_p95_seconds")
    receipts = cap.get("evidence_yield")
    if receipts is not None:
        receipts = number(receipts, "evidence_yield", maximum=1)
    slots = cap.get("available_runner_slots")
    independent = cap.get("ready_disjoint_source_leases")
    owners = cap.get("source_owner_slots")
    if slots is not None:
        integer(slots, "available_runner_slots")
    if independent is not None:
        integer(independent, "ready_disjoint_source_leases")
    if owners is not None:
        integer(owners, "source_owner_slots")
    # Qualified growth must be from two independently committed positive
    # changes. Re-evaluating a source/run does not double the lane budget.
    histories = [r["pulse_evidence"] for r in results]
    current_identity = (cap.get("latest_terminal_run_id"), cap.get("latest_terminal_source_sha"))
    evidence_head_stable = cap.get("head_stable") is True
    queue_identity = (
        cap.get("queue_population_run_id"), cap.get("queue_population_source_sha")
    )
    queue_exact_head = queue_identity == current_identity
    fresh = [
        h for h, result in zip(histories, results)
        if result["state"] == "EXPAND_BEHAVIORAL_TESTS"
        and h["qualified"] and h.get("growth_transitions", 0) >= 2
        and (h.get("last_run_id"), h.get("last_source_sha")) == current_identity
    ]
    new_terminal = (
        type(current_identity[0]) is int and current_identity[0] > 0
        and isinstance(current_identity[1], str) and SHA40.fullmatch(current_identity[1])
        and current_identity != (
            cap.get("last_scaled_run_id"), cap.get("last_scaled_source_sha")
        )
    )
    if not evidence_head_stable:
        mode, observations, reason = "OBSERVE_ONLY", 1, "A_B_A_SOURCE_HEAD_UNVERIFIED"
    elif not queue_complete or queue is None or not queue_exact_head:
        mode, observations, reason = "OBSERVE_ONLY", 1, "QUEUE_POPULATION_UNKNOWN"
    elif queue > hard:
        mode, observations, reason = "THROTTLE", max(1, previous//2), "QUEUE_ABOVE_HARD_LIMIT"
    elif receipts != 1:
        mode, observations, reason = "THROTTLE", max(1, previous//2), "REQUIRED_EVIDENCE_YIELD_BELOW_100_PERCENT"
    elif queue > soft:
        mode, observations, reason = "HOLD_CAPACITY", previous, "QUEUE_ABOVE_SOFT_LIMIT"
    elif fresh and new_terminal:
        mode, observations, reason = "GEOMETRIC_SCALE", min(ceiling, previous*2), "TWO_COMPARABLE_POSITIVE_TRANSITIONS"
    else:
        mode, observations, reason = "HOLD_CAPACITY", previous, "NO_NEW_QUALIFIED_TWO_TRANSITION_GROWTH"
    observations = min(observations, ceiling)
    outstanding = cap.get("outstanding_native_jobs")
    if outstanding is not None:
        integer(outstanding, "outstanding_native_jobs")
    # No new runner sessions if available slots, source leases, or owner
    # capacity are missing. Unknown is not infinite free capacity.
    runner_lanes = 0
    if (queue_complete and queue is not None and queue <= hard and receipts == 1
            and slots is not None and independent is not None and owners is not None
            and outstanding is not None and outstanding == 0
            and evidence_head_stable and queue_exact_head):
        runner_lanes = min(observations, slots, independent, owners,
                           sum(r["state"] in {"EXPAND_BEHAVIORAL_TESTS", "FIRST_RED_REPAIR"}
                               for r in results))
        if actionable and any(a["kind"] == "QUEUE_RECOVERED" for a in actionable):
            runner_lanes = min(runner_lanes, 1)
    return {"state": mode, "reason": reason,
            "recommended_read_only_observation_lanes": observations,
            "proposed_native_runner_lanes": runner_lanes,
            "proposed_source_owner_write_lanes": min(runner_lanes, owners or 0),
            "read_only_ceiling": ceiling,
            "automatic_dispatch_permitted": False,
            "automated_merge_permitted": False,
            "unverified_queue_is_zero": False,
            "repeated_poll_scales_up": False,
            "source_head_stable": evidence_head_stable,
            "queue_bound_to_latest_terminal_head": queue_exact_head}


def _programme_stop(doc, results, artifact_census):
    end = doc.get("global_acceptance")
    if not isinstance(end, dict):
        raise GovernorError("global_acceptance object required")
    roots = end.get("accepted_roots_remaining")
    repos = end.get("repositories")
    verified = end.get("source_attested_repositories")
    artifacts = end.get("required_artifacts")
    valid = end.get("valid_artifacts")
    stable = end.get("independent_stable_pulses")
    gates = end.get("gates")
    # Explicit 0 root backlog is necessary but insufficient. A local
    # plateau below target never qualifies for global completion.
    statuses = {r["id"]: r["state"] for r in results}
    all_source_targets = bool(results) and all(
        r["state"] == "LOCAL_COVERAGE_TARGET" for r in results
    )
    numbers_valid = (
        type(roots) is int and roots == 0
        and type(repos) is int and repos > 0
        and type(verified) is int and verified == repos
        and type(artifacts) is int and artifacts > 0
        and type(valid) is int and valid == artifacts
        and type(stable) is int and stable >= 8
        and end.get("head_stable") is True
        and end.get("canonical_b0_exact_head") is True
    )
    governance = (isinstance(gates, dict) and all(
        gates.get(k) is True for k in
        ("branch_protection", "eligible_independent_review",
         "required_checks", "negative_red_canary", "security")
    ))
    stability = end.get("no_special_cause_variation") is True
    consumer_evidence = artifact_census.get("status") == "NATIVE_COMPLETE_CONSUMER_ATTESTED"
    complete = bool(all_source_targets and numbers_valid and governance
                    and stability and consumer_evidence)
    return {"state": "GLOBAL_CONTROL_ELIGIBLE" if complete else "CONTINUE_OR_HOLD",
            "stop_entire_program": complete, "all_source_targets": all_source_targets,
            "governance_qualified": bool(governance),
            "artifact_consumer_evidence_complete": consumer_evidence,
            "accepted_roots_remaining": roots if type(roots) is int else None,
            "repo_reach": {"verified": verified, "total": repos},
            "required_artifact_yield": (valid / artifacts if type(valid) is int
                                         and type(artifacts) is int and artifacts > 0 else None),
            "repeatability_observations": stable if type(stable) is int else None,
            "is_six_sigma_capability_proof": False,
            "no_automatic_authority_transfer": True,
            "family_statuses": statuses}


def artifact_type_census(doc):
    """Track artifact type breadth without mistaking uploads for federation.

    Native-local verification and downstream consumer acceptance are separate.
    Missing type lists remain UNKNOWN, not 100%.
    """
    rows = doc.get("artifact_types")
    if rows is None:
        return {"status": "ARTIFACT_TYPE_POPULATION_UNKNOWN",
                "native_expected": None, "native_verified": None,
                "native_yield": None, "consumer_attested_types": None}
    if not isinstance(rows, list) or not rows:
        raise GovernorError("artifact_types must be a nonempty list or null")
    seen = set()
    out = []
    for row in rows:
        if not isinstance(row, dict):
            raise GovernorError("artifact type must be an object")
        kind = row.get("kind")
        if not isinstance(kind, str) or not kind or kind in seen:
            raise GovernorError("artifact type names must be distinct and nonempty")
        seen.add(kind)
        expected = integer(row.get("expected"), f"{kind}.expected", 1)
        verified = integer(row.get("native_verified"), f"{kind}.native_verified")
        if verified > expected:
            raise GovernorError("artifact type verified exceeds denominator")
        if row.get("source_sha") != doc.get("snapshot_source_sha"):
            raise GovernorError("artifact type SHA mismatch")
        if row.get("consumer_attested") is not True and row.get("consumer_attested") is not False and row.get("consumer_attested") is not None:
            raise GovernorError("consumer attestation must be boolean or UNKNOWN")
        out.append({"kind": kind, "expected": expected,
                    "native_verified": verified, "consumer_attested": row.get("consumer_attested"),
                    "native_yield": round(verified / expected, 6)})
    total = sum(x["expected"] for x in out)
    verified = sum(x["native_verified"] for x in out)
    complete = total == verified
    consumer = all(x["consumer_attested"] is True for x in out)
    return {"status": "NATIVE_COMPLETE_CONSUMER_ATTESTED" if complete and consumer
            else "NATIVE_COMPLETE_CONSUMER_UNKNOWN" if complete
            else "NATIVE_INCOMPLETE", "types": out,
            "native_expected": total, "native_verified": verified,
            "native_yield": round(verified / total, 6),
            "consumer_attested_types": sum(x["consumer_attested"] is True for x in out),
            "consumer_attestation_complete": consumer,
            "global_federation_credit": None}


def evaluate(doc):
    if not isinstance(doc, dict) or doc.get("schema") != "codepurple.elastic_wave_input.v1":
        raise GovernorError("unsupported input schema")
    if doc.get("repository") != "GBOGEB/ABACUS":
        raise GovernorError("repository identity mismatch")
    sha(doc.get("snapshot_source_sha"), "snapshot_source_sha")
    families = doc.get("families")
    if not isinstance(families, list) or not families:
        raise GovernorError("nonempty families required")
    results = [family_result(f) for f in families]
    ids = [r["id"] for r in results]
    if len(set(ids)) != len(ids):
        raise GovernorError("duplicate source family")
    leases = []
    for result in results:
        for path in result["paths"]:
            for owner, older in leases:
                if source_path_overlap(path, older):
                    raise GovernorError(
                        "non-disjoint source path leases: "
                        f"{owner} vs {result['id']}"
                    )
            leases.append((result["id"], path))
    if any(f["source_sha"] != doc["snapshot_source_sha"] for f in results):
        raise GovernorError("mixed source SHA: no exact-head comparison")
    actionable, suppressed, withheld = _events(
        doc.get("events", []), doc.get("seen_event_keys", []), set(ids)
    )
    reopens = {e["family"] for e in actionable if e["reopens_local_coverage"]}
    for r in results:
        if r["id"] in reopens and r["stop_local_coverage"]:
            r["state"] = "LOCAL_RETRIGGER_PILOT"
            r["stop_local_coverage"] = False
    artifacts = artifact_type_census(doc)
    programme = _programme_stop(doc, results, artifacts)
    capacity = _capacity(doc, results, actionable)
    if programme["stop_entire_program"]:
        capacity["proposed_native_runner_lanes"] = 0
        capacity["proposed_source_owner_write_lanes"] = 0
    ranking = sorted(
        (r for r in results if not r["stop_local_coverage"]),
        key=lambda r: (
            r["state"] not in {"FIRST_RED_REPAIR", "LOCAL_RETRIGGER_PILOT"},
            -r["covered_opportunities_needed_for_target"],
            r["id"],
        ),
    )
    return {"schema": "codepurple.elastic_wave_decision.v1",
            "snapshot_source_sha": doc["snapshot_source_sha"],
            "families": results, "capacity": capacity, "programme": programme,
            "artifact_type_census": artifacts,
            "retrigger": {"actionable": actionable, "duplicate_suppressed": suppressed,
                          "withheld": withheld, "consume_only_after_actual_execution":
                          [r["key"] for r in actionable]},
            "ranked_next_source_families": [r["id"] for r in ranking],
            "next_pilot": ranking[0]["id"] if ranking else None,
            "explicit_stop_scope": "GLOBAL" if programme["stop_entire_program"]
                else "LOCAL_ONLY_OR_NONE",
            "governed_merge_admission": "HOLD",
            "formal_acceptance_claim": False,
            "forecast_type": "POLICY_TARGET_NOT_PROBABILISTIC",
            "control_method": "AIMD_WITH_HYSTERESIS_AND_IDEMPOTENT_RETRIGGERS",
            "caveat": "8 stable pulses plus negative canary is operational control, not a Six Sigma capability estimate"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"decision": result["capacity"]["state"],
                      "next_pilot": result["next_pilot"],
                      "runner_lanes": result["capacity"]["proposed_native_runner_lanes"],
                      "global_stop": result["programme"]["stop_entire_program"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
