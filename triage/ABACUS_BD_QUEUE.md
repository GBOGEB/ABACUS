# ABACUS current BD queue

**As of:** 2026-09-26
**Repository:** `GBOGEB/ABACUS`
**Start of pulse:** 30 open issues
**Discovered during pulse:** 7 (#1313, #1369, #1377, #1379, #1380, #1381, #1391)
**Evidence-backed closures:** 22
**Current open count:** 15

The YAML file is the machine-readable queue authority. This file is the
human-facing execution view.

## Current lanes

- **NEXT_RECONCILE — 0:** none.
- **EXECUTE_NOW — 0:** none.
- **PROVE — 0:** none.
- **PROVE_HOLD — 3:** #1379, #1380, #1381.
- **CONTROL_WATCH — 0:** none.
- **EXTERNAL / LOCAL RETURN — 8:** #633, #635, #636, #637, #644, #1278,
  #1313, #1369.
- **PROGRAMME PARENT — 4:** #667, #785, #981, #1164.

There is currently no code-only `EXECUTE_NOW` or active `PROVE` item.
Issue #1369 is an external execution-return gate because the required
`workflow_dispatch` runs cannot be created by the connected execution surface.
Issues #1379/#1380/#1381 are shared proof-hold children after merged PR #1384 and must
not trigger new coding unless a material current-code first red appears.

## Completed in this pulse

Closed or retired with evidence:

- #583, #645, #659, #672, #673, #674, #679, #683;
- #750, #818, #1180, #1186, #1187, #1188, #1195, #1256, #581, #638;
- #776, #1002, #1377, #1391.

Issue #644 received its repository-local bridge implementation through
PRs #1365 and #1366, but remains open for its governed-binary execution and direct
consumer-ingestion DoD. Issue #776 closed after PR #1325 and distinct
post-control same-ref runs proved superseded unified-CD cancellation.

The Wave-01 runtime now has a merged/default-branch receipt:

- source SHA: `3d0456e8d0c47dddebb3a16a400c581f138edc1d`;
- run: `35591481543`;
- job: `106306626481`;
- artifact: `10634817457`;
- six required DOW stages: PASS.

The stronger W04 real-source cycle remains the closure basis for #659:

- run: `33330746930`;
- artifact: `9738796700`;
- child disposition: 0 ACCEPT / 5 REJECT / 4 DEFER;
- re-ingestion: deterministic no-op because no DOW child delta was accepted.

## Next execution edge

1. Reconcile the shared #1379/#1380/#1381 proof-hold set against existing
   merged PR #1384 evidence; close only when their requested proof set is
   actually satisfied, and repair only on a material current-code first red.
2. Re-enter #1369 only when seven real workflow-dispatch run IDs exist on one
   unchanged main SHA. Reject mixed-SHA evidence.
3. Execute #644 only when the governed binary set and cryoplant consumer are
   available; public fixture proof does not satisfy its issue-level DoD.
4. Keep #1313 outside coding capacity until its source/calibration closure
   predicates are satisfied; do not infer missing engineering values.
5. Leave #1278 outside coding capacity. Its remaining gate is owner/admin merge
   admission, not another code detector.

## Closure rule

An issue leaves this queue only as one of:

- **FIXED:** merged repair plus required runtime or CI receipt;
- **VERIFIED_COMPLETE:** existing implementation proven against its DoV;
- **SUPERSEDED:** a named successor owns the remaining gate;
- **EXTERNAL_RETURN:** still open but waiting on local/private/admin evidence.

Age, issue count, an unrelated green workflow, or a merged PR alone is not
closure.

## #1002 disposition

Issue #1002 is `SUPERSEDED_WITH_REPLACEMENT`. Current `main` already contains the
required control surfaces; the remaining gap is a synchronized exact-head
cluster receipt. That proof-only residual moved to #1369 with no new
architecture authority or engineering credit.

## Recent verified closures

- **#1377 — VERIFIED_COMPLETE:** PR #1406 merged as
  `7b6a39f96a4a48c5d7ff01733467ae15f2d12049`; Codex was clean and
  post-merge run `36256707225` re-executed all bounded zero-denominator and
  mixed-state AHT regressions successfully. Later suite reds were unrelated.
- **#1391 — VERIFIED_COMPLETE / GREEN_CONTROL:** PR #1403 merged as
  `1500fb73adfefe54d0549afc64986e1be0f54f96`; post-merge DMAIC run
  `36254865597` reproduced **70.73%** coverage against the unchanged 70%
  hard gate with non-coverage gates green.
