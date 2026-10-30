"""Lane A wave 1: architecture/mesh scripts and the temporal H2 DOW challenge."""

import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_a._load import REPO, load

EMIT = REPO / "architecture" / "mesh" / "emit_mesh_status.py"
SELECT = REPO / "architecture" / "mesh" / "select_mesh_blocker.py"
H2 = "governance/qps_triage/temporal_h2_dow_challenge.py"
SHA = "a" * 40


def test_emit_mesh_status_writes_all_dimensions(tmp_path, monkeypatch, capsys):
    calls = []

    def fake_check_output(cmd, text):
        calls.append(cmd)
        return SHA + "\n"

    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    monkeypatch.chdir(tmp_path)
    ns = runpy.run_path(str(EMIT))
    assert calls == [["git", "rev-parse", "HEAD"]]
    out = json.loads((tmp_path / "mesh-status.json").read_text(encoding="utf-8"))
    assert out["source_sha"] == SHA
    assert set(out["dimensions"]) == set(ns["K"])
    assert out["dimensions"]["BG"]["state"] == "BLOCKED"
    assert out["dimensions"]["RR"]["source_ref"] == SHA
    assert out["dimensions"]["KR"] == {
        k: out["dimensions"]["KR"][k]
        for k in ("state", "confidence", "evidence_class", "observed_at", "source_ref")
    }
    assert out["dimensions"]["KR"]["state"] == "UNKNOWN"
    assert "detail" in out["dimensions"]["CG"]
    assert "PASS emitted 13 dimensions" in capsys.readouterr().out
    plain = ns["A"]()
    assert "detail" not in plain and plain["source_ref"] == "self"


def _vector(repo, bg_state, atom):
    return {
        "repo": repo,
        "source_sha": SHA,
        "freshness_timestamp": "2026-10-27T00:00:00+00:00",
        "dimensions": {"BG": {"state": bg_state}},
        "blocking_atom": atom,
        "next_action": "act-" + repo,
    }


def _run_select(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["select_mesh_blocker.py", *argv])
    runpy.run_path(str(SELECT), run_name="__main__")


def test_select_mesh_blocker_picks_highest_rank(tmp_path, monkeypatch, capsys):
    paths = []
    for repo, state in (("r/a", "GREEN"), ("r/b", "RED"), ("r/c", "WEIRD")):
        p = tmp_path / (repo.replace("/", "_") + ".json")
        p.write_text(json.dumps(_vector(repo, state, "atom-" + repo)), encoding="utf-8")
        paths.append(str(p))
    out = tmp_path / "rollup.json"
    _run_select(monkeypatch, [*paths, "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["selected_repo"] == "r/b"
    assert data["selected_blocking_atom"] == "atom-r/b"
    assert data["next_CG_action"] == "act-r/b"
    assert data["repo_count"] == 3
    assert data["commit_or_pr_noise_read"] is False
    assert [r["repo"] for r in data["repos"]] == ["r/a", "r/b", "r/c"]
    assert "PASS contract-only selection r/b" in capsys.readouterr().out


def test_select_mesh_blocker_unknown_state_ranks_as_unknown(tmp_path, monkeypatch):
    paths = []
    for repo, state in (("r/a", "GREEN"), ("r/b", "NA"), ("r/c", "MYSTERY")):
        p = tmp_path / (repo.replace("/", "_") + ".json")
        p.write_text(json.dumps(_vector(repo, state, None)), encoding="utf-8")
        paths.append(str(p))
    out = tmp_path / "o.json"
    _run_select(monkeypatch, [*paths, "--out", str(out)])
    assert json.loads(out.read_text(encoding="utf-8"))["selected_repo"] == "r/c"


def test_select_mesh_blocker_needs_three_vectors(tmp_path, monkeypatch):
    p = tmp_path / "one.json"
    p.write_text(json.dumps(_vector("r/a", "RED", None)), encoding="utf-8")
    with pytest.raises(SystemExit, match="need >=3"):
        _run_select(monkeypatch, [str(p), str(p)])


@pytest.fixture(scope="module")
def h2():
    return load(H2)


def _window(wid, created, direction, pairs=2, strength=0.75, **over):
    row = {
        "window_id": str(wid),
        "created_at": created,
        "event": "schedule",
        "workflow_path": ".github/workflows/h2.yml",
        "source_kind": "NATIVE",
        "task_classes": {
            "build": {
                "direction": direction,
                "observed_pairs": pairs,
                "single_normalized_strength": strength,
            }
        },
    }
    row.update(over)
    return row


def _receipt(windows):
    return {
        "scheduled_control_frontier": {
            "eligibility_event": "schedule",
            "eligibility_workflow_path": ".github/workflows/h2.yml",
        },
        "windows": windows,
        "temporal_surveillance": {"schema": "mc.h2.v1"},
        "policies": {"build": {}},
    }


def test_genuine_windows_filters_and_sorts(h2):
    receipt = _receipt(
        [
            _window(10, "2026-10-02T00:00:00Z", "A"),
            _window(2, "2026-10-01T00:00:00Z", "A"),
            _window(9, "2026-10-01T00:00:00Z", "B"),
            _window(3, "2026-10-01T00:00:00Z", "A", event="push"),
            _window(4, "2026-10-01T00:00:00Z", "A", workflow_path="x.yml"),
            _window(5, "2026-10-01T00:00:00Z", "A", source_kind="SYNTHETIC_TEST"),
        ]
    )
    rows = h2.genuine_windows(receipt)
    assert [r["window_id"] for r in rows] == ["2", "9", "10"]


def test_genuine_span_seconds(h2):
    assert h2.genuine_span_seconds([]) == 0.0
    assert h2.genuine_span_seconds([_window(1, "2026-10-01T00:00:00Z", "A")]) == 0.0
    rows = [
        _window(1, "2026-10-01T00:00:00Z", "A"),
        _window(2, "2026-10-01T01:00:00+00:00", "A"),
    ]
    assert h2.genuine_span_seconds(rows) == 3600.0
    assert h2.genuine_span_seconds(list(reversed(rows))) == 0.0


def test_recompute_counts_flips_and_strength(h2):
    rows = [
        _window(1, "t1", "UP", pairs=2, strength=0.8),
        _window(2, "t2", "INDETERMINATE", pairs=0, strength=0.5),
        _window(3, "t3", "DOWN", pairs=2, strength=0.2),
        _window(4, "t4", "UP", pairs=4, strength=0.9),
    ]
    out = h2.recompute(rows, "build")
    assert out["genuine_scheduled_windows"] == 4
    assert out["directional_windows"] == 3
    assert out["direction_flip_count"] == 2
    assert out["indeterminate_window_fraction"] == 0.25
    assert out["dominant_direction"] == "UP"
    assert out["pooled_winner_strength"] == pytest.approx(0.7)
    assert out["authority_transfer"] is False


def test_recompute_empty_and_indeterminate_only(h2):
    empty = h2.recompute([], "build")
    assert empty["indeterminate_window_fraction"] is None
    assert empty["dominant_direction"] == "INDETERMINATE"
    assert empty["pooled_winner_strength"] == 0.5
    rows = [_window(1, "t", "INDETERMINATE", pairs=0)]
    out = h2.recompute(rows, "build")
    assert out["indeterminate_window_fraction"] == 1.0
    assert out["direction_flip_count"] == 0


def test_recompute_low_strength_mirrors_to_winner(h2):
    out = h2.recompute([_window(1, "t", "DOWN", pairs=1, strength=0.1)], "build")
    assert out["pooled_winner_strength"] == pytest.approx(0.9)


def test_main_writes_challenge(h2, tmp_path, monkeypatch):
    receipt = _receipt(
        [
            _window(1, "2026-10-01T00:00:00Z", "UP"),
            _window(2, "2026-10-01T00:10:00Z", "UP"),
        ]
    )
    src = tmp_path / "receipt.json"
    src.write_text(json.dumps(receipt), encoding="utf-8")
    dst = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["h2", "--receipt", str(src), "--out", str(dst)])
    h2.main()
    result = json.loads(dst.read_text(encoding="utf-8"))
    assert result["origin_schema"] == "mc.h2.v1"
    assert result["genuine_scheduled_windows"] == 2
    assert result["genuine_temporal_span_seconds"] == 600.0
    assert result["classes"]["build"]["dominant_direction"] == "UP"
    assert result["disposition"] == "CHALLENGE_RECOMPUTED"
    assert result["control_authority"] is False
