"""Lane-B wave 16: qplant handover dashboard builders build_v2 and build_v3_1.

plotly is not a CI dependency, so both builders run against a permissive
recording fake injected through ``deps``. The real sibling physics modules are
loaded by path behind a synthetic ``src`` package. Import-time ``mkdir`` calls
are neutralised while loading and every output path constant is redirected
to tmp_path, so nothing is written into the repository.
"""

import json
import os
import pathlib
import sys
import types

import pandas as pd
import pytest

from ._l2_loader import load

SRC = "qplant/handover_dashboard/src/"

# --------------------------------------------------------------------------
# Permissive plotly fake
# --------------------------------------------------------------------------

FIGS = []


class _Trace:
    def __init__(self, kind, args, kwargs):
        self.kind = kind
        self.args = args
        self.kwargs = kwargs


class _Fig:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls = []
        FIGS.append(self)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self

        return record

    def write_html(self, path, **kwargs):
        self.calls.append(("write_html", (path,), kwargs))
        pathlib.Path(path).write_text("<html>fake plot</html>", encoding="utf-8")

    def named(self, name):
        return [c for c in self.calls if c[0] == name]

    def traces(self):
        return [c[1][0] for c in self.named("add_trace")]


def _trace_factory(name):
    if name.startswith("__"):
        raise AttributeError(name)

    def make(*args, **kwargs):
        return _Trace(name, args, kwargs)

    return make


def _px_factory(name):
    if name.startswith("__"):
        raise AttributeError(name)

    def make(*args, **kwargs):
        return _Fig(name, *args, **kwargs)

    return make


_go = types.ModuleType("plotly.graph_objects")
_go.Figure = _Fig
_go.__getattr__ = _trace_factory
_px = types.ModuleType("plotly.express")
_px.__getattr__ = _px_factory
_sub = types.ModuleType("plotly.subplots")
_sub.make_subplots = lambda *a, **k: _Fig("subplots", *a, **k)
_plotly = types.ModuleType("plotly")
_plotly.graph_objects = _go
_plotly.express = _px
_plotly.subplots = _sub
PLOTLY_DEPS = {
    "plotly": _plotly,
    "plotly.graph_objects": _go,
    "plotly.express": _px,
    "plotly.subplots": _sub,
}

# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _load_quietly(rel, deps):
    """Load ``rel`` with import-time mkdir disabled and sys.path restored."""
    saved_path = list(sys.path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "mkdir", lambda self, *a, **k: None)
        try:
            return load(rel, deps=deps)
        finally:
            sys.path[:] = saved_path


with pytest.MonkeyPatch.context() as _mp:
    _mp.delenv("SSOT_CONFIG_PATH", raising=False)
    _mp.delenv("QPLANT_CONFIG_PATH", raising=False)
    cl = load(SRC + "config_loader.py", name="l2_w16_build_config_loader")

clr = load(SRC + "calc_leak_rate.py", name="l2_w16_build_calc_leak_rate")
mc = load(SRC + "monte_carlo.py", name="l2_w16_build_monte_carlo")
mdb = load(SRC + "materials_db.py", name="l2_w16_build_materials_db")
rm = load(SRC + "risk_model.py", name="l2_w16_build_risk_model")
lhl = load(SRC + "liquid_he_loss.py", name="l2_w16_build_liquid_he_loss")

SRC_PKG = types.ModuleType("src")
SRC_PKG.__path__ = []
SRC_PKG.config_loader = cl
_cfg_deps = {"src": SRC_PKG, "src.config_loader": cl}
cr = load(SRC + "compressor_reliability.py", deps=_cfg_deps)
wcs = load(SRC + "wcs_scenarios.py", deps=_cfg_deps)

SRC_DEPS = {
    "src": SRC_PKG,
    "src.config_loader": cl,
    "src.calc_leak_rate": clr,
    "src.monte_carlo": mc,
    "src.materials_db": mdb,
    "src.risk_model": rm,
    "src.liquid_he_loss": lhl,
    "src.compressor_reliability": cr,
    "src.wcs_scenarios": wcs,
}
for _key, _mod in SRC_DEPS.items():
    if _key != "src":
        setattr(SRC_PKG, _key.split(".", 1)[1], _mod)

bv2 = _load_quietly(SRC + "build_v2.py", {**PLOTLY_DEPS, **SRC_DEPS})
bv31 = _load_quietly(SRC + "build_v3_1.py", {**PLOTLY_DEPS, **SRC_DEPS})


def test_fakes_and_src_do_not_leak():
    assert sys.modules.get("plotly.graph_objects") is not _go
    assert sys.modules.get("src") is not SRC_PKG


def test_import_time_mkdir_targets_are_repo_relative():
    root = pathlib.Path(bv2.__file__).resolve().parent.parent
    assert bv2.ROOT == root
    assert bv2.HEROES == root / "docs" / "heroes"
    assert bv31.VIZ_DIR == root / "docs" / "visualizations_v3"
    assert not (root / "docs").exists() or (root / "docs").is_dir()


_REAL_WRITE_TEXT = pathlib.Path.write_text


def _utf8_write_text(self, data, encoding=None, *args, **kwargs):
    return _REAL_WRITE_TEXT(self, data, encoding or "utf-8", *args, **kwargs)


@pytest.fixture(autouse=True)
def utf8_default(monkeypatch):
    """The builders call write_text() without an encoding.

    Linux CI defaults to UTF-8; a cp1252 Windows locale cannot encode the
    emoji in the pages, so pin the default to UTF-8 for portability.
    """
    monkeypatch.setattr(pathlib.Path, "write_text", _utf8_write_text)


# --------------------------------------------------------------------------
# build_v2
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mc_small():
    results = {}
    for key, config in mc.SCENARIOS.items():
        df = mc.run_monte_carlo(config, n_runs=60)
        results[key] = {
            "config": config,
            "df": df,
            "stats": mc.compute_statistics(df),
            "tornado": mc.sensitivity_tornado(df, config),
        }
    return results


@pytest.fixture
def v2(tmp_path, monkeypatch):
    root = tmp_path / "hd"
    docs = root / "docs"
    paths = {
        "ROOT": root,
        "DOCS": docs,
        "HEROES": docs / "heroes",
        "SLIDES": docs / "slides",
        "NOTES": docs / "notes",
        "VIZ": docs / "visualizations",
        "ASSETS": docs / "assets",
        "DATA_OUT": root / "outputs" / "data_v2",
    }
    for key, value in paths.items():
        value.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(bv2, key, value)
    FIGS.clear()
    return types.SimpleNamespace(**paths)


def test_write_css_and_js(v2):
    bv2.write_css()
    bv2.write_js()
    css = (v2.ASSETS / "style_v2.css").read_text(encoding="utf-8")
    js = (v2.ASSETS / "heroes.js").read_text(encoding="utf-8")
    assert ".kpi-grid" in css and "@media print" in css
    assert "function setTier(tier)" in js and "exportPdf" in js


def test_nav_html_hub_and_hero_variants():
    hub = bv2._nav_html()
    assert 'href="heroes/interface.html"' in hub
    assert 'href="index.html"' in hub
    assert 'class="active"' not in hub
    hero = bv2._nav_html("risk", is_hero=True)
    assert 'href="risk.html" class="active"' in hero
    assert 'href="../index.html"' in hero
    assert hero.count('class="active"') == 1


def test_breadcrumb_tier_nav_kpi_badge():
    crumb = bv2._breadcrumb("COST", "Tier 2")
    assert 'href="cost.html">COST</a>' in crumb and crumb.endswith("Tier 2</div>")
    nav = bv2._tier_nav(("1", "One"), ("2", "Two"), active="2")
    assert nav.startswith('<div class="tier-nav">')
    assert 'data-tier="2" class="active">Two' in nav
    assert 'data-tier="1">One' in nav
    assert bv2._kpi("5", "L", "red") == (
        '<div class="kpi kpi-red"><div class="value">5</div>'
        '<div class="label">L</div></div>'
    )
    assert bv2._badge("Under Review") == (
        '<span class="badge badge-under-review">Under Review</span>'
    )


def test_page_prefixes_assets_for_hero_pages():
    hub = bv2._page("Hub", "<p>b</p>")
    assert 'href="assets/style_v2.css"' in hub and "<main><p>b</p></main>" in hub
    hero = bv2._page("X", "", "risk", "<meta x>", is_hero=True)
    assert 'href="../assets/style_v2.css"' in hero
    assert 'src="../assets/heroes.js"' in hero and "<meta x>" in hero


def test_df_to_html_formats_small_and_large_floats():
    df = pd.DataFrame({"a": [1.23456789, 12345678.9], "b": ["x", "y"]})
    html = bv2._df_to_html(df, max_rows=5)
    assert "1.235" in html
    assert "12,345,679" in html
    assert html.lstrip().startswith("<table")
    assert bv2._df_to_html(df, max_rows=1).count("<tr") == 2


def test_save_plot_applies_template_and_writes(v2):
    fig = _Fig()
    path = bv2._save_plot(fig, "demo")
    assert path == v2.VIZ / "demo.html"
    assert path.read_text(encoding="utf-8").startswith("<html>")
    layouts = fig.named("update_layout")
    assert layouts[0][2] == {"template": "plotly_white"}
    assert layouts[1][2]["paper_bgcolor"] == "#FFFFFF"
    assert fig.named("write_html")[0][2]["include_plotlyjs"] == "cdn"


def test_plot_leak_vs_loss_enhanced(v2):
    path = bv2.plot_leak_vs_loss_enhanced()
    assert path.name == "enhanced_leak_rate_comparison.html" and path.exists()
    fig = FIGS[-1]
    traces = fig.traces()
    assert [t.kwargs["name"] for t in traces] == ["4 K", "20 K", "80 K", "300 K"]
    assert len(traces[0].kwargs["y"]) == 80
    # Colder gas loses more mass at the same leak rate.
    assert traces[0].kwargs["y"][-1] > traces[-1].kwargs["y"][-1]
    assert len(fig.named("add_vrect")) == 2 and len(fig.named("add_hline")) == 1


def test_plot_monte_carlo_distribution(v2, mc_small):
    path = bv2.plot_monte_carlo_distribution(mc_small)
    assert path.name == "monte_carlo_cost_distribution.html"
    fig = FIGS[-1]
    assert [t.kind for t in fig.traces()] == [
        "Histogram",
        "Histogram",
        "Histogram",
        "Scatter",
    ]
    vlines = fig.named("add_vline")
    assert [c[2]["annotation_text"].split(":")[0] for c in vlines] == [
        "P10",
        "P50",
        "P90",
    ]
    title = fig.named("update_layout")[0][2]["title"]["text"]
    assert "60 Simulations" in title


def test_plot_tornado(v2, mc_small):
    bv2.plot_tornado(mc_small)
    fig = FIGS[-1]
    low, high = fig.traces()
    assert low.kwargs["name"] == "Low (P10)" and high.kwargs["name"] == "High (P90)"
    tornado = mc_small["baseline"]["tornado"]
    base = tornado["base"].iloc[0]
    assert list(high.kwargs["x"]) == list(tornado["high"] - base)


def test_plot_supplier_comparison(v2):
    path = bv2.plot_supplier_comparison()
    assert path.name == "supplier_comparison.html"
    capex, meca, swag = FIGS[-1].traces()
    assert capex.kwargs["x"] == [d["supplier"] for d in mdb.SUPPLIER_COMPARISON]
    assert meca.kwargs["name"] == "Meca Inox" and swag.kwargs["y"] == [1e-9, 1e-4]


def test_plot_risk_heatmap_counts_every_risk(v2):
    bv2.plot_risk_heatmap()
    heat = FIGS[-1].args[0]
    assert heat.kind == "Heatmap"
    assert heat.kwargs["z"].sum() == len(rm.risk_matrix_data())
    flat = [cell for row in heat.kwargs["text"] for cell in row if cell]
    assert all(not cell.endswith(" ") for cell in flat)


def test_plot_waterfall_cost(v2, mc_small):
    bv2.plot_waterfall_cost(mc_small)
    wf = FIGS[-1].args[0]
    stats = mc_small["baseline"]["stats"]
    assert wf.kind == "Waterfall"
    assert wf.kwargs["y"][2] == stats["total_cost_eur"]["p50"]
    assert wf.kwargs["measure"] == ["relative", "relative", "total"]


def test_plot_scenario_comparison(v2, mc_small):
    bv2.plot_scenario_comparison(mc_small)
    boxes = FIGS[-1].traces()
    assert [b.kwargs["name"] for b in boxes] == [
        c["config"].name for c in mc_small.values()
    ]
    assert boxes[1].kwargs["marker_color"] == "#EF4444"
    assert all(len(b.kwargs["y"]) == 60 for b in boxes)


def test_plot_gantt_and_sankey(v2):
    assert bv2.plot_gantt_maintenance().name == "maintenance_gantt.html"
    gantt = FIGS[-1]
    assert gantt.args[0] == "timeline"
    assert len(gantt.args[1]) == 8 and gantt.kwargs["color"] == "Resource"
    assert bv2.plot_helium_sankey().name == "helium_sankey.html"
    sankey = FIGS[-1].args[0]
    assert sankey.kind == "Sankey"
    assert len(sankey.kwargs["link"]["value"]) == 9


def test_build_index_lists_every_hero(mc_small):
    html = bv2.build_index(mc_small)
    for hero in bv2.HERO_TABS:
        assert f'href="heroes/{hero["id"]}.html"' in html
    p50 = mc_small["baseline"]["stats"]["total_cost_eur"]["p50"]
    assert f"€{p50:,.0f}" in html
    assert "<title>Navigation Hub" in html


def test_static_hero_pages():
    iface = bv2.build_hero_interface()
    assert "Cold Box Interior" in iface and 'class="active"' in iface
    ops = bv2.build_hero_operations()
    for scenario in rm.OPERATIONAL_SCENARIOS:
        assert scenario["name"] in ops
    assert "Total Spares Investment" in ops


def test_build_hero_control_note_and_hardness_branches(monkeypatch):
    classes = [
        {
            "sub_class": "QX",
            "temp_range_k": "1-2",
            "actuation": "air",
            "electrical_valve": "piezo",
            "position_control": "0-100",
            "radiation_hardness": "required",
        },
        {
            "sub_class": "WX",
            "temp_range_k": "3-4",
            "actuation": "elec",
            "electrical_valve": "sol",
            "position_control": "LS",
            "radiation_hardness": "no",
            "note": "derogation pending",
        },
    ]
    monkeypatch.setattr(bv2, "VALVE_CLASSES", classes)
    html = bv2.build_hero_control()
    assert "<strong>QX</strong>" in html and "<strong>WX</strong>" in html
    assert html.count("badge-required") == 1 and html.count("badge-review") == 1
    assert "<em style='color:#EF4444'>derogation pending</em>" in html


def test_build_hero_design_includes_grid_and_proof(mc_small):
    html = bv2.build_hero_design(mc_small)
    assert "Mass Loss (g/yr)" in html
    proof = clr.dimensional_proof(1e-5, 4.0, 12.0)
    for key in proof:
        assert f"<tr><td>{key}</td>" in html
    assert "<td>g/year</td>" in html


def test_build_hero_cost_scenario_rows(mc_small):
    html = bv2.build_hero_cost(mc_small)
    for data in mc_small.values():
        assert f"<strong>{data['config'].name}</strong>" in html
    assert "€117 / €120 / €300 per kg" in html


def test_build_hero_materials_and_risk():
    mats = bv2.build_hero_materials()
    for code in mdb.CODES_STANDARDS:
        assert f"<strong>{code['code']}</strong>" in mats
    assert mdb.WELDING_SPECS["orbital_tig"]["filler"] in mats
    risk = bv2.build_hero_risk()
    risks = rm.risk_matrix_data()
    assert f'<div class="value">{len(risks)}</div>' in risk
    for r in risks:
        assert f"<p><strong>{r['id']} — {r['title']}:</strong>" in risk
    for b in rm.beam_impact_analysis().values():
        assert b["name"] in risk


def test_write_speaker_notes(v2, mc_small):
    names = bv2.write_speaker_notes(mc_small)
    assert len(names) == 8
    written = sorted(p.stem for p in v2.NOTES.glob("*.md"))
    assert written == sorted(names)
    cost = (v2.NOTES / "slide_005_cost.md").read_text(encoding="utf-8")
    p90 = mc_small["baseline"]["stats"]["total_cost_eur"]["p90"]
    assert f"Worst case (P90): €{p90:,.0f}" in cost


def test_build_end_to_end(v2, mc_small, monkeypatch, capsys):
    monkeypatch.setattr(bv2, "run_all_scenarios", lambda: mc_small)
    result = bv2.build()
    assert result is mc_small
    for key in mc_small:
        records = json.loads(
            (v2.DATA_OUT / f"mc_{key}.json").read_text(encoding="utf-8")
        )
        assert len(records) == 60
        assert (v2.DATA_OUT / f"mc_{key}_stats.json").exists()
        assert (v2.DATA_OUT / f"mc_{key}_tornado.json").exists()
    assert len(list(v2.VIZ.glob("*.html"))) == 9
    assert sorted(p.stem for p in v2.HEROES.glob("*.html")) == sorted(
        h["id"] for h in bv2.HERO_TABS
    )
    assert (v2.DOCS / "index.html").exists()
    version = json.loads((v2.ROOT / "VERSION.json").read_text(encoding="utf-8"))
    assert version["version"] == bv2.VERSION and len(version["features"]) == 9
    out = capsys.readouterr().out
    assert "[8/8] Build complete!" in out


# --------------------------------------------------------------------------
# build_v3_1
# --------------------------------------------------------------------------


@pytest.fixture
def v31(tmp_path, monkeypatch):
    root = tmp_path / "hd31"
    paths = {
        "ROOT": root,
        "VIZ_DIR": root / "docs" / "visualizations_v3",
        "DOC_DIR": root / "docs",
        "DATA_DIR": root / "docs" / "visualizations_v3" / "data",
        "TABLES_DIR": root / "outputs" / "tables_v31",
    }
    for key, value in paths.items():
        value.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(bv31, key, value)
    (root / "docs" / "liquid_he").mkdir()
    (root / "docs" / "compressors").mkdir()
    monkeypatch.setitem(sys.modules, "src", SRC_PKG)
    monkeypatch.setitem(sys.modules, "src.config_loader", cl)
    FIGS.clear()
    return types.SimpleNamespace(**paths)


def test_save_chart_writes_relative_report(v31, capsys):
    fig = _Fig()
    path = bv31._save_chart(fig, "demo", "Demo")
    assert path == v31.VIZ_DIR / "demo.html" and path.exists()
    kwargs = fig.named("write_html")[0][2]
    assert kwargs["config"] == {"displayModeBar": True, "responsive": True}
    assert fig.named("update_layout")[0][2]["paper_bgcolor"] == "white"
    rel = os.path.join("docs", "visualizations_v3", "demo.html")
    assert rel in capsys.readouterr().out


def test_chart_liquid_inventory_depletion_real(v31):
    fig = bv31.chart_liquid_inventory_depletion()
    names = [t.kwargs["name"] for t in fig.traces()]
    assert len(names) == 4
    assert all(n.split(" ")[0] in ("1e-09", "1e-08", "1e-05", "1e-04") for n in names)
    assert (v31.VIZ_DIR / "liquid_inventory_depletion.html").exists()
    assert fig.named("add_hline")[0][2]["y"] == 20


def test_chart_liquid_inventory_depletion_label_branches(v31, monkeypatch):
    days = iter([100.0, 3650.0, 1e9, 1e9])
    monkeypatch.setattr(bv31, "time_to_threshold", lambda *a: next(days))
    fig = bv31.chart_liquid_inventory_depletion()
    names = [t.kwargs["name"] for t in fig.traces()]
    assert names[0].endswith("(refill @ 100d)")
    assert names[1].endswith("(refill @ 10yr)")
    assert names[2].endswith("(>100yr to refill)")


def test_chart_compressor_availability(v31):
    fig = bv31.chart_compressor_availability()
    bar = fig.traces()[0]
    df = cr.build_comparison_table()
    assert list(bar.kwargs["x"]) == list(df["name"])
    assert all(t.endswith("%") for t in bar.kwargs["text"])
    assert len(fig.named("add_hline")) == 4
    yrange = fig.named("update_layout")[0][2]["yaxis"]["range"]
    assert yrange[1] >= 6


def test_chart_boiloff_architecture_cost_benefit(v31):
    boil = bv31.chart_boiloff_vs_leakrate()
    assert len(boil.traces()) >= 3
    assert (v31.VIZ_DIR / "boiloff_vs_leakrate.html").exists()
    arch = bv31.chart_wcs_hp_architecture()
    assert arch.calls and (v31.VIZ_DIR / "wcs_hp_architecture.html").exists()
    rcb = bv31.chart_redundancy_cost_benefit()
    assert rcb.calls and (v31.VIZ_DIR / "redundancy_cost_benefit.html").exists()


def test_chart_vfd_energy_savings_annotates_only_positive_savings(v31):
    fig = bv31.chart_vfd_energy_savings()
    vfd = cr.build_vfd_savings_table(
        full_load_kw=cl.cfg.get(
            "compressor_specifications.fsd575.package_power_kW", 348.54
        )
    )
    positive = int((vfd["cost_savings_eur_yr"] > 0).sum())
    assert len(fig.named("add_annotation")) == positive
    assert 0 < positive < len(vfd)
    title = fig.named("update_layout")[0][2]["title"]
    assert title.startswith("VFD Energy Savings — FSD575 (")


def test_export_data_writes_tables(v31, capsys):
    bv31.export_data()
    for name in (
        "liquid_he_loss_table.csv",
        "liquid_he_loss_table.json",
        "compressor_comparison.csv",
        "compressor_comparison.json",
        "vfd_savings.csv",
        "wcs_scenarios.csv",
        "leak_budget.csv",
        "interlocks.csv",
    ):
        assert (v31.TABLES_DIR / name).exists(), name
    dep = pd.read_csv(v31.DATA_DIR / "inventory_depletion.csv")
    assert "day" in dep.columns
    liq = json.loads(
        (v31.TABLES_DIR / "liquid_he_loss_table.json").read_text(encoding="utf-8")
    )
    assert isinstance(liq, list) and "leak_rate_mbar_l_s" in liq[0]
    assert "Data exported to" in capsys.readouterr().out


def test_page_template_wraps_body():
    html = bv31._page_template("T1", "<p>body</p>")
    assert html.startswith("<!DOCTYPE html>")
    assert "<p>body</p>" in html and "T1" in html
    assert 'href="index_v3_1.html"' in html


def test_build_liquid_operations_guide_threshold_branches(v31, monkeypatch):
    days = iter([365 * 2000.0, 730.0, 30.0, 12.5])
    monkeypatch.setattr(bv31, "time_to_threshold", lambda *a: next(days))
    bv31.build_liquid_operations_guide()
    html = (v31.DOC_DIR / "liquid_he" / "Liquid_Operations_Guide.html").read_text(
        encoding="utf-8"
    )
    assert "<tr><td>1e-09</td><td>>2e+03 years</td></tr>" in html
    assert "<tr><td>1e-08</td><td>2.0 years</td></tr>" in html
    assert "<tr><td>1e-05</td><td>30.0 days</td></tr>" in html
    assert "<tr><td>1e-04</td><td>12.5 days</td></tr>" in html


def test_build_hp_redundancy_and_wcs_protection(v31):
    bv31.build_hp_redundancy_analysis()
    hp = (v31.DOC_DIR / "compressors" / "HP_Redundancy_Analysis.html").read_text(
        encoding="utf-8"
    )
    for name in cr.build_comparison_table()["name"]:
        assert str(name) in hp
    bv31.build_wcs_hp_protection()
    prot = (v31.DOC_DIR / "compressors" / "WCS_HP_Protection.html").read_text(
        encoding="utf-8"
    )
    assert "<!DOCTYPE html>" in prot
    assert "wcs_hp_architecture.html" in prot


def test_build_all_slides_structure(v31):
    slides = bv31._build_all_slides()
    assert len(slides) >= 30
    assert all({"title", "content"} <= set(s) for s in slides)
    assert any(len(s["title"]) > 25 for s in slides)
    assert any(len(s["title"]) <= 25 for s in slides)


def test_build_navigator_thumbs_and_sections(v31, monkeypatch, capsys):
    slides = [
        {"title": "Short", "section": "Alpha", "content": "<p>a</p>"},
        {"title": "A title that is definitely longer", "content": "<p>b</p>"},
        {"title": "Third", "section": "Alpha", "content": "<p>c</p>"},
    ]
    monkeypatch.setattr(bv31, "_build_all_slides", lambda: slides)
    bv31.build_navigator()
    html = (v31.DOC_DIR / "index_v3_1.html").read_text(encoding="utf-8")
    assert '<div class="slide active" data-title="Short">' in html
    assert '<div class="slide" data-title="Third">' in html
    assert "2. A title that is definitel…</div>" in html
    assert "1. Short</div>" in html
    assert '<button class="nav-btn" onclick="goSlide(1)">Alpha</button>' in html
    assert '<button class="nav-btn" onclick="goSlide(2)">General</button>' in html
    assert "index_v3_1.html" in capsys.readouterr().out


def test_main_end_to_end(v31, capsys):
    bv31.main()
    out = capsys.readouterr().out
    assert "BUILD v3.1.0 COMPLETE" in out
    assert len(list(v31.VIZ_DIR.glob("*.html"))) == 6
    assert (v31.DOC_DIR / "index_v3_1.html").exists()
    assert (v31.DOC_DIR / "liquid_he" / "Liquid_Operations_Guide.html").exists()
    assert (v31.TABLES_DIR / "interlocks.csv").exists()
