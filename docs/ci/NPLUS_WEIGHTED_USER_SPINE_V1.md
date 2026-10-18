# CODE PURPLE - weighted N+i process DAG / SIPOC / USER SPINE v1

**Status:** proposed read-only projection for user review, not a new canonical SSOT, CI admission mechanism or autonomous scheduler. Main currently has unqualified P0 required-check and independent-approval enforcement: `MERGE_ADMISSION=HOLD`. User choice does not waive existing code-security or QPS child authority.

## Canonical sources retained

- [ABACUS graph/LDAB/merge-runway authority](../CODE_PURPLE_EXECUTION_GRAPH_ARCHITECTURE.md)
- [MIP native SIPOC/DAG/3P contract](MIP_SIPOC_DAG.md)
- [ABACUS repo-local cADR and child QPS authority](../../triage/CADR_REPOSITORY_ARCHITECTURE.md)
- [Typed graph and SIPOC producer](../../tools/everred_v3/acceptance/graph.py)
- [Existing GitHub-first handover template](../../handover/HANDOVER_MESSAGE_TEMPLATE.md)

This additive overlay **does not override those sources**. Existing visualization stays at `docs/code_purple_execution_graph.html`. Main historical weighted evidence is frozen in [NPLUS_WEIGHTED_RUN_CATEGORY_20261018.json](../data/NPLUS_WEIGHTED_RUN_CATEGORY_20261018.json).

## Three network graphs use one absolute scale

The left/middle/right network views show *workflow executions*, *successful workflow executions* and *failed workflow executions* against **identical** category/wave positions. A link is a descriptive observed category count, not an engineering root, dispatch or causal dependency.

- Edge width: `1 + 2.7 * sqrt(weight)` pixels, **same formula in all three views**.
- Wave radius: `7 + 2.5 * sqrt(sum outgoing metric)`.
- Category radius: `6 + 1.5 * sqrt(sum incoming metric)`.
- 7 exact-SHA wave atoms, 8 curated category atoms and 49 nonzero *run-count* category links. All run, success and failure weights are integers, not normalized separately.
- N23 source highlight **green**; N27 source highlight **gold**. This highlights cohort identity, not PASS status. Failure edges use red. N26* is a one-run divergent branch.
- At the 18 Oct 2026 readback: 165 total run executions, 122 successful, 22 failed, 21 cancelled/other terminal; all seven displayed cohorts terminal at that observation.
- N23 37/31/4/2 (runs/success/failed/cancelled) vs N27 28/21/6/1; **N23 repeated qps-canonicalization 12 times (one workflow ID), N27 once**. N23 26 distinct workflow IDs; N27 28. Workflow-run ratios are not pytest test-case coverage.
- Run counts on historic SHAs may change after re-trigger. Record fresh observation epoch instead of silently altering the frozen baseline.

## Process DAG and SIPOC (not a new SSOT)

Source [Mermaid DAG](NPLUS_WEIGHTED_USER_SPINE_V1.mmd) includes exact SHA -> family census -> scoped testflight -> native receipts -> coverage/root evidence -> independent P0 gate -> main readback. Feedback is a separately marked next-iteration overlay.

| SIPOC | Source-owner treatment |
| --- | --- |
| Suppliers | GitHub runner, ABACUS source/test owners, CODEX governance consumer, authorized reviewer/admin, QPS child authority |
| Inputs | Exact SHA, workflow ID/run/attempt, path and dependency lease, configured scanner, JUnit/coverage/ZIP digest, user choice |
| Process | Observe -> classify three denominators -> compete advisory options -> user choose/veto -> bounded source work -> native verify -> HOLD or owner admission |
| Outputs | Tagged workflow-family atoms and observations; separate canonical causal roots; matched statement/branch/diff pairs; native admission evidence |
| Customers | Human operator, #1860 gate owner, #1929 BD owner, MissionControl CODEX, QPS engineering acceptance owner |

## USER SPINE - proposed competition, prerogative, feedback

1. **USER sets intent and criteria** (risk, time, measurable uplift, evidence, source scope).
2. **Competition** among A governance recovery, B first-red elimination, C coverage expansion, D telemetry fidelity. These are **options**, not invented quantified scores or guaranteed winner.
3. **USER has final choice/override/veto** on prioritization. An override must carry rationale and may NOT bypass security, permissions, review or QPS authority.
4. **Bounded wave proposal only**, with disjoint owner-path lease and tests. Selection alone does not dispatch actual workers.
5. **Native evidence / N-1, N, N+1** return with comparable numerators/denominators, SHA, job and artifact digests; UNKNOWN not zero.
6. **USER feedback** accept / reject / retarget / compete again, recorded as local proposal for the next independent iteration. The loop is not a cycle in execution/acceptance DAG.

The standalone offline HTML prototype supports focus-wave/category, edge inspection, explicit choice, manual comparison priority, feedback and JSON export. SVG and one-page A2 landscape vector PDF are derived from the same render. **Rendered artifacts are delivered separately for visual review; this branch contains only the documentation and compact GitHub-source data, not the full PDF binary nor a registered deployment.**

## USER feedback data contract

Recommended fields: `schema=code-purple.user-spine-feedback-draft.v1`, `selected_lane`, `comparison_priority`, `decision` (choose / override / veto / request review), `feedback`, `reference_main_sha`, and immutable `source_cohorts`. Guard fields: `not_a_dispatch=true`, `merge_authorized=false`, `independent_review_required=true`, `qps_child_authority_retained=true`.

No personal profile or preference scores are inferred by the observatory. User selection is an iteration input, never a substitute for effective GitHub protected merge policy.

## Definition of done / next development cycle

- [ ] User reviews layout and chooses which metric/competing options dominate; incorporate documented feedback.
- [ ] Owner verifies workflow-family-to-category assignment and final SOURCE SHA list; no category edge may count as source-owned causal root proof.
- [ ] HTML/SVG/PDF rendering parity and keyboard/Windows browser QA on actual published viewer, with source-bound asset digest.
- [ ] Publish reproducible repo-owned renderer only after owner approval; no duplicate SSOT or hard-coded token.
- [ ] Obtain native CI JUnit/coverage and canonical BD owner dispositions with matched populations.
- [ ] Administrator restores effective required checks + eligible independent approval and proves blocked RED negative canary before any governed merge credit.

`P0=HOLD`, `AUTHORITY_TRANSFER=false`, `CODEX_AUTHENTICATED_CREW_LAUNCH=UNKNOWN`, `CANONICAL_BD_ROOT_OPEN/CLOSED=UNKNOWN/UNKNOWN`, `MATCHED_MAIN_DIFF_COVERAGE_UPLIFT=UNKNOWN`.
