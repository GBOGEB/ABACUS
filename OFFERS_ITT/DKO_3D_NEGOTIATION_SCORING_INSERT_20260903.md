# DKO 3D Model Compliance — Negotiation Scoring Insert

**Reviewer:** DKO (Diamantis Kounadis)  
**Source:** `QPS- 3D _DKO.pptx`, SCK CEN/101648634, 2026-08-25  
**Decision use:** QPLANT tender scoring matrix and September 2026 negotiation agenda.

> Control: DKO compliance statements are **SOURCE-SUPPORTED**. The €150/h, 36-month internal integration-cost model below is **POSTULATED owner-side exposure** and must not overwrite bidder values or be double-counted in scoring.

## ALAT

| Requirement | Deviation | DKO status | Technical / owner burden |
|---|---|---|---|
| RTM-438 / RTM-442 — STEP AP242 + metadata | AP203/AP214; metadata not applicable | NOT COMPLIANT | Manual SBS/control-tag and component metadata mapping; weaker digital-twin/O&M continuity. |
| RTM-447 / OFFER-36 — 3D management platform | Refused for cost reasons | NOT COMPLIANT | Federation, version control and clash-management burden moves to SCK CEN. |
| RTM-443 — LoR throughout | STEP files at milestones | NOT COMPLIANT | Reduced concurrent engineering; late spatial/structural rework risk. |
| RTM-439 / RTM-442 — naming + interfaces | Native naming; interfaces mature later | NOT COMPLIANT BUT NEGOTIABLE | Close only with controlled interface/metadata crosswalk to SCK CEN SBS and control tags. |

## LKT

| Requirement | Deviation | DKO status | Technical / owner burden |
|---|---|---|---|
| RTM-441 — coherent MINERVA coordinates/global origin | Own dimensioning method | NOT COMPLIANT | Critical integration risk; manual realignment otherwise required for every model drop. |
| RTM-442 — as-built 3D LoR 99 | Smaller deviations as PDF red-marks | NOT COMPLIANT | SCK CEN would reconstruct final 3D as-built/digital twin during commissioning. |
| RTM-443 — LoR throughout | 30/60/90% drops | NOT COMPLIANT | LoR appears conflated with LoD/status; static drops inhibit continuous warm-piping/utilities integration. |
| RTM-447 — 3D management platform | No offer comment | PENDING CLARIFICATION | Confirm federated platform/workflow, access, versioning and cost responsibility before closure. |

## Projected internal integration-cost exposure

| Phase | Months | ALAT | LKT | Primary SCK CEN burden |
|---|---:|---:|---:|---|
| Concept | 1–6 | €27,000 | €36,000 | LKT coordinate translation / ALAT interface mapping |
| Detailed | 7–18 | €108,000 | €90,000 | ALAT metadata injection / LKT spatial integration |
| Construction | 19–30 | €90,000 | €72,000 | Clash resolution from static or milestone-only CAD exchanges |
| Commissioning | 31–36 | €36,000 | €90,000 | ALAT data architecture / LKT 3D as-built reconstruction |
| **Total** | **36** | **€261,000** | **€288,000** | **POSTULATED @ €150/h internal operational cost** |

## Negotiation gates

1. **LKT P1:** formally accept MINERVA coordinate system/global origin; prove with an aligned sample model drop.
2. **LKT P1:** abandon PDF-red-mark-only as-built deviations; maintain 3D LoR 99 through commissioning handover.
3. **LKT P1:** answer RTM-447 explicitly: platform, federation, access, versioning, responsibilities and costs.
4. **ALAT P1:** if AP242 remains rejected, deliver a machine-readable metadata/interface manifest plus ICD crosswalk from native AP203/AP214 objects to SBS/control/interface identifiers.
5. **ALAT P2:** replace milestone-only exchange with reviewable LoR/model-exchange gates supporting concurrent integration.

## Scoring treatment

Use the DKO finding as a technical compliance/review input. Keep the integration penalty as a separate owner-cost exposure field until the evaluation method explicitly authorizes monetization. Record any negotiated cure as a closure condition with evidence, owner and due date rather than silently changing the original DKO disposition.