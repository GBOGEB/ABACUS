# ABACUS current BD queue

**As of:** 2026-09-21  
**Repository:** `GBOGEB/ABACUS`  
**Start of this pulse:** 30 open issues  
**Evidence-backed closures in this pulse:** #1186, #1187, #1188, #1195  
**Current open count after those closures:** 26

This file is the human-facing view of `ABACUS_BD_QUEUE_CURRENT.yaml`. The YAML is the
machine-readable queue authority for this burn-down pulse.

| Lane | Issues | Operating rule |
|---|---|---|
| **EXECUTE_NOW** | #683, #645, #818 | Bounded code/contract repair. Every fix must land through a PR and carry a closure gate. |
| **VERIFY_CLOSE** | #583, #672, #673, #674, #679, #1002, #1256 | Implementation/evidence appears to exist; verify the exact DoV before closing. |
| **EXTERNAL / LOCAL RETURN** | #633, #635, #636, #637, #638, #1278 | Do not spend coding capacity to fake missing local/Office/admin evidence. |
| **PROGRAMME PARENT** | #581, #644, #659, #667, #750, #776, #785, #981, #1164, #1180 | Keep only while real child gates or programme outcomes remain active. |

## First burn-down order

1. **#683 — executable first fix.** Add a path-scoped `pull_request` trigger to the
   hardened QPS DOW warm-up and prove the six-stage receipt on the PR head.
2. **#679 — verify and close** if current-main regression evidence confirms the already
   merged #680/#695/#702 hardening.
3. **#583 — verify and close** if the requested scenario/progress/RTM files are already
   present and complete.
4. **#1256 — verify downstream receipt consumption** of the exact support pin from #1267;
   close once MissionControl/QPS binding is evidenced.
5. **#645 / #818 — bounded implementation slices**, not broad refactors.
6. **#1278 stays visible but leaves the runnable crew queue.** Its remaining gate is
   owner/admin merge-admission configuration, not another code repair.

## Closure rule

An issue leaves this queue only when one of these is explicit:

- **FIXED:** merged PR + required runtime/CI receipt;
- **VERIFIED_COMPLETE:** existing implementation is proven against the issue DoV;
- **SUPERSEDED:** named successor owns the remaining scope;
- **EXTERNAL_RETURN:** still open, but blocked on an owner/local/private-evidence action.

Age, issue volume, a green unrelated workflow, or a merged PR by itself is not closure.
