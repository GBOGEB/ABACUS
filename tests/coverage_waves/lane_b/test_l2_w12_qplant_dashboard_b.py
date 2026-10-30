"""Lane-B wave 12: qplant handover dashboard builders and plot factory.

Covers build_all, build_dashboard, build_dense_slides and plotting/plot_factory.
Every output path is redirected to tmp_path. plotly is not a CI dependency, so
plot_factory runs against recording stubs injected through ``deps``.
"""

import json
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

from ._l2_loader import load

SRC = "qplant/handover_dashboard/src/"

# --------------------------------------------------------------------------
# build_all
# --------------------------------------------------------------------------

SUMMARY = {
    "single_valve_1e8_300k_1bar_g_year": 0.0506,
    "baseline_total_kg_year": 1.234,
    "rtm048_cap_kg_year": 65.2,
}

_handover_calls = []


def _fake_generate_dashboard():
    return dict(SUMMARY)


def _fake_build_handover(summary):
    _handover_calls.append(summary)


_gd_stub = types.ModuleType("generate_dashboard")
_gd_stub.generate_dashboard = _fake_generate_dashboard
_bh_stub = types.ModuleType("build_handover")
_bh_stub.build_handover = _fake_build_handover
manifest = load(SRC + "manifest.py")
ba = load(
    SRC + "build_all.py",
    deps={
        "generate_dashboard": _gd_stub,
        "build_handover": _bh_stub,
        "manifest": manifest,
    },
)


@pytest.fixture
def ba_root(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    docs = root / "docs"
    outputs = root / "outputs"
    monkeypatch.setattr(ba, "ROOT", root)
    monkeypatch.setattr(ba, "DOCS", docs)
    monkeypatch.setattr(ba, "ASSETS", root / "assets")
    monkeypatch.setattr(ba, "DOCS_ASSETS", docs / "assets")
    monkeypatch.setattr(ba, "OUTPUTS", outputs)
    monkeypatch.setattr(ba, "MANIFESTS", outputs / "manifests")
    (root / "assets").mkdir(parents=True)
    (root / "assets" / "style.css").write_text("body{}", encoding="utf-8")
    (root / "assets" / "triage.js").write_text("// js", encoding="utf-8")
    (root / "source").mkdir()
    (root / "source" / "handover.md").write_text("# H", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "x.pyc").write_bytes(b"\0")
    _handover_calls.clear()
    return root


def test_build_error_log_formats_summary(ba_root):
    ba._build_error_log(SUMMARY)
    text = (ba_root / "ERROR_LOG.md").read_text(encoding="utf-8")
    assert "1e-8 mbar·L/s @300K,1bar: 0.050600 g/year" in text
    assert "Baseline 410-valve scenario: 1.234 kg/year" in text
    assert "(1 Nm³/day): 65.20 kg/year" in text
    assert "CONTRACTUAL_ALIGNMENT_FACTOR=1000" in text


def test_readme_changelog_and_classifications(ba_root):
    ba._build_readme()
    ba._build_changelog()
    assert "python src/build_all.py" in (ba_root / "README.md").read_text(
        encoding="utf-8"
    )
    assert (
        (ba_root / "CHANGELOG.md")
        .read_text(encoding="utf-8")
        .startswith("# CHANGELOG\n\n## 2.0.0")
    )
    cls = ba._collect_classifications()
    assert len(cls) == 6
    assert cls["docs/handover.pdf"]["purpose"] == "formal export"


def test_copy_assets(ba_root):
    ba._copy_assets()
    assert (ba_root / "docs" / "assets" / "style.css").read_text(
        encoding="utf-8"
    ) == "body{}"
    assert (ba_root / "docs" / "assets" / "triage.js").exists()


def test_run_builds_tree_and_manifest(ba_root):
    stale = ba_root / "docs" / "stale.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")

    ba.run()

    assert not stale.exists()
    assert _handover_calls == [SUMMARY]
    assert (ba_root / "docs" / "source" / "handover.md").read_text(
        encoding="utf-8"
    ) == "# H"
    assert not (ba_root / "docs" / "source" / "assumptions.md").exists()
    assert (ba_root / "docs" / "handover_link.txt").exists()
    data = json.loads((ba_root / "OUTPUT_MANIFEST.json").read_text(encoding="utf-8"))
    paths = {Path(rec["path"]).as_posix() for rec in data["files"]}
    assert "README.md" in paths
    assert "docs/assets/style.css" in paths
    assert not any(p.startswith(".git") or "__pycache__" in p for p in paths)
    assert data["builder_version"] == "2.0.0"
    assert data["file_count"] == len(paths)
    latest = ba_root / "outputs" / "manifests" / "latest_manifest.json"
    assert json.loads(latest.read_text(encoding="utf-8")) == data


def test_run_is_rerunnable_when_docs_exist(ba_root):
    ba.run()
    ba.run()
    assert len(_handover_calls) == 2
    assert (ba_root / "docs" / "handover_link.txt").read_text(
        encoding="utf-8"
    ) == "Open handover.html or handover.pdf in docs/.\n"


# --------------------------------------------------------------------------
# build_dashboard
# --------------------------------------------------------------------------

bd = load(SRC + "build_dashboard.py")


@pytest.fixture
def bd_docs(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    monkeypatch.setattr(bd, "DOCS", docs)
    monkeypatch.setattr(bd, "MANIFEST_PATH", docs / "manifest.json")
    monkeypatch.setattr(bd, "OUT_PATH", docs / "index.html")
    return docs


@pytest.mark.parametrize(
    "status, cls",
    [
        ("Verified (3/3)", "pill ok"),
        ("In progress", "pill progress"),
        ("Pending review", "pill pending"),
        ("Blocked", "pill pending"),
    ],
)
def test_status_pill(status, cls):
    assert bd._status_pill(status) == f'<span class="{cls}">{status}</span>'


def test_iso_now_is_utc():
    assert bd._iso_now().endswith("+00:00")


def test_read_manifest_default_when_missing(bd_docs):
    m = bd._read_manifest()
    assert m["version"] == "4.0.0"
    assert m["build"]["status"] == "pending"
    assert m["tests"] == {"total": 0, "passed": 0, "failed": 0, "coverage": "0.0%"}


def test_read_manifest_from_file(bd_docs):
    bd_docs.mkdir()
    (bd_docs / "manifest.json").write_text('{"version": "9.1"}', encoding="utf-8")
    assert bd._read_manifest() == {"version": "9.1"}


def test_render_dashboard_full_manifest():
    html = bd.render_dashboard(
        {
            "version": "5.0",
            "build": {"timestamp": "T0", "git_commit": "abc", "status": "green"},
            "tests": {"total": 9, "passed": 8, "coverage": "88%"},
        }
    )
    assert html.count('<section class="card">') == 4
    assert "Verified (8/9 tests pass)" in html
    assert "Last updated: T0" in html
    assert "Git commit: abc · Build status: green · Test coverage: 88%" in html
    assert "(v5.0)" in html


def test_render_dashboard_defaults():
    html = bd.render_dashboard({})
    assert "Verified (0/0 tests pass)" in html
    assert "Git commit: unknown" in html


def test_main_writes_index(bd_docs, capsys):
    bd.main()
    out = bd_docs / "index.html"
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert f"Dashboard generated: {out}" in capsys.readouterr().out


# --------------------------------------------------------------------------
# build_dense_slides
# --------------------------------------------------------------------------

ds = load(SRC + "build_dense_slides.py")


def test_badge_shorthand():
    assert ds._b("risk", "X") == '<span class="badge badge-risk">X</span>'


def test_build_dense_slides(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ds, "DOCS", tmp_path)
    path = ds.build_dense_slides()
    assert path == tmp_path / "index_v3_1.html"
    html = path.read_text(encoding="utf-8")
    assert html.count('" data-title="') == 40
    assert html.count('<div class="slide active" data-title=') == 1
    assert (
        'title="Leak Rate Conversion Table (Full)">8. Leak Rate Conversion Table (Fu…'
        in (html)
    )
    assert 'title="Version History & DMAIC">4. Version History & DMAIC</div>' in html
    assert "40 slides" in capsys.readouterr().out


def test_build_stakeholder(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ds, "DOCS", tmp_path)
    path = ds.build_stakeholder()
    assert path == tmp_path / "STAKEHOLDER_PRESENTATION.html"
    html = path.read_text(encoding="utf-8")
    assert html.count('<div class="slide') == 10
    assert html.count('<div class="slide active">') == 1
    assert '<span class="counter" id="cnt">1 / 10</span>' in html
    assert "10 slides" in capsys.readouterr().out


# --------------------------------------------------------------------------
# plotting/plot_factory (plotly stubbed)
# --------------------------------------------------------------------------


class _Fig:
    def __init__(self, kind=None, data=None, kwargs=None):
        self.kind = kind
        self.data_frame = data
        self.kwargs = kwargs or {}
        self.traces = []
        self.layout = {}
        self.trace_updates = []
        self.written = None

    def add_trace(self, trace):
        self.traces.append(trace)

    def update_layout(self, **kw):
        self.layout.update(kw)

    def update_traces(self, **kw):
        self.trace_updates.append(kw)

    def write_html(self, path, include_plotlyjs, full_html):
        self.written = (path, include_plotlyjs, full_html)
        Path(path).write_text("<html>plot</html>", encoding="utf-8")


def _trace(kind):
    def make(**kw):
        return (kind, kw)

    return make


_px = types.ModuleType("plotly.express")
_px.line = lambda df, **kw: _Fig("line", df, kw)
_px.bar = lambda df, **kw: _Fig("bar", df, kw)
_go = types.ModuleType("plotly.graph_objects")
_go.Figure = _Fig
_go.Bar = _trace("Bar")
_go.Scatter = _trace("Scatter")
_plotly = types.ModuleType("plotly")
_plotly.express = _px
_plotly.graph_objects = _go

pf = load(
    SRC + "plotting/plot_factory.py",
    deps={"plotly": _plotly, "plotly.express": _px, "plotly.graph_objects": _go},
)


def _conversion_df():
    return pd.DataFrame(
        {
            "pressure_bar_abs": [5, 5, 1, 1],
            "leak_rate_mbar_l_s": [1e-8, 1e-5, 1e-8, 1e-5],
            "temperature_K": [4, 300, 4, 300],
            "mass_flow_g_year": [1.0, 2.0, 3.0, 4.0],
        }
    )


def test_write_plot(tmp_path):
    fig = _Fig()
    out = tmp_path / "a" / "b" / "p.html"
    pf.write_plot(fig, out)
    assert fig.written == (str(out), "cdn", True)
    assert out.read_text(encoding="utf-8") == "<html>plot</html>"


def test_plot_1_filters_pressure_five():
    fig = pf.make_plot_1_leak_vs_loss(_conversion_df())
    assert fig.kind == "line"
    assert list(fig.data_frame["pressure_bar_abs"]) == [5, 5]
    assert fig.kwargs["log_x"] is True and fig.kwargs["log_y"] is True
    assert fig.kwargs["color"] == "temperature_K"
    assert "Leak=%{x:.1e}" in fig.trace_updates[0]["hovertemplate"]


def test_plot_2_filters_leak_class():
    fig = pf.make_plot_2_temp_effect(_conversion_df())
    assert list(fig.data_frame["leak_rate_mbar_l_s"]) == [1e-8, 1e-8]
    assert fig.kwargs["x"] == "temperature_K"
    assert fig.kwargs["color"] == "pressure_bar_abs"


def test_plot_3_grouped_bar():
    cost = pd.DataFrame(
        {"class": ["a"], "valve_capex_eur": [1], "helium_cost_over_life_eur": [2]}
    )
    fig = pf.make_plot_3_valve_comparison(cost)
    assert fig.kind == "bar"
    assert fig.data_frame is cost
    assert fig.kwargs["y"] == ["valve_capex_eur", "helium_cost_over_life_eur"]
    assert fig.kwargs["barmode"] == "group"


def test_plot_4_projection_scenarios():
    inv = pd.DataFrame({"mass_loss_g_year_total": [1000.0, 1000.0]})
    fig = pf.make_plot_4_system_projection(inv, helium_price_eur_kg=10.0)
    (bar_kind, bar), (sc_kind, sc) = fig.traces
    assert (bar_kind, sc_kind) == ("Bar", "Scatter")
    assert list(bar["x"]) == [
        "Baseline mix",
        "All leak-tight (1e-9)",
        "All standard warm (1e-5)",
    ]
    assert list(bar["y"]) == pytest.approx([2.0, 0.3, 3.7])
    assert list(sc["y"]) == pytest.approx([20.0, 3.0, 37.0])
    assert sc["yaxis"] == "y2"
    assert fig.layout["yaxis2"]["overlaying"] == "y"


def test_plot_5_reliability_traces():
    rel = pd.DataFrame(
        {
            "valve_type": ["cold", "cold", "warm"],
            "leak_class_mbar_l_s": [1e-8, 1e-5, 1e-5],
            "mtbf_years": [10, 8, 6],
        }
    )
    spare = pd.DataFrame(
        {"valve_population": ["cold", "warm"], "recommended_spares_per_year": [2, 3]}
    )
    fig = pf.make_plot_5_reliability(rel, spare)
    names = [kw["name"] for _, kw in fig.traces]
    assert names == ["MTBF cold", "MTBF warm", "Recommended spares/year"]
    assert list(fig.traces[0][1]["y"]) == [10, 8]
    assert fig.traces[-1][0] == "Bar"
    assert fig.layout["xaxis"]["type"] == "log"


def test_plotly_stub_does_not_leak():
    assert sys.modules.get("plotly.express") is not _px
