# ABACUS / DOW gg_MATH QPS P4 wormhole observation

**Contract:** `gg-math-qps-wormhole/v1` to
`abacus.dow.qps_math_wormhole_observation/v1`.

The gg_MATH P1 / 3PR provider supplies synthetic mathematical reference.
CODEX / KEB retains semantic identity and governance.
ABACUS / DOW challenges provenance without importing gg_MATH or private QPS.
The QPS child owns project population and thresholds, P2/MIP application,
P3/3PC engineering decisions, and P4 re-entry.

This observer is deliberately diagnostic. Even `VALID_PROPOSAL_ONLY` means
only that the supplied proposal met schema and hash assertions.
Independent native GitHub receipts are required for execution proof.
The observer cannot assert CODEX/KEB or QPS acceptance, nor safety,
negotiation, or release credit.

## Metrics and integration

- `received`, `contract_valid`, `invalid`, `unique_roots`,
  `runtime_authenticated` and `qps_dispositions` are typed counters.
- Invalid roots have deterministic SHA-plus-cause fingerprints.
  Each carries a conservative owner and `DEFER` disposition.
  Join to EVERRED and BD–LDAB by provider SHA and fingerprint.
- Public outputs never contain QPS private source vectors.
- Unrecognized fields and apparent QPS child decisions are rejected.
- No dispatch token, merge permissions, runner control, or port is created.

## Local TestPilot

Run:

```bash
python -m unittest discover -s tests \
  -p test_qps_math_wormhole_dow.py -v
```

## Existing exact consumer lineage

Existing consumers remain in:

- `runtime/federation/gg_math_temporal_pca_dow_consumer.py`
- `runtime/federation/w259_method_cards_independent_dow.py`

This observer does not relabel accepted *knowledge-only* W259 or
temporal PCA bindings as newly executed native proof.

## Promotion sequence (not yet complete)

Provider source SHA and artifact → CODEX/KEB semantic witness →
ABACUS/DOW independently verified replay → QPS child source and
threshold control → human/governed decision → source-bound telemetry.
The bounded DAG remains acyclic even if the global QPS loop returns.
