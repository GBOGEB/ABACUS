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
