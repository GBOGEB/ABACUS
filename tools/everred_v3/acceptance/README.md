# Governed Acceptance Debt: read-only core provider

The Python files in this directory implement an additive, zero-dependency
ABACUS evidence projection. The consumer contracts in `input/contributor/`
are read-only envelopes for CODEX and QPS; they do not activate remote workers.

Machine sources: `input/obligations.json`, `input/contexts.json` and
`input/observations.jsonl`. The first two are a frozen snapshot of known
GitHub source identities. The last one contains **proposals** for previously
observed receipts and is not an independently authenticated GitHub API feed.

Human outputs: `dashboard/index.html` and `dashboard/acceptance_debt.md`.
Machine outputs: `dashboard/acceptance.json`, `dashboard/dag.json`,
`dashboard/sipoc.json`, `dashboard/dmaic_mip_pulses.json`,
`dashboard/ledger_proposals.jsonl`, `dashboard/sha256.json`.

Run locally via `python -m acceptance.cli` with explicit input arguments;
there are no network requests, no GitHub writes and no background scheduler.
Main, CODEX and QPS consumers shall supply new exact-head native evidence
and independent disposition via their own governed processes.
