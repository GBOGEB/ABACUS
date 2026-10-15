"""Exact-SHA, scope-matched Mission Control Lite coverage wave observations.

Measurements never grant root closure or merge admission.
"""
import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
COUNT = re.compile(r"Ran (\d+) tests? in ")
SOURCE_PREFIX = "mission_control_lite/"
SCHEMA = "mcl.coverage.pulse.v1"


def _counts(summary, *, allow_empty=False):
    fields = ("covered_lines", "num_statements", "covered_branches", "num_branches")
    if not isinstance(summary, dict):
        raise ValueError("missing coverage totals")
    for field in fields:
        if type(summary.get(field)) is not int or summary[field] < 0:
            raise ValueError("invalid coverage " + field)
    if (summary["num_statements"] == 0 and not allow_empty) or summary["covered_lines"] > summary["num_statements"]:
        raise ValueError("invalid line denominator")
    if summary["num_statements"] == 0 and summary["num_branches"] != 0:
        raise ValueError("invalid empty module branch denominator")
    if summary["covered_branches"] > summary["num_branches"]:
        raise ValueError("invalid branch denominator")
    return summary


def _percent(num, den):
    return None if not den else round(100 * num / den, 4)


def compare(previous, current):
    """Only credit deltas for exactly matched source files/config/denominators."""
    if previous is None:
        return {"status": "UNKNOWN", "reason": "no native baseline pulse supplied"}
    if previous.get("schema") != SCHEMA:
        raise ValueError("invalid baseline schema")
    keys = ("repository", "scope_id", "files", "coverage_version")
    if any(previous.get(key) != current.get(key) for key in keys):
        return {"status": "INCOMPARABLE", "reason": "scope/files/tool mismatch"}
    before, after = previous.get("totals"), current["totals"]
    _counts(before)
    if any(before[name] != after[name] for name in ("num_statements", "num_branches")):
        return {"status": "INCOMPARABLE", "reason": "coverage denominator changed"}
    return {
        "status": "COMPARABLE",
        "baseline_sha": previous["source_sha"],
        "current_sha": current["source_sha"],
        "line_delta_pp": round(
            current["line_percent"] - previous["line_percent"], 4
        ),
        "branch_delta_pp": (
            None if current["branch_percent"] is None
            else round(current["branch_percent"] - previous["branch_percent"], 4)
        ),
        "new_covered_lines": after["covered_lines"] - before["covered_lines"],
        "new_covered_branches": after["covered_branches"] - before["covered_branches"],
        "test_delta": current["tests_passed"] - previous["tests_passed"],
    }


def build(report, test_logs, source_sha, event_sha, run_id, previous=None, phases=None):
    if not isinstance(source_sha, str) or not SHA.fullmatch(source_sha):
        raise ValueError("invalid executed source SHA")
    if not isinstance(event_sha, str) or not SHA.fullmatch(event_sha):
        raise ValueError("invalid event SHA")
    if not str(run_id).isdigit():
        raise ValueError("invalid run ID")
    if not isinstance(report, dict) or "meta" not in report:
        raise ValueError("coverage JSON metadata missing")
    version = report["meta"].get("version")
    files = report.get("files")
    if not isinstance(version, str) or not version or not isinstance(files, dict):
        raise ValueError("coverage files/version missing")
    names = sorted(files)
    if not names or any(not name.startswith(SOURCE_PREFIX) for name in names):
        raise ValueError("coverage source scope invalid")
    required = {"core.py", "policy.py", "rex.py", "cli.py"}
    if not required <= {Path(name).name for name in names}:
        raise ValueError("incomplete production source coverage")
    totals = _counts(report.get("totals"))
    per_file = {}
    for name in names:
        item = _counts(files[name].get("summary"), allow_empty=True)
        per_file[name] = {
            "line_percent": _percent(item["covered_lines"], item["num_statements"]),
            "branch_percent": _percent(item["covered_branches"], item["num_branches"]),
            "missing_lines": item["num_statements"] - item["covered_lines"],
            "missing_branches": item["num_branches"] - item["covered_branches"],
        }
    if not isinstance(test_logs, dict) or not test_logs:
        raise ValueError("test logs missing")
    counts = {}
    for name, text in test_logs.items():
        matches = COUNT.findall(text)
        if len(matches) != 1 or not re.search(r"(?m)^OK\s*$", text):
            raise ValueError("missing native passing test summary: " + name)
        counts[name] = int(matches[0])
        if counts[name] <= 0:
            raise ValueError("empty test suite: " + name)
    obj = {
        "schema": SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_sha": source_sha,
        "event_sha": event_sha,
        "run_id": str(run_id),
        "scope_id": "mission_control_lite/branch-v1",
        "coverage_version": version,
        "files": names,
        "per_file": per_file,
        "totals": {k: totals[k] for k in (
            "covered_lines", "num_statements", "covered_branches", "num_branches"
        )},
        "line_percent": _percent(totals["covered_lines"], totals["num_statements"]),
        "branch_percent": _percent(totals["covered_branches"], totals["num_branches"]),
        "tests_by_suite": counts,
        "tests_passed": sum(counts.values()),
        "native_scope": "focused_unittest_only",
        "verified_root_closures": 0,
        "merge_admission": "HOLD",
    }
    if phases is not None:
        if not isinstance(phases, list) or not phases:
            raise ValueError("missing native phase timings")
        names = set()
        elapsed = 0.0
        for phase in phases:
            if not isinstance(phase, dict):
                raise ValueError("invalid native phase record")
            label = phase.get("phase")
            seconds = phase.get("duration_seconds")
            if not isinstance(label, str) or not label or label in names:
                raise ValueError("duplicate or missing native phase")
            if (not isinstance(seconds, (int, float)) or isinstance(seconds, bool)
                    or seconds < 0 or phase.get("exit_code") != 0):
                raise ValueError("invalid/failed native phase")
            names.add(label)
            elapsed += seconds
        obj["execution_phases"] = phases
        obj["timed_execution_seconds"] = round(elapsed, 6)
        obj["tests_per_timed_second"] = (
            round(obj["tests_passed"] / elapsed, 6) if elapsed else None
        )
        obj["job_queue_seconds"] = None
        obj["wheel_unpack_seconds"] = None
        obj["measurement_note"] = (
            "Inside-job monotonic phase times only; queue and wheel extraction "
            "require separate independent measurements."
        )
    obj["comparison"] = compare(previous, obj)
    return obj


def render_summary(pulse):
    """Display exact-SHA metrics; never substitute missing deltas with zero."""
    comparison = pulse["comparison"]
    delta = comparison.get("line_delta_pp")
    bdelta = comparison.get("branch_delta_pp")
    def display(value, suffix=""):
        return "UNKNOWN" if value is None else str(value) + suffix

    lines = [
        "## Mission Control Lite: measured wave",
        "",
        "| Metric | Native evidence |",
        "| --- | ---: |",
        "| Executed SHA | `" + pulse["source_sha"] + "` |",
        "| Run ID | " + pulse["run_id"] + " |",
        "| Passed focused tests | " + str(pulse["tests_passed"]) + " |",
        "| Line coverage | " + display(pulse["line_percent"], "%") + " |",
        "| Branch coverage | " + display(pulse["branch_percent"], "%") + " |",
        "| Comparable baseline | " + comparison["status"] + " |",
        "| Line delta | " + display(delta, " pp") + " |",
        "| Branch delta | " + display(bdelta, " pp") + " |",
        "| Timed native phases | " +
        display(pulse.get("timed_execution_seconds"), " s") + " |",
        "| Runner queue | UNKNOWN (external run metadata needed) |",
        "| Verified root closures | 0 |",
        "| Merge admission | HOLD |",
        "",
        "### Timed phases",
        "",
        "| Phase | Seconds | Exit |",
        "| --- | ---: | ---: |",
    ]
    for item in pulse.get("execution_phases", []):
        lines.append(
            "| " + item["phase"] + " | " +
            str(item["duration_seconds"]) + " | " +
            str(item["exit_code"]) + " |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-json", required=True, type=Path)
    parser.add_argument("--core-log", required=True, type=Path)
    parser.add_argument("--rex-log", required=True, type=Path)
    parser.add_argument("--metrics-log", required=True, type=Path)
    parser.add_argument("--timing-log", type=Path)
    parser.add_argument("--timing-tests-log", type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--event-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    logs = {
        "core": args.core_log.read_text(),
        "rex": args.rex_log.read_text(),
        "metrics": args.metrics_log.read_text(),
    }
    if args.timing_tests_log:
        logs["timing"] = args.timing_tests_log.read_text()
    old = json.loads(args.baseline.read_text()) if args.baseline else None
    phases = json.loads(args.timing_log.read_text()) if args.timing_log else None
    pulse = build(
        json.loads(args.coverage_json.read_text()), logs,
        args.source_sha, args.event_sha, args.run_id, old, phases,
    )
    args.output.write_text(json.dumps(pulse, indent=2, sort_keys=True) + "\n")
    if args.summary:
        with args.summary.open("a") as summary:
            summary.write(render_summary(pulse))
    print(json.dumps({
        "source_sha": pulse["source_sha"],
        "tests": pulse["tests_passed"],
        "line_percent": pulse["line_percent"],
        "branch_percent": pulse["branch_percent"],
        "comparison": pulse["comparison"]["status"],
        "merge_admission": "HOLD",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
