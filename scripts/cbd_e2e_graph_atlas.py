"""CBD E2E evidence multigraph: exact-head run/job/step atoms and conservative edges.

Workflow labels, shared PRs and job labels are symptoms, never causal roots.
The directed process DAG excludes co-occurrence edges (which can contain cycles).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}")
STAGES = (
    ("E0", "source/index", "before_git"),
    ("E1", "developer pre-commit", "before_git"),
    ("E2", "developer pre-push", "before_git"),
    ("E3", "GitHub exact HEAD", "github"),
    ("E4", "isolated local clone", "after_github"),
    ("E5", "N/N+1 parity", "after_github"),
    ("E6", "security/governance admission", "admission"),
)
JOB_GROUPS = {
    "Security Scanning": "SECURITY",
    "Code Quality Checks": "QUALITY",
    "Code Coverage": "COVERAGE",
    "Full Red Proof Summary": "DOWNSTREAM_SUMMARY",
}


def need(condition, why):
    if not condition:
        raise ValueError(why)


def digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_cohort(documents):
    """Validate disjoint head manifests and failure-link source identities."""
    need(len(documents) == 2, "two exact 10-PR cohorts required")
    seen = {}
    links = []
    counts = []
    run_ids = {}
    for document in documents:
        need(document.get("schema") == "cbd.pr_workflow_observations.v1",
             "wrong cohort schema")
        need(document.get("repository") == "GBOGEB/ABACUS",
             "wrong cohort repository")
        need(document.get("authority", {}).get("merge_admission") == "HOLD"
             and document["authority"].get("security_waiver") is False,
             "unsafe cohort authority")
        manifest = document.get("sampled_pr_heads")
        need(isinstance(manifest, list) and len(manifest) == 10,
             "sampled heads missing")
        for item in manifest:
            pr = item.get("pr")
            head = item.get("sha")
            need(type(pr) is int and pr > 0 and isinstance(head, str)
                 and SHA.fullmatch(head), "invalid PR head")
            need(pr not in seen, "duplicate PR across cohorts")
            seen[pr] = item
            total = item.get("workflow_associations_seen")
            red = item.get("failed_associations_seen")
            need(type(total) is int and type(red) is int
                 and 0 <= red <= total, "denominator mismatch")
            counts.append(total)
        observations = document.get("observations")
        need(isinstance(observations, list), "missing workflow observations")
        links.extend(observations)

    by_pr = Counter()
    for link in links:
        pr, run_id = link.get("pr"), link.get("run_id")
        need(pr in seen and link.get("sha") == seen[pr]["sha"],
             "workflow head drift")
        need(type(run_id) is int and run_id > 0, "invalid native run ID")
        need(link.get("conclusion") == "failure", "failure cohort invalid")
        need(link.get("attempt") is None, "unproven run attempt promoted")
        name = link.get("workflow")
        need(isinstance(name, str) and name.strip(), "missing workflow label")
        need(link.get("url") ==
             f"https://github.com/GBOGEB/ABACUS/actions/runs/{run_id}",
             "workflow evidence URL drift")
        if run_id in run_ids:
            need(run_ids[run_id] == (link["sha"], name),
                 "shared run identity conflict")
        run_ids[run_id] = (link["sha"], name)
        by_pr[pr] += 1
    need(all(by_pr[p] == head["failed_associations_seen"]
             for p, head in seen.items()), "failed-link denominator mismatch")
    return seen, links, sum(counts)


def validate_native(documents):
    """Latest-attempt job details are bound to the native source head."""
    need(len(documents) == 2, "two native job snapshots required")
    seen_runs, seen_jobs = set(), set()
    runs = []
    for d in documents:
        need(d.get("schema") == "cbd.native_ci_job_snapshot.v1"
             and d.get("repository") == "GBOGEB/ABACUS",
             "native source schema mismatch")
        need(d.get("authority", {}).get("merge_admission") == "HOLD"
             and d["authority"].get("security_waiver") is False,
             "unsafe native authority")
        for run in d.get("runs", []):
            rid, sha = run.get("run_id"), run.get("source_head_sha")
            need(type(rid) is int and rid > 0 and rid not in seen_runs,
                 "duplicate/invalid native run")
            seen_runs.add(rid)
            need(isinstance(sha, str) and SHA.fullmatch(sha),
                 "native source head invalid")
            jobs = run.get("jobs")
            need(isinstance(jobs, list)
                 and type(run.get("job_total")) is int
                 and run["job_total"] >= len(jobs),
                 "invalid job denominator")
            for job in jobs:
                jid = job.get("job_id")
                need(type(jid) is int and jid > 0 and jid not in seen_jobs,
                     "duplicate/invalid native job")
                seen_jobs.add(jid)
                need(job.get("head_sha") == sha,
                     "native job refers to different source head")
                need(type(job.get("run_attempt")) is int
                     and job["run_attempt"] > 0,
                     "missing native attempt")
                need(job.get("conclusion") in
                     ("success", "failure", "skipped", "cancelled", None),
                     "invalid native outcome")
                need(isinstance(job.get("failed_steps"), list),
                     "missing native failed-step list")
            runs.append(run)
    return runs


def build(cohorts, native, stage_receipts=()):
    """Build a source-bound multigraph and compute noncausal overlap strength."""
    heads, workflow_links, total_workflows = validate_cohort(cohorts)
    native_runs = validate_native(native)
    nodes, edges, unique = {}, [], set()

    def node(key, kind, label, rank, **attributes):
        if key not in nodes:
            nodes[key] = {
                "id": key, "kind": kind, "label": label, "rank": rank,
                "attributes": attributes,
            }
        return key

    def edge(src, dst, relationship, evidence, *, support=1,
             jaccard=None, causal=False):
        key = (src, dst, relationship, evidence)
        if key in unique:
            return
        unique.add(key)
        edges.append({
            "source": src, "target": dst, "relationship": relationship,
            "evidence": evidence, "support": support,
            "jaccard": jaccard, "causal_confirmed": causal,
        })

    for i, (eid, label, lane) in enumerate(STAGES):
        node("stage:" + eid, "stage", label, i, lane=lane,
             status="UNKNOWN", observed=False)
        if i:
            edge("stage:" + STAGES[i-1][0], "stage:" + eid,
                 "expected_stage_transition", "DECLARED", support=0)

    run_meta = {}
    affected = defaultdict(set)
    for pr, head in sorted(heads.items()):
        p = node(f"pr:{pr}", "pr", f"PR #{pr}", 2, number=pr)
        h = node(f"head:{pr}:{head['sha']}", "head",
                 head["sha"][:12], 3, sha=head["sha"], pr=pr,
                 exact_head=True)
        edge(p, h, "has_observed_head", "SOURCE_BOUND")

    for item in workflow_links:
        pr, sha, run_id, label = (
            item["pr"], item["sha"], item["run_id"], item["workflow"]
        )
        run = node(f"run:{run_id}", "run", f"run {run_id}", 4,
                   run_id=run_id, workflow=label, attempt=None)
        head = f"head:{pr}:{sha}"
        edge(head, run, "failed_workflow_observation", "SOURCE_BOUND")
        f = node("workflow:" + label, "workflow_family", label, 8)
        edge(run, f, "manifested_as_workflow", "OBSERVED")
        affected[label].add(pr)
        run_meta[run_id] = {"sha": sha, "pr": pr, "workflow": label}

    for run in native_runs:
        rid, pr, sha = (
            run["run_id"], run["pr"], run["source_head_sha"]
        )
        node(f"pr:{pr}", "pr", f"PR #{pr}", 2, number=pr)
        hn = node(f"head:{pr}:{sha}", "head", sha[:12], 3,
                  sha=sha, pr=pr, exact_head=True)
        edge(f"pr:{pr}", hn, "has_native_run_head", "SOURCE_BOUND")
        rnode = node(f"run:{rid}", "run", f"run {rid}", 4,
                     run_id=rid, workflow=run["workflow"])
        if rid in run_meta:
            need(run_meta[rid]["sha"] == sha and run_meta[rid]["pr"] == pr,
                 "same run ID carries contradictory PR/source SHA")
        edge(hn, rnode, "native_job_run", "OBSERVED")
        for job in run["jobs"]:
            attempt = job["run_attempt"]
            aid = node(f"attempt:{rid}:{attempt}", "attempt",
                       f"attempt {attempt}", 5,
                       run_id=rid, attempt=attempt)
            edge(rnode, aid, "native_attempt", "OBSERVED")
            jid = job["job_id"]
            jnode = node(f"job:{jid}", "job", job["job_name"], 6,
                         job_id=jid, status=job["status"],
                         conclusion=job["conclusion"],
                         run_attempt=attempt)
            edge(aid, jnode, "executed_job", "OBSERVED")
            if job["conclusion"] == "failure":
                group = JOB_GROUPS.get(job["job_name"], "UNCLASSIFIED")
                family_id = node("jobfamily:" + group, "job_family", group, 8,
                                 causal_root_id=None)
                edge(jnode, family_id, "failed_job_symptom", "OBSERVED")
                for step in job["failed_steps"]:
                    idx = step["step_number"]
                    skey = node(f"step:{jid}:{idx}", "failed_step",
                                step["step_name"], 7, job_id=jid, number=idx)
                    edge(jnode, skey, "failed_at_step", "OBSERVED")

    # Co-occurrence links are undirected association, NOT DAG/causal edges.
    labels = sorted(affected)
    for i, left in enumerate(labels):
        for right in labels[i+1:]:
            overlap = affected[left] & affected[right]
            if not overlap:
                continue
            union = affected[left] | affected[right]
            edge("workflow:" + left, "workflow:" + right,
                 "same_PR_head_cooccurrence", "ASSOCIATION",
                 support=len(overlap), jaccard=round(len(overlap)/len(union), 5))

    stages = list(stage_receipts)
    for value in stages:
        need(isinstance(value, dict) and value.get("schema") ==
             "abacus.cbd.e2e.stage.v1", "unsupported stage receipt")
        st = value.get("stage")
        mapped = {"pre-commit":"E1", "pre-push":"E2",
                  "checkout":"E3", "replay":"E4"}.get(st)
        need(mapped is not None, "unknown stage receipt")
        src = value.get("source", {})
        sha = src.get("head_sha")
        need(isinstance(sha, str) and SHA.fullmatch(sha),
             "stage receipt without exact source")
        sid = node("stage-receipt:" + mapped + ":" + sha, "stage_receipt",
                   st + " " + sha[:9], 1,
                   status=value.get("status"), sha=sha,
                   elapsed_process_ms=value.get("clock", {}).get(
                       "elapsed_process_ms"))
        edge("stage:" + mapped, sid, "recorded_stage", "OBSERVED")
    degree = Counter()
    weighted = Counter()
    for e in edges:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
        if e["evidence"] in {"OBSERVED", "SOURCE_BOUND"}:
            weighted[e["source"]] += e["support"]
            weighted[e["target"]] += e["support"]
    for n in nodes.values():
        n["degree"] = degree[n["id"]]
        n["observed_weighted_degree"] = weighted[n["id"]]
    groups = Counter(x["kind"] for x in nodes.values())
    kinds = Counter(x["evidence"] for x in edges)
    summary = {
        "cohort_pr_heads": len(heads),
        "cohort_workflow_associations": total_workflows,
        "failed_workflow_associations": len(workflow_links),
        "native_run_count": len(native_runs),
        "native_job_count": sum(len(r["jobs"]) for r in native_runs),
        "native_failed_jobs": sum(
            j["conclusion"] == "failure"
            for r in native_runs for j in r["jobs"]),
        "native_failed_steps": sum(
            len(j["failed_steps"]) for r in native_runs for j in r["jobs"]),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(sorted(groups.items())),
        "edge_evidence_classes": dict(sorted(kinds.items())),
        "confirmed_causal_root_edges": 0,
        "matched_coverage_delta": None,
        "developer_pre_push_proven": None,
    }
    return {
        "schema": "cbd.e2e.evidence_multigraph.v1",
        "repository": "GBOGEB/ABACUS",
        "scope": "NONATOMIC_20_PR_WORKFLOW_AND_16_NATIVE_JOB_SNAPSHOTS",
        "authority": {"merge_admission":"HOLD", "security_waiver":False,
                      "causal_root_promoted":False},
        "input_digests": [digest(x) for x in cohorts + native],
        "metrics": summary,
        "nodes": sorted(nodes.values(), key=lambda x: x["id"]),
        "edges": sorted(edges, key=lambda x: (
            x["source"], x["target"], x["relationship"])),
        "safety": [
            "COOCCURRENCE_IS_NOT_CAUSATION",
            "RUN_ATTEMPT_IS_DISTINCT_FROM_RUN_ID",
            "UNKNOWN_DEVELOPER_HOOK_CANNOT_BE_PROMOTED",
            "DAG_EXCLUDES_ASSOCIATION_EDGES",
            "NO_COVERAGE_OR_SECURITY_CREDIT_WITHOUT_MATCHED_PROOF",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, nargs=2, required=True)
    parser.add_argument("--native", type=Path, nargs=2, required=True)
    parser.add_argument("--stage-receipt", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    result = build([load(p) for p in args.cohort],
                   [load(p) for p in args.native],
                   [load(p) for p in args.stage_receipt])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps(result["metrics"], sort_keys=True))


if __name__ == "__main__":
    main()
