# W64 Generic 3P rollout — controlled session handover

Date: 2026-09-08

## Global goal / intent
Build a reusable TRIAGE control method that selects the right 3P variant for the current item state ("horses for courses"), learns from execution evidence, scales read-only discovery safely, preserves stable root IDs, and keeps mutation / engineering authority behind single-writer re-entry gates.

## Current global DoV
NOT PROMOTED.

Reason: the generic method, adaptive selector, sampling cadence, parallel pilot, stability ledger, and downstream adapters exist, but the first execution series has not yet produced enough evidence to establish stable speed improvement or close W64 blockers. Statistical PCA / covariance / empirical BT remain gated by sample size and stability rules. No release or engineering credit is granted by these control-plane changes.

## Merged baseline
- ABACUS #979 — generic 3P discriminator and preservation contract.
- ABACUS #980 — end-to-end DMAIC pipeline, adaptive selector, sampling/PCA cadence.
- ABACUS #982 — parallel 3P agent pilot, agent responsibility/DoD, stability ledger, per-run speed/stability roll-up.
- CODEX #485 — semantic/orchestration adapter.
- cryoplant-project #666 — engineering re-entry adapter.

## Live rollout PRs at handover
- CODEX #486 — adaptive selector consumer / orchestration follow-up.
- cryoplant-project #667 — adaptive selector consumer / engineering-safe routing follow-up.

## Agent responsibility boundary
- Coordinator freezes scope/root IDs, assigns facets, validates completeness, and assembles receipts.
- Discovery workers are read-only and may execute 3PE / 3PL.
- Challenge workers are read-only and may execute 3PC / 3PV.
- Statistical worker computes descriptive / candidate PCA / BT / covariance only when eligible; it cannot create authority.
- P3 writer count remains exactly one for mutation-bearing re-entry.
- cryoplant-project remains engineering-truth and acceptance authority; CODEX owns semantic orchestration; ABACUS owns execution/evidence/receipts.

## Sampling / learning cadence
- Every valid run: raw timing, normalized timing, AHT, evidence/edge yield, rework, first-pass yield, queue/blocker movement, DoV-gap movement, rule-based semantic/PCA dimensions.
- Every 5 valid runs: coverage matrix, semantic-weight drift, variant-transition matrix, runner-allocation comparison, exploratory correlation/PCA candidate refresh.
- Every 10 valid runs: robust distribution/control-band refresh.
- Empirical covariance: complete n >= max(30, 10p).
- Empirical PCA for decision weighting: complete n >= max(50, 10p), with missingness/scaling controls and two consecutive similar dominant-loading refreshes.
- Empirical BT: terminal n >= 30 and at least 5 positive/useful outcomes.

## Speed / stability contract
Every comparable run records speed versus fixed baseline, previous valid run, and rolling median of up to five prior comparable runs. Speed is normalized per root item and worker-hour.

Stability classes:
- INSUFFICIENT_EVIDENCE: <3 comparable runs.
- DIRECTIONAL_IMPROVEMENT: current normalized speed better than baseline without quality regression.
- PROVISIONALLY_STABLE: >=3/5 recent comparable runs positive, rolling median >=1.05x, quality guards pass.
- STABLE_IMPROVEMENT: >=5 comparable runs, >=4/5 positive, rolling median >=1.10x, no P95/FPY/rework/info-loss/DoV regression.
- REGRESSION: speed, quality, preservation, or DoV control limit breached.

## Session DoD
Completed:
- adaptive selector built and merged into ABACUS baseline;
- progression / semantic-weight / AHT / yield / rework / DoV signals formalized;
- small-sample versus empirical-statistics boundary formalized;
- parallel 3PE+3PL and 3PC+3PV pilot implemented and merged;
- explicit coordinator/worker/statistical/P3-writer scope and DoD implemented;
- stability ledger and executable per-run speed/stability roll-up implemented;
- CODEX and cryoplant adaptive-consumer PRs opened;
- this handover committed to GitHub so restart does not depend on chat context.

Not completed / deliberately open:
- no stable speedup claim yet;
- no empirical PCA/covariance/BT activation yet;
- no W64 release DoV or engineering DoV promotion;
- no duplicate/authority asset deletion or mutation from this control-plane work;
- downstream #486/#667 require final status/merge verification.

## Next mechanical actions
1. Recheck CODEX #486 and cryoplant #667 exact-head CI and merge state; patch only confirmed red failures.
2. Execute first real comparable W64 pilot series; establish R01 fixed baseline.
3. Grow stratified evidence depth 5 -> 10 -> 20 -> 30 -> 50 while preserving breadth across variant/state/type/difficulty.
4. After every 5 valid runs refresh coverage/semantic/PCA candidate views; do not promote empirical statistical weights before gates are met.
5. Feed only proven routing/search/runner improvements back into selector defaults; preserve single-writer P3 and local engineering authority.
