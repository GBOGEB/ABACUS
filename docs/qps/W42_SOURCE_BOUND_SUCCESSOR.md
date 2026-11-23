# W42 source-bound successor qualification

The bridge's native XLSX reader changed the eligible statement population.
The original W42 proof remains historical evidence: 214 statements and
62 branches on its original source. Reusing those counts on the changed bridge
correctly fails. Updating those integers alone would leave two import-fallback
statements untested and would not establish a new proof.

## Scope and ownership

The existing W42 workflow remains the one canonical producer. It now invokes
`scripts/qps_bridge_source_proof.py` against a reviewed, versioned contract in
`ci/contracts/qps_binary_bridge_w42_v2.json`. The consumer cannot generate or
repin that contract. A changed source, configuration, instrumentor, test identity
or coverage opportunity set requires explicit requalification and review.

The target remains `tools/qps_binary_bridge.py`. Its native XLSX dependency is
source-bound, but the dependency's own coverage is outside this experiment.
Native workbook preservation, recalculation, Office behavior, source authority
and repository admission retain separate gates.

The bound native-feature reader includes worksheet and table AutoFilter trees,
table sort state and explicit formula metadata. This successor replays its
unchanged bridge opportunity set against that final reader; helper changes
cannot silently reuse an earlier source-bound receipt.

## Preserved and added evidence

| Epoch | Distinct tests | Covered opportunities | Eligible opportunities |
| --- | ---: | ---: | ---: |
| N | 27 | 234 | 281 |
| N+2 | 81 | 274 | 281 |
| N+3 | 85 | 279 | 281 |
| N+4 | 88 | 281 | 281 |

These values are observed on the new source population: 219 statements and
62 branches. The first three case populations and the four original W42 oracles
are preserved. Three additional controls exercise the actual standalone native
reader, absence of both import routes, and malformed input through the fallback.
The positive control compares real parsed features and unchanged input bytes;
the negative controls cannot emit structured success.

The consumer checks exact source/config/test digests, coverage version, every
eligible statement and branch identity, all test identities, cumulative test
sets, monotone coverage sets, unchanged exclusions, complete final coverage,
and internally consistent JUnit and coverage counters. It rejects both absent
and duplicated evidence. Its validation uses explicit exceptions so it remains
active under `python -O`.

Every report is captured once; its parsed content and receipt hash use the same
bytes. A path replacement between validation and receipt construction cannot
attribute an accepted result to different bytes. Optional aggregate JUnit root
counters must agree with the case population and clean child suites.

## Historical lineage

The immutable historical source is retained at commit
`ecc601294ffdc5e1ba167071581921bf09939d00`, bridge SHA-256
`daf90d0df06e18caaa4262bf99543cd986def26245c88f3e461a18111c6ebafd`.
The historical inline proof can be retrieved at commit
`7650834b19347147c0fe11821accb1f9b6258439` in the same workflow path.
Its schema is `codepurple.w42.matched-fixpop/1.0`; the new receipt schema is
`qps.bridge.source-proof/2`. The historical 214/62 and 231/271/276 values are
retained in the new contract as historical values, not rewritten measurements.

The lane adapter's upstream pin is also advanced to the reviewed bridge bytes
at `7fc8f8295333b928b533806be4ee405ba1306039`. The diff from its previous pin
adds native XLSX feature extraction and a standalone import fallback, and
advances parser version 1.1 to 1.2.1. All 13 adapter controls, including the
pre-import tamper rejection, must pass against the new pin. Hash enforcement
and source authority separation remain unchanged.

## Execution and acceptance

Local source-snapshot receipts have no head, run or job ID and cannot represent
GitHub execution. The native workflow checks its Git checkout before each epoch,
binds the provider's event head, run and attempt, and uploads its evidence even
when red. A provider readback must still attach the actual job ID and conclusion.
The Python/OS matrix remains Ubuntu 24.04 and Windows 2022, Python 3.11 and 3.13.
The source contract does not weaken or replace any branch protection, review,
security, full-suite or compatibility requirement. Every receipt retains
`merge_admission=HOLD` and no engineering or document-control credit.
