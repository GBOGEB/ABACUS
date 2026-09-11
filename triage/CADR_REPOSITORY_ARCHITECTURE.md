<!-- markdownlint-disable MD013 -->

# cADR — ABACUS repository architecture

**ID:** TRIAGE-CADR-ABACUS-001  
**Decision:** `GBOGEB/ABACUS` is the TRIAGE DOW analytical/runtime parent.

## QPS authority source

The child authority for QPS engineering ADR/OCD content is `GBOGEB/cryoplant-project`, registered in:

`ocd-adr/20_canonical/control/QPS_GLOBAL_ADR_OCD_SSOT_v1.json`

This cADR is authoritative for ABACUS repo-local analytical/runtime architecture only. It cannot establish or promote QPS engineering facts, compliance, canonical OCD content or engineering ADR dispositions.

## Decision

ABACUS owns bounded engineering/scientific analysis, DMAIC runtime, PCA/BT, analytical findings, handover runtime and multi-agent execution. It does not own QPS engineering authority, final compliance/disposition or KEB semantic governance.

## Canonical runtime spine

```text
immutable governed child projection
  |
C1/C2 Define
  |
C3/C4 Measure
  |
C5/C6 Analyze + Improve
  |
C7/C8 Control + Knowledge
  |
C9/C10 KEB/runtime operations
  |
C11/C12 TODO + temporal monitoring
  |
DOW typed findings receipt
  |
KEB normalization
  |
child re-entry disposition
```

The canonical orchestrator is `DMAIC_V3/core/twelve_cluster_orchestrator.py`. Compatibility/versioned trees are classified separately and do not count as canonical runtime merely because they contain similar scripts or deployment files.

## Invariants

1. DOW consumes immutable governed payload identity.
2. DOW emits findings/recommendations, not child decisions.
3. PCA/BT/DMAIC scores are diagnostics unless explicitly accepted by child governance.
4. ABACUS repo-local cADR/xOCD authority never supersedes child QPS ADR/OCD authority.
5. Historical deployments and duplicate version trees are excluded from active penetration metrics unless referenced by canonical runtime/CI.
6. Findings return through KEB normalization before child disposition.
