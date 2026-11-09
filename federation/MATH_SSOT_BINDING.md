# Federation Math SSOT Binding — gg_MATH

**Status:** Reference / governance note. Additive. No authority transfer.
**Plane:** `math` (see `federation/manifest.yaml` → `planes.math`).
**Registered:** branch `feat/register-gg_math-ssot-and-qps-parity`.

---

## 1. Single Source of Truth (corrected)

`GBOGEB/gg_MATH` is the **mathematical single source of truth** for Principal
Component Analysis (PCA) and Bradley-Terry (BT) ranking across the DELTA_1
federation. Downstream repositories **consume** its kernels through parity
contracts; they do **not** re-derive or fork the math.

This note records a correction: an earlier proposal promoted the CODEX
`pca_engine` as the authority. On inspection, CODEX `pca_engine` **duplicates**
capability that already exists — and is more rigorously implemented — in
`gg_MATH/kernels/`. The federation therefore binds to gg_MATH and treats both the
CODEX engine and the QPS slide-reviewer as **consumers** that must stay in parity.

### Canonical kernels (`gg_MATH/kernels/`)

- **PCA** — `pca_reference.py`: exact cyclic-by-row Jacobi eigendecomposition
  (`matrix_core.symmetric_eigen_jacobi`), standardised correlation PCA, with
  `parallel_analysis` (PA95 retention) and `bootstrap_loading_stability`
  (matched-column congruence CIs).
- **Bradley-Terry** — `bradley_terry.py`: `rank_pairs` (MM / Hunter 2004) with
  **fail-closed** guards — `DEFER_NO_USABLE_COMPARISONS`,
  `DEFER_DISCONNECTED_COMPARISON_GRAPH`, `DEFER_NO_FINITE_MLE`,
  `DEFER_MM_NOT_CONVERGED`.
- Every kernel carries `authority_transfer = False`.

## 2. Consumers bound by parity

| Consumer | Location | Binding artifact |
|----------|----------|------------------|
| QPS slide-reviewer | `qps_slide_reviewer/lib/stats.ts` | `qps_slide_reviewer/parity/QPS_SLIDE_REVIEWER_PARITY_CONTRACT_v1.md` |
| CODEX `pca_engine` | `GBOGEB/CODEX` | to be bound via the same parity-contract pattern (dedupe, do not promote) |

## 3. Verified parity evidence (QPS slide-reviewer)

Reproduced with a faithful Python port of the app's BT+PCA
(`qps_slide_reviewer/parity/slide_reviewer_port.py`) run against the gg_MATH
kernels. Seed `20260925`, 8 slides x 4 features
(evidence / reliability / delivery / visual). Verifier:
`qps_slide_reviewer/parity/verify_qps_parity.py` →
`qps_slide_reviewer/parity/qps_parity_vector.json`.

- **PCA — machine-precision parity.** `max|Delta eigenvalue (top-3)| = 8.88e-16`,
  `max|Delta explained-variance (top-3)| = 1.11e-16`. Canonical explained
  variance `[0.674, 0.230, 0.090]`.
- **PA95 retention** keeps PC1 only → `[true, false, false, false]`, matching the
  gg_MATH doctrine "PC1 retained, PC2 provisional, PC3 monitor-only".
- **BT convergent case** (4x round-robin, 25% upsets): canonical
  `PASS_TESTABLE_ENGINE`; ranking identical to the app → `[7,6,8,3,1,4,2,5]`.
- **BT fail-closed case** (sparse, single round-robin): gg_MATH returns
  `DEFER_NO_FINITE_MLE` (Ford condition — directed win-graph not strongly
  connected). The slide-reviewer's `prior = 0.1` **masks** this and emits a
  ranking anyway. This is the **one real divergence**, and it is *semantic*
  (fail-open vs fail-closed), not numerical. The convergence target is to make
  the consumer honour the DEFER verdict.

## 4. Reproduction

```
# from a checkout that has gg_MATH/kernels/ on the Python path
python3 qps_slide_reviewer/parity/verify_qps_parity.py
# exit 0 + "PARITY OK" prints the verdict; regenerates qps_parity_vector.json
```

The verifier is self-contained except for `gg_MATH/kernels/` (the canonical
source it checks against). See the parity contract for the full field-by-field
specification.
