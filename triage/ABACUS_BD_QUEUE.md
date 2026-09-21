# ABACUS current BD queue

**As of:** 2026-09-21  
**Repository:** `GBOGEB/ABACUS`  
**Start of this pulse:** 30 open issues  
**Evidence-backed closures in this pulse:** #1186, #1187, #1188, #1195, #583  
**Current open count after those closures:** 25

This file is the human-facing view of `ABACUS_BD_QUEUE_CURRENT.yaml`. The YAML is the
machine-readable queue authority for this burn-down pulse.

| Lane | Issues | Operating rule |
|---|---|---|
| **EXECUTE_NOW** | #683, #679, #645, #818 | Bounded code/contract repair. Every fix must land through a PR and carry a closure gate. |
| **VERIFY_CLOSE** | #672, #673, #674, #1002, #1256 | Implementation/evidence appears to exist; verify the exact DoV before closing. |
| **EXTERNAL / LOCAL RETURN** | #633, #635, #636, #637, #638, #1278 | Do not spend coding capacity to fake missing local/Office/admin evidence. |
| **PROGRAMME PARENT** | #581, #644, #659, #667, #750, #776, #785, #981, #1164, #1180 | Keep only while real child gates or programme outcomes remain active. |

## First burn-down order

1. **#683 — runtime first-red repair.** PR #1300 proved the new PR lane but failed
   at Stage 1 with `ModuleNotFoundError: DMAIC_V3`. PR #1306 is the active
   fix/proof transaction.
2. **#679 — promoted back to EXECUTE_NOW.** Static review found the canonical Stage-5
   file still declares `0.0.0-stub`; a stub must never earn a successful stage.
3. **#1256 — verify downstream receipt consumption** of the exact support pin from #1267;
   close once MissionControl/QPS binding is evidenced.
4. **#645 / #818 — bounded implementation slices**, not broad refactors.
5. **#1278 stays visible but leaves the runnable crew queue.** Its remaining gate is
   owner/admin merge-admission configuration, not another code repair.

## Closure rule

An issue leaves this queue only when one of these is explicit:

- **FIXED:** merged PR + required runtime/CI receipt;
- **VERIFIED_COMPLETE:** existing implementation is proven against the issue DoV;
- **SUPERSEDED:** named successor owns the remaining scope;
- **EXTERNAL_RETURN:** still open, but blocked on an owner/local/private-evidence action.

Age, issue volume, a green unrelated workflow, or a merged PR by itself is not closure.
