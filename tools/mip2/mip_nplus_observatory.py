"""N+i evidence telemetry: exact-SHA read-only CI cohort comparisons.

No network, actions, merge authority, root closure, worker dispatch or waiver.
Native API records are observed evidence, not signed artifact-byte attestations.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from tools.mip2.workflow_family_metrics import summarize_families

SCHEMA = "abacus.nplus.native-ci-intake.v1"
OUTPUT = "abacus.nplus.telemetry.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = "GBOGEB/ABACUS"
TERMINAL = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "startup_failure",
    "neutral",
}
OPEN_STATES = {"queued", "pending", "in_progress", "requested", "waiting"}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def positive(x):
    return type(x) is int and x > 0


def rate(num, den):
    return round(num / den, 6) if den else None


def validate_wave(wave):
    require(isinstance(wave, dict), "wave must be object")
    name, sha = wave.get("wave"), wave.get("source_sha")
    require(isinstance(name, str) and re.fullmatch(r"N[0-9]+", name), "invalid N-index")
    require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid exact SHA")
    require(
        wave.get("source_role") == "HISTORICAL_MAIN_HEAD", "observed main head required"
    )
    url = (
        "https://api.github.com/repos/GBOGEB/ABACUS/actions/runs"
        f"?head_sha={sha}&event=push&per_page=100"
    )
    require(wave.get("api_url") == url, "unbound native API URL")
    rows = wave.get("runs")
    require(isinstance(rows, list) and len(rows) <= 100, "invalid run list")
    require(positive(wave.get("native_total_count")), "missing native denominator")
    require(len(rows) == wave["native_total_count"], "truncated API page; no credit")
    seen = set()
    families = defaultdict(list)
    count = Counter()
    for row in rows:
        require(isinstance(row, dict), "invalid workflow run")
        run_id, wf_id, attempt = (
            row.get("id"),
            row.get("workflow_id"),
            row.get("run_attempt"),
        )
        require(
            positive(run_id) and positive(wf_id) and positive(attempt),
            "invalid native run/attempt/workflow identity",
        )
        require(run_id not in seen, "duplicate native run")
        seen.add(run_id)
        require(
            row.get("head_sha") == sha and row.get("event") == "push",
            "mixed SHA or non-push event",
        )
        status, conclusion = row.get("status"), row.get("conclusion")
        require(status == "completed" or status in OPEN_STATES, "unknown run status")
        if status == "completed":
            require(conclusion in TERMINAL, "invalid terminal outcome")
            count[conclusion] += 1
        else:
            require(conclusion is None, "nonterminal with conclusion")
            count["nonterminal"] += 1
        families[wf_id].append(row)
    count["terminal"] = len(rows) - count["nonterminal"]
    family_breakdown = summarize_families(rows)
    return {
        "wave": name,
        "source_sha": sha,
        "runs": rows,
        "native_total_count": len(rows),
        "outcomes": dict(sorted(count.items())),
        "workflow_family_accounting": family_breakdown,
        "terminal_fraction": rate(count["terminal"], len(rows)),
        "success_fraction_all": rate(count["success"], len(rows)),
        "success_fraction_terminal": rate(count["success"], count["terminal"]),
        "status_population": "ALL_RETURNED_PUSH_RUNS_OF_ONE_EXACT_SHA",
        "root_open": None,
        "root_closed": None,
        "matched_main_coverage": None,
        "matched_diff_coverage": None,
        "authenticated_crew_launches": None,
        "first_governed_merge": None,
        "_families": families,
    }


def matched_workflow_flip(before, after):
    """Pair only workflow IDs occurring once on each head, both terminal."""
    b, a = before["_families"], after["_families"]
    counts = Counter()
    flips = []
    for wf in sorted(set(b) & set(a)):
        if len(b[wf]) != 1 or len(a[wf]) != 1:
            counts["duplicate_family_excluded"] += 1
            continue
        x, y = b[wf][0], a[wf][0]
        if x["status"] != "completed" or y["status"] != "completed":
            counts["nonterminal_excluded"] += 1
            continue
        counts["paired_terminal_families"] += 1
        old, new = x["conclusion"], y["conclusion"]
        failures = {"failure", "timed_out", "action_required", "startup_failure"}
        if old in failures and new == "success":
            label = "RECOVERED_FAILURE_OUTCOME"
        elif old == "success" and new in failures:
            label = "NEW_FAILURE_OUTCOME"
        elif old == "success" and new == "success":
            label = "UNCHANGED_SUCCESS"
        elif old == new:
            label = "UNCHANGED_OTHER"
        else:
            # Cancelled, skipped and neutral are not first-red evidence.
            label = "NONFAILURE_OUTCOME_TRANSITION"
        counts[label] += 1
        if label in ("NEW_FAILURE_OUTCOME", "RECOVERED_FAILURE_OUTCOME"):
            flips.append(
                {
                    "workflow_id": wf,
                    "from_run": x["id"],
                    "to_run": y["id"],
                    "before": old,
                    "after": new,
                    "classification": label,
                }
            )
    return {
        "counts": dict(sorted(counts.items())),
        "flips": flips,
        "status": "OBSERVATIONAL_DIFFERENT_HEADS",
        "causal_root_closure": None,
    }


def rollup(doc):
    require(isinstance(doc, dict) and doc.get("schema") == SCHEMA, "wrong input schema")
    require(doc.get("repository") == REPO, "foreign repository")
    require(
        doc.get("provenance") == "LIVE_GITHUB_CONNECTOR_READ_ONLY",
        "unverified acquisition label",
    )
    raw = doc.get("waves")
    require(
        isinstance(raw, list) and 2 <= len(raw) <= 25, "need 2..25 chronological waves"
    )
    waves = [validate_wave(w) for w in raw]
    indexes = [int(w["wave"][1:]) for w in waves]
    require(
        len(set(indexes)) == len(indexes)
        and indexes == list(range(indexes[0], indexes[0] + len(indexes))),
        "N-series must be consecutive and ordered",
    )
    all_ids = [row["id"] for w in waves for row in w["runs"]]
    require(
        len(all_ids) == len(set(all_ids)),
        "same run observed twice; not an independent cross-head sample",
    )
    comparisons = []
    for old, new in zip(waves, waves[1:]):
        comparisons.append(
            {
                "from": old["wave"],
                "to": new["wave"],
                "before_sha": old["source_sha"],
                "after_sha": new["source_sha"],
                "before_terminal": old["outcomes"]["terminal"],
                "before_total": old["native_total_count"],
                "after_terminal": new["outcomes"]["terminal"],
                "after_total": new["native_total_count"],
                "terminal_count_delta": (
                    new["outcomes"]["terminal"] - old["outcomes"]["terminal"]
                ),
                "cohort_comparability": "DISTINCT_RUN_POPULATIONS",
                "matched_workflows": matched_workflow_flip(old, new),
                "coverage_delta_pp": None,
                "root_closure_delta": None,
                "engineering_improvement_inferred": False,
            }
        )
    latest = waves[-1]
    blocked = latest["outcomes"].get("nonterminal", 0)
    sample = len(waves)
    # Diagnostics can expand; no mutation/merge authority is implied.
    read_only_proposal = min(8, max(1, (blocked + 3) // 4))
    clean_waves = [{k: v for k, v in w.items() if not k.startswith("_")} for w in waves]
    for w in clean_waves:
        del w["runs"]  # keep full native run population in input receipt
    return {
        "schema": OUTPUT,
        "repository": REPO,
        "waves": clean_waves,
        "comparisons": comparisons,
        "progress": {
            "latest_terminal": latest["outcomes"]["terminal"],
            "latest_denominator": latest["native_total_count"],
            "latest_nonterminal": blocked,
            "latest_nonterminal_fraction": rate(blocked, latest["native_total_count"]),
            "latest_success": latest["outcomes"].get("success", 0),
            "latest_distinct_workflows": latest["workflow_family_accounting"][
                "distinct_workflows"
            ],
            "latest_repeated_run_excess": latest["workflow_family_accounting"][
                "repeated_executions"
            ],
            "latest_clean_workflow_families": latest["workflow_family_accounting"][
                "family_clean_success"
            ],
            "latest_repeat_success_excess": latest["workflow_family_accounting"][
                "success_excess_from_repeat_runs"
            ],
            "latest_workflow_testcase_count": None,
            "queue_congestion": "OBSERVED" if blocked else "NO_OPEN_RUNS_IN_CENSUS",
            "issue_housekeeping_delta": None,
            "verified_root_closure_delta": None,
            "matched_main_coverage_delta_pp": None,
            "matched_diff_coverage_delta_pp": None,
            "first_governed_main_merge": None,
            "p0_admission": "HOLD",
            "stability_decision": (
                "INSUFFICIENT_INDEPENDENT_SERIES"
                if sample < 20
                else "M2_DIAGNOSTIC_ELIGIBILITY_REVIEW_ONLY"
            ),
            "observed_main_heads": sample,
            "minimum_m2_screening_heads": 20,
            "bradley_terry": "NOT_ASSESSABLE",
            "pca": "NOT_ASSESSABLE",
        },
        "scaling": {
            "read_only_diagnostic_lanes_proposed": read_only_proposal,
            "mutation_lanes_authorized": None,
            "worker_launch_receipts": None,
            "next_action": "CLEAR_QUEUE_AND_P0_GATES_BEFORE_MUTATION_SCALE",
            "scale_does_not_mean_worker_launch": True,
        },
        "authority_transfer": False,
        "security_waiver": False,
        "merge_authorized": False,
        "native_artifact_bytes_reauthenticated": False,
    }


def as_markdown(r):
    lines = [
        "# CODE PURPLE N+i — native CI cohort observatory",
        "",
        "Distinct main-SHA push-run populations; **not matched coverage or "
        "engineering-root closures**.",
        "",
        "| Wave | SHA | Runs | Families | Repeat extras | Extra green repeats | Green families | Success | Failed | Cancelled | Open | Success/all | Terminal/all |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for w in r["waves"]:
        c = w["outcomes"]
        fam = w["workflow_family_accounting"]
        lines.append(
            f"| {w['wave']} | {w['source_sha'][:12]} | "
            f"{w['native_total_count']} | {fam['distinct_workflows']} | "
            f"{fam['repeated_executions']} | "
            f"{fam['success_excess_from_repeat_runs']} | "
            f"{fam['family_clean_success']}/{fam['distinct_workflows']} | "
            f"{c.get('success', 0)} | {c.get('failure', 0)} | "
            f"{c.get('cancelled', 0)} | {c.get('nonterminal', 0)} | "
            f"{c.get('success', 0)}/{w['native_total_count']} | "
            f"{c['terminal']}/{w['native_total_count']} |"
        )
    lines.extend(
        [
            "",
            "Repeat-adjusted counts are diagnostic only; test cases, matched coverage and formal root closures remain UNKNOWN.",
            "",
            "## Sequential paired-family observations",
            "",
            "A family is paired only when unique and terminal on both "
            "different heads. Status changes **do not prove causation**.",
            "",
        ]
    )
    for comparison in r["comparisons"]:
        c = comparison["matched_workflows"]["counts"]
        lines.append(
            f"- {comparison['from']} -> {comparison['to']}: "
            f"paired={c.get('paired_terminal_families', 0)}, "
            f"recovered-failure-outcome={c.get('RECOVERED_FAILURE_OUTCOME', 0)}, "
            f"new-failure-outcome={c.get('NEW_FAILURE_OUTCOME', 0)}, "
            f"excluded nonterminal={c.get('nonterminal_excluded', 0)}, "
            f"excluded duplicate={c.get('duplicate_family_excluded', 0)}."
        )
    p = r["progress"]
    lines.extend(
        [
            "",
            f"Latest terminal: **{p['latest_terminal']}/"
            f"{p['latest_denominator']}**. "
            f"Nonterminal: **{p['latest_nonterminal']}**.",
            f"Stability: **{p['stability_decision']}** ("
            f"{p['observed_main_heads']} observed heads; "
            f"{p['minimum_m2_screening_heads']} screening minimum).",
            f"Read-only lane proposal: "
            f"{r['scaling']['read_only_diagnostic_lanes_proposed']}; "
            "not authenticated launches or approved mutation slots.",
            "Main/diff coverage, source-owned root closures and admission "
            "are UNKNOWN/HOLD unless separately matched and independently verified.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    obj = rollup(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    args.output.with_suffix(".md").write_text(as_markdown(obj), encoding="utf-8")
    print(
        json.dumps(
            {
                "waves": len(obj["waves"]),
                "admission": "HOLD",
                "terminal": obj["progress"]["latest_terminal"],
                "denominator": obj["progress"]["latest_denominator"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
