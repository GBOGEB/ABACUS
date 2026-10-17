"""Read-only scheduled CBD method planner, not a dispatch or admission authority.

The existing EVERRED and BD-LDAB producers remain authoritative. A schedule
may plan work, but source writers, failed-job reruns and main merges require
separate authenticated owner permission and independently admissible evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "abacus.cbd.scheduled_observation.v1"
MODES = ("auto", "gogreen", "everred", "code_purple", "full")
STAGES = (
    ("N0", "Source and queue census", ()),
    ("N1", "Native first-red readback", ("N0",)),
    ("N2", "gg_MATH exploratory provider handoff", ("N1",)),
    ("N3", "GoGREEN negative and reverse tests", ("N0",)),
    ("N4", "CODE PURPLE independent admission review", ("N1", "N3")),
    ("N5", "Main and recurrence verification", ("N4",)),
)
SELECT = {
    "gogreen": ("N0", "N3"),
    "everred": ("N0", "N1", "N2"),
    "code_purple": ("N0", "N4"),
    "full": ("N0", "N1", "N2", "N3", "N4", "N5"),
}
MAX_QUEUE = 40
MAX_RUNNING = 12
READERS = 4
OWNER_WRITERS_BEFORE_LEASE = 0


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(obj):
    return hashlib.sha256(canonical(obj).encode("ascii")).hexdigest()


def method_for_date(day):
    """Mon/Wed/Fri GoGREEN; Tue/Thu EVERRED; Saturday CODE PURPLE."""
    weekday = date.fromisoformat(day).weekday()
    if weekday in (0, 2, 4, 6):
        return "gogreen"
    if weekday in (1, 3):
        return "everred"
    return "code_purple"


def plan(observation, mode="auto", day="2026-10-17", event="schedule", full_ack=False):
    require(isinstance(observation, dict), "observation must be an object")
    require(observation.get("schema") == SCHEMA, "wrong observation schema")
    require(observation.get("repository") == "GBOGEB/ABACUS", "repository mismatch")
    head = observation.get("source_sha")
    require(isinstance(head, str) and SHA.fullmatch(head), "invalid source SHA")
    require(observation.get("authority_transfer") is False and
            observation.get("security_waiver") is False and
            observation.get("merge_admission") == "HOLD",
            "forged admission or waiver")
    require(mode in MODES, "unsupported method")
    require(event in ("schedule", "workflow_dispatch"), "unsupported event")
    require(type(full_ack) is bool, "full_ack must be boolean")
    effective = method_for_date(day) if mode == "auto" else mode
    capacity = observation.get("capacity")
    require(isinstance(capacity, dict), "missing capacity")
    q, active = capacity.get("queued"), capacity.get("in_progress")
    require(q is None or type(q) is int and q >= 0, "invalid queued count")
    require(active is None or type(active) is int and active >= 0,
            "invalid in-progress count")
    if q is None or active is None:
        state = "CAPACITY_UNKNOWN"
    elif q > MAX_QUEUE or active > MAX_RUNNING:
        state = "QUEUE_SATURATED"
    elif effective == "full" and (event != "workflow_dispatch" or not full_ack):
        state = "FULL_REQUIRES_MANUAL_ACK"
    else:
        state = "BOUNDED_READ_ONLY"
    allowed = state == "BOUNDED_READ_ONLY"
    selected = SELECT[effective]
    phase_records = []
    for phase, title, deps in STAGES:
        requested = phase in selected
        # Reviewing an admission does not itself approve a merge.
        state_for_phase = (
            "NOT_REQUESTED" if not requested else
            "READ_ONLY_ELIGIBLE" if allowed and phase in ("N0", "N1", "N2", "N3") else
            "REVIEW_ONLY_HOLD" if allowed else
            "DEFERRED_" + state
        )
        phase_records.append({
            "atom": phase, "title": title, "requires": list(deps),
            "selected": requested, "state": state_for_phase,
            "accepted_root_closures": None, "human_approval": None,
        })
    observed = {
        "queued": q, "in_progress": active,
        "queue_threshold": MAX_QUEUE, "running_threshold": MAX_RUNNING,
        "capacity_is_atomic": False,
    }
    graph = {
        "nodes": [
            {"id": a["atom"], "label": a["title"], "state": a["state"]}
            for a in phase_records
        ],
        "edges": [
            {"source": dep, "target": stage, "kind": "REQUIRES"}
            for stage, _title, deps in STAGES for dep in deps
        ],
    }
    return {
        "schema": "abacus.cbd.scheduled_pulse.v1",
        "source_repository": observation["repository"],
        "source_sha": head, "utc_day": day, "event": event,
        "requested_method": mode, "selected_method": effective,
        "gate": state, "dispatch_scope": (
            "READ_ONLY_TESTFLIGHT" if allowed else "COLD_PLAN_ONLY"
        ),
        "execute_mode": effective if allowed else "none",
        "source_observation_sha256": sha256(observation),
        "metrics": {
            **observed,
            "read_only_scout_cap": READERS,
            "source_writers_without_lease": OWNER_WRITERS_BEFORE_LEASE,
            "confirmed_causal_roots_open": None,
            "confirmed_causal_roots_closed": None,
            "main_coverage": None, "diff_coverage": None,
            "crew_launch_proven": None, "correct_merges": None,
        },
        "dag": graph,
        "stages": phase_records,
        "sipoc": {
            "supplier": "GitHub Actions metadata and native EVERRED source-bound producer",
            "input": "Exact source SHA, UTC day, observed capacity, evidence digest",
            "process": "N0 census; N1 first-red; N2 math; N3 tests; N4 review; N5 recurrence",
            "output": "Immutable plan, candidate DAG, review HTML, SHA receipts and proposal ledger",
            "customer": "BD-LDAB #1929, DOW, gg_MATH, Mission Control, P0 #1860",
        },
        "controls": {
            "merge_admission": "HOLD", "security_waiver": False,
            "authority_transfer": False, "rerun_requested": False,
            "source_mutated": False, "worker_launch_claimed": False,
            "full_requires_manual_ack": True,
            "schedule_activates_only_on_admitted_default_branch": True,
        },
    }


def render_html(result):
    esc = lambda v: html.escape(str(v), quote=True)
    m = result["metrics"]
    cards = "".join(
        "<div class='kpi'><span>" + esc(label) + "</span><b>"
        + esc(m.get(key)) + "</b></div>"
        for key, label in (
            ("queued", "Observed queued"), ("in_progress", "Observed running"),
            ("read_only_scout_cap", "Read-only scouts"),
        )
    )
    rows = "".join(
        "<tr><td>" + esc(p["atom"]) + "</td><td>" + esc(p["title"]) +
        "</td><td>" + esc(",".join(p["requires"]) or "none") +
        "</td><td>" + esc(p["state"]) + "</td></tr>"
        for p in result["stages"]
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='referrer' content='no-referrer'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>CBD Scheduled DAG - governed review</title>"
        "<style>body{background:#111e30;color:#f3f7ff;font:15px system-ui;"
        "margin:0}main{max-width:1180px;margin:auto;padding:24px}header{"
        "border-bottom:1px solid #68819d;padding-bottom:16px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax("
        "150px,1fr));gap:12px;margin:20px 0}.kpi{border:1px solid #68819d;"
        "border-radius:10px;padding:12px}.kpi span{display:block;color:#b6d0e6}"
        ".kpi b{font-size:28px}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #58738d;padding:11px;text-align:left}"
        "a{color:#9ed0fa}small{color:#ffd69e}.scroll{overflow-x:auto}"
        "</style></head><body><main><header><small>CODE PURPLE / EVERRED / "
        "GoGREEN - NON-ADMITTING</small><h1>Scheduled DAG review</h1>"
        "<p>Method " + esc(result["selected_method"]) + " / gate "
        + esc(result["gate"]) + " / head <code>" +
        esc(result["source_sha"]) + "</code></p></header>"
        "<section class='grid'>" + cards + "</section><div class='scroll'>"
        "<table><thead><tr><th>Atom</th><th>Engineering stage</th>"
        "<th>Depends on</th><th>Disposition</th></tr></thead><tbody>"
        + rows + "</tbody></table></div>"
        "<p>All stages preserve independent Safety, A10 and governance gates. "
        "Observed signatures are not confirmed causes. Review is not merge "
        "approval. Missing metrics remain UNKNOWN, never zero.</p>"
        "</main></body></html>\n"
    )


def write(result, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    proposed = {
        "schema": "abacus.cbd.ledger_proposal.v1",
        "authority": "NOT_CANONICAL_EVENT",
        "source_sha": result["source_sha"],
        "source_observation_sha256": result["source_observation_sha256"],
        "method": result["selected_method"],
        "gate": result["gate"],
        "root_closure_credit": 0, "merge_admission": "HOLD",
        "authority_transfer": False, "security_waiver": False,
    }
    output = {
        "pulse-plan.json": canonical(result) + "\n",
        "pulse-dag.json": canonical(result["dag"]) + "\n",
        "pulse-sipoc.json": canonical(result["sipoc"]) + "\n",
        "ledger-proposal.jsonl": canonical(proposed) + "\n",
        "review.html": render_html(result),
    }
    for filename, value in output.items():
        (output_dir / filename).write_text(value, encoding="utf-8")
    (output_dir / "sha256.json").write_text(
        canonical({k: hashlib.sha256(v.encode("utf-8")).hexdigest()
                   for k, v in sorted(output.items())}) + "\n",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--method", choices=MODES, default="auto")
    parser.add_argument("--utc-day", required=True)
    parser.add_argument("--event", default="schedule")
    parser.add_argument("--full-ack", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    observation = json.loads(args.observation.read_text(encoding="utf-8"))
    result = plan(observation, args.method, args.utc_day, args.event,
                  args.full_ack)
    write(result, args.output_dir)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write("execute_mode=" + result["execute_mode"] + "\n")
            stream.write("gate=" + result["gate"] + "\n")
    print(canonical({
        "method": result["selected_method"], "gate": result["gate"],
        "head": result["source_sha"], "admission": "HOLD",
    }))


if __name__ == "__main__":
    main()
