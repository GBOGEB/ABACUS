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

Everything derives from ONE Excel workbook (`current/QPS_OFFER_Evaluation_FULL_v24.xlsx`).
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
python3 scripts/build_workbook_v23.py             # needs FULL_v22.xlsx as input (not included -- see docs/SESSION_SSOT.yaml builder_chain for the full version history if you need an older input)
python3 scripts/compute_pca.py current/QPS_OFFER_Evaluation_FULL_v23.xlsx current/pca_results_v23.json
python3 scripts/compute_weight_scenario4.py current/QPS_OFFER_Evaluation_FULL_v23.xlsx current/weight_scenario4_v23.json
python3 scripts/build_workbook_v24.py             # needs FULL_v23.xlsx as input -- run compute_pca.py/compute_weight_scenario4.py first, this script reads their JSON output
python3 scripts/build_workbook_slim_v24.py        # FULL_v24 -> LITE_v24 -- synced this round (see docs/NEXT_ITERATION_BACKLOG.md Section 29)
python3 scripts/export_nav_data.py current/QPS_OFFER_Evaluation_FULL_v24.xlsx current/nav_data_v24.json
python3 scripts/splice_navigator.py current/nav_data_v24.json QPS_RTM_BT_Navigator_v22.html scripts/navigator_template.html
python3 scripts/build_pdf_export.py current/nav_data_v24.json  # re-pointed at v24 this round; also fixed a Windows /tmp file:// path bug, see Section 29
python3 scripts/merge_taxonomy_pdf.py QPS_Taxonomy_and_Domain_Summary.pdf
python3 scripts/compute_metrics_snapshot.py --backfill
python3 scripts/generate_artifact_registry.py
```

Note: most `build_workbook_vNN.py` scripts take the PREVIOUS version as
input (`vNN-1 -> vNN`), not the original baseline -- this package only
includes the CURRENT (v24) workbook, not every intermediate version, so a
from-scratch rebuild of the full v5->v24 history isn't possible from this
package alone. If you need that, ask for the full working directory
(534MB) or the raw `.git` history instead. New this round:
`scripts/compute_pca.py` and `scripts/compute_weight_scenario4.py` (both
run BEFORE `build_workbook_v24.py`, which reads their JSON output) --
see `docs/PIPELINE_DIAGRAM.md` for the full updated diagram.

## Artifacts ready to review now (accessible list, priority order)

1. **`current/QPS_RTM_BT_Navigator_v22.html`** -- open in any browser, no
   install needed. Fastest way to see everything, including the new
   "PCA / Structure" tab (13th tab). Start with its own in-page "Start"
   tab.
2. **`current/QPS_OFFER_Evaluation_FULL_v24.xlsx`** -- the SSOT workbook.
   New this round: `PCA_ANALYSIS` sheet (34 sheets total, was 33); the
   3rd weight-toggle option in `WEIGHTS_METHOD` (cell B56 dropdown).
3. **`current/DELIVERABLES_INDEX.html`** -- now the real top-level landing
   page (closed 28b this round): every deliverable filename/heading is a
   working link, including the two previously-orphaned dashboards
   (`MASTER_DEVELOPER_DASHBOARD.html`, `QPS_DMAIC_KPI_Dashboard.html`),
   now linked from here for the first time.
4. **`docs/NEXT_ITERATION_BACKLOG.md` Section 28 and Section 29** -- 28 is
   what got built in the PCA/BT-Excel round (items 1, 2c, part of 10) and
   what did NOT (28a-28e). 29 is this round: LITE + PDF export synced to
   v24, DELIVERABLES_INDEX.html promoted to a landing page (28b closed),
   artifact registry refreshed -- 28a/28c/28d still open, read Section 29's
   own closing list before assuming anything past 28b is done.
5. **`docs/PIPELINE_DIAGRAM.md`** -- two ASCII diagrams: the build
   pipeline (which script produces which file) and, new this round, the
   evaluation process (what happens to one RTM/OFFER end to end,
   independent of the build plumbing).
6. **`docs/DMAIC_BT_TECHNICAL_REPORT.md`** -- the PCA/DMAIC narrative the
   new workbook sheet and Navigator tab summarise; read this for the "why"
   behind the numbers, not just the numbers themselves.
7. **`docs/SESSION_SSOT.yaml`** -- structured facts, canonical-version
   pointers (all updated this round), and the new Excel-COM-automation
   finding (`decisions_log.excel_repaired_file_investigation.new_lead_v24_round`)
   -- relevant if the "repaired file" question (item below) ever gets
   revisited.

**Re-synced to v24 this round** (see `docs/NEXT_ITERATION_BACKLOG.md`
Section 29): `current/QPS_OFFER_Evaluation_LITE_v24.xlsx` (was 1 version
behind FULL, now in lockstep), `current/QPS_Taxonomy_and_Domain_Summary.pdf`
(rebuilt from `nav_data_v24.json`; a real Windows `file://` path bug in
`build_pdf_export.py`/`merge_taxonomy_pdf.py` was found and fixed in the
process -- see Section 29). Note: this file previously described the
Taxonomy PDF as "built against v7 data" -- that was inherited, undisclosed
drift from an earlier round's stale claim, not the actual state; corrected
here.

**Still stale, not touched this round** (out of this round's scope, not an
oversight): `current/BT_Method_Evaluation_v12.pptx` -- built against v23
data, this round's PCA/weight-scenario-4 findings not in it yet (backlog
item 28d, explicitly not attempted).

## What's actually outstanding right now

Two separate lists -- don't conflate them:

**Closed this round** (`docs/NEXT_ITERATION_BACKLOG.md` Section 28 + 29):
Section 28's item 1 (PCA -> Excel + Navigator tab), item 2c (PCA tab design
question), and the BT λ export half of item 10 (λ now visible in the
Navigator; the "who fitted it and how" question to GBO is still open).
Section 29: LITE + PDF export synced to v24, artifact registry refreshed,
and backlog item **28b closed** -- `current/DELIVERABLES_INDEX.html` is now
a real top-level landing page with working links to every deliverable
including the two previously-orphaned dashboards.

**Still open, untouched this round** -- pulled directly from this session's
own tracking, not re-guessed:

- **The original 8 pending tasks** (see `docs/NEXT_ITERATION_BACKLOG.md`
  and `docs/SESSION_ARTEFACT_AND_TASK_INDEX.md` for full detail): recurring
  documentation upkeep, in-deck slide navigation, revisiting 4 early
  modelling assumptions with GBO, a per-RTM/OFFER JSON edge-index, a
  thematic session compendium, ADDENDUM-to-graph linking in the Navigator,
  and two open questions GBO has never directly answered (Aptos vs Carlito
  font preference; whether an old "repaired file" Excel warning still
  applies -- see the new, related-but-not-conclusive COM-automation finding
  in `SESSION_SSOT.yaml` noted above).
- **New this round (28a/28c/28d), still not built** (`NEXT_ITERATION_BACKLOG.md`
  Section 28, 28b now closed per above): a comment/annotation criticality
  system (Editorial/L1/L2/L3, dropdown, both HTML and Excel -- 28a);
  deliverables mapped per execution phase (L1-L6) through to as-built/
  handover -- 28c, the largest remaining item; BT deck updates (OneDrive/
  SSOT framing + new PCA/weight-scenario-4 slides) -- 28d, deliberately left
  open (separate, larger design task requiring human content judgment, not
  attempted this round).
- **A requested but not-yet-built feature**: a multi-node OFFER<->RTM
  relationship diagram with richer hover detail -- the current Navigator
  only has a single-OFFER "link wheel," flagged as low-priority in its own
  code comments. Terminology now clarified (not yet confirmed by GBO): a
  **radial/chord diagram** (Circos-style) -- categories evenly spaced
  around a circle, arced links between them, matching what GBO described
  as a "bicycle chart" for OFFER<->RTM interaction-Pareto.

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
