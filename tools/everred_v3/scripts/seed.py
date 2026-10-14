import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from everred import append_event

P = pathlib.Path(__file__).resolve().parents[1]
path = P / "data/ledger.jsonl"
if path.exists():
    path.unlink()
sha = "e9f34b22967064c779891a4d2ac40541f370e812"
now = "2026-10-14T08:04:49Z"
repo = "GBOGEB/ABACUS"
i = 0


def add(kind, evidence, **kw):
    global i
    i += 1
    e = dict(
        schema="abacus.everred.event.v3",
        id=f"HIST-1914-{i:03d}",
        kind=kind,
        occurred_at=now,
        repo=repo,
        provenance="historical_source",
        evidence=evidence,
        **kw,
    )
    append_event(path, e)


add(
    "verification",
    {
        "status": "PASS",
        "name": "Bandit disjoint census",
        "tests_passed": 52,
        "tests_total": 52,
        "statements_covered": 49,
        "statements_eligible": 61,
        "run_id": "38532010232",
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/38532010232",
    },
    sha=sha,
)
add(
    "verification",
    {
        "status": "PASS",
        "name": "Workflow governance",
        "workflow_inventory": 156,
        "run_id": "38532010504",
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/38532010504",
    },
    sha=sha,
)
add(
    "verification",
    {
        "status": "PASS",
        "name": "MIP B0 canonical",
        "artifact_id": "11878143808",
        "run_id": "38532010296",
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/38532010296",
    },
    sha=sha,
)
add(
    "coverage",
    {
        "scope": "focused",
        "unit": "statements",
        "covered": 49,
        "eligible": 61,
        "config_id": "#1914-bandit-focused",
        "run_id": "38532010232",
        "reported_combined": 82.80,
    },
    sha=sha,
)
add(
    "coverage",
    {
        "scope": "changed_lines",
        "unit": "lines",
        "covered": 3,
        "eligible": 3,
        "config_id": "#1914-pr-changed-source",
        "run_id": "38532010346",
    },
    sha=sha,
)
add(
    "coverage",
    {
        "scope": "broad",
        "unit": "statements",
        "covered": 12731,
        "eligible": 29093,
        "config_id": "#1914-broad-ci-statement",
        "run_id": "38532010346",
        "reported_combined": 42.63,
    },
    sha=sha,
)
add(
    "security_census",
    {
        "scanner": "Bandit",
        "raw_findings": 6363,
        "scope": "full",
        "fingerprint_burndown": None,
        "config_digest": "UNKNOWN",
        "run_id": "38532010346",
    },
    sha=sha,
)
add(
    "security_census",
    {
        "scanner": "Bandit",
        "raw_findings": 3,
        "scope": "separately_configured",
        "fingerprint_burndown": None,
        "config_digest": "UNKNOWN",
        "run_id": "38532010346",
    },
    sha=sha,
)
add(
    "security_census",
    {
        "scanner": "Safety",
        "exit_code": 64,
        "status": "RED",
        "cause": "UNKNOWN",
        "run_id": "38532010346",
    },
    sha=sha,
)
add(
    "occurrence",
    {
        "test": "tests/test_dmaic_measurement_receipts.py::test_real_measurement_and_repeat",
        "signature": "RuntimeError: Measurement reports missing",
        "job_id": "115748918574",
        "run_id": "38532010346",
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/38532010346/job/115748918574",
    },
    sha=sha,
)
add(
    "root_candidate",
    {
        "title": "DMAIC missing measurement receipts",
        "cause": "UNKNOWN",
        "owner": "UNASSIGNED",
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/38532010346/job/115748918574",
    },
    root_id="CANDIDATE-DMAIC-1914",
)
add(
    "root_candidate",
    {
        "title": "Safety exit 64",
        "cause": "UNKNOWN",
        "owner": "UNASSIGNED",
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/38532010346",
    },
    root_id="CANDIDATE-SAFETY-1914",
)
add(
    "governance",
    {
        "branch": "main",
        "effective_protection": False,
        "ruleset_id": 24494381,
        "url": "https://github.com/GBOGEB/ABACUS/settings/rules/24494381",
        "state": "HISTORICAL",
        "main_sha": "02cca5020d59cc339cea486ed38857f53eea3e88",
    },
    sha=sha,
)
add(
    "admission",
    {
        "decision": "HOLD",
        "gates": {
            "exact_head_ci": "RED",
            "security": "RED",
            "coverage": "RED",
            "workflow_governance": "PASS",
            "branch_protection": "RED",
            "independent_review": "UNKNOWN",
            "review_conversations": "UNKNOWN",
        },
    },
    sha=sha,
)
print(f"seeded {i} historical events to {path}")
