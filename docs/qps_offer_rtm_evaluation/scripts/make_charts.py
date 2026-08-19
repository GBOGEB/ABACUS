#!/usr/bin/env python3
"""Generate all supporting charts for the DMAIC deck redesign, in the
corporate SCK-CEN palette. Saved as transparent-background PNGs at 2x for
crisp placement in PowerPoint."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

OUT = "/home/claude/work/charts"
os.makedirs(OUT, exist_ok=True)

PURPLE1 = "#562873"   # accent1
PURPLE2 = "#984A9C"   # accent2
BLUE4   = "#034694"   # accent4 - "technical narrative" contrast
LBLUE3  = "#8ED8F8"   # accent3
GREY5   = "#CACCD0"
GREY6   = "#DFE0E2"
INK     = "#2B2B2B"
MUTED   = "#6B6B6B"
GOOD    = "#2E7D32"
WARN    = "#C77700"
CRIT    = "#C62828"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 13,
    "text.color": INK,
    "axes.edgecolor": GREY5,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
})

def style_ax(ax, hide_y=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(not hide_y)
    if hide_y:
        ax.set_yticks([])
    ax.spines["bottom"].set_color(GREY5)
    ax.grid(axis="y", color=GREY6, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

def save(fig, name, w=8.6, h=5.0):
    fig.set_size_inches(w, h)
    fig.tight_layout(pad=1.2)
    path = f"{OUT}/{name}.png"
    fig.savefig(path, dpi=220, transparent=True)
    plt.close(fig)
    print("saved", path)

# ------------------------------------------------------------------ Slide 5 --
# Compressor flow capability: grouped bar, @60Hz range vs @72Hz
fig, ax = plt.subplots()
cats = ["FSD 475", "FSD 575", "HSD Combi\n(per comp.)"]
v60 = [84, 98, 77.5]
v60_err = [2, 3, 2.5]
v72 = [96, 112.5, 87.5]
x = np.arange(len(cats)); w = 0.34
b1 = ax.bar(x - w/2, v60, width=w, color=LBLUE3, edgecolor=BLUE4, linewidth=0.8,
            yerr=v60_err, capsize=4, ecolor=MUTED, label="@ 60 Hz (OEM range)", zorder=3)
b2 = ax.bar(x + w/2, v72, width=w, color=PURPLE1, label="@ 72 Hz", zorder=3)
for xi, v in zip(x - w/2, v60):
    ax.text(xi, v + 5, f"{v:g}", ha="center", fontsize=10.5, color=MUTED)
for xi, v in zip(x + w/2, v72):
    ax.text(xi, v + 5, f"{v:g}", ha="center", fontsize=10.5, color=PURPLE1, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("Flow (g/s)")
ax.set_ylim(0, 130)
style_ax(ax)
ax.legend(frameon=False, loc="upper left", fontsize=10.5)
save(fig, "s05_flow_capability")

# ------------------------------------------------------------------ Slide 6 --
# Total flow & N-1: fleet totals vs N-1, target line 307 g/s
fig, ax = plt.subplots()
cats = ["FSD 475", "FSD 575", "HSD Combi"]
total4 = [384, 450, 350]
n1 = [288, 337.5, 262.5]
status = [CRIT, GOOD, WARN]
x = np.arange(len(cats)); w = 0.34
ax.bar(x - w/2, total4, width=w, color=GREY5, label="4-unit total @ 72 Hz", zorder=3)
bars = ax.bar(x + w/2, n1, width=w, color=status, label="N−1 (3 units) @ 72 Hz", zorder=3)
for xi, v in zip(x - w/2, total4):
    ax.text(xi, v + 8, f"{v:g}", ha="center", fontsize=10.5, color=MUTED)
icons = ["✗", "✓", "⚠"]
for xi, v, ic, c in zip(x + w/2, n1, icons, status):
    ax.text(xi, v + 8, f"{v:g} {ic}", ha="center", fontsize=10.5, color=c, fontweight="bold")
ax.axhline(307, color=INK, linestyle="--", linewidth=1.4, zorder=2)
ax.text(len(cats) - 0.42, 307 + 8, "target 307 g/s (24 QM FFT)", fontsize=10, color=INK, ha="right")
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("Total flow (g/s)")
ax.set_ylim(0, 480)
style_ax(ax)
ax.legend(frameon=False, loc="upper left", fontsize=10.5)
save(fig, "s06_total_flow_n1")

# ------------------------------------------------------------------ Slide 7 --
# 3-only envelope: 3 units @72Hz and ~65Hz vs target — same style as Slide 6
fig, ax = plt.subplots()
cats = ["FSD 475", "FSD 575"]
v72 = [288, 337.5]
v65 = [270, 300]  # marginal estimate band, illustrative of "~270-285" / OK region
x = np.arange(len(cats)); w = 0.34
ax.bar(x - w/2, v65, width=w, color=LBLUE3, edgecolor=BLUE4, linewidth=0.8, label="3 units @ ≤ 65 Hz (est.)", zorder=3)
ax.bar(x + w/2, v72, width=w, color=[CRIT, GOOD], label="3 units @ 72 Hz", zorder=3)
for xi, v in zip(x - w/2, v65):
    ax.text(xi, v + 8, f"~{v:g}", ha="center", fontsize=10.5, color=MUTED)
for xi, v, c in zip(x + w/2, v72, [CRIT, GOOD]):
    ax.text(xi, v + 8, f"{v:g}", ha="center", fontsize=10.5, color=c, fontweight="bold")
ax.axhline(307, color=INK, linestyle="--", linewidth=1.4, zorder=2)
ax.text(len(cats) - 0.55, 307 + 8, "target 307 g/s  (see Slide 6)", fontsize=10, color=INK, ha="right")
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("3-unit flow (g/s)")
ax.set_ylim(0, 380)
style_ax(ax)
ax.legend(frameon=False, loc="upper left", fontsize=10.5)
save(fig, "s07_three_only_envelope", w=7.6)

# ------------------------------------------------------------------ Slide 9 --
# MTBF targets by failure class (also reused, captioned, on the split Slide 16b)
fig, ax = plt.subplots()
cats = ["Class A\nExit 2 K (≤ 24 h)", "Class B\n→ 4.5 K / TS standby", "Class C\nWarm-up > 4.5 K"]
vals = [5, 10, 15]
colors = [WARN, PURPLE2, PURPLE1]
bars = ax.bar(cats, vals, color=colors, width=0.55, zorder=3)
for xi, v in enumerate(vals):
    ax.text(xi, v + 0.4, f"> {v} yr", ha="center", fontsize=12, fontweight="bold", color=colors[xi])
ax.set_ylabel("Target MTBF (years)")
ax.set_ylim(0, 18)
style_ax(ax)
save(fig, "s09_mtbf_by_class", w=8.2, h=4.8)

# ------------------------------------------------------------------ Slide 12 -
# Appendix A scenarios
fig, ax = plt.subplots()
labels = ["2K Op\n30 QM", "2K Sb\n30 QM", "2K Op\n24 QM", "2K Sb\n24 QM", "4.5K Sb\n24 QM"]
flows = [344, 239, 307, 215, 160]
tags = ["Design pt", "Standby", "Real ops\ntarget", "Mini-design", "Warm standby"]
colors = [GREY5, GREY5, PURPLE1, GREY5, LBLUE3]
x = np.arange(len(labels))
ax.bar(x, flows, color=colors, width=0.6, zorder=3)
for xi, v, c in zip(x, flows, colors):
    ax.text(xi, v + 8, f"{v} g/s", ha="center", fontsize=11, color=INK, fontweight="bold")
new_labels = [f"{l}\n{t}" for l, t in zip(labels, tags)]
ax.set_xticks(x); ax.set_xticklabels(new_labels, fontsize=9.8)
ax.set_ylabel("Total flow (g/s)")
ax.set_ylim(0, 400)
style_ax(ax)
save(fig, "s12_appendixA_scenarios", w=9.0, h=5.0)

# ------------------------------------------------------------------ Slide 13 -
# Appendix B: Hz required for N-1 to reach 307 g/s
fig, ax = plt.subplots()
cats = ["FSD 475", "FSD 575", "HSD Combi\n(4 comp.)"]
hz = [75, 65.5, 72]
status = [CRIT, GOOD, WARN]
icons = ["✗ exceeds limit", "✓ within limit", "⚠ limit edge"]
x = np.arange(len(cats))
ax.bar(x, hz, color=status, width=0.5, zorder=3)
for xi, v, ic, c in zip(x, hz, icons, status):
    ax.text(xi, v + 1.6, f"{v:g} Hz", ha="center", fontsize=11, fontweight="bold", color=c)
    ax.text(xi, v - 6, ic, ha="center", fontsize=9.5, color="white", fontweight="bold")
ax.axhline(72, color=INK, linestyle="--", linewidth=1.4, zorder=2)
ax.set_xlim(-0.6, 3.25)
ax.text(2.85, 72, "72 Hz\nupset ceiling", fontsize=9.5, color=INK, ha="left", va="center",
        linespacing=1.2)
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("Hz required for N−1 → 307 g/s")
ax.set_ylim(0, 82)
style_ax(ax)
save(fig, "s13_appendixB_hz", w=8.6, h=4.9)

# ------------------------------------------------------------------ Slide 14 -
# Appendix C: two small-multiple panels (no dual axis) - descent rate & coverage time
fig, (ax1, ax2) = plt.subplots(1, 2)
cats = ["¾ flow", "⅔ flow", "½ flow"]
descent = [0.4, 0.6, 0.9]
coverage = [12, 8, 5]
x = np.arange(len(cats))
ax1.bar(x, descent, color=LBLUE3, edgecolor=BLUE4, linewidth=0.8, width=0.55, zorder=3)
for xi, v in zip(x, descent):
    ax1.text(xi, v + 0.03, f"{v:g}", ha="center", fontsize=11, fontweight="bold", color=BLUE4)
ax1.set_xticks(x); ax1.set_xticklabels(cats, fontsize=10.5)
ax1.set_ylabel("Descent rate (m³/h)")
ax1.set_ylim(0, 1.1)
style_ax(ax1)

ax2.bar(x, coverage, color=PURPLE1, width=0.55, zorder=3)
for xi, v in zip(x, coverage):
    ax2.text(xi, v + 0.3, f"{v:g} h", ha="center", fontsize=11, fontweight="bold", color=PURPLE1)
ax2.set_xticks(x); ax2.set_xticklabels(cats, fontsize=10.5)
ax2.set_ylabel("Coverage time (h, 5 m³ buffer)")
ax2.set_ylim(0, 15)
style_ax(ax2)
save(fig, "s14_appendixC_buffer", w=9.4, h=4.6)

print("All charts generated.")

# ------------------------------------------------------------------ Slide 4 --
# Frequency / upset policy — operating envelope zones
fig, ax = plt.subplots(figsize=(9.6, 3.6))
zones = [(0, 65, GOOD), (65, 72, WARN), (72, 80, CRIT)]
for lo, hi, c in zones:
    ax.barh(0, hi - lo, left=lo, height=0.62, color=c, zorder=3)
ax.text(32.5, 0, "NOMINAL\ncontinuous", ha="center", va="center", fontsize=11,
        color="white", fontweight="bold", linespacing=1.3)

# narrow zones: label OUTSIDE (above) with a leader tick, so text never collides
callouts = [
    (68.5, "TRANSIENT / UPSET\n≤ 8 h per event", WARN, 0.62),
    (76, "LOGGED, ≤ 24 h / month\ncumulative → monthly RAMI trigger", CRIT, 1.05),
]
for cx, label, c, ytext in callouts:
    ax.plot([cx, cx], [0.31, ytext - 0.05], color=c, linewidth=1.1, zorder=2)
    ax.text(cx, ytext, label, ha="center", va="bottom", fontsize=9.8,
            color=c, fontweight="bold", linespacing=1.3)

ax.axvline(60, color=INK, linestyle=":", linewidth=1.3, zorder=4)
ax.text(60, -0.42, "recovery target ≤ 60 Hz", ha="center", va="top", fontsize=9.3, color=INK)
ax.set_xlim(0, 82); ax.set_ylim(-0.7, 1.55)
ax.set_yticks([])
ax.set_xlabel("Compressor frequency (Hz)")
for s in ["top", "left", "right"]:
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GREY5)
ax.set_xticks([0, 20, 40, 60, 65, 72, 80])
save(fig, "s04_frequency_zones", w=9.6, h=3.6)

print("Slide 4 chart added.")

# ------------------------------------------------------------- Unit Economics --
fig, (ax1, ax2) = plt.subplots(1, 2)
labels = ["Isothermal\n(ideal)", "Actual shaft\n@ 50% η", "Nameplate\n(deck, Slide 3)"]
vals = [178.3, 356.6, 350]
colors = [LBLUE3, PURPLE1, GREY5]
edge = [BLUE4, PURPLE1, MUTED]
x = np.arange(3)
bars = ax1.bar(x, vals, color=colors, edgecolor=edge, linewidth=1.1, width=0.55, zorder=3)
for xi, v, c in zip(x, vals, [BLUE4, PURPLE1, MUTED]):
    ax1.text(xi, v + 8, f"{v:g} kW", ha="center", fontsize=11, fontweight="bold", color=c)
ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=10)
ax1.set_ylabel("Power (kW), single unit")
ax1.set_ylim(0, 420)
style_ax(ax1)

tariffs = ["€0.12/kWh", "€0.15/kWh", "€0.20/kWh"]
costs = [374904, 468630, 624841]
x2 = np.arange(3)
ax2.bar(x2, [c/1000 for c in costs], color=PURPLE2, width=0.55, zorder=3)
for xi, v in zip(x2, costs):
    ax2.text(xi, v/1000 + 12, f"€{v/1000:.0f}k", ha="center", fontsize=11, fontweight="bold", color=PURPLE2)
ax2.set_xticks(x2); ax2.set_xticklabels(tariffs, fontsize=10)
ax2.set_ylabel("Annual energy cost (€k), single unit\ncontinuous full-duty")
ax2.set_ylim(0, 700)
style_ax(ax2)
save(fig, "s_unit_economics", w=9.6, h=4.8)
print("Unit economics chart added.")

# ------------------------------------------------------- Appendix D: Poisson --
# P(zero trips) vs MTBF, for 90-day / 1-year / 5-year windows, with guide lines
# at 94/95/99% and MTBF markers at 4 and 5 years (the two worked examples).
# Replaces 5 near-duplicate screenshots in the old Analyze section with one
# clean, single chart.
fig, ax = plt.subplots()
mtbf = np.linspace(0.5, 30, 400)
colors = [BLUE4, PURPLE2, "#8A8D93"]
labels = ["90-day campaign", "1 year", "5 years"]
ts = [90/365, 1.0, 5.0]
for t, c, lab in zip(ts, colors, labels):
    p0 = np.exp(-t / mtbf)
    ax.plot(mtbf, p0, color=c, linewidth=2.2, label=lab, zorder=3)
for lvl, ls in [(0.94, (0, (5, 3))), (0.95, (0, (2, 2))), (0.99, (0, (1, 1)))]:
    ax.axhline(lvl, color=MUTED, linewidth=0.9, linestyle=ls, zorder=2)
ax.text(29.4, 0.94 - 0.032, "P₀=0.94–0.95", fontsize=8.5, color=MUTED, ha="right")
ax.text(29.4, 0.99 + 0.008, "P₀=0.99", fontsize=8.5, color=MUTED, ha="right")
for m, dy in ((4, 0.03), (5, 0.10)):
    ax.axvline(m, color=WARN, linewidth=0.9, linestyle=(0, (1, 2)), zorder=2)
    ax.text(m, dy, f"{m} y", fontsize=8.5, color=WARN, ha="center")
ax.set_xlabel("MTBF (years)")
ax.set_ylabel("Probability of zero trips, P₀")
ax.set_xlim(0, 30); ax.set_ylim(0, 1.03)
style_ax(ax)
ax.legend(frameon=False, loc="lower right", fontsize=10)
save(fig, "appendixD_poisson", w=8.6, h=4.9)

# --------------------------------------------- Appendix I: Weibull increase --
# Wear-out "increase factor" — chance of failing in next 90 days, age=5y vs
# good-as-new, per component (from the Weibull results table on this slide).
fig, ax = plt.subplots()
comp = ["Oil screw\ncompressor", "Turbine", "Cold\ncompressor"]
fresh = [0.00027, 0.0163, 0.0049]
aged = [0.0645, 0.674, 1.153]
x = np.arange(3)
w = 0.32
b1 = ax.bar(x - w/2, fresh, width=w, color=GREY5, edgecolor=MUTED, linewidth=0.8, label="Good-as-new (age=0)", zorder=3)
b2 = ax.bar(x + w/2, aged, width=w, color=CRIT, label="At 5 years old", zorder=3)
for xi, v in zip(x - w/2, fresh):
    ax.text(xi, v + 0.02, f"{v:.3f}%", ha="center", fontsize=9, color=MUTED)
for xi, v, f in zip(x + w/2, aged, ["×237", "×41", "×235"]):
    ax.text(xi, v + 0.02, f"{v:.3f}%\n{f}", ha="center", fontsize=9, fontweight="bold", color=CRIT)
ax.set_xticks(x); ax.set_xticklabels(comp, fontsize=10)
ax.set_ylabel("P(fail in next 90 days), %")
ax.set_ylim(0, 1.5)
style_ax(ax)
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
save(fig, "appendixI_weibull_increase", w=7.4, h=4.6)
print("Appendix charts added.")
