# Federation integration + bridge acceptance — 26 October 2026

Status: implementation proposal, **not** exact-head admission or deployment.

## Authority and baseline correction

The 25 October integration report called CODEX `pca_engine` canonical. The subsequently merged [ABACUS #2474](https://github.com/GBOGEB/ABACUS/pull/2474) and CODEX `pca_engine/MATH_SSOT_BINDING.md` supersede that wording: **gg_MATH/kernels** owns mathematical authority; CODEX remains the semantic/governance hub; ABACUS owns runtime and the slide-reviewer; cryoplant owns its private engineering evidence. Historical smoke numbers must not be represented as current exact-head PASS.

## Six bridge contracts to qualify

| Edge | Required proof | Current disposition |
| --- | --- | --- |
| Tuple → handover | valid tuple schema, matching input SHA and generated handover manifest | UNKNOWN until live receipt |
| Handover → CI | PR-triggered tuple validator, exact tested commit and failed negative fixture | GAP: legacy `.github/workflows/ci.yml` is dispatch-only |
| Temporal metadata → Phase 6 knowledge | nonempty typed refs with matched source IDs and version | UNKNOWN |
| Handover → agent execution | idempotent task identity and result receipt; no state mutation on invalid handover | UNKNOWN |
| CI → HTML/dashboard | matched run ID, source SHA, artifact digest and deployment readback | UNKNOWN |
| Tuple tests → smoke CI | assertions run on exact PR head with a negative case | REQUIRED |

Bridge catalog: [BRIDGES_AND_CONNECTIONS.md](BRIDGES_AND_CONNECTIONS.md). The historical badge `6 connected` is **not a live CI measurement**.

## Governing rules

- A declared bridge is not an executed bridge. Keep `declared`, `tested`, `deployed`, `owner_accepted` distinct.
- The slide-reviewer BT preflight in `qps_slide_reviewer/lib/bt_admission.ts` checks the provider's necessary graph condition; it does not certify convergence or produce authoritative rankings. All DEFER cases must block promotion.
- Treat CODEX `pca_engine` as a consumer. Preserve provider SHA binding and explicit regularization/normalization differences.
- Do not auto-prune snapshots or remote branches. Review the existing `docs/PRUNE_MANIFEST.md` before any separate deletion PR.
- Never treat CI green as engineering-owner approval or independent review.

## Proposed tests

Run `python -m pytest DMAIC_V3/tests/test_tuple_metadata_validation.py -q` and `python scripts/validate_tuple_metadata.py --input <fixture>` with both valid/invalid fixtures. Test BT preflight with cycles, total-order separation, disconnected components, ties-only and invalid winners. For TS tests run `node --experimental-strip-types --test qps_slide_reviewer/tests/bt_admission.test.ts` on a Node version supporting type stripping; otherwise use the repository's compatible TypeScript runner. Confirm actual CI result rather than assuming a local script command executes in Actions.
