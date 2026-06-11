# DELTA_1 CI Contract

## Purpose

Normalize CI execution semantics across ABACUS workflows.

## Stable command contract

The following `make` targets represent the aspirational CI contract for ABACUS.
They are **not yet fully implemented** — the Makefile currently only defines `docs-zip`.
These targets will be added progressively in follow-up DELTA_1 PRs.

```bash
make bootstrap
make lint
make test
make build
make package
```

### Current canonical CI commands

Until the full `make` contract is implemented, CI uses these direct commands:

```bash
# Install dependencies
pip install -r DMAIC_V3/requirements.txt

# Run tests
python -m pytest DMAIC_V3/tests -q

# Lint (subset scoped in ci.yml)
flake8 DMAIC_V3/core/test_system_bridge.py run_deployment_test_system.py --max-line-length=120

# Package docs
make docs-zip
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
