# W000 Q3/Q4/Q5 Tender Review Artifact Set

This directory contains the provisional review package for ALAT clarification
questions Q3, Q4 and Q5.

## Contents

- `MAIN_QA_REGISTER.md` preserves the tender-question register and draft
  applicant-facing answers.
- `COMPENDIUM.md` consolidates the Q3/Q4/Q5 technical interpretation.
- `MANAGEMENT_SUMMARY.md` highlights highest-risk clarification items.
- The ALAT review-intent artifact was externalized from public ABACUS under
  #1591. Its original path, SHA-256, private repository, and provenance record
  are retained in `ssot/review_artifact_manifest.yaml#tender-alat-intent`.
- `CONTRACTUAL_GAPS.md` summarizes gaps mirrored in
  `ssot/contractual_gap_register.yaml`.

## Governance and Validation

- SSOT registry: `ssot/ssot_items.yaml`
- Contractual gap register: `ssot/contractual_gap_register.yaml`
- Governance controls: `governance/review_gate_policy.yaml` and
  `governance/pr_review_control.yaml`
- CI/CD scaffolding: `.github/workflows/review-artifact-validation.yml`
- Validation command: `python scripts/validate_review_package.py`

Status: Draft Review v0.2
