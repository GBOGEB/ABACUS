# QPS WCS / QRB Energy-Exergy Functional Analysis — rev1.7

**Status: AMBER.** This is the technical-analysis snapshot integrated into ABACUS. It does not promote the offer evaluation to final compliance or final bidder ranking.

## Canonical role

ABACUS owns the technical/contract-analysis snapshot. CODEX owns evidence verification, clean-build/fresh-clone orchestration, semantic comparison, release receipts and CI/CD federation.

The rev1.7 package implements the project SSOT hierarchy:

1. REQUIREMENTS
2. SYSTEM_ARCHITECTURE
3. EQUIPMENT
4. INTERFACES
5. OPERATING_STATES
6. THERMODYNAMIC_STATES
7. ENERGY_EXERGY
8. UTILITIES
9. COST
10. EVIDENCE
11. DELIVERABLES
12. RFI_GAPS
13. LINEAGE

Historic 2023 pre-studies stay under EVIDENCE. Their values are reusable only through explicit provenance links.

## Main additions

- two-sided TP1/TP2 ICD interface model;
- service/provider/requestor terminal-point semantics;
- WCS/QRB utility mapping for electrical, cooling water, RCW/PCW, HVAC, heat recovery, GN2, instrument air, helium process and controls;
- CCB/AUB/Outside location semantics;
- equipment/BOM cards with SBS tags and magnitude/rank fields;
- 24/30-QM operating scenarios and utility profiles;
- source inventory, binary-extraction manifest and deliverable crosswalk;
- P0 RFI closure register;
- DMAIC KPI snapshot and diagnostic PCA pass;
- explicit not-for-use controls.

## Not-for-use boundary

Until the promotion gate is met this snapshot must not be used as proof of complete offer extraction, complete compliance, final bidder comparison, closed exergy balance, full-price decomposition, fresh-clone/CI proof, mutual consistency of every workbook/PDF, or absence of stale references.

## Federation

CODEX registry: `GBOGEB/CODEX:07_ops/qps_roundtrip/evidence_registry.qps_wcs_qrb_rev1_7.yaml`

The binary offer/pre-study PDFs are intentionally not committed here. Their hashes and sizes are preserved in the snapshot and CODEX evidence registry.
