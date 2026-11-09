# Federation bridge admission — 26 October 2026

Status: **HOLD** for any unproven execution, deployment or owner gate.

## Math authority

The 25 October integration report described CODEX `pca_engine` as the
canonical mathematical runtime. ABACUS PR #2474 superseded that assignment.
[gg_MATH](https://github.com/GBOGEB/gg_MATH) owns the math kernels.
CODEX owns semantic provenance and governance. ABACUS owns analytical
execution. The private cryoplant repository owns QPS engineering evidence.

## Six bridge edges and evidence obligations

| Edge | Required proof | Initial status |
| --- | --- | --- |
| Tuple to handover | Source SHA and validated manifest | UNKNOWN |
| Handover to CI | Head-matched validator and RED fixture | UNKNOWN |
| Temporal to Phase 6 | Typed references and source identity | UNKNOWN |
| Handover to agent | Replay-safe task and result receipt | UNKNOWN |
| CI to dashboard | Run, source SHA, artifact digest | UNKNOWN |
| Tuple test to smoke | Exact-head positive and RED tests | UNKNOWN |

The historical bridge badge is not a live measurement.
See [the bridge catalog](BRIDGES_AND_CONNECTIONS.md) for source paths.

## Governance rules

- Declaration, execution, deployment and owner acceptance are separate states.
- The TS Bradley–Terry preflight only tests necessary graph conditions.
  A positive preflight does not certify a provider fit or a finite MLE.
- CODEX `pca_engine` is a consumer of gg_MATH, not math authority.
- A `DEFER` result must block ranking or release promotion.
- An unavailable receipt is UNKNOWN, never PASS.
- Legacy `.github/workflows/ci.yml` is dispatch-only.
  The dedicated federation bridge workflow adds a PR-triggered check.
- No auto-pruning, review bypass or waiver is allowed.

## Reproduction

```bash
python -m pytest -q DMAIC_V3/tests/test_tuple_metadata_validation.py
python -m pytest -q DMAIC_V3/tests/test_federation_bridge_contracts.py
```

For TS preflight, execute the TypeScript tests with the pinned Node runner.
Do not infer runtime enforcement or deployment from test presence alone.
