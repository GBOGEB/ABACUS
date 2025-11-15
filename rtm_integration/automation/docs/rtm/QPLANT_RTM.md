# QPLANT Cryogenic System - Requirements Traceability Matrix
## Engineering Handover Document

**Document Version:** 1.0  
**Generated:** 2025-09-24 10:46:33  
**Project:** MYRRHA Phase 1 - Cryoplant Technical Requirements  
**Document ID:** QPLANT-RTM-001

---

## Executive Summary

This Requirements Traceability Matrix (RTM) provides a comprehensive breakdown of the QPLANT cryogenic system requirements extracted from the technical specification document "Addendum II - Cryoplant Technical Requirements". The RTM establishes clear traceability from high-level system requirements down to specific component-level requirements through a hierarchical System Breakdown Structure (SBS).

### Key Metrics
- **Total Requirements:** 16
- **High Priority Requirements:** 15
- **Safety Requirements:** 0
- **Performance Requirements:** 4

---

## System Breakdown Structure (SBS)

The QPLANT system is organized according to the following hierarchical structure:

### Level 0 - System Level
- **QSYS**: Complete Cryogenic System
- **QSYS-PR**: Project Requirements

### Level 1 - Major Subsystems  
- **QPLANT**: Main cryogenic refrigeration plant
- **QINFRA**: CSS cryogenic supply system infrastructure
- **QCELL**: CSS cryogenic USER - individual cryomodule and valve box combinations
- **QDIST**: CSS cryogenic USER - distribution lines and headers

### Level 2 - Major Components
- **WCS**: Warm Compressor Station
- **QRB**: Refrigeration Cold Box

### Level 3 - Sub-Components
- **PVPS**: Pressure Vessel & Piping System (under WCS)
- **HP**: High Pressure System (under WCS)
- **CC**: Cold Compressors (under QRB)
- **TURBINES**: Turbo Expanders (under QRB)
- **BATH-4K**: 4K Bath System (under QRB)
- **BATH-2K**: 2K Bath System (under QRB)

---

## Requirements Breakdown

### Operational Requirements

#### RTM-01
**Description:** The QPLANT shall be capable to operate uninterrupted in 2K mode for at least 90 consecutive days

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Performance  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Temperature condition: 2K; Value shall meet 90   
**Rationale:** Required for proper system functionality

**Child Requirements:** RTM-02, RTM-03, RTM-04  
---

#### RTM-04
**Description:** The QPLANT shall support ≥ 50 warm-up/cool-down cycles (300 K ↔ 2 K)

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 50 wa; Temperature condition: 300K; Temperature condition: 2K  
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-01  
---

#### RTM-05
**Description:** The QPLANT shall support the steady state operational scenarios: Warm Stop, Thermal Shield Standby, 4.5 K Standby, 2 K Standby, 2 K Operation

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** High  
**Verification Method:** Demonstration  
**Acceptance Criteria:** Temperature condition: 4.5K; Temperature condition: 2K; Temperature condition: 2K  
**Rationale:** Required for proper operational flexibility and system control

---

#### RTM-06
**Description:** The QPLANT shall support the scenario transitions given in Figure 6

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 6   
**Rationale:** Required for proper operational flexibility and system control

**Child Requirements:** RTM-07, RTM-08, RTM-09, RTM-010, RTM-011, RTM-012  
---

#### RTM-08
**Description:** The QPLANT shall perform the cool-down of the QPLANT simultaneously with the cryogenic users (QCELL and QDIST static heat loads only)

**SBS Assignment:** QSYS → QCELL → 

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Compliance with requirement as specified  
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-06  
---

#### RTM-09
**Description:** The QPLANT shall facilitate parallel cool down/warm up of all QCELLs. During cooldown and warm-up, cryomodules impose constraints: Magnetic shields must reach T < 70 K before cavities reach T < 10 K

**SBS Assignment:** QSYS → QCELL → 

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Temperature condition: 70K; Temperature condition: 10K  
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-06  
---

#### RTM-010
**Description:** The QPLANT shall facilitate an alternative cooldown in which only the thermal-shield (TS) circuit is cooled until their average temperature reaches 50 K. Subsequently the headers A–B and D–E are simultaneous cooled down

**SBS Assignment:** QSYS → QDIST → 

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Temperature condition: 50K  
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-06  
---

#### RTM-011
**Description:** The QPLANT shall facilitate the warm-up of the cryogenic users from 2 K to 300 K in less than 5 days

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Temperature condition: 2K; Temperature condition: 300K; Value shall meet 5   
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-06  
---

#### RTM-012
**Description:** The QPLANT shall support the transition shown in Figure 6 for the warming-up of the cryogenic users, whether passively or actively (with QCELL heaters if available)

**SBS Assignment:** QSYS → QCELL → 

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 6   
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-06  
---

#### RTM-013
**Description:** The Contractor may implement a manual purging, manual conditioning, and manual initial preparation of the QPLANT

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** Medium  
**Verification Method:** Test  
**Acceptance Criteria:** Compliance with requirement as specified  
**Rationale:** Required for proper system functionality

**Child Requirements:** RTM-014, RTM-015, RTM-016  
---

### Maintenance Requirements

#### RTM-02
**Description:** The maintenance schedule shall take into account the following constraints: ≥ 6 months: ≤ 10 days in 2K standby; ≥ 1 year: ≤ 20 days in 4.5K standby; ≥ 5 years: ≤ 60 days in warm stop; ≥ 10 years: ≤ 120 days in warm stop

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 6 m; Value shall meet 10 ; Temperature condition: 2K  
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-01  
---

### Lifetime Requirements

#### RTM-03
**Description:** The QPLANT shall have a lifetime of at least 40 years

**SBS Assignment:** QSYS-PR → QPLANT → WCS

**Type:** Design  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 40   
**Rationale:** Required to meet project lifetime objectives

**Parent Requirements:** RTM-01  
---

### Performance Requirements

#### RTM-07
**Description:** The QPLANT shall execute the transition using the capacity defined by the steady state scenarios. No additional capacity shall be added solely for acceleration of state transitions

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Performance  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Compliance with requirement as specified  
**Rationale:** Required to meet operational performance targets

**Parent Requirements:** RTM-06  
---

#### RTM-015
**Description:** The QPLANT shall facilitate an average retention rate of 0.8 g/s LHe per individual QCELL (24 g/s total) during the filling process

**SBS Assignment:** QSYS → QCELL → 

**Type:** Performance  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 0.8 g; Value shall meet 24 g  
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-013  
---

#### RTM-016
**Description:** During LHe filling, the QPLANT shall provide 2,900 L of LHe to the users

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Functional  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Value shall meet 2 ; Value shall meet 900   
**Rationale:** Required for proper system functionality

**Parent Requirements:** RTM-013  
---

### Safety Requirements

#### RTM-014
**Description:** The QPLANT shall adhere to the purge-parameter table (pressure, flow-rate, duration, allowable residual O₂) provided by SCK CEN during contract execution

**SBS Assignment:** QSYS → QPLANT → WCS

**Type:** Performance  
**Priority:** High  
**Verification Method:** Test  
**Acceptance Criteria:** Compliance with requirement as specified  
**Rationale:** Required for safe operation of cryogenic system

**Parent Requirements:** RTM-013  
---


## Traceability Matrix Summary

| SBS Level 1 | Requirements Count | High Priority | Safety Critical |
|-------------|-------------------|---------------|-----------------|
| QPLANT | 11 | 10 | 0 |
| QCELL | 4 | 4 | 0 |
| QDIST | 1 | 1 | 0 |


---

## GitHub Integration Readiness

This RTM is prepared for integration with the existing GitHub infrastructure:

- **GBOGEB/DOCX_RTM_Automation**: Ready for automated RTM updates
- **GBOGEB/ABACUS**: Compatible with existing project structure  
- **pipeline-automation-hub**: Ready for CI/CD integration
- **KEB Digital Twin**: Requirements mapped to system components
- **HEPAK projects**: Traceability established for cryogenic properties

## Next Steps

1. **Review and Validation**: Technical review of extracted requirements
2. **Gap Analysis**: Identify any missing requirements from source documents
3. **Integration Testing**: Verify compatibility with existing GitHub workflows
4. **Stakeholder Approval**: Obtain approval from engineering teams
5. **Implementation**: Deploy to production RTM system

## Document Control

- **Author**: DeepAgent RTM Generator
- **Reviewer**: [To be assigned]
- **Approver**: [To be assigned]
- **Next Review Date**: [To be scheduled]

---

*This document was generated automatically from the QPLANT technical requirements specification. For questions or updates, please contact the project technical team.*
