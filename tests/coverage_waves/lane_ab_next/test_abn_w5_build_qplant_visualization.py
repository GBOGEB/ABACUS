"""Behaviour tests for build_qplant_visualization.py.

The real QPLANT content and renderers drive one end-to-end build into
``tmp_path``; focused tests swap the renderers for recording fakes and point
``CONTENT_DIR`` at a temporary tree to reach the error and branch paths.
"""

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("build_qplant_visualization.py", name="abn_build_qplant_visualization")


class _FakeFlow:
    calls = []

    def render(self, payload, lineage=None):
        _FakeFlow.calls.append((payload, lineage))
        return "<svg id='flow'></svg>"


class _FakeMath:
    calls = []

    def render(self, payload, lineage=None):
        _FakeMath.calls.append((payload, lineage))
        return "<math>" + payload["name"] + "</math>"


@pytest.fixture
def fakes(monkeypatch):
    _FakeFlow.calls = []
    _FakeMath.calls = []
    monkeypatch.setattr(mod, "ProcessFlowRenderer", _FakeFlow)
    monkeypatch.setattr(mod, "MathMLRenderer", _FakeMath)


def _docs():
    flow = dict(
        visualization=dict(title="Flow <A>"),
        process_flow=dict(nodes=[dict(id="n1")], edges=[dict(src="n1")]),
        lineage=dict(wave="W1"),
    )
    thermo = dict(
        visualization=dict(title="Thermo"),
        equations=[
            dict(name="Carnot & co", expression=dict(type="row"), display="a<b"),
            dict(name="NoDisplay", expression=dict(type="row"), display=3),
        ],
    )
    life = dict(
        visualization=dict(title="Life"),
        timeline=dict(stages=[dict(id="S1", label="Design & build")]),
    )
    util = dict(
        visualization=dict(title="Utils"),
        utilities=[dict(name="Water", capacity=1300, unit="kW")],
    )
    return flow, thermo, life, util


def test_load_yaml_returns_mapping(tmp_path):
    path = tmp_path / "a.yaml"
    path.write_bytes(b"k: 1\n")
    assert mod._load_yaml(path) == {"k": 1}


def test_load_yaml_rejects_non_mapping(tmp_path):
    path = tmp_path / "a.yaml"
    path.write_bytes(b"- 1\n- 2\n")
    with pytest.raises(ValueError, match="must load to a mapping"):
        mod._load_yaml(path)


def test_render_process_flow_builds_renderer_input(fakes):
    flow = _docs()[0]
    assert mod._render_process_flow(flow) == "<svg id='flow'></svg>"
    payload, lineage = _FakeFlow.calls[0]
    assert payload == {
        "type": "process_flow",
        "title": "Flow <A>",
        "nodes": [dict(id="n1")],
        "edges": [dict(src="n1")],
    }
    assert lineage == dict(wave="W1")


def test_render_thermodynamics_display_branches(fakes):
    out = mod._render_thermodynamics(_docs()[1])
    assert out.count("<article>") == 2
    assert '<p class="equation-display">a&lt;b</p>' in out
    assert "<h3>Carnot &amp; co</h3>" in out
    # Non-string display is dropped entirely.
    second = out.split("<article>")[2]
    assert "equation-display" not in second
    assert "<math>NoDisplay</math>" in second
    assert [c[1] for c in _FakeMath.calls] == [None, None]


def test_render_lifecycle_and_utilities_escape():
    life = mod._render_lifecycle(_docs()[2])
    assert life == (
        '<ol class="lifecycle-list"><li><strong>S1</strong>'
        "<span>Design &amp; build</span></li></ol>"
    )
    util = mod._render_utilities(_docs()[3])
    assert "<td>Water</td><td>1300</td><td>kW</td>" in util
    assert util.startswith("<table><thead>")


def test_render_html_assembles_sections(fakes):
    flow, thermo, life, util = _docs()
    html = mod._render_html(flow, thermo, life, util)
    assert html.startswith("<!DOCTYPE html>")
    assert "<h2>Flow &lt;A&gt;</h2>" in html
    for label in ("Process Flow", "Thermodynamics", "Lifecycle Timeline", "Utilities"):
        assert 'aria-label="' + label + '"' in html
    assert "<svg id='flow'></svg>" in html


def test_build_writes_custom_output_from_content_dir(fakes, tmp_path, monkeypatch):
    content = tmp_path / "content"
    content.mkdir()
    names = ("process_flow", "thermodynamics", "lifecycle", "utilities")
    for name, doc in zip(names, _docs()):
        (content / (name + ".yaml")).write_text(yaml.safe_dump(doc), encoding="utf-8")
    monkeypatch.setattr(mod, "CONTENT_DIR", content)
    target = tmp_path / "out" / "deep" / "page.html"
    assert mod.build_qplant_visualization(target) == target
    assert "<h2>Utils</h2>" in target.read_text(encoding="utf-8")


def test_main_uses_default_output_with_real_content(tmp_path, monkeypatch, capsys):
    default = tmp_path / "dist" / "qplant_visualization.html"
    monkeypatch.setattr(mod, "DEFAULT_OUTPUT_PATH", default)
    assert mod.main() == 0
    assert "Generated: " in capsys.readouterr().out
    html = default.read_text(encoding="utf-8")
    assert "QPLANT Thermodynamics" in html
    assert "<math" in html and "<svg" in html
    assert "Cooling Water (PCW)" in html


def test_missing_content_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CONTENT_DIR", tmp_path / "absent")
    with pytest.raises(FileNotFoundError):
        mod.build_qplant_visualization(tmp_path / "x.html")
