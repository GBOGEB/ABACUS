# W4 — Evidence-bound continuation and native proof

**Date:** 18 October 2026. **Fidelity:** GitHub-first operational continuity. **Snapshot non-atomic.** Canonical processes remain ABACUS `tools/handover_v2/process_spec.json`, QPS MissionControl `CP.HANDOFF/CP.RESUME` and CODEX vocabulary. This readback does not supersede the governed BD root ledger.

## Pinned five-repository census

| Source owner | Branch | Observed SHA |
| --- | --- | --- |
| ABACUS | main | `403a794e0aac453545cff922c68273b61c527e9f` |
| CODEX | main | `e422201c615db88f74aa0af02460bb5d23bfd262` |
| QPS MissionControl | master | `eee89e30dc736805387b522316a8efbe762eea4b` |
| cryoplant-project | main | `c07666b2dfc77f97980e8661fac3864f975e2d76` |
| gg_MATH | main | `7ce2e3832357c0b87ab17ff439f4d6e84c0292a4` |

These are **observations**, not live HEAD guarantees. An earlier 18 October ABACUS main `e08c51232edbb0ede05eab5bcd21f039539adf92` had [B0 39133581466](https://github.com/GBOGEB/ABACUS/actions/runs/39133581466) and [matrix 39133581513](https://github.com/GBOGEB/ABACUS/actions/runs/39133581513) queued, whereas A10 and CodeQL on that older SHA were successful. Current-main B0 at the later pinned base is UNKNOWN until rechecked.

## Native 3-pulse→W4 evidence

| Pulse | Exact provider run | Outcome | Admission meaning |
| --- | --- | --- | --- |
| P1 pilot | [39064141553](https://github.com/GBOGEB/ABACUS/actions/runs/39064141553) | 3/3 PASS | Focused pilot |
| P2 OS×Python matrix | [39064371857](https://github.com/GBOGEB/ABACUS/actions/runs/39064371857) | 9/9 PASS | Full declared test grid |
| P3 enhanced receipt | [39065353875](https://github.com/GBOGEB/ABACUS/actions/runs/39065353875) | **0/9 PASS** | Duplicate secure dependency, forecast **MISS** preserved |
| W4 corrected receipt | [39065792654](https://github.com/GBOGEB/ABACUS/actions/runs/39065792654) | **9/9 PASS** | 9 ZIPs byte-verified; 9 JUnit/JSON pairs; 225/225 focused cases |

Exact W4 PR head: `43f20c25a1b922ec61f037eca47abfc28fecb3a9`, attempt 1. Each downloaded provider artifact matches its GitHub SHA-256; each JSON inner JUnit SHA-256 matches its actual XML; all cells bind run/head/attempt/OS/Python and carry **25 passing tests, zero failure/error/skip**. [W4_STATE](W4_STATE.json) enumerates all nine artifact IDs and hashes.

**Boundaries:** Nine test cells are a full declared OS×Python grid, not nine statistically independent field incidents. Repeated source-changing pulses `3/3→9/9→0/9→9/9` do not establish stable process/Six Sigma capability or justify PCA/BT scores without qualified independent observations.

## B0, coverage and first-red

Historical source main `b1bfc7b7a5b6191e06a64fb6110d0e91f1ec5be4` [canonical B0 39065946455](https://github.com/GBOGEB/ABACUS/actions/runs/39065946455) terminal **FAIL**: **4,013 PASS, 1 FAIL, 2 SKIP**. The real first-red: `tests/test_dashboard_health_link_contract.py::DashboardLinks::test_unpublished_pages_are_explicitly_disclosed`. MYRRHA handover must remain honestly labeled unpublished if unavailable. [Python matrix 39065946520](https://github.com/GBOGEB/ABACUS/actions/runs/39065946520) terminal FAIL with matching source-root/propagated completeness checks. Do not inherit this first-red to a later head without native comparison; do not claim it fixed just because new source was merged.

Historical coverage anchors (not current): main **36.85%** (11 October), PR broad **36.92%**, PR changed-line **51%** (12 October). Current matched main/branch/PR-diff numerator/denominator and uplift: **UNKNOWN**, not zero. Verified causal BD root closures: **UNKNOWN**.

## Policy / owner gates / next action

[ABACUS #1860](https://github.com/GBOGEB/ABACUS/issues/1860) OPEN **1/12**; [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977) OPEN **0/7**; [ABACUS #1929](https://github.com/GBOGEB/ABACUS/issues/1929) owns root/BD truth. At W4 readback active main ruleset `24494381` enforced 0 approvals, no last-push approval, no resolved threads, no mandatory status check rule. That P0 defect requires eligible repository administrator change **and a negative unapproved/RED merge canary**; no source PR can substitute. GitHub `merged=true` is not governed admission when that review gate is ineffective.

**SIPOC:** Supplier ABACUS runtime and authorized admin; Input exact source + config + native job/artifacts; Process refresh → verify bytes → diagnose first-red → compare → enforce independent gates; Output JUnit/JSON + reasoned HOLD; Customer ABACUS reviewer/CODEX read-only MissionControl/QPS domain authority.

**Bounded next G3P:** P1 fresh current-main B0 and matrix; P2 disjoint source-owner first-red repair or documented global HOLD; P3 comparable statement/branch/diff measurement plus effective admin-review control, and a new addendum. Stage-only worker and CODEX/Mycelium reference links are **not** authorized remote Crew launches. Preserve `MERGE_ADMISSION=HOLD`, no security waiver or authority transfer.
