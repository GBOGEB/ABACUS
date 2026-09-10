# MIP Receipt Policy

MIP receipts are generated evidence, not source contract.

## Public repository rule

Do not commit generated receipt payloads from `MIP/receipts/` to public rollout PRs unless the receipt has been explicitly reviewed and approved for publication.

This keeps local path census, working-tree state, commit evidence, and environment-specific diagnostics out of source-control history by default.

## Expected flow

1. Keep `MIP/README.md`, `MIP/mip_lanes.json`, and MIP runner scripts in source control.
2. Generate receipts locally or in a controlled CI environment.
3. Use receipts to select the next MIP lane, but publish only sanitized conclusions unless full evidence publication is approved.
4. Treat the absence of a public receipt as `DoV withheld`, not as a failed rollout.
