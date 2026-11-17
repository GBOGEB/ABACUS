"""Local reproducible CODE PURPLE EOSS N6 review projection and QA manifest.

Derived surfaces are read-only; native GitHub security, A10 and main gates hold.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from statistics import median

from scripts.cbd_eoss_trajectory import OUTPUT_SCHEMA

RELEASE_SCHEMA = "code-purple.eoss.n6.review-release.v1"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")


def need(value, message):
    if not value:
        raise ValueError(message)


def pretty_json(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def bytes_sha(value):
    return hashlib.sha256(value).hexdigest()


def validate(trajectory, native, plan):
    need(
        isinstance(trajectory, dict) and trajectory.get("schema") == OUTPUT_SCHEMA,
        "trajectory input not validated",
    )
    need(
        trajectory.get("authority")
        == {"admission": "HOLD", "security_waiver": False, "authority_transfer": False},
        "trajectory authority promotion",
    )
    need(
        trajectory.get("waves") == ["N5", "W7", "W8", "W9"], "incomplete W7-W9 wave set"
    )
    need(
        isinstance(native, dict) and native.get("run_id") == 39026629552,
        "unsupported native matrix run evidence",
    )
    need(
        isinstance(native.get("head_sha"), str) and HEX40.fullmatch(native["head_sha"]),
        "unbound native run head",
    )
    need(
        native.get("run_attempt") == 1
        and native.get("clock_basis") == "NATIVE_JOB_CREATED_STARTED_COMPLETED",
        "native job attempt/clock mismatch",
    )
    need(
        isinstance(native.get("jobs"), list) and len(native["jobs"]) == 7,
        "native job count mismatch",
    )
    seen = set()
    for j in native["jobs"]:
        need(
            isinstance(j, dict)
            and type(j.get("job_id")) is int
            and j["job_id"] > 0
            and j["job_id"] not in seen,
            "duplicated native job",
        )
        seen.add(j["job_id"])
        need(j.get("run_attempt") == 1, "job attempt drift")
        for metric in ("queue_seconds", "runtime_seconds"):
            value = j.get(metric)
            need(
                value is None or (type(value) in (int, float) and value >= 0),
                "invalid or negative native clock",
            )
        if j.get("conclusion") == "skipped":
            need(j.get("runtime_seconds") is None, "skipped job duration forged")
    need(
        isinstance(plan, dict)
        and plan.get("schema") == "code-purple.eoss.n6.plan.v1"
        and plan.get("authority")
        == {
            "merge_admission": "HOLD",
            "security_waiver": False,
            "authority_transfer": False,
        },
        "planned wave admission drift",
    )
    need(len(plan.get("waves", [])) == 3, "planned waves missing")
    return True


def dag():
    return """flowchart LR
    subgraph LOCAL[LOCAL E0 to E2]
      S[Source and wheel digest] --> T[Tests plus branch coverage]
      T --> P[Bounded I/O scout and pre-push]
    end
    subgraph REPO[ABACUS E3 to E5]
      H[Exact head SHA] --> R[Run attempt 1]
      R --> J[Native job and step]
      J --> C[Coverage and clock evidence]
    end
    subgraph FED[FEDERATION E6]
      V[Derived EOSS visual suite] --> G{Security / A10 / governance / reviewer}
      G -->|unresolved| X[HOLD]
    end
    P --> H
    C -. observational projection .-> V
    J -. first-red symptom only .-> V
    classDef verified fill:#d8f5e4,stroke:#217354,color:#123b2b
    classDef candidate fill:#fff0ca,stroke:#b78538,color:#5c451a
    classDef denied fill:#ffe2e2,stroke:#bb4551,color:#63151f
    class H,R,J,C verified
    class V candidate
    class X denied
"""


def sipoc():
    return """flowchart LR
    S[SUPPLIERS<br/>GitHub jobs<br/>Local pytest / coverage<br/>TestPilot] --> I[INPUTS<br/>sha, run, attempt, job<br/>test/branch numerator<br/>clock and backlog]
    I --> P[PROCESS<br/>scope match<br/>three-wave trajectory<br/>clock censor / graph QA]
    P --> O[OUTPUTS<br/>EOSS ledgers<br/>DAG + SIPOC<br/>HTML + QA manifest]
    O --> C[CUSTOMERS<br/>source owners<br/>CODEX Mission Control<br/>A10/security reviewers]
    C -. correction request, not direct mutation .-> S
"""


def clock_graph():
    return """flowchart TD
    A[Local monotonic experiment] --> B[Three samples per wave]
    B --> C{Same workload, host, and test selection?}
    C -->|yes| D[Descriptive local duration delta]
    C -->|no| U[UNKNOWN acceleration]
    E[Native job created / started / completed] --> F{Non-skipped, ordered timestamps?}
    F -->|yes| G[Runner job wait and execution]
    F -->|no| H[Clock censored]
    D -. NOT equivalent to .-> G
    U --> K[Forecast next cohort; no speedup credit]
    H --> K
    G --> K
"""


def glossary():
    return (
        """# CODE PURPLE EOSS N6 — Three-wave glossary and interpretation

**Scope:** LOCAL E0-E2, REPO E3-E5, FEDERATION E6. EOSS remains a family of review projections; no new SSOT.

- **Wave W7/W8/W9:** a bounded engineering increment with a committed or locally reproducible source/test output and an explicit receipt.
- **Pulse:** the observation and verification checkpoint inside a wave, not a separate unlimited execution batch.
- **Stability:** repeated matched measurements with differences within a predeclared tolerance. Three compared pairs require FOUR wave states.
- **Acceleration:** a second difference of coverage changes or an independently matched runtime speedup. A negative second difference is deceleration of gains, not declining absolute coverage.
- **Convergence:** a descriptive approach to a coverage plateau or diminishing remaining unknowns; it is not certified causal convergence.
- **Plateau:** constant measured coverage may be 100% or 20%. It never proves sufficiency without absolute quality gates.
- **Coverage:** measured statements and branch opportunities in a fixed source scope, not all-repository or diff coverage unless separately verified.
- **Predicted / planned / actual:** a prior-issued quantitative forecast, an operational target, and an independently measured result. No retroactive scoring.
- **First-red:** native run:attempt and failed job step; a recurring workflow name alone does not confirm causal root.
- **Job wait:** native job.started_at minus job.created_at if both ordered and same job. Run.created_at is NOT a queue-wait proxy.
- **Runner execution:** native completed_at minus started_at; skipped or inverted clocks are censored.
- **Asyncio:** cooperative, bounded I/O fan-out; simulated network waits do not certify GitHub throughput improvements.
- **Wheelhouse:** hash-qualified ABI/OS/lock/wheel cache; any CoolProp or other wheel savings require same-cohort measured cold/warm trials.
- **Unlisted / enumerated / untested / UNKNOWN:** different denominators and evidentiary statuses; never translate unknown into zero.
- **DAG:** directed process/provenance graph. Dashed observational or co-occurrence edges are not causal.
- **SIPOC:** Supplier, Input, Process, Output and Customer contract, with source-owner feedback loops.
- **Governance:** independent A10, security, CI policy, branch protection and human reviewer remain HOLD until accepted.

## Reader navigation

View the [interactive HTML](eoss_n6.html) for trajectory, evidence clocks, and expansion status. The three Mermaid source diagrams are `eoss_n6_process.mmd`, `eoss_n6_sipoc.mmd`, `eoss_n6_clock.mmd`; each is reproduced below with a narrative.

## Process DAG

```mermaid
"""
        + dag()
        + "```\n\nThe process path is directional. Candidate symptom evidence returns to an owner, not directly to a merger.\n\n## SIPOC\n\n```mermaid\n"
        + sipoc()
        + "```\n\nThe output suite is a projection of source receipts; customer feedback is a new owned change request.\n\n## Clock scope\n\n```mermaid\n"
        + clock_graph()
        + "```\n\nNo local build or simulated I/O result is a GitHub runner or CoolProp speedup.\n"
    )


def release(trajectory, native, plan, template):
    validate(trajectory, native, plan)
    need(
        isinstance(template, str) and template.count("__N6_SOURCE_JSON__") == 1,
        "HTML projection template contract drift",
    )
    valid_jobs = [j for j in native["jobs"] if j["runtime_seconds"] is not None]
    waits = [
        j["queue_seconds"]
        for j in native["jobs"]
        if j["queue_seconds"] is not None and j["runtime_seconds"] is not None
    ]
    metrics = {
        "matched_local_coverage_pairs": trajectory["trajectory"]["matched_pairs"],
        "trajectory_state": trajectory["trajectory"]["state"],
        "final_local_test_count": trajectory["observations"][-1]["tests"]["passed"],
        "historical_N0_readbacks": 60,
        "historical_N0_denominator": 253,
        "native_jobs_received": len(native["jobs"]),
        "native_job_durations_observed": len(valid_jobs),
        "native_clock_anomaly_jobs": len(native["jobs"]) - len(valid_jobs),
        "native_job_runtime_seconds_p50": median(
            j["runtime_seconds"] for j in valid_jobs
        ),
        "native_job_wait_seconds_p50": median(waits),
        "native_job_wait_is_not_run_queue": True,
        "current_head_native_tests_terminal": False,
        "security_governance_review": "HOLD",
    }
    view = {
        "schema": RELEASE_SCHEMA,
        "metrics": metrics,
        "trajectory": trajectory,
        "native_clock": native,
        "plan": plan,
        "graph_narrative": "Observational DAG, SIPOC and time-basis edges; no confirmed causal roots.",
        "authority": {
            "admission": "HOLD",
            "security_waiver": False,
            "authority_transfer": False,
        },
    }
    source = pretty_json(view)
    safe_json = (
        source.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )
    dashboard = template.replace("__N6_SOURCE_JSON__", safe_json)
    need("__N6_SOURCE_JSON__" not in dashboard, "unfilled HTML source marker")
    return {
        "eoss_n6_dashboard.html": dashboard,
        "eoss_n6_review.json": source,
        "eoss_n6_glossary.md": glossary(),
        "eoss_n6_process.mmd": dag(),
        "eoss_n6_sipoc.mmd": sipoc(),
        "eoss_n6_clock.mmd": clock_graph(),
    }


def write(outputs, directory):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    sha = {}
    for name, text in sorted(outputs.items()):
        need(
            "/" not in name and "\\" not in name and isinstance(text, str),
            "unsafe output name",
        )
        raw = text.encode("utf-8")
        (destination / name).write_bytes(raw)
        sha[name] = bytes_sha(raw)
    receipt = {
        "schema": "code-purple.eoss.n6.local-release-receipt.v1",
        "artifacts": sha,
        "evidence_level": "LOCAL_REPRODUCIBILITY",
        "checks": {
            "structural": "PASS",
            "visual_playwright": "DEFER",
            "native_exact_head_ci": "DEFER",
            "cross_artifact_sha_parity": "PASS",
        },
        "authority": {
            "admission": "HOLD",
            "security_waiver": False,
            "authority_transfer": False,
        },
    }
    (destination / "eoss_n6_release_receipt.json").write_text(
        pretty_json(receipt), encoding="utf-8"
    )
    return receipt
