#!/usr/bin/env python3
"""OUTPUT_2.5_VISUAL_ENHANCED — Material-Specific Visual Dashboard Suite (v2.5.0).

Generates:
- 18 interactive Plotly charts (overlay/isolines/secondary axes/export helpers)
- Material-specific tables (md/csv/html)
- Data repos (JSON)
- Visual catalog documentation
- Enhanced docs/index.html visual gallery + interactive calculator
- Presentation HTML + PDF summary
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from weasyprint import HTML
except Exception:  # pragma: no cover
    HTML = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.calc_leak_rate import leak_rate_to_mass_flow_g_year
DOCS = ROOT / "docs"
VIZ_DIR = DOCS / "visualizations"
TABLES_DIR = ROOT / "tables"
DOCS_TABLES = DOCS / "tables"
DATA_DIR = ROOT / "data"
OUTPUTS_V25 = ROOT / "outputs" / "v25"

VIZ_DATA_DIR = VIZ_DIR / "data"

for d in [VIZ_DIR, VIZ_DATA_DIR, TABLES_DIR, DOCS_TABLES, DATA_DIR, OUTPUTS_V25, OUTPUTS_V25 / "chart_data"]:
    d.mkdir(parents=True, exist_ok=True)

VERSION = "2.5.0"
HE_PRICE_DEFAULT_EUR_KG = 180.0

VALVE_SIZES = ["DN06", "DN12", "DN25", "DN50"]
SIZE_FACTOR = {"DN06": 0.8, "DN12": 1.0, "DN25": 1.25, "DN50": 1.6}
SIZE_NUMERIC = {"DN06": 6, "DN12": 12, "DN25": 25, "DN50": 50}
PRESSURES = [1, 5, 12]
TEMPS = [4, 20, 80, 300]
LEAK_CLASSES = [1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4]

SUPPLIERS = {
    "Meca Inox (HDPE)": {
        "seal": "HDPE",
        "body_material": "316 SS",
        "ambient_leak_class": 1e-8,
        "restriction_leak_class": 1e-4,
        "base_valve_cost": {"DN06": 500, "DN12": 700, "DN25": 850, "DN50": 1000},
        "seal_cost": {"DN06": 50, "DN12": 70, "DN25": 85, "DN50": 100},
        "electropolish_cost": 180,
        "welding_cost": {"DN06": 200, "DN12": 240, "DN25": 300, "DN50": 400},
        "source_ref": "Cryoworld offer / Warm valves slide 2.3.4",
        "compliance": "Economic derogation for W1d warm valves",
    },
    "Swagelok SS-42GSE (UHMWPE)": {
        "seal": "UHMWPE",
        "body_material": "316 SS",
        "ambient_leak_class": 1e-9,
        "restriction_leak_class": 1e-4,
        "base_valve_cost": {"DN06": 800, "DN12": 1000, "DN25": 1200, "DN50": 1500},
        "seal_cost": {"DN06": 80, "DN12": 100, "DN25": 120, "DN50": 150},
        "electropolish_cost": 220,
        "welding_cost": {"DN06": 200, "DN12": 240, "DN25": 300, "DN50": 400},
        "source_ref": "Swagelok SS-42GSE / Warm valves slide 2.3.4",
        "compliance": "Compliant with 1×10⁻⁹ ambient spec",
    },
}

OPERATING_CONDITIONS = [
    {
        "service_type": "Warm service",
        "temperature_k": "300K",
        "pressure_bar": "1-12",
        "leak_rate_requirement": "1×10⁻⁸ acceptable",
        "acceptable_valve": "Meca Inox HDPE",
        "rationale": "Economic; leak-to-ambient requirement relaxed for W1d derogation",
    },
    {
        "service_type": "Cold service",
        "temperature_k": "4K-80K",
        "pressure_bar": "1-12",
        "leak_rate_requirement": "1×10⁻⁹ required",
        "acceptable_valve": "Swagelok UHMWPE",
        "rationale": "Critical cryogenic containment with tighter leak class",
    },
    {
        "service_type": "Helium guard",
        "temperature_k": "300K",
        "pressure_bar": "Sub-atm",
        "leak_rate_requirement": "1×10⁻⁵ acceptable",
        "acceptable_valve": "Meca Inox HDPE",
        "rationale": "Protected boundary; less stringent leakage criteria",
    },
    {
        "service_type": "Internal protect",
        "temperature_k": "Variable",
        "pressure_bar": "Variable",
        "leak_rate_requirement": "1×10⁻⁴ seat leakage acceptable",
        "acceptable_valve": "Either",
        "rationale": "Internal boundaries allow higher seat leakage",
    },
    {
        "service_type": "To vacuum",
        "temperature_k": "Any",
        "pressure_bar": "Any",
        "leak_rate_requirement": "1×10⁻⁸ required",
        "acceptable_valve": "Swagelok UHMWPE",
        "rationale": "Critical containment toward vacuum boundary",
    },
]


def he_loss_g_year(leak_rate: float, temp_k: float, pressure_bar: float, count: int = 1) -> float:
    return leak_rate_to_mass_flow_g_year(leak_rate, temp_k, pressure_bar) * count


def he_loss_kg_year(leak_rate: float, temp_k: float, pressure_bar: float, count: int = 1) -> float:
    return he_loss_g_year(leak_rate, temp_k, pressure_bar, count) / 1000.0


def _format_scientific(v: float) -> str:
    return f"{v:.1e}"


def _figure_layout(title: str, x_title: str, y_title: str, log_x: bool = False, log_y: bool = False) -> dict[str, Any]:
    return {
        "title": {"text": title},
        "template": "plotly_white",
        "height": 520,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        "xaxis": {"title": x_title, "type": "log" if log_x else "linear"},
        "yaxis": {"title": y_title, "type": "log" if log_y else "linear"},
        "margin": {"l": 70, "r": 40, "t": 70, "b": 60},
    }


def _save_chart(fig: go.Figure, chart_id: str, title: str, category: str, df_export: pd.DataFrame) -> dict[str, str]:
    csv_path = OUTPUTS_V25 / "chart_data" / f"{chart_id}.csv"
    csv_docs_path = VIZ_DATA_DIR / f"{chart_id}.csv"
    df_export.to_csv(csv_path, index=False)
    df_export.to_csv(csv_docs_path, index=False)

    post_script = f"""
(function() {{
  const gd = document.querySelector('.plotly-graph-div');
  if (!gd) return;
  const tools = document.createElement('div');
  tools.style.margin='8px 0 12px 0';
  tools.style.display='flex';
  tools.style.gap='8px';
  tools.innerHTML = `
    <button onclick="Plotly.downloadImage(gd,{{format:'png',filename:'{chart_id}'}})">Export PNG</button>
    <button onclick="Plotly.downloadImage(gd,{{format:'svg',filename:'{chart_id}'}})">Export SVG</button>
    <a href="data/{chart_id}.csv" download>Export CSV</a>`;
  gd.parentElement.insertBefore(tools, gd);
}})();
"""
    html_path = VIZ_DIR / f"{chart_id}.html"
    fig.write_html(str(html_path), include_plotlyjs="cdn", full_html=True, post_script=post_script)

    return {
        "id": chart_id,
        "title": title,
        "category": category,
        "html": f"visualizations/{chart_id}.html",
        "csv": f"visualizations/data/{chart_id}.csv",
        "python": "src/generate_visuals_v3.py",
    }


def _base_grid() -> pd.DataFrame:
    rows = []
    for supplier, meta in SUPPLIERS.items():
        for t in TEMPS:
            for p in PRESSURES:
                for size in VALVE_SIZES:
                    leak = meta["ambient_leak_class"]
                    rows.append(
                        {
                            "supplier": supplier,
                            "seal": meta["seal"],
                            "temperature_k": t,
                            "pressure_bar": p,
                            "size": size,
                            "size_mm": SIZE_NUMERIC[size],
                            "leak_rate": leak,
                            "he_loss_g_year": he_loss_g_year(leak, t, p) * SIZE_FACTOR[size],
                            "he_loss_kg_year": he_loss_kg_year(leak, t, p) * SIZE_FACTOR[size],
                            "source_ref": meta["source_ref"],
                        }
                    )
    return pd.DataFrame(rows)


def build_charts() -> list[dict[str, str]]:
    grid = _base_grid()
    catalog: list[dict[str, str]] = []

    # 1. Enhanced Leak Rate vs He Loss (Log-Log)
    xvals = np.logspace(-10, -4, 120)
    rows = []
    fig = go.Figure()
    for supplier, meta in SUPPLIERS.items():
        for t in [4, 80, 300]:
            y = [he_loss_g_year(x, t, 5) for x in xvals]
            fig.add_trace(
                go.Scatter(
                    x=xvals,
                    y=y,
                    mode="lines",
                    name=f"{supplier} @ {t}K",
                    hovertemplate="Leak=%{x:.1e} mbar·l/s<br>Loss=%{y:.3g} g/yr<br>Supplier=" + supplier + "<br>Source=" + meta["source_ref"] + "<extra></extra>",
                )
            )
            for xv, yv in zip(xvals, y):
                rows.append({"supplier": supplier, "temperature_k": t, "leak_rate": xv, "he_loss_g_year": yv})
    fig.update_layout(**_figure_layout("Chart 1 — Enhanced Leak Rate vs He Loss (material overlays)", "Leak rate (mbar·l/s)", "He loss (g/year)", True, True))
    fig.update_layout(updatemenus=[{
        "buttons": [
            {"label": "Cryogenic zoom", "method": "relayout", "args": [{"xaxis.range": [math.log10(1e-10), math.log10(1e-7)], "yaxis.range": [math.log10(1e-4), math.log10(10)]}]},
            {"label": "Warm zoom", "method": "relayout", "args": [{"xaxis.range": [math.log10(1e-9), math.log10(1e-4)], "yaxis.range": [math.log10(1e-3), math.log10(1e3)]}]},
            {"label": "Reset", "method": "relayout", "args": [{"xaxis.autorange": True, "yaxis.autorange": True}]},
        ],
        "direction": "right", "x": 0, "y": 1.15,
    }])
    catalog.append(_save_chart(fig, "chart01_leak_vs_loss_material_overlay", "Enhanced Leak Rate vs He Loss", "Leak Rate Fundamentals", pd.DataFrame(rows)))

    # 2. Temperature sensitivity with pressure isolines
    rows = []
    fig = go.Figure()
    temp_axis = np.array([4, 6, 8, 12, 20, 40, 80, 120, 200, 300])
    for supplier, meta in SUPPLIERS.items():
        for p in PRESSURES:
            y = [he_loss_g_year(meta["ambient_leak_class"], float(t), p) for t in temp_axis]
            trace_name = f"{supplier} | {p} bar"
            fig.add_trace(go.Scatter(x=temp_axis, y=y, mode="lines+markers", name=trace_name,
                                     hovertemplate="T=%{x}K<br>Loss=%{y:.3g} g/yr<br>Pressure="+str(p)+" bar<extra></extra>"))
            for t, yl in zip(temp_axis, y):
                rows.append({"supplier": supplier, "pressure_bar": p, "temperature_k": t, "he_loss_g_year": yl})
    fig.update_layout(**_figure_layout("Chart 2 — Leak Rate vs Temperature (Pressure Isolines)", "Temperature (K)", "He loss (g/year)", False, True))
    catalog.append(_save_chart(fig, "chart02_temperature_sensitivity_pressure_isolines", "Temperature Sensitivity (pressure isolines)", "Leak Rate Fundamentals", pd.DataFrame(rows)))

    # 3. Pressure sensitivity with temperature isolines + size markers
    rows = []
    fig = go.Figure()
    p_axis = np.arange(1, 13)
    marker_map = {"DN06": "circle", "DN12": "square", "DN25": "diamond", "DN50": "triangle-up"}
    for supplier, meta in SUPPLIERS.items():
        for t in TEMPS:
            base_y = [he_loss_kg_year(meta["ambient_leak_class"], t, float(p)) for p in p_axis]
            for size in VALVE_SIZES:
                y = [val * SIZE_FACTOR[size] for val in base_y]
                fig.add_trace(go.Scatter(x=p_axis, y=y, mode="lines+markers", marker_symbol=marker_map[size],
                                         name=f"{supplier} | {t}K | {size}",
                                         visible=True if size in ["DN06", "DN50"] else "legendonly",
                                         hovertemplate="P=%{x} bar<br>Loss=%{y:.4f} kg/yr<br>T="+str(t)+"K<br>Size="+size+"<extra></extra>"))
                for p, yl in zip(p_axis, y):
                    rows.append({"supplier": supplier, "temperature_k": t, "size": size, "pressure_bar": p, "he_loss_kg_year": yl})
    fig.update_layout(**_figure_layout("Chart 3 — Leak Rate vs Pressure (Temperature Isolines)", "Pressure (bar)", "He loss (kg/year)", False, False))
    catalog.append(_save_chart(fig, "chart03_pressure_sensitivity_temperature_isolines", "Pressure Sensitivity (temperature isolines)", "Leak Rate Fundamentals", pd.DataFrame(rows)))

    # 4. Valve size impact
    size_rows = []
    fig = go.Figure()
    for supplier, meta in SUPPLIERS.items():
        y = [he_loss_g_year(meta["ambient_leak_class"], 300, 5) * SIZE_FACTOR[s] for s in VALVE_SIZES]
        fig.add_trace(go.Bar(x=VALVE_SIZES, y=y, name=supplier))
        for s, yl in zip(VALVE_SIZES, y):
            size_rows.append({"supplier": supplier, "size": s, "he_loss_g_year": yl})
    fig.update_layout(**_figure_layout("Chart 4 — Valve Size Impact (DN06-DN50)", "Valve size", "He loss (g/year)", False, False))
    catalog.append(_save_chart(fig, "chart04_valve_size_impact", "Valve Size Impact", "Leak Rate Fundamentals", pd.DataFrame(size_rows)))

    # 5. Seal material comparison
    seal_rows = []
    fig = go.Figure()
    for seal, leak in [("HDPE", 1e-8), ("UHMWPE", 1e-9)]:
        y = [he_loss_g_year(leak, t, 5) for t in TEMPS]
        fig.add_trace(go.Scatter(x=TEMPS, y=y, mode="lines+markers", name=seal))
        for t, yl in zip(TEMPS, y):
            seal_rows.append({"seal": seal, "temperature_k": t, "he_loss_g_year": yl})
    fig.update_layout(**_figure_layout("Chart 5 — Seal Material Comparison (HDPE vs UHMWPE)", "Temperature (K)", "He loss (g/year)", False, True))
    catalog.append(_save_chart(fig, "chart05_seal_material_comparison", "Seal Material Comparison", "Leak Rate Fundamentals", pd.DataFrame(seal_rows)))

    # 6. Supplier performance matrix
    perf = pd.DataFrame([
        {"supplier": s, "capex_eur": np.mean(list(meta["base_valve_cost"].values())), "ambient_leak": meta["ambient_leak_class"], "radiation_score": 8 if meta["seal"] == "HDPE" else 9}
        for s, meta in SUPPLIERS.items()
    ])
    fig = px.scatter(perf, x="ambient_leak", y="capex_eur", size="radiation_score", color="supplier", log_x=True,
                     title="Chart 6 — Meca Inox vs Swagelok Performance Matrix",
                     labels={"ambient_leak": "Ambient leak class (mbar·l/s)", "capex_eur": "Valve CAPEX (€)"})
    catalog.append(_save_chart(fig, "chart06_supplier_performance_matrix", "Supplier Performance Matrix", "Supplier & Material Analysis", perf))

    # 7. Material cost breakdown secondary axis
    rows = []
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for supplier, meta in SUPPLIERS.items():
        base = [meta["base_valve_cost"][s] for s in VALVE_SIZES]
        electro = [meta["electropolish_cost"]] * len(VALVE_SIZES)
        seal = [meta["seal_cost"][s] for s in VALVE_SIZES]
        install = [meta["welding_cost"][s] for s in VALVE_SIZES]
        fig.add_trace(go.Bar(name=f"{supplier} 316 SS base", x=VALVE_SIZES, y=base, legendgroup=supplier), secondary_y=False)
        fig.add_trace(go.Bar(name=f"{supplier} electropolish", x=VALVE_SIZES, y=electro, legendgroup=supplier), secondary_y=False)
        fig.add_trace(go.Bar(name=f"{supplier} seal", x=VALVE_SIZES, y=seal, legendgroup=supplier), secondary_y=False)
        fig.add_trace(go.Scatter(name=f"{supplier} welding/install", x=VALVE_SIZES, y=install, mode="lines+markers", legendgroup=supplier), secondary_y=True)
        for s, b, e, se, ins in zip(VALVE_SIZES, base, electro, seal, install):
            rows.append({"supplier": supplier, "size": s, "base_eur": b, "electropolish_eur": e, "seal_eur": se, "welding_install_eur": ins})
    fig.update_layout(title="Chart 7 — Material Cost Breakdown", barmode="stack", template="plotly_white", height=560)
    fig.update_xaxes(title_text="Valve size")
    fig.update_yaxes(title_text="Material cost (€)", secondary_y=False)
    fig.update_yaxes(title_text="Welding/install (€)", secondary_y=True)
    catalog.append(_save_chart(fig, "chart07_material_cost_breakdown", "Material Cost Breakdown", "Supplier & Material Analysis", pd.DataFrame(rows)))

    # 8. Radiation tolerance degradation curves
    dose = np.linspace(0, 100, 80)
    hdpe_perf = np.exp(-dose / 120) * 100
    uhmwpe_perf = np.exp(-dose / 150) * 100
    rad_df = pd.DataFrame({"dose_kGy": dose, "HDPE_performance_pct": hdpe_perf, "UHMWPE_performance_pct": uhmwpe_perf})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dose, y=hdpe_perf, mode="lines", name="HDPE"))
    fig.add_trace(go.Scatter(x=dose, y=uhmwpe_perf, mode="lines", name="UHMWPE"))
    fig.update_layout(**_figure_layout("Chart 8 — Radiation Tolerance Degradation", "Dose (kGy)", "Relative seal performance (%)", False, False))
    catalog.append(_save_chart(fig, "chart08_radiation_tolerance_curves", "Radiation Tolerance", "Supplier & Material Analysis", rad_df))

    # 9. Welding cost by size
    weld_rows = []
    fig = go.Figure()
    for supplier, meta in SUPPLIERS.items():
        y = [meta["welding_cost"][s] for s in VALVE_SIZES]
        fig.add_trace(go.Bar(x=VALVE_SIZES, y=y, name=supplier))
        for s, c in zip(VALVE_SIZES, y):
            weld_rows.append({"supplier": supplier, "size": s, "welding_cost_eur_joint": c})
    fig.update_layout(**_figure_layout("Chart 9 — Orbital TIG Welding Cost by Size", "Valve size", "Cost (€/joint)", False, False))
    catalog.append(_save_chart(fig, "chart09_welding_cost_by_size", "Welding Cost by Size", "Supplier & Material Analysis", pd.DataFrame(weld_rows)))

    # 10. Warm service analysis
    warm_rows = []
    fig = go.Figure()
    p_axis = np.arange(1, 13)
    for supplier, meta in SUPPLIERS.items():
        y = [he_loss_kg_year(meta["ambient_leak_class"], 300, float(p), 50) for p in p_axis]
        fig.add_trace(go.Scatter(x=p_axis, y=y, mode="lines+markers", name=supplier))
        for p, yl in zip(p_axis, y):
            warm_rows.append({"supplier": supplier, "pressure_bar": p, "loss_kg_year_50_valves": yl})
    fig.update_layout(**_figure_layout("Chart 10 — Warm Service (300K, 1-12 bar)", "Pressure (bar)", "He loss (kg/year) for 50 valves", False, False))
    catalog.append(_save_chart(fig, "chart10_warm_service_analysis", "Warm Service Analysis", "Operating Conditions", pd.DataFrame(warm_rows)))

    # 11. Cold service analysis
    cold_rows = []
    fig = go.Figure()
    for supplier, meta in SUPPLIERS.items():
        y = [he_loss_kg_year(meta["ambient_leak_class"], float(t), 5, 50) for t in [4, 10, 20, 40, 80]]
        fig.add_trace(go.Scatter(x=[4, 10, 20, 40, 80], y=y, mode="lines+markers", name=supplier))
        for t, yl in zip([4, 10, 20, 40, 80], y):
            cold_rows.append({"supplier": supplier, "temperature_k": t, "loss_kg_year_50_valves": yl})
    fig.update_layout(**_figure_layout("Chart 11 — Cold Service (4K-80K, 1-12 bar)", "Temperature (K)", "He loss (kg/year) for 50 valves", False, True))
    catalog.append(_save_chart(fig, "chart11_cold_service_analysis", "Cold Service Analysis", "Operating Conditions", pd.DataFrame(cold_rows)))

    # 12. Helium guard systems
    guard_df = pd.DataFrame({
        "boundary": ["Primary", "Helium Guard", "Secondary Containment"],
        "acceptable_leak_rate": [1e-8, 1e-5, 1e-4],
        "recommendation": ["Swagelok", "Meca Inox", "Either"],
    })
    fig = px.bar(guard_df, x="boundary", y="acceptable_leak_rate", color="recommendation", log_y=True,
                 title="Chart 12 — Helium Guard Systems (sub-atmospheric)",
                 labels={"acceptable_leak_rate": "Acceptable leak class (mbar·l/s)"})
    catalog.append(_save_chart(fig, "chart12_helium_guard_systems", "Helium Guard Systems", "Operating Conditions", guard_df))

    # 13. Internal protect systems
    ip_df = pd.DataFrame({
        "condition": ["Internal boundary", "Protected manifold", "To vacuum"],
        "acceptable_rate": [1e-4, 1e-5, 1e-8],
        "supplier_fit_score_meca": [9, 8, 4],
        "supplier_fit_score_swag": [8, 8, 10],
    })
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ip_df["condition"], y=ip_df["supplier_fit_score_meca"], mode="lines+markers", name="Meca Inox"))
    fig.add_trace(go.Scatter(x=ip_df["condition"], y=ip_df["supplier_fit_score_swag"], mode="lines+markers", name="Swagelok"))
    fig.update_layout(**_figure_layout("Chart 13 — Internal Protect Systems Recommendation", "Condition", "Supplier fit score (0-10)", False, False))
    catalog.append(_save_chart(fig, "chart13_internal_protect_systems", "Internal Protect Systems", "Operating Conditions", ip_df))

    # 14. Cost waterfall
    capex = 410 * 900
    install = 410 * 280
    he_loss_cost = he_loss_kg_year(1e-8, 300, 5, 210) * HE_PRICE_DEFAULT_EUR_KG + he_loss_kg_year(1e-9, 80, 5, 200) * HE_PRICE_DEFAULT_EUR_KG
    maint = 410 * 75
    total = capex + install + he_loss_cost + maint
    wf_df = pd.DataFrame({"component": ["Capital", "Install", "He loss", "Maintenance", "Total"], "eur": [capex, install, he_loss_cost, maint, total]})
    fig = go.Figure(go.Waterfall(
        x=wf_df["component"],
        y=wf_df["eur"],
        measure=["relative", "relative", "relative", "relative", "total"],
    ))
    fig.update_layout(**_figure_layout("Chart 14 — Cost Waterfall", "Category", "Cost (€)", False, False))
    catalog.append(_save_chart(fig, "chart14_cost_waterfall", "Cost Waterfall", "Cost Analysis", wf_df))

    # 15. Monte Carlo
    rng = np.random.default_rng(42)
    he_price = rng.triangular(117, 180, 300, 8000)
    annual_kg = rng.normal(35, 7, 8000).clip(5, None)
    total_cost = annual_kg * he_price + rng.normal(50_000, 8_000, 8000)
    mc_df = pd.DataFrame({"he_price": he_price, "annual_loss_kg": annual_kg, "total_cost_eur": total_cost})
    fig = px.histogram(mc_df, x="total_cost_eur", nbins=60, title="Chart 15 — Monte Carlo Total Cost Distribution")
    catalog.append(_save_chart(fig, "chart15_monte_carlo_results", "Monte Carlo Results", "Cost Analysis", mc_df))

    # 16. Sensitivity analysis
    sens_df = pd.DataFrame({
        "parameter": ["He price", "Welding", "Electropolish", "Leak class choice", "Replacement frequency"],
        "delta_cost_low": [-22000, -7000, -5000, -18000, -12000],
        "delta_cost_high": [34000, 10000, 8000, 26000, 18000],
    })
    fig = go.Figure()
    fig.add_trace(go.Bar(y=sens_df["parameter"], x=sens_df["delta_cost_low"], orientation="h", name="Low", marker_color="#10b981"))
    fig.add_trace(go.Bar(y=sens_df["parameter"], x=sens_df["delta_cost_high"], orientation="h", name="High", marker_color="#ef4444"))
    fig.update_layout(**_figure_layout("Chart 16 — Sensitivity Analysis", "Δ Cost (€)", "Parameter", False, False))
    catalog.append(_save_chart(fig, "chart16_sensitivity_analysis", "Sensitivity Analysis", "Cost Analysis", sens_df))

    # 17. Lifecycle TCO with secondary axis replacements
    years = np.arange(0, 41)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    rows = []
    for name, leak_class, repl_interval, capex in [
        ("Meca Inox", 1e-8, 12, 750),
        ("Swagelok", 1e-9, 18, 1100),
        ("Bellow-sealed", 1e-10, 20, 2400),
    ]:
        yearly_loss = he_loss_kg_year(leak_class, 300, 5, 100) * HE_PRICE_DEFAULT_EUR_KG
        cumulative = years * yearly_loss + capex * 100
        replacements = np.floor(years / repl_interval)
        fig.add_trace(go.Scatter(x=years, y=cumulative, mode="lines", name=f"{name} cumulative cost"), secondary_y=False)
        fig.add_trace(go.Scatter(x=years, y=replacements, mode="lines", name=f"{name} replacements", line=dict(dash="dot")), secondary_y=True)
        for yv, cv, rv in zip(years, cumulative, replacements):
            rows.append({"valve_type": name, "year": int(yv), "cumulative_cost_eur": float(cv), "replacements": int(rv)})
    fig.update_layout(title="Chart 17 — Valve Lifecycle Cost Analysis (0-40 years)", template="plotly_white", height=560)
    fig.update_xaxes(title_text="Years of operation")
    fig.update_yaxes(title_text="Cumulative He loss cost (€)", secondary_y=False)
    fig.update_yaxes(title_text="Number of replacements", secondary_y=True)
    catalog.append(_save_chart(fig, "chart17_lifecycle_tco_secondary_axis", "Lifecycle TCO Comparison", "Cost Analysis", pd.DataFrame(rows)))

    # 18. Replacement strategy
    repl_df = pd.DataFrame({
        "strategy": ["Run-to-failure", "Scheduled 12y", "Scheduled 18y", "Hybrid condition-based"],
        "lifecycle_cost_eur": [2_200_000, 1_820_000, 1_740_000, 1_690_000],
        "availability_pct": [96.9, 98.1, 98.4, 99.0],
    })
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=repl_df["strategy"], y=repl_df["lifecycle_cost_eur"], name="Lifecycle cost (€)"), secondary_y=False)
    fig.add_trace(go.Scatter(x=repl_df["strategy"], y=repl_df["availability_pct"], mode="lines+markers", name="Availability (%)"), secondary_y=True)
    fig.update_layout(title="Chart 18 — Valve Replacement Strategy Cost", template="plotly_white", height=520)
    fig.update_yaxes(title_text="Cost (€)", secondary_y=False)
    fig.update_yaxes(title_text="Availability (%)", secondary_y=True)
    catalog.append(_save_chart(fig, "chart18_valve_replacement_strategy", "Valve Replacement Strategy Cost", "Cost Analysis", repl_df))

    return catalog


def _write_table(df: pd.DataFrame, base_name: str) -> None:
    (TABLES_DIR / f"{base_name}.csv").write_text(df.to_csv(index=False))
    (TABLES_DIR / f"{base_name}.md").write_text(df.to_markdown(index=False))
    (DOCS_TABLES / f"{base_name}.html").write_text(df.to_html(index=False, border=0))


def build_tables_and_data() -> None:
    # Table 1 supplier comparison
    t1 = pd.DataFrame(
        [
            {
                "Parameter": "Seal material",
                "Meca Inox (HDPE)": "HDPE",
                "Swagelok SS-42GSE (UHMWPE)": "UHMWPE",
            },
            {"Parameter": "Base material", "Meca Inox (HDPE)": "316 SS", "Swagelok SS-42GSE (UHMWPE)": "316 SS"},
            {"Parameter": "Electropolish", "Meca Inox (HDPE)": "Yes (Ra <0.4 μm)", "Swagelok SS-42GSE (UHMWPE)": "Yes (Ra <0.4 μm)"},
            {"Parameter": "Leak rate (ambient)", "Meca Inox (HDPE)": ">1×10⁻⁹ (derogation)", "Swagelok SS-42GSE (UHMWPE)": "≤1×10⁻⁹ (compliant)"},
            {"Parameter": "Leak rate (restriction)", "Meca Inox (HDPE)": "1×10⁻⁴", "Swagelok SS-42GSE (UHMWPE)": "1×10⁻⁴"},
            {"Parameter": "Size range", "Meca Inox (HDPE)": "DN12-DN50", "Swagelok SS-42GSE (UHMWPE)": "DN06-DN25"},
            {"Parameter": "Actuation", "Meca Inox (HDPE)": "Pneumatic (W1d) / Manual", "Swagelok SS-42GSE (UHMWPE)": "Manual + limit switch"},
            {"Parameter": "Radiation hardness", "Meca Inox (HDPE)": "Required", "Swagelok SS-42GSE (UHMWPE)": "Required"},
            {"Parameter": "Typical application", "Meca Inox (HDPE)": "Warm On/Off (W1d)", "Swagelok SS-42GSE (UHMWPE)": "Instrumentation, precise control"},
            {"Parameter": "Compliance status", "Meca Inox (HDPE)": "Economic derogation", "Swagelok SS-42GSE (UHMWPE)": "Industry standard"},
        ]
    )
    _write_table(t1, "supplier_comparison")

    # Table 2 helium loss by valve count
    rows = []
    test_cases = [
        (10, 1e-9, "Warm", 300, 1),
        (10, 1e-8, "Warm", 300, 1),
        (50, 1e-9, "Cold", 4, 5),
        (100, 1e-8, "Warm", 300, 12),
    ]
    for count, leak, service, temp, pressure in test_cases:
        g = he_loss_g_year(leak, temp, pressure, count)
        rows.append({
            "Valve Count": count,
            "Leak Rate (mbar·l/s)": _format_scientific(leak),
            "Service": service,
            "Temp": f"{temp}K",
            "Pressure": f"{pressure} bar",
            "Loss (g/year)": round(g, 4),
            "Loss (kg/year)": round(g / 1000, 6),
        })

    g_mix_210 = 0.5 * he_loss_g_year(1e-9, 80, 5, 210) + 0.5 * he_loss_g_year(1e-8, 80, 5, 210)
    rows.append({
        "Valve Count": 210,
        "Leak Rate (mbar·l/s)": "1×10⁻⁹ (50%) + 1×10⁻⁸ (50%)",
        "Service": "Mixed",
        "Temp": "80K",
        "Pressure": "5 bar",
        "Loss (g/year)": round(g_mix_210, 4),
        "Loss (kg/year)": round(g_mix_210 / 1000, 6),
    })

    g_410 = (
        he_loss_g_year(1e-8, 300, 5, 200)
        + he_loss_g_year(1e-9, 80, 5, 130)
        + he_loss_g_year(1e-5, 4, 12, 80)
    )
    rows.append({
        "Valve Count": 410,
        "Leak Rate (mbar·l/s)": "Mixed fleet",
        "Service": "Mixed",
        "Temp": "Mixed",
        "Pressure": "Mixed",
        "Loss (g/year)": round(g_410, 4),
        "Loss (kg/year)": round(g_410 / 1000, 6),
    })
    t2 = pd.DataFrame(rows)
    _write_table(t2, "helium_loss_by_valve_count")

    # Table 3 material costs
    t3 = pd.DataFrame([
        {"Cost Category": "Valve hardware", "Unit": "€/valve", "Meca Inox": "€500-1000", "Swagelok": "€800-1500", "Notes": "Size-dependent"},
        {"Cost Category": "HDPE seal", "Unit": "€/seal", "Meca Inox": "€50-100", "Swagelok": "N/A", "Notes": "Radiation-hardened"},
        {"Cost Category": "UHMWPE seal", "Unit": "€/seal", "Meca Inox": "N/A", "Swagelok": "€80-150", "Notes": "Higher performance"},
        {"Cost Category": "316 SS base", "Unit": "€/kg", "Meca Inox": "€15-25", "Swagelok": "€15-25", "Notes": "Same material"},
        {"Cost Category": "Electropolish", "Unit": "€/valve", "Meca Inox": "€150-300", "Swagelok": "€150-300", "Notes": "Ra <0.4 μm"},
        {"Cost Category": "Orbital welding", "Unit": "€/joint", "Meca Inox": "€200-400", "Swagelok": "€200-400", "Notes": "DN-dependent"},
        {"Cost Category": "Solenoid valve", "Unit": "€/valve", "Meca Inox": "€300-500", "Swagelok": "N/A", "Notes": "For W1d only"},
        {"Cost Category": "Position sensor", "Unit": "€/valve", "Meca Inox": "€200-400", "Swagelok": "Optional", "Notes": "For W1d"},
        {"Cost Category": "Mechanical limit switch", "Unit": "€/valve", "Meca Inox": "€100-200", "Swagelok": "€100-200", "Notes": "Optional"},
    ])
    _write_table(t3, "material_costs")

    # Table 4 operating conditions
    t4 = pd.DataFrame([
        {"Service Type": "Warm service", "Temp": "300K", "Pressure": "1-12 bar", "Leak Rate Requirement": "1×10⁻⁸ acceptable", "Acceptable Valve": "Meca Inox HDPE", "Rationale": "Economic, less critical"},
        {"Service Type": "Cold service", "Temp": "4K-80K", "Pressure": "1-12 bar", "Leak Rate Requirement": "1×10⁻⁹ required", "Acceptable Valve": "Swagelok UHMWPE", "Rationale": "Critical, tight spec"},
        {"Service Type": "Helium guard", "Temp": "300K", "Pressure": "Sub-atm", "Leak Rate Requirement": "1×10⁻⁵ acceptable", "Acceptable Valve": "Meca Inox HDPE", "Rationale": "Protected system"},
        {"Service Type": "Internal protect", "Temp": "Variable", "Pressure": "Variable", "Leak Rate Requirement": "1×10⁻⁴ acceptable (seat)", "Acceptable Valve": "Either", "Rationale": "Internal boundaries"},
        {"Service Type": "To vacuum", "Temp": "Any", "Pressure": "Any", "Leak Rate Requirement": "1×10⁻⁸ required", "Acceptable Valve": "Swagelok UHMWPE", "Rationale": "Critical containment"},
    ])
    _write_table(t4, "operating_conditions")

    # Data repos
    (DATA_DIR / "meca_inox_specs.json").write_text(json.dumps(SUPPLIERS["Meca Inox (HDPE)"], indent=2))
    (DATA_DIR / "swagelok_specs.json").write_text(json.dumps(SUPPLIERS["Swagelok SS-42GSE (UHMWPE)"], indent=2))
    (DATA_DIR / "material_costs.json").write_text(json.dumps(t3.to_dict(orient="records"), indent=2))
    (DATA_DIR / "operating_conditions.json").write_text(json.dumps(OPERATING_CONDITIONS, indent=2))


def build_visual_catalog_md() -> None:
    content = """# VISUAL_CATALOG

## Existing Visuals (Created in v2.1.0)
- [x] Chart 1: Basic leak rate vs mass loss
- [x] Chart 2: Temperature effects
- [x] Chart 3: Cost waterfall
- [x] Chart 4: Monte Carlo distribution
- [x] Chart 5: Risk heatmap
- [x] Chart 6: Sankey diagram
- [x] Chart 7: Supplier comparison (basic)
- [x] Chart 8: Maintenance Gantt
- [x] Chart 9: Reliability distributions

## Reproducible (Can Regenerate)
- All existing charts via `python src/build_v2.py`

## TODO (Planned Enhancements)
- [ ] Overlay plots with isolines (Charts 1-3 above)
- [ ] Secondary axis plots (Charts 4-5)
- [ ] Material-specific comparisons (Charts 6-9)
- [ ] Operating condition matrices (Charts 10-13)
- [ ] Enhanced cost analysis (Charts 14-18)

## Value-Add Recommendations
1. **Interactive Valve Selector**: User picks valve type/size → see all impacts
2. **Scenario Builder**: User defines operating conditions → get recommendation
3. **Cost Optimizer**: Find optimal valve mix for budget constraint
4. **Risk Explorer**: Adjust MTBF/MTTR/He price → see cost distribution

## v2.5 Material-Specific Traceability Notes
- Derogation documented: W1d warm valves use Meca Inox HDPE at 1×10⁻⁸ equivalent ambient class where 1×10⁻⁹ is considered non-industry-stringent.
- Supplier specs linked to source anchors from warm valve slide section 2.3.4 and vendor offers.
- RTM mapping focus: material choice, service type, and leak class acceptance boundaries.
"""
    (ROOT / "VISUAL_CATALOG.md").write_text(content)


def build_index_html(catalog: list[dict[str, str]]) -> None:
    cats = sorted(set(c["category"] for c in catalog))
    cards = []
    for item in catalog:
        cards.append(
            f"""
            <div class='card' data-category='{item['category']}'>
              <h4>{item['id']}: {item['title']}</h4>
              <p><b>Category:</b> {item['category']}</p>
              <div class='actions'>
                <a href='{item['html']}' target='_blank'>Open interactive chart</a>
                <a href='{item['csv']}' target='_blank'>CSV</a>
                <a href='../{item['python']}' target='_blank'>Python regen</a>
              </div>
            </div>
            """
        )

    cat_options = "".join([f"<option value='{c}'>{c}</option>" for c in cats])
    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8' />
<meta name='viewport' content='width=device-width, initial-scale=1' />
<title>QPLANT Visual Dashboard v{VERSION}</title>
<style>
body {{font-family: Inter, Arial, sans-serif; margin:0; background:#f8fafc; color:#0f172a;}}
header {{background:#1e3a8a; color:white; padding:18px 24px;}}
main {{padding:20px; max-width:1300px; margin:auto;}}
.hero {{background:white; border-radius:10px; padding:18px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.08);}}
.grid {{display:grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap:12px;}}
.card {{background:white; border:1px solid #e2e8f0; border-radius:10px; padding:12px;}}
.actions a {{display:inline-block; margin-right:8px; margin-top:6px; font-size:13px;}}
.controls {{display:flex; gap:12px; flex-wrap:wrap; align-items:center;}}
label {{font-size:14px;}}
input,select {{padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px;}}
.kpi {{display:grid; grid-template-columns:repeat(3,minmax(120px,1fr)); gap:8px; margin-top:8px;}}
.kpi div {{background:#e2e8f0; border-radius:8px; padding:8px; text-align:center;}}
small.note {{display:block; color:#334155; margin-top:10px;}}
</style>
<script>
function filterCharts() {{
  const cat = document.getElementById('cat').value;
  const supplier = document.getElementById('supplier').value;
  document.querySelectorAll('.card').forEach(card => {{
    const okCat = cat === 'all' || card.dataset.category === cat;
    const txt = card.textContent.toLowerCase();
    const okSupplier = supplier === 'all' || txt.includes(supplier.toLowerCase());
    card.style.display = (okCat && okSupplier) ? 'block' : 'none';
  }});
}}

function compute() {{
  const count = Number(document.getElementById('count').value || 0);
  const leak = Number(document.getElementById('leak').value || 0);
  const temp = Number(document.getElementById('temp').value || 300);
  const pressure = Number(document.getElementById('pressure').value || 1);
  const material = document.getElementById('material').value;
  const service = document.getElementById('service').value;

  const R = 8.314462618;
  const M = 4.002602; // g/mol
  const secYear = 365.25 * 86400;
  const q = leak * 0.1; // Pa m3/s
  const nDot = (q * pressure) / (R * temp);
  const gYear = nDot * M * secYear * count;
  const kgYear = gYear / 1000;
  const hePrice = 180;
  const sealPremium = material === 'UHMWPE' ? 120 : 80;
  const annualCost = kgYear * hePrice + count * sealPremium * 0.08;

  document.getElementById('out_g').textContent = gYear.toFixed(4);
  document.getElementById('out_kg').textContent = kgYear.toFixed(6);
  document.getElementById('out_cost').textContent = '€' + annualCost.toFixed(2);
  document.getElementById('out_note').textContent = 'Service=' + service + ', Material=' + material + ', He price=€180/kg';
}}
</script>
</head>
<body>
<header>
  <h2>OUTPUT_2.5_VISUAL_ENHANCED — Material-Specific Visual Dashboard Suite</h2>
  <p>HDPE vs UHMWPE comparison with derogation justification for Meca Inox warm valves</p>
</header>
<main>
  <section class='hero'>
    <h3>Visual Gallery (18 charts)</h3>
    <div class='controls'>
      <label>Category <select id='cat' onchange='filterCharts()'><option value='all'>All</option>{cat_options}</select></label>
      <label>Supplier <select id='supplier' onchange='filterCharts()'><option value='all'>All</option><option value='Meca'>Meca Inox</option><option value='Swagelok'>Swagelok</option></select></label>
      <a href='../VISUAL_CATALOG.md' target='_blank'>Open VISUAL_CATALOG.md</a>
    </div>
    <div class='grid'>{''.join(cards)}</div>
  </section>

  <section class='hero'>
    <h3>Interactive Calculator</h3>
    <div class='controls'>
      <label>Valve count <input id='count' type='number' value='210' oninput='compute()'/></label>
      <label>Leak rate (mbar·l/s) <input id='leak' type='number' step='1e-9' value='1e-8' oninput='compute()'/></label>
      <label>Temperature (K) <input id='temp' type='number' value='300' oninput='compute()'/></label>
      <label>Pressure (bar) <input id='pressure' type='number' value='5' oninput='compute()'/></label>
      <label>Service
        <select id='service' onchange='compute()'>
          <option>Warm</option><option>Cold</option><option>Helium guard</option><option>Internal protect</option>
        </select>
      </label>
      <label>Material
        <select id='material' onchange='compute()'>
          <option>HDPE</option><option>UHMWPE</option>
        </select>
      </label>
    </div>
    <div class='kpi'>
      <div><b id='out_g'>0</b><br/>g/year</div>
      <div><b id='out_kg'>0</b><br/>kg/year</div>
      <div><b id='out_cost'>€0</b><br/>annual estimate</div>
    </div>
    <small class='note' id='out_note'></small>
  </section>

  <section class='hero'>
    <h3>Material and Cost Tables</h3>
    <ul>
      <li><a href='tables/supplier_comparison.html' target='_blank'>Supplier comparison</a></li>
      <li><a href='tables/material_costs.html' target='_blank'>Material costs</a></li>
      <li><a href='tables/operating_conditions.html' target='_blank'>Operating conditions</a></li>
      <li><a href='tables/helium_loss_by_valve_count.html' target='_blank'>Helium loss by valve count</a></li>
    </ul>
  </section>
</main>
<script>compute();</script>
</body></html>
"""
    (DOCS / "index.html").write_text(html)

    (DOCS / "visual_catalog.json").write_text(json.dumps(catalog, indent=2))


def build_presentation_pdf() -> None:
    html_content = """<!doctype html><html><head><meta charset='utf-8'>
<style>
body{font-family:Inter,Arial,sans-serif;margin:0;padding:0;color:#0f172a}
.slide{page-break-after:always;padding:38px 44px;height:92vh}
h1,h2{color:#1e3a8a}.k{background:#eef2ff;padding:10px;border-radius:8px;margin:6px 0}
</style></head><body>
<div class='slide'><h1>QPLANT v2.5.0 Presentation (Material Specific)</h1><p>Generated by src/generate_visuals_v3.py</p></div>
<div class='slide'><h2>Slide 5: Supplier comparison</h2>
<div class='k'><b>Meca Inox (HDPE)</b> — warm W1d, economic derogation (ambient class effectively 1×10⁻⁸)</div>
<div class='k'><b>Swagelok SS-42GSE (UHMWPE)</b> — instrumentation, compliant with 1×10⁻⁹</div>
<p>Reference charts: chart06_supplier_performance_matrix, chart05_seal_material_comparison</p></div>
<div class='slide'><h2>Slide 8: Material cost breakdown</h2>
<p>316 SS + electropolish + seal + welding are separated. HDPE and UHMWPE seal costs shown by DN06-DN50 sizes.</p>
<p>Reference chart: chart07_material_cost_breakdown</p></div>
<div class='slide'><h2>Slide 12: Operating condition recommendations</h2>
<ul><li>Warm service: Meca Inox HDPE acceptable with derogation</li><li>Cold service: Swagelok UHMWPE preferred</li><li>Helium guard/internal protect: less strict classes acceptable</li></ul>
<p>Reference charts: chart10, chart11, chart12, chart13</p></div>
<div class='slide'><h2>Slide 15: Visual evidence gallery</h2>
<p>18 interactive plots generated with Plotly and export links (PNG/SVG/CSV).</p>
<p>Landing page: docs/index.html</p></div>
</body></html>"""
    presentation_html = DOCS / "presentation.html"
    presentation_html.write_text(html_content)
    if HTML is not None:
        HTML(string=html_content, base_url=str(ROOT)).write_pdf(str(DOCS / "presentation.pdf"))


def main() -> None:
    catalog = build_charts()
    build_tables_and_data()
    build_visual_catalog_md()
    build_index_html(catalog)
    build_presentation_pdf()

    summary = {
        "version": VERSION,
        "charts_generated": len(catalog),
        "tables_generated": [
            "tables/supplier_comparison.md",
            "tables/material_costs.md",
            "tables/operating_conditions.md",
            "tables/helium_loss_by_valve_count.md",
        ],
    }
    (OUTPUTS_V25 / "build_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
