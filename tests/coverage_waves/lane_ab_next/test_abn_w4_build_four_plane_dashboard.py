"""Behaviour tests for tools/everred_v3/scripts/build_four_plane_dashboard.py.

The diagram directory is redirected to tmp_path through ``BASE`` so the real
dashboard and diagrams are never rewritten.
"""

import hashlib
import importlib.util
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/build_four_plane_dashboard.py"
SCRIPT = REPO_ROOT / REL
SCHEMA = "abacus.everred.four_plane.preflight.v1"
SHA = "a" * 40

mod = load(REL, name="abn_w4_build_four_plane_dashboard")


def _snapshot(observations=2, task_count=3, sha=SHA, schema=SCHEMA):
    tasks = [
        dict(id="T_ONE", plane="diagnostic", actor="ops", needs=[], state="HOLD"),
        dict(id="T_TWO", plane="runtime", actor="ops", needs=["T_ONE"], state="X"),
        dict(id="T_SIX", plane="evidence", actor="ops", needs=[], state="Y"),
    ]
    return {
        "schema": schema,
        "source_binding": {"source_sha": sha},
        "joined_census": {"observation_count": observations},
        "receipts": [{"note": "</script><b>x</b>"}, {"note": "plain"}],
        "dispatch_preview": {"tasks": tasks},
        "plan": {"task_count": task_count},
        "claims": {"admission": "HOLD"},
    }


def _write_snapshot(tmp_path, obj):
    path = tmp_path / "snap.json"
    path.write_bytes(json.dumps(obj).encode("utf-8"))
    return path


def _fake_base(tmp_path, monkeypatch):
    base = tmp_path / "base"
    diagrams = base / "diagrams"
    diagrams.mkdir(parents=True)
    (diagrams / "06_four_plane_execution.svg").write_bytes(
        b'<?xml version="1.0"?>\n<svg id="dag"><text>dag</text></svg>'
    )
    (diagrams / "07_four_plane_sipoc.svg").write_bytes(
        b'<!-- prolog --><svg id="sipoc"><text>sipoc</text></svg>'
    )
    monkeypatch.setattr(mod, "BASE", base)
    return base


def test_build_writes_dashboard_and_returns_digests(tmp_path, monkeypatch):
    _fake_base(tmp_path, monkeypatch)
    snap = _write_snapshot(tmp_path, _snapshot())
    target = tmp_path / "out" / "nested" / "dash.html"

    result = mod.build(snap, target)

    assert target.is_file()
    digest = hashlib.sha256(snap.read_bytes()).hexdigest()
    assert result["snapshot_sha256"] == digest
    assert result["html_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert result["observations"] == 2
    assert result["tasks"] == 3
    assert result["html"] == target.as_posix()

    page = target.read_text(encoding="utf-8")
    assert page.count(digest) == 2
    assert '<strong id="metricObservations">2</strong>' in page
    assert '<strong id="metricTasks">3</strong>' in page
    assert '<code id="sha">' + SHA + "</code>" in page
    # XML prologs / comments before <svg are stripped, diagrams kept in order.
    assert "<?xml" not in page
    assert "prolog" not in page
    assert page.index('<svg id="dag">') < page.index('<svg id="sipoc">')
    assert "<h3>Execution DAG</h3>" in page
    assert "<h3>SIPOC ownership and evidence flow</h3>" in page
    for marker in ("DIGEST", "COUNT", "HEAD_PLACEHOLDER", "ARTS"):
        assert marker not in page


def test_embedded_snapshot_is_escaped_and_round_trips(tmp_path, monkeypatch):
    _fake_base(tmp_path, monkeypatch)
    obj = _snapshot()
    snap = _write_snapshot(tmp_path, obj)
    target = tmp_path / "dash.html"
    mod.build(snap, target)
    page = target.read_text(encoding="utf-8")

    head = '<script type="application/json" id="embeddedSnapshot">'
    start = page.index(head) + len(head)
    embedded = page[start : page.index("</script>", start)]
    assert "<" not in embedded
    assert "\\u003c/script>" in embedded
    assert json.loads(embedded) == obj


def test_build_uses_repository_diagrams_by_default(tmp_path):
    snap = _write_snapshot(tmp_path, _snapshot())
    target = tmp_path / "real.html"
    result = mod.build(snap, target)
    page = target.read_text(encoding="utf-8")
    assert page.count('<article class="diagram">') == 2
    assert result["tasks"] == 3


@pytest.mark.parametrize(
    "obj, message",
    [
        (_snapshot(schema="other.schema"), "unknown preflight schema"),
        (_snapshot(sha="abc"), "missing source pin"),
        (_snapshot(observations=5), "dashboard source count mismatch"),
        (_snapshot(task_count=9), "dashboard source count mismatch"),
    ],
)
def test_build_rejects_invalid_snapshots(tmp_path, monkeypatch, obj, message):
    _fake_base(tmp_path, monkeypatch)
    snap = _write_snapshot(tmp_path, obj)
    target = tmp_path / "never.html"
    with pytest.raises(ValueError, match=message):
        mod.build(snap, target)
    assert not target.exists()


def test_main_prints_sorted_json_summary(tmp_path, monkeypatch, capsys):
    _fake_base(tmp_path, monkeypatch)
    snap = _write_snapshot(tmp_path, _snapshot())
    out = tmp_path / "cli.html"
    monkeypatch.setattr(
        sys, "argv", ["prog", "--snapshot", str(snap), "--output", str(out)]
    )
    mod.main()
    printed = capsys.readouterr().out.strip()
    data = json.loads(printed)
    assert data["observations"] == 2
    assert data["tasks"] == 3
    assert list(data) == sorted(data)
    assert out.is_file()


def test_script_entry_point_runs_main(tmp_path, monkeypatch, capsys):
    snap = _write_snapshot(tmp_path, _snapshot())
    out = tmp_path / "entry.html"
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--snapshot", str(snap), "--output", str(out)]
    )
    spec = importlib.util.spec_from_file_location("__main__", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads(capsys.readouterr().out)
    assert data["snapshot_sha256"] == hashlib.sha256(snap.read_bytes()).hexdigest()
    assert out.is_file()
