"""Read-only union of frozen CBD workflow cohorts; no new source of authority.

Calls the existing cbd_workflow_failure_waves producer. Source-declared run/attempt
identities are NOT proof of a live PR head, job first-red or causal root.
"""

from __future__ import annotations

from copy import deepcopy

from cbd_workflow_failure_waves import produce, sha256, validate


def produce_cohorts(sources: list[dict]) -> dict:
    """Reconcile declared workflow observations without double-counting runs.

    Independent source records are validated before aggregation. Identical
    run-attempts can appear in multiple snapshots, but conflicting metadata or
    competing head SHAs for the same PR fail closed.
    """
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("at least one source snapshot is required")

    rows_by_run: dict[tuple[int, int | None], dict] = {}
    head_by_pr: dict[int, str] = {}
    source_digests: list[str] = []
    input_rows = 0
    missing_attempts = 0
    missing_manifests = 0
    manifests_by_pr: dict[int, dict] = {}
    native_run_identity: dict[int, tuple[int, str, str, int | None]] = {}
    ingestion_pulses: list[dict] = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source snapshot must be an object")
        validate(source)
        source_digests.append(sha256(source))
        if "sampled_pr_heads" not in source:
            missing_manifests += 1
        for head in source.get("sampled_pr_heads", []):
            pr_id = head["pr"]
            if pr_id in manifests_by_pr and manifests_by_pr[pr_id] != head:
                raise ValueError("conflicting sampled PR head manifest")
            manifests_by_pr[pr_id] = deepcopy(head)
        for row in source["observations"]:
            # bool is an int subclass; it cannot identify a real GitHub run.
            if type(row["run_id"]) is not int or (
                row["attempt"] is not None and type(row["attempt"]) is not int
            ):
                raise ValueError("run/attempt identities must be integers or unknown")
            if row["attempt"] is None:
                missing_attempts += 1
            rid = row["run_id"]
            native_identity = (
                row["pr"], row["sha"], row["workflow"], row["attempt"]
            )
            if rid in native_run_identity:
                prior = native_run_identity[rid]
                if prior[:3] != native_identity[:3]:
                    raise ValueError("conflicting cross-attempt run provenance")
                if (prior[3] is None) != (row["attempt"] is None):
                    raise ValueError("ambiguous unknown/known run attempt")
            else:
                native_run_identity[rid] = native_identity
            key = (row["run_id"], row["attempt"])
            if row["pr"] in head_by_pr and head_by_pr[row["pr"]] != row["sha"]:
                raise ValueError("incompatible pull-head snapshots")
            head_by_pr[row["pr"]] = row["sha"]
            if key in rows_by_run and rows_by_run[key] != row:
                raise ValueError("conflicting run-attempt provenance")
            rows_by_run[key] = deepcopy(row)
            input_rows += 1
        ingestion_pulses.append(
            {
                "source_index": len(ingestion_pulses) + 1,
                "declared_rows_cumulative": input_rows,
                "distinct_run_ids_cumulative": len({key[0] for key in rows_by_run}),
                "distinct_failed_pr_heads_cumulative": len(head_by_pr),
                "kind": "SOURCE_INGESTION_NOT_TEMPORAL_IMPROVEMENT",
            }
        )

    authority = {
        "security_waiver": False,
        "authority_transfer": False,
        "merge_admission": "HOLD",
        "dispatch": "STAGED_NOT_LAUNCHED",
    }
    merged = {
        "schema": "cbd.pr_workflow_observations.v1",
        "repository": "GBOGEB/ABACUS",
        "sampling": "FROZEN_FIRST_PAGE_ASSOCIATIONS_NOT_LIVE_ROOT_EVIDENCE",
        "authority": authority,
        "observations": sorted(
            rows_by_run.values(),
            key=lambda row: (row["pr"], row["run_id"], row["attempt"]),
        ),
    }
    output = produce(merged)
    output["cohort_reconciliation"] = {
        "source_document_count": len(sources),
        "distinct_source_documents": len(set(source_digests)),
        "source_digests_sha256": sorted(source_digests),
        "declared_observation_rows": input_rows,
        "distinct_run_attempts": (
            len(rows_by_run) if missing_attempts == 0 else None
        ),
        "distinct_declared_run_ids": len({key[0] for key in rows_by_run}),
        "unknown_attempt_associations": missing_attempts,
        "snapshots_without_head_manifests": missing_manifests,
        "distinct_manifested_pr_heads": len(manifests_by_pr),
        "manifested_zero_failure_prs": sorted(
            pr for pr, head in manifests_by_pr.items()
            if head["failed_associations_seen"] == 0
        ),
        "non_atomic_manifest_workflow_associations": sum(
            head["workflow_associations_seen"]
            for head in manifests_by_pr.values()
        ),
        "non_atomic_manifest_failed_associations": sum(
            head["failed_associations_seen"]
            for head in manifests_by_pr.values()
        ),
        "manifest_comparability": "NOT_A_DENOMINATOR_FOR_UNION_PASS_RATE",
        "ingestion_pulses": ingestion_pulses,
        "cross_source_duplicate_rows": input_rows - len(rows_by_run),
        "distinct_declared_pr_heads": len(head_by_pr),
        "source_attempt_verification": "NOT_LIVE_VERIFIED",
        "current_head_verification": "NOT_LIVE_VERIFIED",
        "job_first_red_verification": "NOT_LIVE_VERIFIED",
        "matched_coverage": None,
        "root_closure_credit": None,
        "admission": "HOLD",
    }
    output["safety_rules"].append("MULTI_SOURCE_UNION_IS_NOT_NATIVE_ROOT_PROOF")
    return output
