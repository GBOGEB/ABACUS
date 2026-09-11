# MIP Receipt Policy

MIP receipts are generated evidence, not source contract.

## Public repository rule

Do not commit generated receipt payloads from `MIP/receipts/` to public rollout PRs unless the receipt has been explicitly reviewed and approved for publication.

This keeps local path census, working-tree state, commit evidence, and environment-specific diagnostics out of source-control history by default.

## Expected flow

1. Keep `MIP/README.md`, `MIP/mip_lanes.json`, and MIP runner scripts in source control.
2. Generate receipts locally or in a controlled CI environment.
3. Use receipts to select the next MIP lane, but publish only sanitized conclusions unless full evidence publication is approved.
4. Use reviewed private receipts to assess DoV against `MIP/README.md`; public publication is not required. Missing executable evidence keeps DoV withheld.

## Execution register

Follow the [shared MIP execution register](https://github.com/GBOGEB/ABACUS/blob/mip/receipt-policy/MIP/EXECUTION.md) for priorities, dependencies, scaling and CONTROL gates. After merge, use its main-branch version.

Ignore rules do not untrack existing receipts. The DOCX remote bootstrap is historical source-seeding evidence, not runtime proof; do not refresh it with local diagnostics.
