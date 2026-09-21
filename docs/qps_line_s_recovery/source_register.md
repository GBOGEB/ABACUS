# Source register

| Source ID | D2.1 section | Role | Status |
|---|---|---|---|
| SRC-D2-5-6-5 | 5.6.5 Utility event | LOOP profile, relief timing, return-flow profile, shield-cooling mitigation | MASTER for session |
| SRC-D2-5-6-6 | 5.6.6 Cryoplant trip | Similar fallback reaction and compressor restart recovery statement | MASTER for session |
| SRC-D2-8-2 | Appendix 8.2 General PFD | Topology anchor for QPS, QCells, QVE, QRB, warm lines, Line S, recovery and purification | MASTER for session |
| SRC-D2-8-3 | Appendix 8.3 model | Model decomposition into 300 K to 30 K, 30 K to 4 K, and LINAC subsystems | MASTER for session |
| SRC-D2-8-4 | Appendix 8.4 modes | Valve-state, operating-mode, recovery-path, and mode-dependent V_eff extraction | SOURCE_PENDING_EXTRACTION — ABACUS #1313 |

## Appendix 8.4 extraction rule

The authoritative Appendix 8.4 source content is not present as an extracted evidence table in this repository. Until source evidence is attached, no valve state, fail state, recovery path, or mode-dependent connected volume may be inferred or promoted.

Machine-readable intake contract:
`docs/qps_line_s_recovery/appendix_8_4_mode_valve_extraction.yaml`.
