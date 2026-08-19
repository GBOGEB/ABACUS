# DMAIC-framed bug-fix log — QPS OFFER/RTM Evaluation project

Closes the backlog item GBO raised and explicitly demoted to low priority
without dropping it: *"Expand on fix — part of testing, QA, DMAIC?"* — a
DMAIC-framed write-up of the project's actual defect history, distinct from
`DMAIC_BT_TECHNICAL_REPORT.md` (which is the PCA/ranking-structure analysis,
not this). Raw material for entries 1–9 already existed in
`ENGINEERING_HANDOVER_SESSION.md` §5; this document adds the two 2026-08-19
KPI-script bugs and the ABACUS-side data-scoring corrections, and organizes
all of it under Define/Measure/Analyze/Improve/Control rather than leaving
it as a flat "notable bugs" list.

## Define

**Scope of "defect" for this log:** anything that produced a wrong result
that shipped, was caught before shipping only by this project's own QA
convention, or was a false-positive QA signal worth documenting so it isn't
re-investigated from scratch. Excludes scoped-but-not-built features and
open standing questions — those live in `NEXT_ITERATION_BACKLOG.md`, not
here.

**Why this matters for the project as a whole:** the same handful of root
causes recur across otherwise-unrelated bugs (assumed data formats, tools
with sharp edges around merged cells/hyperlinks, unscoped filesystem/repo
operations). Cataloguing them once, with the control action that closes
each, is cheaper than re-discovering the same class of bug on the next
build round — which is exactly what happened twice with the isolated-sheet
QA false positive (#4) before it was written down.

## Measure

14 defects found across the v5→v24 + ABACUS-side history, in four
categories:

| # | Defect | Category | Round found |
|---|---|---|---|
| 1 | `RTM_CROSSWALK!J` white-on-white text | Formatting/CF | pre-v20 |
| 2 | README dead hyperlinks survived into LITE | Tooling gap | pre-v20 |
| 3 | Navigator `renderParetoInto` scoping bug | Code defect | pre-v20 |
| 4 | Isolated-sheet visual-QA false positives (recurred 2×) | QA-harness artefact | pre-v20, v20 |
| 5 | `LITE_v18.xlsx` opened "Repaired" in real Excel | Data-integrity | v18→v19 |
| 6 | `banded()` row-striper overwrote colour-coded columns, 4× | Code defect | v20 |
| 7 | `PHASE_ORDER`/`PHASE_COLORS` built from an assumed string format | Data-assumption | v20 |
| 8 | `openpyxl.insert_rows()` doesn't shift merged-cell ranges | Tooling gap (library edge case) | v23 |
| 9 | Duplicate BT-deck slide badge code (`EVAL-S08` on 2 slides) | Code defect | v23 (inherited from unsaved v9) |
| 10 | KPI-dashboard `git log` unscoped, pulling the whole 2,129-commit shared-repo history | Code defect | 2026-08-19 |
| 11 | KPI-dashboard script hardcoded a `/home/claude/work` cwd from a different environment | Environment-assumption | 2026-08-19 |
| 12 | 7 P1-priority RTM rows scored by raw keyword matching, never verified against shall-text | Data-scoring defect | v3.6 era, closed 2026-08-18 |
| 13 | OFFER-25 carried an all-zero dimension vector, ranking last by construction | Data-scoring defect | v3.6 era, closed 2026-08-18 |
| 14 | RTM-320's Performance dimension scored 0 despite explicit "1 Gbit/s bandwidth" text | Data-scoring defect | v23, closed 2026-08-19 |

**Real Excel-open lead, not yet a confirmed defect** (tracked separately,
not counted above): COM automation failed to open even a pristine
`FULL_v23.xlsx` on the 2026-08-19 round's machine — suspected environmental
(Trust Center/automation security), not file corruption, since a blank
workbook opened fine via the same COM session, and this repo's independent
XML/OPC audit (PR #622, PR #623) found the file structurally clean on every
check in the same defect class as #5. Still open — see
`SESSION_SSOT.yaml`'s `decisions_log.excel_repaired_file_investigation.new_lead_v24_round`.

## Analyze

Four recurring root-cause patterns account for 11 of the 14 defects:

- **Assumed a format instead of scanning live data** (#7, and the same
  instinct nearly caused a bad fix on RTM-320/OFFER-25's dimension scores
  before the 2026-08-18 re-judgment corrected it): a lookup dict or a score
  gets built from one remembered example row or a keyword heuristic, then
  silently misses real variation the live data actually contains.
- **Shared helpers with a hidden assumption about their callers** (#3, #6):
  `renderParetoInto` assumed it would always be called from top-level scope;
  `banded()` assumed no column in its range ever carried its own colour.
  Both broke the first time a new caller violated the unstated assumption.
- **Tooling edge cases around structural Excel features** (#1, #2, #8):
  conditional formatting, hyperlinks, and merged cells each have an
  `openpyxl`-specific gotcha that doesn't surface until the specific
  operation (a `dxf` color rule, a native `.hyperlink` attribute, an
  `insert_rows()` near a merge) is exercised.
- **Operations that assumed a small/local/single-environment scope** (#10,
  #11): a `git log` with no path filter is fine in a small repo and silently
  expensive in a 2,129-commit shared one; a hardcoded path is fine in the
  environment it was written in and silently wrong in the next one.

The QA-harness false positive (#4) and the data-scoring defects (#12–14)
don't fit those four patterns — they're a fifth, distinct class each:
**#4 is a scope-mismatch between the QA copy and the real dependency graph**
(stripping a workbook to one sheet breaks any formula it references), and
**#12–14 are evidence-quality gaps**, not code bugs: a score existed, was
internally consistent, and was still wrong because it was never checked
against the primary source text.

## Improve

Fix + verification method for every defect (control action folded into
Control, below, where one was recorded):

1. Root-caused from saved `dxf` properties directly; fill color set explicitly.
2. Slim-builder's dead-link neutralizer extended to match both the
   `HYPERLINK()` formula-string convention and openpyxl's native
   `.hyperlink` attribute.
3. Hoisted to top-level scope; caught by this project's own pre-ship QA,
   not reported by GBO.
4. Confirmed as harness-only (not real) both times via the always-passing
   full-workbook LibreOffice recalculation pass — the actual formula-
   integrity gate, distinct from a stripped-sheet visual QA copy.
5. `DOMAIN_SUMMARY`'s `AutoFilter` re-applied to the sheet's real 36-domain/
   41-row extent (was sized for ~22 domains). Not re-confirmed against real
   Excel since — see the open COM-automation lead above.
6. Fixed per-instance by narrowing the banded column range to skip the
   pre-colored column in each of the 4 occurrences.
7. Both dicts rebuilt from a direct scan of every distinct value actually
   present in the live `RTM_RANKING` column (10 real phase values found,
   not the assumed 7).
8. Explicit unmerge-before-insert, re-merge-at-new-location-after, added
   around the `insert_rows()` call. Caught by the project's own
   re-read-the-saved-file convention before shipping.
9. Found via raw XML grep for every badge code across all 24 slides
   (`python-pptx`'s shape traversal alone would not reliably have caught
   it); fixed by renumbering the two colliding slides.
10. `git log` call scoped to the project's own path.
11. Path resolved relative to the script's own location instead of hardcoded.
12–13. Re-scored from verbatim shall-text/offer-text with disclosed
   rationale per item; applied via PR #622. Independently re-derived and
   validated against all 722 existing rows before trusting the correction
   tool to write anything (see #14's verification method, same tooling).
14. Corrected via `scripts/recompute_rtm_ranking.py` (PR #622/#623): every
   formula (Weighted S, gate-aware Rank, Tier, BT Win%, BT λ via regularised
   Zermelo/MM) was independently re-derived and validated against all 722
   pre-existing rows before the script was trusted to write anything — exact
   match on 3 of 4 formulas, Pearson r=0.999999999999 on the λ fit — then the
   correction was applied and rows physically re-sorted to match the sheet's
   documented sort order.

## Control — standing rules now in force

Consolidated from each defect's own recorded control action, so the next
build round doesn't have to re-derive them:

1. **Any lookup dict keyed on a data-derived string** (phase names,
   category labels, status values) must be built or verified from a live
   scan of the actual column — never carried forward from a remembered
   example row. *(closes #7, generalizes the lesson from #12–14)*
2. **Any `insert_rows()`/`delete_rows()` call on a sheet with merged cells**
   at or below the insertion point must explicitly handle the merge
   ranges — openpyxl will not do it. *(closes #8)*
3. **Any `banded()`-style row-striping helper** called on a table with its
   own colour-coded column must explicitly exclude that column from the
   banded range. *(closes #6)*
4. **Cross-slide/cross-sheet badge or code uniqueness** must be verified via
   a raw XML grep across every slide/sheet, not assumed from local
   authoring context. *(closes #9)*
5. **Dead/legacy hyperlink neutralization** must pattern-match both the
   `HYPERLINK()` formula-string convention and openpyxl's native
   `.hyperlink` attribute. *(closes #2)*
6. **Any git-log or repository-scanning script** must scope explicitly to
   the relevant path — never assume the repo is small. *(closes #10)*
7. **Any hardcoded filesystem path** (cwd, temp dir) must be resolved
   relative to the script's own location or passed as a parameter — never
   assumed from a prior or different execution environment. *(closes #11)*
8. **Isolated-sheet QA copies** must retain every sheet referenced by a
   formula in the sheet under test, or `#NAME?` false positives will recur —
   the always-passing full-workbook recalculation pass is the real
   formula-integrity gate. *(closes #4)*
9. **Any single-dimension score correction on `RTM_RANKING`** must go
   through `scripts/recompute_rtm_ranking.py`, never a hand-patched cell —
   this sheet is a static snapshot (literal values), not live formulas, and
   a single-cell edit leaves Rank/Tier/BT-Win%/BT-λ inconsistent with the
   other 721 rows. *(closes #14, generalizes for any future dimension-score
   correction)*
10. **Still open:** confirm whether the real-Excel COM open-failure
    (2026-08-19 lead) is genuinely environmental or a real defect this
    project's own XML/OPC audit method isn't catching — the audit method
    itself (Content_Types coverage, relationship-target resolution,
    dimension/autoFilter extent) has now caught every *other* Excel-repair-
    class defect found in this project's history (#5), so a clean audit
    result is meaningful evidence, not proof.
