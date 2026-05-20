# DELTA_1 CI Contract

## Purpose

Normalize CI execution semantics across ABACUS workflows.

## Stable command contract

All workflows should progressively converge toward:

```bash
make bootstrap
make lint
make test
make build
make package
```

## Objectives

- deterministic workflow execution
- reusable workflow composition
- reduced workflow duplication
- reproducible local-to-CI behavior
- language-agnostic orchestration

## Governance requirements

### Required

- protected main branch
- PR-based merge model
- status checks
- release lineage
- immutable workflow audit trail

### Recommended

- SHA-pinned GitHub Actions
- OIDC-based cloud authentication
- artifact attestations
- dependency review
- CodeQL scanning

## Execution model

ABACUS remains implementation-aware while exposing stable governance-oriented interfaces for CI/CD orchestration.
