# CI governance control surface

This directory is the machine-governed control surface for ABACUS workflow ownership,
ordering, consolidation and retirement decisions.

## Authority

- `workflow_policy.json` is the workflow-policy SSOT.
- `../../docs/ci/WORKFLOW_RATIONALIZATION.md` is a generated, version-bound view.
- `tests/test_workflow_policy.py` protects classification, parsing, report freshness and
  trigger isolation.
- `audit_ci_workflows.py` generates and validates the inventory.

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
python ci/governance/audit_ci_workflows.py \
  --check \
  --json-output ci-governance-report.json \
  --markdown-output docs/ci/WORKFLOW_RATIONALIZATION.md
```

## Adding a workflow

Every file in `.github/workflows/` must match exactly one rule in
`workflow_policy.json`, or `policy-and-inventory` fails.

1. Extend the regex of the rule whose cluster and lifecycle fit the new
   workflow. Add a new rule only when none fits; two matching rules fail
   the audit.
2. Regenerate the report and commit it with the workflow:

   ```bash
   python ci/governance/audit_ci_workflows.py \
     --markdown-output docs/ci/WORKFLOW_RATIONALIZATION.md
   ```

3. On Windows, convert the regenerated report to LF line endings before
   committing; otherwise the whole file shows as changed.
4. Run the local validation above. The report also records the policy
   SHA-256, so any policy edit needs a regenerated report.
5. Keep workflow YAML lines at 80 characters or fewer; `Changed docs lint`
   runs yamllint on changed files.
6. Check whether `MIP/statistics/g3a_w16_epoch.json` needs a re-pin
   (`scripts/g3a_w16_repin.py`); it pins the workflow population.

## Fan-out control

Governance-only changes belong under `ci/governance/**`. They are intentionally excluded
from the full product regression Python filter and remain covered by
`policy-and-inventory`.

Auto-merge is manual-only; ordinary PRs should not attach auto-merge, auto-approve or
auto-update checks as pass evidence.

The comparison baseline is PR #685: 71 checks, comprising 65 queued checks and six
conditional skips at the observation point. A governance-only PR is the acceptance probe
for the reduced fan-out. Queued checks are not counted as pass evidence.
