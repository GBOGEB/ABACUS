# ABACUS current BD queue

**As of:** 2026-09-26
**Repository:** `GBOGEB/ABACUS`
**Start of pulse:** 30 open issues
**Discovered during pulse:** 2 (#1313, #1369)
**Evidence-backed closures:** 20
**Current open count:** 12

The YAML file is the machine-readable queue authority. This file is the
human-facing execution view.

## Current lanes

- **NEXT_RECONCILE — 0:** none.
- **PROVE — 1:** #1369.
- **CONTROL_WATCH — 0:** none.
- **EXTERNAL / LOCAL RETURN — 7:** #633, #635, #636, #637, #644, #1278,
  #1313.
- **PROGRAMME PARENT — 4:** #667, #785, #981, #1164.

There is currently no code-only `EXECUTE_NOW` item. The sole bounded active
lane is proof-only #1369, which must execute existing W62/W64/W7x/W8x controls
on one common exact `main` SHA. RETURN/HOLD lanes consume no coding capacity.

## Completed in this pulse

Closed or retired with evidence:

- #583, #645, #659, #672, #673, #674, #679, #683;
- #750, #818, #1180, #1186, #1187, #1188, #1195, #1256, #581, #638;
- #776, #1002.

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

1. Execute proof-only successor #1369 using the existing workflow-dispatch
   entry points; do not mutate workflow semantics merely to force evidence.
2. Execute #644 only when the governed binary set and cryoplant consumer are
   available; public fixture proof does not satisfy its issue-level DoD.
3. Keep #1313 outside coding capacity until authoritative Appendix 8.4 and
   named calibration/source evidence returns. Do not infer mode/valve state.
4. Leave #1278 outside coding capacity. Its remaining gate is owner/admin merge
   admission, not another code detector.
5. Re-enter #635 only on the real Windows/evidence-vault production roundtrip;
   public parser proof cannot substitute for that external evidence.

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
