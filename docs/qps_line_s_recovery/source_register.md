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
- Status: `SOURCE_PENDING_EXTRACTION`.
- Successor work-order: ABACUS #1313.

## Appendix 8.4 extraction rule

The authoritative Appendix 8.4 content is not present as an extracted evidence
table in this repository.

Until source evidence is attached, no valve state, fail state, recovery path,
or mode-dependent connected volume may be inferred or promoted.

Machine-readable intake contract:

`docs/qps_line_s_recovery/appendix_8_4_mode_valve_extraction.yaml`
