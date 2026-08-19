# Engineering handover — QPS OFFER Evaluation project

## 0. START HERE

**If you're picking this project up cold, in this order:**
1. Open `QPS_OFFER_Evaluation_FULL_v23.xlsx` — this is the SSOT. Everything
   else is derived from it.
2. Open `QPS_RTM_BT_Navigator_v20.html` in a browser to browse it without
   Excel — **but note it is currently stale relative to FULL_v23** (does not
   yet reflect the AD_07/AD_08 additions; re-export is task #60, not yet run).
3. Read `SESSION_ARTEFACT_AND_TASK_INDEX.md` for a compact snapshot of every
   canonical file, folder, and open task as of this round.
4. Read §4 below for the blow-by-blow of what happened this session and §6
   for what's still outstanding — that's the honest gap-check.
5. To reproduce or extend anything, `SESSION_SSOT.yaml` → `families.*.builder_chain`
   has the exact script-by-script lineage; `ARTIFACT_REGISTRY.json` (re-run
   `python3 generate_artifact_registry.py`, no args) is the always-current
   file inventory — trust it over any hand-typed table, including this one.

**Full intent of the project**: independently score two Applicants' OFFER
responses against SCK CEN's 722-requirement RTM for a MYRRHA/QPS (Quench
Protection System) procurement, using a defensible, disclosed, re-weightable
7-dimension method — not a black-box score. Every number in every
deliverable must be traceable back to this one workbook and reproducible
from a saved script; nothing is hand-typed into a slide that isn't sourced
from the data.

## 1. What this project is

A contract-compliance evaluation system built around one SSOT Excel workbook
(`QPS_OFFER_Evaluation_FULL_vNN.xlsx`) that scores 50 OFFER items against 722
RTM (Requirements Traceability Matrix) requirements using a 7-dimension
weighted BT (Bradley-Terry-style) ranking method — Safety/Legal (0.20),
Reliability (0.22), Performance (0.20), Functional (0.16),
Quality/Verifiability (0.12), Lifecycle (0.07), Cost (0.03), frozen weights.
Everything else derives from that one workbook: a reviewer-facing "LITE"
trim, a read-only HTML Navigator for browsing without opening Excel, a
BT-methodology slide deck, and (separately) an MTBF/DMAIC reliability deck
with its own lineage.

The standing design rule across the whole project, applied consistently: **no
duplicated SSOT, disclose rather than fabricate.** Every rule-derived or
inferred value (taxonomy classification, cluster assignment, deliverable
text, AD-document RTM links) is tagged with its confidence/method right on
the sheet, never presented as equivalent to hand-reviewed data. Every
visualization that would otherwise mislead gets its limitation disclosed in
the UI itself, not just in a doc nobody reads — e.g. the weight-sensitivity
chart states plainly it's a full-range scatter, and this round's Deliverables
Dossier note explains exactly which links are text-scan-derived vs.
self-declared-anchor-derived.

## 2. Current canonical deliverables

| Family | File | Notes |
|---|---|---|
| Full workbook | `QPS_OFFER_Evaluation_FULL_v23.xlsx` | SSOT, 32 sheets, 34-entry Deliverables Dossier |
| Reviewer workbook | `QPS_OFFER_Evaluation_LITE_v23.xlsx` | 23-sheet trim of FULL_v23 |
| HTML Navigator | `QPS_RTM_BT_Navigator_v20.html` | ⚠ stale — not yet re-exported against FULL_v23 (task #60) |
| BT-method deck | `BT_Method_Evaluation_v11.pptx` | 24 slides; v11 fixed a duplicate slide-code bug inherited from v9 |
| MTBF/DMAIC deck | `QPS_MTBF_WCS_DMAIC_v7.pptx` | separate deck, untouched this round — not lost, just not this round's focus |
| Deliverables Index | `DELIVERABLES_INDEX.html` | one page, all deliverables, audience/purpose/version-status — ⚠ not refreshed this round, check before trusting version numbers in it |
| Taxonomy/Domain PDF | `QPS_Taxonomy_and_Domain_Summary.pdf` | stale — built from an early nav-data snapshot, several rounds behind |
| Knowledge Taxonomy mapping | `KNOWLEDGE_TAXONOMY_MAPPING.md` | GBO's SKILL_user_ADD 00-10 mapped onto real project artifacts |
| PCA / DMAIC BT analysis | `PCA_DMAIC_BT_ANALYSIS.md` | real 7-dim PCA, Sum-vs-Average divergence — this round added a second, distinct PCA-clustering pass (`pca_pareto_cluster.py`, results in `NEXT_ITERATION_BACKLOG.md` §25), not yet folded into this doc |
| DMAIC metric history | `METRIC_HISTORY.json` | version-over-version stats — ⚠ not backfilled past v20, 3 versions behind |
| Artefact/task index | `SESSION_ARTEFACT_AND_TASK_INDEX.md` | **new this round** — folders/local paths, task list snapshot, honest-assessment findings |

Full version history and script provenance for each family is in
`SESSION_SSOT.yaml` under `families.*.builder_chain`. Git commit history
(local-only repo, see `SESSION_SSOT.yaml` → `meta.git_repository`) is the
other traceable log — `git log` for the full narrative, 19 commits as of
this writing.

## 3. How to regenerate anything

```bash
pip install python-pptx openpyxl matplotlib pyyaml playwright numpy scikit-learn --break-system-packages

# Workbook chain (each script's IN must match the previous OUT — see
# SESSION_SSOT.yaml families.workbook_full.builder_chain for the full list)
python3 build_workbook_v23.py          # FULL_v22 -> FULL_v23
python3 build_workbook_slim_v23.py     # FULL_v23 -> LITE_v23

# Navigator (re-run export whenever RTM_RANKING/OFFER_RANKING/TAXONOMY/
# DELIVERABLES_DOSSIER/etc. change) -- NOT YET RUN against v23, do this next:
python3 export_nav_data.py             # reads FULL_v23, writes /tmp/nav_data_v23.json (check script's hardcoded IN path first)
python3 -c "
tpl = open('navigator_template.html', encoding='utf-8').read()
data = open('/tmp/nav_data_v23.json', encoding='utf-8').read()
open('QPS_RTM_BT_Navigator_v21.html','w',encoding='utf-8').write(tpl.replace('__NAV_DATA_JSON__', data))
"

# PCA-clustered Pareto (new this round, standalone, reads FULL_v23 directly)
python3 pca_pareto_cluster.py          # writes /tmp/pca_cluster_results.json

# Registry refresh (run after any new file lands)
python3 generate_artifact_registry.py

# Git (local-only repo — see SESSION_SSOT.yaml meta.git_repository; GBO
# pushes/pulls to GitHub themselves, this session never touches a remote)
git add <changed files>
git commit -m "<what changed and why>"
```

QA gates before anything ships (unchanged from prior rounds, still enforced):
- **xlsx**: LibreOffice headless recalculation, reload with `data_only=True`, scan every cell for error strings. Zero tolerance. This round added a new class of check learned the hard way: **after any `insert_rows()`, reload the saved file and diff every affected row's full column set** — `openpyxl` does not shift merged-cell ranges, which silently blanks whatever new row lands on the stale merge (see §5.8).
- **xlsx zip/xml integrity**: `zipfile.testzip()` + `xml.etree.ElementTree.fromstring()` over every internal XML/rels part.
- **html**: Playwright headless Chromium — zero console errors, zero `pageerror`, zero horizontal overflow, across every tab/dropdown interaction touched by the change.
- **pptx**: full visual QA render sweep (LibreOffice → PDF → PyMuPDF page images) of every slide touched, plus a raw XML `grep` across ALL slides for the badge-code convention (`METHOD-Sxx`/`EVAL-Sxx`/`CHART-Sxx`) to catch duplicates — this is how the real v9-inherited `EVAL-S08` collision was found this round (§5.9), and python-pptx's own shape traversal is not trustworthy enough for this check on its own.

## 4. Task/subtask progress report — what actually happened this session

This session runs across many rounds; the git log (19 commits) and
`NEXT_ITERATION_BACKLOG.md` (26 dated sections) are the two most reliable
chronological records — this section summarizes both into one narrative,
oldest to newest.

**Foundational rounds** (baseline commit + early workbook/deck builds): the
project's baseline commit bundled workbook v19, Navigator v10, both decks,
and the handover/SSOT/build-script set already in place — this predates
detailed round-by-round logging in this session's memory, so treat the git
log itself as the ground truth for that period rather than this prose.

**Mid-session rounds** (Excel v20, BT deck v9, Navigator v11-v15, Master
Developer Dashboard): built the 9-section v20 workbook update from GBO's
uploaded annotation file (Relation Types table, formal Primary/Supporting/
Review-flag definitions, REVIEW_FOCUS, RTM_PHASE_EXPANSION, DELIVERABLES_DOSSIER
sourced from the real contract PDF's own Table 2, DASHBOARD_2 review-completion
rollup, CONFLICT_CANDIDATES heuristic pass); added BT deck's PCA and
Sum-vs-Average domain-quadrant slides; brought the Navigator through
typing-ease, cross-link chips, Clusters-tab depth, and Code/Standard dropdown
rounds; wrote the DMAIC metric-history log (backfilled v5-v20); built the
Master Developer Dashboard, ASCII pipeline diagram, and skills inventory
(GBO's prioritized picks from an earlier large ask).

**Bug-fix + data-correction rounds** (PDF page numbers, DASHBOARD_2 chart
range): found and fixed the RTM_RANKING PDF-page-number field being wrong on
475/722 rows (66%) against the real source PDF's own printed page numbers,
triggered by a GBO screenshot; found and fixed a DASHBOARD_2 chart pulling a
data range 14 rows too wide, bleeding into an unrelated table and producing
the incoherent bars GBO screenshotted from Google Drive.

**Taxonomy/Dossier/AD round** (this session's largest recent push, workbook
v20→v23, Navigator v19→v20, BT deck v10→v11): led the Taxonomy tab with a
real colour-coded STATUS legend; added a phase-coverage visual (L0-L6 active,
PAC/Warranty/FAC flagged out of scope, with the finding that "supergroups"
have zero live metric usage disclosed rather than glossed over); built a
Subsystems drill-down (202 RTMs, 45 real sub-groups, cluster mix + top-ranked
item per group); built the AD Deliverables Dossier as both a flat table and a
collapsible tree (6 top-level → 26 sub-items at the time); added a
Deliverables-relevance slide to the BT deck; found and fixed a real duplicate
badge-code bug (`EVAL-S08` used on two different slides, inherited from an
earlier unsaved v9 build step) via raw XML grep across all 24 slides; ran and
disclosed a full weight-sensitivity re-analysis (Base / Equal / Cost=70%
scenarios, Spearman rank correlations, 3 explainable rank-shift sets); ran
and disclosed a genuine empirical Pareto/elbow check on the "top-5%" P1
cutoff (found no natural break near rank 36 — it's an administrative
workload cutoff, not a data-driven concentration boundary; the real 80%
cumulative-importance line sits at rank ~490).

**This most recent round** (workbook v23, PCA-clustered Pareto, artefact
index): GBO granted access to `Master_Input` (his real Windows working
folder) and pointed at the AD document set; staged and read AD_07
(Cybersecurity Policy Framework) and AD_08 (Abnormal Scenarios/Line S), added
both to DELIVERABLES_DOSSIER (34 entries now) with links taken from each
document's own self-declared RTM anchor rather than a fuzzy scan; found and
fixed a real `openpyxl` bug in the process (`insert_rows()` doesn't shift
merged-cell ranges, which silently blanked the new row's data on first save
— caught by the project's own re-read-the-saved-file convention, not shipped
broken); ran a targeted honest-assessment query on the 44-row "Broad/contextual"
relation type and found all 44 trace to exactly one OFFER item (OFFER-13)
fanning out across 7 RTM Categories — a legitimate but narrow pattern, now
disclosed; ran the PCA-clustered-Pareto analysis GBO explicitly requested
(KMeans k=5 on standardized 7-dim scores, silhouette-selected) and found real
requirement-TYPE clusters (Reliability-dominant, Cost-dominant, etc.) that do
NOT produce a cleaner P1 importance cutoff than what was already found —
a genuinely different, useful lens, reported as such rather than oversold as
"the answer"; refreshed `ARTIFACT_REGISTRY.json` (175 files, 76 families);
bumped `SESSION_SSOT.yaml` canonicals to v23; wrote and delivered
`SESSION_ARTEFACT_AND_TASK_INDEX.md`; now rewriting this handover doc to the
same standard.

## 5. Notable bugs found and fixed this session (worth knowing about even though shipped)

1. **RTM_CROSSWALK!J white-on-white text** — conditional-formatting rules set font color to white with no fill ever defined. Root-caused from saved `dxf` properties directly.
2. **README's dead hyperlinks survived into LITE** — slim-builder's neutralizer only pattern-matched formula-string hyperlinks, not openpyxl's native `.hyperlink` attribute. Fixed, now enforced project-wide.
3. **Navigator `renderParetoInto` scoping bug** — shared chart renderer accidentally nested inside `buildDomains()`, unreachable from `buildOutline()`. Caught by this session's own pre-ship QA, not GBO. Hoisted to top-level scope.
4. **Isolated-sheet visual-QA false positives** — stripping a workbook copy to one sheet for a clean PDF render breaks any formula referencing a now-deleted sheet, which looks like a real bug but isn't. Recurred twice, same non-issue both times, confirmed via the full-workbook LibreOffice pass.
5. **`QPS_OFFER_Evaluation_LITE_v18.xlsx` opened "Repaired" in real Excel** — root-caused to DOMAIN_SUMMARY's stale AutoFilter (`A5:L27` vs. real 36-domain/41-row extent). Fixed in v19. Not re-confirmed against real Excel since (no Excel available in this environment) — flagged as the strongest lead, not a certainty.
6. **v20's `banded()` row-striping helper overwrote intentional colour fills, 4×** — the shared helper unconditionally colours every even row in its range, blind to columns that already carry deliberate colour-coding. Fixed per-instance by narrowing the banded range; **control action**: any future `banded()` call on a table with its own colour-coded column must explicitly exclude that column.
7. **v20's `PHASE_ORDER`/`PHASE_COLORS` were built from an assumed string format**, not the live data — missed the real spacing (`"L0 Tender / Offer"` not `"L0 Tender/Offer"`) and 3 real phase values. Fixed by rebuilding both dicts from a direct scan of the live column. **Control action**: any lookup dict keyed on a data-derived string must be built/verified from a live scan, never a remembered example row.
8. **`openpyxl.insert_rows()` does not shift merged-cell ranges** (new this round) — building `build_workbook_v23.py`, the DELIVERABLES_DOSSIER note row's pre-existing `A:F` merge stayed anchored at its old row number after inserting 2 rows above it, silently discarding the new AD_08 row's columns B-F on save. Caught by re-reading the saved file (project convention). Fixed by explicit unmerge-before-insert, re-merge-at-new-location-after. **Control action**: any `insert_rows()`/`delete_rows()` call on a sheet with merged cells at or below the insertion point must explicitly handle the merge ranges — openpyxl will not do it.
9. **Duplicate BT-deck slide badge code (`EVAL-S08`) across two slides** (new this round) — inherited from an earlier unsaved v9 build step (slides 21 and 22 both carried `EVAL-S08`). Found via raw XML grep across all 24 slides for every badge code, confirming true uniqueness — python-pptx's shape traversal alone would not have reliably caught this. Fixed in v11 by renumbering slides 22/23/24 (`EVAL-S10`/`S11`/`S12`).

## 6. Known gaps / outstanding — the honest checklist

Grouped by how close each is to actionable:

**In progress right now:**
- Task #59 — BT deck updates: Base/Equal/Cost=70% weight-scenario slide(s)
  with a message banner; a granular OFFER/RTM/Deliverable/Code&Standard/
  Lifecycle slide using the new AD_07/08 data; EVAL-S09 toggle-metric idea
  (needs honest framing before building — true interactive toggling isn't
  native to static PPTX).
- Task #60 — Navigator re-export against FULL_v23 (currently stale), LITE
  re-verify, Playwright QA, commit, deliver. **This is the single biggest
  "not yet true" gap right now**: the workbook has AD_07/08 and the Navigator
  doesn't, and nobody should assume they're in sync until #60 runs.

**Explicitly deferred, not forgotten (your prioritisation, not dropped):**
- Broad scan/index of the entire `Master_Input` folder by size/date, with a
  look for existing git repos to integrate — you ordered items 1/2/3 ahead
  of this when asked, so it hasn't been started.
- Indexing/rewriting all `.txt` files in `Master_Input` by category/topic.
- "Bicycle chart" for OFFER↔RTM links ("interaction pareto") — terminology
  needs a one-line clarification from you before this can be scoped, let
  alone built.

**Real, older gaps carried forward and still true (not re-verified this
round, listed here rather than silently dropped):**
- `BT_Method_Evaluation` versions v7/v8/v9 have no saved build script (v6
  and v10 do). Whatever changed in those two steps is only reconstructable
  from the binary files themselves or prose, not a script.
- `workbook_full` v10 through v15 has no saved per-version orchestration
  script (the underlying logic scripts exist; the glue that sequenced them
  doesn't).
- The Navigator's JSON-splice step is still inline Python, never promoted to
  a saved `splice_navigator.py`.
- `Taxonomy/Domain Summary PDF`, `DELIVERABLES_INDEX.html`, and
  `METRIC_HISTORY.json` are all stale by several versions — none has been
  actively wrong, just not refreshed in step with the workbook.
- A systematic "relic-field" scan of EVALUATION_WORKSPACE/OFFER_CANONICAL for
  manually-copied carryover fields — requested earlier, not yet built.
- The full cross-workbook font/heading-size consistency audit across every
  sheet — requested earlier, not yet done.
- Standing open questions never answered by GBO: Aptos-vs-Carlito font
  consistency preference; whether an earlier "repaired file" warning still
  applies to the current version; SYSTEM requirement-type subcategory
  clarification.

**What this gap-check did NOT find**: no evidence any previously-reported
"done" item has silently regressed — the git log and backlog sections
corroborate each other, and this round's re-derived facts (registry query,
task list) matched what was claimed rather than contradicting it. The gaps
above are all "not yet started/refreshed," not "claimed done but isn't."

## 7. Session-improvement notes

The working style this session — dense, multi-ask messages, often with
screenshots, arriving faster than any single ask can be fully closed out —
has gotten every substantive request addressed eventually, but the same two
costs from earlier rounds recurred again this round in miniature: build
scripts occasionally lag a step behind being saved/committed until a
dedicated "catch-up" pass (this document is itself one), and some
investigation-only asks (e.g. the Broad/contextual honest assessment) sat
computed-but-unreported for a round before being relayed. Procedural fix,
unchanged from the standing note: save/commit each build before considering
it "done," and explicitly flag investigation-only findings the moment
they're computed rather than batching them. Full suggestion list is in
`SESSION_SSOT.yaml` → `session_improvement`.

## 8. Full artifact list

`ARTIFACT_REGISTRY.json` is the ground truth (auto-generated, 175 files / 76
families as of this writing). Query it directly rather than trusting a
hand-typed table to stay current:

```bash
python3 -c "
import json
d = json.load(open('ARTIFACT_REGISTRY.json'))
fams = d.get('families', d)
for fam, info in sorted(fams.items()):
    latest = info.get('latest') if isinstance(info, dict) else info
    print(latest)
"
```
