"""Negative controls for the read-only canonical BD three-pulse consumer."""

import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "bd_three_pulse_bridge.py"
SPEC = importlib.util.spec_from_file_location("bd_three_pulse_bridge", SOURCE)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def pulse(i):
    sha = str(i) * 40
    run_id, job_id = 100 + i, 200 + i
    scope = {
        "repository": "GBOGEB/ABACUS",
        "head_sha": sha,
        "scan_configuration": "bandit-full-v1",
        "run_id": run_id,
        "job_id": job_id,
        "evidence_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{run_id}/job/{job_id}",
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


def test_three_pulses_preserve_unknown_and_are_deterministic():
    inp = [pulse(i) for i in (1, 2, 3)]
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


def test_reject_duplicate_sha_and_missing_pulse():
    rows = [pulse(i) for i in (1, 2, 3)]
    with pytest.raises(ValueError):
        m.rollup(rows[:2])
    rows[1]["scope"]["head_sha"] = rows[0]["scope"]["head_sha"]
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_reject_self_reported_coverage_even_when_denominators_match():
    rows = [pulse(i) for i in (1, 2, 3)]
    for i, row in enumerate(rows):
        row["coverage"] = {
            "main_branch": {"covered": 10 + i, "eligible": 20, "config": "same"}
        }
    with pytest.raises(ValueError, match="unverified coverage"):
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
    with pytest.raises(ValueError, match="denominator"):
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
    rows = [pulse(i) for i in (1, 2, 3)]
    change(rows[1])
    with pytest.raises(ValueError):
        m.rollup(rows)


def test_ci_root_does_not_inflate_bandit_denominator():
    rows = [pulse(i) for i in (1, 2, 3)]
    rows[0]["roots"].append(
        {
            "root_id": "CI-fake-but-distinct",
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


def test_cli_emits_deterministic_validated_output(tmp_path, monkeypatch):
    import json
    import runpy
    import sys

    paths = []
    for i in (1, 2, 3):
        path = tmp_path / f"pulse-{i}.json"
        path.write_text(json.dumps(pulse(i)), encoding="utf-8")
        paths.append(path)
    out = tmp_path / "receipt.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SOURCE), "--inputs", *(str(path) for path in paths), "--out", str(out)],
    )
    runpy.run_path(str(SOURCE), run_name="__main__")
    first = out.read_bytes()
    runpy.run_path(str(SOURCE), run_name="__main__")
    assert out.read_bytes() == first
    assert json.loads(first)["merge_admission"] == "HOLD"
