"""CBD! workflow manifestation -> candidate family / disjoint repair waves.

Observational only. Workflow names are *symptoms*, never causal root proof.
No runner launch, security waiver, authoritative BD mutation or main admission.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

FAMILIES = {
    "CI Workflow Governance": ("GOVERNANCE_POLICY", "ci/governance/", "P0"),
    "a10-guard": ("A10_SECURITY_REVIEW", "ci/governance/", "P0"),
    "Bandit Disjoint Census": ("BANDIT_CENSUS", "tools/everred_v3/", "P0"),
    "CI/CD Test Suite": ("INTEGRATED_TEST_SUITE", "tests/", "P1"),
    "ABACUS v032 - CI/CD Pipeline": ("LEGACY_PIPELINE", "ci/", "P1"),
    "CI - ABACUS Matrix": ("MATRIX_COMPATIBILITY", "DMAIC_V3/", "P1"),
    "Validate Docs (Markdown/YAML/JSON)": ("DOCS_LINT", "docs/", "P2"),
    "EVERRED V3 Governed Control Plane": ("EVERRED_CONTROL", "tools/everred_v3/", "P1"),
    "DOW + Recursive DMAIC - Enhanced CI": ("DOW_TESTS", "tests/", "P1"),
    "DMAIC V3 Test Suite - Continuous Integration": (
        "DMAIC_TESTS",
        "DMAIC_V3/tests/",
        "P1",
    ),
    "DMAIC V3 Enterprise CI": ("ENTERPRISE_MATRIX", "DMAIC_V3/", "P1"),
}
P0 = {"GOVERNANCE_POLICY", "A10_SECURITY_REVIEW", "BANDIT_CENSUS"}
FAMILIES.update(
    {
        "Semgrep": ("SEMGREP_SECURITY", "UNOWNED", "P0"),
        "OSV-Scanner": ("OSV_SECURITY", "UNOWNED", "P0"),
        "DMAIC V3 Bridge Integration - Test System": (
            "DMAIC_BRIDGE",
            "DMAIC_V3/core/",
            "P1",
        ),
    }
)


def sha256(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def _valid_sha(value):
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value)
    )


def validate(d):
    """Reject fabricated source identities, attempts, gates, and cohort totals."""
    if not isinstance(d, dict):
        raise ValueError("source object")
    if (
        d.get("schema") != "cbd.pr_workflow_observations.v1"
        or d.get("repository") != "GBOGEB/ABACUS"
    ):
        raise ValueError("source schema or repository")
    expected_authority = {
        "security_waiver": False,
        "authority_transfer": False,
        "merge_admission": "HOLD",
        "dispatch": "STAGED_NOT_LAUNCHED",
    }
    if d.get("authority") != expected_authority:
        raise ValueError("authority")
    rows = d.get("observations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty observations")

    manifest = d.get("sampled_pr_heads")
    sampled = None
    if manifest is not None:
        if not isinstance(manifest, list) or not manifest:
            raise ValueError("empty sampled PR head manifest")
        sampled = {}
        for head in manifest:
            if not isinstance(head, dict):
                raise ValueError("invalid sampled PR head")
            pr = head.get("pr")
            if type(pr) is not int or pr <= 0 or not _valid_sha(head.get("sha")):
                raise ValueError("invalid sampled PR head identity")
            total = head.get("workflow_associations_seen")
            failures = head.get("failed_associations_seen")
            if (
                type(total) is not int
                or type(failures) is not int
                or total < 0
                or failures < 0
                or failures > total
            ):
                raise ValueError("invalid sampled PR denominator")
            if pr in sampled:
                raise ValueError("duplicate sampled PR head")
            sampled[pr] = head

    seen = set()
    run_identity = {}
    immutable_run_identity = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid observation")
        pr = row.get("pr")
        attempt = row.get("attempt")
        run_id = row.get("run_id")
        if (
            type(pr) is not int
            or pr <= 0
            or not _valid_sha(row.get("sha"))
            or type(run_id) is not int
            or run_id <= 0
            or (attempt is not None and (type(attempt) is not int or attempt <= 0))
        ):
            raise ValueError("invalid source/run identity")
        if not isinstance(row.get("workflow"), str) or not row["workflow"].strip():
            raise ValueError("workflow")
        if row.get("conclusion") not in ("success", "failure", "cancelled", None):
            raise ValueError("conclusion")
        if row.get("url") != (
            f"https://github.com/GBOGEB/ABACUS/actions/runs/{run_id}"
        ):
            raise ValueError("source URL")
        if sampled is not None and (
            pr not in sampled or sampled[pr]["sha"] != row["sha"]
        ):
            raise ValueError("observation does not match sampled PR head")
        key = (pr, run_id, attempt)
        if key in seen:
            raise ValueError("duplicate PR/run/attempt observation")
        seen.add(key)
        identity = (row["sha"], row["workflow"], row["conclusion"])
        run_key = (run_id, attempt)
        if run_key in run_identity and run_identity[run_key] != identity:
            raise ValueError("conflicting repeated native run identity")
        run_identity[run_key] = identity
        # A rerun can change attempt/conclusion, never the GitHub run's
        # source SHA or workflow. PR aliases for the same run remain allowed.
        immutable = (row["sha"], row["workflow"])
        if (
            run_id in immutable_run_identity
            and immutable_run_identity[run_id] != immutable
        ):
            raise ValueError("conflicting native run provenance across attempts")
        immutable_run_identity[run_id] = immutable

    if sampled is not None:
        actual = defaultdict(int)
        for row in rows:
            if row["conclusion"] == "failure":
                actual[row["pr"]] += 1
        for pr, head in sampled.items():
            if actual[pr] != head["failed_associations_seen"]:
                raise ValueError("failed-association denominator mismatch")
    return d


def combine_sources(sources):
    """Combine disjoint PR-head snapshots without claiming fleet completeness."""
    if not isinstance(sources, list) or not sources:
        raise ValueError("nonempty source list required")
    for source in sources:
        validate(source)
        if "sampled_pr_heads" not in source:
            raise ValueError("multi-source projection needs PR head manifests")
    merged = {
        "schema": "cbd.pr_workflow_observations.v1",
        "repository": sources[0]["repository"],
        "sampling": "NONATOMIC_DISJOINT_FIRST_PAGE_PR_HEAD_COHORTS",
        "authority": sources[0]["authority"],
        "sampled_pr_heads": [],
        "observations": [],
    }
    for source in sources:
        if (
            source["repository"] != merged["repository"]
            or source["authority"] != merged["authority"]
        ):
            raise ValueError("mixed source authority")
        merged["sampled_pr_heads"].extend(source["sampled_pr_heads"])
        merged["observations"].extend(source["observations"])
    return validate(merged)


def produce(d):
    """Read-only candidate-family DAG, with UNKNOWN attempt and coverage facts."""
    validate(d)
    families = {}
    counts = {"success": 0, "failure": 0, "cancelled": 0, "nonterminal": 0}
    failed_prs = set()
    observed_prs = set()
    unknown_attempts = 0
    distinct_attempts = set()
    failure_runs = []
    for row in d["observations"]:
        observed_prs.add(row["pr"])
        result = row["conclusion"] or "nonterminal"
        counts[result] += 1
        if row["attempt"] is None:
            unknown_attempts += 1
        distinct_attempts.add((row["run_id"], row["attempt"]))
        if result != "failure":
            continue

        failed_prs.add(row["pr"])
        failure_runs.append(row)
        workflow = row["workflow"]
        family, path, priority = FAMILIES.get(
            workflow, ("UNCLASSIFIED_WORKFLOW:" + workflow, "UNOWNED", "P1")
        )
        if family not in families:
            families[family] = {
                "prs": set(),
                "evidence": [],
                "path": path,
                "priority": priority,
            }
        entry = families[family]
        entry["prs"].add(row["pr"])
        entry["evidence"].append(
            {
                "pr": row["pr"],
                "sha": row["sha"],
                "run_id": row["run_id"],
                "attempt": row["attempt"],
                "workflow": workflow,
                "url": row["url"],
            }
        )

    ledger = []
    for family, entry in families.items():
        rows = sorted(
            entry["evidence"],
            key=lambda item: (
                item["pr"],
                item["run_id"],
                item["attempt"] or 0,
            ),
        )
        unknown = sum(item["attempt"] is None for item in rows)
        unique_run_attempts = {(item["run_id"], item["attempt"]) for item in rows}
        ledger.append(
            {
                "candidate_family": family,
                "priority": entry["priority"],
                "candidate_path_lease": entry["path"],
                "unique_prs_affected": len(entry["prs"]),
                "failed_run_associations": len(rows),
                "failed_run_attempts": (
                    len(unique_run_attempts) if not unknown else None
                ),
                "unknown_run_attempt_associations": unknown,
                "distinct_failed_run_ids": len({item["run_id"] for item in rows}),
                "root_confirmed": False,
                "first_red_confirmed": False,
                "repair_committed": False,
                "independent_admission": False,
                "prs": sorted(entry["prs"]),
                "evidence": rows,
            }
        )

    ledger.sort(
        key=lambda item: (
            item["priority"] != "P0",
            -item["unique_prs_affected"],
            -item["failed_run_associations"],
            item["candidate_family"],
        )
    )
    waves = []
    leases = []
    for entry in ledger:
        family = entry["candidate_family"]
        if family.startswith("UNCLASSIFIED_WORKFLOW:"):
            kind = "READER"
        elif entry["priority"] == "P0":
            kind = "OWNER_SECURITY_OR_POLICY"
        else:
            kind = "SOURCE_DIAGNOSTIC"
        path = entry["candidate_path_lease"]
        collision = path != "UNOWNED" and any(
            path.startswith(lease) or lease.startswith(path) for lease in leases
        )
        status = (
            "SERIALIZE_PATH_COLLISION" if collision else "READY_FOR_READER_DIAGNOSTIC"
        )
        if entry["priority"] == "P0":
            status = "HOLD_INDEPENDENT_OWNER_REVIEW"
        if path != "UNOWNED" and not collision:
            leases.append(path)
        waves.append(
            {
                "candidate_family": family,
                "worker_type": kind,
                "path_lease_candidate": path,
                "scheduler_status": status,
                "source_mutation_authorized": False,
                "predicted_unblock_upper_bound_prs": entry["unique_prs_affected"],
                "causally_predicted_unblocked_prs": None,
            }
        )

    manifest = d.get("sampled_pr_heads")
    failures_distinct = {(row["run_id"], row["attempt"]) for row in failure_runs}
    return {
        "schema": "cbd.failure_census_projection.v1",
        "observation_scope": "PR_HEAD_ASSOCIATED_FIRST_PAGE_ONLY",
        "input_digest": sha256(d),
        "source_sha_scope": "PR_HEAD_PER_OBSERVATION",
        "authority": d["authority"],
        "observed": {
            "pr_count": len(manifest) if manifest is not None else len(observed_prs),
            "prs_with_failed_workflows": len(failed_prs),
            "first_page_workflow_associations_seen": (
                sum(head["workflow_associations_seen"] for head in manifest)
                if manifest is not None
                else None
            ),
            "run_association_count": len(d["observations"]),
            "failure_workflow_associations": counts["failure"],
            "run_attempt_count": (
                len(distinct_attempts) if unknown_attempts == 0 else None
            ),
            "unknown_run_attempt_associations": unknown_attempts,
            "distinct_failed_run_ids": len({row["run_id"] for row in failure_runs}),
            "duplicate_failed_run_associations": (
                len(failure_runs) - len(failures_distinct)
            ),
            "conclusions": counts,
            "candidate_family_count": len(ledger),
            "confirmed_causal_root_count": None,
            "accepted_closed_root_count": None,
            "matched_coverage_delta": None,
            "source_snapshot_atomic": False,
        },
        "candidate_families": ledger,
        "candidate_disjoint_waves": waves,
        "safety_rules": [
            "FAMILY_NAME_IS_SYMPTOM_NOT_CONFIRMED_ROOT",
            "REUSE_CANONICAL_BD_LDAB_JOINER",
            "NO_MERGE_OR_WAIVER",
            "VERIFY_JOB_STEP_FIRST_RED_BEFORE_REPAIR",
            "READ_ONLY_SCOUT_CAN_FAN_OUT_MUTATION_CANNOT_OVERLAP_PATH",
            "EXACT_HEAD_AFTER_EACH_MUTATION",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--additional-source", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.source] + args.additional_source
    sources = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    source = combine_sources(sources) if len(sources) > 1 else sources[0]
    output = produce(source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output["observed"], sort_keys=True))


if __name__ == "__main__":
    main()
