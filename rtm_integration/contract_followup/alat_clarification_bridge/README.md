# ALaT Clarification Bridge

Version: `0.1.0`

This package adds a YAML-driven clarification bridge for RTM, Contract Follow-up and OFFER_list management.

## Purpose

The bridge tracks bidder clarification questions using a controlled Q3/Q4/Q5 route:

- Q3: Recovery System
- Q4: Line S
- Q5: Line W

It supports:

- RTM-linked clarification management
- Contract follow-up
- OFFER_list and bidder-response preparation
- internal SCK traceability using sub-question IDs
- consolidated bidder-facing answer generation
- stakeholder action tracking
- SSOT-to-Excel/HTML generation

## Locked origin tuple

The contractual origin remains the locked tuple:

- `MASTER.docx`
- `QPS_Contract_mirror_DOCX(1).pdf`

The YAML SSOT is the working clarification model only. It does not replace the locked contract source.

## Governance rules

- Keep the external route as Q3, Q4 and Q5.
- Internal sub-question numbering is retained for SCK traceability.
- Bidder-facing answers may omit the internal sub-numbering.
- Answers use short bullet roll-ups with Excel-friendly formatting.
- Slides are internal preparation material only and are not part of bidder-facing answers.
- Pressure, temperature and flow values shall be taken from the applicable main input/interface tables and contractual requirements.
- DBE shall confirm Line W and Line S handover conditions for nominal, transient and abnormal boundaries.

## Build

```bash
pip install pyyaml openpyxl
python rtm_integration/contract_followup/alat_clarification_bridge/tools/generate_bridge.py \
  --ssot rtm_integration/contract_followup/alat_clarification_bridge/ssot/alat_questions_ssot_v0_1.yaml \
  --out rtm_integration/contract_followup/alat_clarification_bridge/dist
```

Generated views:

- `dist/excel/ALaT_Questions_Bridge_v0_1.xlsx`
- `dist/html/alat_questions_bridge_v0_1.html`

## Roll-up logic

Granular internal candidate answers roll up into a single consolidated parent answer per question group:

```text
Q3.x -> Q3 parent answer
Q4.x -> Q4 parent answer
Q5.x -> Q5 parent answer
```
