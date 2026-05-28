#!/usr/bin/env python3
"""OUTPUT_2_DMAIC_REFINED — Enhanced Multi-Tier Professional Dashboard v2.1.0

MAPPING_HEROES navigation with Monte Carlo cost analysis, supplier comparison,
material specs, risk modeling, and enhanced Plotly visualizations.
"""
from __future__ import annotations
import json, math, shutil, os, sys
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Project paths ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.calc_leak_rate import (
    build_conversion_grid, leak_rate_to_mass_flow_g_year,
    dimensional_proof, normal_m3_per_day_to_kg_per_year,
    mbar_l_s_to_pa_m3_s, SECONDS_PER_YEAR, R_UNIVERSAL,
    MOLAR_MASS_HE_G_PER_MOL, MOLAR_MASS_HE_KG_PER_MOL,
)
from src.monte_carlo import run_all_scenarios, SCENARIOS, compute_statistics, sensitivity_tornado
from src.materials_db import (
    MATERIALS, WELDING_SPECS, CODES_STANDARDS, SUPPLIER_COMPARISON,
    VALVE_CLASSES, RELIABILITY_DATA,
)
from src.risk_model import (
    RISK_REGISTER, OPERATIONAL_SCENARIOS, risk_matrix_data, beam_impact_analysis,
)

VERSION = "2.1.0"
BUILD_ID = f"OUTPUT_2_DMAIC_REFINED"
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

# ── Output directories ──
DOCS = ROOT / "docs"
HEROES = DOCS / "heroes"
SLIDES = DOCS / "slides"
NOTES = DOCS / "notes"
VIZ = DOCS / "visualizations"
ASSETS = DOCS / "assets"
DATA_OUT = ROOT / "outputs" / "data_v2"

for d in [DOCS, HEROES, SLIDES, NOTES, VIZ, ASSETS, DATA_OUT]:
    d.mkdir(parents=True, exist_ok=True)

# ── Color scheme ──
COLORS = {
    "primary": "#1E3A8A",
    "secondary": "#10B981",
    "accent": "#F59E0B",
    "danger": "#EF4444",
    "neutral": "#6B7280",
    "bg": "#F9FAFB",
    "bg_card": "#FFFFFF",
    "text": "#111827",
    "text_light": "#6B7280",
    "border": "#E5E7EB",
    "blue_50": "#EFF6FF",
    "blue_100": "#DBEAFE",
    "green_50": "#ECFDF5",
    "amber_50": "#FFFBEB",
    "red_50": "#FEF2F2",
}

HERO_TABS = [
    {"id": "interface", "icon": "🔗", "label": "INTERFACE", "desc": "System boundaries, valve locations, flow diagrams"},
    {"id": "control", "icon": "⚙️", "label": "CONTROL", "desc": "Actuation methods, automation, fail-safe logic"},
    {"id": "design", "icon": "📐", "label": "DESIGN", "desc": "Engineering specs, leak rates, valve classes"},
    {"id": "cost", "icon": "💰", "label": "COST", "desc": "Monte Carlo analysis, TCO, supplier comparison"},
    {"id": "materials", "icon": "🧪", "label": "MATERIALS", "desc": "316 SS specs, electropolish, welding, ASME codes"},
    {"id": "risk", "icon": "⚠️", "label": "RISK", "desc": "Geopolitical, operational, reliability scenarios"},
    {"id": "operations", "icon": "🔧", "label": "OPERATIONS", "desc": "MTBF, MTTR, MDT, maintenance strategy"},
]

# ═══════════════════════════════════════════════════════════
# CSS & JS
# ═══════════════════════════════════════════════════════════

def write_css():
    css = """
:root {
  --primary: #1E3A8A; --secondary: #10B981; --accent: #F59E0B;
  --danger: #EF4444; --neutral: #6B7280; --bg: #F9FAFB;
  --bg-card: #FFFFFF; --text: #111827; --text-light: #6B7280;
  --border: #E5E7EB; --shadow: 0 1px 3px rgba(0,0,0,0.1);
  --radius: 8px; --font-sans: 'Inter','Segoe UI',system-ui,sans-serif;
  --font-mono: 'Fira Code','Fira Mono','Consolas',monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; scroll-behavior: smooth; }
body { font-family: var(--font-sans); background: var(--bg); color: var(--text); line-height: 1.6; }

/* ── Navigation ── */
.top-bar { background: var(--primary); color: #fff; padding: 0.5rem 1rem; display: flex;
  align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 1000; }
.top-bar h1 { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.5px; }
.top-bar .version { font-size: 0.75rem; opacity: 0.7; margin-left: 0.5rem; }
.hero-nav { display: flex; background: #1e2d5a; overflow-x: auto; }
.hero-nav a { color: #cbd5e1; text-decoration: none; padding: 0.6rem 1rem; font-size: 0.8rem;
  font-weight: 600; white-space: nowrap; border-bottom: 3px solid transparent; transition: all 0.2s; }
.hero-nav a:hover { color: #fff; background: rgba(255,255,255,0.05); }
.hero-nav a.active { color: #fff; border-bottom-color: var(--secondary); background: rgba(255,255,255,0.08); }
.hero-nav .icon { margin-right: 0.3rem; }

/* ── Breadcrumb ── */
.breadcrumb { padding: 0.5rem 1.5rem; font-size: 0.8rem; color: var(--text-light); background: #fff; border-bottom: 1px solid var(--border); }
.breadcrumb a { color: var(--primary); text-decoration: none; }
.breadcrumb span { margin: 0 0.3rem; }

/* ── Tier navigation ── */
.tier-nav { display: flex; gap: 0.5rem; padding: 0.75rem 1.5rem; background: var(--bg); border-bottom: 1px solid var(--border); }
.tier-nav a { padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.78rem; font-weight: 600;
  text-decoration: none; color: var(--text-light); background: #fff; border: 1px solid var(--border); transition: all 0.2s; }
.tier-nav a:hover { border-color: var(--primary); color: var(--primary); }
.tier-nav a.active { background: var(--primary); color: #fff; border-color: var(--primary); }

/* ── Main ── */
main { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
.slide { background: var(--bg-card); border-radius: var(--radius); box-shadow: var(--shadow);
  padding: 2rem; margin-bottom: 1.5rem; border: 1px solid var(--border); }
.slide h2 { font-size: 1.5rem; font-weight: 700; color: var(--primary); margin-bottom: 1rem; }
.slide h3 { font-size: 1.15rem; font-weight: 600; color: var(--text); margin: 1.2rem 0 0.5rem; }
.slide h4 { font-size: 0.95rem; font-weight: 600; margin: 1rem 0 0.4rem; }

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
.kpi { padding: 1.2rem; border-radius: var(--radius); text-align: center; }
.kpi .value { font-size: 1.8rem; font-weight: 800; }
.kpi .label { font-size: 0.75rem; color: var(--text-light); margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-blue { background: #EFF6FF; border: 1px solid #BFDBFE; }
.kpi-blue .value { color: var(--primary); }
.kpi-green { background: #ECFDF5; border: 1px solid #A7F3D0; }
.kpi-green .value { color: #059669; }
.kpi-amber { background: #FFFBEB; border: 1px solid #FDE68A; }
.kpi-amber .value { color: #D97706; }
.kpi-red { background: #FEF2F2; border: 1px solid #FECACA; }
.kpi-red .value { color: var(--danger); }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 1rem 0; }
th { background: var(--primary); color: #fff; padding: 0.6rem 0.8rem; text-align: left; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 0.55rem 0.8rem; border-bottom: 1px solid var(--border); }
tr:hover { background: #F8FAFC; }
tr:nth-child(even) { background: #FAFBFC; }
tr:nth-child(even):hover { background: #F1F5F9; }

/* ── Badges ── */
.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.3px; }
.badge-accept { background: #D1FAE5; color: #065F46; }
.badge-review { background: #FEF3C7; color: #92400E; }
.badge-risk { background: #FEE2E2; color: #991B1B; }
.badge-open { background: #FEE2E2; color: #991B1B; }
.badge-mitigated { background: #D1FAE5; color: #065F46; }
.badge-monitor { background: #DBEAFE; color: #1E40AF; }
.badge-accepted { background: #FEF3C7; color: #92400E; }
.badge-trace { background: #E0E7FF; color: #3730A3; }

/* ── Plot container ── */
.plot-container { width: 100%; min-height: 400px; margin: 1rem 0; border-radius: var(--radius); overflow: hidden; }
.plot-container iframe { width: 100%; height: 500px; border: none; border-radius: var(--radius); }

/* ── Comparison grid ── */
.compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 1rem 0; }
.compare-card { padding: 1.5rem; border-radius: var(--radius); border: 2px solid var(--border); }
.compare-card h4 { color: var(--primary); margin-bottom: 0.8rem; }
.compare-card.highlight { border-color: var(--secondary); background: #F0FDF9; }

/* ── Collapsible ── */
details { margin: 0.8rem 0; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
summary { padding: 0.8rem 1rem; background: #F8FAFC; cursor: pointer; font-weight: 600; font-size: 0.9rem; }
details > div, details > table, details > p { padding: 0 1rem 1rem; }

/* ── Footer ── */
footer { text-align: center; padding: 2rem; color: var(--text-light); font-size: 0.75rem; }

/* ── Print ── */
@media print {
  .top-bar, .hero-nav, .tier-nav, .breadcrumb { display: none !important; }
  .slide { break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }
  body { background: #fff; }
  main { max-width: 100%; padding: 0; }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .compare-grid { grid-template-columns: 1fr; }
  .hero-nav a { padding: 0.5rem 0.6rem; font-size: 0.72rem; }
}
"""
    (ASSETS / "style_v2.css").write_text(css)


def write_js():
    js = """
// MAPPING_HEROES Navigation & Interactivity
function setTier(tier) {
  document.querySelectorAll('.tier-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tier-nav a').forEach(el => el.classList.remove('active'));
  const target = document.getElementById('tier-' + tier);
  if (target) target.style.display = 'block';
  const btn = document.querySelector('.tier-nav a[data-tier="' + tier + '"]');
  if (btn) btn.classList.add('active');
}
function expandAll() { document.querySelectorAll('details').forEach(d => d.open = true); }
function collapseAll() { document.querySelectorAll('details').forEach(d => d.open = false); }
function exportPdf() { window.print(); }
document.addEventListener('DOMContentLoaded', () => { setTier && setTier('1'); });
"""
    (ASSETS / "heroes.js").write_text(js)


# ═══════════════════════════════════════════════════════════
# HTML Templating
# ═══════════════════════════════════════════════════════════

def _nav_html(active_hero: str = "", is_hero: bool = False) -> str:
    prefix = "" if not is_hero else ""
    links = []
    for h in HERO_TABS:
        cls = ' class="active"' if h["id"] == active_hero else ""
        href = f"{h['id']}.html" if is_hero else f"heroes/{h['id']}.html"
        links.append(f'<a href="{href}"{cls}><span class="icon">{h["icon"]}</span>{h["label"]}</a>')
    hub_href = "../index.html" if is_hero else "index.html"
    return f"""<div class="top-bar">
  <div><h1>QPLANT Cryogenic Dashboard</h1><span class="version">v{VERSION} • {BUILD_ID}</span></div>
  <div style="font-size:0.8rem"><a href="{hub_href}" style="color:#93c5fd;text-decoration:none;">🏠 Hub</a></div>
</div>
<nav class="hero-nav">{''.join(links)}</nav>"""


def _breadcrumb(hero_label: str, tier: str = "Overview") -> str:
    return f'<div class="breadcrumb"><a href="index.html">Dashboard</a><span>›</span><a href="{hero_label.lower()}.html">{hero_label}</a><span>›</span>{tier}</div>'


def _tier_nav(*tier_pairs, active: str = "1") -> str:
    """Accept pairs like ("1", "Tier 1 — Overview"), ("2", "Details"), ..."""
    links = []
    for tid, label in tier_pairs:
        cls = ' class="active"' if tid == active else ""
        links.append(f'<a href="#" onclick="setTier(\'{tid}\');return false;" data-tier="{tid}"{cls}>{label}</a>')
    return '<div class="tier-nav">' + ''.join(links) + '</div>'


def _page(title: str, body: str, hero: str = "", extra_head: str = "", is_hero: bool = False) -> str:
    prefix = "../" if is_hero else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — QPLANT Dashboard v{VERSION}</title>
<link rel="stylesheet" href="{prefix}assets/style_v2.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
{extra_head}
</head>
<body>
{_nav_html(hero, is_hero)}
<main>{body}</main>
<footer>QPLANT Cryogenic Leak Rate Dashboard v{VERSION} • {BUILD_ID} • Generated {TIMESTAMP}<br>
SCK CEN / MYRRHA — Confidential</footer>
<script src="{prefix}assets/heroes.js"></script>
</body></html>"""


def _kpi(value: str, label: str, style: str = "blue") -> str:
    return f'<div class="kpi kpi-{style}"><div class="value">{value}</div><div class="label">{label}</div></div>'


def _badge(status: str) -> str:
    cls = status.lower().replace(" ", "-")
    return f'<span class="badge badge-{cls}">{status}</span>'


def _df_to_html(df: pd.DataFrame, max_rows: int = 50) -> str:
    return df.head(max_rows).to_html(index=False, classes="", border=0, escape=False,
                                       float_format=lambda x: f"{x:,.4g}" if abs(x) < 1e6 else f"{x:,.0f}")


# ═══════════════════════════════════════════════════════════
# PLOTLY CHART GENERATORS
# ═══════════════════════════════════════════════════════════

PLOT_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, sans-serif", size=13),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FAFBFC",
        margin=dict(l=60, r=30, t=50, b=50),
        hoverlabel=dict(bgcolor="#1E3A8A", font_color="#fff", font_size=12),
    )
)

def _save_plot(fig: go.Figure, name: str):
    fig.update_layout(template="plotly_white")
    fig.update_layout(**PLOT_TEMPLATE["layout"])
    path = VIZ / f"{name}.html"
    fig.write_html(str(path), include_plotlyjs="cdn", full_html=True)
    return path


def plot_leak_vs_loss_enhanced():
    """Enhanced log-log scatter: leak rate vs He loss with supplier zones."""
    leak_rates = np.logspace(-10, -3, 80)
    temps = [4, 20, 80, 300]
    temp_colors = {4: "#1E3A8A", 20: "#7C3AED", 80: "#059669", 300: "#DC2626"}
    
    fig = go.Figure()
    for t in temps:
        g_year = [leak_rate_to_mass_flow_g_year(lr, t, 5.0) for lr in leak_rates]
        fig.add_trace(go.Scatter(
            x=leak_rates, y=g_year, mode="lines",
            name=f"{t} K", line=dict(color=temp_colors[t], width=2.5),
            hovertemplate="Leak: %{x:.1e} mbar·L/s<br>Loss: %{y:.3g} g/yr<br>T=%{text} K<extra></extra>",
            text=[str(t)] * len(leak_rates),
        ))
    
    # Supplier zones
    fig.add_vrect(x0=1e-10, x1=1e-9, fillcolor="#10B981", opacity=0.08, line_width=0,
                  annotation_text="Ultra-tight\n(1e-9 spec)", annotation_position="top left",
                  annotation=dict(font_size=10, font_color="#065F46"))
    fig.add_vrect(x0=1e-6, x1=1e-4, fillcolor="#F59E0B", opacity=0.08, line_width=0,
                  annotation_text="Derogation zone\n(Meca Inox)", annotation_position="top right",
                  annotation=dict(font_size=10, font_color="#92400E"))
    
    # RTM limit
    fig.add_hline(y=65000, line_dash="dash", line_color="#EF4444", line_width=1.5,
                  annotation_text="RTM-048 Cap ≈ 65 kg/yr", annotation_position="bottom right",
                  annotation=dict(font_size=11, font_color="#EF4444"))
    
    fig.update_xaxes(type="log", title="Leak Rate (mbar·L/s)", gridcolor="#E5E7EB",
                     showline=True, linecolor="#9CA3AF")
    fig.update_yaxes(type="log", title="He Mass Loss (g/year)", gridcolor="#E5E7EB",
                     showline=True, linecolor="#9CA3AF")
    fig.update_layout(
        title=dict(text="Leak Rate vs Helium Mass Loss — Temperature Sensitivity", font=dict(size=16)),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#E5E7EB", borderwidth=1),
        height=550,
    )
    return _save_plot(fig, "enhanced_leak_rate_comparison")


def plot_monte_carlo_distribution(mc_results):
    """Cost distribution histogram from Monte Carlo."""
    df = mc_results["baseline"]["df"]
    
    fig = make_subplots(rows=2, cols=2,
        subplot_titles=("Total Annual Cost Distribution", "Helium Price Sampled",
                        "Beam Availability", "He Loss vs Cost"),
        vertical_spacing=0.12, horizontal_spacing=0.1)
    
    # 1: Cost histogram
    stats = mc_results["baseline"]["stats"]["total_cost_eur"]
    fig.add_trace(go.Histogram(x=df["total_cost_eur"], nbinsx=60, name="Total Cost",
        marker_color="#1E3A8A", opacity=0.8), row=1, col=1)
    for pct, val, color in [("P10", stats["p10"], "#10B981"), ("P50", stats["p50"], "#F59E0B"), ("P90", stats["p90"], "#EF4444")]:
        fig.add_vline(x=val, line_dash="dash", line_color=color, row=1, col=1,
                      annotation_text=f"{pct}: €{val:,.0f}", annotation=dict(font_size=10, font_color=color))
    
    # 2: He price
    fig.add_trace(go.Histogram(x=df["he_price_eur_kg"], nbinsx=50, name="He Price",
        marker_color="#7C3AED", opacity=0.8, showlegend=False), row=1, col=2)
    
    # 3: Availability
    fig.add_trace(go.Histogram(x=df["beam_availability_pct"], nbinsx=40, name="Availability",
        marker_color="#059669", opacity=0.8, showlegend=False), row=2, col=1)
    
    # 4: Scatter He loss vs cost
    fig.add_trace(go.Scatter(x=df["total_he_loss_kg"], y=df["total_cost_eur"],
        mode="markers", marker=dict(size=3, color=df["he_price_eur_kg"],
        colorscale="Viridis", showscale=True, colorbar=dict(title="He €/kg", len=0.4, y=0.2)),
        name="Runs", showlegend=False), row=2, col=2)
    
    fig.update_layout(height=700, title=dict(text=f"Monte Carlo Cost Analysis — {len(df):,} Simulations", font=dict(size=16)))
    return _save_plot(fig, "monte_carlo_cost_distribution")


def plot_tornado(mc_results):
    """Sensitivity tornado chart."""
    tornado = mc_results["baseline"]["tornado"]
    base = tornado["base"].iloc[0]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=tornado["variable"], x=tornado["low"] - base,
        orientation="h", name="Low (P10)", marker_color="#10B981",
        hovertemplate="%{y}: €%{x:,.0f} from base<extra>Low</extra>",
    ))
    fig.add_trace(go.Bar(
        y=tornado["variable"], x=tornado["high"] - base,
        orientation="h", name="High (P90)", marker_color="#EF4444",
        hovertemplate="%{y}: €%{x:,.0f} from base<extra>High</extra>",
    ))
    fig.update_layout(
        barmode="overlay", height=400,
        title=dict(text="Sensitivity Tornado — Total Cost Drivers", font=dict(size=16)),
        xaxis_title="Deviation from Median Cost (€)",
        yaxis=dict(autorange="reversed"),
    )
    return _save_plot(fig, "sensitivity_tornado")


def plot_supplier_comparison():
    """Supplier comparison bar chart."""
    data = SUPPLIER_COMPARISON
    suppliers = [d["supplier"] for d in data]
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Cost Comparison (€)", "Leak Rate Comparison"))
    
    fig.add_trace(go.Bar(x=suppliers, y=[d["cost_eur"] for d in data],
        marker_color=["#1E3A8A", "#7C3AED"], text=[f"€{d['cost_eur']:,}" for d in data],
        textposition="outside", name="CAPEX"), row=1, col=1)
    
    # Leak rates
    lr_labels = ["To Ambient", "Across Restriction"]
    fig.add_trace(go.Bar(x=lr_labels, y=[1e-5, 1e-4], name="Meca Inox",
        marker_color="#1E3A8A", opacity=0.8), row=1, col=2)
    fig.add_trace(go.Bar(x=lr_labels, y=[1e-9, 1e-4], name="Swagelok",
        marker_color="#7C3AED", opacity=0.8), row=1, col=2)
    
    fig.update_yaxes(type="log", row=1, col=2, title="mbar·L/s")
    fig.update_layout(height=400, title=dict(text="Supplier Comparison — Meca Inox vs Swagelok", font=dict(size=16)))
    return _save_plot(fig, "supplier_comparison")


def plot_risk_heatmap():
    """Risk matrix heatmap (likelihood × impact)."""
    risks = risk_matrix_data()
    
    # Build 5x5 matrix
    matrix = np.zeros((5, 5))
    labels = [["" for _ in range(5)] for _ in range(5)]
    for r in risks:
        li, im = r["likelihood"] - 1, r["impact"] - 1
        matrix[li][im] += 1
        labels[li][im] += r["id"].split("-")[1] + " "
    
    fig = go.Figure(go.Heatmap(
        z=matrix, x=["1-Negligible", "2-Minor", "3-Moderate", "4-Major", "5-Critical"],
        y=["1-Rare", "2-Unlikely", "3-Possible", "4-Likely", "5-Almost Certain"],
        text=[[c.strip() for c in row] for row in labels],
        texttemplate="%{text}", colorscale=[[0, "#ECFDF5"], [0.3, "#FEF3C7"], [0.6, "#FED7AA"], [1, "#FEE2E2"]],
        showscale=False, hovertemplate="Likelihood: %{y}<br>Impact: %{x}<br>Count: %{z}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Risk Matrix — Likelihood × Impact", font=dict(size=16)),
        xaxis_title="Impact", yaxis_title="Likelihood", height=450,
    )
    return _save_plot(fig, "risk_heatmap")


def plot_waterfall_cost(mc_results):
    """Waterfall chart: cost breakdown."""
    stats = mc_results["baseline"]["stats"]
    he_cost = stats["he_cost_eur"]["p50"]
    repl_cost = stats["replacement_cost_eur"]["p50"]
    total = stats["total_cost_eur"]["p50"]
    
    fig = go.Figure(go.Waterfall(
        x=["Helium Loss", "Valve Replacements", "Total Annual Cost"],
        y=[he_cost, repl_cost, total],
        measure=["relative", "relative", "total"],
        text=[f"€{he_cost:,.0f}", f"€{repl_cost:,.0f}", f"€{total:,.0f}"],
        textposition="outside",
        connector=dict(line=dict(color="#9CA3AF", width=1.5)),
        increasing=dict(marker_color="#1E3A8A"),
        totals=dict(marker_color="#059669"),
    ))
    fig.update_layout(
        title=dict(text="Annual Cost Breakdown (P50 Estimate)", font=dict(size=16)),
        yaxis_title="Cost (€)", height=400,
    )
    return _save_plot(fig, "cost_waterfall")


def plot_scenario_comparison(mc_results):
    """Box plot comparing all scenarios."""
    dfs = []
    for key, data in mc_results.items():
        d = data["df"][["total_cost_eur"]].copy()
        d["scenario"] = data["config"].name
        dfs.append(d)
    combined = pd.concat(dfs)
    
    fig = go.Figure()
    colors = {"Baseline": "#1E3A8A", "Geopolitical Crisis": "#EF4444",
              "Supply Chain Disruption": "#F59E0B", "Accelerated Failure": "#7C3AED"}
    for scenario in combined["scenario"].unique():
        vals = combined[combined["scenario"] == scenario]["total_cost_eur"]
        fig.add_trace(go.Box(y=vals, name=scenario, marker_color=colors.get(scenario, "#6B7280"),
                             boxmean="sd"))
    
    fig.update_layout(
        title=dict(text="Scenario Comparison — Total Cost Distribution", font=dict(size=16)),
        yaxis_title="Total Annual Cost (€)", height=450,
    )
    return _save_plot(fig, "scenario_comparison")


def plot_gantt_maintenance():
    """Gantt chart for maintenance timeline."""
    tasks = [
        dict(Task="Cold Valve PM", Start="2026-01-01", Finish="2026-01-15", Resource="Preventive"),
        dict(Task="Warm Valve Inspection", Start="2026-03-01", Finish="2026-03-05", Resource="Preventive"),
        dict(Task="Solenoid Pilot Replace", Start="2026-04-15", Finish="2026-04-16", Resource="Corrective"),
        dict(Task="Annual Leak Test", Start="2026-06-01", Finish="2026-06-14", Resource="Inspection"),
        dict(Task="Seal Replacement (Warm)", Start="2026-07-01", Finish="2026-07-03", Resource="Preventive"),
        dict(Task="Cold Valve PM #2", Start="2026-09-01", Finish="2026-09-14", Resource="Preventive"),
        dict(Task="LOOP Recovery Drill", Start="2026-10-01", Finish="2026-10-02", Resource="Drill"),
        dict(Task="Year-End Inspection", Start="2026-12-01", Finish="2026-12-14", Resource="Inspection"),
    ]
    df = pd.DataFrame(tasks)
    colors = {"Preventive": "#1E3A8A", "Corrective": "#EF4444", "Inspection": "#F59E0B", "Drill": "#7C3AED"}
    
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Resource",
                      color_discrete_map=colors)
    fig.update_layout(
        title=dict(text="Maintenance Schedule — 2026", font=dict(size=16)),
        height=400, yaxis=dict(autorange="reversed"),
    )
    return _save_plot(fig, "maintenance_gantt")


def plot_helium_sankey():
    """Sankey diagram for helium flow & loss pathways."""
    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15, thickness=20, line=dict(color="#1E3A8A", width=0.5),
            label=["He Supply\n(600 kg/yr)", "Cold System", "Warm System",
                   "Process Use", "Cold Valve Leaks", "Warm Valve Leaks",
                   "Recovery System", "Loss to Ambient", "Recovered He"],
            color=["#1E3A8A", "#3B82F6", "#60A5FA", "#10B981",
                   "#EF4444", "#F59E0B", "#8B5CF6", "#DC2626", "#059669"],
        ),
        link=dict(
            source=[0, 0, 1, 2, 1, 2, 4, 5, 6],
            target=[1, 2, 3, 3, 4, 5, 6, 7, 8],
            value=[400, 200, 350, 180, 50, 20, 40, 30, 40],
            color=["rgba(30,58,138,0.2)"] * 9,
        ),
    ))
    fig.update_layout(
        title=dict(text="Helium Flow & Loss Pathways (Estimated Annual)", font=dict(size=16)),
        height=450,
    )
    return _save_plot(fig, "helium_sankey")


# ═══════════════════════════════════════════════════════════
# HERO PAGE BUILDERS
# ═══════════════════════════════════════════════════════════

def build_index(mc_results):
    """Hub page with hero navigation."""
    stats = mc_results["baseline"]["stats"]
    body = f"""
{_breadcrumb("Dashboard Hub", "Home")}
<div class="slide">
  <h2>🏠 QPLANT Cryogenic Dashboard — Navigation Hub</h2>
  <p style="color:{COLORS['text_light']};margin-bottom:1.5rem">OUTPUT_2_DMAIC_REFINED v{VERSION} — Enhanced Multi-Tier Professional Dashboard with Monte Carlo Cost Analysis</p>
  <div class="kpi-grid">
    {_kpi(f"€{stats['total_cost_eur']['p50']:,.0f}", "Median Annual Cost (P50)", "blue")}
    {_kpi(f"{stats['total_he_loss_kg']['p50']:,.1f} kg", "Median He Loss/Year", "amber")}
    {_kpi(f"{stats['beam_availability_pct']['p50']:.1f}%", "Beam Availability (P50)", "green")}
    {_kpi(f"410", "Total Valve Count", "blue")}
  </div>
</div>
<div class="slide">
  <h3>Hero Domains</h3>
  <div class="kpi-grid">
"""
    for h in HERO_TABS:
        body += f"""<a href="heroes/{h['id']}.html" style="text-decoration:none">
  <div class="kpi kpi-blue" style="cursor:pointer;transition:transform 0.2s" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">
    <div class="value" style="font-size:2rem">{h['icon']}</div>
    <div class="label" style="font-size:0.85rem;font-weight:700;color:{COLORS['primary']}">{h['label']}</div>
    <div style="font-size:0.72rem;color:{COLORS['text_light']};margin-top:0.3rem">{h['desc']}</div>
  </div></a>"""
    body += """</div></div>
<div class="slide">
  <h3>Quick Access</h3>
  <div class="kpi-grid">
    <a href="visualizations/monte_carlo_cost_distribution.html" style="text-decoration:none"><div class="kpi kpi-amber" style="cursor:pointer"><div class="value">📊</div><div class="label">Monte Carlo Analysis</div></div></a>
    <a href="visualizations/enhanced_leak_rate_comparison.html" style="text-decoration:none"><div class="kpi kpi-green" style="cursor:pointer"><div class="value">📈</div><div class="label">Leak Rate Charts</div></div></a>
    <a href="visualizations/risk_heatmap.html" style="text-decoration:none"><div class="kpi kpi-red" style="cursor:pointer"><div class="value">⚠️</div><div class="label">Risk Matrix</div></div></a>
    <a href="visualizations/helium_sankey.html" style="text-decoration:none"><div class="kpi kpi-blue" style="cursor:pointer"><div class="value">🔄</div><div class="label">He Flow Sankey</div></div></a>
  </div>
</div>"""
    return _page("Navigation Hub", body)


def build_hero_interface():
    body = f"""
{_breadcrumb("INTERFACE")}
{_tier_nav(("1","Tier 1 — Overview"),("2","Tier 2 — Boundaries"),("3","Tier 3 — Technical Detail"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>🔗 INTERFACE — System Boundaries & Valve Locations</h2>
  <div class="kpi-grid">
    {_kpi("410", "Total Valves", "blue")}
    {_kpi("210", "Cold Valves (≤80K)", "blue")}
    {_kpi("200", "Warm Valves (≥273K)", "amber")}
    {_kpi("4", "Valve Sub-Classes", "green")}
  </div>
  <h3>System Architecture</h3>
  <p>The QPLANT cryogenic helium system interfaces with the MYRRHA proton beam facility. Helium serves as the primary coolant for superconducting magnets and beam targets. The system boundary encompasses:</p>
  <ul style="margin:0.5rem 0 0 1.5rem">
    <li><strong>Cold box</strong> — Cryogenic distribution at 4K-80K</li>
    <li><strong>Warm distribution</strong> — Gas handling at 273K-373K</li>
    <li><strong>Recovery system</strong> — Helium recapture and purification</li>
    <li><strong>Interface points</strong> — Terminal connections per QPLANT_Interface doc</li>
  </ul>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>Interface Boundaries — Detailed</h2>
  <h3>Valve Location Classification</h3>
  <table><thead><tr><th>Zone</th><th>Temp Range</th><th>Valve Count</th><th>Sub-Classes</th><th>Interface Type</th></tr></thead><tbody>
    <tr><td>Cold Box Interior</td><td>1.5 — 80 K</td><td>150</td><td>Q1, Q2d</td><td>Welded / VCR</td></tr>
    <tr><td>Cold-Warm Transition</td><td>80 — 273 K</td><td>60</td><td>Q2d</td><td>Flanged</td></tr>
    <tr><td>Warm Process</td><td>273 — 323 K</td><td>180</td><td>W1d, W3</td><td>Swagelok / Flanged</td></tr>
    <tr><td>Instrumentation</td><td>273 — 373 K</td><td>20</td><td>W3</td><td>Swagelok 1/4"-1/2"</td></tr>
  </tbody></table>
</div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Interface — Technical Detail</h2>
  <h3>Terminal Point Specifications (from QPLANT_Interface and Terminal Points)</h3>
  <table><thead><tr><th>Parameter</th><th>Value</th><th>Reference</th></tr></thead><tbody>
    <tr><td>Piping standard</td><td>ASME B31.3</td><td>ACC NF specification</td></tr>
    <tr><td>Tubing connections</td><td>Swagelok compression fittings</td><td>SS-42GSE series</td></tr>
    <tr><td>Welded joints</td><td>Orbital TIG per ASME BPE</td><td>DN06-DN50</td></tr>
    <tr><td>He leak test method</td><td>EN 13185:2001</td><td>All connections</td></tr>
    <tr><td>Purge gas</td><td>Ar 99.999% (5N)</td><td>Welding procedure</td></tr>
  </tbody></table>
  <h3>Exhaust System Interface (QPLANT_HV02)</h3>
  <p>The HV02 exhaust interface for KAEZER compressor system provides the boundary condition for warm helium gas handling, including pressure relief and vent connections.</p>
</div></div>"""
    return _page("INTERFACE", body, "interface", is_hero=True)


def build_hero_control():
    vc_html = ""
    for vc in VALVE_CLASSES:
        note = f"<br><em style='color:{COLORS['danger']}'>{vc.get('note','')}</em>" if vc.get("note") else ""
        vc_html += f"<tr><td><strong>{vc['sub_class']}</strong></td><td>{vc['temp_range_k']} K</td>"
        vc_html += f"<td>{vc['actuation']}</td><td>{vc['electrical_valve']}</td>"
        vc_html += f"<td>{vc['position_control']}</td><td>{_badge('required') if vc.get('radiation_hardness')=='required' else _badge('review')}{note}</td></tr>"
    
    body = f"""
{_breadcrumb("CONTROL")}
{_tier_nav(("1","Tier 1 — Overview"),("2","Tier 2 — Actuation"),("3","Tier 3 — Fail-Safe Logic"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>⚙️ CONTROL — Actuation Methods & Automation</h2>
  <div class="kpi-grid">
    {_kpi("3", "Actuation Types", "blue")}
    {_kpi("Pneumatic", "Primary Method", "green")}
    {_kpi("24V", "Standard Voltage", "amber")}
    {_kpi("6 bar(g)", "Instrument Air", "blue")}
  </div>
  <h3>Actuation Overview</h3>
  <table><thead><tr><th>Sub-Class</th><th>Temp Range</th><th>Actuation</th><th>Pilot Valve</th><th>Position Control</th><th>Rad. Hardness</th></tr></thead>
  <tbody>{vc_html}</tbody></table>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>Actuation Methods — Detailed</h2>
  <div class="compare-grid">
    <div class="compare-card">
      <h4>🔵 Pneumatic Actuation (Q1, Q2d, W1d)</h4>
      <ul style="margin:0.5rem 0 0 1rem"><li>Requires instrument air supply (6 bar(g))</li>
      <li>Fail-safe position on air loss</li><li>Indirect actuation via pilot valve</li>
      <li>Q1: Piezo pilot + electronic positioner (0-100%)</li>
      <li>Q2d: Piezo pilot + limit switches</li><li>W1d: Solenoid pilot + limit switch 0%</li></ul>
    </div>
    <div class="compare-card">
      <h4>🟡 Direct Electrical (W3)</h4>
      <ul style="margin:0.5rem 0 0 1rem"><li>No instrument air required</li>
      <li>24V solenoid direct actuation</li><li>Limit switch at 0% (closed)</li>
      <li>Linear Kv characteristic</li><li>Radiation hardness: not required</li>
      <li>Note: tbc if Asco or Bürkert can be 1LS</li></ul>
    </div>
  </div>
</div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Fail-Safe Logic — Technical</h2>
  <h3>LOOP (Loss of Instrument Air) Response</h3>
  <table><thead><tr><th>Sub-Class</th><th>Fail Position</th><th>Recovery Action</th><th>Impact</th></tr></thead><tbody>
    <tr><td>Q1</td><td>Fail-closed</td><td>Restore air, verify positioner</td><td>Process isolation</td></tr>
    <tr><td>Q2d</td><td>Fail-closed</td><td>Restore air, check limits</td><td>Process isolation</td></tr>
    <tr><td>W1d</td><td>Fail-closed (spring return)</td><td>Restore air, re-energize solenoid</td><td>Warm process shutdown</td></tr>
    <tr><td>W3</td><td>De-energized position</td><td>Restore power, re-energize</td><td>Minimal (no air dependency)</td></tr>
  </tbody></table>
  <h3>Position Feedback Matrix</h3>
  <table><thead><tr><th>Sub-Class</th><th>Feedback Type</th><th>Signal</th><th>Remote</th></tr></thead><tbody>
    <tr><td>Q1</td><td>Continuous 0-100%</td><td>4-20 mA via positioner</td><td>Yes (remote electronics)</td></tr>
    <tr><td>Q2d</td><td>Limit switches 0% & 100%</td><td>Digital</td><td>No</td></tr>
    <tr><td>W1d</td><td>Limit switch 0%</td><td>Digital</td><td>No</td></tr>
    <tr><td>W3</td><td>Limit switch 0%</td><td>Analogue 4-20 mA</td><td>No</td></tr>
  </tbody></table>
</div></div>"""
    return _page("CONTROL", body, "control", is_hero=True)


def build_hero_design(mc_results):
    # Build conversion grid
    grid = build_conversion_grid(
        leak_classes=[1e-9, 1e-8, 1e-5, 1e-4],
        temperatures_k=[4, 20, 80, 300],
        pressures_bar_abs=[1, 5, 12],
    )
    grid_short = grid[["leak_rate_mbar_l_s", "temperature_K", "pressure_bar_abs",
                        "mass_flow_g_year"]].copy()
    grid_short.columns = ["Leak Rate (mbar·L/s)", "Temperature (K)", "Pressure (bar)", "Mass Loss (g/yr)"]
    
    body = f"""
{_breadcrumb("DESIGN")}
{_tier_nav(("1","Tier 1 — Overview"),("2","Tier 2 — Leak Classes"),("3","Tier 3 — Calculations"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>📐 DESIGN — Engineering Specifications</h2>
  <div class="kpi-grid">
    {_kpi("1×10⁻⁹", "Ambient Leak Spec (mbar·L/s)", "blue")}
    {_kpi("1×10⁻⁴", "Restriction Leak Spec", "amber")}
    {_kpi("4", "Valve Sub-Classes", "green")}
    {_kpi("DEROGATION", "Warm Valve Status", "red")}
  </div>
  <h3>Key Design Decisions</h3>
  <ul style="margin:0.5rem 0 0 1.5rem">
    <li>All valve classes specify <strong>1×10⁻⁹ mbar·L/s</strong> max leak to ambient</li>
    <li>Warm valves (W1d): Meca Inox <strong>does NOT comply</strong> with 1×10⁻⁹ — derogation requested</li>
    <li>Max leak across restriction: <strong>1×10⁻⁴ mbar·L/s</strong> (all classes)</li>
    <li>Action items: Create new sub-class, GBO calculation, evaluate Cryoworld variants</li>
  </ul>
  <div class="plot-container"><iframe src="../visualizations/enhanced_leak_rate_comparison.html"></iframe></div>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>Leak Class Definitions</h2>
  <table><thead><tr><th>Class</th><th>Sub-Class</th><th>Max Leak Ambient</th><th>Max Leak Restriction</th><th>Temp Range</th><th>Status</th></tr></thead><tbody>
    <tr><td>CV</td><td>Q1</td><td>1.0E-09</td><td>1.0E-04</td><td>1.5 — 373 K</td><td>{_badge('ACCEPT')}</td></tr>
    <tr><td>CV</td><td>Q2d</td><td>1.0E-09</td><td>1.0E-04</td><td>1.5 — 373 K</td><td>{_badge('ACCEPT')}</td></tr>
    <tr><td>CV</td><td>W1d</td><td>1.0E-09</td><td>1.0E-04</td><td>273 — 323 K</td><td>{_badge('RISK')} Derogation</td></tr>
    <tr><td>CV</td><td>W3</td><td>1.0E-09</td><td>1.0E-04</td><td>273 — 323 K</td><td>{_badge('REVIEW')}</td></tr>
  </tbody></table>
  <h3>Warm Valve Derogation (Section 2.3.4)</h3>
  <div class="compare-grid">
    <div class="compare-card" style="border-color:{COLORS['danger']}; background:{COLORS['red_50']}">
      <h4>⚠️ Issue</h4>
      <p>Meca Inox ball valves with HDPE seals <strong>do NOT comply</strong> with He leak rate to ambient of 1×10⁻⁹ mbar·l/s. This is considered <strong>unnecessary stringent</strong> for the purpose and non-industry standard.</p>
    </div>
    <div class="compare-card" style="border-color:{COLORS['accent']}; background:{COLORS['amber_50']}">
      <h4>📋 Actions Required</h4>
      <ul style="margin:0.5rem 0 0 1rem">
        <li>Create a new sub-class with higher leak rate of He to air</li>
        <li>Ask GBO to perform short calculation</li>
        <li>Look into spec of proposed variants from Cryoworld</li>
      </ul>
    </div>
  </div>
</div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Conversion Grid — Leak Rate to Mass Loss</h2>
  <details open><summary>Full Conversion Table (48 combinations)</summary>
  {_df_to_html(grid_short)}
  </details>
  <h3>Dimensional Proof (Reference Point)</h3>"""
    proof = dimensional_proof(1e-5, 4.0, 12.0)
    body += "<table><thead><tr><th>Step</th><th>Value</th><th>Unit</th></tr></thead><tbody>"
    units = {"q_input_mbar_l_s": "mbar·L/s", "q_si_pa_m3_s": "Pa·m³/s", "pressure_ratio": "—",
             "temperature_k": "K", "n_dot_mol_s": "mol/s", "m_dot_g_s": "g/s",
             "m_dot_g_day": "g/day", "m_dot_g_year": "g/year"}
    for k, v in proof.items():
        body += f"<tr><td>{k}</td><td>{v:.6e}</td><td>{units.get(k,'')}</td></tr>"
    body += "</tbody></table></div></div>"
    return _page("DESIGN", body, "design", is_hero=True)


def build_hero_cost(mc_results):
    stats = mc_results["baseline"]["stats"]
    
    # Scenario comparison table
    scenario_rows = ""
    for key, data in mc_results.items():
        s = data["stats"]["total_cost_eur"]
        scenario_rows += f"""<tr><td><strong>{data['config'].name}</strong></td>
          <td>€{s['p10']:,.0f}</td><td>€{s['p50']:,.0f}</td><td>€{s['p90']:,.0f}</td>
          <td>€{s['mean']:,.0f}</td><td>€{s['std']:,.0f}</td></tr>"""
    
    body = f"""
{_breadcrumb("COST")}
{_tier_nav(("1","Tier 1 — Executive"),("2","Tier 2 — Monte Carlo"),("3","Tier 3 — Sensitivity"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>💰 COST — Monte Carlo Analysis & TCO</h2>
  <div class="kpi-grid">
    {_kpi(f"€{stats['total_cost_eur']['p50']:,.0f}", "Median Total Cost (P50)", "blue")}
    {_kpi(f"€{stats['total_cost_eur']['p10']:,.0f}", "Best Case (P10)", "green")}
    {_kpi(f"€{stats['total_cost_eur']['p90']:,.0f}", "Worst Case (P90)", "red")}
    {_kpi(f"€{stats['he_cost_eur']['p50']:,.0f}", "He Cost Median", "amber")}
  </div>
  <h3>Scenario Summary</h3>
  <table><thead><tr><th>Scenario</th><th>P10</th><th>P50</th><th>P90</th><th>Mean</th><th>Std Dev</th></tr></thead>
  <tbody>{scenario_rows}</tbody></table>
  <div class="plot-container"><iframe src="../visualizations/cost_waterfall.html"></iframe></div>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>Monte Carlo Simulation Results</h2>
  <p><strong>10,000 iterations</strong> using triangular He price distribution (€{SCENARIOS['baseline'].he_price_min:.0f} / €{SCENARIOS['baseline'].he_price_mode:.0f} / €{SCENARIOS['baseline'].he_price_max:.0f} per kg)</p>
  <div class="plot-container"><iframe src="../visualizations/monte_carlo_cost_distribution.html" style="height:720px"></iframe></div>
  <h3>Distribution Parameters</h3>
  <table><thead><tr><th>Parameter</th><th>Distribution</th><th>Low</th><th>Mode</th><th>High</th></tr></thead><tbody>
    <tr><td>Helium price (€/kg)</td><td>Triangular</td><td>€117</td><td>€120</td><td>€300</td></tr>
    <tr><td>Valve failure rate</td><td>Normal (from MTBF)</td><td>—</td><td>MTBF-based</td><td>—</td></tr>
    <tr><td>Replacement cost</td><td>Uniform ±20%</td><td>0.8×</td><td>1.0×</td><td>1.2×</td></tr>
    <tr><td>He loss variation</td><td>Uniform ±20%</td><td>0.8×</td><td>1.0×</td><td>1.2×</td></tr>
  </tbody></table>
  <div class="plot-container"><iframe src="../visualizations/scenario_comparison.html"></iframe></div>
</div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Sensitivity Analysis</h2>
  <div class="plot-container"><iframe src="../visualizations/sensitivity_tornado.html"></iframe></div>
  <h3>Supplier Cost Comparison</h3>
  <div class="plot-container"><iframe src="../visualizations/supplier_comparison.html"></iframe></div>
  <h3>Detailed Supplier Table</h3>
  <table><thead><tr><th>Criteria</th><th>Meca Inox</th><th>Swagelok SS-42GSE</th></tr></thead><tbody>
    <tr><td>Leak rate (ambient)</td><td style="color:{COLORS['danger']}">{'>'} 1×10⁻⁹ (derogation)</td><td style="color:{COLORS['secondary']}">≤1×10⁻⁹ (standard)</td></tr>
    <tr><td>Leak rate (restriction)</td><td>1×10⁻⁴</td><td>1×10⁻⁴</td></tr>
    <tr><td>Actuation</td><td>Pneumatic + solenoid</td><td>Manual</td></tr>
    <tr><td>Size range</td><td>Large (DN15-DN50)</td><td>Instrumentation (1/4"-1/2")</td></tr>
    <tr><td>CAPEX (€)</td><td>€4,200</td><td>€4,700</td></tr>
    <tr><td>Material (body)</td><td>316 SS</td><td>316 SS</td></tr>
    <tr><td>Material (seal)</td><td>HDPE</td><td>UHMWPE</td></tr>
    <tr><td>Radiation hardness</td><td>Required ✓</td><td>Required ✓</td></tr>
    <tr><td>Cost relative</td><td>1.0× (baseline)</td><td>1.12× </td></tr>
  </tbody></table>
</div></div>"""
    return _page("COST", body, "cost", is_hero=True)


def build_hero_materials():
    mat = MATERIALS["316L_SS"]
    props_html = "".join(f"<tr><td>{k.replace('_',' ').title()}</td><td>{v}</td></tr>"
                         for k, v in mat["properties"].items())
    comp_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in mat["composition"].items())
    
    codes_html = "".join(f"<tr><td><strong>{c['code']}</strong></td><td>{c['title']}</td><td>{c['scope']}</td></tr>"
                         for c in CODES_STANDARDS)
    
    weld = WELDING_SPECS["orbital_tig"]
    
    body = f"""
{_breadcrumb("MATERIALS")}
{_tier_nav(("1","Tier 1 — Overview"),("2","Tier 2 — Specifications"),("3","Tier 3 — Codes & Welding"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>🧪 MATERIALS — Specifications Database</h2>
  <div class="kpi-grid">
    {_kpi("316L", "Primary Steel Grade", "blue")}
    {_kpi("Ra < 0.4 μm", "Surface Finish", "green")}
    {_kpi("Orbital TIG", "Welding Method", "amber")}
    {_kpi("DN06-DN50", "Weld Size Range", "blue")}
  </div>
  <h3>Material Summary</h3>
  <div class="compare-grid">
    <div class="compare-card"><h4>HDPE (Meca Inox seals)</h4>
      <p>Service temp: 73-393K. Density: 0.95 g/cm³. Good for warm service. Radiation resistant. Lower cost.</p></div>
    <div class="compare-card"><h4>UHMWPE (Swagelok seals)</h4>
      <p>Service temp: 73-353K. Density: 0.93 g/cm³. Superior abrasion resistance. Higher cost. Precision applications.</p></div>
  </div>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>316L Stainless Steel — Full Specification</h2>
  <div class="compare-grid">
    <div class="compare-card"><h4>Composition</h4><table><thead><tr><th>Element</th><th>Range</th></tr></thead><tbody>{comp_html}</tbody></table></div>
    <div class="compare-card"><h4>Mechanical Properties</h4><table><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>{props_html}</tbody></table></div>
  </div>
  <h3>Surface Treatment</h3>
  <table><thead><tr><th>Step</th><th>Specification</th><th>Standard</th></tr></thead><tbody>
    <tr><td>Electropolish</td><td>Ra {'<'} 0.4 μm</td><td>ASME BPE</td></tr>
    <tr><td>Post-EP wash</td><td>DI water rinse</td><td>Internal procedure</td></tr>
    <tr><td>Passivation</td><td>Per ASTM A967</td><td>ASTM A967</td></tr>
  </tbody></table>
</div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Welding & Codes</h2>
  <h3>Orbital TIG Welding Specification</h3>
  <table><thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>
    <tr><td>Method</td><td>{weld['method']}</td></tr>
    <tr><td>Size range</td><td>{weld['size_range']}</td></tr>
    <tr><td>Filler</td><td>{weld['filler']}</td></tr>
    <tr><td>Purge gas</td><td>{weld['purge_gas']}</td></tr>
    <tr><td>Interpass max</td><td>{weld['interpass_temp_max_c']}°C</td></tr>
    <tr><td>Qualification</td><td>{weld['qualification']}</td></tr>
    <tr><td>NDE</td><td>{', '.join(weld['nde_requirements'])}</td></tr>
  </tbody></table>
  <h3>Applicable Codes & Standards</h3>
  <table><thead><tr><th>Code</th><th>Title</th><th>Scope</th></tr></thead><tbody>{codes_html}</tbody></table>
</div></div>"""
    return _page("MATERIALS", body, "materials", is_hero=True)


def build_hero_risk():
    risks = risk_matrix_data()
    risk_rows = ""
    for r in risks:
        risk_rows += f"""<tr><td>{r['id']}</td><td>{_badge(r['status'])}</td><td>{r['category']}</td>
          <td><strong>{r['title']}</strong></td><td>{r['likelihood']}</td><td>{r['impact']}</td>
          <td style="font-weight:700;color:{'#EF4444' if r['risk_score']>=15 else '#F59E0B' if r['risk_score']>=9 else '#10B981'}">{r['risk_score']}</td>
          <td>{r['owner']}</td></tr>"""
    
    body = f"""
{_breadcrumb("RISK")}
{_tier_nav(("1","Tier 1 — Overview"),("2","Tier 2 — Register"),("3","Tier 3 — Scenarios"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>⚠️ RISK — Geopolitical, Operational & Reliability</h2>
  <div class="kpi-grid">
    {_kpi(str(len(risks)), "Total Risks", "blue")}
    {_kpi(str(sum(1 for r in risks if r['risk_score']>=15)), "Critical (≥15)", "red")}
    {_kpi(str(sum(1 for r in risks if r['status']=='OPEN')), "Open Risks", "amber")}
    {_kpi(str(sum(1 for r in risks if r['status']=='MITIGATED')), "Mitigated", "green")}
  </div>
  <div class="plot-container"><iframe src="../visualizations/risk_heatmap.html"></iframe></div>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>Risk Register</h2>
  <table style="font-size:0.78rem"><thead><tr><th>ID</th><th>Status</th><th>Category</th><th>Title</th><th>L</th><th>I</th><th>Score</th><th>Owner</th></tr></thead>
  <tbody>{risk_rows}</tbody></table>
  <details><summary>🔍 Mitigation Details</summary><div>"""
    for r in risks:
        body += f"<p><strong>{r['id']} — {r['title']}:</strong> {r['mitigation']}</p>"
    body += """</div></details></div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Geopolitical & Supply Risk Scenarios</h2>
  <div class="compare-grid">
    <div class="compare-card" style="border-color:#EF4444;background:#FEF2F2">
      <h4>🌍 Iran Conflict Scenario</h4>
      <p>Military escalation disrupts Qatar helium production (30% global supply). Algeria and US sources insufficient. He price spike 2-3× baseline.</p>
      <p><strong>Impact:</strong> €/kg rises from €120 to €300+. Annual cost increase: 150-200%.</p>
    </div>
    <div class="compare-card" style="border-color:#F59E0B;background:#FFFBEB">
      <h4>⛽ LNG Market Coupling</h4>
      <p>Helium is byproduct of LNG processing. LNG market disruption cascades to He supply. Price correlation with natural gas futures.</p>
      <p><strong>Mitigation:</strong> He-specific supply contracts decoupled from LNG spot pricing.</p>
    </div>
  </div>
  <h3>Beam Availability Impact</h3>"""
    beam = beam_impact_analysis()
    body += "<table><thead><tr><th>Scenario</th><th>Beam Trips/yr</th><th>MDT (h)</th><th>Lost Hours</th><th>Financial Impact</th></tr></thead><tbody>"
    for bid, bdata in beam.items():
        body += f"<tr><td>{bdata['name']}</td><td>{bdata['beam_trips']}</td><td>{bdata['mdt_hours']}</td><td>{bdata['lost_beam_hours']}</td><td>€{bdata['financial_impact_eur']:,}</td></tr>"
    body += "</tbody></table></div></div>"
    return _page("RISK", body, "risk", is_hero=True)


def build_hero_operations():
    body = f"""
{_breadcrumb("OPERATIONS")}
{_tier_nav(("1","Tier 1 — Overview"),("2","Tier 2 — Reliability"),("3","Tier 3 — Maintenance"))}
<div id="tier-1" class="tier-content">
<div class="slide">
  <h2>🔧 OPERATIONS — MTBF, MTTR, MDT & Maintenance</h2>
  <div class="kpi-grid">
    {_kpi("60,000 h", "Cold Valve MTBF", "blue")}
    {_kpi("4 h", "Baseline MTTR", "green")}
    {_kpi("12 h", "Baseline MDT", "amber")}
    {_kpi("99%", "Target Availability", "blue")}
  </div>
  <h3>Operational Scenarios</h3>
  <table><thead><tr><th>Scenario</th><th>Availability</th><th>MTTR</th><th>MDT</th><th>Beam Trips/yr</th><th>He Loss (kg/yr)</th></tr></thead><tbody>"""
    for ops in OPERATIONAL_SCENARIOS:
        body += f"<tr><td><strong>{ops['name']}</strong></td><td>{ops['availability_pct']}%</td><td>{ops['mttr_hours']}h</td><td>{ops['mdt_hours']}h</td><td>{ops['beam_trips_per_year']}</td><td>{ops['he_loss_kg_year']}</td></tr>"
    body += """</tbody></table>
  <div class="plot-container"><iframe src="../visualizations/helium_sankey.html"></iframe></div>
</div></div>
<div id="tier-2" class="tier-content" style="display:none">
<div class="slide">
  <h2>Reliability Data</h2>
  <table><thead><tr><th>Component</th><th>MTBF (h)</th><th>MTTR (h)</th><th>MDT (h)</th><th>λ (per 10⁶h)</th><th>Avail. %</th><th>Spare %</th><th>PM Interval</th></tr></thead><tbody>"""
    for comp, rd in RELIABILITY_DATA.items():
        body += f"""<tr><td>{comp.replace('_',' ').title()}</td><td>{rd['mtbf_hours']:,}</td>
          <td>{rd['mttr_hours']}</td><td>{rd['mdt_hours']}</td><td>{rd['failure_rate_per_1e6h']}</td>
          <td>{rd['availability_pct']:.3f}</td><td>{rd['spare_ratio']*100:.0f}%</td>
          <td>{rd['preventive_interval_months']} months</td></tr>"""
    body += """</tbody></table>
  <h3>Spare Parts Strategy</h3>
  <table><thead><tr><th>Component</th><th>Fleet Size</th><th>Spare Ratio</th><th>Spares Needed</th><th>Cost/Unit (€)</th><th>Spares Cost (€)</th></tr></thead><tbody>
    <tr><td>Cold cryogenic valve</td><td>210</td><td>10%</td><td>21</td><td>€8,900</td><td>€186,900</td></tr>
    <tr><td>Warm pneumatic (Meca Inox)</td><td>180</td><td>5%</td><td>9</td><td>€4,200</td><td>€37,800</td></tr>
    <tr><td>Warm manual (Swagelok)</td><td>20</td><td>3%</td><td>1</td><td>€4,700</td><td>€4,700</td></tr>
    <tr><td>Solenoid pilot valves</td><td>230</td><td>15%</td><td>35</td><td>€350</td><td>€12,250</td></tr>
    <tr><td colspan="5" style="text-align:right;font-weight:700">Total Spares Investment</td><td style="font-weight:700">€241,650</td></tr>
  </tbody></table>
</div></div>
<div id="tier-3" class="tier-content" style="display:none">
<div class="slide">
  <h2>Maintenance Schedule</h2>
  <div class="plot-container"><iframe src="../visualizations/maintenance_gantt.html"></iframe></div>
  <h3>Preventive Maintenance Tasks</h3>
  <table><thead><tr><th>Task</th><th>Interval</th><th>Duration</th><th>Scope</th></tr></thead><tbody>
    <tr><td>Cold valve seat inspection</td><td>24 months</td><td>14 days</td><td>All cold valves (during planned outage)</td></tr>
    <tr><td>Warm valve seal check</td><td>36 months</td><td>5 days</td><td>All Meca Inox + Swagelok</td></tr>
    <tr><td>Solenoid pilot replacement</td><td>18 months</td><td>1 day per 50 valves</td><td>Preventive swap program</td></tr>
    <tr><td>Leak rate verification</td><td>12 months</td><td>14 days</td><td>100% per EN 13185</td></tr>
    <tr><td>LOOP recovery drill</td><td>12 months</td><td>2 days</td><td>Full system test</td></tr>
  </tbody></table>
</div></div>"""
    return _page("OPERATIONS", body, "operations", is_hero=True)


# ═══════════════════════════════════════════════════════════
# SPEAKER NOTES GENERATOR
# ═══════════════════════════════════════════════════════════

def write_speaker_notes(mc_results):
    stats = mc_results["baseline"]["stats"]
    
    notes = {
        "slide_001_title": f"""# QPLANT Cryogenic Dashboard — Title Slide
## Key Talking Points
- OUTPUT_2_DMAIC_REFINED v{VERSION} — major enhancement from baseline
- Monte Carlo cost analysis with 10,000 simulations
- 7 hero domains covering all engineering aspects
- Professional presentation-quality output

## Audience
- Executive summary for management
- Technical depth available via tier navigation
""",
        "slide_002_interface_overview": """# INTERFACE — System Boundaries
## Key Points
- 410 total valves: 210 cold (≤80K) + 200 warm (≥273K)
- 4 valve sub-classes: Q1, Q2d, W1d, W3
- System boundary: cold box → warm distribution → recovery
- Terminal points per QPLANT_Interface and Terminal Points document

## Q&A Prep
- Q: Why 4 sub-classes? A: Different temperature ranges and actuation needs
- Q: What's the cold/warm split? A: ~50/50, but cold valves are more expensive
""",
        "slide_003_control": """# CONTROL — Actuation Methods
## Key Points
- Primary actuation: Pneumatic (indirect via pilot valve)
- Q1 uses piezo pilot with electronic positioner (0-100%)
- W1d/W3 use solenoid (direct or pilot)
- All pneumatic valves require 6 bar(g) instrument air
- LOOP event: all pneumatic valves go to fail-safe position

## Important
- W3 is direct-electrical: NO air dependency
- Radiation hardness NOT required for W3
""",
        "slide_004_design": """# DESIGN — Engineering Specifications
## Critical Issue: Warm Valve Derogation
- Meca Inox ball valves do NOT comply with 1×10⁻⁹ mbar·l/s
- This spec is considered "unnecessary stringent" by supplier
- Action: Create new sub-class, GBO calculation, Cryoworld variants

## Leak Rate Summary
- All classes: 1×10⁻⁹ to ambient (spec'd but not met by warm valves)
- All classes: 1×10⁻⁴ across restriction
- Temperature sensitivity: 4K loss >> 300K loss for same leak rate
""",
        "slide_005_cost": f"""# COST — Monte Carlo Analysis
## Key Numbers (Baseline Scenario)
- Median total cost (P50): €{stats['total_cost_eur']['p50']:,.0f}
- Best case (P10): €{stats['total_cost_eur']['p10']:,.0f}
- Worst case (P90): €{stats['total_cost_eur']['p90']:,.0f}
- He price distribution: Triangular €117/€120/€300 per kg

## Scenarios Modeled
1. Baseline: Standard operations
2. Geopolitical: Iran conflict, 30% disruption probability
3. Supply chain: Extended MTTR (8h vs 4h)
4. Accelerated failure: 1.5× failure rate

## Assumptions
- 10,000 Monte Carlo iterations
- He price as triangular distribution (€/kg, not €k/kg)
- Valve failure from Poisson distribution (MTBF-based)
- ±20% variation on replacement costs and He loss
""",
        "slide_006_materials": """# MATERIALS — 316L SS & Seal Specifications
## Key Points
- Primary material: 316L stainless steel (low carbon for weldability)
- Surface finish: Electropolished Ra < 0.4 μm
- Post-treatment: DI water wash + ASTM A967 passivation
- Seals: HDPE (Meca Inox) or UHMWPE (Swagelok)

## Welding
- Orbital TIG (GTAW) for DN06-DN50
- Filler: ER316L, Purge: Ar 99.999%
- Standards: ASME BPE + ASME B31.3
""",
        "slide_007_risk": """# RISK — Geopolitical & Operational
## Top Risks (Score ≥ 15)
- RISK-001: Iran Conflict → Helium Supply (Score: 20)
- RISK-010: Beam Downtime from Valve Failure (Score: 15)

## Geopolitical Context
- Qatar/Iran produce ~30% of global helium
- He is byproduct of LNG processing
- Price spike model: 2.5× multiplier during disruption

## Beam Impact
- Each QPLANT trip: ~12h MDT
- Baseline: 3 trips/year = 36 lost beam hours
- €15,000/hour estimated beam time value
""",
        "slide_008_operations": """# OPERATIONS — Maintenance Strategy
## Reliability Targets
- Cold valve MTBF: 60,000h, MTTR: 4h, MDT: 12h
- Warm pneumatic: MTBF 80,000h, MTTR: 2h
- Solenoid pilots: MTBF 50,000h (highest failure rate)

## Spare Parts Investment
- Total: ~€241,650
- Cold valves dominate (€186,900)
- Solenoid pilot program most impactful for reliability

## Maintenance Schedule
- Annual leak test (EN 13185): 14 days
- Cold valve PM: every 24 months (during outage)
- LOOP recovery drill: annual
""",
    }
    
    for name, content in notes.items():
        (NOTES / f"{name}.md").write_text(content)
    return list(notes.keys())


# ═══════════════════════════════════════════════════════════
# MAIN BUILD
# ═══════════════════════════════════════════════════════════

def build():
    print(f"{'='*60}")
    print(f"  OUTPUT_2_DMAIC_REFINED v{VERSION}")
    print(f"  Building MAPPING_HEROES Dashboard")
    print(f"{'='*60}")
    
    # CSS & JS
    print("  [1/8] Writing CSS & JS assets...")
    write_css()
    write_js()
    
    # Monte Carlo
    print("  [2/8] Running Monte Carlo simulations (10,000 × 4 scenarios)...")
    mc_results = run_all_scenarios()
    
    # Save MC data
    for key, data in mc_results.items():
        data["df"].to_json(str(DATA_OUT / f"mc_{key}.json"), orient="records", indent=2)
        pd.DataFrame([data["stats"]]).to_json(str(DATA_OUT / f"mc_{key}_stats.json"), indent=2)
        data["tornado"].to_json(str(DATA_OUT / f"mc_{key}_tornado.json"), orient="records", indent=2)
    print(f"    ✓ Monte Carlo data saved to {DATA_OUT}")
    
    # Plots
    print("  [3/8] Generating enhanced Plotly visualizations...")
    plot_leak_vs_loss_enhanced()
    plot_monte_carlo_distribution(mc_results)
    plot_tornado(mc_results)
    plot_supplier_comparison()
    plot_risk_heatmap()
    plot_waterfall_cost(mc_results)
    plot_scenario_comparison(mc_results)
    plot_gantt_maintenance()
    plot_helium_sankey()
    print(f"    ✓ 9 interactive charts saved to {VIZ}")
    
    # Hero pages
    print("  [4/8] Building MAPPING_HEROES pages...")
    pages = {
        "interface": build_hero_interface(),
        "control": build_hero_control(),
        "design": build_hero_design(mc_results),
        "cost": build_hero_cost(mc_results),
        "materials": build_hero_materials(),
        "risk": build_hero_risk(),
        "operations": build_hero_operations(),
    }
    for name, html in pages.items():
        (HEROES / f"{name}.html").write_text(html)
    print(f"    ✓ 7 hero pages saved to {HEROES}")
    
    # Index
    print("  [5/8] Building navigation hub...")
    (DOCS / "index.html").write_text(build_index(mc_results))
    
    # Speaker notes
    print("  [6/8] Generating speaker notes...")
    note_names = write_speaker_notes(mc_results)
    print(f"    ✓ {len(note_names)} speaker note files saved to {NOTES}")
    
    # VERSION.json update
    print("  [7/8] Updating VERSION.json...")
    version_data = {
        "version": VERSION,
        "baseline": BUILD_ID,
        "timestamp": TIMESTAMP,
        "dmaic_iteration": 2,
        "git_ready": True,
        "features": [
            "MAPPING_HEROES navigation (7 heroes, 3 tiers each)",
            "Monte Carlo cost analysis (10,000 runs × 4 scenarios)",
            "Supplier comparison (Meca Inox vs Swagelok)",
            "Enhanced Plotly visualizations (9 interactive charts)",
            "Material specifications database (316L, HDPE, UHMWPE)",
            "Risk register (10 risks, heatmap)",
            "Operations modeling (MTBF, MTTR, MDT, spare parts)",
            "Speaker notes (8 slide-level markdown files)",
            "Professional presentation styling",
        ],
    }
    (ROOT / "VERSION.json").write_text(json.dumps(version_data, indent=2))
    
    # Summary
    print("  [8/8] Build complete!")
    print(f"\n{'='*60}")
    print(f"  ✓ Dashboard: {DOCS / 'index.html'}")
    print(f"  ✓ Heroes:    {HEROES} (7 pages)")
    print(f"  ✓ Charts:    {VIZ} (9 visualizations)")
    print(f"  ✓ Notes:     {NOTES} (8 files)")
    print(f"  ✓ Data:      {DATA_OUT}")
    print(f"{'='*60}")
    
    return mc_results


if __name__ == "__main__":
    build()
