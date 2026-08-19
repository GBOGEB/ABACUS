# ABACUS import note — QPS OFFER/RTM evaluation package

This directory is a direct import of `QPS_Project_Handover_2026-08-17.tar.gz`,
handed to this session by GBO on 2026-08-17 and described as the canonical
handover and SSOT source for the QPS OFFER/RTM Bradley–Terry evaluation
project. Start at `CONTINUATION.md`, then `docs/ENGINEERING_HANDOVER_SESSION.md`,
then `docs/SESSION_SSOT.yaml` — do not re-derive anything already answered
there (see `CONTINUATION.md`'s own instructions to that effect).

**Canonical workbook:** `current/QPS_OFFER_Evaluation_FULL_v24.xlsx` (34
sheets: the 32 imported + `RECOMPUTE_LOG` added 2026-08-18 by this repo's own
correction pass + `PCA_ANALYSIS` added upstream in v24).
Everything else under `current/` derives from it via the scripts in `scripts/`.

## v24 update (2026-08-19)

The upstream (local-only) session kept building after the v23 import landed
here — its build read `FULL_v23.xlsx` *after* this repo's RTM-320 correction
was already saved to it, so **the fix is carried forward intact** (verified:
RTM-320 P=1, rank 132, identical to the corrected v23 — re-checked after this
v24 import). New in v24, per upstream's own `docs/SESSION_SSOT.yaml`:

- **`PCA_ANALYSIS` sheet** (new) — explained-variance/loadings/domain-position
  tables from `scripts/compute_pca.py`; re-running it against live v23 data
  reproduced `DMAIC_BT_TECHNICAL_REPORT.md`'s original numbers exactly
  (PC1=30.6%, PC2=16.5%, 174 distinctive items) — no drift since that report
  was written.
- **3rd weight-sensitivity scenario** ("Cost-heavy-proportional") on
  `WEIGHTS_METHOD` — keeps the other 6 dimensions' relative ratios instead of
  splitting the remaining 30% flat 5% each. Real finding disclosed inline:
  both variants give Cost the same 70% weight but rank very differently
  (Spearman vs. Base: 0.994 flat vs. 0.661 proportional) — *how* the rest of
  the weight is redistributed matters as much as the headline number.
- **`QPS_RTM_BT_Navigator_v22.html`** — 13th tab ("PCA / Structure": a PC1×PC2
  scatter of all 722 RTMs + a 22-domain quadrant view, both self-contained
  inline SVG); BT λ surfaced on RTM/OFFER Lookup cards for the first time.
- `LITE_v24`, refreshed `DASHBOARD`/KPI/deliverables-index/metric-history/PDF
  export artifacts, all re-derived from `FULL_v24` via the matching scripts.

**Independent cross-confirmation on their open Excel-COM lead:** upstream's
SSOT records a new finding — real Excel COM automation failed to *open*
`FULL_v23.xlsx` outright on their machine (not the softer "Repaired" warning
from the v19-era investigation), suspected environmental (Trust Center/
automation security) rather than file corruption, since a brand-new blank
workbook opened fine via the same COM session. This repo's own XML/OPC audit
(re-run on `FULL_v24`/`LITE_v24` after this import, same method as before)
came back clean on every check — no stale relationships, no Content_Types
gaps, no autoFilter/dimension mismatches, no macros. That doesn't prove the
COM failure is environmental, but it rules out the file-corruption
explanation from the same defect class their v19 investigation catalogued,
which is independent evidence pointing the same direction.

Verified before this import: structural invariants (722 RTMs, 50 OFFER items,
no gaps/duplicates), zero formula-error cells, RTM-320 fix intact, on both
`FULL_v24.xlsx` and `LITE_v24.xlsx`.

## Why this directory exists / what it replaces

An earlier pass in this same ABACUS session worked from a much older snapshot
of this project (`ENGINEERING_HANDOVER_OFFER_BT_v3_6.md` + a 22-sheet
workbook, delivered as `files_Claude_RTM.zip` in the Master_Input working
folder — never committed to this repo). That pass:

1. Verified the v3.6 workbook's structural invariants (722 RTMs, 50 OFFER
   items, no gaps/duplicates, weights summing to 1.00) — all passed.
2. Found two open items the v3.6 handover doc had flagged since 2026-07-17
   and never actioned: 7 P1-priority RTM rows still scored by raw keyword
   matching (RTM-328, 482, 603, 718, 599, 018, 320), and OFFER-25 carrying
   an all-zero dimension vector that forced it to rank last by construction.
3. Re-scored all 8 items from their verbatim shall-text/offer-text, with
   full rationale, and was about to commit that correction into this repo
   when this v23 package arrived instead.

**Cross-check result:** every one of those 8 items had *already* been
independently re-scored in the v23 lineage (see `docs/SESSION_SSOT.yaml`'s
`builder_chain`, versions v6–v20) — the v3.6→v23 evolution effectively
re-derives from the same keyword-verify problem and fixes it via a much more
thorough process (rule-based extension, hand-curated Primary/Supporting
review, disclosed evidence-basis per row, and eventually gate flags on RTM
items too, not just OFFER items).

## Full re-judgment (2026-08-18)

GBO asked for a second, deeper pass: re-read each of the 7 previously-flagged
RTM rows' full verbatim requirement text *and* any thematically-related OFFER
item's full bulleted text (via `RTM_CROSSWALK`/`OFFER_CANONICAL`, plus a
keyword sweep across all 50 OFFER items since none of the 7 turned out to
carry a formal crosswalk link), then decide — for each dimension where the
retired v3.6-pass and canonical v23 disagreed — which read the actual
contract text better supports. Outcome:

| RTM | Disagreement | Verdict | Why |
|---|---|---|---|
| RTM-599 | none material | v23 correct | fail-safe interlock wiring — L/F high, P=0 right |
| RTM-603 | none material | v23 correct | personnel-safety PPE clause — matches |
| RTM-482 | R(2→3), F(2→3), LC(1→0) | **v23 correct** | text explicitly names "thermal stability and **mechanical reliability**" (R) and "**interface control logic** validation" (F); no maintainability content (LC) |
| RTM-328 | L(1→0), R(2→0) | **v23 correct** | v3.6-pass inferred an unstated reliability/legal angle from the clause's *purpose*; v23's stricter score-only-what's-named discipline is more textually honest |
| RTM-018 | R/L/Q inferences | **v23 correct** | same over-inference pattern as RTM-328 |
| RTM-718 | Q(3 vs 1), LC(3 vs 2), C(3 vs 0) | **v23 correct** | checked the adjacent OFFER-50 ("Warranty Extension Commercial Terms", §10.2) for context — it links to RTM-708–710, *not* RTM-718, confirming RTM-718 is genuinely un-linked but confirming the neighbourhood is commercial/warranty in nature; the clause's entire content is a financial-compensation denial tied to the final-acceptance milestone — v23's Q=3/LC=3/C=3 all textually justified, the retired pass under-scored all three |
| **RTM-320** | **P(1 vs 0)** | **v3.6-pass correct — corrected in v23** | text explicitly states "All links ... **shall support 1 Gbit/s bandwidth**" — a concrete capacity figure v23's own scoring missed. R=3/F=3 both independently re-confirmed correct. |

**One real correction found: RTM-320's Performance dimension, 0→1.** Applied
via `scripts/recompute_rtm_ranking.py` (see below), not a hand-edited cell —
`RTM_RANKING` is a *static* snapshot (literal values, not live formulas), so
changing one dimension without recomputing Rank/Tier/BT-Win%/BT-λ for the
whole 722-row sheet would have left it internally inconsistent. That script
was written for exactly this: it re-derives the sheet's own formulas from
first principles, validates them against all 722 existing rows before
trusting them (S: 0/722 mismatches; gate-aware rank ordering: 0/722; BT
Win%: 0/722; BT λ via regularised Zermelo/MM, 320 iterations: Pearson
r=0.999999999999 vs. stored), then applies the one dimension change and
**physically re-sorts all 722 rows** to match (this sheet's row order *is*
its documented sort order — rank was literally `row − 5` for every row,
verified before touching anything). Result: RTM-320 moves from rank 189 to
**rank 132** (S 38.0 → 44.67), still Tier T1 Primary; 68 other rows shift by
exactly one position each as a side effect (all still T1, no tier boundary
crossed). Full before/after and the run's audit trail: `RECOMPUTE_LOG` sheet
in both workbooks, and `current/RTM_RANKING_RECOMPUTE_LOG.json`.

**`recompute_rtm_ranking.py` is a rerunnable tool, not a one-off patch.** Any
future dimension-score correction should go through it: edit the
`OVERRIDES`/`RUN_NOTE` block at the top, re-run against `current/`, both
workbooks stay in sync. Every run appends a numbered, dated entry to
`RECOMPUTE_LOG` (in-workbook) and to the JSON log (before/after values, rank/
tier side effects, who triggered it) — same "append, never overwrite"
convention as the project's own `METRIC_HISTORY.json`. This is deliberately
**outside** the original `build_workbook_v5.py..v23.py` chain (those remain
the source of truth for anything beyond RTM_RANKING's 5 derived columns);
it exists because a hand-verified dimension correction needed a safe way to
land without waiting for a full v24 orchestration script.

**Governance note:** per `WEIGHTS_METHOD`'s own guardrail ("do not change the
weighting … unless the panel formally approves a controlled rerun"), this
correction was made only because GBO — the project's creator, developer, and
data/system owner — is that panel and directed it explicitly, on the same
system-owner authority that already governs every other change in this
package. Nothing about the frozen *weights* (0.20/0.22/0.20/0.16/0.12/0.07/
0.03) changed — only one item's dimension *input* score.

The retired v3.6 zip (`files_Claude_RTM.zip` / `files_Claude_RTM_updated.zip`,
Master_Input working folder, never git-tracked) is superseded by this import
and can be deleted; left in place for now in case GBO wants to diff against it.

## Excel integrity audit (2026-08-18)

Mirrored the project's own "Repaired file" investigation method
(`decisions_log.excel_repaired_file_investigation` in `SESSION_SSOT.yaml`) —
raw OPC/XML audit of both workbooks post-correction: Content_Types coverage
of every part, relationship-target resolution across every `.rels` file,
`workbook.xml` ↔ `workbook.xml.rels` sheet mapping, and `<dimension>`/
`<autoFilter>` vs. real data extent per sheet (the exact defect class that
caused the DOMAIN_SUMMARY "Repaired" warning in LITE_v18). **Both
`FULL_v23.xlsx` and `LITE_v23.xlsx` come back clean on all checks** — no
stale autoFilter/dimension ranges, no broken relationship targets, no
macros, no sheet/workbook protection. This doesn't *prove* real Excel won't
show a "Repaired" dialog (no real Excel available in this environment
either, same limitation the original investigation noted) but it rules out
every XML-level defect class their own prior investigation catalogued.

## CI status (informational, low priority)

This import was PR #622. CI ran 213 checks; 14 failed. Every failure
investigated traces to pre-existing repository infrastructure, unrelated to
this import's content (missing test files, missing `pyyaml`/`pkg_resources`
in CI images, a `bandit -f sarif` flag the installed bandit doesn't support,
a dangling `git add` on a deleted `ABACUS-v032/output/` path confirmed
broken on `main` since 2026-07-24, and a GitHub Copilot bot infra hiccup).
None reference anything under `docs/qps_offer_rtm_evaluation/`. Left as a
lower-priority backlog item for whoever owns ABACUS CI — not blocking this
import.

## Provenance of this import

- Source: `QPS_Project_Handover_2026-08-17.tar.gz`, generated by
  `scripts/build_handover_package.py` in a separate, local-only Claude
  session (`git_repository.status` in `docs/SESSION_SSOT.yaml`: "local-only,
  per GBO's explicit choice ... no GitHub remote configured").
  That session's full working directory (~534MB, ~175MB `.git` history of
  superseded binary versions) was not requested — this is the curated
  handover package only (see `MANIFEST.yaml`'s `deliberately_excluded`).
- Imported as-is: no files inside `current/`, `docs/`, or `scripts/` were
  modified during import. This README and the ABACUS commit/PR wrapping it
  are the only additions.
