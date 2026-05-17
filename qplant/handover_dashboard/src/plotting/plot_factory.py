"""Plotly chart generation for cryogenic leak-rate dashboard."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def write_plot(fig: go.Figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs="cdn", full_html=True)


def make_plot_1_leak_vs_loss(conversion_df: pd.DataFrame) -> go.Figure:
    df = conversion_df[conversion_df["pressure_bar_abs"] == 5].copy()
    fig = px.line(
        df,
        x="leak_rate_mbar_l_s",
        y="mass_flow_g_year",
        color="temperature_K",
        log_x=True,
        log_y=True,
        markers=True,
        title="Plot 1 — Leak Rate vs Helium Loss (P=5 bar)",
        labels={"mass_flow_g_year": "Mass loss (g/year)", "leak_rate_mbar_l_s": "Leak rate (mbar·L/s)", "temperature_K": "Temperature (K)"},
    )
    fig.update_traces(hovertemplate="Leak=%{x:.1e} mbar·L/s<br>T=%{customdata[0]} K<br>Loss=%{y:.3e} g/year")
    return fig


def make_plot_2_temp_effect(conversion_df: pd.DataFrame) -> go.Figure:
    df = conversion_df[conversion_df["leak_rate_mbar_l_s"] == 1e-8].copy()
    fig = px.line(
        df,
        x="temperature_K",
        y="mass_flow_g_year",
        color="pressure_bar_abs",
        markers=True,
        title="Plot 2 — Temperature Effect on Mass Loss (Leak class 1e-8)",
        labels={"mass_flow_g_year": "Mass loss (g/year)", "temperature_K": "Temperature (K)", "pressure_bar_abs": "Pressure (bar abs)"},
    )
    return fig


def make_plot_3_valve_comparison(cost_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        cost_df,
        x="class",
        y=["valve_capex_eur", "helium_cost_over_life_eur"],
        barmode="group",
        title="Plot 3 — Valve Class CAPEX vs Helium-Loss Cost (40y)",
        labels={"value": "EUR", "variable": "Cost component"},
        color_discrete_map={"valve_capex_eur": "#1f77b4", "helium_cost_over_life_eur": "#ff7f0e"},
    )
    return fig


def make_plot_4_system_projection(inventory_df: pd.DataFrame, helium_price_eur_kg: float = 15.0) -> go.Figure:
    base_loss_kg = inventory_df["mass_loss_g_year_total"].sum() / 1000.0
    scenarios = pd.DataFrame(
        [
            {"scenario": "Baseline mix", "annual_loss_kg": base_loss_kg},
            {"scenario": "All leak-tight (1e-9)", "annual_loss_kg": base_loss_kg * 0.15},
            {"scenario": "All standard warm (1e-5)", "annual_loss_kg": base_loss_kg * 1.85},
        ]
    )
    scenarios["annual_cost_eur"] = scenarios["annual_loss_kg"] * helium_price_eur_kg

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Annual He loss (kg)", x=scenarios["scenario"], y=scenarios["annual_loss_kg"], marker_color="#17becf"))
    fig.add_trace(go.Scatter(name="Annual He cost (EUR)", x=scenarios["scenario"], y=scenarios["annual_cost_eur"], yaxis="y2", mode="lines+markers", line=dict(color="#d62728", width=3)))
    fig.update_layout(
        title="Plot 4 — System-Level Annual Loss Projection (210 cold + 200 warm)",
        yaxis=dict(title="Helium loss (kg/year)"),
        yaxis2=dict(title="Cost (EUR/year)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
    )
    return fig


def make_plot_5_reliability(rel_df: pd.DataFrame, spare_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for valve_type in rel_df["valve_type"].unique():
        subset = rel_df[rel_df["valve_type"] == valve_type]
        fig.add_trace(
            go.Scatter(
                x=subset["leak_class_mbar_l_s"],
                y=subset["mtbf_years"],
                mode="lines+markers",
                name=f"MTBF {valve_type}",
            )
        )
    fig.add_trace(
        go.Bar(
            x=spare_df["valve_population"],
            y=spare_df["recommended_spares_per_year"],
            name="Recommended spares/year",
            yaxis="y2",
            marker_color="#9467bd",
            opacity=0.5,
        )
    )
    fig.update_layout(
        title="Plot 5 — Reliability Dashboard (MTBF + Spare Strategy)",
        xaxis=dict(type="log", title="Leak class (mbar·L/s)"),
        yaxis=dict(title="MTBF (years)"),
        yaxis2=dict(title="Spares/year", overlaying="y", side="right"),
        legend=dict(orientation="h"),
    )
    return fig
