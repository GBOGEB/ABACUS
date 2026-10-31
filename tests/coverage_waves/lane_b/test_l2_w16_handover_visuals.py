"""Lane-B wave 16: qplant handover visual suites.

Covers generate_visuals_v3 and generate_standards_stats. plotly and weasyprint
are replaced by recording fakes injected through ``deps``; import-time mkdir is
neutralised and every path constant is redirected to tmp_path. The standards
builder reads two data files that are not committed to the repository, so the
tests supply synthetic ones. Nothing touches the network.
"""

import importlib.util
import json
import pathlib
import sys
import types

import numpy as np
import pandas as pd
import pytest

from ._l2_loader import load

SRC = "qplant/handover_dashboard/src/"

# --------------------------------------------------------------------------
# Permissive plotly / weasyprint fakes
# --------------------------------------------------------------------------

FIGS = []
PDFS = []


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


class _FakeHTML:
    def __init__(self, string, base_url):
        self.string = string
        self.base_url = base_url

    def write_pdf(self, target):
        PDFS.append((self.base_url, target))
        pathlib.Path(target).write_bytes(b"%PDF-fake")


_go = types.ModuleType("plotly.graph_objects")
_go.Figure = _Fig
_go.__getattr__ = _trace_factory
_px = types.ModuleType("plotly.express")
_px.__getattr__ = _px_factory
_px.colors = types.SimpleNamespace(
    qualitative=types.SimpleNamespace(Set2=["#66c2a5", "#fc8d62"])
)
_sub = types.ModuleType("plotly.subplots")
_sub.make_subplots = lambda *a, **k: _Fig("subplots", *a, **k)
_plotly = types.ModuleType("plotly")
_plotly.graph_objects = _go
_plotly.express = _px
_plotly.subplots = _sub
_weasy = types.ModuleType("weasyprint")
_weasy.HTML = _FakeHTML
PLOTLY_DEPS = {
    "plotly": _plotly,
    "plotly.graph_objects": _go,
    "plotly.express": _px,
    "plotly.subplots": _sub,
}

clr = load(SRC + "calc_leak_rate.py", name="l2_w16_vis_calc_leak_rate")
SRC_PKG = types.ModuleType("src")
SRC_PKG.__path__ = []
SRC_PKG.calc_leak_rate = clr
SRC_DEPS = {"src": SRC_PKG, "src.calc_leak_rate": clr}


def _load_quietly(rel, deps):
    """Load ``rel`` with import-time mkdir disabled and sys.path restored."""
    saved_path = list(sys.path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "mkdir", lambda self, *a, **k: None)
        try:
            return load(rel, deps=deps)
        finally:
            sys.path[:] = saved_path


gv = _load_quietly(
    SRC + "generate_visuals_v3.py",
    {**PLOTLY_DEPS, **SRC_DEPS, "weasyprint": _weasy},
)
gs = _load_quietly(SRC + "generate_standards_stats.py", {**PLOTLY_DEPS, **SRC_DEPS})

_REAL_WRITE_TEXT = pathlib.Path.write_text


def _utf8_write_text(self, data, encoding=None, *args, **kwargs):
    return _REAL_WRITE_TEXT(self, data, encoding or "utf-8", *args, **kwargs)


def _fake_tabulate_module():
    mod = types.ModuleType("tabulate")
    mod.__version__ = "0.9.0"

    def tabulate(rows, headers=(), tablefmt="pipe", **_kw):
        lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
        lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
        return "\n".join(lines)

    mod.tabulate = tabulate
    return mod


@pytest.fixture(autouse=True)
def portable_io(monkeypatch):
    """Pin write_text() to UTF-8 and supply tabulate when CI lacks it.

    The generators call write_text() without an encoding (cp1252 Windows
    locales cannot encode their glyphs) and DataFrame.to_markdown needs the
    optional tabulate package, which is not a declared dependency.
    """
    monkeypatch.setattr(pathlib.Path, "write_text", _utf8_write_text)
    if importlib.util.find_spec("tabulate") is None:  # pragma: no cover
        monkeypatch.setitem(sys.modules, "tabulate", _fake_tabulate_module())
    FIGS.clear()
    PDFS.clear()


def test_fakes_and_src_do_not_leak():
    assert sys.modules.get("plotly.express") is not _px
    assert sys.modules.get("weasyprint") is not _weasy
    assert sys.modules.get("src") is not SRC_PKG
    assert gv.HTML is _FakeHTML


# --------------------------------------------------------------------------
# generate_visuals_v3
# --------------------------------------------------------------------------


@pytest.fixture
def gvp(tmp_path, monkeypatch):
    root = tmp_path / "hd"
    docs = root / "docs"
    viz = docs / "visualizations"
    outputs = root / "outputs" / "v25"
    paths = {
        "ROOT": root,
        "DOCS": docs,
        "VIZ_DIR": viz,
        "TABLES_DIR": root / "tables",
        "DOCS_TABLES": docs / "tables",
        "DATA_DIR": root / "data",
        "OUTPUTS_V25": outputs,
        "VIZ_DATA_DIR": viz / "data",
    }
    for key, value in paths.items():
        value.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(gv, key, value)
    (outputs / "chart_data").mkdir()
    return types.SimpleNamespace(**paths)


def test_he_loss_helpers_scale_with_count():
    single = gv.he_loss_g_year(1e-8, 300, 5)
    assert single == pytest.approx(clr.leak_rate_to_mass_flow_g_year(1e-8, 300, 5))
    assert gv.he_loss_g_year(1e-8, 300, 5, 10) == pytest.approx(single * 10)
    assert gv.he_loss_kg_year(1e-8, 300, 5, 10) == pytest.approx(single / 100)
    assert gv._format_scientific(0.000123) == "1.2e-04"


def test_figure_layout_axis_types():
    lin = gv._figure_layout("T", "x", "y")
    assert lin["xaxis"] == {"title": "x", "type": "linear"}
    assert lin["yaxis"]["type"] == "linear" and lin["title"] == {"text": "T"}
    log = gv._figure_layout("T", "x", "y", True, True)
    assert log["xaxis"]["type"] == "log" and log["yaxis"]["type"] == "log"


def test_save_chart_writes_csv_html_and_catalog_entry(gvp):
    fig = _Fig()
    df = pd.DataFrame({"a": [1, 2]})
    entry = gv._save_chart(fig, "c99", "Title", "Cat", df)
    assert entry == {
        "id": "c99",
        "title": "Title",
        "category": "Cat",
        "html": "visualizations/c99.html",
        "csv": "visualizations/data/c99.csv",
        "python": "src/generate_visuals_v3.py",
    }
    assert pd.read_csv(gvp.OUTPUTS_V25 / "chart_data" / "c99.csv")["a"].tolist() == [
        1,
        2,
    ]
    assert (gvp.VIZ_DATA_DIR / "c99.csv").exists()
    assert (gvp.VIZ_DIR / "c99.html").exists()
    post = fig.named("write_html")[0][2]["post_script"]
    assert "filename:'c99'" in post and 'href="data/c99.csv"' in post


def test_base_grid_shape_and_size_factor():
    grid = gv._base_grid()
    expected = (
        len(gv.SUPPLIERS) * len(gv.TEMPS) * len(gv.PRESSURES) * len(gv.VALVE_SIZES)
    )
    assert len(grid) == expected
    row6 = grid[(grid["size"] == "DN06")].iloc[0]
    row50 = grid[
        (grid["size"] == "DN50")
        & (grid["supplier"] == row6["supplier"])
        & (grid["temperature_k"] == row6["temperature_k"])
        & (grid["pressure_bar"] == row6["pressure_bar"])
    ].iloc[0]
    assert row50["he_loss_g_year"] / row6["he_loss_g_year"] == pytest.approx(2.0)
    assert row6["he_loss_kg_year"] == pytest.approx(row6["he_loss_g_year"] / 1000)


def test_build_charts_catalog(gvp):
    catalog = gv.build_charts()
    assert len(catalog) == 18
    ids = [c["id"] for c in catalog]
    assert ids[0] == "chart01_leak_vs_loss_material_overlay"
    assert ids[-1] == "chart18_valve_replacement_strategy"
    assert len(set(ids)) == 18
    assert {c["category"] for c in catalog} == {
        "Leak Rate Fundamentals",
        "Supplier & Material Analysis",
        "Operating Conditions",
        "Cost Analysis",
    }
    for cid in ids:
        assert (gvp.VIZ_DIR / f"{cid}.html").exists()
        assert (gvp.OUTPUTS_V25 / "chart_data" / f"{cid}.csv").exists()
    chart1 = pd.read_csv(gvp.VIZ_DATA_DIR / f"{ids[0]}.csv")
    assert len(chart1) == len(gv.SUPPLIERS) * 3 * 120
    chart3 = [f for f in FIGS if any("Chart 3" in str(c) for c in f.calls)][0]
    vis = {
        t.kwargs["name"].split(" | ")[-1]: t.kwargs["visible"] for t in chart3.traces()
    }
    assert vis == {
        "DN06": True,
        "DN12": "legendonly",
        "DN25": "legendonly",
        "DN50": True,
    }
    perf = pd.read_csv(gvp.VIZ_DATA_DIR / "chart06_supplier_performance_matrix.csv")
    assert sorted(perf["radiation_score"]) == [8, 9]
    mc = pd.read_csv(gvp.VIZ_DATA_DIR / "chart15_monte_carlo_results.csv")
    assert len(mc) == 8000 and mc["annual_loss_kg"].min() >= 5
    tco = pd.read_csv(gvp.VIZ_DATA_DIR / "chart17_lifecycle_tco_secondary_axis.csv")
    meca = tco[tco["valve_type"] == "Meca Inox"].set_index("year")
    assert meca.loc[11, "replacements"] == 0 and meca.loc[12, "replacements"] == 1


def test_build_tables_and_data(gvp):
    gv.build_tables_and_data()
    for base in (
        "supplier_comparison",
        "helium_loss_by_valve_count",
        "material_costs",
        "operating_conditions",
    ):
        assert (gvp.TABLES_DIR / f"{base}.csv").exists()
        assert (
            (gvp.TABLES_DIR / f"{base}.md").read_text(encoding="utf-8").startswith("|")
        )
        assert "<table" in (gvp.DOCS_TABLES / f"{base}.html").read_text(
            encoding="utf-8"
        )
    loss = pd.read_csv(gvp.TABLES_DIR / "helium_loss_by_valve_count.csv")
    assert loss["Valve Count"].tolist() == [10, 10, 50, 100, 210, 410]
    assert loss["Leak Rate (mbar·l/s)"].tolist()[:2] == ["1.0e-09", "1.0e-08"]
    meca = json.loads(
        (gvp.DATA_DIR / "meca_inox_specs.json").read_text(encoding="utf-8")
    )
    assert meca["seal"] == "HDPE"
    ops = json.loads(
        (gvp.DATA_DIR / "operating_conditions.json").read_text(encoding="utf-8")
    )
    assert ops == gv.OPERATING_CONDITIONS
    costs = json.loads((gvp.DATA_DIR / "material_costs.json").read_text("utf-8"))
    assert len(costs) == 9


def test_visual_catalog_and_index(gvp):
    gv.build_visual_catalog_md()
    md = (gvp.ROOT / "VISUAL_CATALOG.md").read_text(encoding="utf-8")
    assert md.startswith("# VISUAL_CATALOG")
    catalog = [
        {
            "id": "c1",
            "title": "One",
            "category": "Zeta",
            "html": "visualizations/c1.html",
            "csv": "visualizations/data/c1.csv",
            "python": "src/x.py",
        },
        {
            "id": "c2",
            "title": "Two",
            "category": "Alpha",
            "html": "visualizations/c2.html",
            "csv": "visualizations/data/c2.csv",
            "python": "src/x.py",
        },
    ]
    gv.build_index_html(catalog)
    html = (gvp.DOCS / "index.html").read_text(encoding="utf-8")
    assert html.index("<option value='Alpha'>") < html.index("<option value='Zeta'>")
    assert "<h4>c1: One</h4>" in html and "href='../src/x.py'" in html
    saved = json.loads((gvp.DOCS / "visual_catalog.json").read_text("utf-8"))
    assert saved == catalog


def test_presentation_pdf_with_and_without_weasyprint(gvp, monkeypatch):
    gv.build_presentation_pdf()
    assert (gvp.DOCS / "presentation.html").exists()
    assert PDFS == [(str(gvp.ROOT), str(gvp.DOCS / "presentation.pdf"))]
    assert (gvp.DOCS / "presentation.pdf").read_bytes() == b"%PDF-fake"
    (gvp.DOCS / "presentation.pdf").unlink()
    monkeypatch.setattr(gv, "HTML", None)
    gv.build_presentation_pdf()
    assert not (gvp.DOCS / "presentation.pdf").exists()
    assert len(PDFS) == 1


def test_visuals_main_writes_summary(gvp, capsys):
    gv.main()
    summary = json.loads(
        (gvp.OUTPUTS_V25 / "build_summary.json").read_text(encoding="utf-8")
    )
    assert summary["version"] == gv.VERSION
    assert summary["charts_generated"] == 18
    assert len(summary["tables_generated"]) == 4
    assert json.loads(capsys.readouterr().out) == summary
    assert (gvp.DOCS / "index.html").exists()


# --------------------------------------------------------------------------
# generate_standards_stats
# --------------------------------------------------------------------------


def _helium_properties():
    points = []
    for t in (4.0, 20.0, 80.0, 300.0):
        for p in (1, 5, 12):
            points.append(
                {
                    "temperature_K": t,
                    "pressure_bar": p,
                    "density_kg_m3": p * 4.0 / t,
                    "viscosity_Pa_s": 1e-6 * t,
                    "thermal_conductivity_W_mK": 0.01 * t,
                    "specific_heat_J_kgK": 5193.0,
                    "speed_of_sound_m_s": 10.0 * t,
                    "compressibility_factor": 1.0 - 0.01 * p / t,
                }
            )
    return {"evaluation_points": points}


def _standards():
    full_sub = {
        "number": "6.2",
        "title": "Helium test",
        "equation": "Q = dP V / dt",
        "activities": ["calibrate", "measure"],
        "deliverables": ["report"],
        "lifecycle_phase": "FAT",
    }
    bare_sub = {"table": "T1", "description": "Seat class"}
    return {
        "standards": [
            {
                "code": "EN 13185",
                "title": "Leak test",
                "scope": "Tracer gas methods",
                "sections": [
                    {"section": "6", "title": "Methods", "subsections": [full_sub]},
                    {"section": "7", "title": "Tables", "tables": [bare_sub, "x"]},
                    {"section": "8", "title": "Text", "requirements": "free text"},
                ],
            },
            {
                "code": "PED",
                "title": "Pressure equipment",
                "articles": [{"article": "4", "title": "Category"}],
            },
            {"code": "ISO 5208", "title": "Valve testing"},
        ],
        "rtm_to_standards_mapping": [
            {
                "rtm_id": "RTM-047",
                "requirement": "Ambient leak",
                "standard": "EN 13185",
                "section": "6.2",
                "test_method": "Helium",
                "acceptance": "<1e-9",
                "deliverable": "Report",
                "phase": "FAT",
            },
            {
                "rtm_id": "RTM-048",
                "requirement": "System leak",
                "standard": "EN 13185",
                "section": "6.3",
                "test_method": "Pressure hold",
                "acceptance": "<1e-5",
                "deliverable": "Chart",
                "phase": "Unlisted",
            },
        ],
        "lifecycle_phases": [{"phase": "Design", "activities": 3}],
    }


@pytest.fixture
def gsp(tmp_path, monkeypatch):
    root = tmp_path / "hd"
    docs = root / "docs"
    paths = {
        "ROOT": root,
        "DATA": root / "data",
        "DOCS": docs,
        "STD_DOCS": docs / "standards",
        "STAT_DOCS": docs / "statistical",
        "VIZ_DOCS": docs / "visualizations_v3",
        "HE_DOCS": docs / "helium_properties",
        "TABLE_DOCS": docs / "tables_v3",
    }
    for key, value in paths.items():
        monkeypatch.setattr(gs, key, value)
    paths["DATA"].mkdir(parents=True)
    (paths["DATA"] / "helium_properties.json").write_text(
        json.dumps(_helium_properties()), encoding="utf-8"
    )
    (paths["DATA"] / "standards_compliance.json").write_text(
        json.dumps(_standards()), encoding="utf-8"
    )
    monkeypatch.setattr(gs, "N_MC", 400)
    monkeypatch.setattr(gs, "RNG", np.random.default_rng(gs.SEED))
    return types.SimpleNamespace(**paths)


def test_io_helpers_round_trip(tmp_path):
    gs._ensure(tmp_path / "a" / "b", tmp_path / "c")
    assert (tmp_path / "a" / "b").is_dir() and (tmp_path / "c").is_dir()
    target = tmp_path / "c" / "x.json"
    gs._write_json(target, {"p": pathlib.Path("q"), "n": 1})
    assert gs._read_json(target) == {"p": "q", "n": 1}
    gs._write(tmp_path / "c" / "t.txt", "hello")
    assert (tmp_path / "c" / "t.txt").read_text(encoding="utf-8") == "hello"


def test_plotly_html_applies_layout(tmp_path):
    fig = _Fig()
    gs._plotly_html(fig, tmp_path / "f.html", height=321)
    layout = fig.named("update_layout")[0][2]
    assert layout["height"] == 321 and layout["template"] == "plotly_white"
    assert (tmp_path / "f.html").exists()


def test_physics_charts_data():
    fig, df = gs.make_chart_leak_vs_loss_extended()
    assert len(df) == 4 * 60 and len(fig.named("add_vline")) == 3
    assert df["kg/year"].iloc[0] == pytest.approx(df["g/year"].iloc[0] / 1000)
    _, df = gs.make_chart_temp_effect_pressure()
    assert set(df["P (bar)"]) == {"1 bar", "5 bar", "12 bar"}
    fig, df = gs.make_chart_choked_flow()
    crit = clr.choked_flow_critical_ratio()
    assert df["Choked"].tolist() == (df["Pressure Ratio"] <= crit).tolist()
    assert df["Choked"].any() and not df["Choked"].all()
    assert fig.named("add_hline")[0][2]["y"] == crit
    _, df = gs.make_chart_purity_dilution()
    assert df["Purity (%)"].min() >= 90 and df["Purity (%)"].max() == 100
    _, df = gs.make_chart_internal_vs_external()
    assert sorted(set(df["Leak Rate"])) == ["1e-04", "1e-09"]
    fig, df = gs.make_chart_valve_fleet_sensitivity()
    assert df["Valve Count"].iloc[0] == 200 and len(fig.traces()) == 2


def test_helium_and_lifecycle_charts(gsp):
    fig, df = gs.make_chart_helium_properties_vs_temp()
    assert len(df) == 12 and len(fig.traces()) == 12
    fig, df = gs.make_chart_compressibility()
    assert fig.args[0] == "line" and fig.named("add_hline")[0][2]["y"] == 1.0
    fig, df = gs.make_chart_lifecycle_standards()
    assert df["Phase_idx"].tolist() == [3, 5]
    assert fig.named("update_traces")[0][2] == {"marker": {"size": 14}}


def test_monte_carlo_pca_and_correlation(gsp):
    mc_df, stats, sens = gs.run_monte_carlo()
    assert len(mc_df) == 400 and stats["n_simulations"] == 400
    assert stats["p5"] <= stats["median"] <= stats["p95"]
    assert set(sens) == {
        "he_price_eur_kg",
        "valve_failure_rate",
        "mttr_hours",
        "leak_class_idx",
        "material_uhmwpe",
        "valve_count",
    }
    finite = {k: v for k, v in sens.items() if np.isfinite(v)}
    assert all(0 <= v <= 1 for v in finite.values())
    assert mc_df["valve_count"].between(300, 520).all()
    np.testing.assert_allclose(
        mc_df["total_cost_eur"], mc_df["he_loss_cost_eur"] + mc_df["maint_cost_eur"]
    )
    pca, scores, loadings = gs.run_pca(mc_df)
    assert scores.shape == (400, 6) and list(loadings.columns) == ["PC1", "PC2", "PC3"]
    assert pca["cumulative_variance"][-1] == pytest.approx(1.0)
    assert pca["eigenvalues"] == sorted(pca["eigenvalues"], reverse=True)
    corr = gs.compute_correlation_matrix(mc_df)
    assert corr.shape == (9, 9)
    assert np.allclose(np.diag(corr.values), 1.0)


def test_first_order_sensitivity_indices_bounded(gsp):
    """First-order indices are Var(E[Y|Xi]) / Var(Y): each lies in [0, 1],
    none saturates at the clamp, and they sum to about 1 at most (sampling
    noise at N=400 allows a small overshoot)."""
    _mc_df, _stats, sens = gs.run_monte_carlo()
    values = list(sens.values())
    assert all(np.isfinite(v) and 0.0 <= v < 1.0 for v in values)
    assert sum(values) <= 1.15
    assert max(sens, key=sens.get) == "valve_failure_rate"


def test_binary_material_sensitivity_is_finite(gsp):
    """The binary material input is grouped by raw value, so its index is
    finite and positive and the indices serialise as strict JSON."""
    _mc_df, _stats, sens = gs.run_monte_carlo()
    assert np.isfinite(sens["material_uhmwpe"])
    assert 0.0 < sens["material_uhmwpe"] < 1.0
    json.dumps(sens, allow_nan=False)


def test_sensitivity_single_group_falls_back_to_zero(gsp, monkeypatch):
    """An input with fewer than 2 groups gets 0.0, never NaN."""
    rng = gs.RNG

    class _ConstantIntegers:
        def __getattr__(self, name):
            return getattr(rng, name)

        def integers(self, low, high, size):
            return np.zeros(size, dtype=int)

    monkeypatch.setattr(gs, "RNG", _ConstantIntegers())
    _mc_df, _stats, sens = gs.run_monte_carlo()
    assert sens["material_uhmwpe"] == 0.0
    assert sens["leak_class_idx"] == 0.0


def test_pca_handles_constant_column():
    df = pd.DataFrame(
        {
            "he_price_eur_kg": [1.0, 2.0, 3.0, 4.0],
            "valve_failure_rate": [0.1, 0.3, 0.2, 0.4],
            "mttr_hours": [1.0, 1.0, 1.0, 1.0],
            "leak_class_idx": [0, 1, 2, 3],
            "material_uhmwpe": [0, 1, 0, 1],
            "valve_count": [300, 320, 310, 330],
        }
    )
    pca, scores, _ = gs.run_pca(df)
    assert np.isfinite(scores).all()
    assert min(pca["eigenvalues"]) == pytest.approx(0.0, abs=1e-9)


def test_statistical_charts(gsp):
    mc_df, _stats, sens = gs.run_monte_carlo()
    hist = gs.make_chart_mc_histogram(mc_df)
    assert [c[2]["annotation_text"].split(":")[0] for c in hist.named("add_vline")] == [
        "Mean",
        "P5",
        "P95",
    ]
    _, sdf = gs.make_chart_sensitivity_bar({"valve_count": 0.2, "other": 0.7})
    assert sdf["Variable"].tolist() == ["other", "Valve Count"]
    pca, scores, loadings = gs.run_pca(mc_df)
    _, scree = gs.make_chart_scree(pca)
    assert scree["Component"].tolist()[0] == "PC1" and len(scree) == 6
    biplot = gs.make_chart_biplot(scores, loadings, mc_df)
    assert len(biplot.named("add_annotation")) == 2 * len(loadings)
    heat = gs.make_chart_correlation_heatmap(gs.compute_correlation_matrix(mc_df))
    assert heat.args[0] == "imshow"
    scatter = gs.make_chart_mc_scatter(mc_df)
    assert len(scatter.args[1]) == 400
    box = gs.make_chart_cost_breakdown_box(mc_df)
    assert set(box.args[1]["Component"]) == {"He Loss", "Maintenance", "Total"}


def test_slide_primitives():
    assert gs._slide("T", "c").startswith('<div class="slide" data-title="T">')
    assert '<div class="slide cat-x" data-title="T">' in gs._slide("T", "c", "x")
    assert gs._kpi("1", "L") == (
        '<div class="kpi"><div class="value">1</div><div class="label">L</div></div>'
    )
    assert 'src="a.html"' in gs._iframe("a.html")
    assert gs._badge("B") == '<span class="badge badge-trace">B</span>'
    df = pd.DataFrame({"tiny": [1e-5, 0.5], "big": [5e7, 2.0], "s": ["a", "b"]})
    html = gs._table_html(df, "tid", max_rows=5)
    assert html.startswith('<table id="tid"><thead><tr><th>tiny</th>')
    assert "<td>1.000e-05</td><td>5.000e+07</td><td>a</td>" in html
    assert "<td>0.500</td><td>2.000</td><td>b</td>" in html
    assert gs._table_html(df.head(0)).startswith("<table><thead>")


def test_build_all_slides_and_master_index(gsp):
    mc_df, stats, sens = gs.run_monte_carlo()
    pca, scores, loadings = gs.run_pca(mc_df)
    corr = gs.compute_correlation_matrix(mc_df)
    slides = gs.build_all_slides(mc_df, stats, sens, pca, scores, loadings, corr)
    assert len(slides) >= 25
    joined = "".join(slides)
    assert "<h4>6.2: Helium test</h4>" in joined
    assert '<div class="equation">Q = dP V / dt</div>' in joined
    assert "<li>calibrate</li>" in joined and "<li>report</li>" in joined
    assert '<span class="badge badge-design">FAT</span>' in joined
    assert "<h4>T1: Seat class</h4>" in joined
    assert "<h3>§8 — Text</h3>" in joined and "<h3>§4 — Category</h3>" in joined
    assert '<table id="tblCompliance"><thead><tr><th>RTM</th>' in joined
    html = gs.build_master_index(slides)
    assert f"Slide 1 of {len(slides)}" in html
    assert '<option value="0">1. OUTPUT_3' in html
    fallback = gs.build_master_index(["<div>no title</div>", slides[0]])
    assert '<option value="0">1. Slide 1</option>' in fallback
    assert "width:50.0%" in fallback


def test_build_all_slides_without_mapping(gsp):
    data = _standards()
    data["rtm_to_standards_mapping"] = []
    (gsp.DATA / "standards_compliance.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    mc_df, stats, sens = gs.run_monte_carlo()
    pca, scores, loadings = gs.run_pca(mc_df)
    corr = gs.compute_correlation_matrix(mc_df)
    slides = gs.build_all_slides(mc_df, stats, sens, pca, scores, loadings, corr)
    matrix = [s for s in slides if "RTM → Standards Compliance Matrix" in s][0]
    assert '<table id="tblCompliance"><thead><tr></tr></thead><tbody></tbody>' in matrix


def test_markdown_documents():
    fat = gs.build_fat_sat_procedures_md()
    assert fat.startswith("# FAT/SAT Procedures")
    ped = gs.build_ped_workflow_md()
    assert ped.lstrip().startswith("#") and "PED" in ped


def test_standards_build_end_to_end(gsp, capsys):
    result = gs.build()
    assert result["version"] == gs.VERSION and result["n_charts"] == 15
    assert result["n_slides"] >= 25
    assert 0 < result["pca_var_pc3"] <= 1
    assert result["mc_p5"] <= result["mc_mean"] <= result["mc_p95"]
    viz = sorted(p.name for p in gsp.VIZ_DOCS.glob("*.html"))
    assert len(viz) == 16
    assert (gsp.DOCS / "index_v3.html").exists()
    for name in (
        "FAT_SAT_Procedures.md",
        "PED_Compliance_Workflow.md",
        "Compliance_Matrix.csv",
        "Compliance_Matrix.json",
    ):
        assert (gsp.STD_DOCS / name).exists()
    stats = json.loads((gsp.STAT_DOCS / "mc_stats.json").read_text("utf-8"))
    assert stats["n_simulations"] == 400
    grid = pd.read_csv(gsp.DOCS / "data_exports" / "full_conversion_grid.csv")
    assert len(grid) == 6 * 6 * 3
    assert (gsp.DOCS / "data_exports" / "mc_summary_statistics.csv").exists()
    assert "BUILD COMPLETE" in capsys.readouterr().out
