"""Deterministic Mission Control wave-to-wave roll-up without authority transfer.

Consumes source-bound CI snapshots and optional MIP wave receipts. It does not
re-authenticate artifact bytes, infer root closure, or approve a red check.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SCHEMA = "mission.wave.history.v1"
INPUT = "mission.wave.history.input.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def tally_states(states):
    require(isinstance(states, dict), "missing states")
    counts = {
        "success": 0, "failed": 0, "skipped": 0,
        "cancelled": 0, "terminal_other": 0, "nonterminal": 0,
    }
    for key, number in states.items():
        require(type(number) is int and number >= 0, "invalid run count")
        if key == "completed/success":
            counts["success"] += number
        elif key == "completed/skipped":
            counts["skipped"] += number
        elif key == "completed/cancelled":
            counts["cancelled"] += number
        elif key in {"completed/failure", "completed/timed_out",
                     "completed/action_required", "completed/startup_failure"}:
            counts["failed"] += number
        elif key.startswith("completed/"):
            counts["terminal_other"] += number
        else:
            counts["nonterminal"] += number
    counts["non_success_terminal"] = sum(counts[k] for k in (
        "failed", "skipped", "cancelled", "terminal_other"
    ))
    return counts


def identities(snapshot):
    manifest = snapshot.get("run_manifest", [])
    require(isinstance(manifest, list), "run manifest malformed")
    ids = [item.get("workflow_id") for item in manifest]
    run_ids = [item.get("run_id") for item in manifest]
    if (not ids or len(run_ids) != len(set(run_ids)) or
            len(manifest) != snapshot.get("run_count") or
            any(type(i) is not int for i in ids + run_ids)):
        return None
    # Repeated workflow IDs are valid when each execution has a distinct ID.
    return tuple(sorted(ids))


def summarize_wave(entry):
    require(isinstance(entry, dict), "wave must be an object")
    wid = entry.get("wave_id")
    require(isinstance(wid, str) and wid, "missing wave ID")
    observations = entry.get("observations")
    require(isinstance(observations, list) and observations,
            "wave requires observed snapshots")
    repos = {}
    totals = Counter()
    families = Counter()
    terminal = 0
    complete = True
    sample_jobs = 0
    queue_values = []
    execution_values = []
    for observation in observations:
        require(observation.get("schema") == "mission.control.ci-telemetry.v1",
                "not a native CI telemetry snapshot")
        repo, sha = observation.get("repo"), observation.get("sha")
        require(isinstance(repo, str) and repo.startswith("GBOGEB/"),
                "invalid repo in snapshot")
        require(isinstance(sha, str) and SHA.fullmatch(sha),
                "invalid snapshot source SHA")
        require(repo not in repos, "duplicate repository in wave")
        require(observation.get("provenance") == "LIVE_GITHUB_API_READ_ONLY",
                "not a read-only API census")
        states = tally_states(observation.get("run_states"))
        require(sum(states.values()) == observation.get("run_count"),
                "snapshot counts disagree")
        complete = complete and observation.get("run_census_complete") is True
        totals.update(states)
        terminal += observation.get("terminal_run_count", 0)
        jm = observation.get("job_metrics", {})
        require(isinstance(jm, dict), "malformed job metrics")
        count = jm.get("sampled_jobs")
        require(type(count) is int and count >= 0, "invalid sampled jobs")
        sample_jobs += count
        if jm.get("queue_p50_s") is not None:
            queue_values.append({"repo": repo, "seconds": jm["queue_p50_s"]})
        if jm.get("execution_p50_s") is not None:
            execution_values.append({"repo": repo, "seconds": jm["execution_p50_s"]})
        for group, groups in observation.get("family_run_states", {}).items():
            require(isinstance(groups, dict), "invalid family counters")
            families[group] += sum(groups.values())
        repos[repo] = {"sha": sha, "run_states": states,
                       "workflow_ids": identities(observation),
                       "job_metrics": jm,
                       "run_census_complete": observation["run_census_complete"]}
    coverages = {}
    submitted_roots = {}
    pulses = entry.get("mip_pulses", [])
    require(isinstance(pulses, list), "invalid MIP pulses")
    for pulse in pulses:
        require(pulse.get("schema") == "abacus.mip.wave-pulse.v1",
                "invalid MIP pulse schema")
        repo, sha = pulse.get("repository"), pulse.get("head_sha")
        require(repo in repos and repos[repo]["sha"] == sha,
                "MIP pulse does not match exact observed wave SHA")
        require(pulse.get("wave_id") == wid, "MIP wave ID mismatch")
        require(repo not in coverages, "duplicate MIP pulse")
        cv = pulse.get("coverage", {})
        require(cv.get("status") in {"COMPARABLE", "UNKNOWN", "INCOMPARABLE"},
                "coverage classification missing")
        coverages[repo] = {"status": cv["status"],
                           "delta_pp": cv.get("delta_pp")
                           if cv["status"] == "COMPARABLE" else None,
                           "evidence": "PRODUCER_DECLARED_NOT_REAUTHENTICATED"}
        root_counts = pulse.get("root_counts", {})
        require(isinstance(root_counts, dict), "malformed root counts")
        submitted_roots[repo] = root_counts
    requests = entry.get("solo_decisions", [])
    require(isinstance(requests, list), "invalid exceptions")
    for decision in requests:
        require(decision.get("head_sha") in
                {repo["sha"] for repo in repos.values()},
                "exception source SHA not in wave")
        require(decision.get("merge_admitted") is False,
                "solo ledger cannot authorize a merge")
    depth = ["CI_RUN_CENSUS"]
    if sample_jobs:
        depth.append("CI_JOB_SAMPLE")
    if coverages:
        depth.append("MIP_PULSE_SUBMITTED")
    if requests:
        depth.append("EXCEPTION_LEDGER")
    return {
        "wave_id": wid,
        "repos": repos,
        "breadth_observed_repositories": len(repos),
        "depth_evidence_dimensions": depth,
        "checks": dict(totals),
        "terminal_runs": terminal,
        "run_census_complete": complete,
        "job_sample_count": sample_jobs,
        "queue_p50_samples": queue_values,
        "execution_p50_samples": execution_values,
        "family_routing_counts": dict(sorted(families.items())),
        "coverage_by_repo": coverages,
        "submitted_root_counts_by_repo": submitted_roots,
        "amber_requests": sum(
            d.get("decision") == "AMBER_REQUESTED" for d in requests),
        "formal_root_closures_credited": None,
        "rex_accepted_credited": None,
        "merge_admitted": False,
    }


def compare(before, after):
    comparison = {}
    for name in sorted(set(before["repos"]) | set(after["repos"])):
        a, b = before["repos"].get(name), after["repos"].get(name)
        if not a or not b:
            comparison[name] = {"status": "INCOMPARABLE_REPO_COHORT"}
            continue
        if not a["run_census_complete"] or not b["run_census_complete"]:
            comparison[name] = {"status": "INCOMPLETE_RUN_CENSUS"}
            continue
        if a["workflow_ids"] is None or a["workflow_ids"] != b["workflow_ids"]:
            comparison[name] = {"status": "INCOMPARABLE_WORKFLOW_SET"}
            continue
        if (a["run_states"]["nonterminal"] or b["run_states"]["nonterminal"]):
            comparison[name] = {"status": "NONTERMINAL_WITHHELD"}
            continue
        comparison[name] = {
            "status": "MATCHED_WORKFLOW_SET_ONLY",
            "delta_success": (b["run_states"]["success"]
                              - a["run_states"]["success"]),
            "delta_non_success_terminal": (
                b["run_states"]["non_success_terminal"]
                - a["run_states"]["non_success_terminal"]),
            "delta_failed": b["run_states"]["failed"] - a["run_states"]["failed"],
            "delta_skipped": (
                b["run_states"]["skipped"] - a["run_states"]["skipped"]),
            "caveat": "Does not establish equal dependencies or root closure",
        }
    return comparison


def rollup(document):
    require(document.get("schema") == INPUT, "wrong input schema")
    waves = document.get("waves")
    require(isinstance(waves, list) and waves, "missing wave history")
    summaries = [summarize_wave(x) for x in waves]
    names = [x["wave_id"] for x in summaries]
    require(len(set(names)) == len(names), "duplicate wave ID")
    pairs = []
    for first, second in zip(summaries, summaries[1:]):
        pairs.append({"from": first["wave_id"], "to": second["wave_id"],
                      "by_repo": compare(first, second)})
    return {"schema": SCHEMA,
            "waves": summaries,
            "wave_comparisons": pairs,
            "independent_evidence_verified": False,
            "global_coverage_delta_pp": None,
            "global_root_closures": None,
            "global_merge_authority": False}



def as_markdown(payload):
    rows = [
        "# Mission Control wave progression",
        "",
        "Read-only telemetry. Counts below are **workflow runs**, not test cases.",
        "Unknown or incomparable evidence is not a measured zero.",
        "",
        "| Wave | Repos | Dimensions | Pass | Fail | Skipped | " +
        "Cancelled | Pending | Jobs sampled | Coverage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for wave in payload["waves"]:
        count = wave["checks"]
        coverage = ", ".join(
            repo + ": " + (
                str(value["delta_pp"]) + " pp (producer-declared)"
                if value["status"] == "COMPARABLE" and value["delta_pp"] is not None
                else value["status"]
            )
            for repo, value in sorted(wave["coverage_by_repo"].items())
        ) or "UNKNOWN"
        rows.append(
            "| " + wave["wave_id"] + " | " +
            str(wave["breadth_observed_repositories"]) + " | " +
            str(len(wave["depth_evidence_dimensions"])) + " | " +
            str(count["success"]) + " | " +
            str(count["failed"]) + " | " +
            str(count["skipped"]) + " | " +
            str(count["cancelled"]) + " | " +
            str(count["nonterminal"]) + " | " +
            str(wave["job_sample_count"]) + " | " +
            coverage + " |"
        )
    rows.extend(["", "## Matched workflow-set comparisons", "",
                 "| From -> To | Repo | Status | Delta success | " +
                 "Delta failed | Delta skipped |",
                 "|---|---|---|---:|---:|---:|"])
    for pair in payload["wave_comparisons"]:
        for repo, change in pair["by_repo"].items():
            rows.append(
                "| " + pair["from"] + " -> " + pair["to"] +
                " | " + repo + " | " + change["status"] +
                " | " + str(change.get("delta_success", "UNKNOWN")) +
                " | " + str(change.get("delta_failed", "UNKNOWN")) +
                " | " + str(change.get("delta_skipped", "UNKNOWN")) +
                " |"
            )
    rows.extend([
        "", "Depth is observed data-dimension count, not method maturity.",
        "Breadth counts observed repo snapshots, not admitted federation workers.",
        "PCA/BT, REX acceptance, exact-main root closure and merge admission",
        "remain uncredited without their independent native evidence.",
        "",
    ])
    return "\n".join(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.input).read_bytes()
    payload = rollup(json.loads(source))
    payload["input_sha256"] = hashlib.sha256(source).hexdigest()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=list) +
                    "\n", encoding="utf-8")
    path.with_suffix(".md").write_text(as_markdown(payload), encoding="utf-8")
    print(json.dumps({"waves": len(payload["waves"]),
                      "comparisons": len(payload["wave_comparisons"]),
                      "merge_authority": False}))


if __name__ == "__main__":
    main()
