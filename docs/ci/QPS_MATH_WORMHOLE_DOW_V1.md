# ABACUS / DOW gg_MATH QPS P4 wormhole observation

**Contract:** `gg-math-qps-wormhole/v1` → `abacus.dow.qps_math_wormhole_observation/v1`

The gg_MATH P1 / 3PR provider supplies synthetic mathematical reference only.
CODEX / KEB retains semantic identity and governance.
ABACUS / DOW challenges source and provenance without importing gg_MATH or the private QPS child.
The QPS child (`GBOGEB/cryoplant-project`) owns P2/MIP application semantics, P3/3PC engineering decisions and the P4 re-entry decision.

This observer is deliberately diagnostic. Even `VALID_PROPOSAL_ONLY` means only that untrusted public proposal bytes met the declared schema/hash assertions against supplied expected identities. An independently authenticated native GitHub run is still required. The observer cannot assert CODEX/KEB acceptance, QPS acceptance, or safety/negotiation/release credit.

## Metrics / integration
- `received`, `contract_valid`, `invalid`, `unique_roots`, `runtime_authenticated` and `qps_dispositions` are explicit integer counters.
- Invalid roots carry stable SHA+cause fingerprints, conservative owner and `DEFER` disposition; link these to EVERRED ledger and the BD–LDAB census by `provider_source_sha` + `fingerprint`.
- No public upload of QPS private vectors; unrecognized fields and apparent QPS child decisions are rejected.
- No merge permissions, dispatch token, runner control or web port is configured.

## Local TestPilot
`python -m unittest discover -s tests -p test_qps_math_wormhole_dow.py -v`

## Existing exact consumer lineage
See `runtime/federation/gg_math_temporal_pca_dow_consumer.py` and `runtime/federation/w259_method_cards_independent_dow.py`. This additive v1 observer does not re-label previously accepted *knowledge-only* W259 or temporal-PCA bindings as executed native proof.

## Promotion sequence (not yet complete)
Provider SHA/artifact → CODEX/KEB semantic witness → ABACUS/DOW independently verified replay → QPS child source/threshold control → human/governed decision → rerun source-bound telemetry. The bounded DAG must remain acyclic even when the global QPS learning loop returns.
