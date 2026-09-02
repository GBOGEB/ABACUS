# QPS session narrative — workbook reconciliation, 2026-08-31 → 09-01

## What happened, in order

1. **Discovered two independently-built RTM/OFFER workbooks** describing the same
   real evaluation: `QPS_OFFER_Evaluation_FULL_v24.xlsx` (git-tracked, Master_Input)
   and `QPS_OFFER_Cluster_v3_4_BT_RTM_Standards_Evidence.xlsx` (governed by
   `cryoplant-project`'s OCD-ADR system, sitting unconnected in `~/Documents`).
2. **Verified they're the same evaluation, not a guess**: 722 RTM rows, 50 OFFER
   rows, 377 crosswalk rows in both, confirmed by direct row count — plus the
   BT weights match to the decimal. Zero shared sheet names between them
   otherwise; two genuinely different build pipelines.
3. **First merge attempt was wrong** — bolted the second workbook's sheets
   directly onto a file that read as "the new canonical," conflating a governed
   parent with unreviewed child detail. Caught, corrected same session.
4. **Rebuilt properly**: `QPS_OFFER_Evaluation_FULL_v24.xlsx` left completely
   untouched (verified by file-modification-time, not assumed). All child detail
   moved into a clearly-labeled companion file,
   `QPS_BT34_SUPPLEMENTARY_DETAIL_v1.xlsx`, cross-referenced by ID rather than
   merged by row.
5. **Normalized real duplication**: two sheets inside the *source* v3_4 workbook
   were already 100% identical to two others in the same file
   (`Format_Pivot`≡`OFFER_RTM_Crosswalk`, `RTM_Offer`≡`RTM_Canonical`) — dropped
   in the companion file with zero data loss.
6. **QA'd for real, not just structurally**:
   - SHA256 on every artefact, independently re-verified.
   - Zip/XML structural validation on every `.xlsx`/`.pptx`.
   - **Playwright**, actually installed (chromium binary + all), run against
     3 HTML pages — caught a real label-collision bug on first render,
     fixed it, re-screenshotted to confirm.
   - **PowerPoint and Excel COM automation** — both files actually opened in
     the real applications, not just parsed as XML. PowerPoint exported all
     29 slides to PNG; the 2 new slides visually confirmed pixel-correct.
7. **Reconciled the BT deck's own version gap**: `BT_Method_Evaluation_v12.pptx`
   (git-tracked "current") was missing 2 slides that existed only in a PDF
   export 2 rounds ahead. Diffed the actual text, found the exact gap (not a
   broad rebuild), rebuilt as `v15.pptx` via direct OOXML editing since
   `python-pptx` was blocked by a broken Pillow DLL in this environment.
8. **Built the federation topology view** — a real node graph of
   `cryoplant-project` (child SSOT) ↔ `ABACUS` (DOW analysis plane) ↔ `CODEX`
   (KEB exchange plane), with live-checked GitHub issue states, not the
   architecture doc's own claims taken on faith.

## Changelog

| Date | Change | File(s) |
|---|---|---|
| 2026-08-31 | Built PCA visual (variance, loadings, domain structure, KMO) | `QPS_PCA_Navigator.html` |
| 2026-08-31 | Reconciled BT deck v12→v15 (2 missing slides recovered) | `BT_Method_Evaluation_v15.pptx` |
| 2026-08-31 | First workbook merge attempt (flawed — parent/child conflated) | `_DEPRECATED_conflated_parent_QPS_OFFER_Evaluation_CANONICAL_v1.xlsx` |
| 2026-09-01 | Corrected: v24 untouched, deduplicated companion file built | `QPS_BT34_SUPPLEMENTARY_DETAIL_v1.xlsx` |
| 2026-09-01 | Real render QA added (Playwright, PowerPoint COM, Excel COM) | all of the above |
| 2026-09-01 | Fixed a real label-collision bug found by Playwright | `QPS_PCA_Navigator.html` |
| 2026-09-01 | Built federation topology + this narrative + lineage manifest | `QPS_FEDERATION_TOPOLOGY.html`, `QPS_ARTEFACT_LINEAGE.json`, this file |

Full machine-readable version with checksums: [`QPS_ARTEFACT_LINEAGE.json`](QPS_ARTEFACT_LINEAGE.json).

## PCA + BT ranking → what to actually work on next

Not opinion — read directly from `v24!PCA_ANALYSIS`, `v24!OFFER_RANKING`,
`v24!RTM_RANKING`, `v24!CONFLICT_CANDIDATES` (also reproduced in
`QPS_BT34_SUPPLEMENTARY_DETAIL_v1.xlsx!EXECUTION_PRIORITY`).

1. **Gate items first, always.** 6 OFFER T0 Gate items (OFFER-01/02/03/47/48/49)
   and 43 RTM T0 Gate items outrank everything else regardless of BT score —
   lexicographic precedence, not compensatory. RTM gate cluster: Safety &
   Protection and Codes & Standards dominate the first 13 `RTM_RANKING` rows.
2. **Don't shortcut to fewer dimensions.** PCA: PC1 is only 30.6% of variance,
   7 components needed to reach 100%. PC3 is a near-pure Cost axis (0.881
   loading) — Cost is structurally independent of the other 6, so a
   cost-only or performance-only shortlist misses real signal.
3. **Next 5 non-gate OFFER items** (rank 7–11): OFFER-09 (LN2
   techno-economic), OFFER-42 (after-sales), OFFER-20 (helium leak
   detection), OFFER-34 (cooling water), OFFER-29 (control system
   obsolescence).
4. **Conflict-review hotspots** — not random, 3 sections carry the bulk of
   68 heuristic candidate pairs:
   - §4.6.8 Control & Interlock (~15 pairs) — operator-station
     visualization language repeats across adjacent RTMs, likely a shared
     drafting template.
   - §8.1.7 Quality Assurance & Control (~15 pairs) — non-conformity/
     corrective-action language, same pattern.
   - §10.3 Acceptance & Warranty (8 pairs) — RTM-711 through RTM-722,
     review as one warranty block.

## Honest open items (not resolved this session)

- The 5 pairs flagged `DIFFERENT GRANULARITY` in `MERGE_CANDIDATES` (Standards,
  Deliverables, Clusters) were compared by row count only — a full row-level
  diff hasn't been done.
- ~~No ABACUS DOW or CODEX KEB cycle has actually executed against real QPS
  content yet~~ — **superseded 2026-09-02**: both cycles have now executed,
  repeatedly. ABACUS #809→#810→#811 and CODEX #335→#336→#337 are the same
  W08 DOW/KEB "runtime-return artifact" sequence, one day apart on each peer
  plane. The tracking issues (#659, #667, #254, #255) are still open only
  because none of those PRs used a GitHub closing keyword against them — a
  tracking gap, not a work gap. See
  [`QPS_GITHUB_ROUNDTRIP_HANDOVER.html`](QPS_GITHUB_ROUNDTRIP_HANDOVER.html) §1/§3.
- The BT34 companion file's own `Standards_Register`/`Deliverables_Register`
  granularity claim ("likely the source detail v24's summary was digested
  from") is inferred from row-count and column-shape similarity, not proven
  by tracing an actual build script.
