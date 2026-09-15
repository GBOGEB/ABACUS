# W110 DOW Consumer: MIP Canonical SSOT Registry

ABACUS/DOW consumes the CODEX W110 registry as derived analysis and disposition
logic. It does not move QPS engineering authority out of the child repo.

## Result

- Core registry: **ACCEPT**
- Previous LLDB-DAP tail: **ACCEPT as historical receipt-backed proof**
- Smaller active repos: **DEFER** until each has a repo-local visible SSOT
  pointer and exact-head receipt.

## Denominators

- Active satellite repos: 5
- Dormant candidates not promoted: 2

## Consumed historical tail

- CODEX exact head: `5e58badb150df9ce0423e1d02f9d913380d4597d`
- receipt SHA256: `3b32650abf18b824b5f3f06a113139ce470900c0957cef9d44c4b4e6e920f2d1`
- real LLDB steps: `10`

## DOW rule

ACCEPT only when exact SHA, receipt status, DoV status and steps are all bound.
DEFER active satellites when the repo exists and is active but lacks a canonical
repo-local SSOT pointer.
