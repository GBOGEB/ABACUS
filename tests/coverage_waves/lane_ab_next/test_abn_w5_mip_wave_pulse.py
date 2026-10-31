"""Behaviour tests for tools/mip_wave_pulse.py (fail-closed MIP wave pulse)."""

import copy
import hashlib
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/mip_wave_pulse.py", name="abn_w5_mip_wave_pulse")

HEAD = "a" * 40
BASE = "b" * 40
MAIN = "c" * 40


def _cov(covered=50, branches=20, sha=HEAD, **extra):
    doc = dict(
        scope="unit",
        config_id="cfg-1",
        source_sha=sha,
        lines_covered=covered,
        lines_total=100,
        branches_covered=branches,
        branches_total=40,
    )
    doc.update(extra)
    return doc


def _data(**extra):
    doc = {
        "schema": "abacus.mip.wave-input.v1",
        "repository": "GBOGEB/ABACUS",
        "head_sha": HEAD,
        "base_sha": BASE,
        "wave_id": "W5",
        "roots": [
            dict(root_id="R1", owner="ann", state="REPAIRED", fingerprint="fp1"),
            dict(
                root_id="R2",
                owner="bob",
                state="REOPENED",
                fingerprint="fp1",
                manifestations=3,
            ),
            dict(root_id="R3", owner="cy", state="NEW", fingerprint="fp2"),
        ],
        "jobs": [
            dict(
                run_id=11,
                job_id="22",
                head_sha=HEAD,
                duration_seconds=1800,
                result="success",
            ),
            dict(
                run_id="12",
                job_id=23,
                head_sha=HEAD,
                duration_seconds=1800.0,
                result="failure",
            ),
        ],
    }
    doc.update(extra)
    return doc


# --- coverage_delta -------------------------------------------------------


def test_coverage_delta_unknown_when_missing():
    assert mod.coverage_delta(None, _cov())["disposition"] == "UNKNOWN"
    assert mod.coverage_delta(_cov(), None)["reason"] == "missing comparable coverage"


def test_coverage_delta_comparable_math():
    result = mod.coverage_delta(_cov(50, 20), _cov(60, 30, sha=MAIN))
    assert result["disposition"] == "COMPARABLE"
    assert result["before_percent"] == pytest.approx(50.0)
    assert result["after_percent"] == pytest.approx(64.28571429)
    assert result["delta_percentage_points"] == pytest.approx(14.28571429)
    assert result["new_lines"] == 10
    assert result["new_branches"] == 10
    assert result["same_source"] is False
    assert result["before_source_sha"] == HEAD
    assert result["after_source_sha"] == MAIN


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope", "integration"),
        ("config_id", "cfg-2"),
        ("lines_total", 101),
        ("branches_total", 41),
    ],
)
def test_coverage_delta_incomparable(field, value):
    after = _cov(**{field: value})
    result = mod.coverage_delta(_cov(), after)
    assert result["disposition"] == "INCOMPARABLE"


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda c: "not a dict", "coverage must be object"),
        (lambda c: {k: v for k, v in c.items() if k != "scope"}, "missing scope"),
        (lambda c: dict(c, source_sha="xyz"), "invalid coverage source_sha"),
        (lambda c: dict(c, lines_covered=-1), "invalid lines_covered"),
        (lambda c: dict(c, branches_total=4.0), "invalid branches_total"),
        (lambda c: dict(c, lines_total=0, lines_covered=0), "zero coverage"),
        (lambda c: dict(c, lines_covered=101), "exceeds denominator"),
        (lambda c: dict(c, branches_covered=41), "exceeds denominator"),
    ],
)
def test_coverage_delta_rejects_malformed(mutate, message):
    with pytest.raises(ValueError, match=message):
        mod.coverage_delta(_cov(), mutate(_cov()))


# --- build: happy path ----------------------------------------------------


def test_build_without_closure_holds(tmp_path):
    pulse, backlog = mod.build(_data(), tmp_path)
    assert pulse["disposition"] == "MEASURED_NOT_MERGE_AUTHORIZED"
    assert pulse["worker_hours_observed"] == 1.0
    assert pulse["jobs"][0] == dict(
        run_id="11", job_id="22", result="success", duration_seconds=1800
    )
    assert pulse["coverage"]["disposition"] == "UNKNOWN"
    assert pulse["coverage_units_per_worker_hour"] is None
    assert pulse["formal_root_closure_count"] == 0
    assert pulse["artifact_hashes"] == {}
    assert backlog["closure_disposition"] == "HOLD_UNKNOWN"
    assert backlog["distinct_root_count"] == 3
    assert backlog["states"] == {"NEW": 1, "REOPENED": 1, "REPAIRED": 1}
    assert backlog["recurrence_by_fingerprint"] == {"fp1": 4, "fp2": 1}
    assert backlog["candidate_repaired_root_ids"] == ["R1"]
    assert backlog["verified_closed_root_ids"] == []
    assert backlog["reopened_root_ids"] == ["R2"]


def test_build_with_admitted_closure_and_artifacts(tmp_path):
    raw = b"evidence-bytes\n"
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.json").write_bytes(raw)
    closure = dict(
        merge_admitted=True,
        main_verified=True,
        merge_commit_sha=MAIN,
        verified_main_sha=MAIN,
        native_evidence_refs=["run/1"],
        individually_verified_root_ids=["R1"],
    )
    data = _data(
        artifacts={"receipt": "sub/a.json"},
        coverage_before=_cov(50, 20),
        coverage_after=_cov(60, 30),
        closure=closure,
        formal_baseline_roots=7,
        first_reds=["x"],
        required_tests=["t1"],
        tests=["t2"],
    )
    pulse, backlog = mod.build(data, tmp_path)
    assert pulse["artifact_hashes"]["receipt"] == {
        "path": "sub/a.json",
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    assert pulse["coverage"]["disposition"] == "COMPARABLE"
    assert pulse["coverage_units_per_worker_hour"] == 20.0
    assert pulse["formal_root_closure_count"] == 1
    assert pulse["first_reds"] == ["x"]
    assert pulse["required_tests"] == ["t1"]
    assert backlog["closure_disposition"] == "EXACT_MAIN_PROVEN"
    assert backlog["verified_closed_root_ids"] == ["R1"]
    assert backlog["verified_closed_count"] == 1
    assert backlog["formal_baseline_roots"] == 7


def test_build_comparable_without_hours_has_no_rate(tmp_path):
    data = _data(jobs=[], coverage_before=_cov(), coverage_after=_cov(60))
    pulse, _ = mod.build(data, tmp_path)
    assert pulse["coverage"]["disposition"] == "COMPARABLE"
    assert pulse["coverage_units_per_worker_hour"] is None


def test_build_closure_not_admitted_without_evidence_refs(tmp_path):
    closure = dict(
        merge_admitted=True,
        main_verified=True,
        merge_commit_sha=MAIN,
        verified_main_sha=MAIN,
        native_evidence_refs=[],
        individually_verified_root_ids=["R1"],
    )
    _, backlog = mod.build(_data(closure=closure), tmp_path)
    assert backlog["closure_disposition"] == "HOLD_UNKNOWN"
    assert backlog["verified_closed_root_ids"] == []


# --- build: fail-closed error paths ---------------------------------------


def _mutated(path, value):
    data = _data()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


@pytest.mark.parametrize(
    "path,value,message",
    [
        (("schema",), "v0", "schema mismatch"),
        (("wave_id",), "", "missing wave_id"),
        (("head_sha",), "ABC", "invalid head_sha"),
        (("base_sha",), "1234", "invalid base_sha"),
        (("repository",), "GBOGEB/CODEX", "unexpected repository"),
        (("roots",), {"a": 1}, "roots/jobs must be arrays"),
        (("jobs",), "x", "roots/jobs must be arrays"),
        (("roots", 0), ["bad"], "invalid root record"),
        (("roots", 1, "root_id"), "R1", "duplicate root_id"),
        (("roots", 0, "state"), "CLOSED", "invalid root state"),
        (("roots", 0, "owner"), "", "missing attribution"),
        (("roots", 0, "manifestations"), 0, "invalid manifestations"),
        (("roots", 0, "manifestations"), True, "invalid manifestations"),
        (("jobs", 0, "result"), None, None),
        (("jobs", 0), dict(run_id=1), "incomplete job"),
        (("jobs", 0, "head_sha"), "zz", "invalid job head_sha"),
        (("jobs", 0, "head_sha"), MAIN, "mixed-head native jobs"),
        (("jobs", 0, "duration_seconds"), -1, "invalid duration"),
        (("jobs", 0, "duration_seconds"), True, "invalid duration"),
        (("jobs", 0, "duration_seconds"), "9", "invalid duration"),
        (("jobs", 0, "run_id"), "run-1", "invalid native IDs"),
        (("jobs", 0, "job_id"), "-3", "invalid native IDs"),
    ],
)
def test_build_rejects_bad_input(tmp_path, path, value, message):
    data = _mutated(path, value)
    if message is None:
        pulse, _ = mod.build(data, tmp_path)
        assert pulse["jobs"][0]["result"] is None
        return
    with pytest.raises(ValueError, match=message):
        mod.build(data, tmp_path)


@pytest.mark.parametrize(
    "relative,message",
    [
        ("", "invalid artifact path"),
        (5, "invalid artifact path"),
        ("missing.json", "artifact absent/outside root"),
        ("../outside.json", "artifact absent/outside root"),
        ("empty.json", "empty artifact"),
    ],
)
def test_build_rejects_bad_artifacts(tmp_path, relative, message):
    root = tmp_path / "root"
    root.mkdir()
    (root / "empty.json").write_bytes(b"")
    (tmp_path / "outside.json").write_bytes(b"x")
    with pytest.raises(ValueError, match=message):
        mod.build(_data(artifacts={"a": relative}), root)


def _closure(**extra):
    doc = dict(
        merge_admitted=True,
        main_verified=True,
        merge_commit_sha=MAIN,
        verified_main_sha=MAIN,
        native_evidence_refs=["r"],
    )
    doc.update(extra)
    return doc


def test_build_closure_rejects_invalid_main_sha(tmp_path):
    closure = _closure(merge_commit_sha="nope", verified_main_sha="nope")
    with pytest.raises(ValueError, match="invalid verified_main_sha"):
        mod.build(_data(closure=closure), tmp_path)


def test_build_closure_rejects_unchanged_main(tmp_path):
    closure = _closure(merge_commit_sha=BASE, verified_main_sha=BASE)
    with pytest.raises(ValueError, match="unchanged main is not a closure"):
        mod.build(_data(closure=closure), tmp_path)


def test_build_closure_rejects_non_repaired_root(tmp_path):
    closure = _closure(individually_verified_root_ids=["R3"])
    with pytest.raises(ValueError, match="closed root lacks repaired status"):
        mod.build(_data(closure=closure), tmp_path)


def test_build_does_not_mutate_input(tmp_path):
    data = _data()
    snapshot = copy.deepcopy(data)
    mod.build(data, tmp_path)
    assert data == snapshot


# --- main -----------------------------------------------------------------


def test_main_writes_reports_and_prints_summary(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(_data()), encoding="utf-8")
    out = tmp_path / "out" / "nested"
    argv = [
        "mip_wave_pulse",
        "--input",
        str(source),
        "--artifact-root",
        str(tmp_path),
        "--output-dir",
        str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    pulse = json.loads((out / "mip_wave_pulse.json").read_text())
    backlog = json.loads((out / "mip_backlog_delta.json").read_text())
    assert pulse["wave_id"] == "W5"
    assert backlog["schema"] == "abacus.mip.backlog-delta.v1"
    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "wave_id": "W5",
        "coverage": "UNKNOWN",
        "verified_closed_roots": 0,
        "disposition": "MEASURED_NOT_MERGE_AUTHORIZED",
    }


def test_main_requires_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mip_wave_pulse"])
    with pytest.raises(SystemExit) as info:
        mod.main()
    assert info.value.code == 2
