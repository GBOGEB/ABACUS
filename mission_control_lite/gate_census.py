"""Read-only, exact-head gate metrics; never confers merge admission."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


TERMINAL = {
    "success", "failure", "cancelled", "skipped", "timed_out",
    "action_required", "neutral", "stale", "startup_failure",
}
BLOCKING_TERMINAL = {
    "failure", "cancelled", "timed_out", "action_required",
    "stale", "startup_failure",
}


def summarize(source_sha: str, runs: list[dict]) -> dict:
    """Compute explicit-denominator, per-run outcomes without collapsing gates."""
    if len(source_sha) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in source_sha):
        raise ValueError("full hexadecimal pull-head SHA required")
    seen = set()
    counts = Counter()
    records = []
    for run in runs:
        if run.get("head_sha") != source_sha:
            raise ValueError("run source differs from requested pull head")
        run_id = run.get("id")
        if type(run_id) is not int or run_id < 1 or run_id in seen:
            raise ValueError("invalid or duplicate workflow run ID")
        seen.add(run_id)
        state = run.get("status")
        conclusion = run.get("conclusion")
        if state != "completed" or conclusion not in TERMINAL:
            raise ValueError("nonterminal or unsupported run result")
        counts[conclusion] += 1
        records.append({"run_id": run_id, "name": str(run.get("name", "")),
                        "conclusion": conclusion, "source_sha": source_sha})
    total = len(records)
    success = counts["success"]
    return {
        "schema": "code-purple.exact-head-gate-census.v1",
        "source_sha": source_sha,
        "observations": total,
        "successful": success,
        "failed": counts["failure"],
        "cancelled": counts["cancelled"],
        "stale": counts["stale"],
        "startup_failure": counts["startup_failure"],
        "blocking_terminal": sum(counts[reason] for reason in BLOCKING_TERMINAL),
        "other_terminal": total - success - counts["failure"] - counts["cancelled"],
        "success_fraction": success / total if total else None,
        "gate_admission": "HOLD",
        "note": "Workflow-level descriptive census only; not independent trials or merge admission.",
        "records": sorted(records, key=lambda row: row["run_id"]),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--runs-json", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    runs = json.loads(args.runs_json.read_text(encoding="utf-8"))
    if not isinstance(runs, list):
        raise ValueError("input must be a JSON list of workflow runs")
    result = summarize(args.head_sha, runs)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
