"""G3G disjoint source lease + evidence DAG evaluation (read-only).

No worker launch, merge, source write, reviewer grant, secret read or
engineering acceptance is possible from this module. Node-count depth is
not a run-duration or scheduling forecast.
"""
from __future__ import annotations

import re
from typing import Any

SHA = re.compile(r"^[a-f0-9]{40}$")
PARENTS = ("GOVERNANCE", "ADMISSION", "CREDENTIALS", "BROWSER", "FEDERATION")
STATES = frozenset((
    "NATIVE_PASS", "SOURCE_ONLY", "HOLD_OWNER", "HOLD_NATIVE",
    "DEFERRED", "FIRST_RED", "READ_ONLY_PROBE",
))


def require(flag: bool, why: str) -> None:
    if not flag:
        raise ValueError("G3G_DISJOINT_FAIL_CLOSED:" + why)


def _path(s: Any) -> bool:
    return isinstance(s, str) and bool(s) and not s.startswith("/") and (
        not re.match(r"^[A-Za-z]:", s) and "\0" not in s and
        "\\" not in s and all(x not in ("", ".", "..") for x in s.split("/"))
    )


def _overlap(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def assess(payload: dict) -> dict:
    require(isinstance(payload, dict) and
            payload.get("schema") == "codepurple.g3g_disjoint_plan.v1",
            "schema")
    require(payload.get("authority_transfer") is False and
            payload.get("merge_admission") == "HOLD" and
            payload.get("active_workers_launched") is None and
            payload.get("human_worker_hours") is None,
            "authority/capacity must not be fabricated")
    parents = payload.get("parents")
    require(isinstance(parents, list) and
            tuple(p.get("id") for p in parents) == PARENTS,
            "canonical five parents")
    require(all(p.get("accepted_closed") is False for p in parents),
            "no unsupported five-parent closure")
    lanes = payload.get("lanes")
    require(isinstance(lanes, list) and lanes,
            "nonempty real source-owner lane census")
    ids = [x.get("id") for x in lanes if isinstance(x, dict)]
    require(len(ids) == len(lanes) and len(ids) == len(set(ids)) and
            all(isinstance(s, str) and s for s in ids), "lane IDs")
    table = {x["id"]: x for x in lanes}
    for lane in lanes:
        require(lane.get("parent") in PARENTS and
                lane.get("state") in STATES, "parent/state")
        require(isinstance(lane.get("repo"), str) and
                lane["repo"].startswith("GBOGEB/") and
                lane["repo"].count("/") == 1, "repository")
        require(isinstance(lane.get("head_sha"), str) and
                bool(SHA.fullmatch(lane["head_sha"])), "exact SHA")
        deps = lane.get("depends_on")
        require(isinstance(deps, list) and len(deps) == len(set(deps)) and
                all(d in table and d != lane["id"] for d in deps), "DAG edges")
        paths = lane.get("lease_paths")
        require(isinstance(paths, list) and all(_path(x) for x in paths) and
                len(paths) == len(set(paths)), "leased source paths")
        # An independent test-file lease does not prove independence of the
        # production code under test. Missing targets remain UNKNOWN.
        targets = lane.get("sut_paths")
        require(targets is None or (
            isinstance(targets, list) and
            all(_path(x) for x in targets) and
            len(targets) == len(set(targets))
        ), "SUT source paths")
        need = lane.get("receipt")
        if lane["state"] == "NATIVE_PASS":
            require(isinstance(need, dict) and
                    need.get("conclusion") == "success" and
                    need.get("source_sha") == lane["head_sha"] and
                    all(type(need.get(x)) is int and need[x] > 0
                        for x in ("run_id", "attempt", "job_id")),
                    "exact terminal native identity")
        require(lane.get("accepted_root_id") is None,
                "fingerprint is not accepted causal root")
        require(lane.get("worker_hours") is None and
                lane.get("worker_capacity") is None,
                "worker labor and capacity UNKNOWN")
    # Every edge must be acyclic. Work topologically instead of creating
    # fictional jobs or assuming a DAG node's owner is available.
    marks = {}
    depths = {}
    def walk(node: str) -> int:
        if marks.get(node) == "visiting":
            raise ValueError("G3G_DISJOINT_FAIL_CLOSED:dependency cycle")
        if marks.get(node) == "done":
            return depths[node]
        marks[node] = "visiting"
        depth = 1 + max((walk(d) for d in table[node]["depends_on"]),
                        default=0)
        marks[node] = "done"
        depths[node] = depth
        return depth
    for key in table:
        walk(key)
    used = []
    for lane in lanes:
        repo_key = lane["repo"].casefold()
        for path in lane["lease_paths"]:
            for repo, other, owner in used:
                require(not (repo == repo_key and _overlap(path, other)),
                        f"overlapping source lease {owner} -> {lane['id']}")
            used.append((repo_key, path, lane["id"]))
    # Preserve historical plans: absent SUT inventories do not cause an
    # exception, but they cannot be promoted to independent scaling proof.
    sut_used = []
    sut_unknown = []
    for lane in lanes:
        repo_key = lane["repo"].casefold()
        targets = lane.get("sut_paths")
        if targets is None or (not targets and lane["lease_paths"]):
            sut_unknown.append(lane["id"])
            continue
        for target in targets:
            for repo, other, owner in sut_used:
                require(not (repo == repo_key and _overlap(target, other)),
                        f"overlapping SUT source target {owner} -> {lane['id']}")
            sut_used.append((repo_key, target, lane["id"]))
    sut_complete = not sut_unknown
    fingerprint_counts = {}
    occurrence_counts = {}
    for lane in lanes:
        fp = lane.get("first_red_fingerprint")
        if fp is not None:
            require(isinstance(fp, str) and bool(fp), "fingerprint")
            fingerprint_counts[fp] = fingerprint_counts.get(fp, 0) + 1
            occurrences = lane.get("observed_occurrences")
            require(occurrences is None or
                    (type(occurrences) is int and occurrences >= 1),
                    "missing occurrence is UNKNOWN")
            occurrence_counts[fp] = (
                None if occurrences is None or occurrence_counts.get(fp) is None
                and fp in occurrence_counts
                else occurrence_counts.get(fp, 0) + occurrences
            )
    status = {x["state"]: sum(l["state"] == x["state"] for l in lanes)
              for x in lanes}
    ready = [l["id"] for l in lanes
             if l["state"] == "READ_ONLY_PROBE" and
             all(table[d]["state"] == "NATIVE_PASS"
                 for d in l["depends_on"])]
    return {
        "schema": "codepurple.g3g_disjoint_receipt.v1",
        "cohort": payload.get("cohort"),
        "total_lanes": len(lanes),
        "lanes_by_state": dict(sorted(status.items())),
        "graph_edges": sum(len(x["depends_on"]) for x in lanes),
        "max_dependency_depth_nodes_not_duration": max(depths.values()),
        "read_only_unblocked_lanes": ready,
        "advisory_readonly_parallel_limit": min(3, len(ready)),
        "source_path_leases_disjoint": True,
        "sut_source_leases_disjoint": True if sut_complete else None,
        "sut_lease_census_complete": sut_complete,
        "sut_source_target_count": len(sut_used) if sut_complete else None,
        "sut_unreported_lane_ids": sorted(sut_unknown),
        "distinct_first_red_fingerprints": len(fingerprint_counts),
        "fingerprint_manifestations_by_lane": dict(sorted(fingerprint_counts.items())),
        "source_observed_occurrences": dict(sorted(occurrence_counts.items())),
        "accepted_causal_root_closures": 0,
        "parents_verified_closed": 0,
        "worker_launch_ids": None, "actual_worker_hours": None,
        "effective_runner_slots": None, "queue_p95_seconds": None,
        "no_native_census_promotion": True,
        "source_write_permission_granted_by_viewer": False,
        "merge_admission": "HOLD", "formal_credit_delta": 0,
    }
