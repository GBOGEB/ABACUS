"""Behaviour tests for tools/everred_v3/scripts/build_mission_cycle.py.

``mission_cycle.project`` is replaced by a deterministic stub so the tests
exercise only the script's fail-closed source checks, template injection and
CLI render / --check behaviour. All files live under tmp_path.
"""

import importlib.util
import json
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/build_mission_cycle.py"
SCRIPT = REPO_ROOT / REL
MARKER = "@@GUIDANCE_JSON@@"
TEMPLATE = "<html><script>const g=" + MARKER + ";</script></html>"


def _project(data):
    return {
        "families": len(data["families"]),
        "note": "</script>é",
        "stages": ["Mission", "Wave"],
    }


def _stub():
    stub = types.ModuleType("mission_cycle")
    stub.project = _project
    return stub


DEPS = {"mission_cycle": _stub()}
_saved_path = list(sys.path)
mod = load(REL, name="abn_w4_build_mission_cycle", deps=DEPS)
sys.path[:] = _saved_path


def _data(**over):
    data = {
        "schema": "abacus.everred.bd-queue.observation.v1",
        "mode": "FROZEN_HISTORICAL_EVIDENCE_NOT_LIVE",
        "disposition": "ADMISSION_HOLD",
        "families": [{"id": 1}, {"id": 2}],
    }
    data.update(over)
    return data


def test_build_injects_compact_escaped_guidance():
    out = mod.build(_data(), TEMPLATE)
    assert MARKER not in out
    prefix = "<html><script>const g="
    assert out.startswith(prefix)
    payload = out[len(prefix) : out.index(";</script></html>")]
    assert "</" not in payload
    assert "é" in payload
    assert payload.startswith('{"families":2,"note":')
    assert json.loads(payload) == _project(_data())


@pytest.mark.parametrize(
    "over, message",
    [
        (dict(schema="other"), "wrong source evidence schema"),
        (dict(mode="LIVE"), "unqualified source status"),
        (dict(disposition="ADMIT"), "admission authority cannot be inherited"),
    ],
)
def test_build_rejects_unqualified_sources(over, message):
    with pytest.raises(ValueError, match=message):
        mod.build(_data(**over), TEMPLATE)


@pytest.mark.parametrize("template", ["<html></html>", MARKER + MARKER])
def test_build_requires_exactly_one_marker(template):
    with pytest.raises(ValueError, match="missing or duplicate data marker"):
        mod.build(_data(), template)


def _files(tmp_path):
    source = tmp_path / "bd.json"
    source.write_text(json.dumps(_data()), encoding="utf-8")
    template = tmp_path / "tpl.html"
    template.write_text(TEMPLATE, encoding="utf-8")
    output = tmp_path / "out" / "mission_cycle.html"
    args = [
        "--source",
        str(source),
        "--template",
        str(template),
        "--output",
        str(output),
    ]
    return output, args


def test_main_renders_then_check_passes(tmp_path, capsys):
    output, args = _files(tmp_path)
    assert mod.main(args) == 0
    assert "Rendered" in capsys.readouterr().out
    expected = mod.build(_data(), TEMPLATE)
    assert output.read_text(encoding="utf-8") == expected
    assert mod.main(args + ["--check"]) == 0


def test_main_check_fails_when_output_missing(tmp_path):
    output, args = _files(tmp_path)
    with pytest.raises(SystemExit, match="stale Mission Cycle HTML"):
        mod.main(args + ["--check"])
    assert not output.exists()


def test_main_check_fails_when_output_stale(tmp_path):
    output, args = _files(tmp_path)
    output.parent.mkdir(parents=True)
    output.write_text("old", encoding="utf-8")
    with pytest.raises(SystemExit, match="stale Mission Cycle HTML"):
        mod.main(args + ["--check"])
    assert output.read_text(encoding="utf-8") == "old"


def test_script_entry_point_exits_with_main_status(tmp_path, monkeypatch, capsys):
    output, args = _files(tmp_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)] + args)
    spec = importlib.util.spec_from_file_location("__main__", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    saved = sys.modules.get("mission_cycle")
    sys.modules.update(DEPS)
    try:
        with pytest.raises(SystemExit) as exc:
            spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_path
        if saved is None:
            sys.modules.pop("mission_cycle", None)
        else:
            sys.modules["mission_cycle"] = saved
    assert exc.value.code == 0
    assert output.is_file()
    assert "Rendered" in capsys.readouterr().out
