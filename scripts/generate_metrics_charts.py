#!/usr/bin/env python3
"""
Generate static matplotlib chart SVGs for the ABACUS metrics dashboard.

Output: docs/assets/charts/*.svg
Run:    python scripts/generate_metrics_charts.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "assets", "charts")

# ── shared style ──────────────────────────────────────────────────────────────
PALETTE = {
    "define":    "#1a73e8",
    "measure":   "#34a853",
    "analyze":   "#fbbc04",
    "improve":   "#ea4335",
    "control":   "#9c27b0",
    "infra":     "#00bcd4",
    "accent":    "#ff5722",
}
BG = "#f8f9fa"
GRID = "#dadce0"
FONT = "DejaVu Sans"

plt.rcParams.update({
    "font.family": FONT,
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def save(fig, name):
    path = os.path.join(OUT_DIR, f"{name}.svg")
    fig.savefig(path, format="svg", bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  ✔  {path}")


# ── 1. Test Growth Over Versions ──────────────────────────────────────────────
def chart_test_growth():
    versions = ["v2.3.0", "v3.0.0", "v3.3.0", "v3.3.1\n(current)"]
    counts   = [62, 78, 90, 93]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(versions, counts, marker="o", linewidth=2.5,
            color=PALETTE["define"], markersize=8, zorder=3)
    for x, y in enumerate(counts):
        ax.annotate(str(y), (x, y), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=10, fontweight="bold")
    ax.fill_between(range(len(versions)), counts, alpha=0.10, color=PALETTE["define"])
    ax.set_ylim(50, 105)
    ax.set_ylabel("Test count", fontsize=11)
    ax.set_title("Test Suite Growth by Version", fontsize=13, fontweight="bold", pad=12)
    save(fig, "test_growth")


# ── 2. Tests per DMAIC Phase (grouped bar) ────────────────────────────────────
def chart_tests_per_phase():
    phases  = ["Define\n(P1)", "Measure\n(P2)", "Analyze\n(P3)",
               "Improve\n(P4)", "Control\n(P5)"]
    counts  = [11, 8, 10, 12, 11]
    colors  = [PALETTE["define"], PALETTE["measure"], PALETTE["analyze"],
               PALETTE["improve"], PALETTE["control"]]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(phases, counts, color=colors, width=0.55, zorder=3)
    ax.bar_label(bars, padding=3, fontsize=10, fontweight="bold")
    ax.set_ylim(0, 16)
    ax.set_ylabel("Tests", fontsize=11)
    ax.set_title("Tests per DMAIC Phase", fontsize=13, fontweight="bold", pad=12)
    save(fig, "tests_per_phase")


# ── 3. Full test module breakdown (horizontal bar) ───────────────────────────
def chart_module_breakdown():
    modules = [
        "Phase 4 – Improve",
        "Phase 5 – Control",
        "Phase 1 – Define",
        "Phase 3 – Analyze",
        "Bridge Integration",
        "Phase 2 – Measure",
        "Full Cycle Integration",
        "Stability Monitor",
        "Version Manager",
        "DMAIC Contract",
        "Tuple Metadata",
        "Maturity Tracker",
        "Git Manager",
        "DOW Contract",
        "Docs Navigation",
    ]
    counts = [12, 11, 11, 10, 10, 8, 7, 5, 4, 4, 3, 3, 3, 1, 1]
    colors = [
        PALETTE["improve"], PALETTE["control"], PALETTE["define"],
        PALETTE["analyze"], PALETTE["infra"], PALETTE["measure"],
        PALETTE["accent"], PALETTE["infra"], PALETTE["infra"],
        PALETTE["define"], PALETTE["infra"], PALETTE["infra"],
        PALETTE["infra"], PALETTE["measure"], PALETTE["infra"],
    ]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    y_pos = np.arange(len(modules))
    bars  = ax.barh(y_pos, counts, color=colors, height=0.65, zorder=3)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(modules, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Tests", fontsize=11)
    ax.set_title("Tests per Module (93 total)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, 16)
    save(fig, "module_breakdown")


# ── 4. Phase implementation lines-of-code (radar / bar) ──────────────────────
def chart_phase_loc():
    phases  = ["P1\nDefine", "P2\nMeasure", "P3\nAnalyze", "P4\nImprove", "P5\nControl"]
    loc     = [800, 1000, 900, 1200, 800]
    colors  = [PALETTE["define"], PALETTE["measure"], PALETTE["analyze"],
               PALETTE["improve"], PALETTE["control"]]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(phases, loc, color=colors, width=0.5, zorder=3)
    ax.bar_label(bars, labels=[f"{v:,}" for v in loc], padding=3,
                 fontsize=10, fontweight="bold")
    ax.set_ylim(0, 1500)
    ax.set_ylabel("Lines of code (est.)", fontsize=11)
    ax.set_title("DMAIC Phase Implementation Scale", fontsize=13, fontweight="bold", pad=12)
    save(fig, "phase_loc")


# ── 5. Version artifact lineage (stacked bar: new / changed / removed) ────────
def chart_version_lineage():
    versions  = ["v2.3.0", "v3.0.0", "v3.3.0", "v3.3.1"]
    new_arts  = [6, 12, 8, 5]
    changed   = [2, 7, 11, 9]
    removed   = [0, 3, 2, 1]

    x = np.arange(len(versions))
    w = 0.5

    fig, ax = plt.subplots(figsize=(7, 4))
    b1 = ax.bar(x, new_arts, w, label="New",     color=PALETTE["define"], zorder=3)
    b2 = ax.bar(x, changed,  w, label="Changed", color=PALETTE["analyze"],
                bottom=new_arts, zorder=3)
    b3 = ax.bar(x, removed,  w, label="Removed", color=PALETTE["improve"],
                bottom=[a + b for a, b in zip(new_arts, changed)], zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(versions)
    ax.set_ylabel("Artifact / config file count", fontsize=11)
    ax.set_title("Version Artifact Lineage (changes per release)", fontsize=13,
                 fontweight="bold", pad=12)
    ax.legend(loc="upper left", framealpha=0.85)
    save(fig, "version_lineage")


# ── 6. DMAIC phase status radar ───────────────────────────────────────────────
def chart_dmaic_radar():
    categories = ["Define", "Measure", "Analyze", "Improve", "Control"]
    values     = [92, 88, 90, 95, 90]  # maturity % per phase
    N          = len(categories)
    angles     = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values_    = values + values[:1]
    angles_    = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw={"polar": True})
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.plot(angles_, values_, "o-", linewidth=2.2, color=PALETTE["define"])
    ax.fill(angles_, values_, alpha=0.2, color=PALETTE["define"])
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=11, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100%"], fontsize=8)
    ax.set_title("DMAIC Phase Maturity (%)", fontsize=13, fontweight="bold",
                 pad=18)
    ax.grid(color=GRID, linestyle="--", linewidth=0.7)
    save(fig, "dmaic_radar")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Generating static chart SVGs …")
    chart_test_growth()
    chart_tests_per_phase()
    chart_module_breakdown()
    chart_phase_loc()
    chart_version_lineage()
    chart_dmaic_radar()
    print("Done — 6 charts written to docs/assets/charts/")
