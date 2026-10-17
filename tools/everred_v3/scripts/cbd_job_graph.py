"""Deterministic, non-causal graph of source-bound CBD native job observations.

This is a review projection, not a root ledger, runner dispatcher or merger.
Only the existing cbd_260 reader can fetch native GitHub data.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import Counter, defaultdict
from pathlib import Path


TRUST = "GITHUB_API_METADATA_NOT_CAUSAL_CONFIRMATION"
BOUND = "JOB_METADATA_BOUND"
WITHHELD = "READBACK_WITHHELD"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def analyze(snapshot, native):
    """Validate exact sampled run IDs and project job/step candidate signatures."""
    index = snapshot["unique_failed_runs"]
    require(isinstance(native, dict), "native must be mapping")
    require(set(native) == {str(n) for n in index}, "run ID census mismatch")
    by_run_pr = defaultdict(set)
    for row in snapshot["rows"]:
        for run in row["failed_runs"]:
            by_run_pr[run["run_id"]].add(row["pr"])

    signatures = {}
    attempt_histogram = Counter()
    metrics = Counter()
    seen_job_ids = set()
    nodes = {}
    edges = set()

    def node(node_id, kind, **attrs):
        nodes[node_id] = {"id": node_id, "kind": kind, **attrs}

    def edge(source, target, kind):
        edges.add((source, target, kind))

    for rid in sorted(index):
        expected = index[rid]
        observation = native[str(rid)]
        require(isinstance(observation, dict), "invalid native observation")
        status = observation.get("status")
        require(status in (BOUND, WITHHELD), "invalid native status")
        metrics["runs_requested"] += 1
        run_node = f"run:{rid}"
        node(run_node, "FAILED_RUN", run_id=rid, source_sha=expected["sha"])
        for pr in sorted(by_run_pr[rid]):
            pid = f"pr:{pr}"
            node(pid, "PR", pr=pr)
            edge(pid, run_node, "PR_HAS_RUN_ASSOCIATION")
        require(observation.get("first_red_causal_root") is None,
                "root confirmation claim forbidden")
        require(observation.get("full_log_read") is False,
                "full-log claim forbidden")
        if status == WITHHELD:
            require(observation.get("failed_jobs") is None
                    and observation.get("failed_job_count") is None,
                    "withheld readback carries jobs")
            metrics["runs_withheld"] += 1
            continue

        require(
            observation.get("head_sha") == expected["sha"]
            and observation.get("workflow") == expected["workflow"]
            and observation.get("trust") == TRUST,
            "source or trust mismatch",
        )
        attempt = observation.get("run_attempt")
        require(type(attempt) is int and attempt > 0, "invalid run attempt")
        jobs = observation.get("failed_jobs")
        require(isinstance(jobs, list) and
                observation.get("failed_job_count") == len(jobs),
                "job denominator mismatch")
        metrics["runs_bound"] += 1
        attempt_histogram[str(attempt)] += 1
        if not jobs:
            metrics["bound_runs_without_failure_job"] += 1
        for job in jobs:
            require(isinstance(job, dict), "invalid failure job")
            jid = job.get("job_id")
            require(type(jid) is int and jid > 0 and jid not in seen_job_ids,
                    "missing or duplicate job ID")
            seen_job_ids.add(jid)
            require(job.get("step_causality") == "UNATTRIBUTED",
                    "forged causal attribution")
            job_name = job.get("job_name")
            require(isinstance(job_name, str) and job_name.strip(),
                    "missing job name")
            step = job.get("first_failed_step")
            if step is None:
                step_name = "UNKNOWN_FIRST_FAILED_STEP"
                metrics["jobs_without_failed_step"] += 1
            else:
                require(isinstance(step, dict) and
                        type(step.get("number")) is int and
                        step["number"] > 0 and
                        isinstance(step.get("name"), str) and
                        step["name"].strip(), "malformed first failed step")
                step_name = step["name"]
                metrics["jobs_with_failed_step"] += 1
            fingerprint = digest(
                [expected["workflow"], job_name, step_name]
            )[:16]
            signature_id = "sig:" + fingerprint
            if signature_id not in signatures:
                signatures[signature_id] = {
                    "candidate_id": signature_id,
                    "workflow": expected["workflow"],
                    "job": job_name,
                    "first_failed_step": step_name,
                    "manifestations": 0,
                    "affected_prs": set(),
                    "run_ids": set(),
                    "causal_root_id": None,
                    "confirmed_closed": None,
                    "treatment": "DOWNSTREAM_SUSPECT" if (
                        "summary" in job_name.lower()
                        or "feedback gate" in job_name.lower()
                    ) else "REQUIRES_LOG_LEVEL_CAUSAL_REVIEW",
                }
            record = signatures[signature_id]
            record["manifestations"] += 1
            record["run_ids"].add(rid)
            record["affected_prs"].update(by_run_pr[rid])
            jid_node = f"job:{jid}"
            node(jid_node, "FAILED_JOB", job_id=jid, attempt=attempt,
                 source_sha=expected["sha"])
            node(signature_id, "STEP_SIGNATURE_CANDIDATE",
                 first_failed_step=step_name, root_confirmed=None)
            edge(run_node, jid_node, "RUN_HAS_FAILED_JOB")
            edge(jid_node, signature_id, "FIRST_FAILED_STEP_SIGNATURE")
            metrics["failed_job_observations"] += 1

    ranked = []
    for record in signatures.values():
        ranked.append({
            **record,
            "affected_prs": sorted(record["affected_prs"]),
            "run_ids": sorted(record["run_ids"]),
            "pr_reach_upper_bound": len(record["affected_prs"]),
        })
    ranked.sort(key=lambda x: (-x["manifestations"], -x["pr_reach_upper_bound"],
                                x["candidate_id"]))
    for rank, record in enumerate(ranked, 1):
        record["priority_rank_by_observation_frequency"] = rank
    counted = {
        key: metrics[key]
        for key in (
            "runs_requested", "runs_bound", "runs_withheld",
            "bound_runs_without_failure_job", "failed_job_observations",
            "jobs_with_failed_step", "jobs_without_failed_step",
        )
    }
    counted["candidate_step_signatures"] = len(ranked)
    counted["run_attempt_histogram"] = dict(sorted(attempt_histogram.items()))
    counted["confirmed_roots_open"] = None
    counted["confirmed_roots_closed"] = None
    counted["formal_closures_delta"] = 0
    counted["main_coverage"] = None
    counted["diff_coverage"] = None
    counted["authenticated_crew_dispatches"] = None
    counted["complete_entire_repository_run_denominator"] = None
    return {
        "schema": "abacus.everred.cbd.job_step_candidate_dag.v1",
        "repository": snapshot["repository"],
        "main_sha_at_N0": snapshot["main_sha_at_observation"],
        "N0_source_sha256": snapshot["source_sha256"],
        "scope": "HISTORICAL_FIRST_PAGE_RUN_IDS_NATIVE_PAGINATED_JOB_METADATA",
        "native_logs_read": False,
        "atomic_live_census": False,
        "metrics": counted,
        "candidate_signatures": ranked,
        "graph": {
            "nodes": [nodes[k] for k in sorted(nodes)],
            "edges": [
                {"from": source, "to": target, "type": kind}
                for source, target, kind in sorted(edges)
            ],
        },
        "sipoc": {
            "supplier": "N0 exact-PR-head corpus and GitHub run/jobs reader",
            "input": "run ID, source SHA, attempt, job ID, first failed step",
            "process": [
                "N0 deduplicate PR/run aliases",
                "N1 validate source/attempt/job custody",
                "N2 shortlist first-step signatures without inferring roots",
                "N3 owner-owned log causal review and disjoint fixes",
                "N4 matched positive/negative branch and diff coverage",
                "N5 governed checks, independent review and main readback",
            ],
            "output": "hashed observational DAG and prior-to-repair candidate ranking",
            "customer": "BD-LDAB #1929; Mission Control reader; admission #1860",
        },
        "safety": {
            "merge_admission": "HOLD",
            "authority_transfer": False,
            "security_waiver": False,
            "authenticated_dispatch": "NOT_CLAIMED",
            "candidate_is_not_confirmed_root": True,
        },
    }


def render_html(dag):
    def esc(value):
        return html.escape(str(value), quote=True)

    rows = []
    for row in dag["candidate_signatures"]:
        url = ("https://github.com/GBOGEB/ABACUS/actions/runs/"
               + str(row["run_ids"][0])) if row["run_ids"] else "#"
        rows.append(
            "<tr><td>" + esc(row["priority_rank_by_observation_frequency"])
            + "</td><td>" + esc(row["manifestations"])
            + "</td><td>" + esc(row["pr_reach_upper_bound"])
            + "</td><td>" + esc(row["workflow"])
            + "</td><td>" + esc(row["job"])
            + "</td><td>" + esc(row["first_failed_step"])
            + "</td><td>" + esc(row["treatment"])
            + "</td><td><a href='" + esc(url) + "'>Run</a></td></tr>"
        )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='referrer' content='no-referrer'>"
        "<title>CBD job-step candidate DAG</title>"
        "<style>body{font:14px/1.5 system-ui;background:#142136;color:#f5f8ff;"
        "margin:22px}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #587086;padding:7px;text-align:left}"
        "a{color:#9fdcff}small{color:#ffcf91}table{display:block;"
        "overflow:auto}tr:nth-child(2n){background:#253951}</style>"
        "</head><body><h1>CBD first-red signature candidates</h1>"
        "<small>NOT causal roots / no security waivers / admission HOLD</small>"
        "<p>Bounded native API metadata; not a complete live repository census."
        " Run ID aliases are counted once. No raw logs published.</p>"
        "<table><thead><tr><th>Rank</th><th>Jobs</th><th>PR reach ceiling</th>"
        "<th>Workflow</th><th>Job</th><th>First failed step</th>"
        "<th>Classification</th><th>Evidence</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></body></html>\n"
    )


def write(dag, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    outputs = {
        "candidate_dag.json": canonical(dag) + "\n",
        "candidate_metrics.json": canonical(dag["metrics"]) + "\n",
        "candidate_sipoc.json": canonical(dag["sipoc"]) + "\n",
        "candidate_index.html": render_html(dag),
    }
    for name, data in outputs.items():
        (directory / name).write_text(data, encoding="utf-8")
    (directory / "sha256.json").write_text(
        canonical({
            k: hashlib.sha256(v.encode("utf-8")).hexdigest()
            for k, v in sorted(outputs.items())
        }) + "\n",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--native-jobs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    import cbd_260

    snapshot = cbd_260.read_n0(args.inputs)
    native = json.loads(args.native_jobs.read_text(encoding="utf-8"))
    graph = analyze(snapshot, native)
    write(graph, args.output_dir)
    print(canonical({"scope": graph["scope"], "metrics": graph["metrics"],
                     "root_confirmation": "UNKNOWN", "admission": "HOLD"}))


if __name__ == "__main__":
    main()
