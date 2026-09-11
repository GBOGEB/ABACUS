# MIP Receipt Policy

MIP receipts are generated evidence, not source contract.

## Public repository rule

Do not commit generated receipt payloads from `MIP/receipts/` to public rollout
PRs unless the receipt has been explicitly reviewed and approved for publication.

This keeps local path census, working-tree state, commit evidence, and
thvironment-specific diagnostics out of source-control history by default.

The same rule applies to nested MIP surfaces, including
`integration/codespace_jyperter/MIP/receipts/`.

## Expected flow

1. Keep `MIP/README.md`, `MIP/mip_lanes.json`, runner scripts, tests, schemas,
   and sanitized acceptance summaries in source control.
2. Generate receipts locally or in a controlled CI environment.
3. Use receipts to select the next MIP lane, but publish only sanitized
   conclusions unless full evidence publication is approved.
4. Treat the absence of a public receipt as `DoV withheld`, not as a failed
   rollout.
5. A receipt that is already tracked must be explicitly reviewed; adding an
   ignore rule does not untrack it.
