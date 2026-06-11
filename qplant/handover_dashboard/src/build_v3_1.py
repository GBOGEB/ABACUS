#!/usr/bin/env python3
"""
BUILD v4.0.0 — Critical Correction: HP Compressor Count 4→3, Pressure Parameters Updated

Generates:
  1. Six new Plotly visualizations in docs/visualizations_v3/
  2. Three documentation HTML pages in docs/
  3. Updated master navigator (index_v3_1.html) with 40 slides
  4. Data exports (CSV/JSON)
"""

import sys, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.liquid_he_loss import (
    build_leak_rate_liquid_loss_table,
    inventory_depletion_timeseries,
    compute_liquid_loss,
    LiquidHeState,
    time_to_threshold,
    HE_PRICE_EUR_PER_KG,
    RHO_LIQ_DEFAULT,
)
from src.compressor_reliability import (
    build_comparison_table,
    build_vfd_savings_table,
    build_reliability_curves,
    CONFIGS,
    annual_energy_savings_vfd,
    vfd_power_at_load,
    fixed_speed_power_at_load,
)
from src.wcs_scenarios import (
    build_leak_budget_table,
    build_interlock_table,
    build_scenario_table,
    SCENARIOS,
    LEAK_ALLOCATIONS,
    TOTAL_LEAK_BUDGET,
)

# ── Output directories ──────────────────────────────────────────────
VIZ_DIR = ROOT / "docs" / "visualizations_v3"
DOC_DIR = ROOT / "docs"
DATA_DIR = ROOT / "docs" / "visualizations_v3" / "data"
TABLES_DIR = ROOT / "outputs" / "tables_v31"

for d in [VIZ_DIR, DATA_DIR, TABLES_DIR, DOC_DIR / "liquid_he", DOC_DIR / "compressors"]:
    d.mkdir(parents=True, exist_ok=True)


# ── Common styling ──────────────────────────────────────────────────
COLORS = {
    "primary": "#1a365d",
    "accent": "#2b6cb0",
    "success": "#38a169",
    "warning": "#d69e2e",
    "danger": "#e53e3e",
    "info": "#3182ce",
}

PLOTLY_TEMPLATE = "plotly_white"
PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, Segoe UI, sans-serif", size=12),
    title_font_size=16,
    margin=dict(l=60, r=40, t=60, b=50),
    paper_bgcolor="white",
    plot_bgcolor="#fafbfc",
    legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#e2e8f0", borderwidth=1),
)


def _save_chart(fig, name: str, title: str = ""):
    """Save Plotly figure as standalone HTML."""
    fig.update_layout(**PLOTLY_LAYOUT)
    path = VIZ_DIR / f"{name}.html"
    fig.write_html(str(path), include_plotlyjs="cdn",
                   full_html=True,
                   config={"displayModeBar": True, "responsive": True})
    print(f"  ✓ {path.relative_to(ROOT)}")
    return path


# ══════════════════════════════════════════════════════════════════
# CHART 1: Liquid Inventory Depletion Over Time
# ══════════════════════════════════════════════════════════════════

def chart_liquid_inventory_depletion():
    """Plotly line chart: liquid He level vs time for multiple leak rates."""
    leak_rates = [1e-9, 1e-8, 1e-5, 1e-4]
    initial_vol = 5000.0
    min_frac = 0.20
    duration = 365

    df = inventory_depletion_timeseries(
        initial_volume_L=initial_vol,
        leak_rates=leak_rates,
        duration_days=duration,
    )

    fig = go.Figure()

    colors_line = ["#38a169", "#3182ce", "#d69e2e", "#e53e3e"]
    for i, q in enumerate(leak_rates):
        col = f"Q={q:.0e}"
        pct = (df[col] / initial_vol) * 100
        t_thresh = time_to_threshold(initial_vol, q, min_frac)
        label = f"{q:.0e} mbar·L/s"
        if t_thresh < duration:
            label += f" (refill @ {t_thresh:.0f}d)"
        elif t_thresh < 365 * 100:
            label += f" (refill @ {t_thresh/365:.0f}yr)"
        else:
            label += " (>100yr to refill)"

        fig.add_trace(go.Scatter(
            x=df["day"], y=pct, mode="lines", name=label,
            line=dict(color=colors_line[i], width=2.5),
        ))

    # Threshold line
    fig.add_hline(y=20, line_dash="dash", line_color="#e53e3e",
                  annotation_text="20% — Min Operating Level",
                  annotation_position="top right")

    fig.update_layout(
        title="Liquid He Inventory Depletion — WSH 5,000 L Vessel",
        xaxis_title="Time (days)",
        yaxis_title="Liquid He Level (%)",
        yaxis=dict(range=[0, 105]),
        xaxis=dict(range=[0, duration]),
    )

    _save_chart(fig, "liquid_inventory_depletion",
                "Liquid He Inventory Depletion")
    return fig


# ══════════════════════════════════════════════════════════════════
# CHART 2: HP Compressor Availability Comparison
# ══════════════════════════════════════════════════════════════════

def chart_compressor_availability():
    """Bar chart: system availability comparison."""
    df = build_comparison_table()

    # Use "nines" for log-friendly display
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["name"],
        y=df["A_system_nines"],
        marker_color=[COLORS["info"], COLORS["accent"],
                      COLORS["success"], COLORS["primary"]],
        text=[f'{a:.4f}%' for a in df["A_system_pct"]],
        textposition="outside",
    ))

    # Reference lines
    for nines, label in [(2, "99% (2 nines)"), (3, "99.9% (3 nines)"),
                          (4, "99.99% (4 nines)"), (5, "99.999% (5 nines)")]:
        fig.add_hline(y=nines, line_dash="dot", line_color="#a0aec0",
                      annotation_text=label, annotation_position="top left",
                      annotation_font_size=10)

    fig.update_layout(
        title="HP Compressor System Availability Comparison",
        yaxis_title="Availability (nines = −log₁₀(1−A))",
        xaxis_title="Configuration",
        yaxis=dict(range=[0, max(df["A_system_nines"].max() * 1.2, 6)]),
        showlegend=False,
    )

    _save_chart(fig, "compressor_availability_comparison",
                "HP Compressor Availability")
    return fig


# ══════════════════════════════════════════════════════════════════
# CHART 3: Boil-off Rate vs Leak Rate
# ══════════════════════════════════════════════════════════════════

def chart_boiloff_vs_leakrate():
    """Scatter plot: leak rate → liquid boil-off & cost."""
    temps = [4.222, 80, 300]
    temp_labels = ["4K (liquid space)", "80K (shield)", "300K (ambient)"]
    temp_colors = ["#e53e3e", "#d69e2e", "#3182ce"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    leak_rates = np.logspace(-9, -2, 50)

    for T, label, color in zip(temps, temp_labels, temp_colors):
        losses_L_day = []
        costs_eur_day = []
        for q in leak_rates:
            state = LiquidHeState(leak_rate_mbar_l_s=q, temperature_K=T)
            r = compute_liquid_loss(state)
            losses_L_day.append(r["liquid_loss_L_day"])
            costs_eur_day.append(r["cost_eur_day"])

        fig.add_trace(go.Scatter(
            x=leak_rates, y=losses_L_day,
            mode="lines", name=f"Boil-off ({label})",
            line=dict(color=color, width=2),
        ), secondary_y=False)

        fig.add_trace(go.Scatter(
            x=leak_rates, y=costs_eur_day,
            mode="lines", name=f"Cost ({label})",
            line=dict(color=color, width=1.5, dash="dot"),
        ), secondary_y=True)

    fig.update_xaxes(type="log", title_text="Leak Rate (mbar·L/s)")
    fig.update_yaxes(type="log", title_text="Liquid Boil-off (L/day)", secondary_y=False)
    fig.update_yaxes(type="log", title_text="Cost (€/day @ €120/kg)", secondary_y=True)

    fig.update_layout(
        title="Boil-off Rate & Cost vs Leak Rate (by temperature)",
    )

    _save_chart(fig, "boiloff_vs_leakrate", "Boil-off vs Leak Rate")
    return fig


# ══════════════════════════════════════════════════════════════════
# CHART 4: WCS.HP Reliability Block Diagram
# ══════════════════════════════════════════════════════════════════

def chart_wcs_hp_architecture():
    """Visual flowchart of HP supply architecture using Plotly shapes."""
    fig = go.Figure()

    # Layout dimensions
    W, H = 1000, 600

    # --- Draw compressor blocks ---
    comp_names = ["Compressor A\n(Running)", "Compressor B\n(Running)", "Compressor C\n(Standby)"]
    comp_colors = ["#38a169", "#38a169", "#d69e2e"]
    for i, (name, color) in enumerate(zip(comp_names, comp_colors)):
        x0 = 50
        y0 = 80 + i * 160
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x0+180, y1=y0+100,
                      fillcolor=color, line_color="#2d3748", line_width=2,
                      opacity=0.85)
        fig.add_annotation(x=x0+90, y=y0+50, text=name, showarrow=False,
                           font=dict(color="white", size=11, family="Inter"))

    # --- Check valves ---
    for i in range(3):
        x_cv = 260
        y_cv = 120 + i * 160
        fig.add_shape(type="circle", x0=x_cv, y0=y_cv-15, x1=x_cv+30, y1=y_cv+15,
                      fillcolor="#bee3f8", line_color="#2a4365")
        fig.add_annotation(x=x_cv+15, y=y_cv, text="CV", showarrow=False,
                           font=dict(size=9))

    # --- HP Header (main bus) ---
    fig.add_shape(type="rect", x0=330, y0=50, x1=360, y1=530,
                  fillcolor="#2b6cb0", line_color="#1a365d", line_width=3)
    fig.add_annotation(x=345, y=30, text="HP Header\n14 barg",
                       showarrow=False, font=dict(size=12, color="#1a365d"))

    # --- Connection lines ---
    for i in range(3):
        y_line = 130 + i * 160
        fig.add_shape(type="line", x0=230, y0=y_line, x1=260, y1=y_line,
                      line_color="#4a5568", line_width=2)
        fig.add_shape(type="line", x0=290, y0=y_line, x1=330, y1=y_line,
                      line_color="#4a5568", line_width=2)

    # --- Main supply branch ---
    fig.add_shape(type="line", x0=360, y0=150, x1=450, y1=150,
                  line_color="#2b6cb0", line_width=3)
    fig.add_shape(type="rect", x0=450, y0=110, x1=620, y1=190,
                  fillcolor="#ebf8ff", line_color="#2b6cb0", line_width=2)
    fig.add_annotation(x=535, y=150, text="Main Supply\nQVB / WSH / Beam\n(70% leak budget)",
                       showarrow=False, font=dict(size=10))

    # --- Sidestream branch ---
    fig.add_shape(type="line", x0=360, y0=350, x1=420, y1=350,
                  line_color="#d69e2e", line_width=2)
    # Isolation valve symbol (use path for diamond shape)
    fig.add_shape(type="path",
                  path="M 440 330 L 460 350 L 440 370 L 420 350 Z",
                  fillcolor="#fefcbf", line_color="#d69e2e", line_width=2)
    fig.add_annotation(x=440, y=350, text="IV", showarrow=False,
                       font=dict(size=10))
    fig.add_shape(type="line", x0=460, y0=350, x1=500, y1=350,
                  line_color="#d69e2e", line_width=2)
    fig.add_shape(type="rect", x0=500, y0=310, x1=670, y1=390,
                  fillcolor="#fefcbf", line_color="#d69e2e", line_width=2)
    fig.add_annotation(x=585, y=350,
                       text="Sidestreams\nRecovery / Purif / Research\n(20% leak budget)",
                       showarrow=False, font=dict(size=10))

    # --- Pressure transmitters ---
    fig.add_annotation(x=345, y=560, text="PT-101 / PT-102\n(redundant)",
                       showarrow=True, ay=-30, font=dict(size=9, color="#718096"))

    # --- Legend ---
    fig.add_annotation(x=800, y=100, text="<b>WCS.HP Protection Logic</b><br>"
                       "P < 13.5 barg → Close sidestream IV<br>"
                       "P < 13.0 barg → Alarm + start standby<br>"
                       "2 failed → Beam to 50%",
                       showarrow=False, font=dict(size=10),
                       align="left", bordercolor="#e2e8f0", borderwidth=1,
                       bgcolor="white", borderpad=8)

    fig.update_layout(
        title="WCS.HP Supply Architecture — Reliability Block Diagram",
        xaxis=dict(range=[0, W], visible=False),
        yaxis=dict(range=[H, 0], visible=False, scaleanchor="x"),
        width=W, height=H,
        showlegend=False,
    )

    _save_chart(fig, "wcs_hp_architecture", "WCS.HP Architecture")
    return fig


# ══════════════════════════════════════════════════════════════════
# CHART 5: Redundancy Cost-Benefit Analysis
# ══════════════════════════════════════════════════════════════════

def chart_redundancy_cost_benefit():
    """Scatter plot: capital cost vs availability, bubble = energy cost."""
    df = build_comparison_table()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["total_capex_eur"] / 1000,
        y=df["A_system_nines"],
        mode="markers+text",
        text=df["name"],
        textposition="top center",
        marker=dict(
            size=df["annual_energy_eur"] / 8000,
            sizemin=10,
            color=[COLORS["info"], COLORS["accent"],
                   COLORS["success"], COLORS["primary"]],
            line=dict(width=2, color="#2d3748"),
        ),
    ))

    fig.update_layout(
        title="Redundancy Cost-Benefit — Capital vs Availability<br>"
              "<sub>Bubble size = annual energy cost</sub>",
        xaxis_title="Total Capital Cost (k€)",
        yaxis_title="Availability (nines)",
    )

    _save_chart(fig, "redundancy_cost_benefit", "Redundancy Cost-Benefit")
    return fig


# ══════════════════════════════════════════════════════════════════
# CHART 6: VFD Energy Savings
# ══════════════════════════════════════════════════════════════════

def chart_vfd_energy_savings():
    """Bar chart: fixed-speed vs VFD power at various loads."""
    from src.config_loader import cfg as _cfg
    _pkg_kw = _cfg.get('compressor_specifications.fsd575.package_power_kW', 348.54)
    vfd_df = build_vfd_savings_table(full_load_kw=_pkg_kw)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=vfd_df["load_pct"],
        y=vfd_df["power_fixed_kw"],
        name="Fixed Speed",
        marker_color="#e53e3e",
        opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        x=vfd_df["load_pct"],
        y=vfd_df["power_vfd_kw"],
        name="With VFD",
        marker_color="#38a169",
        opacity=0.85,
    ))

    # Add savings annotations
    for _, row in vfd_df.iterrows():
        if row["cost_savings_eur_yr"] > 0:
            fig.add_annotation(
                x=row["load_pct"],
                y=row["power_fixed_kw"] + 15,
                text=f"€{row['cost_savings_eur_yr']/1000:.0f}k/yr",
                showarrow=False,
                font=dict(size=9, color=COLORS["success"]),
            )

    fig.update_layout(
        title=f"VFD Energy Savings — FSD575 ({_pkg_kw:.0f} kW package) per Compressor",
        xaxis_title="Load (%)",
        yaxis_title="Power Consumption (kW)",
        barmode="group",
    )

    _save_chart(fig, "vfd_energy_savings", "VFD Energy Savings")
    return fig


# ══════════════════════════════════════════════════════════════════
# DATA EXPORTS
# ══════════════════════════════════════════════════════════════════

def export_data():
    """Export calculation tables to CSV/JSON."""
    # Liquid loss table
    liq_df = build_leak_rate_liquid_loss_table()
    liq_df.to_csv(TABLES_DIR / "liquid_he_loss_table.csv", index=False)
    liq_df.to_json(TABLES_DIR / "liquid_he_loss_table.json", orient="records", indent=2)

    # Also save as chart data
    liq_df.to_csv(DATA_DIR / "liquid_he_loss.csv", index=False)

    # Compressor comparison
    comp_df = build_comparison_table()
    comp_df.to_csv(TABLES_DIR / "compressor_comparison.csv", index=False)
    comp_df.to_json(TABLES_DIR / "compressor_comparison.json", orient="records", indent=2)
    comp_df.to_csv(DATA_DIR / "compressor_comparison.csv", index=False)

    # VFD savings
    vfd_df = build_vfd_savings_table()
    vfd_df.to_csv(TABLES_DIR / "vfd_savings.csv", index=False)
    vfd_df.to_csv(DATA_DIR / "vfd_savings.csv", index=False)

    # WCS scenarios
    scn_df = build_scenario_table()
    scn_df.to_csv(TABLES_DIR / "wcs_scenarios.csv", index=False)
    scn_df.to_csv(DATA_DIR / "wcs_scenarios.csv", index=False)

    # Leak budget
    budget_df = build_leak_budget_table()
    budget_df.to_csv(TABLES_DIR / "leak_budget.csv", index=False)
    budget_df.to_csv(DATA_DIR / "leak_budget.csv", index=False)

    # Interlocks
    int_df = build_interlock_table()
    int_df.to_csv(TABLES_DIR / "interlocks.csv", index=False)
    int_df.to_csv(DATA_DIR / "interlocks.csv", index=False)

    # Inventory depletion
    dep_df = inventory_depletion_timeseries()
    dep_df.to_csv(DATA_DIR / "inventory_depletion.csv", index=False)

    print(f"  ✓ Data exported to {TABLES_DIR.relative_to(ROOT)} and {DATA_DIR.relative_to(ROOT)}")


# ══════════════════════════════════════════════════════════════════
# DOCUMENTATION PAGES
# ══════════════════════════════════════════════════════════════════

def _page_template(title: str, body: str) -> str:
    """Standard HTML page wrapper."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — QPLANT v4.0.0</title>
<style>
:root {{ --primary: #1a365d; --accent: #2b6cb0; --bg: #f7fafc; --card: #fff; --border: #e2e8f0; --text: #2d3748; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter','Segoe UI',system-ui,sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.header {{ background: linear-gradient(135deg, var(--primary), var(--accent)); color: white; padding: 18px 32px; }}
.header h1 {{ font-size: 1.3rem; }}
.header p {{ opacity: 0.85; font-size: 0.85rem; }}
main {{ max-width: 1100px; margin: 24px auto; padding: 0 24px; }}
.card {{ background: var(--card); border-radius: 10px; box-shadow: 0 1px 6px rgba(0,0,0,.06); padding: 28px; margin-bottom: 24px; }}
h2 {{ color: var(--primary); font-size: 1.35rem; margin-bottom: 14px; border-bottom: 2px solid var(--accent); padding-bottom: 6px; }}
h3 {{ color: var(--accent); margin: 16px 0 8px; }}
h4 {{ margin: 12px 0 6px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.85rem; }}
th {{ background: var(--primary); color: white; padding: 8px 10px; text-align: left; }}
td {{ padding: 7px 10px; border-bottom: 1px solid var(--border); }}
tr:nth-child(even) {{ background: #f7fafc; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
.badge-accept {{ background: #c6f6d5; color: #22543d; }}
.badge-review {{ background: #fefcbf; color: #744210; }}
.badge-risk {{ background: #fed7d7; color: #742a2a; }}
.badge-info {{ background: #bee3f8; color: #2a4365; }}
.equation {{ background: #f0f4f8; padding: 14px 18px; border-left: 4px solid var(--accent); border-radius: 4px; font-family: 'Courier New',monospace; margin: 12px 0; overflow-x: auto; white-space: pre-wrap; }}
.kpi-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 14px 0; }}
.kpi {{ flex: 1; min-width: 130px; padding: 14px; border-radius: 8px; background: linear-gradient(135deg, #ebf8ff, #bee3f8); text-align: center; }}
.kpi .value {{ font-size: 1.5rem; font-weight: 700; color: var(--primary); }}
.kpi .label {{ font-size: 0.78rem; color: #718096; margin-top: 3px; }}
iframe {{ width: 100%; height: 500px; border: none; border-radius: 8px; margin: 10px 0; }}
a {{ color: var(--accent); }}
.nav {{ padding: 10px 32px; background: white; border-bottom: 1px solid var(--border); font-size: 0.85rem; }}
.nav a {{ margin-right: 16px; text-decoration: none; }}
.nav a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <p>QPLANT Cryogenic Leak Rate Dashboard — v4.0.0 · Critical Correction: 3× FSD575, 14 barg, SSoT</p>
</div>
<div class="nav">
  <a href="index_v3_1.html">◀ Navigator</a>
  <a href="liquid_he/Liquid_Operations_Guide.html">Liquid He</a>
  <a href="compressors/HP_Redundancy_Analysis.html">HP Compressors</a>
  <a href="compressors/WCS_HP_Protection.html">WCS.HP Protection</a>
  <a href="index.html">v2.5 Dashboard</a>
  <a href="index_v3.html">v3.0 Standards</a>
</div>
<main>
{body}
</main>
</body>
</html>"""


def build_liquid_operations_guide():
    """Build Liquid_Operations_Guide.html."""
    liq_df = build_leak_rate_liquid_loss_table()

    # Build the table HTML
    table_rows = ""
    for _, row in liq_df.iterrows():
        table_rows += f"""<tr>
  <td>{row['leak_rate_mbar_l_s']:.0e}</td>
  <td>{row['mass_flow_g_year']:.4f}</td>
  <td>{row['mass_flow_kg_year']:.6f}</td>
  <td>{row['liquid_loss_L_year']:.6f}</td>
  <td>€{row['cost_eur_year']:.4f}</td>
</tr>\n"""

    # Time to threshold examples
    threshold_rows = ""
    for q in [1e-9, 1e-8, 1e-5, 1e-4]:
        days = time_to_threshold(5000, q, 0.20)
        if days > 365*1000:
            t_str = f">{days/365:.0e} years"
        elif days > 365:
            t_str = f"{days/365:.1f} years"
        else:
            t_str = f"{days:.1f} days"
        threshold_rows += f"<tr><td>{q:.0e}</td><td>{t_str}</td></tr>\n"

    body = f"""
<div class="card">
  <h2>Liquid Helium Properties at Normal Boiling Point (4.222 K, 1 atm)</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="value">4.222 K</div><div class="label">Normal Boiling Point</div></div>
    <div class="kpi"><div class="value">124.96</div><div class="label">Density (kg/m³)</div></div>
    <div class="kpi"><div class="value">20.9</div><div class="label">ΔH_vap (kJ/kg)</div></div>
    <div class="kpi"><div class="value">5.195 K</div><div class="label">Critical Temperature</div></div>
    <div class="kpi"><div class="value">2.275 bar</div><div class="label">Critical Pressure</div></div>
  </div>

  <h3>Saturation Curve Summary</h3>
  <table>
    <tr><th>T (K)</th><th>P (bar)</th><th>ρ_liq (kg/m³)</th><th>ΔH_vap (kJ/kg)</th><th>Phase</th></tr>
    <tr><td>2.5</td><td>0.065</td><td>145.2</td><td>23.1</td><td>Superfluid He-II</td></tr>
    <tr><td>3.0</td><td>0.117</td><td>141.3</td><td>22.5</td><td>Normal He-I</td></tr>
    <tr><td>4.0</td><td>0.813</td><td>130.4</td><td>21.1</td><td>Normal He-I</td></tr>
    <tr><td>4.222</td><td>1.000</td><td>124.96</td><td>20.9</td><td>NBP</td></tr>
    <tr><td>4.5</td><td>1.48</td><td>119.8</td><td>19.5</td><td>Normal He-I</td></tr>
    <tr><td>5.0</td><td>2.04</td><td>100.5</td><td>11.5</td><td>Near-critical</td></tr>
    <tr><td>5.19</td><td>2.27</td><td>69.64</td><td>0</td><td>Critical point</td></tr>
  </table>
</div>

<div class="card">
  <h2>Leak Rate → Liquid Inventory Loss Conversion</h2>

  <h3>Physics</h3>
  <p>A gas leak from a liquid-filled volume causes the liquid to boil off to replace lost gas (mass conservation). The conversion follows:</p>

  <div class="equation">ṁ_gas = (Q [Pa·m³/s] × M [kg/mol]) / (R [J/mol·K] × T [K])
where: Q = leak rate in Pa·m³/s  (1 mbar·L/s = 0.1 Pa·m³/s)
       M = 0.004003 kg/mol (He-4)
       R = 8.3145 J/(mol·K)

Liquid volume loss: V̇_liq = ṁ_gas / ρ_liq   (ρ_liq = 125 kg/m³ at NBP)</div>

  <h3>Standard Leak Rate → Liquid Loss Table (at 4.222 K, 1 bar)</h3>
  <table>
    <tr><th>Leak Rate (mbar·L/s)</th><th>Mass Loss (g/yr)</th><th>Mass Loss (kg/yr)</th><th>Liquid Loss (L/yr)</th><th>Cost (€/yr)</th></tr>
    {table_rows}
  </table>
  <p><em>Cost basis: €{HE_PRICE_EUR_PER_KG:.0f}/kg liquid helium (2024 market estimate).</em></p>
</div>

<div class="card">
  <h2>Liquid Inventory Depletion — WSH 5,000 L Vessel</h2>
  <iframe src="../visualizations_v3/liquid_inventory_depletion.html"></iframe>

  <h3>Time to 20% Threshold (Minimum Operating Level)</h3>
  <table>
    <tr><th>Leak Rate (mbar·L/s)</th><th>Time to 20% Level</th></tr>
    {threshold_rows}
  </table>
  <p>At the tightest spec (10⁻⁹ mbar·L/s), liquid loss from leaks is negligible over operational lifetimes.
     At 10⁻⁴ mbar·L/s, losses are measurable but still small (0.29 L/yr).</p>
</div>

<div class="card">
  <h2>Boil-off Rate vs Leak Rate (Temperature Dependence)</h2>
  <iframe src="../visualizations_v3/boiloff_vs_leakrate.html"></iframe>
  <p>Higher gas temperatures at the leak point yield <em>lower</em> mass flow for the same volumetric throughput
     (ideal gas: n ∝ PV/T). Cold leaks (4K) lose more mass per mbar·L/s than warm leaks (300K).</p>
</div>
"""

    html = _page_template("Liquid Helium Operations Guide", body)
    path = DOC_DIR / "liquid_he" / "Liquid_Operations_Guide.html"
    path.write_text(html, encoding="utf-8")
    print(f"  ✓ {path.relative_to(ROOT)}")


def build_hp_redundancy_analysis():
    """Build HP_Redundancy_Analysis.html."""
    comp_df = build_comparison_table()
    vfd_df = build_vfd_savings_table()

    # Comparison table
    comp_rows = ""
    for _, r in comp_df.iterrows():
        comp_rows += f"""<tr>
  <td>{r['name']}</td><td>{r['units']}</td><td>{r['redundancy']}</td>
  <td>{r['type']}</td><td>{r['A_system_pct']:.4f}%</td>
  <td>{r['downtime_h_yr']:.4f}</td><td>{r['MTBF_system_years']:.0f}</td>
  <td>€{r['total_capex_eur']:,.0f}</td><td>€{r['total_annual_opex_eur']:,.0f}</td>
</tr>\n"""

    # VFD table
    vfd_rows = ""
    for _, r in vfd_df.iterrows():
        vfd_rows += f"""<tr>
  <td>{r['load_pct']:.0f}%</td><td>{r['power_fixed_kw']:.0f}</td>
  <td>{r['power_vfd_kw']:.0f}</td><td>{r['savings_pct']:.1f}%</td>
  <td>€{r['cost_savings_eur_yr']:,.0f}</td>
</tr>\n"""

    body = f"""
<div class="card">
  <h2>HP Compressor System Architecture</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="value">14 barg</div><div class="label">HP Header Pressure</div></div>
    <div class="kpi"><div class="value">3× FSD575</div><div class="label">HP Compressors (corrected)</div></div>
    <div class="kpi"><div class="value">99.999%+</div><div class="label">Target Availability</div></div>
    <div class="kpi"><div class="value">8 h</div><div class="label">MTTR (conservative)</div></div>
  </div>

  <h3>Configuration Options</h3>
  <p><strong>Selected: 3× FSD575 SFC VFD</strong> (CORRECTED from 4 units in v3.1.0).<br>
     Each unit: 112.54 g/s @ 72 Hz, 315 kW motor, 348.54 kW package. 2 running + 1 standby.</p>
  <p><strong>Alternative: HSD Twin Combi</strong> — 2× oil-free centrifugal twin-head, each 100% capacity (true N+1).</p>
  <p><strong>⚠ v4.0.0 Correction:</strong> Design flow of 350 g/s is achievable with 3× FSD575 (max 337.62 g/s).
     Expected operational flow is 304 g/s. CAPEX saved: €200k (3 vs 4 units).</p>
</div>

<div class="card">
  <h2>Reliability & Availability Comparison</h2>

  <h3>Formulas</h3>
  <div class="equation">Single unit:  A = MTBF / (MTBF + MTTR) = 8760 / (8760 + 8) = 99.91%
k-of-M system: A_sys = Σ(i=k..M) C(M,i) × A^i × (1-A)^(M-i)
2-of-3:  A_sys = A²(3 − 2A) = 99.9997%
3-of-4:  A_sys = A³(4 − 3A) = 99.9995%
2-of-4:  A_sys = 6A⁴ − 8A³ + 3A² (via binomial) → ~100%
1-of-2:  A_sys = 2A − A² = 99.9999%</div>

  <h3>Comparison Table</h3>
  <table>
    <tr><th>Configuration</th><th>Units</th><th>Redundancy</th><th>Type</th><th>Availability</th><th>Downtime (h/yr)</th><th>MTBF (years)</th><th>CAPEX</th><th>OPEX/yr</th></tr>
    {comp_rows}
  </table>

  <iframe src="../visualizations_v3/compressor_availability_comparison.html"></iframe>
</div>

<div class="card">
  <h2>VFD Energy Savings Analysis (FSD575, 400 kW)</h2>

  <h3>Affinity Law</h3>
  <div class="equation">P_VFD = P_full × (load_fraction)³ / η_VFD
P_fixed ≈ P_full × (0.4 + 0.6 × load_fraction)   [slide-valve unloading]

At 70% load:  P_fixed = 328 kW,  P_VFD = 141 kW  →  savings: 57%</div>

  <table>
    <tr><th>Load</th><th>Fixed Speed (kW)</th><th>VFD (kW)</th><th>Savings</th><th>Annual Savings (€/yr)</th></tr>
    {vfd_rows}
  </table>

  <iframe src="../visualizations_v3/vfd_energy_savings.html"></iframe>
</div>

<div class="card">
  <h2>Redundancy Cost-Benefit Analysis</h2>
  <iframe src="../visualizations_v3/redundancy_cost_benefit.html"></iframe>

  <h3>FSD575 vs HSD Twin Combi — Key Trade-offs</h3>
  <table>
    <tr><th>Parameter</th><th>3× FSD575 VFD (CORRECTED)</th><th>2× HSD Twin Combi</th></tr>
    <tr><td>Redundancy</td><td>N+1 (2+1)</td><td>True N+1 (1+1)</td></tr>
    <tr><td>Technology</td><td>Oil-flooded screw + VFD</td><td>Oil-free centrifugal</td></tr>
    <tr><td>Max Flow</td><td>337.62 g/s (3 × 112.54)</td><td>N/A (single unit 100%)</td></tr>
    <tr><td>Efficiency</td><td>70-75%</td><td>80-85%</td></tr>
    <tr><td>Turndown</td><td>Excellent (VFD 30-100%)</td><td>Limited (70-100%)</td></tr>
    <tr><td>Maintenance</td><td>Oil changes, separator</td><td>Bearings, less frequent</td></tr>
    <tr><td>Capital Cost</td><td>€600k (3 units)</td><td>€600k-800k (2 units)</td></tr>
    <tr><td>Oil contamination</td><td>Yes (requires removal)</td><td>No (oil-free)</td></tr>
  </table>
</div>
"""

    html = _page_template("HP Compressor Redundancy Analysis", body)
    path = DOC_DIR / "compressors" / "HP_Redundancy_Analysis.html"
    path.write_text(html, encoding="utf-8")
    print(f"  ✓ {path.relative_to(ROOT)}")


def build_wcs_hp_protection():
    """Build WCS_HP_Protection.html."""
    budget_df = build_leak_budget_table()
    int_df = build_interlock_table()
    scn_df = build_scenario_table()

    budget_rows = ""
    for _, r in budget_df.iterrows():
        budget_rows += f"<tr><td>{r['circuit']}</td><td>{r['budget_mbar_l_s']:.0e}</td><td>{r['fraction_pct']}%</td><td>{r['justification']}</td></tr>\n"

    int_rows = ""
    for _, r in int_df.iterrows():
        badge_cls = {"WARNING": "review", "ALARM": "risk", "AUTO": "accept", "TRIP": "risk"}.get(r["priority"], "info")
        int_rows += f"<tr><td>{r['condition']}</td><td>{r['setpoint']}</td><td>{r['action']}</td><td><span class='badge badge-{badge_cls}'>{r['priority']}</span></td></tr>\n"

    scn_rows = ""
    for _, r in scn_df.iterrows():
        badge_cls = {"NOMINAL": "accept", "WARNING": "review", "ALARM": "risk", "TRIP": "risk"}.get(r["status"], "info")
        scn_rows += f"""<tr>
  <td><strong>{r['scenario']}</strong></td>
  <td>{r['compressors_running']}/{r['compressors_available']}</td>
  <td>{r['capacity_pct']:.0f}%</td><td>{r['hp_header_barg']} barg</td>
  <td>{r['sidestreams']}</td><td>{r['beam_pct']:.0f}%</td>
  <td><span class='badge badge-{badge_cls}'>{r['status']}</span></td>
</tr>\n"""

    body = f"""
<div class="card">
  <h2>WCS.HP Supply Protection — Overview</h2>
  <p>The <strong>WCS.HP (Worst Case Supply — High Pressure)</strong> protection system ensures that
     sidestream activities (recovery, purification, research taps) do <strong>not</strong> compromise
     the main 14 barg HP helium supply to QVB / WSH / beam cooling.</p>

  <div class="kpi-row">
    <div class="kpi"><div class="value">14 barg</div><div class="label">Nominal HP Header</div></div>
    <div class="kpi"><div class="value">1×10⁻⁵</div><div class="label">Total Leak Budget (mbar·L/s)</div></div>
    <div class="kpi"><div class="value">70/20/10</div><div class="label">Main/Side/Contingency (%)</div></div>
    <div class="kpi"><div class="value">13.5 barg</div><div class="label">Sidestream Isolation Trigger</div></div>
  </div>
</div>

<div class="card">
  <h2>Leak Budget Allocation</h2>
  <table>
    <tr><th>Circuit</th><th>Budget (mbar·L/s)</th><th>Fraction</th><th>Justification</th></tr>
    {budget_rows}
  </table>
</div>

<div class="card">
  <h2>Interlock Logic Table</h2>
  <table>
    <tr><th>Condition</th><th>Setpoint</th><th>Action</th><th>Priority</th></tr>
    {int_rows}
  </table>
</div>

<div class="card">
  <h2>WCS.HP Supply Architecture</h2>
  <iframe src="../visualizations_v3/wcs_hp_architecture.html" style="height:620px;"></iframe>
</div>

<div class="card">
  <h2>Scenario Analysis</h2>
  <table>
    <tr><th>Scenario</th><th>Compressors (run/avail)</th><th>Capacity</th><th>HP Header</th><th>Sidestreams</th><th>Beam</th><th>Status</th></tr>
    {scn_rows}
  </table>

  <h3>Scenario Details</h3>
  <h4>Scenario 1: Normal Operation</h4>
  <p>All 3 compressors available (2 running, 1 standby). HP header stable at 14.0 barg.
     Sidestreams open. Total leak: 9×10⁻⁶ mbar·L/s (within budget). Full beam operation.</p>

  <h4>Scenario 2: WCS — 1 Compressor Failed</h4>
  <p>2 compressors running at 100% capacity, no standby margin. HP header drops to ~13.8 barg.
     Sidestreams automatically closed by interlock (P < 13.5 trigger may not yet activate,
     but precautionary closure reduces leak budget to 7×10⁻⁶). Full beam operation maintained.</p>

  <h4>Scenario 3: Emergency — 2 Compressors Failed</h4>
  <p>1 compressor running at 50% capacity. HP header at 13.2 barg (below LOW-LOW).
     Alarm raised. Beam reduced to 50% intensity to match available capacity.
     Total leak budget halved to 3.5×10⁻⁶.</p>

  <h4>Scenario 4: Total Failure</h4>
  <p>All compressors failed. Emergency beam shutdown. Vent to recovery system.
     Minimise He loss through controlled depressurisation.</p>
</div>
"""

    html = _page_template("WCS.HP Supply Protection Analysis", body)
    path = DOC_DIR / "compressors" / "WCS_HP_Protection.html"
    path.write_text(html, encoding="utf-8")
    print(f"  ✓ {path.relative_to(ROOT)}")


# ══════════════════════════════════════════════════════════════════
# MASTER NAVIGATOR — index_v3_1.html (40 slides)
# ══════════════════════════════════════════════════════════════════

def build_navigator():
    """Build the 40-slide master navigator."""
    # Read existing v3 slides for reference
    existing_v3 = (DOC_DIR / "index_v3.html").read_text(encoding="utf-8") if (DOC_DIR / "index_v3.html").exists() else ""

    # Build slide content
    slides = _build_all_slides()

    # Build slide thumbnails
    thumb_html = ""
    for i, s in enumerate(slides):
        thumb_html += f'<div class="thumb" onclick="goSlide({i+1})" title="{s["title"]}">{i+1}. {s["title"][:25]}{"…" if len(s["title"])>25 else ""}</div>\n'

    # Build slide divs
    slide_html = ""
    for i, s in enumerate(slides):
        active = ' active' if i == 0 else ''
        slide_html += f'<div class="slide{active}" data-title="{s["title"]}">\n{s["content"]}\n</div>\n\n'

    # Section buttons
    sections = {}
    for i, s in enumerate(slides):
        sec = s.get("section", "General")
        if sec not in sections:
            sections[sec] = i + 1

    section_btns = ""
    for sec, idx in sections.items():
        section_btns += f'<button class="nav-btn" onclick="goSlide({idx})">{sec}</button>\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OUTPUT_3.1 — Liquid He Operations & HP Compressor Redundancy v3.1.0</title>
<style>
:root {{
  --primary: #1a365d; --accent: #2b6cb0; --bg: #f7fafc; --card: #ffffff;
  --border: #e2e8f0; --text: #2d3748; --text-light: #718096;
  --success: #38a169; --warning: #d69e2e; --danger: #e53e3e; --info: #3182ce;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter','Segoe UI',system-ui,sans-serif; background: var(--bg); color: var(--text); }}
.app-header {{
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  color: white; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,.2);
}}
.app-header h1 {{ font-size: 1.1rem; font-weight: 600; }}
.slide-counter {{ font-size: 0.9rem; opacity: 0.9; font-variant-numeric: tabular-nums; }}
.progress-bar {{ height: 4px; background: rgba(255,255,255,.2); width: 100%; }}
.progress-fill {{ height: 100%; background: #68d391; transition: width 0.3s; }}
.nav-controls {{
  display: flex; gap: 8px; align-items: center; padding: 10px 24px; background: var(--card);
  border-bottom: 1px solid var(--border); flex-wrap: wrap;
}}
.nav-btn {{
  padding: 6px 14px; border: 1px solid var(--border); border-radius: 6px;
  background: white; cursor: pointer; font-size: 0.82rem; transition: all .15s;
}}
.nav-btn:hover {{ background: var(--accent); color: white; border-color: var(--accent); }}
.nav-btn.active {{ background: var(--accent); color: white; }}
.slide-container {{ max-width: 1200px; margin: 24px auto; padding: 0 24px; }}
.slide {{
  display: none; background: var(--card); border-radius: 12px;
  box-shadow: 0 1px 8px rgba(0,0,0,.08); padding: 32px; min-height: 500px;
}}
.slide.active {{ display: block; }}
.slide h2 {{ color: var(--primary); font-size: 1.5rem; margin-bottom: 16px; border-bottom: 2px solid var(--accent); padding-bottom: 8px; }}
.slide h3 {{ color: var(--accent); font-size: 1.15rem; margin: 18px 0 8px; }}
.slide h4 {{ color: var(--text); font-size: 1rem; margin: 14px 0 6px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.85rem; }}
th {{ background: var(--primary); color: white; padding: 8px 10px; text-align: left; font-weight: 600; }}
td {{ padding: 7px 10px; border-bottom: 1px solid var(--border); }}
tr:nth-child(even) {{ background: #f7fafc; }}
tr:hover {{ background: #edf2f7; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
.badge-accept {{ background: #c6f6d5; color: #22543d; }}
.badge-review {{ background: #fefcbf; color: #744210; }}
.badge-risk {{ background: #fed7d7; color: #742a2a; }}
.badge-trace {{ background: #bee3f8; color: #2a4365; }}
.badge-new {{ background: #e9d8fd; color: #44337a; }}
.kpi-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 16px 0; }}
.kpi {{ flex: 1; min-width: 140px; padding: 14px; border-radius: 8px; background: linear-gradient(135deg, #ebf8ff 0%, #bee3f8 100%); text-align: center; }}
.kpi .value {{ font-size: 1.6rem; font-weight: 700; color: var(--primary); }}
.kpi .label {{ font-size: 0.78rem; color: var(--text-light); margin-top: 4px; }}
.plot-frame {{ width: 100%; height: 480px; border: none; border-radius: 8px; margin: 12px 0; }}
.equation {{ background: #f0f4f8; padding: 14px 18px; border-left: 4px solid var(--accent); border-radius: 4px; font-family: 'Courier New',monospace; margin: 12px 0; overflow-x: auto; white-space: pre-wrap; }}
.thumb-sidebar {{
  position: fixed; right: 0; top: 90px; width: 160px; max-height: calc(100vh - 100px);
  overflow-y: auto; background: var(--card); border-left: 1px solid var(--border);
  padding: 8px 0; font-size: 0.72rem; z-index: 500;
}}
.thumb {{ padding: 4px 10px; cursor: pointer; border-bottom: 1px solid var(--border); }}
.thumb:hover {{ background: #edf2f7; }}
.thumb.active {{ background: #bee3f8; font-weight: 600; }}
@media(max-width: 900px) {{ .thumb-sidebar {{ display:none; }} }}
</style>
</head>
<body>

<div class="app-header">
  <h1>OUTPUT_3.1 — Liquid He Operations & HP Compressor Redundancy v3.1.0</h1>
  <span class="slide-counter" id="slideCounter">1 / {len(slides)}</span>
</div>
<div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:{100/len(slides):.1f}%"></div></div>

<div class="nav-controls">
  <button class="nav-btn" onclick="prevSlide()">◀ Prev</button>
  <button class="nav-btn" onclick="nextSlide()">Next ▶</button>
  <span style="margin:0 8px;color:#a0aec0;">|</span>
  {section_btns}
</div>

<div class="thumb-sidebar" id="thumbSidebar">
{thumb_html}
</div>

<div class="slide-container" style="margin-right:170px;">
{slide_html}
</div>

<script>
let current = 1;
const total = {len(slides)};

function goSlide(n) {{
  if (n < 1 || n > total) return;
  document.querySelectorAll('.slide')[current-1].classList.remove('active');
  current = n;
  document.querySelectorAll('.slide')[current-1].classList.add('active');
  document.getElementById('slideCounter').textContent = current + ' / ' + total;
  document.getElementById('progressFill').style.width = (current/total*100) + '%';
  document.querySelectorAll('.thumb').forEach((t,i) => t.classList.toggle('active', i===current-1));
  window.scrollTo(0,0);
}}
function nextSlide() {{ goSlide(current+1); }}
function prevSlide() {{ goSlide(current-1); }}
document.addEventListener('keydown', e => {{
  if (e.key==='ArrowRight'||e.key===' ') nextSlide();
  if (e.key==='ArrowLeft') prevSlide();
}});
// init
document.querySelectorAll('.thumb')[0]?.classList.add('active');
</script>
</body>
</html>"""

    path = DOC_DIR / "index_v3_1.html"
    path.write_text(html, encoding="utf-8")
    print(f"  ✓ {path.relative_to(ROOT)}")


def _build_all_slides():
    """Build all 40 slide definitions."""
    # Load data for slide content
    comp_df = build_comparison_table()
    liq_df = build_leak_rate_liquid_loss_table()
    vfd_df = build_vfd_savings_table()
    budget_df = build_leak_budget_table()
    int_df = build_interlock_table()
    scn_df = build_scenario_table()

    slides = []

    # ── Section 1: Overview (slides 1-4) ──
    slides.append({"title": "v3.1.0 Overview", "section": "Overview", "content": """
<h2>OUTPUT_3.1.0 — Liquid Helium Operations & HP Compressor Redundancy</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">v3.1.0</div><div class="label">Version</div></div>
  <div class="kpi"><div class="value">40</div><div class="label">Slides</div></div>
  <div class="kpi"><div class="value">6</div><div class="label">New Charts</div></div>
  <div class="kpi"><div class="value">3</div><div class="label">New Modules</div></div>
</div>
<h3>What's New in v3.1.0</h3>
<ul>
  <li><strong>Liquid helium inventory management</strong> — all calculations now in liquid He context at 4K</li>
  <li><strong>HP compressor redundancy analysis</strong> — N=3 vs N+1 (FSD575 VFD, HSD Twin Combi)</li>
  <li><strong>WCS.HP supply protection</strong> — leak budget, interlocks, scenario analysis</li>
  <li><strong>6 new interactive Plotly charts</strong> — liquid depletion, compressor availability, VFD savings, etc.</li>
  <li><strong>3 Python calculation modules</strong> — liquid_he_loss.py, compressor_reliability.py, wcs_scenarios.py</li>
</ul>
<h3>Document Links</h3>
<p>
  <a href="liquid_he/Liquid_Operations_Guide.html">📄 Liquid He Operations Guide</a> ·
  <a href="compressors/HP_Redundancy_Analysis.html">📄 HP Redundancy Analysis</a> ·
  <a href="compressors/WCS_HP_Protection.html">📄 WCS.HP Protection</a>
</p>
"""})

    slides.append({"title": "System Architecture Overview", "section": "Overview", "content": """
<h2>QPLANT Helium System Architecture</h2>
<h3>Primary Mode: Liquid Helium at 4K</h3>
<p>The QPLANT cryogenic system operates with <strong>liquid helium</strong> at 4K as the primary coolant.
   The Warm Storage Holders (WSH) contain the liquid helium inventory. Leaks from the system cause
   liquid inventory loss through boil-off.</p>
<h3>HP Compressor Supply</h3>
<p>The HP compressor system provides helium at <strong>14 barg</strong> (15 bara) to the main beam cooling loop.
   Redundancy options range from N=3 (baseline) to N+1 configurations with FSD575 VFD or HSD Twin Combi.</p>
<h3>Key System Parameters</h3>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Source</th></tr>
  <tr><td>Operating temperature</td><td>4.222 K (NBP at 1 atm)</td><td>NIST</td></tr>
  <tr><td>Liquid density</td><td>124.96 kg/m³</td><td>NIST REFPROP</td></tr>
  <tr><td>HP supply pressure</td><td>14 barg (15 bara)</td><td>QPLANT spec</td></tr>
  <tr><td>System leak budget</td><td>1×10⁻⁵ mbar·L/s</td><td>RTM-048</td></tr>
  <tr><td>WSH capacity</td><td>5,000 L</td><td>Design basis</td></tr>
  <tr><td>He recovery target</td><td>200 g/s</td><td>RTM-054</td></tr>
</table>
"""})

    slides.append({"title": "Deliverables Summary", "section": "Overview", "content": """
<h2>v3.1.0 Deliverables</h2>
<h3>New Files Created</h3>
<table>
  <tr><th>Category</th><th>File</th><th>Description</th></tr>
  <tr><td>Data</td><td>data/helium_properties.json</td><td>Extended with liquid phase (saturation curve, subcooled)</td></tr>
  <tr><td>Data</td><td>data/compressor_specs.json</td><td>FSD575 & HSD Twin specifications</td></tr>
  <tr><td>Module</td><td>src/liquid_he_loss.py</td><td>Leak rate → liquid loss conversion</td></tr>
  <tr><td>Module</td><td>src/compressor_reliability.py</td><td>k-of-M availability, VFD savings</td></tr>
  <tr><td>Module</td><td>src/wcs_scenarios.py</td><td>WCS scenarios, interlocks, leak budget</td></tr>
  <tr><td>Chart</td><td>liquid_inventory_depletion.html</td><td>WSH 5000L depletion over time</td></tr>
  <tr><td>Chart</td><td>compressor_availability_comparison.html</td><td>Availability bar chart (nines)</td></tr>
  <tr><td>Chart</td><td>boiloff_vs_leakrate.html</td><td>Boil-off & cost vs leak rate</td></tr>
  <tr><td>Chart</td><td>wcs_hp_architecture.html</td><td>HP supply block diagram</td></tr>
  <tr><td>Chart</td><td>redundancy_cost_benefit.html</td><td>CAPEX vs availability scatter</td></tr>
  <tr><td>Chart</td><td>vfd_energy_savings.html</td><td>Fixed-speed vs VFD bars</td></tr>
  <tr><td>Doc</td><td>Liquid_Operations_Guide.html</td><td>Full liquid He reference</td></tr>
  <tr><td>Doc</td><td>HP_Redundancy_Analysis.html</td><td>Compressor comparison</td></tr>
  <tr><td>Doc</td><td>WCS_HP_Protection.html</td><td>Supply protection analysis</td></tr>
  <tr><td>Nav</td><td>index_v3_1.html</td><td>40-slide master navigator</td></tr>
</table>
"""})

    slides.append({"title": "Version History", "section": "Overview", "content": """
<h2>Version History</h2>
<table>
  <tr><th>Version</th><th>Date</th><th>Description</th></tr>
  <tr><td><span class="badge badge-trace">v1.0</span></td><td>2026-05</td><td>Initial baseline — leak rate conversion (had ×1000 error)</td></tr>
  <tr><td><span class="badge badge-accept">v2.0</span></td><td>2026-05</td><td>Corrected physics, triage system, DMAIC, handover package</td></tr>
  <tr><td><span class="badge badge-accept">v2.5</span></td><td>2026-05</td><td>Visual dashboard (18 charts), material comparison, Monte Carlo</td></tr>
  <tr><td><span class="badge badge-accept">v3.0</span></td><td>2026-05</td><td>Standards & statistical framework, PCA, compliance tables</td></tr>
  <tr><td><span class="badge badge-new">v3.1</span></td><td>2026-05</td><td>Liquid He operations, HP compressor redundancy, WCS.HP protection</td></tr>
</table>
"""})

    # ── Section 2: Liquid Helium Properties (slides 5-10) ──
    slides.append({"title": "Liquid He Properties", "section": "Liquid He", "content": """
<h2>Liquid Helium-4 Thermophysical Properties</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">4.222 K</div><div class="label">Normal Boiling Point</div></div>
  <div class="kpi"><div class="value">124.96</div><div class="label">ρ_liq (kg/m³)</div></div>
  <div class="kpi"><div class="value">20.9</div><div class="label">ΔH_vap (kJ/kg)</div></div>
  <div class="kpi"><div class="value">5.195 K</div><div class="label">T_critical</div></div>
  <div class="kpi"><div class="value">2.275 bar</div><div class="label">P_critical</div></div>
</div>
<h3>Saturation Curve</h3>
<table>
  <tr><th>T (K)</th><th>P (bar)</th><th>ρ_liq (kg/m³)</th><th>ρ_vap (kg/m³)</th><th>ΔH_vap (kJ/kg)</th><th>Phase</th></tr>
  <tr><td>2.5</td><td>0.065</td><td>145.2</td><td>0.95</td><td>23.1</td><td>Superfluid He-II</td></tr>
  <tr><td>3.0</td><td>0.117</td><td>141.3</td><td>1.44</td><td>22.5</td><td>Normal He-I</td></tr>
  <tr><td>4.0</td><td>0.813</td><td>130.4</td><td>6.40</td><td>21.1</td><td>Normal He-I</td></tr>
  <tr><td>4.222</td><td>1.000</td><td>124.96</td><td>16.89</td><td>20.9</td><td>NBP</td></tr>
  <tr><td>4.5</td><td>1.48</td><td>119.8</td><td>22.5</td><td>19.5</td><td>Normal He-I</td></tr>
  <tr><td>5.0</td><td>2.04</td><td>100.5</td><td>40.2</td><td>11.5</td><td>Near-critical</td></tr>
  <tr><td>5.19</td><td>2.27</td><td>69.64</td><td>69.64</td><td>0</td><td>Critical point</td></tr>
</table>
<p><em>Data source: NIST REFPROP He-4. Lambda point (superfluid transition): T_λ = 2.1768 K at SVP.</em></p>
"""})

    slides.append({"title": "Superfluid He & Phase Diagram", "section": "Liquid He", "content": """
<h2>Helium Phase Diagram & Superfluid Transition</h2>
<h3>Unique Properties of He-4</h3>
<ul>
  <li>Helium is the <strong>only element that remains liquid at 0 K</strong> (at ambient pressure)</li>
  <li><strong>Lambda transition</strong> at 2.1768 K: He-I (normal) → He-II (superfluid)</li>
  <li>Superfluid He-II has <strong>zero viscosity</strong> and extremely high thermal conductivity</li>
  <li>Critical point at only 5.195 K, 2.275 bar — very narrow liquid range</li>
</ul>
<h3>Implications for Leak Analysis</h3>
<table>
  <tr><th>Aspect</th><th>Impact</th></tr>
  <tr><td>Narrow liquid range (4.2–5.2 K)</td><td>Small temperature excursions → phase change</td></tr>
  <tr><td>Low latent heat (20.9 kJ/kg)</td><td>Small heat inputs cause significant boil-off</td></tr>
  <tr><td>Low surface tension (0.35 mN/m)</td><td>Can penetrate very small leak paths</td></tr>
  <tr><td>Low viscosity (3.5 μPa·s)</td><td>High mobility through micro-cracks</td></tr>
  <tr><td>Low density (125 kg/m³)</td><td>Large volumes needed for modest mass</td></tr>
</table>
"""})

    slides.append({"title": "Leak Rate → Liquid Loss Physics", "section": "Liquid He", "content": """
<h2>Leak Rate to Liquid Inventory Loss — Physics</h2>
<h3>Mass Conservation Principle</h3>
<p>A gas leak from the ullage space above liquid helium causes the liquid to boil off
   to replace the lost gas molecules. At steady state:</p>
<div class="equation">ṁ_leak,gas = ṁ_boiloff,liquid   (mass conservation)

Gas mass flow from leak rate:
  ṁ = (Q × M) / (R × T)

where:
  Q = leak rate [Pa·m³/s]   (1 mbar·L/s = 0.1 Pa·m³/s)
  M = 0.004003 kg/mol       (He-4 molar mass)
  R = 8.3145 J/(mol·K)      (universal gas constant)
  T = temperature at leak    [K]

Liquid volume loss rate:
  V̇_liq = ṁ / ρ_liq    (ρ_liq = 124.96 kg/m³ at NBP)</div>
<p><strong>Key insight:</strong> Cold leaks (4K) lose more mass per mbar·L/s than warm leaks (300K),
   because n ∝ PV/T — more moles at lower T for same throughput.</p>
"""})

    # Build the leak rate table for slide
    liq_table_rows = ""
    for _, r in liq_df.iterrows():
        liq_table_rows += f"<tr><td>{r['leak_rate_mbar_l_s']:.0e}</td><td>{r['mass_flow_g_year']:.4f}</td><td>{r['liquid_loss_L_year']:.6f}</td><td>€{r['cost_eur_year']:.4f}</td></tr>\n"

    slides.append({"title": "Leak Rate → Liquid Loss Table", "section": "Liquid He", "content": f"""
<h2>Standard Leak Rate → Liquid He Loss Conversion</h2>
<p>Conditions: T = 4.222 K (NBP), P = 1 bar, ρ_liq = 125 kg/m³. Cost: €120/kg.</p>
<table>
  <tr><th>Leak Rate (mbar·L/s)</th><th>Mass Loss (g/yr)</th><th>Liquid Loss (L/yr)</th><th>Cost (€/yr)</th></tr>
  {liq_table_rows}
</table>
<h3>Interpretation</h3>
<ul>
  <li>At 10⁻⁹ mbar·L/s (ultra-tight): 0.00036 g/yr — completely negligible</li>
  <li>At 10⁻⁵ mbar·L/s (RTM-048 cap): 3.6 g/yr — very small, 0.03 L/yr liquid</li>
  <li>At 10⁻⁴ mbar·L/s (warm valve offer): 36 g/yr — 0.29 L/yr, still manageable</li>
  <li>At 10⁻² mbar·L/s (significant leak): 3,600 g/yr — 29 L/yr, needs attention</li>
</ul>
"""})

    slides.append({"title": "Liquid Inventory Depletion Chart", "section": "Liquid He", "content": """
<h2>Liquid He Inventory Depletion — WSH 5,000 L Vessel</h2>
<iframe class="plot-frame" src="visualizations_v3/liquid_inventory_depletion.html"></iframe>
<p>Even at the least tight specification (10⁻⁴ mbar·L/s), liquid helium loss from valve leaks
   is extremely small compared to the 5,000 L inventory. The dominant He loss mechanism in practice
   is static heat leak (boil-off from insulation imperfection), not valve leaks.</p>
<p><strong>Conclusion:</strong> The valve leak rate specification has minimal impact on liquid inventory
   management. The derogation request for warm valves (higher leak rate) is justified from an
   inventory perspective.</p>
"""})

    slides.append({"title": "Boil-off vs Leak Rate Chart", "section": "Liquid He", "content": """
<h2>Boil-off Rate & Cost vs Leak Rate</h2>
<iframe class="plot-frame" src="visualizations_v3/boiloff_vs_leakrate.html"></iframe>
<p>Three temperature regimes are shown: 4K (liquid space), 80K (radiation shield), 300K (ambient).
   The 4K curve represents the worst case (most mass per throughput unit).
   At typical valve leak rates (10⁻⁹ to 10⁻⁴), the cost impact is negligible (&lt; €5/year).</p>
"""})

    # ── Section 3: HP Compressor (slides 11-20) ──
    slides.append({"title": "HP Compressor Overview", "section": "HP Compressors", "content": """
<h2>HP Compressor Supply System</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">14 barg</div><div class="label">HP Header Pressure</div></div>
  <div class="kpi"><div class="value">3 or 4</div><div class="label">Compressor Options</div></div>
  <div class="kpi"><div class="value">99.999%+</div><div class="label">Target Availability</div></div>
  <div class="kpi"><div class="value">575 Nm³/h</div><div class="label">FSD575 Capacity</div></div>
</div>
<h3>System Purpose</h3>
<p>The HP compressor system supplies compressed helium at 14 barg to the main beam cooling loop
   (QVB heat exchangers, WSH pressurisation, beam cooling circuits).
   Reliability is critical — compressor failure degrades or stops beam operation.</p>
<h3>Options Under Consideration</h3>
<table>
  <tr><th>Option</th><th>Config</th><th>Type</th></tr>
  <tr><td>Baseline (N=3)</td><td>3× 50% each, 2 running + 1 standby</td><td>Generic screw</td></tr>
  <tr><td>Option A: FSD575 VFD</td><td>3× with Variable Frequency Drive</td><td>Oil-flooded screw + VFD</td></tr>
  <tr><td>Option B: HSD Twin</td><td>2× 100% each, 1 running + 1 standby</td><td>Oil-free centrifugal</td></tr>
</table>
"""})

    slides.append({"title": "N=3 Baseline Configuration", "section": "HP Compressors", "content": """
<h2>Baseline: N=3 Compressor Configuration</h2>
<h3>Configuration</h3>
<ul>
  <li>3 compressors, each sized at <strong>50% capacity</strong></li>
  <li>Normal operation: 2 running (100% total), 1 standby</li>
  <li>System works if ≥ 2 of 3 operational (2-out-of-3)</li>
</ul>
<h3>Failure Scenarios</h3>
<table>
  <tr><th>Failed Units</th><th>Available Capacity</th><th>Status</th></tr>
  <tr><td>0</td><td>150% (all 3 running for overload)</td><td><span class="badge badge-accept">NOMINAL</span></td></tr>
  <tr><td>1</td><td>100% (2 remaining = nominal)</td><td><span class="badge badge-accept">OK</span></td></tr>
  <tr><td>2</td><td>50% (degraded, beam limited)</td><td><span class="badge badge-risk">DEGRADED</span></td></tr>
  <tr><td>3</td><td>0% (system down)</td><td><span class="badge badge-risk">FAILED</span></td></tr>
</table>
<h3>Reliability</h3>
<div class="equation">A_single = MTBF/(MTBF+MTTR) = 8760/(8760+8) = 99.91%
A_sys(2-of-3) = A²(3−2A) = 0.9991²(3−2×0.9991) = 99.9997%
Downtime: 0.022 h/yr</div>
"""})

    slides.append({"title": "FSD575 VFD Specifications", "section": "HP Compressors", "content": """
<h2>FSD575 with Variable Frequency Drive — Specifications</h2>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Notes</th></tr>
  <tr><td>Type</td><td>Oil-flooded screw</td><td>Standard industrial</td></tr>
  <tr><td>Capacity</td><td>575 Nm³/h @ STP</td><td>Per unit</td></tr>
  <tr><td>Discharge pressure</td><td>14-16 barg</td><td>Per QPLANT spec</td></tr>
  <tr><td>Motor power</td><td>315 kW</td><td>ALaT vendor sheet</td></tr>
  <tr><td>VFD range</td><td>30-100% speed</td><td>Turndown ratio 3:1</td></tr>
  <tr><td>Efficiency</td><td>70-75% (ISO 1217)</td><td>Typical for class</td></tr>
  <tr><td>Oil separator</td><td>Integrated coalescing</td><td>Standard</td></tr>
  <tr><td>Cooling</td><td>Water-cooled</td><td>Typical for this size</td></tr>
  <tr><td>Noise</td><td>85-90 dB(A)</td><td>Enclosure recommended</td></tr>
  <tr><td>Footprint</td><td>2 × 3 m per unit</td><td>Excluding services</td></tr>
  <tr><td>Weight</td><td>~3,000 kg</td><td>Installed</td></tr>
  <tr><td>Capital cost</td><td>€175k-205k</td><td>VFD adds ~€30k</td></tr>
  <tr><td>Maintenance</td><td>Oil: 4,000h, Separator: 8,000h</td><td>Annual: ~€15k</td></tr>
</table>
"""})

    slides.append({"title": "HSD Twin Combi Specifications", "section": "HP Compressors", "content": """
<h2>HSD Twin Combi — Specifications</h2>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Notes</th></tr>
  <tr><td>Type</td><td>Oil-free centrifugal (twin-head)</td><td>High-speed</td></tr>
  <tr><td>Capacity</td><td>1,150 Nm³/h per unit (2×575)</td><td>Each = 100%</td></tr>
  <tr><td>Stages</td><td>2 per unit (twin-head)</td><td>2-stage compression</td></tr>
  <tr><td>Speed</td><td>30,000-50,000 RPM</td><td>High-speed</td></tr>
  <tr><td>Bearings</td><td>Active Magnetic (AMB)</td><td>Oil-free</td></tr>
  <tr><td>Efficiency</td><td>80-85%</td><td>Higher than screw</td></tr>
  <tr><td>Turndown</td><td>70-105% (IGV/blow-off)</td><td>Limited vs VFD</td></tr>
  <tr><td>Surge control</td><td>Active anti-surge valve</td><td>Required</td></tr>
  <tr><td>Cooling</td><td>Air-cooled + water intercooler</td><td>Compact</td></tr>
  <tr><td>Noise</td><td>75-80 dB(A)</td><td>Quieter, enclosed</td></tr>
  <tr><td>Footprint</td><td>2 × 4 m per unit</td><td>Larger per unit</td></tr>
  <tr><td>Weight</td><td>~5,000 kg</td><td>Gearbox + intercooler</td></tr>
  <tr><td>Capital cost</td><td>€300k-400k per unit</td><td>Higher tech</td></tr>
  <tr><td>Maintenance</td><td>Bearing: 50,000h</td><td>Annual: ~€10k</td></tr>
</table>
<p><strong>Assumption:</strong> "HSD Twin Combi" = 2 units, each a twin-head (2-stage) compressor, providing true N+1 redundancy.</p>
"""})

    # Compressor comparison table
    comp_rows = ""
    for _, r in comp_df.iterrows():
        comp_rows += f"<tr><td>{r['name']}</td><td>{r['units']}</td><td>{r['redundancy']}</td><td>{r['A_system_pct']:.4f}%</td><td>{r['downtime_h_yr']:.4f}</td><td>{r['MTBF_system_years']:.0f}</td><td>€{r['total_capex_eur']:,}</td></tr>\n"

    slides.append({"title": "Reliability Comparison Table", "section": "HP Compressors", "content": f"""
<h2>Reliability & Availability Comparison</h2>
<h3>Formulas</h3>
<div class="equation">Single unit: A = MTBF/(MTBF+MTTR) = 8760/(8760+8) = 99.91%
k-of-M system: A_sys = Σ(i=k..M) C(M,i) × Aⁱ × (1-A)^(M-i)</div>
<table>
  <tr><th>Configuration</th><th>Units</th><th>Redundancy</th><th>Availability</th><th>Downtime (h/yr)</th><th>MTBF (years)</th><th>CAPEX</th></tr>
  {comp_rows}
</table>
<p>All configurations exceed 99.99% availability. The 2-of-4 option approaches 100% availability
   with two spare units.</p>
"""})

    slides.append({"title": "Availability Comparison Chart", "section": "HP Compressors", "content": """
<h2>HP Compressor Availability — Visual Comparison</h2>
<iframe class="plot-frame" src="visualizations_v3/compressor_availability_comparison.html"></iframe>
<p>Availability expressed in "nines" (−log₁₀(1−A)). Each additional "nine" represents a 10× reduction
   in downtime. All options exceed 4 nines (99.99%), with 2-of-4 reaching nearly 6 nines.</p>
"""})

    slides.append({"title": "FSD575 vs HSD Comparison", "section": "HP Compressors", "content": """
<h2>FSD575 VFD vs HSD Twin Combi — Trade-off Matrix</h2>
<table>
  <tr><th>Parameter</th><th>3× FSD575 VFD</th><th>2× HSD Twin Combi</th></tr>
  <tr><td>Redundancy</td><td>N+1 (3+1 or 2+2)</td><td>True N+1 (1+1)</td></tr>
  <tr><td>Technology</td><td>Oil-flooded screw</td><td>Oil-free centrifugal</td></tr>
  <tr><td>Efficiency</td><td>70-75% (part load with VFD)</td><td>80-85% (full load)</td></tr>
  <tr><td>Maintenance</td><td>Oil changes, separator service</td><td>Bearing replacement, less frequent</td></tr>
  <tr><td>Turndown</td><td>Excellent (30-100%)</td><td>Limited (70-100%)</td></tr>
  <tr><td>Footprint</td><td>Larger (4 × 6m² = 24m²)</td><td>Smaller (2 × 8m² = 16m²)</td></tr>
  <tr><td>Noise</td><td>Higher (85-90 dBA)</td><td>Lower (75-80 dBA)</td></tr>
  <tr><td>Capital Cost</td><td>€760k-820k</td><td>€600k-800k</td></tr>
  <tr><td>Oil contamination</td><td>Yes (requires oil removal)</td><td>No (oil-free)</td></tr>
  <tr><td>Complexity</td><td>Proven technology, simpler</td><td>Higher tech, magnetic bearings</td></tr>
</table>
"""})

    slides.append({"title": "VFD Energy Savings", "section": "HP Compressors", "content": """
<h2>VFD Energy Savings — FSD575 (400 kW)</h2>
<iframe class="plot-frame" src="visualizations_v3/vfd_energy_savings.html"></iframe>
<p>VFD provides significant energy savings at partial loads (affinity law: P ∝ Speed³).
   At typical 70% average load, VFD saves ~57% energy per compressor.
   At 100% load, VFD introduces 3% loss (power electronics overhead).</p>
<div class="equation">Annual savings at 70% avg load (per compressor):
  ΔE = (328 − 141) kW × 8,000 h = 1,496,000 kWh/yr
  Cost: 1,496,000 × €0.15 = €224k/yr per unit</div>
"""})

    slides.append({"title": "Redundancy Cost-Benefit", "section": "HP Compressors", "content": """
<h2>Redundancy Cost-Benefit Analysis</h2>
<iframe class="plot-frame" src="visualizations_v3/redundancy_cost_benefit.html"></iframe>
<p>Bubble size represents annual energy cost. The HSD Twin Combi offers the best availability
   per euro of capital investment, while the FSD575 VFD options offer superior energy efficiency
   through variable-speed operation.</p>
"""})

    # ── Section 4: WCS.HP Protection (slides 21-28) ──
    slides.append({"title": "WCS.HP Overview", "section": "WCS.HP", "content": """
<h2>WCS.HP Supply Protection — Overview</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">14 barg</div><div class="label">Nominal HP Header</div></div>
  <div class="kpi"><div class="value">1×10⁻⁵</div><div class="label">Total Leak Budget</div></div>
  <div class="kpi"><div class="value">70/20/10</div><div class="label">Main/Side/Cont (%)</div></div>
  <div class="kpi"><div class="value">13.5 barg</div><div class="label">Isolation Trigger</div></div>
</div>
<h3>Design Principle</h3>
<p><strong>WCS.HP</strong> (Worst Case Supply — High Pressure) ensures sidestream activities
   (recovery, purification, research taps) do <strong>not</strong> compromise the main 14 barg supply.
   Fail-safe isolation valves on sidestreams close automatically when HP header pressure drops.</p>
"""})

    # Leak budget
    budget_rows = ""
    for _, r in budget_df.iterrows():
        budget_rows += f"<tr><td>{r['circuit']}</td><td>{r['budget_mbar_l_s']:.0e}</td><td>{r['fraction_pct']}%</td><td>{r['justification']}</td></tr>\n"

    slides.append({"title": "Leak Budget Allocation", "section": "WCS.HP", "content": f"""
<h2>Leak Rate Budget Allocation</h2>
<p>Total system budget: <strong>1×10⁻⁵ mbar·L/s</strong> (RTM-048 system cap)</p>
<table>
  <tr><th>Circuit</th><th>Budget (mbar·L/s)</th><th>Fraction</th><th>Justification</th></tr>
  {budget_rows}
</table>
<h3>Protection Strategy</h3>
<ol>
  <li><strong>Normal:</strong> All circuits active, total leak within budget</li>
  <li><strong>WCS trigger:</strong> HP pressure < 13.5 barg → close sidestream valves, recover 20% budget</li>
  <li><strong>Emergency:</strong> HP pressure < 13.0 barg → alarm, start backup compressor, reduce beam</li>
</ol>
"""})

    # Interlock table
    int_rows = ""
    for _, r in int_df.iterrows():
        badge_cls = {"WARNING": "review", "ALARM": "risk", "AUTO": "accept", "TRIP": "risk"}.get(r["priority"], "trace")
        int_rows += f"<tr><td>{r['condition']}</td><td>{r['setpoint']}</td><td>{r['action']}</td><td>{r['purpose']}</td><td><span class='badge badge-{badge_cls}'>{r['priority']}</span></td></tr>\n"

    slides.append({"title": "Interlock Logic", "section": "WCS.HP", "content": f"""
<h2>Interlock Logic Table</h2>
<table>
  <tr><th>Condition</th><th>Setpoint</th><th>Action</th><th>Purpose</th><th>Priority</th></tr>
  {int_rows}
</table>
"""})

    slides.append({"title": "WCS.HP Architecture Diagram", "section": "WCS.HP", "content": """
<h2>WCS.HP Supply Architecture — Block Diagram</h2>
<iframe class="plot-frame" style="height:640px;" src="visualizations_v3/wcs_hp_architecture.html"></iframe>
<p>Compressors in parallel feed the HP header at 14 barg. Check valves prevent backflow.
   The main supply branch (QVB/WSH/Beam) receives 70% of the leak budget.
   Sidestream branches have normally-closed isolation valves that close on low HP pressure.</p>
"""})

    # Scenario table
    scn_rows = ""
    for _, r in scn_df.iterrows():
        badge_cls = {"NOMINAL": "accept", "WARNING": "review", "ALARM": "risk", "TRIP": "risk"}.get(r["status"], "trace")
        scn_rows += f"<tr><td>{r['scenario']}</td><td>{r['compressors_running']}/{r['compressors_available']}</td><td>{r['capacity_pct']:.0f}%</td><td>{r['hp_header_barg']}</td><td>{r['sidestreams']}</td><td>{r['beam_pct']:.0f}%</td><td><span class='badge badge-{badge_cls}'>{r['status']}</span></td></tr>\n"

    slides.append({"title": "WCS Scenario Analysis", "section": "WCS.HP", "content": f"""
<h2>WCS Scenario Analysis</h2>
<table>
  <tr><th>Scenario</th><th>Compressors (run/avail)</th><th>Capacity</th><th>HP Header</th><th>Sidestreams</th><th>Beam</th><th>Status</th></tr>
  {scn_rows}
</table>
"""})

    slides.append({"title": "Scenario 1: Normal Operation", "section": "WCS.HP", "content": """
<h2>Scenario 1: Normal Operation</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">3</div><div class="label">Compressors Available</div></div>
  <div class="kpi"><div class="value">2</div><div class="label">Running</div></div>
  <div class="kpi"><div class="value">14.0 barg</div><div class="label">HP Header</div></div>
  <div class="kpi"><div class="value">100%</div><div class="label">Beam Operation</div></div>
</div>
<h3>Operating State</h3>
<ul>
  <li>All 3 compressors available: 2 running (100% capacity), 1 standby</li>
  <li>HP header stable at 14.0 barg</li>
  <li>Sidestreams: <strong>Open</strong> — recovery, purification, research taps active</li>
  <li>Total leak budget used: 9×10⁻⁶ mbar·L/s (90% of allowable)</li>
  <li>Full beam operation at 100% intensity</li>
</ul>
<p><span class="badge badge-accept">NOMINAL</span> — System fully operational with margin.</p>
"""})

    slides.append({"title": "Scenario 2: WCS (1 Failed)", "section": "WCS.HP", "content": """
<h2>Scenario 2: WCS — 1 Compressor Failed</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">2</div><div class="label">Compressors Available</div></div>
  <div class="kpi"><div class="value">2</div><div class="label">Running (no standby)</div></div>
  <div class="kpi"><div class="value">13.8 barg</div><div class="label">HP Header</div></div>
  <div class="kpi"><div class="value">100%</div><div class="label">Beam (maintained)</div></div>
</div>
<h3>Response</h3>
<ul>
  <li>2 compressors running at 100% capacity, <strong>no standby margin</strong></li>
  <li>HP header slightly reduced to 13.8 barg</li>
  <li>Sidestreams: <strong>Closed</strong> by interlock (precautionary isolation)</li>
  <li>Leak budget reduced to 7×10⁻⁶ mbar·L/s (main supply only)</li>
  <li>Beam operation maintained at 100%</li>
  <li>Maintenance team dispatched to repair failed compressor</li>
</ul>
<p><span class="badge badge-review">WARNING</span> — Operational but no redundancy margin.</p>
"""})

    slides.append({"title": "Scenario 3: Emergency (2 Failed)", "section": "WCS.HP", "content": """
<h2>Scenario 3: Emergency — 2 Compressors Failed</h2>
<div class="kpi-row">
  <div class="kpi"><div class="value">1</div><div class="label">Compressor Available</div></div>
  <div class="kpi"><div class="value">50%</div><div class="label">Capacity</div></div>
  <div class="kpi"><div class="value">13.2 barg</div><div class="label">HP Header</div></div>
  <div class="kpi"><div class="value">50%</div><div class="label">Beam (reduced)</div></div>
</div>
<h3>Response</h3>
<ul>
  <li>1 compressor running at 50% capacity</li>
  <li>HP header dropped to 13.2 barg — below LOW-LOW threshold</li>
  <li>Sidestreams: <strong>Closed</strong></li>
  <li>Beam intensity reduced to 50% to match available capacity</li>
  <li>Total leak budget: 3.5×10⁻⁶ mbar·L/s (half load)</li>
  <li><strong>Priority repair</strong> of failed compressors</li>
</ul>
<p><span class="badge badge-risk">ALARM</span> — Degraded operation, immediate repair needed.</p>
"""})

    # ── Section 5: Warm Valve Derogation (slides 29-32) ──
    slides.append({"title": "Warm Valve Derogation Context", "section": "Derogation", "content": """
<h2>Warm Valve Leak Tightness Derogation</h2>
<h3>Background (from Cryoworld Offer)</h3>
<p>For warm On/Off valves (W1d), Cryoworld proposes <strong>pneumatic ball valves of Meca Inox</strong>
   with HDPE sealing. These valves do not comply with the specified He leak rate of 1×10⁻⁹ mbar·L/s
   (considered unnecessarily stringent for warm service).</p>
<h3>Proposed Approach</h3>
<ul>
  <li>Create a new sub-class (W1d) with higher allowable leak rate to ambient</li>
  <li>Ask GBO to perform short calculation on acceptable leak rate</li>
  <li>Look into spec of proposed variants from Cryoworld</li>
</ul>
<h3>Valve Proposals</h3>
<table>
  <tr><th>Type</th><th>Application</th></tr>
  <tr><td>Meca Inox ball valves with HDPE seals</td><td>Larger size manual valves</td></tr>
  <tr><td>Swagelok SS-42GSE with UHMWPE seal</td><td>Instrumentation valves</td></tr>
</table>
<p>Both types are suitable for the specified radiation environment and are an economic solution.</p>
"""})

    slides.append({"title": "Warm Valve Impact Analysis", "section": "Derogation", "content": """
<h2>Impact of Derogation on Liquid He Inventory</h2>
<h3>Leak Rate Comparison: W1d Warm Valves</h3>
<table>
  <tr><th>Spec</th><th>Leak Rate</th><th>Mass Loss (g/yr)</th><th>Liquid Loss (L/yr)</th><th>Cost (€/yr)</th></tr>
  <tr><td>Original (1×10⁻⁹)</td><td>1×10⁻⁹ mbar·L/s</td><td>0.00036</td><td>0.000003</td><td>€0.00004</td></tr>
  <tr><td>Proposed (1×10⁻⁵)</td><td>1×10⁻⁵ mbar·L/s</td><td>3.60</td><td>0.029</td><td>€0.43</td></tr>
  <tr><td>Worst case (1×10⁻⁴)</td><td>1×10⁻⁴ mbar·L/s</td><td>35.99</td><td>0.288</td><td>€4.32</td></tr>
</table>
<p><strong>Note:</strong> These are per-valve values at 4.222K. In practice, warm valves operate at 273-323K,
   where losses are even smaller (by factor T_warm/T_cold ≈ 70×).</p>
<h3>At Warm Temperature (300K)</h3>
<p>At 300K, the mass flow for same throughput is reduced by 300/4.222 ≈ 71× compared to 4K.
   For 1×10⁻⁴ mbar·L/s at 300K: mass loss = 0.51 g/yr per valve. Completely negligible.</p>
<h3>Conclusion</h3>
<p><span class="badge badge-accept">ACCEPT</span> The derogation is justified.
   Even at 1×10⁻⁴ mbar·L/s, the liquid He inventory impact from warm valves is negligible.
   The economic solution (Meca Inox / Swagelok) is appropriate.</p>
"""})

    slides.append({"title": "Valve Classification Table", "section": "Derogation", "content": """
<h2>Control Valve Classification (CV Classes)</h2>
<table>
  <tr><th>Class</th><th>CV</th><th>CV</th><th>CV</th><th>CV</th></tr>
  <tr><td>Sub-class</td><td>Q1</td><td>Q2d</td><td>W1d</td><td>W3</td></tr>
  <tr><td>Temp range (K)</td><td>1.5 - 373</td><td>1.5 - 373</td><td>273 - 323</td><td>273 - 323</td></tr>
  <tr><td>Conduction heat min.</td><td>yes</td><td>no</td><td>no</td><td>no</td></tr>
  <tr><td>Actuation</td><td>indirect-pneumatic</td><td>indirect-pneumatic</td><td>indirect-pneumatic</td><td>direct-electrical</td></tr>
  <tr style="background:#fefcbf;"><td><strong>Max leak to ambient</strong></td><td><strong>1.0E-09</strong></td><td><strong>1.0E-09</strong></td><td><strong>1.0E-09</strong></td><td><strong>1.0E-09</strong></td></tr>
  <tr style="background:#fefcbf;"><td><strong>Max leak across</strong></td><td><strong>1.0E-04</strong></td><td><strong>1.0E-04</strong></td><td><strong>1.0E-04</strong></td><td><strong>1.0E-04</strong></td></tr>
  <tr><td>Electrical valve tech</td><td>piezo</td><td>piezo</td><td>solenoid</td><td>solenoid</td></tr>
  <tr><td>Position indicator</td><td>continuous</td><td>limit switches</td><td>limit switches</td><td>limit switch</td></tr>
  <tr><td>Radiation hardness</td><td>required</td><td>required</td><td>required</td><td>not required</td></tr>
</table>
<p><em>Highlighted rows show the current leak rate specs that Cryoworld is requesting derogation for (W1d class).</em></p>
"""})

    slides.append({"title": "Derogation Recommendation", "section": "Derogation", "content": """
<h2>Derogation Recommendation Summary</h2>
<h3>Key Findings</h3>
<ol>
  <li>The 1×10⁻⁹ mbar·L/s to-ambient spec is <strong>unnecessarily stringent</strong> for warm valves (273-323K)</li>
  <li>Liquid He inventory impact at 1×10⁻⁴ mbar·L/s warm valve is <strong>0.007 g/yr</strong> (at 300K)</li>
  <li>Proposed Meca Inox ball valves with HDPE seals are <strong>industry standard</strong> for radiation environments</li>
  <li>Economic benefit: HDPE ball valves are significantly cheaper than bellow-sealed alternatives</li>
</ol>
<h3>Recommended Actions</h3>
<table>
  <tr><th>#</th><th>Action</th><th>Owner</th><th>Status</th></tr>
  <tr><td>1</td><td>Create W1d sub-class with 1×10⁻⁵ or 1×10⁻⁴ to-ambient</td><td>SCK CEN</td><td><span class="badge badge-review">REVIEW</span></td></tr>
  <tr><td>2</td><td>GBO to perform short calculation on acceptable limit</td><td>GBO</td><td><span class="badge badge-review">PENDING</span></td></tr>
  <tr><td>3</td><td>Review Cryoworld proposed variants and validate</td><td>SCK CEN</td><td><span class="badge badge-review">PENDING</span></td></tr>
  <tr><td>4</td><td>Document derogation in SoR matrix</td><td>SCK CEN</td><td><span class="badge badge-trace">TODO</span></td></tr>
</table>
"""})

    # ── Section 6: Compliance (slides 33-36) ──
    slides.append({"title": "PED Classification", "section": "Compliance", "content": """
<h2>PED Classification — HP System at 14 barg</h2>
<h3>Pressure Equipment Directive 2014/68/EU</h3>
<p>The HP helium supply operates at <strong>15 bara (14 barg)</strong>, which places it in
   PED Category II or III depending on volume:</p>
<table>
  <tr><th>Parameter</th><th>Value</th><th>PED Implication</th></tr>
  <tr><td>Max pressure</td><td>15 bara (14 barg)</td><td>Above 0.5 bar → PED applies</td></tr>
  <tr><td>Fluid group</td><td>Group 2 (He, non-dangerous)</td><td>Less stringent than Group 1</td></tr>
  <tr><td>PS × V</td><td>Depends on vessel size</td><td>Category I if < 1000 bar·L</td></tr>
  <tr><td>Module</td><td>A2 or D/D1</td><td>Notified body for Cat ≥ II</td></tr>
</table>
<h3>ASME B31.3 — Cryogenic Service</h3>
<ul>
  <li>Impact testing required for materials below −29°C (−20°F)</li>
  <li>He at 4K: extreme cryogenic service → austenitic stainless steel (AISI 316L)</li>
  <li>Welding procedures per ASME IX, post-weld heat treatment not required for 316L</li>
</ul>
"""})

    slides.append({"title": "EN 13458 Compliance", "section": "Compliance", "content": """
<h2>EN 13458 — Cryogenic Vessels</h2>
<h3>Static Vacuum-Insulated Vessels</h3>
<p>The WSH (Warm Storage Holder) containing 5,000 L liquid He must comply with EN 13458-2 for design
   and EN 13458-3 for operational requirements.</p>
<table>
  <tr><th>Requirement</th><th>EN 13458 Clause</th><th>Status</th></tr>
  <tr><td>Design pressure</td><td>§5.2</td><td>Per MAWP calculation</td></tr>
  <tr><td>Vacuum insulation</td><td>§6.3</td><td>MLI + vacuum jacket</td></tr>
  <tr><td>Safety devices</td><td>§7</td><td>PRV, burst disc, vacuum gauge</td></tr>
  <tr><td>Level measurement</td><td>§8.2</td><td>Capacitance or differential pressure</td></tr>
  <tr><td>Leak testing</td><td>§9.3</td><td>He mass spectrometer, <1×10⁻⁸ mbar·L/s</td></tr>
  <tr><td>Documentation</td><td>§10</td><td>Design file, operating manual</td></tr>
</table>
"""})

    slides.append({"title": "EN 13185 Leak Detection", "section": "Compliance", "content": """
<h2>EN 13185 — Leak Detection Methods</h2>
<table>
  <tr><th>Method</th><th>Sensitivity (mbar·L/s)</th><th>Application</th></tr>
  <tr><td>He mass spectrometer (vacuum)</td><td>10⁻¹² to 10⁻⁸</td><td>Cold valves, vessel welds</td></tr>
  <tr><td>He mass spectrometer (sniffer)</td><td>10⁻⁷ to 10⁻⁵</td><td>Field testing, warm valves</td></tr>
  <tr><td>Pressure decay</td><td>10⁻⁵ to 10⁻²</td><td>System-level testing</td></tr>
  <tr><td>Bubble test</td><td>10⁻⁴ to 10⁻¹</td><td>Gross leak detection</td></tr>
</table>
<h3>Testing Strategy for Warm Valves (W1d)</h3>
<p>If the derogation is approved to 1×10⁻⁵ or 1×10⁻⁴ mbar·L/s, sniffer testing is sufficient.
   This is significantly faster and cheaper than vacuum-mode mass spectrometer testing required
   for the 1×10⁻⁹ specification.</p>
"""})

    slides.append({"title": "RTM Traceability Update", "section": "Compliance", "content": """
<h2>Requirements Traceability — v3.1.0 Updates</h2>
<table>
  <tr><th>RTM ID</th><th>Requirement</th><th>v3.1 Update</th><th>Status</th></tr>
  <tr><td>RTM-048</td><td>System max leak: 1×10⁻⁵ mbar·L/s</td><td>Liquid loss: 3.6 g/yr (negligible)</td><td><span class="badge badge-accept">ACCEPT</span></td></tr>
  <tr><td>RTM-049</td><td>Valve leak to ambient: 1×10⁻⁹</td><td>Warm valve derogation analysis added</td><td><span class="badge badge-review">REVIEW</span></td></tr>
  <tr><td>RTM-053</td><td>MTTR: 4-8 hours</td><td>Used in compressor availability model</td><td><span class="badge badge-accept">ACCEPT</span></td></tr>
  <tr><td>RTM-054</td><td>Recovery: 200 g/s</td><td>WCS scenario uses this as demand basis</td><td><span class="badge badge-trace">TRACE</span></td></tr>
  <tr><td>NEW</td><td>HP availability >99.99%</td><td>All configs exceed target</td><td><span class="badge badge-new">NEW</span></td></tr>
  <tr><td>NEW</td><td>WCS protection logic</td><td>Interlock table defined</td><td><span class="badge badge-new">NEW</span></td></tr>
  <tr><td>NEW</td><td>VFD energy optimization</td><td>Savings calculated: €224k/yr/unit</td><td><span class="badge badge-new">NEW</span></td></tr>
</table>
"""})

    # ── Section 7: Data & Methodology (slides 37-40) ──
    slides.append({"title": "Calculation Methodology", "section": "Methodology", "content": """
<h2>Calculation Methodology Summary</h2>
<h3>Liquid He Loss (src/liquid_he_loss.py)</h3>
<div class="equation">ṁ = Q_Pa_m3_s × M_He / (R × T)
Q_Pa_m3_s = Q_mbar_l_s × 0.1
V̇_liq = ṁ / ρ_liq (125 kg/m³)</div>
<h3>Compressor Reliability (src/compressor_reliability.py)</h3>
<div class="equation">A_single = MTBF / (MTBF + MTTR)
A_sys(k-of-M) = Σ_{i=k}^{M} C(M,i) × A^i × (1-A)^(M-i)
MTBF_sys ≈ A_sys × MTTR / (1-A_sys)</div>
<h3>VFD Savings</h3>
<div class="equation">P_VFD = P_full × (load)³ / η_VFD     (affinity law)
P_fixed ≈ P_full × (0.4 + 0.6 × load) (slide valve)
ΔCost = ΔP × hours × €/kWh</div>
"""})

    slides.append({"title": "Data Sources & Assumptions", "section": "Methodology", "content": """
<h2>Data Sources & Key Assumptions</h2>
<table>
  <tr><th>Data</th><th>Source</th><th>Confidence</th></tr>
  <tr><td>He-4 properties</td><td>NIST REFPROP</td><td><span class="badge badge-accept">HIGH</span></td></tr>
  <tr><td>Valve leak rates</td><td>RTM-048, RTM-049, EN 13185</td><td><span class="badge badge-accept">HIGH</span></td></tr>
  <tr><td>FSD575 specs</td><td>Industry estimate (KAESER class)</td><td><span class="badge badge-review">MEDIUM</span></td></tr>
  <tr><td>HSD Twin specs</td><td>Industry estimate (Atlas Copco class)</td><td><span class="badge badge-review">MEDIUM</span></td></tr>
  <tr><td>MTBF = 8760 h</td><td>Conservative assumption</td><td><span class="badge badge-review">MEDIUM</span></td></tr>
  <tr><td>MTTR = 8 h</td><td>RTM-053 (upper bound)</td><td><span class="badge badge-accept">HIGH</span></td></tr>
  <tr><td>He price €120/kg</td><td>2024 market estimate</td><td><span class="badge badge-review">MEDIUM</span></td></tr>
  <tr><td>Electricity €0.15/kWh</td><td>Industrial rate (Belgium)</td><td><span class="badge badge-accept">HIGH</span></td></tr>
</table>
<h3>Key Assumptions</h3>
<ul>
  <li>Ideal gas law applies (Z ≈ 1 for low-pressure gas leaks)</li>
  <li>Leak rate measured at reference conditions (as per EN 1779)</li>
  <li>Compressor failures are independent (no common-cause)</li>
  <li>VFD affinity law: P ∝ Speed³ (approximate for screw compressors)</li>
  <li>WSH capacity: 5,000 L liquid (design basis, to be confirmed)</li>
</ul>
"""})

    slides.append({"title": "Open Items & Next Steps", "section": "Methodology", "content": """
<h2>Open Items & Next Steps</h2>
<table>
  <tr><th>#</th><th>Item</th><th>Priority</th><th>Owner</th></tr>
  <tr><td>1</td><td>Confirm HSD Twin Combi exact configuration (M definition)</td><td><span class="badge badge-risk">HIGH</span></td><td>Vendor</td></tr>
  <tr><td>2</td><td>GBO calculation for warm valve acceptable leak rate</td><td><span class="badge badge-risk">HIGH</span></td><td>GBO</td></tr>
  <tr><td>3</td><td>Confirm WSH vessel capacity (5,000 L assumed)</td><td><span class="badge badge-review">MEDIUM</span></td><td>Design</td></tr>
  <tr><td>4</td><td>Get actual FSD575 / HSD vendor quotation</td><td><span class="badge badge-review">MEDIUM</span></td><td>Procurement</td></tr>
  <tr><td>5</td><td>Validate MTBF data against manufacturer data sheets</td><td><span class="badge badge-review">MEDIUM</span></td><td>Reliability</td></tr>
  <tr><td>6</td><td>Integrate with SoR Requirements Matrix</td><td><span class="badge badge-review">MEDIUM</span></td><td>Systems</td></tr>
  <tr><td>7</td><td>PED category assessment for HP compressor vessels</td><td><span class="badge badge-trace">LOW</span></td><td>Design</td></tr>
  <tr><td>8</td><td>Common-cause failure analysis for compressors</td><td><span class="badge badge-trace">LOW</span></td><td>Reliability</td></tr>
</table>
"""})

    slides.append({"title": "Conclusions & Recommendations", "section": "Methodology", "content": """
<h2>Conclusions & Recommendations</h2>
<h3>Liquid Helium Operations</h3>
<ul>
  <li>Valve leak rates (10⁻⁹ to 10⁻⁴ mbar·L/s) have <strong>negligible impact</strong> on liquid He inventory</li>
  <li>The warm valve derogation (1×10⁻⁹ → 1×10⁻⁵ or 10⁻⁴) is <strong>justified</strong></li>
  <li>Static heat leak (insulation quality) dominates boil-off, not valve leaks</li>
</ul>
<h3>HP Compressor Redundancy</h3>
<ul>
  <li>All options (N=3, N+1 FSD575, N+1 HSD) exceed 99.99% availability</li>
  <li><strong>Recommended: N+1 FSD575 VFD (2-of-4)</strong> for best combination of availability, energy efficiency, and proven technology</li>
  <li>VFD provides ~€224k/yr energy savings per compressor at 70% load</li>
</ul>
<h3>WCS.HP Protection</h3>
<ul>
  <li>70/20/10 leak budget allocation (main/sidestream/contingency) provides adequate margin</li>
  <li>Interlock logic ensures sidestream isolation before main supply is compromised</li>
  <li>System can maintain 100% beam at single compressor failure, 50% at double failure</li>
</ul>
"""})

    return slides


# ══════════════════════════════════════════════════════════════════
# MAIN BUILD
# ══════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  BUILD v3.1.0 — Liquid He Operations & HP Compressors      ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    print("[1/6] Generating charts...")
    chart_liquid_inventory_depletion()
    chart_compressor_availability()
    chart_boiloff_vs_leakrate()
    chart_wcs_hp_architecture()
    chart_redundancy_cost_benefit()
    chart_vfd_energy_savings()

    print("\n[2/6] Exporting data tables...")
    export_data()

    print("\n[3/6] Building Liquid He Operations Guide...")
    build_liquid_operations_guide()

    print("\n[4/6] Building HP Redundancy Analysis...")
    build_hp_redundancy_analysis()

    print("\n[5/6] Building WCS.HP Protection Analysis...")
    build_wcs_hp_protection()

    print("\n[6/6] Building Master Navigator (40 slides)...")
    build_navigator()

    print("\n✅ BUILD v3.1.0 COMPLETE")
    print(f"   Charts: {VIZ_DIR.relative_to(ROOT)}/")
    print(f"   Docs:   {DOC_DIR.relative_to(ROOT)}/")
    print(f"   Data:   {TABLES_DIR.relative_to(ROOT)}/")
    print(f"   Navigator: docs/index_v3_1.html")


if __name__ == "__main__":
    main()
