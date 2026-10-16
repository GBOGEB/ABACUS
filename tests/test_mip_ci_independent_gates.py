"""Disjoint workflow gate-vector regressions: no cross-gate credit."""

import copy

import pytest

from tools.mip_ci_wave_telemetry import GATE_DOMAINS, independent_gate_vector, summarize


SHA = "a" * 40
OTHER_SHA = "b" * 40
ENTERPRISE = ".github/workflows/dmaic-enterprise-ci.yml"
GOVERNANCE = ".github/workflows/ci-governance.yml"
A10 = ".github/workflows/a10-guard.yml"


def workflow(identity, path, name, conclusion="success", attempt=1, sha=SHA):
    return {
        "id": identity,
        "run_attempt": attempt,
        "head_sha": sha,
        "created_at": "2026-10-16T08:00:00Z",
        "path": path,
        "name": name,
        "status": "completed" if conclusion is not None else "queued",
        "conclusion": conclusion,
        "html_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{identity}",
    }


def job(identity, run_id, name, conclusion="success", attempt=1, *, steps=None):
    result = {
        "id": identity,
        "run_id": run_id,
        "run_attempt": attempt,
        "head_sha": SHA,
        "name": name,
        "status": "completed" if conclusion is not None else "queued",
        "conclusion": conclusion,
        "started_at": "2026-10-16T08:01:00Z",
        "completed_at": "2026-10-16T08:04:00Z" if conclusion is not None else None,
    }
    if steps is not None:
        result["steps"] = [
            {"name": step, "status": "completed", "conclusion": "success"}
            for step in steps
        ]
    return result


def enterprise_jobs(run_id=101, *, test_count=12, summary=True):
    result = []
    n = 0
    for version in ("3.9", "3.10", "3.11", "3.12"):
        for operating_system in ("ubuntu-latest", "windows-latest", "macos-latest"):
            if n >= test_count:
                break
            result.append(
                job(
                    1000 + n,
                    run_id,
                    f"Test Python {version} on {operating_system}",
                    steps=["Run pytest --benchmark-disable with coverage"],
                )
            )
            n += 1
    if summary:
        result.append(job(1100, run_id, "CI Summary"))
    return result


def governance_job(run_id=102, *, conclusion="success", step=True):
    return job(
        1102,
        run_id,
        "policy-and-inventory",
        conclusion,
        steps=["Fail closed on governance red"] if step else None,
    )


def input_payload(enterprise="success", governance="failure", *, a10=None):
    runs = [
        workflow(101, ENTERPRISE, "DMAIC V3 Enterprise CI", enterprise),
        workflow(102, GOVERNANCE, "CI Workflow Governance", governance),
    ]
    jobs = enterprise_jobs() + [governance_job(conclusion=governance)]
    bindings = {
        "enterprise_ci": {"run_id": 101, "run_attempt": 1},
        "workflow_governance": {"run_id": 102, "run_attempt": 1},
    }
    if a10 is not None:
        runs.append(workflow(103, A10, "a10-guard", a10))
        jobs.append(job(1103, 103, "a10-guard", a10))
        bindings["a10_confidentiality"] = {"run_id": 103, "run_attempt": 1}
    return {
        "source_sha": SHA,
        "repository": "GBOGEB/ABACUS",
        "runs": runs,
        "jobs": jobs,
        "gate_bindings": bindings,
    }


def gate(payload, name):
    return summarize(payload)["independent_gates"]["domains"][name]


def test_missing_all_gates_is_unknown_not_six_false_green():
    report = summarize({"source_sha": SHA, "jobs": []})["independent_gates"]
    assert tuple(report["domains"]) == GATE_DOMAINS
    assert report["domain_counts"]["UNKNOWN"] == 6
    assert report["domain_counts"]["PASS"] == 0
    assert report["admission"] == "HOLD"
    assert report["coverage_artifact_verified"] is None
    assert report["merge_authorized"] is False


def test_enterprise_pass_governance_fail_stay_separate():
    report = summarize(input_payload())["independent_gates"]
    assert report["domains"]["enterprise_ci"]["status"] == "PASS"
    assert report["domains"]["workflow_governance"]["status"] == "FAIL"
    assert report["domains"]["enterprise_ci"]["run_id"] == 101
    assert report["domains"]["workflow_governance"]["run_id"] == 102
    assert report["domain_counts"]["PASS"] == 1
    assert report["domain_counts"]["FAIL"] == 1
    assert report["red_domains"] == ["workflow_governance"]
    assert report["admission"] == "HOLD"
    assert report["merge_authorized"] is False


def test_reverse_enterprise_failure_does_not_erase_governance_pass():
    report = summarize(input_payload("failure", "success"))["independent_gates"]
    assert report["domains"]["enterprise_ci"]["status"] == "FAIL"
    assert report["domains"]["workflow_governance"]["status"] == "PASS"
    assert report["red_domains"] == ["enterprise_ci"]


def test_both_workflows_pass_but_a10_security_and_review_unknown():
    report = summarize(input_payload("success", "success"))["independent_gates"]
    assert report["domains"]["enterprise_ci"]["status"] == "PASS"
    assert report["domains"]["workflow_governance"]["status"] == "PASS"
    assert report["domain_counts"]["UNKNOWN"] == 4
    assert report["admission"] == "HOLD"
    assert report["unknown_domains"] == [
        "a10_confidentiality",
        "bandit",
        "independent_review",
        "safety",
    ]


def test_a10_failure_is_independent_even_if_both_workflows_pass():
    report = summarize(
        input_payload("success", "success", a10="failure")
    )["independent_gates"]
    assert report["domains"]["enterprise_ci"]["status"] == "PASS"
    assert report["domains"]["workflow_governance"]["status"] == "PASS"
    assert report["domains"]["a10_confidentiality"]["status"] == "FAIL"
    assert report["admission"] == "HOLD"


def test_passing_a10_does_not_supply_security_or_review_proof():
    report = summarize(
        input_payload("success", "success", a10="success")
    )["independent_gates"]
    assert report["domains"]["a10_confidentiality"]["status"] == "PASS"
    assert report["domains"]["bandit"]["status"] == "UNKNOWN"
    assert report["domains"]["safety"]["status"] == "UNKNOWN"
    assert report["domains"]["independent_review"]["status"] == "UNKNOWN"
    assert report["merge_authorized"] is False


def test_twelve_matrix_jobs_mandatory_not_one_successful_job():
    payload = input_payload("success", "success")
    payload["jobs"] = [
        item for item in payload["jobs"]
        if item["name"] != "Test Python 3.9 on macos-latest"
    ]
    result = gate(payload, "enterprise_ci")
    assert result["status"] == "UNKNOWN"
    assert result["missing_jobs"] == ["Test Python 3.9 on macos-latest"]
    assert gate(payload, "workflow_governance")["status"] == "PASS"


def test_cannot_count_green_when_final_ci_summary_missing():
    payload = input_payload("success", "success")
    payload["jobs"] = [
        item for item in payload["jobs"] if item["name"] != "CI Summary"
    ]
    assert gate(payload, "enterprise_ci")["status"] == "UNKNOWN"


def test_missing_pytest_step_makes_enterprise_unknown_not_pass():
    payload = input_payload("success", "success")
    payload["jobs"][0].pop("steps")
    result = gate(payload, "enterprise_ci")
    assert result["status"] == "UNKNOWN"
    assert result["missing_steps"] == [
        "Test Python 3.9 on ubuntu-latest:Run pytest --benchmark-disable with coverage"
    ]


def test_governance_workflow_final_red_dominates_advisory_green_steps():
    payload = input_payload()
    payload["jobs"][-1]["steps"] = [
        {"name": "Validate workflow policy and retain first-red",
         "status": "completed", "conclusion": "success"},
        {"name": "Check governed inventory and retain first-red",
         "status": "completed", "conclusion": "success"},
        {"name": "Fail closed on governance red",
         "status": "completed", "conclusion": "failure"},
    ]
    assert gate(payload, "workflow_governance")["status"] == "FAIL"


def test_queued_governance_is_pending_not_failure_or_pass():
    payload = input_payload("success", None)
    report = summarize(payload)["independent_gates"]
    assert report["domains"]["enterprise_ci"]["status"] == "PASS"
    assert report["domains"]["workflow_governance"]["status"] == "PENDING"
    assert report["domain_counts"]["FAIL"] == 0
    assert report["admission"] == "HOLD"


def test_skipped_selected_governance_is_blocked_not_green():
    payload = input_payload("success", "skipped")
    result = gate(payload, "workflow_governance")
    assert result["status"] == "BLOCKED"


def test_malformed_or_swapped_workflow_identity_rejected():
    payload = input_payload()
    payload["gate_bindings"]["enterprise_ci"]["run_id"] = 102
    with pytest.raises(ValueError, match="gate binding mismatches"):
        summarize(payload)


@pytest.mark.parametrize("bad", [True, 0, -1, "101", None])
def test_invalid_native_run_selection_never_claims_pass(bad):
    payload = input_payload()
    payload["gate_bindings"]["enterprise_ci"]["run_id"] = bad
    with pytest.raises(ValueError, match="positive native integer"):
        summarize(payload)


def test_wrong_attempt_cannot_borrow_pass_from_previous_attempt():
    payload = input_payload()
    payload["gate_bindings"]["enterprise_ci"]["run_attempt"] = 2
    outcome = gate(payload, "enterprise_ci")
    assert outcome["status"] == "UNKNOWN"
    assert outcome["run_id"] == 101
    assert outcome["run_attempt"] == 2
    assert outcome["run_url"] is None


def test_run_from_different_sha_rejected():
    payload = input_payload()
    payload["runs"][0]["head_sha"] = OTHER_SHA
    with pytest.raises(ValueError, match="run SHA"):
        summarize(payload)


def test_fake_binding_for_review_or_security_cannot_grant_authority():
    for domain in ("independent_review", "bandit", "safety"):
        payload = input_payload()
        payload["gate_bindings"][domain] = {"run_id": 101, "run_attempt": 1}
        with pytest.raises(ValueError, match="unsupported independent gate"):
            summarize(payload)


def test_duplicate_job_names_in_one_gate_run_rejected():
    payload = input_payload()
    extra = copy.deepcopy(payload["jobs"][0])
    extra["id"] = 99999
    payload["jobs"].append(extra)
    with pytest.raises(ValueError, match="duplicate job name"):
        summarize(payload)


def test_run_url_must_bind_expected_repo_and_exact_run():
    payload = input_payload()
    payload["runs"][0]["html_url"] = (
        "https://github.com/GBOGEB/ABACUS/actions/runs/999"
    )
    with pytest.raises(ValueError, match="gate binding mismatches"):
        summarize(payload)


def test_workflow_success_but_required_job_failed_does_not_pass():
    payload = input_payload("success", "success")
    payload["jobs"][0]["conclusion"] = "failure"
    assert gate(payload, "enterprise_ci")["status"] == "FAIL"


def test_no_contradictory_multi_run_credit_to_enterprise():
    payload = input_payload("success", "success")
    payload["runs"].append(
        workflow(201, ENTERPRISE, "DMAIC V3 Enterprise CI", "failure")
    )
    payload["jobs"].append(job(2010, 201, "CI Summary", "failure"))
    report = summarize(payload)["independent_gates"]
    assert report["domains"]["enterprise_ci"]["run_id"] == 101
    assert report["domains"]["enterprise_ci"]["status"] == "PASS"
    assert report["admission"] == "HOLD"
