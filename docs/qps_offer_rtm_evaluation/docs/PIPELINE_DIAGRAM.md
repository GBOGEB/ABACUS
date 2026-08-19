# Build pipeline + evaluation process — ASCII reference

Two different diagrams, kept deliberately separate (conflating "how the
files get built" with "how a requirement gets evaluated" was flagged as a
real risk elsewhere in this project — same instinct as keeping the two PCA
analyses distinct):

1. **Build pipeline** — what goes in, what scripts run in order, what comes
   out. Every arrow is a real script edge from `SESSION_SSOT.yaml`'s
   `builder_chain` entries — nothing here is idealized or aspirational.
2. **Evaluation process** — what actually happens to one requirement or one
   OFFER response, end to end, independent of which script touched which
   file. This is new this round (GBO asked for "process ASCII" directly).

Refreshed this round: canonical versions updated (workbook v20→**v24**,
Navigator v15→**v22**), two new named scripts added
(`compute_pca.py`, `compute_weight_scenario4.py`). LITE, the PDF export,
and both decks are **not yet re-synced to v24** — shown as stale below,
not silently advanced.

---

## 1. Build pipeline

```
                                   ENTRY POINTS
                                   ============
   GBO's hand-edited base          GBO's uploaded          QPS_MTBF_WCS.pptx
   + QPS_RTM_BT_Standalone.xlsx    annotation file          (reliability deck
   (one-time, v5 only)             (.txt, periodic)          source, v5 only)
            |                              |                        |
            v                              v                        v
   +--------------------+       +-------------------+     +-------------------+
   | build_workbook_     |       | build_workbook_v20|     | build_deck.py     |
   | full_v5.py          |       | .py                |     |  .. build_deck5.py|
   +--------------------+       +-------------------+     +-------------------+
            |                              ^                        |
            v                              |                        v
   +===========================================+          +-------------------+
   ||   FULL_v5 -> v6 -> v7 -> v8 -> v9 ->      ||          | fix_mtbf_rtm_     |
   ||   [v10..v15 undocumented, see gaps] ->    ||          | numbers.py        |
   ||   v16 -> v17 -> v18 -> v19 -> v20 -> v21  ||          +-------------------+
   ||   -> v22 -> v23 -> v24 (this round)       ||                    |
   ||                                           ||                    v
   ||        QPS_OFFER_Evaluation_FULL_v24.xlsx ||          QPS_MTBF_WCS_DMAIC_v7.pptx
   ||           <<< THE SINGLE SSOT >>>         ||          (mtbf_dmaic_deck family,
   +===========================================+           separate lineage --
            |         |          |         |                does not feed or get
            |         |          |         |                fed by the workbook)
   +--------+   +-----+----+  +--+------+  +---------+
   |            |          |            |            |
   v            v          v            v            v
+--------+ +---------+ +--------+ +-----------+ +------------------+
|build_  | |export_  | |compute_| |bt_method_ | | compute_pca.py    |
|workbook| |nav_data | |metrics_| |deck: human-| | compute_weight_   |
|_slim_  | |.py      | |snapshot| |carried     | | scenario4.py      |
|v23.py  | |         | |.py     | |content,not | | (NEW this round -- |
+--------+ +---------+ +--------+ |script-driven| | named, discoverable,|
    |           |           |     |from workbook| | not /tmp scratch)  |
    v           v           v     +-------------+ +--------------------+
QPS_OFFER_  nav_data_    METRIC_                        |          |
Evaluation_ v24.json.    HISTORY.json                   v          v
LITE_v23.        |       (dmaic_metric_history    pca_results_  weight_
xlsx (STALE      |       family -- version-over-  v23.json      scenario4_
1 version        |       version stats, not a                  v23.json
behind FULL_v24  |       human-facing document)         |          |
 -- see gaps)    v                                      +----+-----+
            navigator_template.html                          |
            + splice_navigator.py                    (both feed back into
            (script-saved, no longer                  export_nav_data.py's
             inline python)                            "pca" / "weightScenario4"
                 |                                      keys, and into
                 v                                      PCA_ANALYSIS / WEIGHTS_METHOD
       QPS_RTM_BT_Navigator_v22.html                     inside build_workbook_v24.py)


   BT_Method_Evaluation_v6.pptx  (from build_bt_deck_v6.py)
                 |
                 v
       [v7, v8 undocumented -- inline edits, see gaps.missing_build_scripts]
                 |
                 v
       BT_Method_Evaluation_v9 -> v10 -> v11 -> v12.pptx   (STALE -- v12 built
                                                              against nav_data_v23,
                                                              this round's PCA/
                                                              weight-scenario-4
                                                              findings not yet
                                                              in the deck, see
                                                              backlog Section 28d)


   nav_data_v7.json  --(build_pdf_export.py)-->  QPS_Taxonomy_and_
                                                  Domain_Summary.pdf
                                                  (pdf_exports family --
                                                   STALE, v7 data, workbook
                                                   is now v24 -- see gaps)


                                    EXIT POINTS
                                    ===========
   1. QPS_OFFER_Evaluation_FULL_v24.xlsx   -- SSOT, internal working file
   2. QPS_OFFER_Evaluation_LITE_v23.xlsx   -- external reviewer trim (1 version stale)
   3. QPS_RTM_BT_Navigator_v22.html        -- read-only browser companion
   4. BT_Method_Evaluation_v12.pptx        -- BT methodology deck (stale, see 28d)
   5. QPS_MTBF_WCS_DMAIC_v7.pptx           -- MTBF/reliability deck (separate lineage)
   6. QPS_Taxonomy_and_Domain_Summary.pdf  -- static print reference (stale)

   Plus non-document exits that feed the above rather than being handed to
   anyone directly: METRIC_HISTORY.json, nav_data_vN.json,
   pca_results_v23.json, weight_scenario4_v23.json.
```

### Reading the build-pipeline diagram

- **One real SSOT.** Every arrow into the workbook_full block only ever
  flows in one direction — nothing downstream ever writes back to the
  workbook. If a number looks wrong anywhere (Navigator, LITE, PDF), the fix
  always happens in a `build_workbook_vN.py` step and propagates back out,
  never patched directly in the derived file.
- **Two lineages never touch the workbook programmatically.** Both
  PowerPoint decks (`bt_method_deck`, `mtbf_dmaic_deck`) are built and
  edited independently — their content has to be carried forward by a human
  reading the workbook, not a script reading it. That's also why both are
  flagged "watch" in the deliverables index: no script means no diff, no
  automatic regeneration.
- **Broken/missing edges are marked, not hidden.** The `[v10..v15
  undocumented]` and `[v7, v8 undocumented]` bracketed segments are real
  gaps — those versions exist as files but the script that produced them
  from the previous version wasn't saved. See
  `gaps.missing_build_scripts` in `SESSION_SSOT.yaml` for the full list.
- **`export_nav_data.py` is the one script three different consumers
  depend on** (Navigator directly; PDF export depends on an older snapshot
  of the same script's output; METRIC_HISTORY.json is a sibling, not a
  consumer, since it reads the workbook directly rather than through the
  JSON export). If this script's field list changes, check both downstream
  consumers, not just the Navigator.
- **Stale ≠ broken.** LITE/PDF/both decks all still open and work fine —
  "stale" means they reflect an earlier workbook version, not that they're
  defective. Each staleness is stated explicitly above rather than left
  for a reader to discover by comparing numbers by hand.

---

## 2. Evaluation process — what happens to one requirement or OFFER response

Not a build pipeline — this is the actual reviewer-facing workflow, the
same for every one of the 722 RTMs and 50 OFFER items, independent of which
script last touched which file.

```
  CONTRACT SOURCE (tender PDF mirror, 2024-106-IVE Addendum II)
      |
      v
  RTM / OFFER EXTRACTED  (one row each in RTM_RANKING / OFFER_RANKING)
      |
      +--> section (contract PDF subsection, e.g. "4.6.8")
      +--> shall statement + full verbatim text (all bullets/sub-items)
      +--> pdfPage (verified against real printed page numbers, v21)
      |
      v
  7-DIMENSION SCORING  (0-3 raw relevance, per dimension)
      L (Safety/Legal)  R (Reliability)  P (Performance)  F (Functional)
      Q (Quality/Verifiability)  LC (Lifecycle)  C (Cost)
      |
      v
  GATE CHECK  -----------------------------------+
      |                                          |
      | Gate = Yes (T0)                          | Gate = No
      v                                          v
  MANDATORY, must-not-fail                 WEIGHTED S = 100 x
  regardless of score --                   sum(weight x score/3)
  independent of Weighted S                       |
  (confirmed with real data,                       v
   NEXT_ITERATION_BACKLOG §7)              TIER (T1 top-10 / T2 next-16 / T3 rest)
      |                                          |
      +------------------+-----------------------+
                          v
                    OFFICIAL RANK
              (gate-first, then Weighted S)
                          |
          +---------------+----------------+
          v                                v
     BT WIN %                         BT LAMBDA INDEX
     100*(N-rank)/(N-1)                regularized MLE fit,
     static, linear, NOT               decays ~exponentially,
     iterative                         relative-strength ONLY
          |                                (not exported to Navigator
          |                                 until this round -- see
          |                                 backlog item 10)
          +---------------+----------------+
                          v
              CROSS-WALK TO OFFER  (RTM <-> OFFER, typed
              Direct / Supporting / Broad / Contextual)
                          |
                          v
              RTM_REVIEW_QUEUE  (T0/T1 + deliverable-heavy subset,
              289 of 722 -- reviewer Disposition field, human input)
                          |
                          v
              DMAIC ITERATION  (this project's own iteration unit --
              Define/Measure/Analyze real findings each round; Improve
              proposals scoped-not-built until GBO confirms; Control =
              reproducibility script saved + QA gate passed)
                          |
                          v
              HANDOVER  (workbook + Navigator + decks + PDF, each
              stamped with its own version and staleness-vs-SSOT state
              -- never silently presented as more current than it is)
```

### Reading the evaluation-process diagram

- **Score and gate are two independent signals, not one.** A T0 item can
  sit at the population floor on Weighted S (19 of 43 T0 items score
  exactly 20.00, the minimum) and still rank #1 — gate precedence overrides
  score, deliberately, always. Conflating "highly gated" with "highly
  scored" was a real question GBO asked and re-asked; the answer is
  structural, not a tuning choice (`NEXT_ITERATION_BACKLOG.md` §7).
- **BT win % and BT λ answer different questions.** Win % is a simple,
  static, linear-in-rank number — easiest to explain, not a model fit. λ is
  the closest thing to a genuine Bradley-Terry relative-strength parameter
  in this project, but its original fitting method (iteration count, if
  any) predates every script in this repo and is still an open question for
  GBO to answer directly (`NEXT_ITERATION_BACKLOG.md` §10).
- **The Review Queue is a workload subset, not the full population.** 289
  of 722 RTMs get active reviewer attention (Disposition field); the other
  433 are ranked and scored but not queued for individual sign-off — a
  workload decision, disclosed as such, not an importance claim.
- **DMAIC is the iteration unit, not a one-time phase gate.** Each round of
  this project runs its own mini Define-Measure-Analyze pass (what's the
  real question, what does live data actually show, what does it mean) —
  Improve proposals are named and scoped but built only on explicit
  confirmation (see this round's item 1 for a worked example: Improve
  Proposals A/B named in DMAIC_BT_TECHNICAL_REPORT.md §4, built only after
  GBO's direct "YES" this round), and Control means a named reproducible
  script plus a passed QA gate, every time.
