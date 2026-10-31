"""Behaviour tests for tools/everred_v3/scripts/build_dashboard.py.

The script does all its work at import: it reads repository inputs under
``tools/everred_v3`` and overwrites ``dashboard/index.html``. To keep the
repository byte-identical and the test independent of data drift,
``Path.read_text``/``exists``/``write_text`` are patched for paths inside that
directory only during the import, and the bare sibling imports
``build_bd_queue`` and ``control`` are in-memory stubs. sys.path is restored.
"""

import contextlib
import io
import json
import pathlib
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/build_dashboard.py"
ROOT = REPO_ROOT / "tools" / "everred_v3"
SVG_NAMES = [
    "01_execution_dag",
    "02_sipoc",
    "03_causal_evidence",
    "04_preflight_gates",
    "05_native_control",
]
TEMPLATE = "<main>@@SNAPSHOT@@|@@SVGJSON@@|@@PULSES@@|@@ALERTS@@</main>"
SNAPSHOT = {"title": "Run </script> é", "n": 3}
HISTORY = [{"pulse": 1, "note": "</b>"}]
ALERTS = [{"id": "A1", "level": "RED"}]


def _inputs(with_alerts):
    files = {
        "data/snapshot.json": json.dumps(SNAPSHOT),
        "dashboard/template.html": TEMPLATE,
    }
    for name in SVG_NAMES:
        files["diagrams/" + name + ".svg"] = "<svg id='" + name + "'></svg>"
    if with_alerts:
        files["data/alerts.json"] = json.dumps({"alerts": ALERTS})
    return files


def _stubs():
    queue = types.ModuleType("build_bd_queue")
    queue.calls = []
    queue.main = lambda: queue.calls.append("regenerated")
    control = types.ModuleType("control")
    control.paths = []

    def read_history(path):
        control.paths.append(path)
        return list(HISTORY)

    control.read_history = read_history
    return queue, control


def _load_dashboard(name, with_alerts):
    files = _inputs(with_alerts)
    written = {}
    queue, control = _stubs()
    real_read = pathlib.Path.read_text
    real_write = pathlib.Path.write_text
    real_exists = pathlib.Path.exists

    def relative(path):
        try:
            return path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return None

    def fake_read(self, *args, **kwargs):
        key = relative(self)
        if key is None:
            return real_read(self, *args, **kwargs)
        return files[key]

    def fake_exists(self, *args, **kwargs):
        key = relative(self)
        if key is None:
            return real_exists(self, *args, **kwargs)
        return key in files

    def fake_write(self, data, *args, **kwargs):
        key = relative(self)
        if key is None:
            return real_write(self, data, *args, **kwargs)
        written[key] = data
        return len(data)

    saved_path = list(sys.path)
    buffer = io.StringIO()
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(pathlib.Path, "read_text", fake_read)
            patch.setattr(pathlib.Path, "exists", fake_exists)
            patch.setattr(pathlib.Path, "write_text", fake_write)
            with contextlib.redirect_stdout(buffer):
                module = load(
                    REL,
                    name=name,
                    deps={"build_bd_queue": queue, "control": control},
                )
    finally:
        sys.path[:] = saved_path
    return module, written, queue, control, buffer.getvalue()


mod, WRITTEN, QUEUE, CONTROL, OUTPUT = _load_dashboard("abn_w5_build_dashboard", True)


def _payload(html):
    body = html[len("<main>") : -len("</main>")]
    return body.split("|")


def test_writes_only_dashboard_index():
    assert list(WRITTEN) == ["dashboard/index.html"]


def test_placeholders_replaced_with_embedded_json():
    html = WRITTEN["dashboard/index.html"]
    assert "@@" not in html
    snapshot, svgs, pulses, alerts = _payload(html)
    assert "</script>" not in snapshot
    assert "<\\/script>" in snapshot
    assert "é" in snapshot
    assert json.loads(snapshot.replace("<\\/", "</")) == SNAPSHOT
    assert json.loads(svgs.replace("<\\/", "</")) == [
        "<svg id='" + name + "'></svg>" for name in SVG_NAMES
    ]
    assert json.loads(pulses.replace("<\\/", "</")) == HISTORY
    assert json.loads(alerts) == ALERTS


def test_history_read_from_kpi_ledger_and_queue_regenerated():
    assert len(CONTROL.paths) == 1
    assert CONTROL.paths[0].name == "kpi_history.jsonl"
    assert CONTROL.paths[0].parent.name == "data"
    assert QUEUE.calls == ["regenerated"]


def test_prints_write_summary():
    html = WRITTEN["dashboard/index.html"]
    line = OUTPUT.strip()
    assert line.startswith("Wrote ")
    assert line.endswith(" " + str(len(html)) + " chars")
    assert "index.html" in line


def test_embedded_escapes_closing_tags():
    assert mod.embedded("</script>") == '"<\\/script>"'
    assert mod.embedded({"k": "ü"}) == '{"k": "ü"}'
    assert mod.embedded([1, None]) == "[1, null]"


def test_missing_alerts_file_embeds_empty_list():
    _, written, queue, _, output = _load_dashboard("abn_w5_build_dash_noalert", False)
    html = written["dashboard/index.html"]
    assert _payload(html)[3] == "[]"
    assert queue.calls == ["regenerated"]
    assert output.startswith("Wrote ")
