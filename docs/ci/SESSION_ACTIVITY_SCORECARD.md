# Session activity scorecard — DMAIC, PCA, BT and CI coverage

Snapshot: 2026-08-29  
Scope: `GBOGEB/ABACUS`, with read-only status comparison to `GBOGEB/CODEX` and `GBOGEB/DOCX_RTM_Automation`.

## Direct status

This scorecard separates **coverage**, **technical completion** and **requirement closure**. They are not interchangeable.

| Measure | Current score | Meaning |
|---|---:|---|
| Structural coverage | 100% | 87/87 ABACUS workflow definitions are classified by the proposed CI policy, including the new governance workflow. |
| Analytical population coverage | 100% | PCA covers 722/722 RTMs; BT/ranking tables cover 722/722 RTMs and 50/50 OFFER items. |
| Evidence/automation coverage | 76% | Reproducible scripts and governed extracts exist, but dedicated PCA/BT CI assertions and one release-lineage chain remain incomplete. |
| Current-session completion | 74% | Define/Measure/Analyse are mature; Improve is implemented in the PR; Control remains pending until checks execute and the new report is accepted. |
| Requirement/contract closure | 0% claimed | The governed v24 pass is prioritisation metadata and item-level review coverage, not bidder acceptance or requirement closure. |

The composite **technical coverage score is 92%**:

`0.30×workflow classification (100) + 0.25×PCA population (100) + 0.25×BT population (100) + 0.20×automation evidence (60) = 92`.

The separate **session completion score is 74%**:

`mean(Define 100, Measure 95, Analyse 90, Improve 65, Control 20) = 74`.

Control is deliberately the limiting term. A queued check is not evidence that code passed.

## DMAIC activity

| Phase | Score | Evidence | Remaining control |
|---|---:|---|---|
| Define | 100% | Scope fixed to workflow/test clustering, ordering and consolidation in a separate ABACUS PR. | None. |
| Measure | 95% | Live baseline: 86 workflows; PR #681 had 119 checks (111 queued, 8 skipped); ABACUS main exposed 122 check runs. | Capture post-merge run-time and check-count delta. |
| Analyse | 90% | Functional clusters, lifecycle order, canonical owners and repeated commands are machine-audited. | Add duration/cost data once completed runs are available consistently. |
| Improve | 65% | Policy, audit script, regression test, governance workflow and path-scoped trigger changes are in the PR. | Prove reduced check fan-out on a representative docs-only and code PR. |
| Control | 20% | Fail-closed classification and canonical-owner tests are written. | PR checks must execute; report artifact and policy hash must be retained; follow-up deletion requires accepted replacement evidence. |

## PCA metric

PCA is exploratory structure, not a second ranking authority.

| PCA metric | Current value |
|---|---:|
| Population | 722 RTMs |
| Dimensions | 7 — L/R/P/F/Q/LC/C |
| PC1 variance | 30.6% |
| PC2 variance | 16.5% |
| PC1+PC2 cumulative | 47.1% |
| First five PCs cumulative | 84.5% |
| Typical/bulk items | 548 (76%) |
| Distinctive items | 174 (24%) |
| Strongest near-independent axis | Cost on PC3, loading 0.881 |

PCA readiness score: **79%**.

- Population coverage: 100%.
- Named reproducible script and result JSON: 90%.
- Workbook/Navigator integration: 90%.
- Version/lineage clarity: 75% (`pca_results_v23.json` feeds the v24 analytical sheet; the relationship is documented but the filename remains v23).
- Dedicated CI assertions for explained variance, loadings and 722-row identity: 40%.

## Bradley–Terry / ranking metric

| BT/ranking metric | Current value |
|---|---:|
| RTM population | 722/722 |
| OFFER population | 50/50 |
| v24 sum Weighted S | 21,674.3 |
| v24 average Weighted S | 30.02 |
| Change v22→v23 | +6.6 (+0.03%), one named RTM-320 correction |
| Change v23→v24 | 0.0 |
| Crosswalk linked | 722/722 (100%) |
| OFFER review-OK indicator | 94% |
| Planned v24 item-level review pass | Complete |
| Requirement closure created by BT/PCA | None |

BT analytical readiness score: **88%**.

The score is not 100% because the workbook still discloses a static legacy RTM-BT snapshot with a 4-dimension L/R/P/F scheme and only 130 formulas across 34,838 cells (0.4% formula density), while the canonical model elsewhere is 7-dimensional. The method is stable, but authority is split between a static snapshot and the live seven-dimension model. The next control action is to make one canonical recomputation contract and test the exact `rank`, `tier`, `Weighted S`, `BT Win %` and `BT λ` fields from SSOT input through generated views.

## CI/CD status at snapshot

| Repository | Definitions | Latest-head status | Last verified success | Known failure |
|---|---:|---|---|---|
| ABACUS | 86 before this PR | 122 checks: 109 queued, 13 skipped on `main`; PR #681: 119 checks, 111 queued, 8 skipped | CI - ABACUS Matrix run 33250830458: Python 3.10/3.11/3.12 jobs completed successfully | Execution Spine Validation run 33250830397 failed in QPLANT presentation-engine tests |
| CODEX | 50 | 39 queued checks; three workflows failed before creating jobs | Dashboard Health run 33238227466 | `ci.yml`, `osv-scanner.yml`, `qps-roundtrip-policy.yml` failed at workflow start with zero jobs |
| DOCX_RTM_Automation | 3 | Python CI passed; Pages failed | Python CI run 32293426129 | Pages run 32293425321 failed at checkout; deploy skipped |

## Completion rule

This session moves to **Control complete** only when:

1. the CI-governance workflow classifies every workflow exactly once;
2. canonical workflow owners exist;
3. a docs-only PR demonstrates materially lower test fan-out;
4. a code PR still exercises its relevant domain suites;
5. the generated inventory/report is attached with the policy hash;
6. no required status protection is silently removed (ABACUS `main` was observed unprotected at this snapshot).

