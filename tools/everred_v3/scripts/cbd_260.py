"""CODE PURPLE CBD: bounded first-page PR failure inventory and optional native job scout.

The ten N0 source slices are frozen GitHub observations, not a new BD SSOT.
Native enrichment reuses EVERRED's exact-SHA, fully paginated job reader.
A repeated workflow/failed step is a signature candidate, NEVER a causal root.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SHA = re.compile(r"^[a-f0-9]{40}$")
SCHEMA = "abacus.everred.cbd.first_page_pr_failures.v1"
SUMMARY = "abacus.everred.cbd.portfolio_projection.v1"
OWNER_HINTS = {
    "CI/CD Test Suite": "MULTIPLE: source/job evidence needed",
    "ABACUS v032 - CI/CD Pipeline": "MULTIPLE: dependencies, format, security",
    "CI Workflow Governance": "#2041 / #1995 / #2037: canonical policy owner decision",
    "CI - ABACUS Matrix": "#2026 / #2045: Python compatibility owner",
    "a10-guard": "#1996: eligible independent restricted review",
    "Validate Docs (Markdown/YAML/JSON)": "#2058 / #2063: documents owner",
    "EVERRED V3 Governed Control Plane": "#2049 / #2004: formatter and engine owners",
    "Bandit Disjoint Census": "#1738 / #2027: security owner",
    "DMAIC V3 Enterprise CI": "#2026 / #2045: Python matrix owner",
    "CODE PURPLE SUT GUI Contract": "#1979: GUI contract owner",
}
COUNTS = ("success", "failure", "cancelled", "nonterminal")


def fail(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(s):
    return isinstance(s, str) and bool(SHA.fullmatch(s))


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def evidence_digest(data):
    return hashlib.sha256(canonical(data).encode("ascii")).hexdigest()


def read_n0(paths):
    fail(bool(paths) and len(paths) <= 32, "bounded N0 file list required")
    seen_files, rows, source_hashes = set(), [], {}
    repo = main = None
    for raw_path in sorted(map(Path, paths)):
        fail(raw_path.name not in seen_files, "duplicate N0 filename")
        seen_files.add(raw_path.name)
        raw = raw_path.read_bytes()
        d = json.loads(raw)
        fail(d.get("schema") == SCHEMA, "wrong N0 schema")
        fail(d.get("scope") == "PR_TRIGGERED_FIRST_PAGE_ASSOCIATION", "scope mismatch")
        fail(d.get("job_logs_read") is False and d.get("run_attempts_covered") is None,
             "unproved first-page completeness")
        fail(d.get("authority_transfer") is False and d.get("security_waiver") is False
             and d.get("merge_admission") == "HOLD", "authority promotion rejected")
        r, m = d.get("repository"), d.get("main_sha_at_observation")
        fail(r == "GBOGEB/ABACUS" and sha(m), "invalid repo/main identity")
        if repo is None:
            repo, main = r, m
        fail((repo, main) == (r, m), "mixed repository or main snapshots")
        fail(isinstance(d.get("rows"), list), "missing cohort rows")
        source_hashes[raw_path.name] = hashlib.sha256(raw).hexdigest()
        for row in d["rows"]:
            fail(isinstance(row, dict), "bad PR row")
            fail(type(row.get("pr")) is int and row["pr"] > 0
                 and row.get("state") == "open" and sha(row.get("head_sha")),
                 "PR head/state not bound")
            fail(isinstance(row.get("base"), str) and bool(row["base"]),
                 "missing base ref")
            c, runs = row.get("counts"), row.get("failed_runs")
            fail(isinstance(c, dict) and set(c) == set(COUNTS), "bad count shape")
            fail(all(type(c[k]) is int and c[k] >= 0 for k in COUNTS),
                 "invalid count")
            fail(isinstance(runs, list) and len(runs) == c["failure"],
                 "failed-workflow denominator mismatch")
            ids = set()
            for run in runs:
                fail(isinstance(run, dict), "bad failed run")
                rid = run.get("run_id")
                fail(type(rid) is int and rid > 0 and rid not in ids,
                     "invalid or repeated PR run ID")
                ids.add(rid)
                fail(isinstance(run.get("workflow"), str)
                     and bool(run["workflow"].strip()), "missing workflow")
                fail(run.get("run_attempt") is None and
                     run.get("first_red_job") is None and
                     run.get("first_red_step") is None and
                     run.get("root_id") is None, "forged first red or root")
            rows.append(row)
    numbers = [r["pr"] for r in rows]
    fail(len(set(numbers)) == len(numbers), "duplicate PR across N0 cohorts")
    rows.sort(key=lambda r: r["pr"], reverse=True)
    index, aliases = {}, []
    for row in rows:
        for run in row["failed_runs"]:
            rid = run["run_id"]
            entry = {"run_id": rid, "workflow": run["workflow"],
                     "workflow_id": run.get("workflow_id"),
                     "pr": row["pr"], "sha": row["head_sha"]}
            if rid in index:
                old = index[rid]
                fail(old["sha"] == entry["sha"]
                     and old["workflow"] == entry["workflow"]
                     and old["workflow_id"] == entry["workflow_id"],
                     "conflicting duplicate run identity")
                aliases.append({"run_id": rid, "pr": row["pr"],
                                "original_pr": old["pr"]})
            else:
                index[rid] = entry
    return {"repository": repo, "main_sha_at_observation": main,
            "source_sha256": source_hashes, "rows": rows,
            "unique_failed_runs": index, "duplicate_associations": aliases}


def project(snapshot, native=None):
    rows = snapshot["rows"]
    totals = {key: sum(r["counts"][key] for r in rows) for key in COUNTS}
    families, grouped = [], defaultdict(list)
    for row in rows:
        for run in row["failed_runs"]:
            grouped[run["workflow"]].append((row["pr"], run["run_id"]))
    for name, links in sorted(grouped.items(), key=lambda x: (-len(x[1]), x[0])):
        ids = sorted(set(run_id for _, run_id in links))
        families.append({
            "candidate_signature": "WFL-" + hashlib.sha256(
                name.encode("utf-8")).hexdigest()[:16],
            "workflow": name,
            "failed_associations": len(links),
            "distinct_failed_runs": len(ids),
            "affected_prs": sorted(set(pr for pr, _ in links)),
            "run_ids": ids,
            "owner_scout_hint": OWNER_HINTS.get(name, "READER_SCOUT_UNALLOCATED"),
            "causal_root_id": None,
            "confirmed_causal_root_count": None,
            "root_confirmation": "UNKNOWN_REQUIRES_JOB_LOG_AND_OWNER",
        })
    if native is None:
        native = {}
    statuses = Counter(x.get("status") for x in native.values())
    return {
        "schema": SUMMARY,
        "repository": snapshot["repository"],
        "main_sha_at_observation": snapshot["main_sha_at_observation"],
        "input_sha256": snapshot["source_sha256"],
        "evidence_scope": "PR_TRIGGERED_RUNS_FIRST_PAGE_PER_HEAD",
        "native_job_readback_scope": (
            "FULL_API_RUN_AND_PAGINATED_JOBS_PER_ID" if native
            else "NOT_COLLECTED"
        ),
        "metrics": {
            "prs_observed": len(rows),
            "distinct_pr_source_shas": len(set(r["head_sha"] for r in rows)),
            "workflow_associations": sum(totals.values()),
            "failed_workflow_associations": totals["failure"],
            "distinct_failed_run_ids": len(snapshot["unique_failed_runs"]),
            "duplicated_pr_failure_associations": len(
                snapshot["duplicate_associations"]),
            "passed_associations": totals["success"],
            "cancelled_associations": totals["cancelled"],
            "nonterminal_associations": totals["nonterminal"],
            "workflow_name_buckets": len(families),
            "job_readbacks_accepted": statuses["JOB_METADATA_BOUND"],
            "job_readbacks_withheld": statuses["READBACK_WITHHELD"],
            "native_complete_failure_job_denominator": None,
            "independently_confirmed_causal_roots": None,
            "open_causal_roots": None,
            "closed_causal_roots": None,
            "reopened_causal_roots": None,
            "current_main_coverage": None,
            "current_diff_coverage": None,
            "authenticated_crew_launches": None,
        },
        "families": families,
        "duplicate_associations": snapshot["duplicate_associations"],
        "safety": {
            "merge_admission": "HOLD", "authority_transfer": False,
            "security_waiver": False, "dispatch": "STAGED_NOT_LAUNCHED",
            "engineering_credit_delta": 0, "formal_root_closure_delta": 0,
            "candidate_is_not_root": True,
        },
    }


def enrich_native(snapshot, reader, *, workers=4, limit=256):
    """Read exact-run source/job/step metadata, no workflow reruns or source writes."""
    index = snapshot["unique_failed_runs"]
    fail(type(workers) is int and 1 <= workers <= 8, "invalid scout worker cap")
    fail(type(limit) is int and 1 <= limit <= 512, "invalid scout run bound")
    fail(len(index) <= limit, "run bound exceeded; split into another pulse")

    def one(entry):
        rid, src = entry
        try:
            run, jobs = reader.run_and_jobs(
                snapshot["repository"], rid, src["sha"])
            fail(run.get("id") == rid and
                 run.get("head_sha") == src["sha"] and
                 run.get("name") == src["workflow"] and
                 run.get("conclusion") == "failure" and
                 type(run.get("run_attempt")) is int and
                 run["run_attempt"] > 0, "unqualified native run")
            failed = []
            for job in jobs:
                if job.get("conclusion") != "failure":
                    continue
                steps = [s for s in (job.get("steps") or [])
                         if s.get("conclusion") in
                         ("failure", "timed_out", "action_required")]
                steps.sort(key=lambda s: s.get("number") if
                           type(s.get("number")) is int else 10**9)
                failed.append({
                    "job_id": job["id"], "job_name": job.get("name"),
                    "job_started_at": job.get("started_at"),
                    "job_completed_at": job.get("completed_at"),
                    "first_failed_step": (
                        {"number": steps[0].get("number"),
                         "name": steps[0].get("name")}
                        if steps else None),
                    "step_causality": "UNATTRIBUTED",
                })
            failed.sort(key=lambda x: x["job_id"])
            return rid, {
                "status": "JOB_METADATA_BOUND", "run_attempt": run["run_attempt"],
                "workflow": src["workflow"], "head_sha": src["sha"],
                "run_created_at": run.get("created_at"),
                "run_started_at": run.get("run_started_at"),
                "updated_at": run.get("updated_at"),
                "failed_jobs": failed,
                "failed_job_count": len(failed),
                "first_red_causal_root": None,
                "full_log_read": False,
                "trust": "GITHUB_API_METADATA_NOT_CAUSAL_CONFIRMATION",
            }
        except Exception:
            # Missing/inconsistent source is an unknown readback, never a pass.
            return rid, {
                "status": "READBACK_WITHHELD", "run_attempt": None,
                "failed_jobs": None, "first_red_causal_root": None,
                "full_log_read": False,
                "trust": "NO_NATIVE_CUSTODY",
            }
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, sorted(index.items())))


def wave_plan(proj):
    families = proj["families"]
    return {
        "schema": "abacus.everred.cbd.sipoc_wave_plan.v1",
        "source_projection_digest": evidence_digest(proj),
        "s":"ABACUS source, native run/job/step APIs, BD/LDAB owner, scanner and test logs",
        "i":"exact PR head, run/attempt/job, first material red, scan config and scope",
        "p":[
            {"wave":"N0", "kind":"DESCRIPTIVE_CENSUS",
             "state":"SOURCE_OBSERVED",
             "work":"PR-head and first-page run association capture"},
            {"wave":"N1", "kind":"READ_ONLY_NATIVE_SCOUT",
             "state":"CANDIDATE_UNTIL_NATIVE",
             "work":"Exact-run paginated jobs and first failed step; no root credit"},
            {"wave":"N2", "kind":"CAUSAL_FIRST_RED",
             "state":"NOT_STARTED",
             "work":"Retrieve failed-job logs; classify common predecessor vs downstream rollup"},
            {"wave":"N3", "kind":"DISJOINT_SOURCE_REPAIR",
             "state":"OWNER_PENDING",
             "work":"Allocate non-overlapping paths and fix one canonical cause per owner"},
            {"wave":"N4", "kind":"POSITIVE_NEGATIVE_COVERAGE",
             "state":"NOT_STARTED",
             "work":"Run matched regression, branch and diff coverage; do not lower gate"},
            {"wave":"N5", "kind":"GOVERNED_FANIN",
             "state":"HOLD",
             "work":"A10/Safety/governance, reviewer, exact main, distinct SHA recurrence"},
        ],
        "o":"root candidates, negative tests, exact-head receipt, BD/REX and HTML projections",
        "c":"DOW owner, KEB provenance, MissionControl viewer, QPS engineering consumer",
        "bounded_parallelism": {
            "read_only_scout_workers_max": 4,
            "source_mutation_workers_max_before_owner_lease": 0,
            "source_mutation_workers_after_disjoint_owner_lease_max": 2,
            "authenticated_crew_launches": None,
        },
        "top4_workflow_associations": sum(
            f["failed_associations"] for f in families[:4]),
        "top6_workflow_associations": sum(
            f["failed_associations"] for f in families[:6]),
        "independent_root_closure_forecast": None,
        "causal_success_prediction": "WITHHELD_UNTIL_QUALIFIED_MATCHED_TRIALS",
    }


def render_html(proj):
    esc = lambda x: html.escape(str(x), quote=True)
    rows = []
    for f in proj["families"]:
        cells = "".join(
            "<li><a href='https://github.com/GBOGEB/ABACUS/actions/runs/"
            + str(n) + "'>Run " + str(n) + "</a></li>"
            for n in f["run_ids"])
        rows.append(
            "<details><summary><b>" + esc(f["workflow"]) + "</b> · "
            + str(f["failed_associations"]) + " associations / "
            + str(f["distinct_failed_runs"]) + " distinct runs</summary>"
            + "<p><b>Owner scout:</b> " + esc(f["owner_scout_hint"])
            + " · <b>Root confirmation:</b> UNKNOWN</p><p><b>PRs:</b> "
            + ", ".join(
                "<a href='https://github.com/GBOGEB/ABACUS/pull/"
                + str(n) + "'>#" + str(n) + "</a>"
                for n in f["affected_prs"])
            ) + "</p><ul>" + cells + "</ul></details>")
    m = proj["metrics"]
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='referrer' content='no-referrer'>"
        "<title>CBD / EVERRED failed workflow census</title>"
        "<style>:root{color-scheme:dark}body{margin:0;background:#0e1d2e;"
        "color:#f0f6ff;font:15px/1.5 system-ui}main{max-width:1180px;"
        "margin:auto;padding:20px}a{color:#9ad7ff}code{overflow-wrap:anywhere}"
        "h1{font-size:clamp(23px,4vw,38px)}.grid{display:grid;"
        "grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:11px}"
        ".metric,details{background:#1a3149;border:1px solid #577b97;"
        "border-radius:9px;padding:13px;margin:12px 0}.metric b{font-size:26px;"
        "display:block}summary{cursor:pointer}ul{display:flex;flex-wrap:wrap;"
        "gap:8px;padding-left:16px}li{margin-right:12px}p{overflow-wrap:anywhere}"
        ".hold{color:#ffd19b}</style></head><body><main>"
        "<small>CODE PURPLE / CBD! / EVERRED V3 / READ-ONLY</small>"
        "<h1>75-PR failed workflow census</h1>"
        "<p class='hold'><b>HOLD:</b> 260 failure associations are not 260 causal "
        "roots. Job-log attribution, security admission and main coverage remain "
        "UNKNOWN.</p><div class='grid'>"
        + "".join(
            "<div class='metric'><b>" + esc(m[k])
            + "</b>" + esc(label) + "</div>"
            for k, label in (
                ("prs_observed", "PR heads"),
                ("failed_workflow_associations", "Failure associations"),
                ("distinct_failed_run_ids", "Distinct failed run IDs"),
                ("workflow_name_buckets", "Workflow name buckets"),
                ("job_readbacks_accepted", "Native jobs read"),
            ))
        + "</div><p>Scope: " + esc(proj["evidence_scope"])
        + ". Linked runs below retain exact run identity; same workflow "
        "name is an analytic grouping, not source-cause proof.</p>"
        + "".join(rows)
        + "<p><a href='https://github.com/GBOGEB/ABACUS/issues/1929'>"
        "Canonical BD–LDAB owner</a> · "
        "<a href='https://github.com/GBOGEB/ABACUS/issues/1860'>"
        "P0 admission authority</a></p></main></body></html>\n"
    )


def build(paths, output_dir, native=None):
    snapshot = read_n0(paths)
    proj = project(snapshot, native)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "summary.json": canonical(proj) + "\n",
        "wave_plan.json": canonical(wave_plan(proj)) + "\n",
        "index.html": render_html(proj),
    }
    if native is not None:
        output["native_jobs.json"] = canonical(native) + "\n"
    for name, value in output.items():
        (output_dir / name).write_text(value, encoding="utf-8")
    (output_dir / "sha256.json").write_text(
        canonical({name: hashlib.sha256(data.encode("utf-8")).hexdigest()
                   for name, data in sorted(output.items())}) + "\n",
        encoding="utf-8")
    return proj


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--enrich-native", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-native-runs", type=int, default=256)
    args = parser.parse_args(argv)
    snapshot = read_n0(args.inputs)
    native = None
    if args.enrich_native:
        from native_ingest import GitHubReadOnly
        native = enrich_native(snapshot, GitHubReadOnly(), workers=args.workers,
                               limit=args.max_native_runs)
    proj = build(args.inputs, args.output_dir, native)
    print(canonical({"status": "READ_ONLY", "metrics": proj["metrics"],
                     "root_closure_credit": 0, "admission": "HOLD"}))


if __name__ == "__main__":
    main()
