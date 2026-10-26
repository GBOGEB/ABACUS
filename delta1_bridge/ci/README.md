# Federation CI workflow (manual install)

`federation-metrics-validate.yml` is a reusable (`workflow_call`) CI workflow for
validating federation metrics via the `delta1_bridge` adapter.

It is shipped here (not under `.github/workflows/`) because the automation account
used to open this PR does not hold the GitHub `workflows` permission and therefore
cannot create files under `.github/workflows/` directly.

## To activate
Copy it into the workflows directory on this branch (or main), then commit:

```bash
mkdir -p .github/workflows
cp delta1_bridge/ci/federation-metrics-validate.yml .github/workflows/
git add .github/workflows/federation-metrics-validate.yml
git commit -m "ci: activate reusable federation-metrics-validate workflow"
```

PowerShell:
```powershell
New-Item -ItemType Directory -Force .github\workflows | Out-Null
Copy-Item delta1_bridge\ci\federation-metrics-validate.yml .github\workflows\
git add .github/workflows/federation-metrics-validate.yml
git commit -m "ci: activate reusable federation-metrics-validate workflow"
```
