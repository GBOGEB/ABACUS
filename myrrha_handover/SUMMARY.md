# MYRRHA WCS Engineering Handover — SUMMARY (v0.4)

## Project Overview
Engineering handover bundle for the **Warm Compressor Station (WCS)** of the MYRRHA cryogenic plant (QPLANT). Compares the two pre-studied warm-compressor concepts — Kaeser **FSD 575 SFC** (ALaT) vs **FSD 475 SFC** (LKT) — against a **350 g/s @ 14 barG** baseline, sizes utilities, and consolidates the operational envelope under a Greek-letter notation (β / γ / α).

**Location:** `/home/ubuntu/myrrha_handover/` · **Entry point:** `index.html`

## Deliverables
### HTML views (14)
| # | File | Purpose |
|---|------|---------|
| 1 | `index.html` | Hub / navigation |
| 2 | `slides.html` | Interactive deck |
| 3 | `slide-editor.html` | Dual-view live editor |
| 4 | `reports.html` | Rendered design arguments B1–B7 |
| 5 | `tables.html` | Specs · CSV / JSON export |
| 6 | `graphs.html` | Chart.js plots |
| 7 | `status.html` | Session TODOs · changelog |
| 8 | `truth.html` | Immutable design decisions |
| 9 | `utilities.html` | Math · sample calculations |
| 10 | `pvps.html` | 2 × 5 LP array · γ = 50 g/s · N+1 |
| 11 | `hx-sizing.html` | RCW oil cooler · COMBI · Plotly |
| 12 | `thermo-analysis.html` | Energy / Sankey / T-s / exergy |
| 13 | `operations.html` | β/γ/α operating windows · 3D surface |
| 14 | `handover.html` | Agent BIOS · session protocol |

### Master sources (single source of truth)
- `master/data.json` — all numeric data
- `master/slides.md` — slide content
- `master/truth.md` — design decisions
- `master/config.yaml` — themes / fonts / layout

### Pipeline & docs
- `render_all.py`, `live-render.js`
- `docs/design-guide.md`, `docs/editing-guide.md`, `docs/slide-notes-guide.md`

## Key Findings & Recommendations
1. **Baseline:** 350 g/s @ 14 barG holds as the utility-sizing point (β_max).
2. **Vendor selection:** LKT (3 × FSD 475) preferred over ALaT (2 × FSD 575) for finer turndown granularity and N+1 economy.
3. **PVPS:** 2 × 5 LP-unit array (γ_nominal = 50 g/s) provides α = 0.4–1.0 turndown with one-unit redundancy.
4. **RCW:** ΔT 25 °C (30 → 55 °C) on oil pre-cool; HX N+1 strategy pending approval.
5. **COMBI concept:** Fixed 64 Hz + VFD unit promising for Config24 — needs Kaeser confirmation.
6. **Exergy efficiency:** ~44 % (current target); review for v0.5.

## Operational Notation (recap)
- **β** = WCS.HP flow [g/s], β_max = 350
- **γ** = PVPS flow [g/s], γ_nominal = 50
- **α** = γ / γ_max, α ∈ [0.4, 1.0]
- **Σ** = β + γ (total WCS)
- Design points: **Config30** (β=330, Σ=380) · **Config24** (β=304, Σ=354)

## Next Steps for Engineering Team
1. **Critical (blocking):** Coldbox QRB interface · COMBI vendor confirmation.
2. **High:** PVPS datasheets · turndown scenarios C30(00,10) / C24(00,10) · RCW HX N+1.
3. **Medium:** Discharge temperatures · noise compliance · waste-heat recovery.
4. **Low:** HVAC allocation · exergy optimization.

## Handover Instructions
- **Boot point:** open `handover.html` for agent BIOS and session protocol.
- **Edit content:** modify files in `master/`; run `render_all.py` to regenerate views.
- **Versioning:** v0.4 = 85 % complete; v0.5 will integrate vendor data + QRB coldbox.

## Contact
Direct continuation in this conversation, or load `handover.html` § "Next-session boot prompt" into a new agent session.
