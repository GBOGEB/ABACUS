# DELTA_1 Artifact Attestation Strategy

## Purpose

Define the provenance and artifact-attestation strategy for recursive GitHub-native release governance.

---

# Strategic objectives

- reproducible releases
- immutable release lineage
- deployment traceability
- auditable provenance
- recursive release evidence

---

# Canonical provenance chain

```text
source commit
  -> PR review
  -> CI validation
  -> protected merge
  -> release workflow
  -> artifact generation
  -> artifact attestation
  -> deployment promotion
```

---

# Recommended controls

| Control | Recommendation |
|---|---|
| SHA-pinned actions | ENABLE |
| Protected release branches | ENABLE |
| Signed tags | ENABLE |
| Artifact attestations | ENABLE |
| Immutable audit lineage | ENABLE |
| Environment-gated promotion | ENABLE |

---

# Attestation objectives

Every release artifact should eventually trace to:

- exact source commit,
- reviewed pull request,
- validated workflow execution,
- governed deployment promotion.

---

# DELTA_1 operational objective

Transform ABACUS into:

- a governed release engine,
- provenance-aware deployment orchestrator,
- recursive operational lineage platform.
