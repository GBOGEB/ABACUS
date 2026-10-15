# Mission Control Wide: federation pulse contract

Status: **read-only measurement candidate**. No merge authority or waiver.

## Existing producers and scope

The tool accepts typed observations for MCL, MIP, DMAIC, REX, LDAB/LLDB,
CENSUS, 3P and PCA. It never starts a worker or authenticates a peer.
Reuse upstream contracts rather than replacing them:

- `scripts/bd_ldab_join_census.py`: BD/LDAB candidate joining
- `scripts/mip_ldab_telemetry.py`: source discovery vs runtime proof
- `architecture/w65/W65_TRI_REPO_DISCOVERY_ROLLUP.yaml`: tri-repo funnel
- `architecture/w72/W72_DOUBLE_3P_BURNDOWN_RECEIPT.json`: 3P limits
- PR #1980 `mission_control_lite/coverage_pulse.py`: scoped coverage

`mcw.federation.proof.v1` is an **adapter contract**. Existing upstream
producers do not automatically conform; approved adapters are future work.

## Run from the checkout

```bash
python tools/mcw_federation_rollup.py --input input.json \
  --artifact-root ./trusted-downloads \
  --output out/mcw-federation-rollup.json
```

An `mcw.federation.input.v1` file has `wave_id`, `nodes` and `edges`.
Each node declares unique `id`, exact `repository`, 40-char `source_sha`,
and a family name. An optional `artifact` supplies a relative `path` and
64-char `sha256` for local-byte validation. Typed proof JSON must match
repository, source SHA, family, positive run/job IDs and reconciled
required/passed/failed/skipped counts. Optional coverage carries
scope ID, config digest, file list and line/branch numerators.

## Per-pulse horizontal metrics

| Dimension | Reported | Not inferred |
| --- | --- | --- |
| Breadth | Repositories and 8 named families | Active federation |
| Depth | Byte-matched vs source-only members | Authenticated producer |
| Fan-out | Declared cross-repo graph edges | Running worker fleet |
| Coverage | Per-member line/branch ratio | Fleet-average percentage |
| Pulse gain | Scope/config/denominator-matched delta | Incomparable gain |
| DMAIC/PCA | Qualification withheld | Capability or stable process |
| REX/LDAB | Candidate classification | Causal closure or LLDB session |
| 3P | Independent observation family | Release promotion |
| Authority | HOLD; verified closures = 0 | Review, merge, waiver |

Missing and incomparable data are UNKNOWN, never zero. The ratio of
locally byte-matched members is not an authenticated GitHub success rate.

## Independent rollout gate

1. Resolve each producing repository's exact head SHA and native run/job.
2. Fetch ZIP and independently verify its GitHub-reported digest.
3. Verify internal receipt-listed bytes before accepting a metric.
4. Independently authenticate peer and workflow identity.
5. Keep security, governance, required checks and reviewer proof separate.
6. Roll up after each accepted observation; never rewrite prior waves.
7. Compare longitudinal PCA candidates only after three independent
   comparable observations, and require separate M1-M3 qualification.

The tool never claims release readiness or native federation operation.

## Source-observation adapters (MCL, LDAB, BD)

Use the existing producer JSON without interpreting an LDAB path as an
executed debugger, a BD fingerprint as a resolved causal root, or an MCL
test-passed count as a complete test denominator:

```bash
python tools/mcw_receipt_adapters.py \
  --artifact-root ./source-receipts \
  --repository GBOGEB/ABACUS \
  --source-sha <exact-40-character-commit> \
  --wave-id W1 --mcl mcl-pulse.json \
  --ldab ldab-telemetry.json --bd bd-ldab-joined.json \
  --output out/mcw-source-input.json
python tools/mcw_federation_rollup.py \
  --input out/mcw-source-input.json \
  --artifact-root ./source-receipts \
  --output out/mcw-source-rollup.json
```

All supplied producer receipts must describe the same repository and source
commit. Each source file receives a local SHA-256, but this is not authenticated
GitHub ZIP evidence. Their observations are tagged
`UNAUTHENTICATED_SOURCE_BYTES`, never mapped to authenticated native proof.

LDAB root and nested counts are **not added**; the nested index can overlap
the root inventory. Actual debugger sessions, active workers, accepted root
closures and formal admission remain UNKNOWN or HOLD. MCL coverage percentages
are source-reported without a complete native test denominator or independent
CI proof. BD findings remain candidate groups, subject to independent security
review. The roll-up counts such observation nodes separately from byte-verified
native-proof nodes.

Local qualification of this disjoint adapter slice exercised 18/18 focused
unit tests, with 244/244 statements and 46/46 branches covered under Python
3.13 / Coverage.py 7.13.3. GitHub native CI and authenticated peer receipts
remain separate decisions.
