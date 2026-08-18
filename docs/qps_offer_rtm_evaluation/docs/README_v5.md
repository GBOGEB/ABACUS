# Phase 5 delivery — build notes

Four deliverables this round, all built from your latest uploads (the contract-mirror PDF, your own hand-edited `QPS_OFFER_Evaluation.xlsx`, the RTM-BT standalone workbook, the BT_Method deck, and the engineering-handover ZIP). Full rationale for every change is in `DMAIC_update_changelog.md`'s Phase 5 addendum — this file is just what's in the box and how to re-run it.

## Files in this delivery

| File | What it is |
|---|---|
| `QPS_MTBF_WCS_DMAIC_v5.pptx` | MTBF deck, v4 + the energy-consumption donut chart on Slide 6 |
| `QPS_OFFER_Evaluation_FULL_v5.xlsx` | Full SSOT workbook — your edits + RTM-BT integrated (21 sheets) |
| `QPS_OFFER_Evaluation_LITE_v5.xlsx` | Reviewer-shareable subset of the FULL workbook (11 sheets) |
| `BT_Method_Evaluation_v5.pptx` | BT methodology deck, restyled to match the MTBF deck |
| `build_deck5.py` | Builds the MTBF v5 deck from v4 (re-runnable) |
| `make_energy_pie.py` | Generates the energy-mix donut chart PNG |
| `build_workbook_full_v5.py` | Builds the FULL workbook from your base + RTM-BT (re-runnable) |
| `build_workbook_slim_v5.py` | Builds the LITE workbook from the FULL workbook (re-runnable) |
| `xlsx_copy_helpers.py` | Cross-workbook worksheet copy helper (openpyxl doesn't have one built in) |
| `build_bt_deck_v5.py` | Restyles the BT deck (re-runnable) |
| `DMAIC_update_changelog.md` | Full history, Phases 1–5 (this pass = the last addendum) |

## Dependencies

```bash
pip install python-pptx openpyxl matplotlib pyyaml --break-system-packages
```

LibreOffice (`soffice`) and Poppler's `pdftoppm` for visual QA re-renders, same as prior phases — see `README_v4.md` for the exact invocation pattern (the pptx skill's `soffice.py` wrapper, not a bare `soffice` call).

## How to re-run

```bash
# MTBF deck energy-mix chart
python3 make_energy_pie.py          # -> energy_mix_donut.png
python3 build_deck5.py              # -> QPS_MTBF_WCS_DMAIC_v5.pptx

# Excel: FULL then LITE, in that order (LITE derives from FULL's output file)
python3 build_workbook_full_v5.py   # -> QPS_OFFER_Evaluation_FULL_v5.xlsx
python3 build_workbook_slim_v5.py   # -> QPS_OFFER_Evaluation_LITE_v5.xlsx

# BT deck restyle
python3 build_bt_deck_v5.py         # -> BT_Method_Evaluation_v5.pptx
```

All four scripts are deterministic (no timestamps, no randomness) — re-running against unchanged inputs reproduces the same output byte-for-byte.

## What to check on your end

1. **The RTM-BT ranking data itself.** `QPS_RTM_BT_Standalone.xlsx`'s values are a static snapshot (not live formulas) using a different 4-dimension scoring scheme than the canonical 7-dimension model in your engineering-handover ZIP. It's integrated and usable for review as-is, but won't recompute if you change weights — see the changelog addendum for the full finding.
2. **The LITE workbook's kept/dropped tab list**, if your sense of "really need / need to know" differs from what your own START_HERE nav bar and NAVIGATION_MAP role column implied — easy to adjust, the KEEP list is one array at the top of `build_workbook_slim_v5.py`.
3. **The four assumptions adopted** after a clarifying-questions prompt was declined this round (RTM-BT scope, BT-deck DMAIC-tag scope, Handover-deck scope, "skill" meaning) — listed in the changelog addendum, easy to flip if any guessed wrong.
4. **Excel formulas in real Excel.** Headless LibreOffice recalculation found zero errors in both workbooks (matching your engineering handover's own §6 bar), but that's not a substitute for opening them in real Excel once, the same caveat as Aptos-in-PowerPoint from Phase 4.

## Not touched this round

- `QPS_OFFER_EVAL_DMAIC_Handover_Deck.pptx` — out of scope this pass, per the adopted default.
- Everything already delivered and QA'd in Phases 1–4 of the MTBF deck, outside the Slide 6 amendment.
