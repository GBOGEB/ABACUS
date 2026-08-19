# Skills inventory — build scripts, where stored, maintenance structure

Every script below lives flat in the project root (`/home/claude/work/`,
same directory as every deliverable — this project has never used a `src/`
or `scripts/` subfolder). Grouped by capability, not alphabetically, so
this reads as "what can this pipeline actually do" rather than a directory
listing (`ARTIFACT_REGISTRY.json` already is that literal listing —
regenerate it with `generate_artifact_registry.py` any time you want the
current file-by-file truth).

## 1. Workbook construction (the SSOT chain)

| Script | Capability |
|---|---|
| `build_workbook_full_v5.py` | One-time bootstrap: merges GBO's hand-edited base + `QPS_RTM_BT_Standalone.xlsx` into the first `FULL` workbook. Not re-run after v5. |
| `build_workbook_v6.py` .. `v9.py` | Taxonomy/cluster/lookup-page scaffolding, requirement-type extension rules, deliverables de-genericisation, cluster colour palette. |
| `build_workbook_v16.py` .. `v20.py` | Current active lineage: dashboard callouts, 7-dimension heatmaps, live weight-scenario toggle, layout overhauls, taxonomy tables, review-flag standardisation, new analytical sheets (REVIEW_FOCUS, RTM_PHASE_EXPANSION, DELIVERABLES_DOSSIER, CONFLICT_CANDIDATES). |
| — | **v10–v15 are a gap**: the underlying transform scripts below were run, but no `build_workbook_v1{0..5}.py` orchestration script was saved. See §4. |

## 2. Classification / inference (called by the workbook builders above)

| Script | Capability |
|---|---|
| `classify_all_rtms.py` | Rule-based Requirement Type/Category extension across all 722 RTMs (disclosed as rule-based, not hand-curated). |
| `infer_clusters.py` | Confidence-tagged C1–C8 cluster inference for RTMs with no direct crosswalk link. |
| `t0_taxonomy.py` | T0 Gate taxonomy/definitions logic. |
| `fix_mtbf_rtm_numbers.py` | Reconciles obsolete `RTM-###` citations in the MTBF deck's appendices against the canonical RTM-001..722 register. |

## 3. LITE (reviewer trim) construction

| Script | Capability |
|---|---|
| `build_workbook_slim_v5.py` .. `v20.py` | One script per FULL version, always `IN = matching FULL_vN`, `OUT = LITE_vN`. The `KEEP` list (which sheets survive the trim) is the single array to edit if the kept/dropped split should change — enforced by a pre-flight regex scan (no kept-sheet formula may depend on a dropped sheet) and dead-hyperlink neutralisation. |

## 4. HTML Navigator data pipeline

| Script | Capability |
|---|---|
| `export_nav_data.py` | Exports the JSON blob (`rtmRanking`, `offerRanking`, `reviewQueue`, `clusters`, `domainSummary`, `taxonomy`, `deliverablesDossier`) the Navigator splices in — reads directly from the live workbook, so the Navigator can never hand-drift from the SSOT. |
| — | **Gap**: the JSON→HTML splice step (`navigator_template.html` + `str.replace('__NAV_DATA_JSON__', ...)`) is currently run as inline Python each round, not a saved `splice_navigator.py`. Flagged in `SESSION_SSOT.yaml gaps.missing_build_scripts` — next round that touches the Navigator should save this as a real script. |

## 5. Deck construction (two independent lineages, not workbook-driven)

| Script | Capability |
|---|---|
| `build_bt_deck_v5.py`, `build_bt_deck_v6.py` | BT-methodology deck: font/palette unification, chart-blowup slides. v7–v9 exist as files but have no saved script (v9's 2 PCA/quadrant slides were built via inline Python this session — also flagged as a gap to close). |
| `build_deck.py` .. `build_deck5.py` | MTBF/DMAIC deck, phases 1–5 of iterative slide construction against `QPS_MTBF_WCS.pptx`. |
| `make_charts.py`, `make_energy_pie.py` | Chart-image generation feeding the deck builders (e.g. the energy-mix donut added in `build_deck5.py`). |

## 6. Static exports

| Script | Capability |
|---|---|
| `build_pdf_export.py` | Print-friendly, mixed-orientation PDF (Taxonomy = portrait, Domain Summary = landscape) computed from the same `nav_data_vN.json` the Navigator uses. Stale — still reads `nav_data_v7.json`, workbook has moved to v20. |

## 7. Cross-version tracking / QA

| Script | Capability |
|---|---|
| `compute_metrics_snapshot.py` | Appends one version's worth of tracked metrics (RTM count, tier/domain/gate distribution, Sum/Avg Weighted S, crosswalk-linked %, review-flag distribution, decided-count, sheet count) to `METRIC_HISTORY.json`. Idempotent — safe to re-run against an unchanged file. Supports `--backfill` against every `FULL_v*.xlsx` on disk at once (used to backfill v5–v20 in one pass). |
| `qa_nav_v8.py`, `qa_nav_v8b/c/d.py` | Playwright headless-Chromium QA harness pattern for the Navigator — console-error/pageerror/overflow sweep across tabs and controls. Named per-round rather than as one evolving script; the pattern (not the specific file) is what gets reused each round via inline Playwright scripts in-session. |
| `generate_artifact_registry.py` | Fully idempotent directory scan → `ARTIFACT_REGISTRY.json` (file names, sizes, mtimes, latest-per-family). Never hand-edited — re-run any time the working directory changes. |

## 8. Utilities

| Script | Capability |
|---|---|
| `xlsx_copy_helpers.py` | Shared openpyxl cell/style copy helpers used across multiple workbook builders. |
| `extract_content.py` | One-off content extraction utility (early-session). |

---

## Maintenance structure

**Naming convention.** Every versioned script is `build_<family>_v<N>.py`,
where `N` matches the version number of the file it produces (e.g.
`build_workbook_v20.py` produces `QPS_OFFER_Evaluation_FULL_v20.xlsx`).
`IN`/`OUT` constants are declared at the top of each script and are the
authoritative source `SESSION_SSOT.yaml`'s `builder_chain` entries were
verified against — trust the script's own constants over any narrative
description if the two ever disagree.

**Where the "truth about the scripts" lives.** Three files, each with a
distinct job — don't duplicate information across them, extend the right
one:
- `ARTIFACT_REGISTRY.json` — auto-generated, what's on disk right now.
  Never hand-edit; re-run `generate_artifact_registry.py`.
- `SESSION_SSOT.yaml` `families.*.builder_chain` — hand-maintained, the
  ordered script chain per deliverable family, with a one-line summary of
  what each version changed. Update this at the end of any round that ships
  a new version.
- This file (`SKILLS_INVENTORY.md`) — hand-maintained, grouped by
  *capability* rather than by family/version, for "what can this pipeline
  do and which script does it" rather than "what version is current."
  Regenerate/re-check whenever a new script is added, not every round.

**Adding a new version.** (1) Copy the previous version's script under the
new `vN` suffix; (2) bump its `IN`/`OUT` constants to point at the new
input/output filenames; (3) make the change; (4) run
`compute_metrics_snapshot.py` against the new output so it lands in
`METRIC_HISTORY.json`; (5) add a `builder_chain` entry to
`SESSION_SSOT.yaml` with a one-line summary; (6) commit the script and its
output together — per this project's established convention, every shipped
version is committed with the script that produced it, not just the
output file.

**Closing the known gaps.** Six version steps currently have no saved
script (`workbook_full` v10–v15, `bt_method_deck` v7/v8, `mtbf_dmaic_deck`
v7, plus the Navigator's inline splice step) — see
`SESSION_SSOT.yaml gaps.missing_build_scripts` for the full list and
impact. None of these are urgent (every shipped file already passed its QA
gate), but the recommendation on record is: the next time any of these
families needs even a small edit, save the script that makes the edit
under a proper `vN` name from the start, rather than another one-off inline
change.
