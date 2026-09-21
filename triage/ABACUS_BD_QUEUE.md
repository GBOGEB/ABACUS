# ABACUS current BD queue

**As of:** 2026-09-21  
**Repository:** `GBOGEB/ABACUS`  
**Start of pulse:** 30 open issues  
**Evidence-backed closures:** 18  
**Current open count:** 12

The YAML file is the machine-readable queue authority. This file is the
human-facing execution view.

## Current lanes

- **NEXT_RECONCILE — 2:** #644, #1002.
- **CONTROL_WATCH — 1:** #776.
- **EXTERNAL / LOCAL RETURN — 5:** #633, #635, #636, #637, #1278.
- **PROGRAMME PARENT — 4:** #667, #785, #981, #1164.

There is currently no unambiguous code-only `EXECUTE_NOW` item. Phase-5
#638 is source-side complete. Its physical release predicates remain
losslessly under #635/#636/#637 and #633. The next useful work is evidence
reconciliation, not another speculative framework.

## Completed in this pulse

Closed or retired with evidence:

- #583, #645, #659, #672, #673, #674, #679, #683;
- #750, #818, #1180, #1186, #1187, #1188, #1195, #1256, #581, #638.

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

1. Reconcile #644 against the current binary/parser/round-trip/federation
   implementation. Close it if the requested minimum bridge tuple is already
   executable; otherwise split only the residual gap.
2. Reconcile #1002 against current exact-head TRIAGE controls. Do not promote
   registry presence into a synchronized-green claim.
3. Keep #776 on measured control watch. The queue improved from 148/5 to a
   current 19/15 checkpoint, but a follow-up 18/1 sample does not yet prove
   repeated healthy occupancy.
4. Leave #1278 outside coding capacity. Its remaining gate is owner/admin merge
   admission, not another code detector.

## Closure rule

An issue leaves this queue only as one of:

- **FIXED:** merged repair plus required runtime or CI receipt;
- **VERIFIED_COMPLETE:** existing implementation proven against its DoV;
- **SUPERSEDED:** a named successor owns the remaining gate;
- **EXTERNAL_RETURN:** still open but waiting on local/private/admin evidence.

Age, issue count, an unrelated green workflow, or a merged PR alone is not
closure.
