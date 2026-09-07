# W60 3PR 5-Horizon DoV/PCA/BT/KPI Roll-up

Repository: `GBOGEB/ABACUS`
Plane: DOW runtime QA
Date: 2026-09-07

## Session vs Global DoV

Session/chat DoV is limited to this branch: DOW runtime gates, render QA requirements, and payload-SHA receipt requirements are recorded. Global DoV remains pending until a real QPS payload is accepted, KEB validates semantics, DOW executes runtime QA, and the child re-entry decision is recorded.

## Five Horizons

| Horizon | Scope | Evidence needed | Current state |
|---|---|---|---|
| H0 session/chat | This branch | Runtime control packet | Defined |
| H1 next pulse | P1-P3 | Real DOW receipt for identical QPS payload SHA | Pending |
| H5 five-wave | P4-P6 | Binary tuple, Playwright/render QA, zero-delta repeat | Blocked by P3/P4 |
| H50 portfolio | Runtime/QA convergence | Stable workers and automated tuple checks | Deferred |
| H100 sustained | Reproducible runtime autonomy | Clean-checkout zero-delta execution | Deferred |

## P1-P7 Controls

DOW validates that P1 input SHA is unchanged, emits the P2 runtime receipt, returns runtime recommendations for P3 without overriding QPS/KEB authority, owns P4/P5 runtime and render evidence, executes P6 zero-delta repeat, and defers P7 cleanup until the baseline is stable.

## PCA and Reverse-Load Priority

The low-scoring DOW dimensions are zero-delta reproducibility, render QA coverage, cross-binary tuple stability, worker receipt integrity, and historical runtime duplication. Reverse-load priority emphasizes the controls that block global DoV and sustained execution.

Current highest reverse-load blocker: `zero_delta_reproducibility`.

## BT Priority

1. P5 cross-binary render QA gap
2. P6 zero-delta reproducibility gap
3. P2 real DOW runtime receipt contract
4. P4 binary tuple regeneration
5. P3 child re-entry runtime recommendation
6. P7 historical cleanup after baseline

## KPI Position

Session/chat DoV: `0.62`
Global DoV: `0.46`

These are planning/control estimates only. No generated binary, render QA, or zero-delta claim is promoted without recorded artifact hashes and receipts.
