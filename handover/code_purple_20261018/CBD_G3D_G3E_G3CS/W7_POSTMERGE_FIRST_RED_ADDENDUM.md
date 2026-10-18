# CBD! W7 — post-merge first-red addendum (18 October 2026)

**Additive evidence:** Does not overwrite the frozen G3D/G3E/G3C-S `STATE.json`, the earlier 89/123-test receipts, or the historical #1980 runs.

## Exact merged main and first-red propagation

ABACUS `main=1122dca15557e4d2b0ec16300fcbf409db678e86` after ordinary merges [#2236](https://github.com/GBOGEB/ABACUS/pull/2236) and [#2237](https://github.com/GBOGEB/ABACUS/pull/2237). Active ruleset 24494381 still has **0 required approving reviews / no required check rule**; no governed admission credit.

| Native surface | Run / failed job | Same root |
|---|---|---|
| Current-main canonical B0 | [39143732112](https://github.com/GBOGEB/ABACUS/actions/runs/39143732112), job `117723231077` | Pytest collection: `tests/test_g3cs_source_mutations.py` |
| Current-main Python compatibility | [39143732055](https://github.com/GBOGEB/ABACUS/actions/runs/39143732055), Python 3.10 `117723910018`, 3.11 `117723909985`, 3.12 `117723909919` | Same `ModuleNotFoundError` |
| Current-main Session Tuple | [39143732054](https://github.com/GBOGEB/ABACUS/actions/runs/39143732054), job `117723230506` | Same collection root |

Native log first-red: `import test_g3cs_assurance_matrix as assurance` fails because pytest collects the test as `tests.test_g3cs_source_mutations` and that other test module is not importable as top-level `test_g3cs_assurance_matrix`. The repository has a real `tests/__init__.py`. These are **manifestations of ONE shared test-import root**, not multiple independent failures or code-design regressions.

## Bounded owner correction (no admission)

GitHub branch `fix/g3cs-w7-package-qualified-test-import-20261018`, commit [`7ed14d5dd6937aaa3fd3c58cbf3bc5f22e334416`](https://github.com/GBOGEB/ABACUS/commit/7ed14d5dd6937aaa3fd3c58cbf3bc5f22e334416) based on pinned main `1122dca...`: change **one import line** in `tests/test_g3cs_source_mutations.py` to `from tests import test_g3cs_assurance_matrix as assurance`. Source blob old `f765d55bc1c1acea8ab6b42655213eefe29c32c9`, new `5065462decdfc93d812d4b17a9074189cfbbaf33`. Branch readback MATCH. **No PR opened, no merge or waiver, native result pending.**

Required DoV: native B0/CI/matrix at this exact new head, plus tests verifying all 16 targeted mutants killed and no false greens; native artifact ZIP digests and changed-line/branch denominator, independent security/Bandit/Safety/A10 and branch governance. No root closure until comparable retest and owner acceptance.

## Updated CODEX source state

CODEX `main=4d86406ccd6751fbe43ecd199ce98a5e608e6ecf` after #1095/#1096 ordinary merges. Prior #1095 exact-head native MYCELIUM [39142904154](https://github.com/GBOGEB/CODEX/actions/runs/39142904154) success, ZIP byte-verified, **521 assets/491 unregistered**. CODEX current-main push CI is in progress; no full-main consumer acceptance. Native consumer `producer_artifact_consumed=false` remains historical. Admin branch protection and eligible human reviewer remain absent.

`merge_admission=HOLD` · `formal_packages_closed=0/14` · `authority_transfer=false` · `causal_root_accepted_closure=0`.
