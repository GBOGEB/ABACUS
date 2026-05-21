# DELTA_1 Security and Release Baseline

## Purpose

Establish the initial DevSecOps and release-governance baseline for ABACUS.

---

# Security baseline

## Required controls

- pull-request review
- protected main branch
- dependency review
- CodeQL scanning
- immutable release lineage
- audit traceability
- secret scanning
- release tagging discipline

## Recommended controls

- SHA-pinned actions
- OIDC-based cloud authentication
- artifact attestations
- environment-gated deployments
- deployment approval workflows

---

# Release lineage

## Canonical release flow

```text
commit -> PR -> CI validation -> merge -> SemVer tag -> release artifacts -> deployment promotion
```

## Release objectives

- reproducibility
- deterministic builds
- traceable provenance
- rollback capability
- environment promotion governance

---

# Deployment promotion model

| Environment | Purpose |
|---|---|
| dev | integration validation |
| stage | release candidate validation |
| prod | protected production deployment |

---

# ABACUS operational role

ABACUS owns:

- workflow execution
- CI orchestration
- release automation
- deployment governance
- runtime delivery lineage

CODEX owns:

- governance
- SDLC policy
- audit lineage
- cross-repository orchestration
