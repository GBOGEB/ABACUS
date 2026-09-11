# MIP Receipt Policy

MIP receipts are generated evidence, not source contract.

## Public repository rule

Do not commit generated receipt payloads from `MIP/receipts/` to public rollout PRs unless the receipt has been explicitly reviewed and approved for publication.

This keeps local path census, working-tree state, commit evidence, and environment-specific diagnostics out of source-control history by default.

The same rule applies to nested MIP surfaces, including `integration/codespace_jyperter/MIP/receipts/`.

## Expected flow

1. Keep `MIP/README.md`, `MIP/mip_lanes.json`, runner scripts, tests, schemas, and sanitized acceptance summaries in source control.
2. Generate receipts locally or in a controlled CI environment.
3. Use receipts to select the next MIP lane, but publish only sanitized conclusions unless full evidence publication is approved.
4. Use reviewed private receipts to assess DoV against `MIP/README.md`; public publication is not required. Missing executable evidence keeps DoV withheld.
5. A receipt that is already tracked must be explicitly reviewed; adding an ignore rule does not untrack it.

## Execution register

Follow the [shared MIP execution register](https://github.com/GBOGEB/ABACUS/blob/main/MIP/EXECUTION.md) for priorities, dependencies, scaling and CONTROL gates. Until ABACUS #1127 merges, review its proposed register in that PR.
