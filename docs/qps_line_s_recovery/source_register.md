# Source register

## SRC-D2-5-6-5

- D2.1 section: 5.6.5 Utility event.
- Role: LOOP profile, relief timing, return flow, shield mitigation.
- Status: `MASTER_FOR_SESSION`.

## SRC-D2-5-6-6

- D2.1 section: 5.6.6 Cryoplant trip.
- Role: fallback reaction and compressor restart recovery statement.
- Status: `MASTER_FOR_SESSION`.

## SRC-D2-8-2

- D2.1 section: Appendix 8.2 General PFD.
- Role: QPS/QCELL/QVE/QRB/Line-S topology anchor.
- Status: `MASTER_FOR_SESSION`.

## SRC-D2-8-3

- D2.1 section: Appendix 8.3 model.
- Role: model decomposition and SIMCRYOGENICS lineage.
- Status: `MASTER_FOR_SESSION`.

## SRC-D2-8-4

- D2.1 section: Appendix 8.4 modes.
- Role: mode, valve-state, recovery-path, and mode-dependent V_eff evidence.
- Status: `SOURCE_BOUND_PARTIAL_EXTRACTION`.
- Work order: ABACUS #1313.
- Source file: `D2_1_CRYOGENIC_SYSTEM_CONCEPTUAL_NATIVE.docx`.
- Document reference: `DSBT-TN-24-37-3.0`.
- Issue / revision: `2-1`.
- Document date: `2024-06-13`.
- Source custody: user Library locked source; not committed to this repository.
- Source SHA-256:
  `2700ea0af44f90dfe140fab8a4b7c203bedcf76ec7eee91b29c92d83d01196ba`.
- Appendix figure inventory: 23 source figures, `image58.emf` through
  `image80.emf`.

## Appendix 8.4 extraction state

The source itself is now bound and the complete 23-mode figure inventory is
represented in the machine-readable extraction contract.

Current extraction is deliberately `PARTIAL_EXTRACTED`:

- 23 / 23 mode identities are source-bound.
- 8 modes contain source-supported partial state/recovery evidence.
- 15 modes remain mode-identified only.
- 0 modes are claimed `STATE_COMPLETE`.
- no mode-dependent V_eff is promoted from an inferred topology.

The repository stores the source receipt, source digest, figure digests, and
the controlled extraction. It does not store or redistribute the locked
24.5 MB source document.

## Appendix 8.4 extraction rule

No valve state, fail state, recovery path, or mode-dependent connected volume
may be promoted from engineering inference alone.

`EXTRACTED` is permitted only when every source mode is
`STATE_COMPLETE` with source/evidence lineage.

Machine-readable extraction:

`docs/qps_line_s_recovery/appendix_8_4_mode_valve_extraction.yaml`

Machine-readable source receipt:

`docs/qps_line_s_recovery/appendix_8_4_source_receipt.json`
