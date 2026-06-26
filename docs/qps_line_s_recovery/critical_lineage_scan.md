# Critical Lineage Scan - QPS Line S Recovery Build

## Purpose

This scan reviews the raw prompt and assistant-output conversation lineage and converts it into a convergence-control view for the QPS Line S recovery package.

## Executive finding

The build has converged from an open calculation request into a repo-backed reduced engineering model. The direction is correct, but the next work must avoid uncontrolled expansion into full SIMCRYOGENICS before the Applicant answer package is closed.

## Evolutionary lineage

| Step | User intent | Assistant/build response | Current status | Critical note |
|---:|---|---|---|---|
| 1 | Calculate helium mass and filling time for 120 m3, 15 barg, 300 K | Ideal-gas mass and fill-rate model created | complete | This established the reusable pressure accumulation factor. |
| 2 | Reframe Applicant question for RTM-261 and RTM-292 | First recovery-path answer created | complete | Good framing, but initially too shallow. |
| 3 | Expand into deep answer paths, sensitivities, investigations | 21-part technical framing created | complete | Strong conceptual structure; needs packaging discipline. |
| 4 | Add D2.1 LOOP p34-37 source basis | LOOP flow-profile logic integrated | complete | Source-grounded turning point. |
| 5 | Add Appendix 8.2, 8.3, 8.4 | Reduced model lineage established | started | Scope risk begins here: full model temptation. |
| 6 | Add native DOCX and 8700 W sensitivity | Native parsing basis and Excel/Python outputs created | started | Good execution; first heat sensitivity direction was later corrected. |
| 7 | Correct heat-load lineage | 8700 W corrected to design point = true baseline x 1.44 | complete | Critical correction preserved in README and Python model. |
| 8 | Create GitHub repo scaffold | Branch w001, issue #581, draft PR #582 created | complete | Repo-backed traceability now active. |
| 9 | Parallelize helper work | Agent A, Agent B, CODEX helper issues created | started | Good orchestration; requires issue-to-file closure tracking. |
| 10 | Compile raw conversation pairs | Current critical scan created | active | This file becomes the convergence checkpoint. |

## Stable invariants

These must not drift:

1. The immediate deliverable is the Applicant answer for RTM-261 and RTM-292.
2. The current model is reduced and first-order; it is not full SIMCRYOGENICS.
3. D2.1 is the MASTER SSOT for this session, even if later design data supersedes it.
4. Appendix 8.2 is topology, Appendix 8.3 is model lineage, Appendix 8.4 is mode and valve-state logic.
5. The 200 g/s case is not credited against 2 x 50 g/s recovery compressors alone.
6. The credible 200 g/s path requires HP compressor availability or a bounded pressure-buffer proof.
7. The 112 g/s pre-HP case creates 12 g/s accumulation against 100 g/s recovery.
8. The pressure build-up criterion is pressure margin divided by pressure rise rate, not a standalone arbitrary pressure value.
9. The corrected heat-load lineage is: true baseline = 8700 / 1.44, uncertainty-only = 7250 W, design point = 8700 W.
10. Every repo artifact must remain indexed.

## Drift risks

| Risk | Symptom | Control |
|---|---|---|
| Full SIMCRYOGENICS expansion too early | Work shifts to full plant reproduction before Applicant package closes | Keep full SIMCRYOGENICS as W005+ only. |
| File proliferation without closure | Many manifests and trackers but no final answer | Maintain one release checklist and one final technical note. |
| Incorrect heat-load basis reappears | 8700 W treated again as 1.0x baseline | Use corrected constants only. |
| Unclear pressure limit | Answer implies an allowed pressure without knowing Line S design/relief/compressor limits | State criterion and confirmation list. |
| Agent work divergence | Agent A and B produce overlapping or conflicting files | Require index update and progress update per file. |
| Raw transcript overcompression | Future work relies on summary memory rather than raw pairs | Keep this critical scan linked to raw prompt/output file. |

## Convergence plan

### Gate 1 - Applicant answer package

Must include:

- final concise answer
- assumption table
- pressure-build-up criterion
- scenario matrix
- RTM traceability
- confirmation list
- model-output appendix

### Gate 2 - Reduced model validation

Must include:

- runnable Python validation
- known reference values
- Excel-compatible CSV or JSON
- corrected heat-load cases

### Gate 3 - Mode and valve-state extraction

Must include:

- Appendix 8.4 mode list
- valve state table
- fail open / fail closed assumptions
- available recovery path per mode

### Gate 4 - Release decision

Possible outcomes:

- close as Applicant-response package
- continue into CoolProp upgrade
- continue into Appendix 8.4 FMECA precursor
- continue into full SIMCRYOGENICS reproduction

## Recommended next action

Do not expand the model further until the final Applicant answer package has been created as a single Markdown document and linked from `index.json`.
