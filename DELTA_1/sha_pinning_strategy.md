# DELTA_1 SHA Pinning Strategy

## Purpose

Define the GitHub Actions immutability strategy for governed CI/CD execution.

---

# Strategic objectives

- immutable workflow dependencies
- deterministic CI execution
- reduced supply-chain risk
- reproducible operational lineage

---

# Governance model

## Required for production-grade workflows

- pin reusable actions to full commit SHAs
- avoid mutable floating tags in protected release workflows
- document approved action sources

---

# Example

## Preferred

```yaml
uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608
```

## Transitional

```yaml
uses: actions/checkout@v4
```

---

# DELTA_1 objective

Ensure ABACUS workflows become:

- immutable,
- reviewable,
- auditable,
- provenance-aware.
