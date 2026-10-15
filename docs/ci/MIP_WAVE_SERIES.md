# MIP wave-series operator contract

A wave is an exact-SHA source change with a canonical #1990 pulse and
backlog receipt. A **series** is a sequence of such waves; it does not make
synthetic or operator-supplied observations native, authenticated, stable,
capable, security-cleared or admitted.

## Canonical inputs per pulse

Provide a separate folder for every chronological wave:

```text
wave-N/
  wave-input.json
  mip_wave_pulse.json
  mip_backlog_delta.json
```

These are the canonical #1990 producer's input bytes and two outputs.
The series reader rehashes the input, checks cross-file identities,
root-status counts, fingerprints, first-reds and exact-SHA linkage.
It validates changed line/branch coverage only if the original #1990
source and output are compatible, including identical denominators.

Run from the ABACUS repository root:

```bash
python tools/mip2/mip_wave_series.py \
  --wave-dir path/to/wave-01 \
  --wave-dir path/to/wave-02 \
  --classification OPERATIONAL_UNVERIFIED \
  --output-dir artifacts/mip-wave-series
python -m unittest discover -s tests -p 'test_mip_wave_series.py' -v
```

This emits `mip_wave_series.json` and `mip_wave_series.md`. Use
`SYNTHETIC` when fixture data are supplied; **both modes withhold
independent native/admission credit**.

## Pulse KPI readback

The series report separates these measurement families:

- **Roots:** six source states; claimed closure is not verification.
- **Burndown:** new, disappeared, claimed closed and reopened root IDs.
- **Errors:** occurrence totals and first-seen/repeated fingerprint pairs.
- **First-red:** new, inherited and repaired; each requires an owner.
- **Coverage:** numerator, denominator, scope, and delta (pp).
  UNKNOWN and INCOMPARABLE never mean zero improvement.
- **CI:** source-reported pass/fail/skip; independently verify jobs.
- **Capacity:** source worker records, not authenticated Crew capacity.
- **Maturity:** M1 evidence and separately gated M2/M3 decisions.
- **PCA / BT:** not assessable without matched independent series.

Inspect one row per pulse and the JSON breakdown. Do not present
different cohort percentages as an improvement or subtract raw scanner
finding counts as matched security burndown.

## Independent native receipts required for operational promotion

This reader checks internal *consistency* but does not contact GitHub.
A separate authenticated ingestor shall verify source repository, actual
checkout SHA, producer SHA, run ID, attempt, job ID, artifact ID, ZIP
digest **and internal JSON bytes**, plus JUnit/coverage/scanner sources.
It shall separately distinguish pull head, merge head and main SHA.

Until that step exists, `native_receipt_verified=null`,
`security_matched_delta=null`, and verified closure/coverage remain
UNKNOWN (not fabricated zeros). Formal engineering and admission credit
are never issued by this statistics process.

## Scaling: disjoint workers and repositories

1. Prove the source and tests on ABACUS first; use #1990 as the
   canonical wave producer, #1989 for M1/M2/M3, and #1994 for dynamic
   denominator and LDAB provenance.
2. Add authenticated artifact intake to one consumer PR, with
   worker/path leases. Measure per-worker tests, roots and source-
   matched coverage before increasing concurrent workers.
3. Repeat with CODEX, QPS and gg_MATH only after each repository has
   its own eligible producer and configuration. This v1 reader
   deliberately **rejects** other repositories rather than invent
   a comparable cross-repository denominator.
4. MissionControl may orchestrate the disjoint queue and report
   per-repository progress, but may not merge source, approve security,
   or aggregate incompatible coverage percentages.
5. Keep formal throughput, queue wait, repair yield per worker-hour,
   recurring roots and reversible first-red pressure as separate
   source-bound operational metrics.

## Each wave's DMAIC decision

- **Define:** root owner, causal hypothesis, path lease and expected DoV.
- **Measure:** source Sha/run, root and fingerprint census, coverage scope,
  runtime/effort and first-red evidence.
- **Analyze:** compare matching cohorts; otherwise flag UNKNOWN.
- **Improve:** commit disjoint source-corrected repairs and execute the
  native testflight; do not reuse a green test across changed SUT.
- **Control:** independently assess M2 process charts, M3 capability,
  recurrence, security, governance and exact-main confirmation.

**P0:** Required status checks remain unconfigured in main's active
ruleset at the latest readback despite main being protected. No source
producer, dashboard, wave or statistical metric can authorize merging.
`merge_admission=HOLD`; `security_waiver=false`;
`authority_transfer=false`; `formal_credit_delta=0`;
`engineering_credit_delta=0`.
