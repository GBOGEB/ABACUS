# CI Workflows Reference

These are reference copies of the GitHub Actions workflow definitions developed
during the MCP Orchestration & Governance session (2026-05-22).

They are stored as `.txt` files here because the GitHub App token used for the
session handover push does NOT have the `workflows` permission and therefore
cannot create/update files under `.github/workflows/`.

## Manual installation (requires a user PAT with `workflow` scope)

```bash
# From the repo root, on a branch:
for f in archive-deploy asset-verification governance-validation sync-assets; do
  cp docs/ci-workflows-reference/$f.yml.txt .github/workflows/$f.yml
done
git add .github/workflows/
git commit -m "ci: install MCP orchestration workflows"
git push
```

| Workflow | Purpose |
|----------|---------|
| archive-deploy.yml | Build & deploy publication archive |
| asset-verification.yml | Verify asset integrity / presence |
| governance-validation.yml | Run governance engine validation gates |
| sync-assets.yml | Synchronize assets across clusters |
