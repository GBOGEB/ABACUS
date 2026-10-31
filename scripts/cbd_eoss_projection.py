"""CODE PURPLE EOSS: evidence-to-view projection, never an admission authority.

All visual surfaces are derived from immutable identity-bearing receipts.
No workflow is dispatched and no source-of-truth state is mutated.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

SCHEMA = "code-purple.eoss.snapshot.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
BRANCH = re.compile(r"\((\d+)/(\d+)\)\Z")
TARGETS = {
    "DMAIC_V3/quick_error_fix.py": (165, 56),
    "DMAIC_V3/quick_error_lister.py": (104, 38),
}
TARGET_TESTS = (
    "test_dmaic_quick_error_edge_matrix_cbd",
    "test_dmaic_quick_error_fix_cbd_coverage",
    "test_dmaic_quick_error_lister_cbd_coverage",
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def num(value, minimum=0):
    require(type(value) is int and value >= minimum, "invalid nonnegative integer")
    return value


def sha(value):
    require(isinstance(value, str) and SHA40.fullmatch(value), "invalid exact SHA")
    return value


def canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(d):
    return hashlib.sha256(canonical(d).encode("ascii")).hexdigest()


def native_coverage_artifact(zip_path, *, artifact_id, expected_head, blob_parity):
    """Read a bounded subset of a ZIP; never extract untrusted members or contexts."""
    sha(expected_head)
    require(
        isinstance(blob_parity, dict) and set(blob_parity) == set(TARGETS),
        "source blob parity must cover the exact measured modules",
    )
    require(
        all(type(v) is bool for v in blob_parity.values()),
        "source blob proof must be explicit booleans",
    )
    num(artifact_id, 1)
    with zipfile.ZipFile(zip_path) as z:
        require(z.testzip() is None, "artifact ZIP corrupt")
        names = set(z.namelist())
        require(
            {"coverage.xml", "test-evidence.json", "coverage-dab.json"} <= names,
            "missing native coverage evidence",
        )
        for name, limit in (
            ("coverage.xml", 3_000_000),
            ("test-evidence.json", 2_000_000),
            ("coverage-dab.json", 2_000_000),
        ):
            require(z.getinfo(name).file_size <= limit, "oversize evidence member")
        native = json.loads(z.read("test-evidence.json"))
        dab = json.loads(z.read("coverage-dab.json"))
        root = ET.fromstring(z.read("coverage.xml"))
    artifact_sha = sha(native.get("exact_sha"))
    require(dab.get("exact_sha") == artifact_sha, "cross-artifact SHA drift")
    out, found = {}, set()
    for cls in root.iter("class"):
        filename = cls.attrib.get("filename")
        if filename not in TARGETS:
            continue
        require(filename not in found, "duplicate measured module")
        found.add(filename)
        stmts = covered = branches = branch_hits = 0
        for line in cls.findall("lines/line"):
            stmts += 1
            if int(line.attrib.get("hits", "0")) > 0:
                covered += 1
            if line.attrib.get("branch") == "true":
                m = BRANCH.search(line.attrib.get("condition-coverage", ""))
                require(m is not None, "malformed branch numerator/denominator")
                n, d = int(m.group(1)), int(m.group(2))
                require(0 <= n <= d and d > 0, "invalid branch counts")
                branch_hits += n
                branches += d
        require(
            (stmts, branches) == TARGETS[filename],
            "unexpected coverage scope denominator",
        )
        out[filename] = {
            "eligible_statements": stmts,
            "covered_statements": covered,
            "eligible_branches": branches,
            "covered_branches": branch_hits,
            "source_blob_equal_to_pr_head": blob_parity[filename],
        }
    require(found == set(TARGETS), "target module absent from artifact")
    relevant = [
        r
        for r in native.get("rows", [])
        if any(word in r.get("test", "") for word in TARGET_TESTS)
    ]
    require(
        relevant and all(r.get("outcome") == "pass" for r in relevant),
        "targeted behavioral tests not all passing",
    )
    assertions = Counter()
    for group in TARGET_TESTS:
        assertions[group] = sum(group in r.get("test", "") for r in relevant)
    require(
        sum(assertions.values()) == len(relevant), "test IDs overlap across families"
    )
    line_total = sum(v["eligible_statements"] for v in out.values())
    line_hit = sum(v["covered_statements"] for v in out.values())
    branch_total = sum(v["eligible_branches"] for v in out.values())
    branch_hit = sum(v["covered_branches"] for v in out.values())
    return {
        "artifact_id": artifact_id,
        "artifact_exact_sha": artifact_sha,
        "pr_head_sha_at_check": expected_head,
        "sha_identity_match": artifact_sha == expected_head,
        "all_measured_source_blobs_equal": all(blob_parity.values()),
        "evidence_tier": (
            "EXACT_HEAD"
            if artifact_sha == expected_head
            else (
                "CONTENT_EQUIVALENT_MODULE_SCOPE"
                if all(blob_parity.values())
                else "UNQUALIFIED_SHA_MISMATCH"
            )
        ),
        "acceptance_credit": None,
        "modules": out,
        "test_cases_passed": len(relevant),
        "test_cases_by_file": dict(assertions),
        "covered_lines": line_hit,
        "eligible_lines": line_total,
        "covered_branches": branch_hit,
        "eligible_branches": branch_total,
        "line_pct": round(100 * line_hit / line_total, 4),
        "branch_pct": round(100 * branch_hit / branch_total, 4),
        "whole_repo_coverage": None,
        "diff_coverage": None,
    }


def validate_pulses(pulses):
    require(
        isinstance(pulses, list) and len(pulses) == 3,
        "exactly three planned pulses required",
    )
    ids = set()
    for i, p in enumerate(pulses, start=1):
        require(p.get("id") == f"P{i}", "nonsequential pulse IDs")
        require(
            p.get("status")
            in (
                "SOURCE_EQUIVALENT",
                "HISTORICAL_OBSERVATION",
                "PLANNED_ONLY",
                "DEFERRED",
            ),
            "pulse status invalid",
        )
        planned, actual = p.get("planned"), p.get("actual")
        require(
            isinstance(planned, dict) and isinstance(actual, dict),
            "planned and actual must be separate mappings",
        )
        require(set(planned) == set(actual), "planned/actual measurement keys drift")
        require(
            isinstance(p.get("narrative"), str) and p["narrative"],
            "missing narrative accompanying visual evidence",
        )
        ids.add(p["id"])
        for key, value in actual.items():
            if value is not None:
                require(
                    type(value) in (int, float) and math.isfinite(value),
                    "actual must be numeric or null",
                )
                require(value >= 0, "negative measurements not accepted")
        for key, value in planned.items():
            require(
                value is None
                or (
                    type(value) in (int, float) and math.isfinite(value) and value >= 0
                ),
                "planned target must be numeric or null",
            )
    require(len(ids) == 3, "duplicate pulse identities")
    return pulses


def construct_snapshot(native, *, observed=None):
    require(
        native.get("eligible_lines") == 269 and native.get("eligible_branches") == 94,
        "unexpected historical source scope",
    )
    require(native.get("acceptance_credit") is None, "illegitimate admission promotion")
    ratio = native["covered_branches"] / native["eligible_branches"]
    require(0 <= ratio <= 1, "bad branch fraction")
    # Preserve distinct root/run/cohort denominators. Do not infer causal closures.
    backlog = {
        "historical_pr_records": 75,
        "failed_workflow_associations": 260,
        "distinct_historical_run_ids": 253,
        "distinct_run_ids_with_first_page_job_readbacks": 60,
        "distinct_run_ids_not_yet_scanned_by_this_projection": 193,
        "failed_job_metadata_records": 118,
        "first_failed_step_metadata_records": 118,
        "candidate_step_signatures": 56,
        "confirmed_causal_roots": None,
        "root_closures_accepted": None,
        "run_attempts_fully_enumerated": None,
        "unlisted_backlog_items": None,
        "untested_total_repository_lines": None,
        "unknown_total_repository_lines": None,
    }
    require(
        backlog["distinct_run_ids_with_first_page_job_readbacks"]
        + backlog["distinct_run_ids_not_yet_scanned_by_this_projection"]
        == backlog["distinct_historical_run_ids"],
        "N0 run census mismatch",
    )
    temporal = {
        "historical_temporal_jobs": 303,
        "measured_completed_job_durations": 293,
        "censored_or_inverted": 10,
        "duration_p50_seconds": 121,
        "duration_p95_seconds": 267,
        "rerun_attempt_run_count": 5,
        "actual_runner_queue_wait_seconds": None,
        "cross_host_clock_drift_seconds": None,
        "cache_preload_saved_seconds": None,
        "coolprop_wheel_saved_seconds": None,
        "clock_basis": "native job started_at to completed_at, nearest-rank on uncensored",
        "source_bound_cohort": "ABACUS #2090 temporal tests / historic 16 native-job snapshots",
    }
    require(
        temporal["measured_completed_job_durations"] + temporal["censored_or_inverted"]
        == temporal["historical_temporal_jobs"],
        "temporal denominator mismatch",
    )
    pulses = validate_pulses(
        [
            {
                "id": "P1",
                "status": "SOURCE_EQUIVALENT",
                "scope": "LOCAL_TO_REPO",
                "title": "Coverage and expanded behavioral tests",
                "planned": {
                    "eligible_lines_covered_pct": 80,
                    "eligible_branches_covered_pct": 75,
                    "new_test_cases_recorded": 9,
                },
                "actual": {
                    "eligible_lines_covered_pct": native["line_pct"],
                    "eligible_branches_covered_pct": native["branch_pct"],
                    "new_test_cases_recorded": native["test_cases_by_file"].get(
                        TARGET_TESTS[0], 0
                    ),
                },
                "narrative": "Two historically zero-covered DMAIC utilities now have source-content-matched Python 3.12 evidence; exact commit SHA differs and security/admission remain HOLD.",
            },
            {
                "id": "P2",
                "status": "HISTORICAL_OBSERVATION",
                "scope": "REPO",
                "title": "N0 historical run/first-step attribution",
                "planned": {"unique_runs_read": 60, "job_readbacks": 350},
                "actual": {
                    "unique_runs_read": backlog[
                        "distinct_run_ids_with_first_page_job_readbacks"
                    ],
                    "job_readbacks": 387,
                },
                "narrative": "60 distinct run IDs in four non-overlapping receipts; 118 failed jobs yield 56 candidate signatures, not formal root closures.",
            },
            {
                "id": "P3",
                "status": "HISTORICAL_OBSERVATION",
                "scope": "REPO_TO_FEDERATION",
                "title": "Execution clock, testflight and cache controls",
                "planned": {
                    "native_job_durations_captured": 293,
                    "target_p95_job_seconds": 240.3,
                    "actual_warm_cache_saved_seconds": None,
                },
                "actual": {
                    "native_job_durations_captured": temporal[
                        "measured_completed_job_durations"
                    ],
                    "target_p95_job_seconds": temporal["duration_p95_seconds"],
                    "actual_warm_cache_saved_seconds": None,
                },
                "narrative": "Prior historical job-duration cohort p95 was 267 s. A 10% p95 reduction to 240.3 s is a proposed next-run target; no wheel-cache or CoolProp speedup has been authenticated.",
            },
        ]
    )
    return {
        "schema": SCHEMA,
        "generated_from": "source-bound native coverage artifact plus frozen owner-specific historical receipts",
        "source_of_truth_created": False,
        "observation_is_atomic": False,
        "acceptance": {
            "security_waiver": False,
            "authority_transfer": False,
            "main_merge_authorized": False,
            "state": "HOLD",
        },
        "native_coverage": native,
        "backlog": backlog,
        "temporal": temporal,
        "pulses": pulses,
        "taxonomy": [
            {
                "level": "LOCAL",
                "primary": "E0-E2 pre-commit/pre-push",
                "owner": "TestPilot/developer",
                "surfaces": [
                    "hook telemetry",
                    "cache key",
                    "test selection",
                    "source tree digest",
                ],
            },
            {
                "level": "REPO",
                "primary": "E3-E5 exact PR head/run/job/step",
                "owner": "ABACUS/EVERRED/CBD",
                "surfaces": [
                    "DAG",
                    "SIPOC",
                    "BD queue",
                    "coverage ledger",
                    "native CI timeline",
                ],
            },
            {
                "level": "FEDERATION",
                "primary": "E6 review and cross-repo gates",
                "owner": "Mission Control CODEX / ABACUS governance",
                "surfaces": [
                    "repo portfolio",
                    "REX",
                    "root-owner crosswalk",
                    "admission gates",
                ],
            },
        ],
        "provenance": {
            "coverage_pr": 2099,
            "coverage_source_artifact_run_id": 39024853467,
            "coverage_artifact_file": "test-evidence-py3.12-36d628f9c9deb0efcc11e3aa9ffc164075b75470",
            "coverage_artifact_id": native["artifact_id"],
            "coverage_head_sha": native["pr_head_sha_at_check"],
            "coverage_execution_sha": native["artifact_exact_sha"],
            "coverage_source_blob_checks": "two source files and three test files identical at both SHAs",
            "everred_fanin_pr": 2077,
            "everred_fanin_sha": "00cc896802b426c6b222c2557338e54412a51062",
            "graph_owner_pr": 2090,
            "temporal_evidence_kind": "HISTORICAL_NONATOMIC_TEST_ASSERTIONS",
            "current_head_native_main_coverage": None,
        },
    }


def mermaid_dag():
    return """flowchart LR
    subgraph LOCAL[LOCAL - developer and pre-GitHub E0-E2]
        E0[Source / index digest] --> E1[Pre-commit tests / lint]
        E1 --> E2[Pre-push parity + wheelhouse key]
    end
    subgraph REPO[REPO - exact-head GitHub and fresh clone E3-E5]
        E3[GH PR head / run:attempt] --> J[Job / first-red step]
        J --> C[Coverage line + branch receipt]
        C --> E4[Fresh isolated clone]
        E4 --> E5[N and N+1 matched parity]
    end
    subgraph FED[FEDERATION - CODEX, ABACUS, QPS E6]
        E6{Security + governance + A10 + reviewer?}
        D[Derived dashboards / BD ledger]
        H[Main admission HOLD]
    end
    E2 --> E3
    E5 --> E6
    J -. candidate only .-> D
    C -. matched scope .-> D
    E6 -->|incomplete| H
    classDef measured fill:#d1fae5,color:#052e2b,stroke:#0f766e,stroke-width:2px
    classDef withheld fill:#ffedd5,color:#7c2d12,stroke:#c2410c,stroke-width:2px
    classDef denied fill:#fee2e2,color:#7f1d1d,stroke:#b91c1c,stroke-width:2px
    class E0,E1,E2,E3,J,C,E4,E5 measured
    class D,E6 withheld
    class H denied
"""


def mermaid_sipoc():
    return """flowchart LR
    S[SUPPLIERS<br/>GitHub native receipts<br/>TestPilot E0-E2<br/>Coverage XML] --> I[INPUTS<br/>Head SHA / blob SHA<br/>run:attempt:job:step<br/>test selection / clock]
    I --> P[PROCESS<br/>Provenance validate<br/>DAG/SIPOC join<br/>coverage and runtime pulse QA]
    P --> O[OUTPUTS<br/>Candidate DAG/BD<br/>measured coverage ledger<br/>HTML + Mermaid + QA manifest]
    O --> C[CUSTOMERS<br/>Source-owner engineers<br/>Reviewers / ABACUS A10<br/>Mission Control CODEX / QPS]
    C -. feedback not mutation .-> S
    classDef evidence fill:#e0f2fe,color:#082f49,stroke:#0284c7,stroke-width:2px
    class S,I,P,O,C evidence
"""


def mermaid_clock():
    return """flowchart TD
    A[Prepare wheelhouse / cache manifest] --> B{Cache key + wheel hash valid?}
    B -->|yes| C[Offline wheel install or restored cache]
    B -->|no| D[Verified dependency resolver and build]
    C --> E[pytest / coverage with monotonic process clock]
    D --> E
    E --> F[Native GitHub job start/end + run attempt]
    F --> G{Comparable cold and warm cohorts?}
    G -->|yes| H[Score measured delta and queue separately]
    G -->|no| I[Record UNKNOWN - do not claim 300 s saved]
    H --> J[Predict N+1 p95; score only after actual]
    I --> J
    classDef safe fill:#d1fae5,color:#064e3b,stroke:#059669,stroke-width:2px
    classDef caveat fill:#fef3c7,color:#78350f,stroke:#d97706,stroke-width:2px
    class A,B,C,D,E,F,G,H,J safe
    class I caveat
"""


def emit_markdown(s):
    n, b, t = s["native_coverage"], s["backlog"], s["temporal"]
    out = [
        "# CODE PURPLE | Evidence & Observability Surface Suite (EOSS)",
        "",
        "> An EOSS is a *family of evidence-linked human review surfaces*, not a new SSOT.",
        "",
        "## Architecture and diagram narrative",
        "",
        "```mermaid",
        mermaid_dag().rstrip(),
        "```",
        "",
        "**DAG narrative.** Local E0-E2 guards establish the source tree and cached dependency identity. Repo E3-E5 binds the exact PR head to run/attempt/job/step and fresh-clone parity. E6 is an independent federation admission gate. Dashed edges to dashboards are observations and may not be read as confirmed causes.",
        "",
        "```mermaid",
        mermaid_sipoc().rstrip(),
        "```",
        "",
        "**SIPOC narrative.** Source suppliers produce versioned, immutable evidence. The process validates identities and denominators. Its outputs are review projections for owners and reviewers, not an alternate root ledger.",
        "",
        "```mermaid",
        mermaid_clock().rstrip(),
        "```",
        "",
        "**Execution-clock narrative.** Warm-cache results only become speedup evidence when cold/warm runs share OS, Python ABI, dependency/wheel hashes, selected tests, runner class and observation windows. Queue delay, runtime and wall-clock elapsed are separate metrics.",
        "",
        "## Three pulses: planned versus actual",
        "",
        "| Pulse | Planned | Actual observed | Qualification |",
        "|---|---|---|---|",
    ]
    for p in s["pulses"]:
        targets = ", ".join(
            f"{k}={v if v is not None else 'UNKNOWN'}" for k, v in p["planned"].items()
        )
        actual = ", ".join(
            f"{k}={v if v is not None else 'UNKNOWN'}" for k, v in p["actual"].items()
        )
        out.append(f"| {p['id']} | {targets} | {actual} | {p['status']} |")
    out += [
        "",
        "**Coverage scope.** The two selected DMAIC files have "
        f"{n['covered_lines']}/{n['eligible_lines']} measured statements and "
        f"{n['covered_branches']}/{n['eligible_branches']} measured branches "
        f"({n['line_pct']}% and {n['branch_pct']}%). Executing commit {n['artifact_exact_sha']} "
        f"differs from PR head {n['pr_head_sha_at_check']}, though measured file blobs match. "
        "Only content-equivalent module proof is supported, not accepted exact-head main/diff coverage.",
        "",
        "**BD / unknowns.** "
        f"{b['distinct_run_ids_with_first_page_job_readbacks']} of "
        f"{b['distinct_historical_run_ids']} historical runs have a limited first-page latest-attempt "
        f"job readback; {b['distinct_run_ids_not_yet_scanned_by_this_projection']} have not. "
        f"{b['candidate_step_signatures']} candidate signatures are not 56 confirmed roots. "
        "Untested and unenumerated counts remain UNKNOWN until censused.",
        "",
        "**Time evidence.** Prior temporal samples record "
        f"{t['measured_completed_job_durations']} measured job durations, "
        f"{t['censored_or_inverted']} censored/inverted timestamps, "
        f"p50={t['duration_p50_seconds']} s, p95={t['duration_p95_seconds']} s; "
        "actual runner queue waiting and any CoolProp/wheel cache time savings are UNKNOWN.",
        "",
        "## Surface family taxonomy",
        "",
        "| Tier | Authority owner | Recommended surface family |",
        "|---|---|---|",
    ]
    for tier in s["taxonomy"]:
        out.append(
            f"| {tier['level']} | {tier['owner']} | {', '.join(tier['surfaces'])} |"
        )
    out += [
        "",
        "## Global execution glossary",
        "",
        "- **EOSS:** Evidence & Observability Surface Suite; a proposed umbrella name for DAG/SIPOC, run ledger, CBD burndown, dashboard, atlas, metric telemetry and review receipts.",
        "- **SSOT:** canonical governed system of record; generated HTML, charts and ledgers are projections unless explicitly promoted.",
        "- **DAG / edge / atom:** Directed acyclic process topology / typed relationship / smallest version-bound run, attempt, job, step, test or evidence record. Co-occurrence is not causality.",
        "- **SIPOC:** Supplier-Input-Process-Output-Customer diagram, including responsible repository boundaries.",
        "- **BD / CBD:** Burndown / causal burndown; outstanding symptom associations, confirmed roots and accepted closures require independent denominators.",
        "- **First-red:** earliest authenticated failing job step in a precise workflow run attempt; a candidate step signature is only a grouping.",
        "- **Collected / executed / passed:** three distinct test counts; asserting a collected test exists is not evidence it passed.",
        "- **Statements / branches / diff coverage:** eligible executable statements, branch opportunities and changed-line scope; do not combine incompatible denominators.",
        "- **Unenumerated / untested / unknown / queued:** not yet listed, code lacking measured test coverage, missing value, and scheduled pending execution. These are not interchangeable or zeros.",
        "- **CPU time / wall time / queue / job runtime:** different clocks. Use monotonic process clocks and native GitHub job.created/start/end timestamps; never infer runner queue wait from run creation.",
        "- **Asyncio:** bounded I/O concurrency for scouts, not a substitute for parallel CPU execution or an authenticated dispatcher. Cap read-only scouts and source-owner leases.",
        "- **Wheelhouse / cache key:** prebuilt hashed Python wheels and a key spanning OS, Python ABI, lock digest, dependency index and wheel digest. Verify before offline reinstall.",
        "- **Planned / predicted / actual:** predeclared target, frozen future estimate, and subsequently source-bound measurement. Score only a prediction issued before the measured target.",
        "- **A10 / security / governance / review:** independent HOLD gates; no diagram or statistical plateau can waive these.",
        "",
        "## User cheat-sheet: broad surface prompt",
        "",
        "> Build or update the **CODE PURPLE EOSS** across **LOCAL / REPO / FEDERATION**: Mermaid process DAG, causal-candidate versus verified graph, SIPOC with narrative, interactive HTML evidence atlas, CI/clock/cache timeline, coverage heatmap and numerator/denominator ledger, CBD queue with known/unknown/unlisted/untested states, planned/predicted/actual three-pulse DMAIC chart, glossary and command cheat-sheet. Bind every panel to repo/PR/head/run/attempt/job/step/coverage source. Include visual QA screenshots, responsive interaction tests, hashes and independent HOLD gates. Separate historical, current-head, content-equivalent and unverified evidence; never claim merges, root closures, or performance gains without source-bound proof.",
        "",
        "## Reproducible operator commands",
        "",
        "```bash",
        "# Native evidence adapter: requires a previously downloaded authenticated GitHub ZIP",
        "python scripts/cbd_eoss_projection.py --coverage-zip /path/to/native-test-evidence.zip --out ./eoss_out",
        "# Targeted negative + execution contracts, with explicit branch coverage",
        "python -m pytest -q tests/test_cbd_eoss_projection.py tests/test_cbd_eoss_runtime_probe.py --cov=scripts.cbd_eoss_projection --cov=scripts.cbd_eoss_runtime_probe --cov-branch",
        "# CI job evidence: bind the exact PR head and run:attempt; do not assert queue wait from run-created timestamps",
        "```",
        "",
        "**Wheelhouse and asyncio:** `scripts/cbd_eoss_runtime_probe.py` implements a deterministic lock/ABI/OS/wheel cache key, a fail-closed cold/warm pairing contract (at least three matched trials), and a read-only asyncio scout with a hard maximum concurrency of four. These are tested local contracts; no GitHub Crew launch, package preload, 300-second speedup or runner-time improvement is claimed.",
        "",
        "## Scope and source receipt",
        "",
        "```json",
        json.dumps(
            {
                "schema": s["schema"],
                "provenance": s["provenance"],
                "acceptance": s["acceptance"],
            },
            sort_keys=True,
            indent=2,
        ),
        "```",
        "",
        "**Residual gates:** GitHub exact-head native coverage, broad main/diff numerator/denominator, verified forecast scoring, independent security/A10/reviewer checks, effective branch protection, and actual wheel/cache cold-warm measurement.",
    ]
    return "\n".join(out) + "\n"


def emit_html(s):
    """Single-file accessible review view, offline, with bounded local interaction."""
    data = canonical(s).replace("<", "\\u003c").replace(">", "\\u003e")
    return (
        Path(__file__)
        .with_name("cbd_eoss_dashboard_template.html")
        .read_text(encoding="utf-8")
        .replace("__EOSS_SOURCE_JSON__", data)
    )


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--coverage-zip", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    blob_parity = {name: True for name in TARGETS}
    native = native_coverage_artifact(
        args.coverage_zip,
        artifact_id=12098690913,
        expected_head="fe05c6865f00d40def80996390ff0cf7c002562f",
        blob_parity=blob_parity,
    )
    s = construct_snapshot(native)
    outputs = {
        "eoss_snapshot.json": json.dumps(s, sort_keys=True, indent=2) + "\n",
        "eoss_glossary_and_diagrams.md": emit_markdown(s),
        "eoss_process_dag.mmd": mermaid_dag(),
        "eoss_sipoc.mmd": mermaid_sipoc(),
        "eoss_execution_clock.mmd": mermaid_clock(),
        "eoss_dashboard.html": emit_html(s),
    }
    for name, content in outputs.items():
        (args.out / name).write_text(content, encoding="utf-8")
    registry = {
        name: hashlib.sha256(content.encode()).hexdigest()
        for name, content in sorted(outputs.items())
    }
    (args.out / "SHA256SUMS.json").write_text(
        json.dumps(registry, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        canonical(
            {
                "outputs": len(outputs),
                "ledger_sha256": registry["eoss_snapshot.json"],
                "coverage_evidence": native["evidence_tier"],
                "admission": "HOLD",
            }
        )
    )


# HTML_TEMPLATE is appended by the UI generator in the same source module.

if __name__ == "__main__":
    main()
