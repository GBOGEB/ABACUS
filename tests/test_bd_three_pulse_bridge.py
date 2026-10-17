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
    return {
        "schema": "bd.ldab.joined.census.v1",
        "scope": {
            "repository": "GBOGEB/ABACUS",
            "head_sha": str(i) * 40,
            "run_id": 100 + i,
            "job_id": 200 + i,
            "scan_configuration": "config-v1",
            "evidence_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{100+i}",
        },
        "metrics": {"full_bandit_unique": 0, "comparable_delta": None},
        "roots": [
            {"root_id": f"CI-{i:024x}", "category": "CI", "fingerprint": None}
        ],
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
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
    inp = [pulse(i) for i in (1, 2, 3)]
    a = m.rollup(inp)
    assert a == m.rollup(inp)
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
    ],
)
def test_reject_forged_or_ambiguous_claims(change):
    rows = [pulse(i) for i in (1, 2, 3)]
    change(rows[1])
    with pytest.raises(ValueError):
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
    result = m.rollup(rows)
    assert result["pulses"][0]["coverage"] is None
    candidate = result["pulses"][0]["coverage_candidates_unverified"]["main_branch"]
    assert candidate["covered"] == 10
    assert result["movements"][0]["coverage"]["main_branch"]["comparable"] is False
    assert result["movements"][0]["coverage"]["main_branch"]["delta_covered"] is None


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
def test_bad_coverage_fails_closed(coverage):
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["coverage"] = coverage
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_bandit_census_reconciles():
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["metrics"]["full_bandit_unique"] = 1
    rows[0]["roots"].append(bandit_root(rows[0]))
    result = m.rollup(rows)
    assert result["pulses"][0]["bandit_observations"] == 1
    assert result["pulses"][0]["candidate_root_count"] == 2


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
