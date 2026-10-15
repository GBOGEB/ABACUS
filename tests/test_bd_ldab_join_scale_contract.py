"""Fail-closed boundary tests for global BD/LDAB join; no worker or merge credit.

These cases exercise the canonical read-only producer, not the EVERRED V3
prototype or CODEX's stage-only transport. Unknown metrics stay unknown.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "bd_ldab_join_census.py"
SPEC = importlib.util.spec_from_file_location("joined_census_scale_contract", SOURCE)
census_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census_module)

HEAD = "a" * 40
BEFORE = "b" * 40
FP = "c" * 64
REPO = "GBOGEB/ABACUS"
URL = "https://github.com/GBOGEB/ABACUS/actions/runs/38531518523"


def report(rows=None, sha=HEAD):
    if rows is None:
        rows = [{"path": "scripts/one.py", "fingerprint": FP, "rule": "B603", "line": 3}]
    lanes = {}
    for name in census_module.LANES:
        items = [dict(row) for row in rows] if name == "B3-subprocess" else []
        lanes[name] = {
            "items": items,
            "findings": len(items),
            "files": len({row["path"] for row in items}),
        }
    return {
        "schema": "bandit.disjoint.census.v1",
        "exact_sha": sha,
        "lanes": lanes,
        "total_unique": len(rows),
    }


def source_bundle(rows=None):
    return {
        "schema": "bd.ldab.input.v1",
        "scope": {
            "repository": REPO,
            "head_sha": HEAD,
            "scan_configuration": "bandit-v1-default",
            "run_id": 38531518523,
            "job_id": 115744267733,
            "evidence_url": URL,
        },
        "bandit_disjoint": report(rows=rows),
    }


def ci_observation(**updates):
    item = {
        "repository": REPO,
        "source_sha": HEAD,
        "signature": "CI.COVERAGE.JSON_MISSING",
        "rule_or_error_code": "COV_JSON",
        "source_path": "tests/orchestrator.py",
        "run_id": 38531518524,
        "job_id": 115744267734,
        "evidence_url": URL,
    }
    item.update(updates)
    return item


def debug_observation(**updates):
    item = {
        "repository": REPO,
        "source_sha": HEAD,
        "run_id": 38531518525,
        "job_id": 115744267735,
        "evidence_url": URL,
        "real_probe_steps": 4,
        "runner_id": "unverified-runner",
        "session_id": "unverified-session",
    }
    item.update(updates)
    return item


@pytest.mark.parametrize("value", [None, False, 1, [], {}, " ", ""])
def test_non_textual_identifiers_are_not_accepted(value):
    with pytest.raises(ValueError, match="requires a non-empty string"):
        census_module.need_text(value, "owner")


@pytest.mark.parametrize("value", [None, True, 1, "A" * 40, "0" * 39, "g" * 40, ""])
def test_exact_sha_rejects_invalid_inputs(value):
    with pytest.raises(ValueError, match="lowercase exact SHA"):
        census_module.need_sha(value, "source")


@pytest.mark.parametrize("value", [None, True, False, 0, -1, 3.0, "12"])
def test_integer_gate_rejects_missing_bools_and_non_ints(value):
    with pytest.raises(ValueError, match="requires integer"):
        census_module.need_integer(value, "run")


@pytest.mark.parametrize("value", [None, "", "http://github.com/a/b", "https://example.com/a/b"])
def test_external_or_missing_evidence_urls_rejected(value):
    with pytest.raises(ValueError):
        census_module.need_url(value, "evidence")


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("src/./one.py", "src/one.py"),
        ("src//one.py", "src/one.py"),
        ("src\\one.py", "src/one.py"),
        ("./src/../outside", None),
        ("//server/share.py", None),
        ("D:\\private\\data.py", None),
        ("././", None),
    ],
)
def test_path_canonicalization_preserves_reject_boundary(raw, normalized):
    if normalized is None:
        with pytest.raises(ValueError):
            census_module.safe_path(raw)
    else:
        assert census_module.safe_path(raw) == normalized


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("schema", "unsupported"),
        ("bandit_disjoint", []),
        ("scope", None),
    ],
)
def test_join_input_schema_invalidity_fails_closed(field, replacement):
    item = source_bundle()
    item[field] = replacement
    with pytest.raises(ValueError):
        census_module.join(item)


@pytest.mark.parametrize("field", ["run_id", "job_id"])
def test_source_scope_requires_actual_numeric_ids(field):
    item = source_bundle()
    item["scope"][field] = True
    with pytest.raises(ValueError, match="requires integer"):
        census_module.join(item)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("bad_lanes", "exactly four"),
        ("bad_items", "Invalid items"),
        ("bad_total", "Full Bandit total"),
        ("bad_findings", "Denominator mismatch"),
        ("bad_files", "Denominator mismatch"),
        ("bad_fp", "Invalid Bandit fingerprint"),
        ("bad_rule", "non-empty string"),
        ("bad_line", "requires integer"),
    ],
)
def test_full_bandit_denominators_and_source_contracts(mutation, expected):
    item = source_bundle()
    scan = item["bandit_disjoint"]
    lane = scan["lanes"]["B3-subprocess"]
    finding = lane["items"][0]
    if mutation == "bad_lanes":
        scan["lanes"].pop("B2-source")
    elif mutation == "bad_items":
        lane["items"] = None
    elif mutation == "bad_total":
        scan["total_unique"] = 99
    elif mutation == "bad_findings":
        lane["findings"] = 99
    elif mutation == "bad_files":
        lane["files"] = 99
    elif mutation == "bad_fp":
        finding["fingerprint"] = "not-a-fingerprint"
    elif mutation == "bad_rule":
        finding["rule"] = ""
    elif mutation == "bad_line":
        finding["line"] = True
    with pytest.raises(ValueError, match=expected):
        census_module.join(item)


def test_alias_file_denominator_cannot_count_same_normalized_path_twice():
    rows = [
        {"path": "src/file.py", "fingerprint": FP, "rule": "B603", "line": 3},
        {"path": "src//file.py", "fingerprint": "d" * 64, "rule": "B603", "line": 4},
    ]
    with pytest.raises(ValueError, match="Denominator mismatch"):
        census_module.join(source_bundle(rows=rows))


@pytest.mark.parametrize("bad", [None, {}, "not a list"])
def test_ci_producer_requires_observation_array(bad):
    item = source_bundle()
    item["ci_failures"] = bad
    with pytest.raises(ValueError, match="require arrays"):
        census_module.join(item)


@pytest.mark.parametrize("field,bad", [("source_sha", "no-sha"), ("job_id", False), ("source_path", "../private")])
def test_ci_observations_reject_untrusted_identity_and_paths(field, bad):
    item = source_bundle()
    item["ci_failures"] = [ci_observation(**{field: bad})]
    with pytest.raises(ValueError):
        census_module.join(item)


def test_ci_cross_repo_cannot_inherit_bandit_ownership():
    item = source_bundle()
    item["ci_failures"] = [ci_observation(
        repository="GBOGEB/CODEX", source_sha="e" * 40)]
    out = census_module.join(item)
    ci_root = next(r for r in out["roots"] if r["category"] == "CI")
    assert ci_root["owner_lane"] is None
    assert out["merge_admission"] == "HOLD"
    assert out["metrics"]["changed_line_coverage"] is None


@pytest.mark.parametrize("field,bad", [("source_sha", "no-sha"), ("real_probe_steps", -1),
                                      ("real_probe_steps", True), ("run_id", 0)])
def test_debugger_provenance_rejects_invalid_identity_and_steps(field, bad):
    item = source_bundle()
    item["debug_receipts"] = [debug_observation(**{field: bad})]
    with pytest.raises(ValueError):
        census_module.join(item)


def test_multiple_unverified_debug_sessions_do_not_become_active_workers():
    item = source_bundle()
    item["debug_receipts"] = [
        debug_observation(run_id=30, job_id=40),
        debug_observation(run_id=31, job_id=41, session_id=None),
    ]
    out = census_module.join(item)
    assert out["metrics"]["debug_receipts"] == 2
    assert out["metrics"]["debug_reported_sessions"] == 1
    assert out["metrics"]["active_workers"] is None
    assert out["unlinked_debug_receipts"][0]["proof_level"] == "REPORTED_UNVERIFIED"
    assert out["merge_admission"] == "HOLD"


def test_old_and_new_fingerprint_sets_are_not_raw_count_assumptions():
    old_finding = {"path": "scripts/old.py", "fingerprint": "f" * 64, "rule": "B603", "line": 8}
    now = source_bundle()
    now["previous"] = {
        "repository": REPO,
        "head_sha": BEFORE,
        "scan_configuration": "bandit-v1-default",
        "bandit_disjoint": report(rows=[old_finding], sha=BEFORE),
    }
    delta = census_module.join(now)["metrics"]["comparable_delta"]
    assert delta["before_unique"] == 1 and delta["after_unique"] == 1
    assert (delta["new"], delta["resolved"], delta["net_reduction"]) == (1, 1, 0)
    assert delta["status"] == "FINGERPRINT_DELTA_ONLY_REVIEW_REQUIRED"


def test_current_and_previous_same_sha_are_not_a_burndown():
    item = source_bundle()
    item["previous"] = {
        "repository": REPO,
        "head_sha": HEAD,
        "scan_configuration": "bandit-v1-default",
        "bandit_disjoint": report(sha=HEAD),
    }
    with pytest.raises(ValueError, match="shall differ"):
        census_module.join(item)


def test_output_has_no_top21_worker_or_coverage_promotion_from_valid_receipts():
    item = source_bundle()
    item["ci_failures"] = [ci_observation()]
    item["debug_receipts"] = [debug_observation()]
    out = census_module.join(item)
    assert out["merge_admission"] == "HOLD"
    assert out["security_disposition"] == "INDEPENDENT_REVIEW_REQUIRED"
    assert out["authority_transfer"] is False
    assert out["security_waiver"] is False
    assert out["formal_credit_delta"] == 0
    assert out["engineering_credit_delta"] == 0
    assert out["metrics"]["changed_line_coverage"] is None
    assert out["metrics"]["active_workers"] is None
    assert json.dumps(out, sort_keys=True) == json.dumps(census_module.join(item), sort_keys=True)
