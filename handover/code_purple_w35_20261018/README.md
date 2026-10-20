# CODE PURPLE W35 — Global DOV live bridge & lossless operational handover

**Status:** `MERGE_ADMISSION=HOLD`. GitHub-first operational; **not** canonical V2 replay-sealed handover, nor independent security/approval proof.

## Central entrypoints

**Canonical global owner:** [W38 Global DOV](../../MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/global/index.html). This remains generated from `global/ledger.json` and `index.template.html` via `render_global.py`. W35 introduces no parallel global SSOT.

**Read-only live companion:** [W35 Mission Control](../../tools/everred_v3/dashboard/mission_control_w35.html). It reads GitHub GET-only; resolves default branch dynamically; displays HEAD, overview, family DOV, first-red and queue; accepts safe untrusted local JSON import and exports browser observations as non-authoritative records.

**Existing views with inbound navigation:** [EVERRED V3](../../tools/everred_v3/dashboard/index.html), [SUT observability](../../tools/everred_v3/sut_gui/dashboard_v3.html). W38 canonical entrypoint also points to W35.

## Read in order

1. [HANDOVER.md](HANDOVER.md) — full family/repo/global DOV and source-owned growth scout.
2. [DROPIN.md](DROPIN.md) — copy-ready receiver for exact-head refresh, gate review and bounded next wave.
3. [QA_REPORT.json](QA_REPORT.json) — local HTML browser and source-test QA; no native promotion.
4. [MANIFEST.json](MANIFEST.json) — GitHub source file index, not cryptographic V2 raw-evidence replay.
5. [W35 source fixture](../../tools/everred_v3/dashboard/w35_ledger.json) and independent [census adapter](../../tools/recovery/w35_census_rollup.py) on **separate disjoint branch** `code-purple/w35-disjoint-census-20261018`.
6. W34 immutable record [handover](../code_purple_w34_20261018/HANDOVER.md); original [handover template](../HANDOVER_MESSAGE_TEMPLATE.md) and [V2 process](../../tools/handover_v2/process_spec.json).

## Guardrails

W38 single Py3.12 focused matched 660/723 to 707/723 is a real **source-specific** gain; current-main broad statement/branch coverage stays UNKNOWN. W35 native CI is **not proven**, source branch commits are not reviewed PR admission. No GitHub admin/merge/runner dispatch/waiver is performed by W35.

The GitHub index is source-bound, but until every cited raw native ZIP/source byte is independently archived and replayed by `tools/handover_v2/build_handover.py`, classification remains `GITHUB_FIRST_OPERATIONAL` and not `V2_SCHEMA_AND_REPLAY_VERIFIED`.
