"""Gap tests for scripts/dab_proposal_queue.py (batching, lanes, CLI)."""

import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/dab_proposal_queue.py", name="abn_w7_dab_proposal_queue")

SHA = "d" * 40

POLICY = dict(
    protected_holds=dict(F821=dict(disposition="HOLD", value_lane="P0")),
    batch_policy=dict(
        LOW_MECHANICAL=dict(families=["W291"], max_findings=2, max_files=5),
        MEDIUM=dict(max_findings=10, max_files=1),
    ),
    value_priority=dict(
        lanes=dict(
            P1_CORRECTNESS=dict(families=["F841"], rank=1),
            P3_STYLE=dict(rank=3, promotion_mode="BATCHED", dedicated_pr_default=False),
        ),
    ),
    gates=dict(
        G1=dict(static_total_exclusive_max=10),
        G2=dict(static_total_exclusive_max=5),
        G3=dict(static_total_exclusive_max=1),
    ),
    governance=dict(authority_transfer=False),
)


def test_load_json_rejects_non_object(tmp_path):
    path = tmp_path / "x.json"
    path.write_text('"text"', encoding="utf-8")
    with pytest.raises(ValueError, match="expected JSON object"):
        mod.load_json(path)


def test_git_head_strips_output(monkeypatch):
    calls = []

    def fake(cmd, text):
        calls.append(cmd)
        return SHA + "\n"

    monkeypatch.setattr(mod.subprocess, "check_output", fake)
    assert mod.git_head() == SHA
    assert calls == [["git", "rev-parse", "HEAD"]]


def test_value_lane_style_promotion_for_pycodestyle():
    lane = mod.value_lane_for("E302", POLICY)
    assert lane["name"] == "P3_STYLE"
    assert lane["promotion_mode"] == "BATCHED"


def test_value_lane_default_without_style_lane():
    policy = dict(value_priority=dict(lanes={}, default_lane="P9"))
    assert mod.value_lane_for("E302", policy) == {"name": "P9"}


def test_build_queue_batches_by_findings_and_files():
    raw = "\n".join(
        [
            "a.py:1:1: W291 trailing whitespace",
            "a.py:2:1: W291 trailing whitespace",
            "a.py:3:1: W291 trailing whitespace",
            "a.py:5:1: F841 local variable unused",
            "b.py:5:1: F841 local variable unused",
            "a.py:9:1: F821 undefined name",
            "not a finding line",
        ]
    )
    census = dict(total=6, all_families=dict(W291=3, F841=2, F821=1))
    queue = mod.build_queue(census, raw, POLICY, SHA)
    families = [(p["family"], p["scope"]["finding_count"]) for p in queue["proposals"]]
    # rank 1 F841 (MEDIUM, max_files=1 splits per file), then rank 3 W291
    # (LOW_MECHANICAL, max_findings=2 splits 3 findings into 2+1).
    assert families == [("F841", 1), ("F841", 1), ("W291", 2), ("W291", 1)]
    ids = [p["proposal_id"] for p in queue["proposals"]]
    assert ids[0].endswith("-F841-001") and ids[-1].endswith("-W291-004")
    assert queue["value_policy"]["style_findings_in_queue"] == 3
    assert queue["protected_holds"]["F821"]["count"] == 1
    gates = queue["measurement"]["gate_status"]
    assert gates["G1"]["status"] == "STATIC_PASS_COMPANION_PENDING"
    assert gates["G2"]["status"] == "OPEN"
    style = queue["proposals"][-1]
    assert style["coverage_growth"]["applicability"] == "NOT_APPLICABLE_MECHANICAL_ONLY"
    assert style["value_priority"]["dedicated_pr_default"] is False


def _files(tmp_path, census):
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(census), encoding="utf-8")
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(POLICY), encoding="utf-8")
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    text_path = tmp_path / "flake8.txt"
    text_path.write_bytes(b"a.py:5:1: F841 local variable unused\n")
    return [
        "--census",
        str(census_path),
        "--text",
        str(text_path),
        "--policy",
        str(policy_path),
        "--contract",
        str(contract_path),
    ]


def test_main_writes_queue_using_census_sha(monkeypatch, tmp_path, capsys):
    args = _files(tmp_path, dict(total=1, exact_sha=SHA, all_families=dict(F841=1)))
    out = tmp_path / "out" / "queue.json"
    monkeypatch.setattr(sys, "argv", ["dab", *args, "--out", str(out)])
    assert mod.main() == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["source_sha"] == SHA
    assert len(written["proposals"]) == 1
    assert json.loads(capsys.readouterr().out) == written


def test_main_rejects_short_sha(monkeypatch, tmp_path):
    args = _files(tmp_path, dict(total=0))
    out = tmp_path / "queue.json"
    argv = ["dab", *args, "--source-sha", "abc123", "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit, match="exact 40-character SHA"):
        mod.main()
    assert not out.exists()


def test_main_falls_back_to_git_head(monkeypatch, tmp_path):
    args = _files(tmp_path, dict(total=1, all_families=dict(F841=1)))
    out = tmp_path / "queue.json"
    monkeypatch.setattr(mod, "git_head", lambda: "e" * 40)
    monkeypatch.setattr(sys, "argv", ["dab", *args, "--out", str(out)])
    assert mod.main() == 0
    assert json.loads(out.read_text(encoding="utf-8"))["source_sha"] == "e" * 40
