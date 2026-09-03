# QPS-LB OFFERS – REVIEW: Contract Compliance Extraction

**Source:** QPS- 3D _DKO.pptx (SCK CEN/101648634, ISC: Restricted), Diamantis Kounadis, 25/08/2026 — 15 slides
**Scope:** QPLANT-LB 3D Model (ALAT-20260812) and 2D Drawings (LKT-20260812)
**Purpose of this document:** Extract what in the two bidder offers is *agreeable*, *negotiable*, and *not agreeable* against SCK CEN requirements (RTM-xxx / OFFER-xx), so the OFFER review can be closed out.

> Numbers below are quoted verbatim from the deck. Nothing outside the deck is asserted as fact; recommended actions are marked as such.

---

## 1. Overall verdict (per bidder)

| Bidder | Compliant | Not compliant but negotiable | Not compliant | Open question |
|---|---|---|---|---|
| **ALAT** (3D model) | 2 (1 conditional) | 2 | 6 | 0 |
| **LKT** (2D drawings) | 2 (1 conditional) | 2 | 3 | 1 (RTM-447) |

**Bottom line from the deck:** neither offer is compliant as-is on 3D-model deliverable format (STEP AP242), Level of Representation (LoR) milestones, or the 3D-model management platform (RTM-447). Both are agreeable on general-arrangement drawings *if* GA drawings are deemed adequate. File-naming (RTM-439) and interface locations (RTM-442) are negotiable for both.

---

## 2. Model / drawing observations (slides 3–8, 11–12) — technical findings

| # | Finding (DKO) | Contract relevance |
|---|---|---|
| F1 | QLM-LB is located on the **South** wall of CCB, not the North wall (ALAT model) | Interface error — model must be corrected before acceptance |
| F2 | Wrong side of the multiline interface location on Cold Box | Interface error |
| F3 | Openings to the building walls need to be foreseen | Building-integration scope gap; clarify who owns wall penetrations |
| F4 | Discrepancy on CCB height between SCK CEN & ALAT 3D model | Coordinate/reference-data mismatch → links to RTM-441 |
| F5 | Interference of the interconnection lines with structural elements | Clash — must be resolved |
| F6 | LKT TAX11 Draft System Layout: "some discrepancy on the dimensions" | Dimensioning mismatch → links to RTM-441 |

---

## 3. ALAT — compliance to requirements (slides 9–10)

| Req. | SCK CEN Requirement (abridged) | ALAT Comment | ALAT Response | DKO Verdict | Agreeable? |
|---|---|---|---|---|---|
| RTM-437 | Supply the 2D manufacturing drawings | Suggestion | Only general drawings due to IP issues | If GA drawings adequate → COMPLIANT | **Conditionally YES** |
| RTM-437 | STEP AP242 or AP203 during Conceptual Design | Compliant | STEP AP203 can be provided | COMPLIANT | **YES** |
| RTM-438 | STEP AP242 during remainder of Contract | Suggestion | STEP AP203 or AP214 | NOT COMPLIANT | **NO** |
| RTM-439 | File names per naming convention [AD_06] | Compliant | Can follow §2.3.2.2 in [AD_06] | NOT COMPLIANT BUT NEGOTIABLE — filenaming per §2.3.2.2 is PS responsibility, not ALAT; own naming OK with clear interface description | **NEGOTIABLE** |
| RTM-442 | Model includes location of all external interfaces | Suggestion | Refer to project document list; interfaces shown in Preliminary design | NOT COMPLIANT BUT NEGOTIABLE — depends on maturity of building & services | **NEGOTIABLE** |
| RTM-442 | Metadata (component IDs, geometry, materials, kinematics, assembly) | Not applicable | STEP files do not include metadata | NOT COMPLIANT | **NO** |
| RTM-443 | LoR levels shall be provided | Suggestion | One STEP file at relevant milestones | NOT COMPLIANT | **NO** |
| RTM-447 | Establish & maintain 3D-model management platform (e.g. BIM 360) | Deviation | For cost reasons, no platform | NOT COMPLIANT | **NO** |
| OFFER-36 | Indicate the 3D-model management platform | Deviation | For cost reasons, no platform | NOT COMPLIANT | **NO** |
| OFFER-36 | Preliminary CAD model ≥ LoR 20 in STEP AP242 | Suggestion | STEP AP203 or AP214 | NOT COMPLIANT | **NO** |

---

## 4. LKT — compliance to requirements (slides 13–14)

| Req. | SCK CEN Requirement (abridged) | LKT Comment | LKT Response | DKO Verdict | Agreeable? |
|---|---|---|---|---|---|
| RTM-437 | Supply the 2D manufacturing drawings | Deviation | No manufacturing detail drawings; only GA | If GA adequate → COMPLIANT | **Conditionally YES** |
| RTM-437 | Supply CAD source file(s) of 3D model(s) | Clarification | Coldbox 3D model may not show internals | COMPLIANT | **YES** |
| RTM-439 | File names per [AD_06] | Deviation | Can't be realized from LKT side | NOT COMPLIANT BUT NEGOTIABLE — own naming OK with clear interface description | **NEGOTIABLE** |
| RTM-441 | Coherent coordinate system, axis orientation, global origin | Deviation | LKT uses own method of dimensioning | NOT COMPLIANT — LKT needs to adapt MINERVA coordinate system | **NO** |
| RTM-442 | Location of all external interfaces | Clarification | Interface position/size may not be final | NOT COMPLIANT BUT NEGOTIABLE — depends on maturity | **NEGOTIABLE** |
| RTM-442 | As-built 3D model at LoR 99 | Deviation | Only significant changes; red-marks in PDF for small deviations | NOT COMPLIANT | **NO** |
| RTM-443 | Level of Representation of 3D models | Deviation | Only 30%, 60%, 90% status | NOT COMPLIANT — likely confused LoR with LoD | **NO** |
| RTM-447 | 3D Model Management | — | *(no comment in offer)* | **Open question:** does silence mean LKT complies? | **TO CONFIRM** |

---

## 5. Cross-bidder synthesis

### Agreeable (accept)
- **RTM-437 GA drawings** (both) — accept *provided* SCK CEN formally states that General Arrangement drawings are adequate. This decision is on SCK CEN, not the bidders.
- **RTM-437 STEP AP203 in Conceptual Design** (ALAT) — accept.
- **RTM-437 CAD source of 3D model** (LKT) — accept; note coldbox internals may be hidden.

### Negotiable (agree a concession)
- **RTM-439 file naming** (both) — DKO position: bidders may use their own naming provided a clear interface description/cross-reference to SCK CEN is delivered; naming per [AD_06] §2.3.2.2 is the PS (SCK CEN) responsibility.
- **RTM-442 external interface locations** (both) — accept staged maturity (locations firmed up in Preliminary design) tied to building & services maturity.

### Not agreeable (hold the requirement / request revised offer)
- **STEP AP242** (RTM-438, OFFER-36) — both bidders offer AP203/AP214 only. AP242 carries the PMI/metadata required by RTM-442. Decision needed: insist on AP242, or formally waive and accept the metadata gap.
- **RTM-442 metadata** (ALAT) — "not applicable" is a rejection of the requirement, not a compliance statement.
- **RTM-443 LoR milestones** (both) — ALAT: single STEP per milestone; LKT: 30/60/90 % status (LoD, not LoR). Clarify the LoR definition with LKT.
- **RTM-447 / OFFER-36 3D model management platform** (ALAT) — refused on cost grounds. This is a process/control requirement; a cost line for it should be requested, or SCK CEN hosts the platform and defines upload obligations instead.
- **RTM-441 coordinate system** (LKT) — must adopt MINERVA coordinate system; ties directly to findings F4/F6 (height and dimension discrepancies).
- **RTM-442 as-built LoR 99** (LKT) — red-marked PDFs are not an as-built model.

### Open
- **RTM-447 (LKT)** — no statement in the offer. Request explicit written confirmation before close-out.

---

## 6. Recommended close-out actions (proposed, not in the deck)
1. SCK CEN internal decision: are GA drawings adequate? → unlocks RTM-437 for both.
2. SCK CEN decision on STEP AP242: enforce or waive (with metadata fallback plan).
3. Send clarification request to LKT: RTM-447 position; LoR vs LoD definition (RTM-443).
4. Send clarification request to ALAT: cost option for RTM-447 platform; metadata alternative for RTM-442.
5. Both bidders: correct model errors F1–F6 before next submission; adopt MINERVA coordinates.
6. Record concessions for RTM-439 and RTM-442 as formal contract deviations.

---

## 7. Deck structure note (for the slide-design side)
15 slides: 1 title, 6 model-observation slides (3–8), 4 compliance tables (9, 10, 13, 14), 2 drawing/room slides (11, 12), 1 legal/closure (15). No agenda, no summary/decision slide, no navigation — consistent with a short technical review deck; a 40–50 slide full deck would add agenda, requirement-by-requirement backup, and a decisions/actions slide.
