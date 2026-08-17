# Continuation guide -- QPS OFFER Evaluation project

If you're picking this up cold, in a coding editor, with no memory of the
Claude session that built it: read this file first, then
`docs/ENGINEERING_HANDOVER_SESSION.md`, then decide what you actually need
to touch.

## What this project is

A contract-compliance evaluation system for a nuclear/physics infrastructure
procurement (SCK CEN, MYRRHA/QPS Quench Protection System). Two Applicants'
OFFER responses are scored against 722 RTM (Requirements Traceability
Matrix) contract requirements, using a 7-dimension weighted Bradley-Terry-
style ranking method: Safety/Legal (0.20), Reliability (0.22), Performance
(0.20), Functional (0.16), Quality/Verifiability (0.12), Lifecycle (0.07),
Cost (0.03) -- frozen contract weights, disclosed everywhere they're used.

Everything derives from ONE Excel workbook (`current/QPS_OFFER_Evaluation_FULL_v23.xlsx`).
Nothing else is hand-edited independently -- the reviewer workbook, the HTML
Navigator, and (partially) the presentation decks are all regenerated FROM
it by the scripts in `scripts/`.

## The one rule that matters most

**No duplicated SSOT, disclose rather than fabricate.** Every rule-derived
or inferred value on any sheet is tagged with its confidence/method right
there, not presented as equivalent to hand-reviewed data. If you extend
this project, keep that convention -- it's why the workbook can be trusted
at 722 rows instead of spot-checked.

## How to reproduce anything

```bash
pip install python-pptx openpyxl matplotlib pyyaml playwright numpy scikit-learn pypdf --break-system-packages

# Full rebuild chain (only run steps you actually need -- most work is
# additive on top of the current canonical files in current/)
python3 scripts/build_workbook_v23.py            # needs FULL_v22.xlsx as input (not included -- see docs/SESSION_SSOT.yaml builder_chain for the full version history if you need an older input)
python3 scripts/build_workbook_slim_v23.py        # FULL_v23 -> LITE_v23
python3 scripts/export_nav_data.py current/QPS_OFFER_Evaluation_FULL_v23.xlsx /tmp/nav_data_v23.json
python3 scripts/splice_navigator.py /tmp/nav_data_v23.json QPS_RTM_BT_Navigator_v21.html scripts/navigator_template.html
python3 scripts/build_pdf_export.py /tmp/nav_data_v23.json
python3 scripts/merge_taxonomy_pdf.py QPS_Taxonomy_and_Domain_Summary.pdf
python3 scripts/compute_metrics_snapshot.py --backfill
python3 scripts/generate_artifact_registry.py
```

Note: most `build_workbook_vNN.py` scripts take the PREVIOUS version as
input (`vNN-1 -> vNN`), not the original baseline -- this package only
includes the CURRENT (v23) workbook, not every intermediate version, so a
from-scratch rebuild of the full v5->v23 history isn't possible from this
package alone. If you need that, ask for the full working directory
(534MB) or the raw `.git` history instead.

## What's actually outstanding right now

Pulled directly from this session's own tracking, not re-guessed:

- **8 pending tasks** (see `docs/NEXT_ITERATION_BACKLOG.md` and
  `docs/SESSION_ARTEFACT_AND_TASK_INDEX.md` for full detail): recurring
  documentation upkeep, in-deck slide navigation, revisiting 4 early
  modelling assumptions with GBO, a per-RTM/OFFER JSON edge-index, a
  thematic session compendium, ADDENDUM-to-graph linking in the Navigator,
  and two open questions GBO has never directly answered (Aptos vs Carlito
  font preference; whether an old "repaired file" Excel warning still
  applies).
- **A requested but not-yet-built feature**: a multi-node OFFER<->RTM
  relationship diagram (Mermaid-style or similar) with richer hover detail
  -- the current Navigator only has a single-OFFER "link wheel," flagged
  as low-priority in its own code comments.
- **Terminology to clarify with GBO before building**: a "bicycle chart"
  for OFFER<->RTM interaction-Pareto -- likely related to the item above,
  not confirmed.

## If you're an AI agent continuing this in a fresh session

Read, in order: this file, `docs/ENGINEERING_HANDOVER_SESSION.md` (full
narrative + gap-check), `docs/SESSION_SSOT.yaml` (structured facts, parse
don't re-derive), `docs/NEXT_ITERATION_BACKLOG.md` (dated findings log).
Do not re-investigate things already answered in those three files -- e.g.
whether T0/Gate items dominate OFFER_RANKING's top rank (yes, by design,
see SESSION_SSOT.yaml decisions_log), or whether the MTBF deck is stale
(untouched but not broken, RTM citations spot-checked valid). Follow the
same QA convention before shipping anything: LibreOffice-PDF render +
direct page inspection for pptx/pdf, Playwright headless sweep (zero
console/page errors, zero horizontal overflow) for html, reload-and-verify
for xlsx after any structural edit (openpyxl has real gotchas -- see the
insert_rows()/merged-cells bug in ENGINEERING_HANDOVER_SESSION.md section 5
before doing any row insertion near a merged cell).
