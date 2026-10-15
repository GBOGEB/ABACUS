# DOW W169 and W74 side-load adapter (MIP P2)

This bounded, read-only producer descriptor can be consumed by the CODEX/KEB
candidate contract and the existing MissionControl Atlas. QPLANT Kubernetes
runtime ownership remains with ABACUS/DOW.

## Existing Kubernetes assets

Canonical static manifests are under qplant/deployment/k8s. The W74 contract
validator and workflow verify manifest/security invariants. W169 owns real
API creation and workload measurements using a temporary kind cluster.

Without an exact-head run, job, attempt and independently verified archive
bytes, W169 workflow source is not proof of cluster success. Do not embed
kubeconfig, access tokens, raw logs or sensitive evidence in this adapter.

## Uniform side-load references

- Registry: triage/SIDELOAD_K8S_SURFACE_CURRENT_v1.json
- Candidate: federation/sideload/DOW_K8S_STATIC_CANDIDATE_v1.json
- KEB transport: CODEX PR #1049; source-bound candidate until revalidated
- Native runtime: existing W74 and W169 workflows, not a new workflow

Docker/Compose products remain separately owned and do not prove Kubernetes
readiness. This PR creates no new cluster, deployment or QPS authority.
The upstream transport's exact SHA must be reviewed before rebinding.

## Verification

Run:

```sh
python -m pytest tests/test_dow_sideload_k8s_surface.py -q
```

The existing QPLANT static contract and W169 runtime work remain independent.
No native acceptance, engineering credit, edge promotion or release is claimed.
