"""W32 queue/attempt/proof yield disjoint runner adversarial census."""
import copy
import pytest

from tools.recovery import w32_runner_telemetry as m

HEAD = "a" * 40
STAMP = "2026-10-18T18:00:00+00:00"


def proof():
    return {"artifact_sha256_verified": True, "junit_identity_verified": True,
            "executed_cases": 40, "eligible_opportunities": 200,
            "covered_opportunities": 198}


def cell(n, *, status="completed", conclusion="success", family="ROOT"):
    return {
        "head_sha": HEAD, "run_id": 39100000000 + n,
        "attempt": 1, "job_id": 117000000000 + n,
        "family": family, "os": "ubuntu-latest", "python": "3.10",
        "status": status, "conclusion": conclusion,
        "created_at": "2026-10-18T18:00:00Z",
        "started_at": "2026-10-18T18:00:40Z",
        "completed_at": "2026-10-18T18:02:40Z",
        "evidence": proof(),
    }


def sample():
    return {"exact_head": HEAD, "cells": [
        cell(1, family="ROOT"), cell(2, family="RUNNER"),
        cell(3, status="completed", conclusion="failure", family="CONTROL"),
    ]}


def test_job_success_and_verified_proof_are_separate_metrics():
    result = m.summarize(sample())
    assert (result["successful"], result["terminal"]) == (2, 3)
    assert result["verified_successful_evidence"] == 2
    assert result["native_proof_yield"] == round(2 / 3, 6)
    assert result["disjoint_families"] == 3
    assert (result["queue_p95_seconds"], result["execution_p95_seconds"]) == (40, 120)
    assert result["merge_admission"] == "HOLD"


@pytest.mark.parametrize("key", ["artifact_sha256_verified",
                                  "junit_identity_verified"])
def test_false_evidence_flag_refuses_proof(key):
    p = sample()
    p["cells"][0]["evidence"][key] = False
    result = m.summarize(p)
    assert result["successful"] == 2
    assert result["verified_successful_evidence"] == 1


@pytest.mark.parametrize("key,mutant", [
    ("executed_cases", 0), ("executed_cases", True),
    ("eligible_opportunities", 0), ("covered_opportunities", -1),
    ("covered_opportunities", 201), ("covered_opportunities", "198"),
])
def test_bad_case_or_coverage_denominator_cannot_gain_proof(key, mutant):
    p = sample()
    p["cells"][0]["evidence"][key] = mutant
    assert m.summarize(p)["verified_successful_evidence"] == 1


def test_missing_evidence_not_inferred_from_green_job():
    p = sample()
    p["cells"][0]["evidence"] = None
    out = m.summarize(p)
    assert out["successful"] == 2
    assert out["verified_successful_evidence"] == 1


def test_pending_job_stays_outside_completed_denominator():
    p = sample()
    p["cells"].append(cell(4, status="queued", conclusion=None))
    p["cells"][-1]["started_at"] = None
    p["cells"][-1]["completed_at"] = None
    out = m.summarize(p)
    assert out["nonterminal"] == 1
    assert out["terminal"] == 3
    assert out["unknown_queue_n"] == 1
    assert out["unknown_runtime_n"] == 1


def test_no_terminal_jobs_do_not_report_fake_zero_yield():
    c = cell(1, status="queued", conclusion=None)
    c["started_at"] = None
    c["completed_at"] = None
    out = m.summarize({"exact_head": HEAD, "cells": [c]})
    assert out["native_proof_yield"] is None
    assert out["execution_p95_seconds"] is None


def test_missing_native_timestamp_not_imputed():
    p = sample()
    p["cells"][0]["created_at"] = None
    out = m.summarize(p)
    assert out["queue_sample_n"] == 2
    assert out["unknown_queue_n"] == 1


@pytest.mark.parametrize("field,value,error", [
    ("head_sha", "b" * 40, "foreign head"),
    ("job_id", 0, "invalid native"),
    ("attempt", False, "invalid native"),
    ("family", "", "runner identity"),
    ("status", "not_run", "runner state"),
    ("conclusion", None, "terminal conclusion"),
    ("created_at", "yesterday", "native timestamp"),
    ("started_at", "2026-10-18T17:59:59Z", "negative queue"),
    ("completed_at", "2026-10-18T18:00:39Z", "negative execution"),
])
def test_invalid_native_cell_fails_closed(field, value, error):
    p = sample()
    p["cells"][0][field] = value
    with pytest.raises(ValueError, match=error):
        m.summarize(p)


def test_duplicate_attempt_must_not_inflate_sample():
    p = sample()
    p["cells"].append(copy.deepcopy(p["cells"][0]))
    with pytest.raises(ValueError, match="duplicate native"):
        m.summarize(p)


def test_attempt_two_has_independent_run_identity_not_new_root():
    p = sample()
    extra = copy.deepcopy(p["cells"][0])
    extra["attempt"] = 2
    p["cells"].append(extra)
    result = m.summarize(p)
    assert result["observed_jobs"] == 4
    assert result["disjoint_families"] == 3


def test_timezone_naive_date_not_accepted():
    p = sample()
    p["cells"][0]["created_at"] = "2026-10-18T18:00:00"
    with pytest.raises(ValueError, match="timezone"):
        m.summarize(p)


def test_zero_terminal_and_zero_scope_still_hold():
    result = m.summarize({"exact_head": HEAD, "cells": []})
    assert result["observed_jobs"] == 0
    assert result["native_proof_yield"] is None
    assert result["merge_admission"] == "HOLD"
