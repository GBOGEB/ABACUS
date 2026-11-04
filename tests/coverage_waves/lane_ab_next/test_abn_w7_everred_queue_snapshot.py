"""Gap tests for scripts/everred_queue_snapshot.py (bad run id, main)."""

import hashlib
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/everred_queue_snapshot.py", name="abn_w7_everred_queue")


@pytest.mark.parametrize("run_id", [None, 0, -3, "7", True])
def test_normalize_rejects_non_positive_numeric_run_id(run_id):
    queued = {"workflow_runs": [{"id": run_id}], "total_count": 1}
    running = {"workflow_runs": [], "total_count": 0}
    with pytest.raises(ValueError, match="positive numeric run ID"):
        mod.normalize(queued, running)


def test_main_writes_snapshot_and_prints_digest(tmp_path, monkeypatch, capsys):
    queued = {
        "workflow_runs": [{"id": 5, "name": "ci", "created_at": "2026-01-02"}],
        "total_count": 3,
    }
    running = {"workflow_runs": [{"id": 9, "event": "push"}], "total_count": 1}
    q = tmp_path / "q.json"
    r = tmp_path / "r.json"
    out = tmp_path / "snap.json"
    q.write_text(json.dumps(queued), encoding="utf-8")
    r.write_text(json.dumps(running), encoding="utf-8")
    argv = ["e", "--queued", str(q), "--running", str(r), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    raw = out.read_bytes().replace(b"\r\n", b"\n")
    digest = capsys.readouterr().out.strip()
    assert digest == hashlib.sha256(raw).hexdigest()
    snap = json.loads(raw)
    assert snap["partial"] is True
    assert snap["counts"]["queued"] == {"api_total": 3, "fetched": 1, "partial": True}
    pairs = [(row["id"], row["status"]) for row in snap["runs"]]
    assert pairs == [(9, "in_progress"), (5, "queued")]
    assert snap["runs"][0]["name"] == "UNKNOWN"
    assert snap["runs"][1]["event"] == "UNKNOWN"
