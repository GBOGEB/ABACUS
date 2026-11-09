# QPS Slide-Reviewer ⇄ gg_MATH Parity Contract — v1

**Status:** DRAFT reference / parity record. Non-authoritative.
**Scope:** Binds the QPS slide-reviewer's in-app BT/PCA consumer to the gg_MATH
canonical kernels. No engineering, compliance, acceptance or release authority is
transferred by this document (see `mission/QPS/QPS_TRIAGE_PCA_MATH_APPLICATION.md`).
**Verifier:** `mission/QPS/parity/verify_qps_parity.py` → `qps_parity_vector.json`.

---

## 1. Single Source of Truth (corrected)

`gg_MATH/kernels/` is the mathematical SSOT for the QPS federation's PCA and
Bradley–Terry work. Concretely:

- **PCA** — `kernels/pca_reference.py` (exact cyclic-by-row Jacobi eigendecomposition
  via `kernels/matrix_core.py`), plus `parallel_analysis` (PA95 retention diagnostic)
  and `bootstrap_loading_stability` (matched-column congruence CIs).
- **Bradley–Terry** — `kernels/bradley_terry.py` (`rank_pairs`, MM / Hunter 2004) with
  **fail-closed** guards: `DEFER_NO_USABLE_COMPARISONS`,
  `DEFER_DISCONNECTED_COMPARISON_GRAPH`, `DEFER_NO_FINITE_MLE`
  (directed-win-graph strong-connectivity / Ford condition), `DEFER_MM_NOT_CONVERGED`.
- **Statistics** — `kernels/stats_core.py` (covariance/correlation, Fisher-z, Wilson,
  ANOVA) and the uncertainty kernels.

This **supersedes** the earlier cross-repo triage note (CODEX PR #1188) that framed
the CODEX `pca_engine` as the authority. `pca_engine` re-implements BT/PCA that
`gg_MATH` already provides; it should be **justified and deduplicated against
`gg_MATH`**, not promoted above it. Recommended resolution: have `pca_engine` either
import/vendor the `gg_MATH` kernels or publish a parity record against them (same
shape as this document), so the federation maintains **one** canonical BT/PCA, not
three divergent ones.

## 2. The three implementations

| Implementation | PCA method | BT method | Degenerate inputs |
|---|---|---|---|
| **gg_MATH** (canonical) | Jacobi eigendecomp of the correlation matrix; all `p` components; PA95 + bootstrap stability | MM, unregularised | **Fails closed** (`DEFER_*`) |
| **CODEX `pca_engine`** | duplicate of the above (to be deduped) | MM + bootstrap CIs; `PAIRWISE_DECISION_ANALYTICS_ONLY` guard | guarded |
| **slide-reviewer** `lib/stats.ts` (consumer) | power iteration + deflation on the correlation matrix; top-3 components | MM **with `prior = 0.1`** (always finite), ties = ½ win, geometric-mean-1 normalisation | **Masks** degeneracy (prior regularises) |

BT⟂PCA is preserved everywhere: Bradley–Terry strengths are **not** fed into PCA and
PCA scores are **not** fed into BT.

## 3. Verified parity (this repo, reproducible)

`verify_qps_parity.py` runs the canonical kernels and a faithful port of the
slide-reviewer algorithms on one seeded synthetic slide×feature matrix (seed
`20260925`, 8 slides, 4 feature blocks: evidence / reliability / delivery / visual).

### 3.1 PCA — machine-precision parity

With the slide-reviewer's standardisation (`scale=True` on the canonical side), the
power-iteration PCA reproduces the exact Jacobi eigendecomposition:

```
max |Δ eigenvalue (top-3)|          = 8.88e-16
max |Δ explained-variance (top-3)|  = 1.11e-16
canonical explained variance        = [0.674, 0.230, 0.090]
PA95 retained candidate             = [PC1=true, PC2=false, PC3=false]
```

PC1 is the only component that clears the PA95 null threshold — consistent with the
"PC1 retained, PC2 provisional, PC3 monitor-only" doctrine in
`QPS_TRIAGE_PCA_MATH_APPLICATION.md`. The slide-reviewer may keep power iteration for
speed, but **retention/promotion decisions must use the canonical PA95 path**, not a
raw explained-variance cutoff.

### 3.2 Bradley–Terry — convergent parity and the one real divergence

- **Convergent case** (4× round-robin, 25% upsets → strongly connected win-graph):
  canonical status `PASS_TESTABLE_ENGINE`, and the canonical ranking is **identical**
  to the slide-reviewer ranking: `[7, 6, 8, 3, 1, 4, 2, 5]`.
- **Fail-closed case** (single round-robin, 15% upsets → win-graph not strongly
  connected): canonical returns `DEFER_NO_FINITE_MLE`; the slide-reviewer's
  `prior = 0.1` **silently returns a ranking anyway**.

The divergence is not numerical — it is a semantics gap. The slide-reviewer can
produce a full ranking in exactly the data regime where the canonical authority
refuses one.

## 4. Convergence plan for the slide-reviewer

Keep the app's fast in-browser math for interactive display, but make it agree with
the SSOT on anything that leaves the app:

1. **Expose the canonical status.** Before publishing a BT ranking (dashboard /
   export), run the same comparisons through the `gg_MATH` fail-closed contract and
   surface `DEFER_*` instead of presenting a regularised ranking as if converged.
   Treat the `prior = 0.1` result as a provisional display value only.
2. **Gate PCA retention on PA95**, not on explained-variance share.
3. **Cross the wormhole.** Export the slide×feature matrix and comparison set as a
   synthetic, non-authoritative envelope through `mission/federation/qps_wormhole.py`
   (methods `M03_COVARIANCE`, `M04_PCA`, `M08_BRADLEY_TERRY`; `M05_CONFIDENCE_INTERVALS`
   for CIs), so authoritative scoring is computed once, by `gg_MATH`, and received by
   the app rather than recomputed divergently.
4. **Parity CI.** `verify_qps_parity.py` is the regression guard: any kernel change
   that breaks machine-precision PCA parity or the convergent-case BT ordering fails.

## 5. Authority boundary

Consistent with the wormhole and triage docs: `gg_MATH` may supply formulas,
reference calculations and synthetic test vectors. It may **not** promote engineering
truth, compliance, acceptance, or a Bradley–Terry ranking without observed pairwise
comparisons. Every artifact here carries `authority_transfer = false`.
