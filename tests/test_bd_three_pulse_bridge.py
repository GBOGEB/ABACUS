"""Negative controls for the read-only canonical BD three-pulse consumer."""

import copy
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "bd_three_pulse_bridge.py"
SPEC = importlib.util.spec_from_file_location("bd_three_pulse_bridge", SOURCE)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def pulse(i):
    """One source-bound Bandit population per pulse; separate CI controls."""
    sha = str(i) * 40
    run_id, job_id = 100 + i, 200 + i
    scope = {
        "repository": "GBOGEB/ABACUS",
        "head_sha": sha,
        "scan_configuration": "config-v1",
        "run_id": run_id,
        "job_id": job_id,
        "evidence_url": (
            f"https://github.com/GBOGEB/ABACUS/actions/runs/{run_id}/job/{job_id}"
        ),
    }
    roots = []
    for j in range(i):
        roots.append(
            {
                "root_id": f"BD-{i:012x}{j:012x}",
                "category": "BANDIT",
                "fingerprint": f"{i:032x}{j:032x}",
                "source_path": "tests/test_example.py",
                "rule_or_error_code": "B101",
                "line": j + 1,
                "owner_lane": "B5-tests",
                "observations": [
                    {
                        "repository": scope["repository"],
                        "source_sha": scope["head_sha"],
                        "run_id": scope["run_id"],
                        "job_id": scope["job_id"],
                        "evidence_url": scope["evidence_url"],
                        "scan_configuration": scope["scan_configuration"],
                        "source": "bandit_disjoint",
                    }
                ],
                "disposition": "OPEN_UNREVIEWED",
            }
        )
    return {
        "schema": "bd.ldab.joined.census.v1",
        "scope": scope,
        "metrics": {"full_bandit_unique": i, "comparable_delta": None},
        "roots": roots,
        "merge_admission": "HOLD",
        "security_disposition": "INDEPENDENT_REVIEW_REQUIRED",
        "authority_transfer": False,
        "security_waiver": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


def bandit_root(row):
    scope = row["scope"]
    return {
        "root_id": "BD-" + "a" * 24,
        "category": "BANDIT",
        "fingerprint": "f" * 64,
        "source_path": "scripts/example.py",
        "rule_or_error_code": "B101",
        "line": 4,
        "owner_lane": "B2-source",
        "disposition": "OPEN_UNREVIEWED",
        "observations": [
            {
                "repository": scope["repository"],
                "source_sha": scope["head_sha"],
                "run_id": scope["run_id"],
                "job_id": scope["job_id"],
                "scan_configuration": scope["scan_configuration"],
                "evidence_url": scope["evidence_url"],
                "source": "bandit_disjoint",
            }
        ],
    }


def test_three_pulses_preserve_unknown_and_are_deterministic():
    inp = [pulse(i, include_bandit=True) for i in (1, 2, 3)]
    a = m.rollup(inp)
    assert a == m.rollup(inp)
    assert [p["bandit_observations"] for p in a["pulses"]] == [1, 2, 3]
    assert a["pulses"][2]["root_open"] is None
    assert a["pulses"][2]["accepted_engineering_root_closures"] is None
    assert a["movements"][0]["coverage"]["main_branch"]["delta_covered"] is None
    assert a["engineering_credit_delta"] == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.pop("metrics"),
        lambda p: p.update(merge_admission="GO"),
        lambda p: p.update(authority_transfer=True),
        lambda p: p.update(security_waiver=True),
        lambda p: p["metrics"].update(full_bandit_unique=True),
        lambda p: p.update(roots=[{"root_id": "same"}, {"root_id": "same"}]),
        lambda p: p["scope"].update(head_sha="MALFORMED"),
        lambda p: p["scope"].update(repository="GBOGEB/CODEX"),
        lambda p: p.update(formal_credit_delta=1),
        lambda p: p.update(security_disposition="APPROVED"),
        lambda p: p["scope"].pop("run_id"),
        lambda p: p["scope"].update(scan_configuration=""),
    ],
)
def test_reject_forged_or_ambiguous_claims(change):
    rows = [pulse(i) for i in (1, 2, 3)]
    change(rows[1])
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_zero_and_nonzero_bandit_populations_are_distinct():
    zero = pulse(1)
    positive = pulse(2, include_bandit=True)
    third = pulse(3)
    assert zero["metrics"]["full_bandit_unique"] == 0
    assert positive["metrics"]["full_bandit_unique"] == 2
    for root in positive["roots"]:
        observation = root["observations"][0]
        assert observation["source_sha"] == positive["scope"]["head_sha"]
        assert observation["scan_configuration"] == positive["scope"]["scan_configuration"]
        assert observation["evidence_url"] == positive["scope"]["evidence_url"]
    result = m.rollup([zero, positive, third])
    assert [p["bandit_observations"] for p in result["pulses"]] == [0, 2, 0]
    assert result["formal_credit_delta"] == result["engineering_credit_delta"] == 0


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("formal_credit_delta", 0.0),
        ("formal_credit_delta", False),
        ("engineering_credit_delta", 0.0),
        ("engineering_credit_delta", False),
    ],
)
def test_reject_noninteger_zero_credit_claims(field, forged):
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0][field] = forged
    with pytest.raises(ValueError, match="authority/admission/security contract"):
        m.rollup(rows)


def test_reject_duplicate_sha_and_missing_pulse():
    rows = [pulse(i) for i in (1, 2, 3)]
    with pytest.raises(ValueError):
        m.rollup(rows[:2])
    rows[1]["scope"]["head_sha"] = rows[0]["scope"]["head_sha"]
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_same_denominator_cannot_promote_unverified_coverage():
    rows = [pulse(i) for i in (1, 2, 3)]
    for i, row in enumerate(rows):
        row["coverage"] = {
            "main_branch": {"covered": 10 + i, "eligible": 20, "config": "same"}
        }
    # A matched denominator does not independently authenticate a coverage receipt.
    # The hardened producer rejects even quarantined user-provided enrichment.
    with pytest.raises(ValueError, match="unverified coverage enrichment"):
        m.rollup(rows)


def test_reject_forged_coverage_verification_marker():
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["coverage"] = {
        "main_branch": {
            "covered": 17, "eligible": 20, "config": "v1", "verified": True
        }
    }
    with pytest.raises(ValueError):
        m.rollup(rows)


@pytest.mark.parametrize(
    "coverage",
    [
        {"main_branch": {"covered": 1, "eligible": 0, "config": "v1"}},
        {"main_branch": {"covered": 3, "eligible": 2, "config": "v1"}},
        {"main_branch": {"covered": True, "eligible": 2, "config": "v1"}},
        {"main_branch": {"covered": 1, "eligible": 2, "config": ""}},
    ],
)
def test_unverified_coverage_always_fails_closed(coverage):
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["coverage"] = coverage
    with pytest.raises(ValueError, match="unverified coverage"):
        m.rollup(rows)


def test_bandit_denominator_999_with_empty_roots_rejected():
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[1]["metrics"]["full_bandit_unique"] = 999
    rows[1]["roots"] = []
    with pytest.raises(ValueError, match="Bandit numerator"):
        m.rollup(rows)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["roots"][0].update(category="CI"),
        lambda p: p["roots"][0].update(fingerprint="fake"),
        lambda p: p["roots"][0]["observations"][0].update(source_sha="f" * 40),
        lambda p: p["roots"][0]["observations"][0].update(run_id=999),
        lambda p: p["roots"][0]["observations"][0].update(scan_configuration="spoof"),
        lambda p: p["roots"][0].update(observations=[]),
        lambda p: p["roots"][0].update(category="UNKNOWN"),
    ],
)
def test_reject_spoofed_bandit_root_claims(change):
    rows = [pulse(i, include_bandit=True) for i in (1, 2, 3)]
    change(rows[1])
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_ci_root_does_not_inflate_bandit_denominator():
    rows = [pulse(i, include_bandit=True) for i in (1, 2, 3)]
    rows[0]["roots"].append(
        {
            "root_id": "CI-" + "d" * 24,
            "category": "CI",
            "fingerprint": None,
            "observations": [{"repository": "GBOGEB/ABACUS", "source": "ci_failure"}],
        }
    )
    result = m.rollup(rows)
    assert result["pulses"][0]["bandit_observations"] == 1
    assert result["pulses"][0]["candidate_root_count"] == 2


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(roots=None),
        lambda p: p["roots"].__setitem__(0, None),
        lambda p: p["roots"][0].update(root_id=123),
        lambda p: p.update(schema="bd.forbidden.v1"),
        lambda p: p["scope"].update(evidence_url="https://example.invalid/forgery"),
    ],
)
def test_reject_remaining_unbound_census_shapes(change):
    rows = [pulse(i) for i in (1, 2, 3)]
    change(rows[1])
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_bandit_census_reconciles():
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["metrics"]["full_bandit_unique"] = 1
    rows[0]["roots"] = [bandit_root(rows[0])]
    result = m.rollup(rows)
    assert result["pulses"][0]["bandit_observations"] == 1
    assert result["pulses"][0]["candidate_root_count"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(category="CI"),
        lambda r: r.update(root_id="CI-" + "a" * 24),
        lambda r: r.update(fingerprint="bad"),
        lambda r: r.update(owner_lane="UNKNOWN"),
        lambda r: r.update(observations=[]),
        lambda r: r["observations"][0].update(source_sha="0" * 40),
        lambda r: r["observations"][0].update(job_id=999),
        lambda r: r["observations"][0].update(source="forged"),
    ],
)
def test_reject_bad_bandit_root(mutation):
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["metrics"]["full_bandit_unique"] = 1
    root = bandit_root(rows[0])
    rows[0]["roots"].append(root)
    mutation(root)
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_bandit_denominator_mismatch_rejected():
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["metrics"]["full_bandit_unique"] = 999
    with pytest.raises(ValueError, match="Bandit numerator"):
        m.rollup(rows)
    rows[0]["metrics"]["full_bandit_unique"] = 0
    rows[0]["roots"].append(bandit_root(rows[0]))
    with pytest.raises(ValueError, match="Bandit numerator"):
        m.rollup(rows)


def test_canonical_pulse_inputs_remain_immutable():
    rows = [pulse(i) for i in (1, 2, 3)]
    baseline = copy.deepcopy(rows)
    m.rollup(rows)
    assert rows == baseline
