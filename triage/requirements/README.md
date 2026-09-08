# ABACUS Coding Requirements (`CReq_###`)

`CReq_###` is the normative coding-requirement layer between architectural/control decisions and implementation PRs.

## Trace chain

```text
repo mission / cOCD
        |
       cADR
        |
    CReq_###        <- stable, testable coding requirement
        |
 implementation surface / test contract
        |
 set -> wave -> pulse -> task -> PR(s)
        |
 verification receipt / CI evidence
        |
 CONTROLLED
```

A PR is not automatically a requirement. Multiple PRs caused by the same contract defect SHALL trace to the same `CReq_###` root requirement.

## Required fields

Each requirement carries:

- stable `CReq_###` identifier;
- normative `statement` using SHALL/MAY semantics;
- rationale/root cause;
- originating or representative `source_prs`;
- parent `cADR` and `cOCD`;
- DMAIC and repository lifecycle phase;
- implementation surfaces;
- executable verification method and acceptance condition;
- controlled status.

## Status lifecycle

`PROPOSED -> ACCEPTED -> IMPLEMENTED -> VERIFIED -> CONTROLLED`

`DEPRECATED` is terminal for superseded requirements. A replacement SHALL retain an explicit lineage edge to the deprecated requirement.

## Credit boundary

A verified `CReq` proves repository/runtime conformance. It does **not** grant QPS engineering, compliance, negotiation, or child-disposition credit. ABACUS/DOW analytical outputs remain diagnostic until explicit governed re-entry through child authority.

## Initial requirement families

| ID | Family | Primary DMAIC role |
|---|---|---|
| `CReq_001` | canonical phase execution contract | Control |
| `CReq_002` | canonical construction / dependency injection | Control |
| `CReq_003` | canonical result schema | Control |
| `CReq_004` | incident deduplication / one repair pulse | Analyze |
| `CReq_005` | editorial-bot isolation | Control |
| `CReq_006` | mandatory PR lineage metadata | Measure |
| `CReq_007` | maturity metric normalization | Measure |
| `CReq_008` | DOW authority-boundary enforcement | Control |

The registry of record is `ABACUS_CODING_REQUIREMENTS.yaml`.
