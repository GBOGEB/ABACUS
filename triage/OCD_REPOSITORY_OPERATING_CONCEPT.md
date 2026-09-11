<!-- markdownlint-disable MD013 -->

# OCD — ABACUS repository operating concept

**ID:** TRIAGE-OCD-ABACUS-001

## Authority boundary

QPS engineering authority is owned by `GBOGEB/cryoplant-project` and registered in:

`ocd-adr/20_canonical/control/QPS_GLOBAL_ADR_OCD_SSOT_v1.json`

ABACUS owns repo-local analytical/runtime execution and its derived findings. Any QPS engineering content carried into DOW is an immutable, non-authoritative child projection. Engineering promotion or compliance disposition is forbidden until child re-entry.

## Mission

Receive immutable governed work payloads; perform bounded engineering, scientific, PCA/BT and DMAIC analysis; preserve provenance; emit typed findings; and return findings for KEB normalization and child-owned disposition.

## Operating sequence

`INTAKE -> DEFINE -> MEASURE -> ANALYZE -> IMPROVE -> CONTROL -> KNOWLEDGE -> TRACK -> DOW_RECEIPT -> KEB_RETURN -> CHILD_REENTRY`

## Modes

- deterministic engineering analysis
- DMAIC iteration
- PCA/drift diagnostics
- bottleneck prioritization
- multi-agent/MCP execution
- handover and temporal monitoring
- dashboard/report generation

## Failure policy

Fail closed on missing payload identity/provenance, digest drift, or an attempt to promote a derived finding into QPS engineering truth. Never convert an analytical recommendation into child compliance or engineering closure without child re-entry.
