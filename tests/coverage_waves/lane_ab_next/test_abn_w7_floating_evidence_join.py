"""Gap tests for tools/triage/floating_evidence_join.py (CLI main)."""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/triage/floating_evidence_join.py", name="abn_w7_floating_join")

SHA = "b" * 40


def _inputs(tmp_path):
    dab = dict(
        exact_sha=SHA,
        rows=[
            dict(
                path="src/a.py",
                covered_statements=4,
                statements=10,
                covered_branches=1,
                eligible_branches=2,
            )
        ],
    )
    floating = dict(floating_buckets=dict(x=dict(paths=["src/a.py", "src/b.py"])))
    dab_path = tmp_path / "dab.json"
    floating_path = tmp_path / "floating.json"
    dab_path.write_text(json.dumps(dab), encoding="utf-8")
    floating_path.write_text(json.dumps(floating), encoding="utf-8")
    return dab_path, floating_path


def test_main_writes_joined_result(monkeypatch, tmp_path):
    dab_path, floating_path = _inputs(tmp_path)
    out = tmp_path / "out" / "deep" / "join.json"
    argv = [
        "floating_evidence_join.py",
        "--dab",
        str(dab_path),
        "--floating",
        str(floating_path),
        "--source-sha",
        SHA,
        "--floating-sha",
        SHA,
        "--out",
        str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 0
    result = json.loads(out.read_text())
    assert result["candidate_paths"] == 2
    assert result["candidate_measured_overlap"] == 1
    assert result["candidate_unmeasured"] == 1
    rows = {r["path"]: r for r in result["rows"]}
    assert rows["src/b.py"]["coverage_evidence"] == "UNKNOWN"
    assert rows["src/a.py"]["statements_covered"] == 4


def test_main_rejects_floating_sha_mismatch(monkeypatch, tmp_path):
    dab_path, floating_path = _inputs(tmp_path)
    out = tmp_path / "never.json"
    argv = [
        "floating_evidence_join.py",
        "--dab",
        str(dab_path),
        "--floating",
        str(floating_path),
        "--source-sha",
        SHA,
        "--floating-sha",
        "c" * 40,
        "--out",
        str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="floating source SHA mismatch"):
        mod.main()
    assert not out.exists()
