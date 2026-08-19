import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Data: RTM-395, Table 19 (Compressor Room/CCB) + Table 20 (Cold Box Room/AUB),
# QPS_Contract_mirror_DOCX.pdf, normal-running loads only (Back-up Diesel 350 kW
# excluded -- RTM-401 confirms it's LOOP-contingency only, not a running load).
HP_COMPRESSORS = 4 * 356          # 1,424 kW -- HP Compressor 1-4 @ 356 kW each
PVPS = 150                         # PVPS pumping skid (single feeder)
REST = (3 * 42) + 65 + 7.5 + 1.5 + 3 + 3   # 206 kW -- Cold Compressors x3 + Other/feeder + ORS heater + Gas Analyzer + UPS + Control systems
TOTAL = HP_COMPRESSORS + PVPS + REST
assert TOTAL == 1780

labels = ["HP Compressors", "PVPS", "Rest of plant"]
values = [HP_COMPRESSORS, PVPS, REST]
colors = ["#562873", "#1FA7A0", "#E0A9D6"]

fig, ax = plt.subplots(figsize=(3.55, 3.55), dpi=300)
wedges, _ = ax.pie(
    values,
    colors=colors,
    startangle=90,
    counterclock=False,
    wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2.5),
)
ax.set_aspect("equal")
ax.text(0, 0.10, f"{TOTAL:,.0f}", ha="center", va="center", fontsize=27, fontweight="bold", color="#2A2A3A")
ax.text(0, -0.16, "kW total", ha="center", va="center", fontsize=12.5, color="#5A5A6A")
fig.patch.set_alpha(0.0)
plt.tight_layout(pad=0.15)
plt.savefig("energy_mix_donut.png", transparent=True)
print("HP", HP_COMPRESSORS, round(100*HP_COMPRESSORS/TOTAL,1), "%")
print("PVPS", PVPS, round(100*PVPS/TOTAL,1), "%")
print("REST", REST, round(100*REST/TOTAL,1), "%")
print("TOTAL", TOTAL)
