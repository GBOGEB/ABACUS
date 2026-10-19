"""P41-L6: source-executing, fail-closed floating-evidence join tests.

Tests are synthetic inputs to the actual production joiner. They do not claim
that a floating path is a runtime orphan or authorize pruning.
"""

import json
import sys

import pytest

from tools.triage import floating_evidence_join as join


SHA = "a" * 40


def _dab():
    return {"exact_sha": SHA, "rows": [
        {"path": "src/real.py", "covered_statements": 4, "statements": 10,
         "covered_branches": 2, "eligible_branches": 6},
    ]}


def _floating():
    return {"floating_buckets": {
        "suspects": {"paths": ["src/real.py", "src/unknown.py"]},
        "repeat": {"paths": ["src/unknown.py", "src/real.py"]},
    }}


def test_cli_writes_deterministic_real_join_result(tmp_path, monkeypatch):
    dab_path, floating_path = tmp_path / "dab.json", tmp_path / "floating.json"
    out = tmp_path / "census" / "joined.json"
    dab_path.write_text(json.dumps(_dab()), encoding="utf-8")
    floating_path.write_text(json.dumps(_floating()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "floating_evidence_join", "--dab", str(dab_path), "--floating",
        str(floating_path), "--source-sha", SHA, "--floating-sha", SHA,
        "--out", str(out),
    ])

    assert join.main() == 0
    first = out.read_bytes()
    assert join.main() == 0
    assert out.read_bytes() == first

    result = json.loads(first)
    assert result["candidate_paths"] == 2
    assert result["candidate_measured_overlap"] == 1
    assert result["candidate_unmeasured"] == 1
    assert [x["path"] for x in result["rows"]] == [
        "src/real.py", "src/unknown.py",
    ]
    measured, unknown = result["rows"]
    assert measured["statements_covered"] == 4
    assert measured["branches_eligible"] == 6
    assert unknown["statements_covered"] is None
    assert unknown["branches_eligible"] is None
    assert all(x["runtime_reachability"] == "UNKNOWN" for x in result["rows"])
    assert all(x["orphan"] is None for x in result["rows"])
    assert result["prune_authorized"] is False


def test_stale_sha_does_not_write_output(tmp_path, monkeypatch):
    dab_path, floating_path = tmp_path / "dab.json", tmp_path / "floating.json"
    out = tmp_path / "denied.json"
    dab_path.write_text(json.dumps(_dab()), encoding="utf-8")
    floating_path.write_text(json.dumps(_floating()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "floating_evidence_join", "--dab", str(dab_path), "--floating",
        str(floating_path), "--source-sha", "b" * 40,
        "--floating-sha", SHA, "--out", str(out),
    ])
    with pytest.raises(ValueError, match="DAB source SHA mismatch"):
        join.main()
    assert not out.exists()


def test_empty_inputs_are_not_invented_as_reachability():
    result = join.reconcile(
        {"exact_sha": SHA, "rows": []},
        {"floating_buckets": {"unobserved": {"paths": ["src/a.py"]}}},
        source_sha=SHA,
        floating_sha=SHA,
    )
    assert result["candidate_unmeasured"] == 1
    assert result["measured_paths"] == 0
    row = result["rows"][0]
    assert row["coverage_evidence"] == "UNKNOWN"
    assert row["runtime_reachability"] == "UNKNOWN"
    assert row["orphan"] is None
    assert row["prune_authorized"] is False
