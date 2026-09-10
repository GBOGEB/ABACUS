# DOW Consumption: LLDB-DAP Swift Docker Runner MCP

ABACUS consumes the CODEX KEB receipt for the widened runtime-health lane.

Current state is **ACCEPT**.

## Consumed KEB Receipt

- Producer PR: https://github.com/GBOGEB/CODEX/pull/598
- Producer exact head SHA: `5e58badb150df9ce0423e1d02f9d913380d4597d`
- Producer workflow run: https://github.com/GBOGEB/CODEX/actions/runs/34508749625
- Receipt artifact ID: `10164897765`
- Receipt artifact digest: `sha256:1e66581b7e2c53db6526eb08490cf744554618025e52e7691ed74373de0ad150`
- Receipt SHA256: `3b32650abf18b824b5f3f06a113139ce470900c0957cef9d44c4b4e6e920f2d1`
- Probe status: `ACCEPT`
- DoV status: `PASS`
- Real LLDB probe steps: `10`

## Consumption Rule

DOW accepts this receipt because the producer receipt exact SHA matches the observed CODEX
PR head, the probe status is `ACCEPT`, DoV status is `PASS`, and
`real_probe_steps_gt_zero` is true.
