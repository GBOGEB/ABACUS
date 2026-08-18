# Build pipeline — entry/exit points

ASCII diagram of the actual, current pipeline: what goes in, what scripts
run in order, what comes out. Every arrow is a real script edge from
`SESSION_SSOT.yaml`'s `builder_chain` entries — nothing here is idealized or
aspirational. Six independent exit families all trace back to one entry
point: the FULL workbook. Two decks are separate lineages that never touch
the workbook programmatically (human-carried-forward content only).

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
   ||   v16 -> v17 -> v18 -> v19 -> v20         ||          +-------------------+
   ||                                           ||                    |
   ||        QPS_OFFER_Evaluation_FULL_v20.xlsx ||                    v
   ||           <<< THE SINGLE SSOT >>>         ||          QPS_MTBF_WCS_DMAIC_v7.pptx
   +===========================================+           (mtbf_dmaic_deck family,
            |         |          |         |                separate lineage --
            |         |          |         |                does not feed or get
            |         |          |         |                fed by the workbook)
   +--------+   +-----+----+  +--+------+  +---------+
   |            |          |            |            |
   v            v          v            v            v
+--------+ +---------+ +--------+ +-----------+ +------------------+
|build_  | |export_  | |compute_| |bt_method_ | | (bt_method_deck   |
|workbook| |nav_data | |metrics_| |deck: human-| |  family below --  |
|_slim_  | |.py      | |snapshot| |carried     | |  see next block)  |
|v20.py  | |         | |.py     | |content,not | |                   |
+--------+ +---------+ +--------+ |script-driven| +------------------+
    |           |           |     |from workbook|
    v           v           v     +-------------+
QPS_OFFER_  /tmp/nav_    METRIC_
Evaluation_ data_v20.    HISTORY.json
LITE_v20.   json               (dmaic_metric_history
xlsx             |             family -- version-over-
(workbook_lite   |             version stats, not a
 family)         v             human-facing document)
            navigator_template.html
            + inline splice
            (str.replace of
            __NAV_DATA_JSON__)
                 |
                 v
       QPS_RTM_BT_Navigator_v15.html
       (html_navigator family)


   BT_Method_Evaluation_v6.pptx  (from build_bt_deck_v6.py)
                 |
                 v
       [v7, v8 undocumented -- inline edits, see gaps.missing_build_scripts]
                 |
                 v
       [v9: inline python, 2 new PCA/quadrant slides -- not yet a saved script]
                 |
                 v
       BT_Method_Evaluation_v9.pptx   (bt_method_deck family)


   nav_data_v7.json  --(build_pdf_export.py)-->  QPS_Taxonomy_and_
                                                  Domain_Summary.pdf
                                                  (pdf_exports family --
                                                   STALE, v7 data, workbook
                                                   is now v20 -- see gaps)


                                    EXIT POINTS
                                    ===========
   1. QPS_OFFER_Evaluation_FULL_v20.xlsx   -- SSOT, internal working file
   2. QPS_OFFER_Evaluation_LITE_v20.xlsx   -- external reviewer trim
   3. QPS_RTM_BT_Navigator_v15.html        -- read-only browser companion
   4. BT_Method_Evaluation_v9.pptx         -- BT methodology deck
   5. QPS_MTBF_WCS_DMAIC_v7.pptx           -- MTBF/reliability deck (separate lineage)
   6. QPS_Taxonomy_and_Domain_Summary.pdf  -- static print reference (stale)

   Plus non-document exits that feed the above rather than being handed to
   anyone directly: METRIC_HISTORY.json (version-over-version stat tracking),
   /tmp/nav_data_vN.json (Navigator's data source, regenerated each round).
```

## Reading the diagram

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
  `gaps.missing_build_scripts` in `SESSION_SSOT.yaml` for the full list and
  the recommendation for closing it going forward.
- **`export_nav_data.py` is the one script three different consumers
  depend on** (Navigator directly; PDF export depends on an older snapshot
  of the same script's output; METRIC_HISTORY.json is a sibling, not a
  consumer, since it reads the workbook directly rather than through the
  JSON export). If this script's field list changes, check both downstream
  consumers, not just the Navigator.
