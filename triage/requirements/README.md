# Coding Requirements (`CReq_###`)

`CReq_###` is a **repo-agnostic canonical coding-requirement namespace**. A requirement may be discovered in ABACUS, CODEX, cryoplant-project, or another child, but discovery location is provenance rather than ownership.

## Identity and scope

- `CReq_###` — global/federated canonical requirement.
- `CReq_ABACUS_###` — ABACUS-local requirement or approved ABACUS override.
- `CReq_CODEX_###` — CODEX-local requirement or approved CODEX override.
- `CReq_CRYOPLANT_###` — cryoplant-project-local requirement or approved override.

Local IDs use their own local sequence and therefore never consume, overwrite, or masquerade as global IDs.

## Resolution hierarchy

```text
GLOBAL CReq_###
     |
     +--> applies by default to every adopted scope
     |
     +--> local non-conflicting addition: CReq_<REPO>_###
     |
     +--> proposed local override: CReq_<REPO>_###
              |
              +--> local repo owner review
              +--> parent cADR/cOCD authority review
              +--> global CReq authority approval
              |
              +--> APPROVED -> local wins inside declared scope only
              +--> otherwise -> global remains effective
```

A local requirement SHALL NOT silently shadow a global requirement. `Local wins` is valid only for an explicit approved override. The global ID, text, and applicability to other repositories remain unchanged.

The normative scope/precedence contract is `CODING_REQUIREMENT_SCOPE_POLICY.yaml`.

## Trace chain

```text
federation / global governance
        |
       cOCD
        |
       cADR
        |
    CReq_###                 <- global stable requirement
        |
        +-- CReq_<REPO>_###  <- local addition/approved override when needed
        |
 implementation surface / test contract
        |
 set -> wave -> pulse -> task -> PR(s)
        |
 verification + approval receipt / CI evidence
        |
 CONTROLLED
```

A PR is not automatically a requirement. Multiple PRs caused by the same contract defect SHALL trace to the same root requirement.

## Status lifecycle

Requirement conformance: `PROPOSED -> ACCEPTED -> IMPLEMENTED -> VERIFIED -> CONTROLLED`.

Override approval is separate: `PROPOSED -> REVIEWED -> APPROVED`, with `REJECTED`, `SUPERSEDED`, and `EXPIRED` states retained as traceable outcomes.

## Credit boundary

A verified `CReq` proves coding/repository/runtime conformance. It does **not** grant QPS engineering, compliance, negotiation, or child-disposition credit. ABACUS/DOW analytical outputs remain diagnostic until explicit governed re-entry through child authority.

## Initial globally-candidate requirement families

The initial `CReq_001`–`CReq_008` were discovered from ABACUS PR history. Their ABACUS origin does not make their identity ABACUS-local. They remain `PROPOSED` global candidates until accepted by the global/federated requirement authority.

The originating registry is `ABACUS_CODING_REQUIREMENTS.yaml`; federation should later promote accepted global records into the canonical cross-repository registry while retaining `origin_repo` and `origin_prs` provenance.
