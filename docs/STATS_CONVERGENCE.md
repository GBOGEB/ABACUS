# Stats convergence — ABACUS → CODEX `pca_engine` (P1)

> Federation action **P1** from [`docs/INTEGRATION_REPORT.md`](INTEGRATION_REPORT.md) §4 item 1.

## Current state

`qps_slide_reviewer/lib/stats.ts` hand-rolls Bradley-Terry pairwise ranking (MM
algorithm) and PCA (power iteration). The federation's **canonical, tested**
implementation is [`GBOGEB/CODEX:pca_engine`](https://github.com/GBOGEB/CODEX/blob/main/pca_engine/CANONICAL_API.md)
(20/20 tests, including a cross-repo parity harness).

## Parity (verified)

`CODEX/pca_engine/tests/test_parity_spoke_stats.py` embeds a faithful Python port
of the TS `bradleyTerry` and asserts:

| Property | Result |
|----------|--------|
| Ranking order | **identical** to canonical |
| Win-probabilities (ABACUS prior removed) | **match canonical to 1e-6** — same MM update |
| Default `prior = 0.1` | shrinks win-probabilities toward 0.5 (documented, intentional) |
| Normalisation basis | ABACUS geometric mean = 1 · canonical arithmetic mean = 1 (both pinned) |

**Verdict:** same algorithm; the only numerical divergence is the regularisation
prior and the normalisation basis — both invariant for ranking and win-probabilities.

## Convergence target (not done in this pass)

The TS maths are **not** rewritten here to avoid destabilising the standalone
build. The intended end state is one of:

1. **Generated artifact** — build a small JSON/WASM binding from `pca_engine` and
   call it from the slide-reviewer; or
2. **Thin wrapper** — expose a `prior`/normalisation option on `pca_engine` and have
   ABACUS call it server-side, keeping the pure-TS path only as an offline fallback.

Until then, the convergence notice at the top of `stats.ts` and the parity test in
CODEX keep the two implementations honest. **Before changing the maths in
`stats.ts`, keep `test_parity_spoke_stats.py` green.**
