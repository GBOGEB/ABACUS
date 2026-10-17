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
        "scope": {"repository": "GBOGEB/ABACUS", "head_sha": str(i) * 40},
        "metrics": {"full_bandit_unique": i, "comparable_delta": None},
        "roots": [{"root_id": f"CI-{i}"}],
        "merge_admission": "HOLD",
        "authority_transfer": False, "security_waiver": False,
    }


def test_three_pulses_preserve_unknown_and_are_deterministic():
    inp = [pulse(i) for i in (1, 2, 3)]
    a = m.rollup(inp)
    assert a == m.rollup(inp)
    assert a["pulses"][2]["root_open"] is None
    assert a["pulses"][2]["accepted_engineering_root_closures"] is None
    assert a["movements"][0]["coverage"]["main_branch"]["delta_covered"] is None
    assert a["engineering_credit_delta"] == 0


@pytest.mark.parametrize("change", [
    lambda p: p.pop("metrics"),
    lambda p: p.update(merge_admission="GO"),
    lambda p: p.update(authority_transfer=True),
    lambda p: p.update(security_waiver=True),
    lambda p: p["metrics"].update(full_bandit_unique=True),
    lambda p: p.update(roots=[{"root_id": "same"}, {"root_id": "same"}]),
    lambda p: p["scope"].update(head_sha="MALFORMED"),
    lambda p: p["scope"].update(repository="GBOGEB/CODEX"),
])
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


def test_only_scope_matched_coverage_deltas():
    rows = [pulse(i) for i in (1, 2, 3)]
    for i, row in enumerate(rows):
        row["coverage"] = {
            "main_branch": {"covered": 10 + i, "eligible": 20, "config": "same"}
        }
    rows[2]["coverage"]["main_branch"]["eligible"] = 21
    result = m.rollup(rows)
    assert result["movements"][0]["coverage"]["main_branch"]["delta_covered"] == 1
    assert result["movements"][1]["coverage"]["main_branch"]["delta_covered"] is None


@pytest.mark.parametrize("coverage", [
    {"main_branch": {"covered": 1, "eligible": 0, "config": "v1"}},
    {"main_branch": {"covered": 3, "eligible": 2, "config": "v1"}},
    {"main_branch": {"covered": True, "eligible": 2, "config": "v1"}},
    {"main_branch": {"covered": 1, "eligible": 2, "config": ""}},
])
def test_bad_coverage_fails_closed(coverage):
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["coverage"] = coverage
    with pytest.raises(ValueError):
        m.rollup(rows)
