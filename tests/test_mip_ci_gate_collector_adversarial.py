"""Attempt-scoped negative proofs for the GitHub CI collector, without network calls."""

import copy

import pytest

from tools import mip_ci_gate_collector as collector

SHA = "a" * 40
RUN = 101


def run():
    return {
        "id": RUN,
        "run_attempt": 1,
        "head_sha": SHA,
        "path": collector.EXPECTED_PATHS["workflow_governance"],
        "html_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{RUN}",
        "name": "CI Workflow Governance",
        "created_at": "2026-10-17T09:00:00Z",
        "status": "completed",
        "conclusion": "success",
    }


def job(identity=201):
    return {
        "id": identity,
        "run_id": RUN,
        "run_attempt": 1,
        "head_sha": SHA,
        "name": "policy-and-inventory",
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-10-17T09:00:00Z",
        "started_at": "2026-10-17T09:01:00Z",
        "completed_at": "2026-10-17T09:02:00Z",
        "steps": [
            {
                "name": "Run policy inventory",
                "status": "completed",
                "conclusion": "success",
            }
        ],
    }


_DEFAULT = object()


def getter(run_value=_DEFAULT, pages=None):
    run_value = run() if run_value is _DEFAULT else run_value
    pages = [{"total_count": 1, "jobs": [job()]}] if pages is None else pages

    def get(path):
        if "/jobs?" not in path:
            return copy.deepcopy(run_value)
        page = int(path.rsplit("page=", 1)[1])
        return copy.deepcopy(pages[min(page - 1, len(pages) - 1)])

    return get


def collect(get):
    return collector.collect_gate_input(
        SHA, {"workflow_governance": (RUN, 1)}, getter=get
    )


@pytest.mark.parametrize("selected", [None, {}, [], {"security": (RUN, 1)}])
def test_unknown_or_empty_gate_selection_never_infers_latest(selected):
    with pytest.raises(ValueError, match="supported gate selections"):
        collector.collect_gate_input(SHA, selected, getter=getter())


@pytest.mark.parametrize(
    "pair", [None, RUN, (RUN,), (RUN, 1, 2), (True, 1), (RUN, False), (0, 1), (RUN, 0)]
)
def test_invalid_explicit_attempt_pair_is_rejected(pair):
    with pytest.raises(ValueError):
        collector.collect_gate_input(
            SHA, {"workflow_governance": pair}, getter=getter()
        )


@pytest.mark.parametrize("replacement", [None, [], "unexpected", 123])
def test_non_object_native_run_fails_closed(replacement):
    with pytest.raises(ValueError, match="invalid GitHub run response"):
        collect(getter(run_value=replacement))


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 102),
        ("head_sha", "b" * 40),
        ("run_attempt", 2),
        ("path", ".github/workflows/unrelated.yml"),
        ("html_url", "https://invalid.example"),
    ],
)
def test_run_identity_changes_do_not_cross_credit(field, value):
    native = run()
    native[field] = value
    with pytest.raises(ValueError, match="identity/SHA/workflow mismatch"):
        collect(getter(run_value=native))


@pytest.mark.parametrize(
    "invalid_page",
    [
        {},
        {"total_count": True, "jobs": []},
        {"total_count": -1, "jobs": []},
        {"total_count": 1, "jobs": "not a list"},
        {"total_count": 2001, "jobs": []},
        {"total_count": 2, "jobs": []},
        {"total_count": 1, "jobs": [job(i) for i in range(101)]},
    ],
)
def test_invalid_or_incomplete_job_page_rejected(invalid_page):
    with pytest.raises(ValueError):
        collect(getter(pages=[invalid_page]))


def test_total_count_drift_between_pages_is_not_silent():
    pages = [
        {"total_count": 2, "jobs": [job(201)]},
        {"total_count": 3, "jobs": [job(202)]},
    ]
    with pytest.raises(ValueError, match="job total changed"):
        collect(getter(pages=pages))


def test_native_job_pagination_missing_tail_is_not_success():
    pages = [
        {"total_count": 201, "jobs": [job(i) for i in range(1, 101)]},
        {"total_count": 201, "jobs": [job(i) for i in range(101, 201)]},
        {"total_count": 201, "jobs": []},
    ]
    with pytest.raises(ValueError, match="incomplete native jobs page"):
        collect(getter(pages=pages))


@pytest.mark.parametrize("native_job", [None, [], "corrupt", 99])
def test_non_object_native_job_is_rejected(native_job):
    with pytest.raises(ValueError, match="native job object required"):
        collect(getter(pages=[{"total_count": 1, "jobs": [native_job]}]))


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 0),
        ("id", True),
        ("run_id", 999),
        ("run_attempt", 2),
        ("head_sha", "f" * 40),
    ],
)
def test_job_identity_and_ambiguous_attempt_rejected(field, value):
    item = job()
    item[field] = value
    with pytest.raises(ValueError, match="native job identity"):
        collect(getter(pages=[{"total_count": 1, "jobs": [item]}]))


def test_corrupt_step_detail_cannot_generate_green_receipt():
    item = job()
    item["steps"] = {"fake": "passed"}
    with pytest.raises(ValueError, match="steps are not a list"):
        collect(getter(pages=[{"total_count": 1, "jobs": [item]}]))


@pytest.mark.parametrize(
    "projection",
    [
        {"merge_authorized": True, "independent_gates": {"admission": "HOLD"}},
        {"merge_authorized": False, "independent_gates": {"admission": "PASS"}},
    ],
)
def test_forged_projection_is_blocked(monkeypatch, projection):
    monkeypatch.setattr(collector, "summarize", lambda _: projection)
    with pytest.raises(ValueError, match="retain independent HOLD"):
        collect(getter())
