# CI governance control surface

This directory is the machine-governed control surface for ABACUS workflow ownership,
ordering, consolidation and retirement decisions.

## Authority

- `workflow_policy.json` is the workflow-policy SSOT.
- `../../docs/ci/WORKFLOW_RATIONALIZATION.md` is a generated, version-bound view.
- `tests/test_workflow_policy.py` protects classification, parsing, report freshness and
  trigger isolation.
- `../../scripts/audit_ci_workflows.py` generates and validates the inventory.

PCA and Bradley–Terry results are analytical evidence, not workflow-policy authority.
CODEX and ABACUS exchange governed evidence through versioned manifests and hashes;
neither repository duplicates the other's canonical source.

## Execution order

1. `pr_fast` — structural and unit evidence.
2. `pr_domain` — path-relevant integration, security and domain evidence.
3. `post_merge` — release, publication and reporting.
4. `scheduled` — comprehensive maintenance and monitoring.
5. `manual` — diagnostics and migration comparison.
6. `retire` — removal after replacement evidence is accepted.

## Local validation

```bash
python -m unittest ci/governance/tests/test_workflow_policy.py -v
python scripts/audit_ci_workflows.py \
  --check \
  --json-output ci-governance-report.json \
  --markdown-output docs/ci/WORKFLOW_RATIONALIZATION.md
```

## Fan-out control

Governance-only changes belong under `ci/governance/**`. They are intentionally excluded
from the full product regression Python filter and remain covered by
`policy-and-inventory`.

The comparison baseline is PR #685: 71 checks, comprising 65 queued checks and six
conditional skips at the observation point. A governance-only PR is the acceptance probe
for the reduced fan-out. Queued checks are not counted as pass evidence.
