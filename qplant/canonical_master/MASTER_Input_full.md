# QPS (Addendum II) — Master Input Document
*Parsed: 2026-05-12T19:54:53.721754*
*Sections: 251 | Tables: 34 | Figures: 38 | Equations: 59 | Requirements: 1254*

---
SCK CEN Ref.:

QPS (Addendum II) draft after approval

Technical Specifications and Project Requirement

Tender reference: 2024-106-IVE

© SCK CEN - Stichting van Openbaar Nut – Fondation d'Utilité Publique ‐ Foundation of Public Utility
Registered Office: Avenue Herrmann Debroux 40 – BE‐1160 BRUSSEL
Research Centres:

Boeretang 200 - 2400 MOL – Belgium

Chemin du Cyclotron 6 - 1348 Ottignies-Louvain-la-Neuve – Belgium

www.sckcen.be

Copyright Rules

All property rights and copyright are reserved to SCK CEN. In case of a contractual arrangement with SCK CEN, the use of this information by a Third Party, or for any purpose other than for which it is intended based on the contract, is not authorized. With respect to any unauthorized use, SCK CEN makes no representation or warranty, expressed or implied, and assumes no liability as to the completeness, accuracy or usefulness of the information contained in this document, or that its use may not infringe privately owned rights.


## Abbreviations

## Terminology
The following terminology applies for the designation of components and subsystems within the Cryogenic System.


## Terms and Definitions

## Table of Figures
Figure 1. Overall layout of the Cryogenic System	14

Figure 2. View of the buildings related to the QPS.	15

Figure 3. Simplified representation of a single QCELL (inside dotted line) as seen by the QPLANT. Temperatures and pressures shown are indicative of the 2 K Operation scenario.	16

Figure 4. Simplified Process Flow Diagram of the QPS.	18

Figure 5. QPS - Control and Interlock related systems	20

Figure 6. Cryogenic User Circuitry Model for steady-state analysis.  Simplified representation of the QDB and QMs as seen by the QPS.	27

Figure 7. Cryogenic User Transient Model for transient analysis.  Simplified representation of the QDB and QMs as seen by the QPS.	27

Figure 8. Operational Scenarios and their transitions of the QPS.	30

Figure 9. Warm Helium Storage (WSH), showing the Helium storage vessels covered under Contingent Part #2.	60

Figure 10. Preliminary arrangement and indicative pipe sizes of the QLM at the QRB-QLM connection.	67

Figure 11. Reference Architecture of the Cryogenic Control System	70

Figure 12. MIT Reference Architecture	72


## Table of Tables
Table 1. Overview of Helium process lines of the QPS.	17

Table 2. Applicable Documentation (AD)	23

Table 3. Steady State Operational Scenarios	28

Table 4. Transient Operational Scenarios	29

Table 5. Indicative LHe Filling and Emptying Demand.	31

Table 6. Operational Heat Load Ranges.	33

Table 7. Operational Flow Conditions.	33

Table 8. Design Cooling Capacity - Heat loads and liquefaction demand.	34

Table 9. Design Flow Conditions at the QRB interfaces.	34

Table 10. Reliability performance requirements	38

Table 11. Maintenance Windows	39

Table 12. Temperature measurement accuracy	46

Table 13. Instrumentation tags.	48

Table 14. Minimum Process Instrumentation for the WCS	54

Table 15. Minimum Process Instrumentation for the QRB	59

Table 16. He Leakage limits	62

Table 17. Helium Inventory at the Cryogenic Users (for LINAC_30)	63

Table 18. Site Environmental Conditions	79

Table 19 Compressor room (CCB) electrical supply and load constraints	81

Table 20 Cold Box Room (AUB) electrical supply & load constraints	81

Table 21 Softened water quality parameters used for closed loop filling	83

Table 22 Provisional contract execution milestones.	117

Table 23. Asset Management and RCM standards	128

Table 24. Pressure Equipment and Safety Standards	129

Table 25. Functional Safety & Control Standards	129

Table 26. Cleanliness and Purity	129

Table 27. Lumped cold mass composition for the Cryogenic User Transient Model.	133

Table 28. Static heat loads for the Cryogenic User Transient Model	133

Table 29. Specific enthalpy (weighted average) of the lumped masses  for the 1 K to 300 K.	133

Table 30. Instructions for GSHRC [AD_04].	134

Table 31. Control Architecture details	135


# Introduction
MINERVA is the “Phase 1 Implementation” of the MYRRHA programme. It focuses on the design, construction, and commissioning of a 4 mA 100 MeV super-conducting continuous-wave proton Linear Accelerator (LINAC), a Proton Target Facility (PTF), and a Full Power Facility (FPF). Phase 2 of the MYRRHA program will be the extension to 600 MeV.


# The LINAC
The ~160 m long LINAC consists of a normal-conducting injector followed by a superconducting section. The superconducting section accelerates protons from 17 MeV to 100 MeV using 352.2 MHz single-spoke cavities operating at 2 K. Each Cavity (CAV) is submerged in saturated superfluid helium (He II) within a helium tank. Two cavities are integrated into one Cryomodule (QM), which is connected to a dedicated Cryogenic Valve Box (QVB). The combination of one QM and one QVB is referred to as a Cryo-Cell (QCELL).

The MINERVA implementation is staged in two steps:

LINAC_24: Initial deployment comprising a LINAC configuration with 24 QMs.

LINAC_30: Full deployment comprising a LINAC configuration with 30 QMs.


# The MINERVA Cryogenic System
The MINERVA Cryogenic System can be decomposed into four main blocks (Figure 1):

Cryogenic Plant & Storage (QPS),

Cryogenic Distribution Backbone (QDB),

Warm Pipping System (WPS)

Cryomodules (QMs).

The QPS provides the refrigeration power and storage capacity. It consists of the following subsystems:

QPLANT: the Cryogenic Plant itself, subdivided into

WCS: Warm Compressor Station

QRB: Cold Box Station

Storage systems

WSH: Warm Helium Gas storage.

QSN: Liquid Nitrogen Storage (if required by the Contractor’s design)

The QDB distributes the cryogenic fluids between the QPS and the QMs. It consists of the following subsystems:

QLM: Main Cryogenic Line, housing the main distribution headers at multiple temperature and pressure levels

QVBs: String of Cryogenic Valve Boxes for controlling the mass flow supplied to each individual QM.

QVE: End Box, acting as the return module for excess helium mass flow.

The QMs house the superconducting cavities to be cooled. The combination of one QM and its associated QVB forms a Cryogenic Cell (QCELL), which acts as a single functional unit regulating its own helium mass flow consumption by extracting flow from, and returning flow to, the main distribution headers.

Figure 1. Overall layout of the Cryogenic System

The MINERVA Cryogenic System is distributed over different areas (Figure 2):

For the QPS:

Compressor Room: Location of the Warm Compression Station (WCS)

Storage Area (outside): Location of the storage vessels (WSH and QSN).

Cold Box Room: Location of the Cold Box Station (QRB).

Connecting rooms: Multiple locations for routing the Interconnecting Warm Lines between the WCS and the QRB.

For the QDB and QMs:

LTU (LINAC Tunnel): Location for the Cryomodules (QMs), Valve Boxes (QVBs), End Box (QVE), and part of the Main Cryogenic Line (QLM).

Figure 2. View of the buildings related to the QPS.

The document “QSYS Conceptual Design Report” (SCK CEN/98143064) provides a preliminary, partially obsolete overview of a potential QSYS design and architecture. The document is included exclusively for contextual purposes and shall have no contractual validity, relevance, or binding force.


# QPS Users
The QPS Users are divided into two groups:

The Cryogenic Users, represented by the QCELLs and associated cryogenic equipment,

The External Dewar Users, withdrawing helium via dewars and returning it via a dedicated line.

The primary purpose of the QPS is to satisfy the operational requirements of the Cryogenic Users. External Dewar Users represent an auxiliary demand that does not govern the design basis of the QPS.


# Cryogenic Users
The Cryogenic Users consists of the QMs equipment and associated cryogenic distribution (QDB). From the perspective of the QPS, the operational behaviour of the Cryogenic Users is dominated by the QCELLs (QM + QVB).

Each QCELL interfaces with the QPS through the designated helium process lines A, B, D, E, and W. Figure 3. provides a simplified representation of a single QCELL as seen by the QPLANT. The QPS supplies refrigeration and liquefaction capacity to the QCELLs through three main helium circuits:

CAV Circuit (Header A to B)

TS Circuit (Header D to E)

CPLR Circuit (Header A to W)

The CAV Circuit provides cooling of the cavity cold masses.

Represents an (predominantly) isothermal refrigeration load, consisting of both static and dynamic heat loads.

Nominal cavity bath temperature: 2 K, saturated liquid helium.

Vapour quality at bath inlet: ~17 % (two-phase helium).

Vapour quality at bath outlet: 100 % (saturated gaseous helium).

During LHe filling, the cavity bath is filled via a dedicated filling valve.

The TS Circuit provides cooling of the thermal shield masses.

Represents a non-isothermal refrigeration load, consisting of static heat loads.

Operates at a significantly higher helium pressure than the CAV Circuit.

The nominal supply pressure and temperature levels will be determined by the QPS design as part of its overall efficiency optimization.

The CPLR Circuit provides thermalization of the RF couplers.

Represents a non-isothermal liquefaction load, consisting of static heat loads.

The operational demand is characterised primarily by helium mass flow consumption rather than fixed temperature setpoints.

Operates over a wide temperature range, from approximately 5 K at the cold end to near ambient temperature at the warm end.

During cooldown and warm-up, the QCELLs autonomously limit temperature gradients and ramp rates via its dedicated control valves. Each QCELL contains electrical heaters for:

Supporting controlled warm-up operations.

Evaporating residual liquid helium.

Simulating dynamic heat loads.

Figure 3. Simplified representation of a single QCELL (inside dotted line) as seen by the QPLANT. Temperatures and pressures shown are indicative of the 2 K Operation scenario.


# External Dewar Users
The External Dewar Users represent other users of the MINERVA facility that require LHe supplied in dewars for experimental purposes.

External Dewar Users may withdraw liquid helium from the QPLANT on a non-continuous basis via dewars. Returned helium is in the form of clean room-temperature gaseous helium (GHe) routed to the QPLANT via a dedicated recovery line.


# Process Flow Diagram and He process lines
An indicative Process Flow Diagram of the QPS is shown in Figure 4, with Table 1 providing a functional description of the main process and interface helium lines.

The helium process lines define the functional boundary between the QPS and the QPS Users. In normal operation:

The W line is the only warm return line and represents the net liquefaction load seen by the QPS. Under nominal conditions, ≤5 % of the helium supplied to the QCELLs via the A-line is returned to the QPS through the W-line.

The U line is a utility supply line providing warm gaseous helium for purging and auxiliary operations. It does not participate in the closed cryogenic cycle during normal operation.

The S line is a safety recovery line intended for abnormal operating conditions (e.g. minor QCELL overpressure events). It provides a controlled return path for discharged clean helium to the QPS, where it is recompressed and reintegrated into the main cycle, thereby preserving the helium inventory.

The G10 and G20 lines provide the supply and return paths for External Dewar Users.

Table 1. Overview of Helium process lines of the QPS.

* Line participating in the main cryogenic refrigeration cycle.

Figure 4. Simplified Process Flow Diagram of the QPS.


# The Control & Interlock System and IT infrastructure.
The MINERVA facility contains a hierarchical control and interlock architecture comprising the following elements:

MINERVA IT Infrastructure (MIT): System providing the supporting IT infrastructure for the entire facility. For the QPS, it provides services such as user authentication, standard network backbone, etc.

MINERVA Control and Interlock System (CIS), consisting of:

MINERVA Control System (MCS): System for the control and monitoring of all accelerator components, including the WPS, QDB, and QMs.

MINERVA Interlock System (MIS): System for the execution of machine and personal protection interlocks. It is subdivided into:

Device Interlock System (DIS): System specific for machine protection. It communicates any machine protection relevant interlock between the QPS and other systems (e.g. loss of cooling water from the SCK CEN infrastructure).

Personnel Protection System (PEPS): System specific for personal protection. It communicates any personal protection relevant interlock between the QPS and other systems (e.g. oxygen deficiency events).

The QPS has its own control and interlock system, referred to as the “QPS Control & Interlock System” (QPS:CIS). The QPS:CIS will manage all internal process operations and local safety functions (e.g. WCS PLC, QRB PLC, WSH PLC, …), as well as include the associated SCADA system.

Figure 5. QPS - Control and Interlock related systems


# Nature of the Procurement

# Scope of Work by the Contractor
The Contract scope covers all services required to design, build, and commission a fully functional QPS (including e.g. QPS:CIS) in compliance with the requirements stated in this document.

The scope of work includes, but is not limited to, the following activities:

Design & engineering

Manufacturing, procurement

Transportation and on-site installation

Stand-alone commissioning and testing

Quality Assurance and Control activities

Training & Competence transfer

Support service

N.B.: Integrated commissioning activities that involve end-user participation (e.g. CIS interfacing or operational acceptance testing by SCK CEN personnel) are outside the Contractor’s scope.


# Scope of Supply by the Contractor

# Fixed Scope
One (1) fully functional “Cryoplant & Storage System” (QPS), including

One (1) QPLANT, which shall be:

Fully operational

Fully operational for (sporadic) supply/return to/from External Dewar Users.

One (1) Warm Storage Helium System (WSH), which shall:

be fully operational

exclude the Helium gas storage vessels (Contingent Part #2)

One (1) LN2 Storage System (QSN), if required by the Contractor’s design.

All associated components, such as

support structures and access equipment (e.g. ladders).

insulation vacuum equipment and instrumentation (pumps, gauges, etc)

internal interconnecting piping for the QPS (e.g. between WCS, QRB, WSH, etc)

One (1) complete Control and Interlock System for the QPS (QPS:CIS)

All Helium inventory and LN2 inventory (if applicable) required by the QPS itself during performance of the Contract, including any replenishment required during this period.

Full documentation package


# Contingent Parts
Strategic spare parts for the first 5 years of operation.

Helium gas storage vessels for the Warm Storage Helium (WSH)

N.B.: There is no order/preference assumed for the contingent parts.


# Applicable Documents
SCK CEN will provide the documentation necessary for the performance of the Contract as outlined below. The level of maturity provided at the current stage suffices for the Applicant to put forward an offer. During performance of the Contract, SCK CEN will provide the final documentation to which the Contractor must adhere.

Table 2. Applicable Documentation (AD)


# Technical Requirements

# General Requirements
The technical requirements imposed by SCK CEN applicable to the development, performance, and quality (e.g. inspections, tests) of the procured items are specified in the present document and all other documents referred to herein. These requirements include, but are not limited to, norms and other standards, processes, and their parameters. All such requirements are mandatory, unless adjusted in accordance with the principles set forth in the subsequent paragraphs.

The Contractor shall be fully responsible for ensuring that the Deliverables and Services provided fully meet the specified requirements for the Contract.

In accordance with §1.11 of the Main Tender Document, the Contractor shall not rely on any alleged lack or insufficiency of information after submission of its offer.

In accordance with § 1.13 of the Main Tender Document, the Contractor may no longer rely on information lacking after the deadline for submitting questions.

Any lack of information during the performance of the Contract shall not constitute grounds for a Variation.

The Contractor shall be fully responsible for the correct definition and execution of all activities (including, but not limited to, engineering, manufacturing, packaging, transportation, delivery, installation, testing, commissioning, QC, QA) necessary to duly perform the Contract and to ensure that (each item in) the Contractor’s scope of supply and (each activity in) the Contractor’s scope of work duly meet the requirements imposed on them.

For some activities, specific requirements are imposed by SCK CEN which the Contractor shall adhere to.

For other activities, the Contractor shall define the appropriate requirements themselves based on the functionality of, as well as the performance requirements imposed on, thereby considering the operational circumstances to which the QPS is subject. In this case, the Contractor shall duly consider all relevant information regarding such functionalities, performance requirements, and operational circumstances as was expressly made known to the Contractor by SCK CEN or could have reasonably been inferred by the Contractor on the basis of its expertise and experience. Any such requirements, defined by the Contractor (regardless of whether they have been included in the Contractor’s Offer or defined during one of the Contractual Phases and accepted by SCK CEN, shall be adhered to thenceforth; any change to such requirements shall be subject to prior written SCK CEN approval.

The Contractor shall be responsible to obtain the corresponding documents for referenced norms, standards, etc.

In the offer, the Applicant shall explicitly confirm that:

All SCK CEN’s Tender Documents have been duly analysed

The information provided therein is considered sufficient to allow the Applicant to submit a compliant proposal ensuring that the supplied items meet the specified requirements.

Any missing or insufficient information identified has been formally notified to SCK CEN without undue delay, in accordance with §1.13 of the Main Tender Document.

In the offer, the Applicant shall submit separate and explicit lists for each of the following cases. Each item listed shall be supported by a clear description and duly justification in the offer.

Any additional requirements defined by the Applicant (beyond those specified by SCK CEN), which are considered necessary to fulfil the intended function, performance, or integration of the proposed solution.

Any assumptions which have been defined by the Applicant, which are considered necessary to evaluate the offer.

Any deviation of the specified technical requirements, including the proposed alternative solution. This shall include, but is not limited to, any deviations from requested norms, standards, or preferred process parameters.

Any suggested modifications vis-à-vis the technical requirements as imposed by SCK CEN; such suggestions shall be presented for consideration only and shall not be treated as deviations. Suggested modifications should, in the Applicant’s opinion, constitute an improvement in terms of cost, reliability, safety, ease of use, or other functional aspects of the QPS. Each suggested modification shall be supported by an assessment of its advantages and drawbacks.

In the offer, the Applicant shall:

Submit a single, consolidated proposal, inclusive of all proposed deviations, representing the most optimal solution compliant with all conditions and requirements of the Contract. Multiple alternatives shall not be permitted.

Provide a clear overview of the (sequence of) activities that shall constitute the Contract performance. For each step in the sequence, the Applicant is to provide information regarding i.e. how the applicable requirements shall be met, the chosen process(es) and technique(s) that shall be implemented, etc.

Provide, as a minimum, the level of detail explicitly requested in the present document. Where no level of detail is specified, the Applicant shall determine and provide an appropriate level of detail based on its experience, proportionate to the criticality and/or complexity of the activity.

Any deviations or modifications shall require prior written approval by SCK CEN to be implemented.

During negotiations (if any), identified deviations and suggested modifications shall be discussed between SCK CEN and the Applicant. SCK CEN reserves the right to accept or reject any deviation or modification at its sole discretion and without justification.

SCK CEN’s shall only consider deviations or modifications that are explicitly identified as such in the Applicant’s offer in a dedicated section as required according to the mandatory structure of the offer as defined in § 1.9 of the Main Tender Document.

SCK CEN’s acceptance of the Applicant’s offer shall not imply acceptance of any deviations or modifications that have not been duly identified. Any such deviations or modifications shall be treated as Non-Conformities, for which the Contractor shall be responsible to duly correct and implement the necessary solutions during Contract performance, at its own risk and expense. Such Non-Conformities shall not constitute grounds for a Variation.


# Applicable Units
All technical documentation, calculations, drawings, and performance data submitted under this Contract shall:

Use SI units for all performance data, calculations, and operating parameters.

State all pressure values as absolute pressure in bar(a).

If alternative units are used, provide the corresponding values in SI units, which shall prevail in case of discrepancy.

Component nominal sizes and internationally recognised standard designations (e.g. NPS, ANSI ratings) may be stated in their standard form.

Use alternative units only with prior written approval by SCK CEN.


# Process and Functional Requirements

# Design and Operational Conditions
The QPS design shall comply with the specified Design Conditions and Operational Conditions (flow, heat loads, etc), as defined in this document. These are defined as follows:

Operational Conditions: Conditions expected during actual operation of the system, derived from cryogenic process specifications.

Design Conditions: Conservative or hypothetical conditions to be used for sizing purposes, which may differ from actual operational conditions.

For the QPS design, the Contractor shall:

Apply all Design and Operational Conditions, as specified hereafter.

For each sizing, verification, and/or engineering calculation, clearly indicate the type of condition used (Design or Operational). Any assumptions or engineering conditions, which the Contractor has adopted for the design in addition to the Design and Operational Conditions specified by SCK CEN, shall also be clearly put forward.

The QPS shall be sized in accordance with the following Design Conditions:

QPLANT Design Point

Design Conditions of 2K-OP (2 K Operation) in accordance with §4.2.4 “Cooling Capacity”

QPLANT Standby Point

Design Conditions of 2K-SB (2 K Standby) in accordance with §4.2.4 “Cooling Capacity”

WSH Design Point

Design Conditions in accordance with RTM-241, §4.4.5.2 “WSH Requirements”

QSN Design Point

Design Conditions in accordance with §4.4.6 ”Liquid Nitrogen Storage (QSN)”

The Contractor shall determine the QPLANT Maximal Point for the QPS, in accordance with RTM-044, §4.2.4 “Cooling Capacity”.


# Simplified User Models
The QPS design shall assume the specified Cryogenic User Circuitry Model (Figure 6), which represents the steady-state behaviour of the user’s circuitry.

The CPLR Circuit has the liquefaction load defined by the mass flow consumption “m_CPLR.”

The CAV Circuit has the heat loads “Q_CAV” at the cavities and “Q_B” at the return header.

The TS Circuit has the heat load “Q_TS” at the Thermal Shield, including supply and return headers.

The boundary conditions are specified in Appendix 11.1.

The respective heat loads and mass flows are specified in §4.2.2 for Operational Conditions and §4.2.4 for Design Conditions.

The QPS design shall assume the specified Cryogenic User Transient Model (Figure 7), which represents the temperature-dependent transient behaviour of the user cold masses.

The CAV mass is represented as a lumped thermal mass receiving heat loads from the Thermal Shield mass via radiation and conduction.

The TS mass is represented as a lumped thermal mass receiving heat loads from ambient via radiation and conduction.

The temperature-dependent properties of the masses and heat loads are specified in Appendix 11.2.

Figure 6. Cryogenic User Circuitry Model for steady-state analysis. 
Simplified representation of the QDB and QMs as seen by the QPS.

Figure 7. Cryogenic User Transient Model for transient analysis. 
Simplified representation of the QDB and QMs as seen by the QPS.


# Operational Scenarios and Transitions
The Contractor shall define and implement all necessary QPS operational scenarios and transitions.

This shall include, at minimum, all operational scenarios and transitions specified in section §4.2.2.

The Contractor may subdivide scenarios into intermediate operational steps, as required by its design for control or sequencing purposes.

All QPS operational scenarios and transitions shall be integrated into the QPS design and control system and shall:

Enable controlled operation in each specified scenario and transition.

Provide, via the QPS:CIS, the scenario execution status, including at minimum the active scenario identifier, current sub-step identifier, readiness-to-proceed status, and hold/abort status.

For each operational scenario and transition, the Contractor shall define the interaction with the Cryogenic Users in terms of the QPS behaviour and constraints. At minimum, this shall include:

The boundary conditions and operational constraints imposed by the QPS at each user interface.

The interface process variable envelopes and ramp limits that the QPS will apply for each scenario/sub step.

The QPS-provided readiness-to-proceed, hold, and abort conditions and their triggers.

The QPS interface behaviour during trips and recovery, including any constraints imposed on the Cryogenic Users.

The QPS state/status information and identifiers required to allow the user-side broker system to manage user actions based on QPS states.

The Contractor shall progressively define the detailed implementation of each specified operational scenario and transition during Basic and Detailed Design. This shall include, for each scenario and sub step, at minimum:

The sub steps, transition conditions, and the associated interface process conditions and control setpoint ranges

The control setpoints, alarm limits, and interlock thresholds


# Steady-State Operational Scenarios
The QPS shall implement the Steady State Operational Scenarios defined in Table 3.

For each Steady State Operational Scenario, the Contractor shall define the objective criteria for declaring the scenario as achieved and stable. At minimum, this shall include:

The controlled variables used for state declaration

The corresponding stability bands

The minimum duration over which the stability bands shall be satisfied

For each Steady State Operational Scenario, the Contractor shall specify the maximum sustainable cooling capacity available to the Cryogenic Users as resulting from the QPS design.

Table 3. Steady State Operational Scenarios


# Transient Operational Scenarios
The QPS shall implement the Transient Operational Scenarios defined in Table 4.

For cooldown and warmup scenarios, the Contractor shall provide and substantiate the following:

The conditions under which the QPS permits and/or initiates process flows to and from the Cryogenic Users.

The expected duration of each scenario and/or sub-step

The maximum refrigeration power the QPS can sustain at discrete temperature levels between 300 K and 4.5 K (e.g., 250 K, 200 K, 150 K, 100 K, 50 K, 4.5 K)

For cooldown and warm-up scenarios, the QPS design shall comply with the following design basis:

The Cryogenic Users may be cooled down and warmed up simultaneously or sequentially, as permitted by the QPS design

During scenarios CD-TS and WU-RT, the temperature difference between headers QRB.D and QRB.E shall be maintained within 50 K

For the 2K-RAMP scenario, the QPS design shall comply with the following design basis:

The 2K-RAMP scenario shall be a controlled transient between 2K-SB and 2K-OP, during which the Cryogenic Users’ heat loads are adjusted in a controlled manner between the standby (static) and the operational heat load level (static + dynamic).

The defined operational heat load level for 2K-RAMP shall be a “priming” setpoint; subsequent dynamic heat load variations during 2K-OP shall be significantly smaller than the heat load change applied during 2K-RAMP.

The QPS shall maintain the 2 K operating conditions within the specified interface envelopes throughout 2K-RAMP.

The Contractor shall define the permissible ramp rates and associated constraints for 2K-RAMP, including the maximum allowable rate of change of heat load (dQ/dt) and/or equivalent process variable ramps (e.g. mass flow), based on the QPS design and the Cryogenic User Circuitry Model.

In their offer the Applicant shall indicate and substantiate using the Cryogenic User Transient Model:

the expected overall cooldown time from 300 K to 2 K.

the expected duration for each cool-down Scenario Transition.

the expected duration of each warm-up Scenario Transition, and the resulting constraints on the warm-up rate and mass flow of the users.

the expected maximum refrigeration power the QPS can sustain at discrete temperature levels between 250 K and 4.5 K (e.g. 250 K, 200 K, 150 K, 100 K, 50 K, 4.5 K).

Table 4. Transient Operational Scenarios


# Transition between Operational Scenarios
The QPS shall implement the transitions between Operational Scenarios defined in Figure 8.

The Contractor shall verify each Transient Operational Scenario using the Cryogenic User Transient Model. At minimum, the Contractor shall:

Confirm that the installed cooling capacity is sufficient to accomplish the transients.

Estimate the time duration to accomplish the transients.

Specify relevant performance limitations (e.g. max. cool-down speed)

Figure 8. Operational Scenarios and their transitions of the QPS.


# Other operational scenarios

# Purging and Conditioning
The QPS shall implement operational scenarios for purging and conditioning of the QPS.

The Contractor shall provide documented procedures for purging and conditioning of the QPS. The procedures shall include, at minimum:

Instrumentation verification steps.

Specification of purge gas quality requirements

Definition of vent routing and discharge conditions

Defined acceptance criteria prior to cooldown (e.g. helium purity).

The purging and conditioning procedures shall be implemented as:

Automated control sequences (preferred method), or

Manual procedures protected by control-system interlocks.

In their offer, the Applicant shall state the type of procedure (automatic vs manual) they will implement.


# Startup preparation
The QPS shall implement operational scenarios for the startup preparation of the QPS.

The Contractor shall provide documented procedures for the startup preparation. The procedures shall include, at minimum:

Verification of instrumentation and control system readiness.

Verification of valve positions and isolation status.

Confirmation of purge completion and gas purity levels.

Verification of safety interlocks and protection systems.

Defined acceptance criteria prior to initiation of cool-down.


# LHe Filling / Emptying
The QPS shall allow the transfer of helium inventory between the QCELLs and the WSH.

The QPS shall autonomously manage the helium inventory during transfer operations within the defined operating limits.

Within the constraints in RTM-043, the QPS shall accommodate LHe filling and emptying consistent with the indicative demand specified in Table 5.

The values in Table 5 indicate the expected LHe filling and emptying demand of the cryogenic users

The terms filling rate and filling capacity refer to accumulated LHe at the cryogenic users.

The terms emptying rate and emptying capacity refer to the evaporated LHe at the cryogenic users.

During LHe evaporation, the QPS shall include provisions to safely accommodate transiently large helium return flows from the cryogenic users.

For the scenarios LHe filling and LHe emptying, the Contractor shall define and substantiate the operating limits supported by the QPS. At minimum, the Contractor shall define:

LHe filling rate

nominal operating range

maximum allowable value

LHe emptying rate

nominal operating range

maximum rate without loss of Helium inventory (all helium recovered by the QPS)

maximum rate with controlled loss of Helium inventory (partial venting of helium to atmosphere)

Table 5. Indicative LHe Filling and Emptying Demand.

† Corresponding to an average of ~0.8 g/s per QCELL.

In their offer, the Applicant shall state:

the expected duration of the LHe filling phase and the maximum continuous LHe filling rate the QPS can produce.

the expected duration of the LHe emptying phase and the maximum continuous emptying flow rate the QPS will be able to accommodate while preserving the helium inventory.


# Operational Condition Ranges
The Contractor shall design the QPS to accommodate the Operational Conditions specified in Table 6 and Table 7, for all applicable operational scenarios and configurations as anticipated by the Cryogenic User.

Table 6 specifies the Operational Heat Load Ranges

Table 7 specifies the Operational Flow Conditions at QPS interfaces

For headers D and E, the Contractor shall treat the provided pressure and temperature values as indicative nominal values.

The Contractor shall refine and document the final design values as part of its design optimisation.

The final design values shall comply with the following constraints:

Design pressure

The pressure at header D shall be within 12-17 bar.

The pressure difference between headers D and E shall be ≥ 1 bar.

Design temperature

The temperature at header D shall be within 30-55 K.

The temperature difference between headers D and E shall be within 20-30 K.

The QPS shall be capable of accommodating step changes in the cavity heat load Q_CAV during the 2K-OP scenario.

Each heat-load step change ΔQ_step shall have a value between -30 W and +30 W.

Each ΔQ_step shall be applied to the cavity heat loads Q_CAV in accordance with the Cryogenic User Circuitry Model.

Following each applied ΔQ_step, the QPS shall remain controllable and shall maintain compliance with the Operational Conditions specified in §4.2.3.

The Contractor shall confirm and refine the Operational Conditions during Basic and Detailed Design based on the final QPS design.

Any refinement shall remain within the specified enveloping ranges.

The Contractor shall comply with the following definitions regarding the Operational Conditions:

Range requirement

The ranges correspond to the expected operating envelope. This shall not be interpreted as requirements for installed cooling capacity, which is specified separately in §4.2.4.

Stability requirement

The maximum deviation from the operating value over a rolling time window  = 1 min, using the measurement location applied for scenario control and state declaration.

Heat Load Ranges

The lower bound excludes contingency margins

The upper bound includes contingency margins

In all operational scenarios, the QPS shall maintain the user interface process variables (temperature and pressure) within the specified interface envelopes.

Where installed cooling capacity is insufficient for a given load, the QPS shall maintain envelope compliance by reducing the attainable mass flow and/or slowing the transient.

Table 6. Operational Heat Load Ranges.

Lower bound excludes contingency; upper bound includes contingency

Table 7. Operational Flow Conditions.

‡ Indicative nominal value; the Contractor shall define the final values in accordance with RTM-035.

† Assumed ambient temperature.


# Cooling Capacity
The QPS shall comply with the Design Cooling Capacity specified in Table 8 in accordance with the Cryogenic User Circuitry Model. To this end, the QPS shall:

Provide sufficient installed cooling capacity to stably sustain the QPLANT Design Point.

Be capable of stable operation at the QPLANT Standby Point.

The Design Cooling Capacity in Table 8 shall apply at the Design Flow Conditions specified in Table 9 for the corresponding operational scenario and configuration.

The values in Table 9 shall define the Design Flow Conditions at the QPS user interfaces for headers A, B, D, E, and W, in terms of temperature, pressure, and mass flow rate.

For the Design Flow Conditions specified in Table 9, the applicable stability requirements shall be those specified in Table 7 for the corresponding operational scenario

The QPS shall be capable of continuous operation at the specified Design Cooling Capacity, while meeting the stability requirements defined in the operational conditions.

For the QPLANT Design Point, the QPS shall not rely on time-limited operating modes (e.g. compressor overspeed).

For the QPLANT Standby Point, the QPS shall not rely on continuous use of supplementary heat loads to maintain controllability.

The QPS design shall not include additional installed refrigeration or liquefaction capacity beyond that required to meet RTM-040 (Design Cooling Capacity) solely for the purpose of aiding or reducing the duration of Capacity-Constrained Operational Scenarios. Capacity-Constrained Operational Scenarios shall include:

All Standby Operational Scenarios, as defined in §4.2.2.1 and not covered by RTM-040

All Transient Operational Scenarios, as defined in §4.2.2.2

All Other Operational Scenarios, as defined in §4.2.2.4

The External Helium Withdrawal and Recovery, as defined in §4.4.8

The Contractor shall determine the “QPLANT Maximal Point” in accordance with the following requirements:

The QPLANT Maximal Point shall correspond to the highest continuous cooling capacity claimed by the Contractor for the as-built QPS.

The QPLANT Maximal Point shall apply to the same user configuration and boundary conditions as the QPLANT Design Point, but with the heat loads at the cavity circuit (Q_CAV) maximised.

In the offer, the Applicant shall:

Indicate the design temperature and pressure on headers D and E.

Table 8. Design Cooling Capacity - Heat loads and liquefaction demand.

Table 9. Design Flow Conditions at the QRB interfaces.

‡ Indicative nominal value; the Contractor shall define the final values in accordance with RTM-035.

† Assumed ambient temperature.


# Liquid Nitrogen Precooling (Optional)
The QPS design may include integration of liquid nitrogen precooling (LN2 Precooling) within the thermodynamic cycle of the QRB.

If LN2 Precooling is implemented, the Contractor shall be responsible to:

define all required LN2 interfaces with the site infrastructure.

provide all necessary mechanical, process, control, and safety interfaces.

fully design and supply the Liquid Nitrogen Storage System (QSN) in accordance with §4.4.6.

specify the expected LN2 consumption, including average, peak, and transient demand

specify the requirements for LN2 replenishment logistics, including filling interfaces, delivery conditions, and operational constraints.

include all associated equipment, instrumentation, control functions, and safety provisions within the QPS scope.

If LN2 Precooling is implemented, it shall:

Not compromise the ability of the QPS to remain safe under loss of LN2 supply.

Account for LN2 supply logistics, including delivery interruptions and pressure instabilities.

Provide an autonomy (e.g. storage capacity) of at least 14 days at the QPLANT Design Point.

In the offer, the Applicant shall explicitly state whether LN2 Precooling will be part of the QPS design.

In the offer, if LN2 Precooling will be implemented, the Applicant shall submit a quantified techno-economic justification substantiating the benefit of implementing LN2 precooling compared to an equivalent configuration without LN2 precooling. The justification shall, at minimum, include:

Capital cost (CAPEX) comparison and identification of the main cost drivers, including equipment, infrastructure, and integration costs.

Operating cost (OPEX) comparison (expressed in EUR for 10 years of operation) and identification of the main cost drivers, including LN2 consumption (average and peak), electricity consumption, and maintenance costs.

The logistics impact associated to the LN2 Precooling, including the expected delivery frequency, storage autonomy, and operational constraints of the LN2 supply.

The impact on the operational reliability and availability of the QPS.

The impact on the overall performance of the QPS.

In the offer, if LN2 Precooling will be implemented, the Applicant shall:

describe its functional role within the refrigeration cycle.

identify all required LN2 interfaces with the site infrastructure.

specify the required LN2 flow rate and operating envelope (pressure and temperature).

specify the expected LN2 consumption, including average, peak, and transient demand, for planning of LN2 supply and replenishment logistics.

specify the QSN storage capacity (tank volume), including the operational autonomy between LN2 deliveries under nominal consumption.

confirming that all contractual performance requirements remain satisfied.


# Abnormal event
The QPS design shall withstand abnormal events without compromising system integrity or personnel safety.

Abnormal events shall include, at minimum, any event affecting:

Electrical supply of the QPS

Cryogenic system of the QPS

Utilities supporting the QPS

Control and instrumentation systems of the QPS

The Contractor shall at minimum consider the abnormal events in this section (§4.2.6).

The Contractor shall identify, define, and implement all abnormal events applicable to the QPS.

The abnormal event implementation shall be based on recognised engineering practices and relevant operational experience.

For each abnormal event, the Contractor shall:

Define the design-basis envelope, including at minimum:

The severity of the event

The duration of the event

The criticality of the event

Where appropriate, subdivide an event into multiple levels of severity, duration, or criticality

Justify and document the selected assumptions in the Engineering File

The QPS design shall consider the following abnormal events affecting the electrical supply of the QPS:

LOOP: Loss of Offsite Power, in the following duration levels

LOOP_15m: LOOP for a total duration of up to 15min

LOOP_1h: LOOP for a total duration of up to 1 hour

LOOP_72h: LOOP for a total duration of up to 72 hours

Loss of electrical supply to the QPS:CIS

Loss of electrical supply to (at least) one warm compressor

Transient grid disturbances, including voltage dip or short-duration power interruption.

The QPS design shall consider the following abnormal events affecting the cryogenic system of the QPS:

For upsets or loss of operation

Loss of operation of at least one compressor (warm, sub-atmospheric, or cold)

Loss of operation of at least one expansion turbine

Unavailability of at least one Helium storage vessel

Loss of helium purity (e.g. air or moisture contamination of the process helium).

For incidents or failures

LOCA: Loss of Coolant Accident for any significant helium release due to rupture or major leak

Loss of Insulation Vacuum, in the following severity levels

Sudden and complete loss of insulation vacuum

Gradual or partial loss of insulation vacuum

Major internal helium discharge to the recovery system (e.g. activation of pressure relief devices)

The QPS design shall consider the following abnormal events affecting the utilities of the QPS:

Loss of cooling water

Loss of instrument air

The QPS design shall consider the following abnormal events affecting the controls and instrumentation systems of the QPS:

Loss of local control power to sensors or actuators

Loss of communication between distributed control subsystems

Failure of a critical sensor (e.g. pressure, temperature, or level measurement)

Failure of a critical control actuator (e.g. control valve or compressor control signal),

Loss of remote supervision while local control remains available.


# Global Design Criteria

# Lifetime
The QPS shall have a minimum service life of ≥40 years.

The QPS shall be capable of withstanding at least 50 complete warm-up and cool-down cycles during its service life.

A complete warm-up and cool-down cycle shall mean a temperature transition from 2 K to ambient temperature and back to 2 K.


# Availability & Reliability
The QPS shall apply industrially proven technologies and engineering processes with demonstrated operational experience in comparable systems. To this end, the Contractor shall:

Use components and subsystems with documented operational experience under comparable operating conditions.

Identify all critical equipment and subsystems.

Identify any critical equipment with limited operational experience and explicitly justify its selection.

Prioritise reliability and availability over performance optimisation in all design decisions.

Obtain prior written approval from SCK CEN before implementing any technology lacking demonstrated operational reference.

The Contractor shall perform an Availability & Reliability Assessment for the QPS. To this end, the Contractor shall:

Base the assessment on recognised RAM engineering practice and statistical modelling methods.

Define and document a failure classification methodology.

Identify all relevant failure modes at system and subsystem level.

Map each failure mode to a failure class.

Ensure that failure classification is based on operational consequences and recovery time.

Determine and state the MTBF and MTTR assumptions for each failure mode.

Document the complete assessment in the Engineering File.

The Availability & Reliability Assessment shall be based on a system-level reliability model representing the actual QPS architecture. The model shall, at minimum:

Represent the functional configuration of the QPS, including all redundancy arrangements (e.g. N+1 configurations).

Represent the dependency between subsystems forming functional chains.

Represent common-cause failures affecting redundant equipment.

Represent dependencies on utilities and auxiliary systems within the QPS scope.

Demonstrate the impact of single failures on the defined operational states.

The Contractor shall maintain and update the Availability & Reliability Assessment throughout the duration of the Contract. To This end, the Contractor shall:

Update the assessment following any design modification that significantly impacts availability or reliability.

Submit an updated assessment during at least at the end of the Conceptual Design and Detail Design phases.

Substantiate the MTBF & MTTR values using documented manufacturer data (OEM or COTS), validated field performance records, and/or recognized predictive reliability models.

Clearly state all assumptions, operating conditions, and statistical distributions used in the assessment calculations.

Identify components for which empirical data are not available and justify the modelling approach applied.

The Contractor shall include the following failure classes in its Availability & Reliability Assessment:

Class A – Failure of sustaining 2 K Operation

While operating in scenario 2K-OP, the failure causes loss of scenario 2K-OP.

Transition to scenario 2K-SB remains possible.

Full restoration to 2K-OP is achieved within 24 hours.

The temperature of each QCELL shall remain at or below the defined Thermal Shield temperature limit for the entire duration of the failure event.

Class B – Failure of sustaining 2 K refrigeration

The failure prevents sustained 2 K refrigeration by impeding scenarios 2K-OP or 2K-SB.

The scenarios 4K-SB or TS-SB remain possible.

Recovery from this failure is achieved within 5 days.

The temperature of each QCELL shall remain at or below the defined Thermal Shield temperature limit for the entire duration of the failure event.

Class C – Failure of sustaining cryogenic refrigeration

The failure prevents sustained cryogenic refrigeration by impeding scenarios 2K-OP, 2K-SB, 4K-SB, and TS-SB:

The QPS is forced to transition to scenarios RT-SB or WSTOP.

The temperature of each QCELL may exceed the defined Thermal Shield temperature limit during the failure event.

The QPS design shall comply with the following availability requirements:

The QPS shall sustain uninterrupted 2 K Operation (2K-OP) for at least 90 consecutive days.

The QPS shall sustain uninterrupted 2 K refrigeration (at least 2K-SB) for at least 12 consecutive months.

The QPS shall sustain uninterrupted cryogenic refrigeration (TS temperature or colder) for at least 5 consecutive years.

The QPS design shall comply with the reliability requirements defined in Table 10.

The reference period shall be the cumulative duration during which the QPS operates under the operational condition specified in the table.

The maximum allowable events represent the maximum number of failures permitted within the corresponding cumulative reference period.

Each failure event shall be assigned to one failure class only, based on the highest severity reached during the event.

Table 10. Reliability performance requirements

In the offer, the Applicant shall provide and thoroughly substantiate the expected MTBF values and associated recovery times. The substantiation shall include, at minimum:

The replacement philosophy (e.g. cartridge-based or modular replacement).

The capability for in-situ replacement without requiring Warm Stop, where claimed.

The isolation and serviceability concept (e.g. bayonet or valve-based isolation), where applied.

The maintenance intervention strategy supporting the assumed recovery times for Failure Classes A, B, and C.


# Maintenance strategy
The Contractor shall provide a Maintenance Plan for the QPS. The Maintenance Plan shall:

Be based on a Reliability-Centred Maintenance analysis

Be consistent with recognized asset management practices, including ISO 55000 and ISO 14224 where applicable

The Maintenance Plan shall include, at minimum:

A testing schedule, including inspection and replacement intervals

Recommended spare parts and minimum stock levels

Identification of critical components and long-lead items

The recommended maintenance strategy for each component (e.g. run-to-failure, time-based, condition-based)

Proof-tests intervals, where applicable

The QPS design shall be compatible with the maintenance windows defined in Table 11.

The maintenance interval represents the calendar duration of QPS operation after which a maintenance window shall be possible.

The maintenance duration represents the maximum time during which maintenance activities may be performed.

During the maintenance window, the QPS shall be able to remain in the specified operational state.

For any maintenance performed during 2K-OP, compliance with all 2K-OP criteria shall be always maintained.

Table 11. Maintenance Windows

The Maintenance Plan may include “online interventions” performed while maintaining the QPS within the applicable cold operational state and without requiring Warm Stop (WSTOP). Where such online interventions are proposed, the Contractor shall:

Identify all applicable components

Specify the operational state during which the online intervention is possible

The QPS design shall ensure that maintenance activities can be performed without unnecessary impact on availability, safety, or helium integrity. To this end, the QPS shall:

Permit isolation of serviceable subsystems prior to disconnection or opening.

Permit verification of leak-tightness prior to opening any cold or pressurised volume.

Enable controlled depressurisation, purge, and evacuation of local service volumes prior to intervention.

Prevent air ingress and contamination of the helium process during maintenance activities.

Ensure that maintenance interventions do not introduce uncontrolled pressure or thermal transients affecting adjacent subsystems.


# Energy-efficiency
The Contractor shall quantify the energy efficiency of the QPS by means of the inverse Coefficient of Performance (invCOP), as defined in §4.3.4.1. To this end, the Contractor shall:

Define and document the invCOP determination methodology

Document and substantiate the results

The Contractor shall guarantee and demonstrate compliance of the Contractual invCOP (invCOP_contract) in accordance with RTM-071.

The invCOP_contract shall correspond to the invCOP, as defined in §4.3.4.1, evaluated for the as-built QPS operating at the QPLANT Design Point, as defined in §4.2.1, under steady-state conditions.

The invCOP_contract shall comply with:

invCOP_contract ≥ invCOP_SAT + U_invCOP_SAT

Where:

invCOP_SAT is the value of invCOP, as defined in §4.3.4.1, determined during the SAT, in accordance with §4.13.3.

U_invCOP_SAT is the reported expanded uncertainty associated with invCOP_SAT, in accordance with RTM-077.

The terms invCOP_SAT and U_invCOP_SAT shall be expressed as absolute values in the same units as invCOP_contract.

The Contractor shall evaluate the invCOP for all steady-state operating scenarios, as defined in §4.2.2.1.

The Contractor shall report the evaluated invCOP at the end of each Contract Phase to reflect the evolving design.

Additionally, the Contractor shall evaluate the invCOP at the QPLANT Design Point and shall report any projected deviation from invCOP_contract.

In the offer, the Applicant shall state and substantiate the invCOP_contract.


# Inverse Coefficient of Performance (invCOP)
The invCOP shall be defined as:

invCOP = W_elec_eq / Q_4.5K_eq

Where:

W_elec_eq is the equivalent electrical input power, as defined in RTM-074

Q_4.5K_eq is the equivalent isothermal refrigeration load at 4.5 K, as defined in RTM-076

The equivalent electrical input power (W_elec_eq) shall include the electrical consumption of the totality of the QPS. This shall include, but is not limited to:

HP compressor system

Process vacuum pumping system (PVPS)

Cold compressor system

QPS insulation vacuum pumping system

QPS internal auxiliaries (e.g. valves, heaters, instrumentation, control cabinets)

If LN2 Precooling is implemented (§4.2.5), its contribution shall be included as equivalent electrical power (W_LN2_eq) in accordance with RTM-075.

If LN2 Precooling is implemented (§4.2.5), the Contractor shall include an equivalent electrical power contribution in the invCOP calculation based on fixed reference unit prices. To this end, the LN2 consumption shall be converted to an equivalent electrical power (W_LN2_eq) using:

W_LN2_eq = (m_LN2 · c_LN2) / (Δt · c_elec)

Where:

m_LN2 is the total LN2 mass consumed over the considered operating period [kg], including boil-off

Δt is the duration of the considered operating period [h]

c_LN2 is the reference market price of LN2 [€/kg] (including delivery to SCK CEN), set at 160 €/ton

c_elec is the reference electricity price, set at 180 €/MWh

The reference price for LN2 and electricity are fixed for the evaluation of the Offer as stated in RTM-075 but will be re-evaluated at the moment of the SAT.

The equivalent isothermal refrigeration load at 4.5 K (Q_4.5K_eq) shall include the useful refrigeration and liquefaction delivered by the QPS to the Cryogenic Users.

The Q_4.5K_eq shall include the contributions associated with headers A, B, D, E, and W at the QRB interface. The contribution of each individual header shall be reported.

The Contractor shall report the conversion method, assumptions, reference conditions, and equations used to determine Q_4.5K_eq.

The conversion method shall assume the reference state: temperature = 300 K; pressure = 1 bar.

The invCOP value shall be reported with its associated expanded uncertainty (U_invCOP).

The expanded uncertainty shall be reported at a confidence level of 95 %

The expanded uncertainty shall include all contributions associated with the determination method of the respective invCOP value, including but not limited to, any uncertainty arising from:

calculation or measuring methods

direct or indirect determination methods

experimental or analytical simplification methods

corrections, interpolations, or extrapolations


# Operational Capability Envelope
The Contractor shall define and document the QPS capability envelopes achievable by its design for the Steady-State Operational Scenarios.

The Contractor shall substantiate the declared capability envelopes by analysis using bounding operating cases; exhaustive mapping of the full operating domain is not required.

At minimum, the declared capability envelopes shall include:

The range of sustainable user demand, in accordance with the Cryogenic User Circuitry Model.

The minimum controllable operating condition (turndown)

The range of achievable flow condition at headers A, B, D, E, and W (pressure, temperature, mass flow)

The range of utility consumption (e.g. electrical power, cooling water)


# Subsystem Requirements
In the offer, the Applicant shall provide the key specifications of the main components.


# Common Parts and features

# Bellows, joints, and seals
The Contractor shall request approval from SCK CEN for the use of any mechanical Part, intended for thermal compensation at cryogenic temperatures, that forms part of the cryogenic process piping.

This requirement applies to the use of Parts such as (but not limited to) bellows, flexible hoses, or any other type of expansion joint.

Where applicable, the Contractor shall submit a duly justified request, supported (at minimum) by the following documentation:

A design justification demonstrating the technical necessity of the mechanical Part.

A risk assessment, with specific emphasis on the reliability of the mechanical Part.

A dedicated QAP addressing the implementation of the mechanical Part.

An intervention plan describing how the mechanical Part can be accessed and repaired in-situ.

In their offer, the Applicants shall

Indicate the quantity and location of expansion joints (if any) that are foreseen to be implemented in the cryogenic process piping.

If the use of (an) expansion joint(s) is anticipated, the Applicants shall provide for each type of expansion joint a (one) representative example of its implementation, including the aforementioned documentation (justification, risk assessment, QAP, and intervention plan).


# Helium guards
The Contractor shall design and implement helium guards to prevent air ingress on any non-welded seals that separate ambient air from sub‑atmospheric helium circuits. This shall include, but is not limited to:

Sealed flanges

Valve stems

Instrument connections

Sampling or purge ports

For each helium guard, the Contractor shall define and substantiate:

The nominal guard pressure

The allowable guard pressure range (including maximum allowable pressure).

The helium guards shall comply with the following requirements:

All helium guards shall be maintained above atmospheric pressure under all operating conditions.

Each helium guard shall consist of a “double-seal configuration,” where two seals form an intermediate space filled with guarding helium.

Use of an “enclosure configuration,” where a protective enclosure surrounding the Part is maintained with guarding helium, shall only be accepted if duly justified by the Contractor and subject to prior written approval by SCK CEN.

Each helium guard shall be connected to a dedicated guard supply line.

The guard supply lines serving the helium guards shall comply with the following requirements:

The main guard supply header shall be equipped with a remotely controllable valve to allow the restoration of the nominal guard pressure.

The guard supply lines shall be segmented, with each segment supplying one or more helium guards.

Each guard supply segment shall include:

Pressure sensors for remote monitoring of the guard pressure via the QPS:CIS

Isolation valves for the identification and localization of helium leaks.


# Venting lines
Where operation of any helium exhaust presents an asphyxiation risk, the Contractor shall route the corresponding exhaust outside the building via a dedicated vent line.

The need of each dedicated vent line shall be confirmed no later than the end of the Conceptual Design phase.


# Filters
The Contractor shall define the number and location of filters required to protect the QPS equipment.

All filters shall comply with the following requirements:

The filters shall be accessible for inspection, cleaning, or replacement.

The filters shall be designed such that particles or dust retained by the filter shall not fall into the connected piping during removal or replacement, including during maintenance operations.


# Support structures and access equipment
The QPS shall include all support structures and access equipment required for the installation, operation, inspection, and maintenance of the QPS. This shall include, at minimum:

Structural support for equipment and piping

Ladders

Access platforms

Walkways and handrails where required

Support structures and access equipment shall allow adequate access for inspection, maintenance, and replacement of major components.

Regarding the support structures, the Contractor shall:

Account for all relevant load cases (operational, maintenance, and exceptional) and installation tolerances.

Define the specifications and positions of interface points with the building structure required for the support structures. The Contractor shall share this information with SCK CEN as soon as practically feasible and not later than the completion of the Detailed Design Phase.


# Internal Interfaces and Interconnections
The Contractor shall be responsible for the complete definition, design, supply, installation, integration, and commissioning of all internal interfaces and interconnections within the QPS.

The QPS shall include all interconnecting piping, valves, instrumentation, electrical wiring, and control interfaces and interlock connections required for the complete and functional integration of all QPS subsystems. This shall include, at minimum:

all connections between WCS, QRB, WSH, and QSN

all connections to any subsystem forming part of the QPS.


# Common Instrumentation Parts
The Contractor shall provide and install all instrumentation required to:

Enable automatic control of all QPS operational scenarios.

Maintain safe operating conditions; and

Verify compliance with the specified performance criteria during acceptance testing.

The Contractor shall define the instrumentation layout and measurement ranges.

The Contractor shall submit this documentation to SCK CEN for review and approval during the Detailed-Design Phase.

The QPS instrumentation shall comply with the following requirements:

all measurements shall be continuously monitored

all measurements shall be remotely read by the QPS:CIS at a rate ≥1 Hz.

The Contractor shall document all instrumentation mounted within the insulation vacuum (e.g. within the cold box unit) in a photographic log per Instance such that its location can be clearly identified.

The photographic log shall provide evidence that the Instrumentation was installed correctly.

At minimum, the Contractor shall provide:

Overview photos (i.e. wide-view photos), showing the Instrumentation’s exact location

Close-up photo showing the details of all connectors (if any)

Close-up photo of each label

The Contractor shall submit a complete set of documentation containing at least:

calibration curves, power rating, location, and protection set points (where applicable).

the complete, as-built wiring diagram


# Valves
Cryogenic valves inside the QRB shall provide external tightness by metallic bellows sealing (or equivalent proven technology) over the full operating temperature range.

Where required by insulation thickness/thermal design, valves shall be provided with an extended bonnet/neck to maintain the actuator and stem seals within acceptable temperature limits

Automatic isolation valves used for helium (independent of temperature) shall be selected and qualified for the applicable process conditions and shall meet the specified tightness and safety requirements.

As a default selection, ball valves shall be used up to DN100 and butterfly valves above DN100. Deviations shall be justified by the Contractor (e.g. throttling duty, cryogenic tightness, cycling, cleanliness, fail-safe requirements).

Isolation valves shall be welded into the process pipework.

All control valves shall be equipped with:

Electro-pneumatic positioners

A position indicator, measuring continuous or discrete valve position when applicable, continuously monitored by the QPS:CIS.

Manual isolation valves that are safety-relevant or operationally critical shall be equipped with end-switches confirming their mechanical position (open/closed) during operation.

Two independent end-switches shall be provided per end position (open and closed).

The Contractor shall submit the list of such valves for SCK CEN approval during the Detailed Design phase.


# Electrical Heaters
The QRB shall include electrical heaters as required to:

Permit controlled warm-up of all relevant cryogenic circuits (including cryogenic distribution and Cryogenic Users where applicable)

Emulate user heat loads for stand-alone commissioning and acceptance testing of the QPS.

The installed heater capacity and control shall permit a controlled warm-up of the QRB circuits from cold to ambient temperature within 24 h.

The Contractor shall substantiate the warm-up capability by calculation.

The Contractor shall define, for each heater (or heater zone), the installed heating capacity and the physical installation location.

Real-time heater electrical power measurements (voltage and current, or derived power) shall be available to the QPS:CIS for monitoring, trending, and alarming.

Each heater (or heater zone) shall be monitored by at least one dedicated temperature sensor located to provide representative protection of the heated surface. The sensor signal shall be available to the QPS:CIS for monitoring and alarming.

The electrical power deposited by each heater shall have an accuracy of ≤ 5 %.

Heating elements required for normal operation shall either be replaceable without breaking the insulation vacuum or be implemented redundantly.

Each heater shall be mechanically attached and thermally bonded to its target surface such that the thermal contact remains effective for the full design lifetime of the QRB, including after thermal cycling.

The Contractor shall define the attachment method and acceptance criteria

The heaters and associated electrical wiring shall be designed to minimise parasitic heat loads to cold surfaces through appropriate thermalisation and optimised wiring routing and diameters.

Each heater circuit shall include at least one independent protection strategy to prevent overheating of the heated component and adjacent equipment under all operating modes and credible faults.

The protection strategy may be based on temperature, liquid level, or other monitored process conditions and shall be documented.

All heater circuits shall successfully pass a dielectric test in accordance with applicable IEC/EN standards at least directly after installation and during the SAT.

Heater power supplies shall be industrial COTS equipment and shall provide, at minimum:

Voltage and current measurement with accuracy ≤ 1%

Remote on/off control and status/diagnostics via the QPS:CIS;

Spare parts/support shall be available for ≥ 10 years.

Preferred nominal output voltage 24 VDC or 48 VDC, unless otherwise justified.

Protection against overload and short-circuit

Remotely readable breaker status and remote breaker actuation for diagnostics and control.


# Temperature sensors
The temperature measurements shall comply with the requirements specified in Table 12.

The specified accuracies shall apply to the installed measurement, including sensor element, mounting, thermalisation, wiring, and signal conditioning.

The Contractor shall design the installation (mounting and lead thermalisation) such that parasitic heat conduction and thermal gradients do not dominate the measurement uncertainty.

For each temperature sensor, the Contractor shall define the accuracy class (“standard” or “high”, as defined in Table 12.).

The Contractor shall submit a proposal for SCK CEN review and approval during the Detailed Design phase.

Table 12. Temperature measurement accuracy

For temperature sensors below 30 K, the temperature difference between the temperature sensor and the surface to be measured shall be below 0.05 K.

For temperature sensors below 30 K, the Contractor shall record their mounted location to ±1 mm accuracy in the QC report.

Thermometers assigned to protect an electrical heater shall be fitted within 1 cm from the heating element.

The cabling between each temperature sensing element and its associated signal conditioning device shall be designed and installed to ensure accurate, stable, and noise-immune signal transmission under all specified operating and environmental conditions.

The Contractor shall employ shielded, twisted-pair conductors or functionally equivalent solutions to minimise electromagnetic interference (EMI), preserve signal resolution, and enable compensation of lead resistance when required by the selected measurement method (e.g. 3-wire or 4-wire RTDs).

The Contractor’s selected cabling solution shall be justified by reference to recognised standards or design practices, such as IEC 60751, IEC 60359, ISA RP12.6, or other EMI mitigation guidelines accepted in industrial instrumentation.

Temperature elements outside cold boxes shall be mounted directly in the fluid stream, using a protection tube welded on the pipe.


# Pressure sensors (incl. vacuum gauges)
Each pressure transmitter shall be installed with at least:

one isolation valve to allow safe removal, calibration, or replacement without depressurizing the connected volume or interrupting vacuum operation

one dedicated connection for calibration or venting, also fitted with an isolation valve.

Each differential pressure transmitter shall additionally be equipped with a bypass valve and calibration valve.

The Contractor shall define the measurement ranges of all pressure instruments and submit them as part of Engineering File.

The accuracy of pressure measurements shall comply with the following requirements:

Absolute pressure accuracy: ±0.5% of the reading

Differential pressure accuracy: ±0.5 % of the reading

Long-term drift: smaller than ±0.5 % of the maximum span per year

Vacuum gauges shall cover the range from 10³ to 10-7 mbar

All pressure transmitters shall withstand, without de-calibration or damage, any pressure from vacuum up to the Operating Pressure defined by the relevant safety valve setting.

Vacuum gauges shall be capable of withstanding gas inrush without loss of calibration or mechanical damage.


# Liquid level sensors
The Contractor shall measure liquid-helium levels using superconducting level sensors.

The Contractor may propose alternative measurement technologies (e.g. differential-pressure sensors qualified for cryogenic service). In such case, the Contractor shall substantiate equivalence in performance and obtain SCK CEN approval prior to implementation.

The design, placement and operation of liquid-level sensors shall ensure that their readings are not influenced by:

bubbles generated by electrical heaters; or

flow turbulence or other hydraulic disturbances inside the vessel.

Liquid-level measurements shall comply with the following requirements:

The level readings shall be displayed to operators as a percentage of the nominal working volume.

The indicated value (including repeatability, hysteresis, and calibration drift) shall be accurate to:

± 0.5 percentage points of full scale for liquid helium; and

± 2 percentage points of full scale for all other cryogenic fluids (where applicable).

The liquid level sensor measurement range shall cover the full usable height of the vessel corresponding to the nominal working volume.

For each liquid level measurement, the displayed level value shall be based on a documented level-to-volume conversion.

The Contractor shall provide the level-to-volume function “volume = f (level)”, derived from the as-built geometry (as-built CAD), and identify the valid level range for the function.

The Contractor shall document the transfer functions used to derive the level reading in engineering units (e.g. mm and/or % of useful working volume) and the corresponding liquid volume (nominal working volume basis), including any non-linear vessel geometry effects.


# Helium flow rate sensors
The helium flow measurement instrumentation shall comply with following performance requirements:

Cryogenic helium flow measurements: accuracy better than ±5% of the calibrated span.

Room-temperature helium flow measurements: accuracy better than ±2% of the calibrated span.

The measurement range shall be selected such that the specified accuracy is achieved over the expected operating range.


# Helium Impurity sensors
The QPS shall include at least two dedicated gas analysers, installed in the following locations:

One gas analyser in the Compressor Room

One gas analyser in the Cold Box Room

The Contractor shall define which impurity measurements are implemented at each gas analyser location. The QPS shall measure, at minimum, moisture, nitrogen, and hydrocarbons.

Each gas analyser shall:

be equipped with a dedicated calibration line

be equipped with a purge or bypass capability for flushing the sampling lines

provide continuous measurement of impurities

trigger alarms on the QPS:CIS when measured concentrations exceed defined thresholds.

Each gas analyser shall have the following performance:

measurement range per impurity type: to be defined by the Contractor

measurement accuracy: ≤±1 ppm by volume across the entire range.

Long-term drift: ≤±1 ppm by volume per year.

Each sampling line shall have at minimum:

a pressure regulator

removable filter elements

a manual process isolation valve

a flow restriction or flow control device

The Contractor shall define the location of sampling points no later than the Detailed Design phase.

Where manual sampling points are provided (for ad hoc user sampling), the system shall be equipped with at least a manual process isolation valve and a plug.

Analysed gas samples shall be recovered and returned to the QPS.


# Instrumentation tags
The Contractor shall apply the following instrument and device numbering convention: “XX###,” where:

XX represents the tag prefix identifying the instrument or device type,

### represents a numerical identifier.

The first digit of the numerical identifier shall indicate the system association:

1 and 2 for QPLANT equipment

7 for QSH or WSH equipment

The second and third digits of the numerical identifier may be assigned according to the Contractor’s internal numbering practice.

The Contractor shall apply the tag prefixes defined in Table 13 for instrumentation and devices represented in P&IDs and control documentation.

All other instrumentation may follow the Contractor’s standard practice.

Table 13. Instrumentation tags.


# Warm Compressor Station (WSC)

# General Requirements
The Warm Compressor Station (WCS) shall provide helium compression across at least three pressure levels: VLP, LP and HP.

The WCS shall comprise the warm compression equipment required to establish and maintain pressure levels, including at minimum:

The HP compressor system, for compression from LP to HP

The Process Vacuum Pumping System (PVPS), for compression from VLP to LP.

Each compression stage shall include at least three compressors.

All compressors within the same compression stage shall be identical.

Each compressor motor shall be equipped with a variable frequency drive (VFD) rated for full load current of the motor.

The efficiency class of Motors and VFDs shall comply with Regulation (EU) 2019/1781.

The maximum vibration levels of the compressors and other rotating machines shall comply with ISO 2372 or its successor ISO 20816.

During the design phase, the Contractor shall submit a vibration-analysis report and calculation dossier.

During SAT, the Contractor shall measure the vibration using calibrated instruments and test methods in accordance with ISO 2954.

The sound pressure level of each compressor shall not exceed 80 dB at 1 m while in any steady-state operating condition.

The Contractor shall validate this by noise tests on each compressor and its electric-motor drive during FAT and SAT, in accordance with ISO 2151 or equivalent.

In the offer, the Applicant shall state and substantiate the expected noise levels at 1 m from each compressor.


# Compressors requirements
The compressor control strategy shall comply with the following requirements:

The VFD speed control shall be used as the primary means of capacity turndown

An internal slide valve shall be used as the trim-control element and to ensure stable operation across the operating range

The control strategy shall minimize power consumption under all load conditions.

Each compressor shall be capable of stable turndown to ≤ 30 % of the rated mass flow, without surge or recycle, over the specified operating-pressure range.

Each compressor shall include:

A bulk oil separator with an integrated first-stage coalescer installed directly downstream of the compressor discharge.

An oil-retention drip pan sized to contain the full oil inventory of the skid in the event of pipe rupture.

Downstream of the bulk oil separator, the oil concentration in the helium stream shall not exceed 100 ppm(w).

The flexible coupling between the electric motor and the HP compressor shall comply with API 671 / ISO 10441, or an equivalent standard.

In the offer, the Applicant shall:

State the number of LP compressors (PVPS units) and HP compressors

Confirm the long term sustainable operating frequency.


# WCS Valve Requirements
The WCS shall include bypass valves between each pair of pressure headers: HP to LP, and LP to VLP.

Each bypass valve shall be sized for at least 100 % of the maximum steady-state mass-flow rate of the corresponding compressor stage under the worst-case differential-pressure condition.

A control valve shall be installed in each of the following connections:

The connection from the helium-gas storage to the LP suction header, for loading.

The connection from the HP discharge header to the helium-gas storage, located downstream of the fine dust filter and the oil-charcoal adsorber.

Each helium connection between the WCS and the QRB shall include a control valve located within the WCS building.

The suction and discharge lines of each compressor stage shall be equipped with non-return valves that automatically close when the corresponding compressor stops.


# Coolers
Each cooler shall include on the gas circuit:

Purge valves suitable for draining and purging the gas circuits, including nitrogen blow-through or helium rinse-out, as applicable.

Each cooler shall include on the water circuit:

Purge and drain valves for draining the water circuits and purging air from them.

A control valve at the outlet for regulation of the cooling-water flow. The valve may be manual or thermostatic.

A manual water shut-off valve at the inlet.


# Oil
The oil-management system of the WCS shall provide, at minimum, the following functions:

Bulk separation of oil from the compressed helium gas immediately downstream of the compressor discharge.

Storage, thermal conditioning, and controlled supply of compressor oil to the lubrication and oil-injection circuits.

Retention of separated oil with sufficient residence time to allow gas disengagement, stable level control, and reliable oil supply.

The Contractor shall supply all compressor oil required for the initial filling.

The oil shall be a synthetic oil qualified for helium-compressor service, or an explicitly approved equivalent, compatible with the supplied compressors.

If an equivalent oil is proposed, it shall comply with the following requirements:

The particle size shall not exceed 25 µm.

The water content shall not exceed 100 ppm(v/v) for Polyalphaolefin (PAO) oils and 1000 ppm(v/v) for Breox-type oils.

The Contractor shall include, in the operation and maintenance manual, at minimum, the following oil-related information:

Detailed procedures for oil preparation, dehydration, and filtration.

The sampling frequency for routine oil analysis.

The specifications and acceptance limits for particle count, water content, and acid number.


# Oil-pump units
Each compressor shall be fitted with a dedicated, automatically controlled auxiliary oil-pump unit to maintain the minimum bearing-lubrication pressure during start-up, shutdown, and coast-down.

Each auxiliary oil-pump unit shall be equipped with:

Suction- and discharge-pressure transmitters

A flow switch interfaced to the compressor protection system


# Bulk Oil Separators and Oil Retention
Each bulk oil separator shall include a differential-pressure indicator across the internal separation element(s) to allow monitoring of fouling and separator performance.

Where the bulk oil separator also fulfils the oil-retention and oil-reservoir functions, it shall be fitted with an electric heater to preheat the retained oil prior to compressor start-up.

The Contractor shall provide suitable sampling points and agreed measurement procedures at the helium-gas outlet of each bulk oil separator to allow verification of oil carry-over during performance tests and long-term operation.

The helium gas at the outlet of each bulk oil separator shall have an oil content of ≤ 100 ppm(w) under all normal operating conditions.

This limit shall define the maximum inlet oil concentration for the downstream Oil Removal System (ORS).


# Oil filters
The compressor oil-filter system shall include, at minimum:

A duplex change-over filter, rated at 25 µm absolute, installed at the inlet of each compressor oil pump.

A fine oil filter installed upstream of the oil-injection points serving the compressor bearings and shaft seals.

Each oil filter shall be equipped with:

Manual isolation valves installed upstream and downstream, to permit maintenance and filter change-out.

A differential-pressure gauge providing visual indication of filter blockage.


# Oil Purge and fill-up
Each compressor shall be equipped with manual isolation valves in all relevant connecting piping to permit full circuit isolation for maintenance.

The oil piping and purge arrangement shall be designed such that all relevant piping has a slope greater than 1 % towards the designated oil traps, in order to prevent migration of oil into oil-free regions.


# Oil Removal and Helium Purification System (ORS/GMP)
The Warm Compressor Station shall include an Oil Removal and Helium Purification System (ORS/GMP) to remove compressor oil from the helium stream.

Under all operating conditions, including start-up and recovery operations, the residual oil content at the QRB interface shall not exceed 10 ppb(w).

The ORS/GMP shall comprise, at minimum

A coalescer system with multiple coalescing stages

A charcoal adsorber system

The instrumentation and diagnostics required to monitor and verify the oil-removal performance.

The Contractor shall provide the diagnostics and validated procedures required to verify the oil concentration, at minimum, at the following locations:

Downstream of the bulk oil separator,

Upstream of the last coalescing stage

Downstream of the charcoal adsorber system


# Coalescer system
The coalescer system shall comply with the following architectural requirements:

It shall be installed downstream of the HP primary oil-removal system.

It shall include at least three (3) coalescing stages installed in series.

The coalescer system shall comply with the following performance requirements:

It shall be sized such that the gas velocity through the coalescing elements is sufficiently low for efficient coalescence.

It shall include a gas-velocity margin of at least 20 %.

Downstream of the coalescer system, the oil content of the helium stream shall be below 0.5 ppm(w).

The coalescer assembly, including its sealing arrangement, shall be designed to withstand the compressor-induced vibration without unacceptable mechanical fatigue, loss of sealing integrity, or loss of fastener tightness.

Each coalescing stage shall be equipped with a standpipe and level measurement suitable for local and remote monitoring.

The last coalescing stage shall act as a guard stage.

The guard stage shall not be automatically drained.

The guard stage shall include an automatic oil-detection system integrated into the station shutdown architecture.

Any detection of oil in the guard stage shall trigger automatic shutdown of the compressor station.

The oil collected in the stages upstream of the guard stage shall be automatically returned to the compressor suction through motorized drain valves controlled by level instrumentation.


# Charcoal adsorber system
The charcoal-adsorber system shall comply with the following architectural requirements:

It shall be installed downstream of the coalescer system

It shall include at least one charcoal-adsorber vessel

It shall include a fine dust filter downstream of the charcoal bed to prevent charcoal particle carry-over

The helium flow through the charcoal adsorber shall be from top to bottom.

The charcoal-adsorber system shall comply with the following performance requirements:

It shall be sized with a gas-velocity margin of at least 20 %.

Downstream of the charcoal-adsorber system, the oil content of the helium stream shall be below 10 ppb(w).

The charcoal adsorber shall be filled only with cleaned and dried charcoal in the form of smooth pellets.

Irregularly broken particles shall not be used.

The bed filling shall be regular and shall not permit preferred helium flow paths.

The Contractor shall demonstrate that movement of the adsorbent and carry-over of dust particles are prevented.

This demonstration shall be supported by both design justification and relevant experience.

The Contractor shall supply:

All necessary equipment to fill the adsorber without degrading the adsorbent.

The heating unit necessary for drying the charcoal.


# Helium dryer
The helium dryer system shall comply with the following architectural requirements:

It shall comprise at least two identical helium dryers installed in parallel.

The arrangement shall provide operational redundancy.

The arrangement shall allow continuous drying of the full HP helium mass flow with one dryer in operation while the other dryer is in regeneration, maintenance, or otherwise unavailable.

The adsorbent material shall be a molecular sieve of alkali alumina-silicate (zeolite) or an equivalent material.

The helium dryer system shall comply with the following performance requirements:

It shall remove water from the helium stream to a residual concentration of less than 1 ppm by volume.

It shall generate a total pressure drop of less than 0.5 bar at nominal operating conditions.

Each helium dryer shall be dimensioned for the full HP helium mass flow contaminated with up to 50 ppm by volume of water for a duration of at least 12 h before regeneration is required.

The helium dryer system shall comply with the following regeneration requirements:

The regeneration of each helium dryer shall be performed by circulation of warm and dry nitrogen gas.

The regeneration time of each helium dryer, including cooling and return to service, shall not exceed 12 h.

Each helium dryer shall include:

Inlet and outlet valves.

A bypass circuit.


# Filters
The WCS shall include, at minimum, the following filters:

A wire-mesh filter with a retention rating of 100 µm at the suction side of each compressor.

A wire-mesh filter downstream of the charcoal adsorber, suitable for retaining charcoal-adsorbent particles.

A wire-mesh filter with a retention rating of 30 µm at the outlet of each helium dryer, suitable for retaining dryer-adsorbent particles.

Each filter shall include manual isolation valves on both sides to minimize contact with air during maintenance or filter replacement.


# Process Instrumentation
The WCS shall include, at minimum, the process instrumentation defined in Table 14.

Table 14. Minimum Process Instrumentation for the WCS


# Refrigeration Cold Box Station (QRB)

# General Requirements
The QPS shall include a Refrigeration Cold Box Station (QRB) responsible for producing the cooling power required by the cryogenic users and distributing the corresponding cryogenic flows to the QDB.

The QRB shall comprise, at minimum, the following subsystems:

A cold box unit (vacuum-insulated cryostat)

A dedicated insulation vacuum pumping system

Warm valve panels and associated instrumentation

Piping and valves required for purging and conditioning of all circuits

Electrical cabinets and local control units

Safety valves and relief devices

Helium guard circuits

Compressed-air distribution for pneumatic devices

Cooling systems for turbines and other auxiliary equipment

Access platforms and maintenance structures, including for all components located at elevated levels (i.e. components at the upper level of the cold box unit)

All external interfaces for utilities and auxiliary systems

Interfaces required to accommodate external helium withdrawal and recovery, as specified in §4.4.8

The cold box unit shall contain, at minimum, the following internal components:

Main Process Heat Exchangers

Expansion turbines

Cold compressors

Process piping

80 K dual-bed adsorbers

20 K single-bed adsorber

Helium phase separators at ~4.5 K and ~2 K

Cryogenic valves

Electrical heaters

Filters

Instrumentation required for operation, protection, and diagnostics

The Contractor shall be responsible to define the arrangement and orientation of the cold box unit.

The space constraints may favour a horizontal cold box configuration.

The interface between the QRB and the WCS shall comply with the following requirements on the QRB side of the interface

Each process line shall include an isolation valve.

The process lines (HP/LP/VLP) shall pass through designated wall sleeves and shall include provisions for thermal expansion compensation and removable spool pieces to allow maintenance access.

In the offer, the Applicant shall provide a preliminary 3D MODEL including the terminal points for the A, B, E and D lines.


# Main components

# Vacuum vessel(s)
The design of all penetrations connecting piping or instrumentation to the QRB vacuum vessel shall prevent condensation or frost formation at the external interfaces during all operational scenarios.

All ports carrying cold valves, turbines, transfer line connections, or instrumentation feedthroughs shall be fabricated from stainless steel. The vacuum vessel shell may be fabricated from mild steel.

The design of the pumping ports shall include provisions to prevent ingestion of multilayer insulation (MLI) into the vacuum pumping system.

The cold box unit shall include a vacuum barrier at the QRB-QLM connection (§4.5.1), located on the QRB side of the interface.

The vacuum barrier shall withstand a pressure difference of ≥3 bar in either direction.


# Main Process Heat Exchangers (MPHX)
The QPS Contractor shall be responsible for the selection, sizing, and detailed design of all Main Process Heat Exchangers (MPHX) installed inside the QRB.

The selected MPHXs shall ensure suitability for cryogenic helium service, including at minimum:

Pressure containment under all design flow conditions.

Resistance to thermal stresses during cool-down and warm-up.

Helium leak-tightness between process streams and towards the insulation vacuum.

The selected MPHX shall comply with the following manufacturing requirements:

If aluminium plate-fin heat exchangers are selected, they shall be

vacuum brazed

equipped with aluminium-to-stainless steel transition joints where applicable.

If stainless steel heat exchangers are selected, they shall be of fully welded construction.

For MPHXs operating below 20 K, each heat exchanger shall be arranged vertically with the warm end at the top to avoid density-driven maldistribution.

For MPHXs operating between 300 K and 80 K, the design shall incorporate provisions for controlled warm-up and regeneration of the high-pressure side to remove frozen moisture and impurities.

Each MPHXs shall incorporate instrumentation to measure the differential pressure between inlet and outlet to monitor the evolution of pressure drop during operation.

If LN2 Precooling is implemented (§4.2.5), the design shall include a dedicated MPHX between the nitrogen circuit and the HP helium stream, including at minimum:

All necessary outfit for integration with the LN₂ system, including matching male connection parts and suitable interfaces for safe operation and maintenance.

Design provisions that prevent nitrogen solidification under all operational and transient conditions, including scenarios involving unintended high mass flow of cold helium in the low-pressure return stream.

For each MPHX, the Contractor shall:

Specify the maximum allowable temperature differences across the HX

Define the operational controls/procedures required to ensure compliance with the specified maximum allowable temperature differences during all operating and transient conditions.

Define the operational controls/procedures for controlled warm-up and regeneration of the high-pressure side to remove frozen moisture and impurities.

In the offer, the Applicant shall describe the selected type of MPHX that will be used.


# Turbines
Each turbine shall be equipped with either gas-lubricated bearings or magnetic bearings.

If gas-lubricated bearings are selected, the design shall include

provisions to control labyrinth leakage

provisions to prevent excessive cooling of the bearing bushings

If magnetic bearings are selected, the design shall include

An emergency power supply or equivalent provision in case of electrical power failure.

A secondary mechanical support system (e.g. backup rolling bearings) to protect the machine in case of bearing control failure.

Each turbine shall be equipped with a continuous rotational speed measurement and an overspeed protection system.

The overspeed protection shall include alarm and automatic stop levels.

The turbine design shall include a brake system suitable to control the turbine rotational speed during cool-down and off-design operation.

The brake system shall reject the extracted power via a water-cooled heat exchanger.

Acceptable materials for the water channels are stainless steel and copper compatible with the water quality specified in §4.7.

The water channels shall provide easy access for inspection and cleaning.

Each turbine shall be equipped with a dedicated inlet gas filtration system to protect the wheel, nozzle, and bearing system from particulate contamination.

The filtration system shall be accessible for inspection and replacement.

The design shall allow in-situ replacement of each turbine cartridge without warming up the main heat exchanger blocks. To this end, the design shall include, at minimum:

Provisions to isolate, warm-up, purge, and coo-down the cartridge individually

The replacement of one turbine cartridge shall not exceed 3 hours under normal maintenance conditions.


# Cold Compressors
The cold compressors shall be of centrifugal type and be equipped with active magnetic bearings.

The magnetic bearings of the cold compressors shall include:

An emergency power supply or equivalent provision in case of electrical power failure.

A secondary mechanical support system (e.g. backup rolling bearings) to protect the machine in case of bearing control failure.

The bearing system shall allow to lower the rotational speed down to 30 % of nominal speed while remaining in the operational window.

The helium mass flow rate shall be adjustable by regulating the rotation speed via a Variable Frequency Drive.

For each cold compressor, the maximum allowable rotational speed shall include at least a 10% margin with respect to the highest speed required under all operational scenarios.

For each cold compressor, the Contractor shall provide:

A detailed cool-down and start-up procedure.

The compressor performance maps showing the pressure ratio as a function of the reduced flow for different reduced iso-speeds. The stall and choke limits shall be clearly indicated.

The design shall allow removal and replacement of each cold compressor without warming up the entire cold box. To this end, the design shall include, at minimum:

Provisions to isolate, warm up, purge, evacuate, and cool down the cold compressor independently from the main cold box.


# Helium phase separators
Two helium phase separators shall be installed in the QRB:

one operating at ∼2 K and connected to the cold compressors

one operating at ∼4.5 K.

Each helium phase separator shall be equipped with electrical heaters to:

Control and stabilise the liquid helium level,

Allow a controlled emptying of the liquid helium

Emulate the user heat load during stand-alone commissioning and acceptance testing of the QPS.

Each helium phase separator shall:

include a diffuser at the inlet.

be insulated with at least 30 layers of Multi-Layer Insulation.


# Adsorbers
The QRB shall include 20K and 80 K adsorbers to remove impurities. All adsorbers shall comply with the following requirements:

Each adsorber shall be equipped with a full mass flow bypass.

Each adsorber shall be equipped with gas analysis ports for monitoring adsorption performance.

Each adsorber shall be equipped with instrumentation to monitor the pressure drop across the bed.

The system shall provide fully automatic regeneration and cool-down of the adsorbers.

The QRB design shall allow easy access for periodic replacement of the adsorbent material.

The 80 K adsorber system shall remove air impurities, and shall comply with the following requirements:

Two 80 K adsorbers shall be installed and arranged in parallel to provide full redundancy.

Each adsorber shall operate at a temperature below 85 K.

Each adsorber shall be sized to purify the full HP compressor flow contaminated with up to 50 ppm by volume of air.

A dedicated bypass line shall be installed between the outlet of the switchable 80 K adsorbers and the QRB low-pressure line (QRB.LP), allowing direct helium purification including purification of QCELL return flow during conditioning operations.

The adsorption and regeneration cycle shall provide fully automatic switching of the adsorbers.

The adsorption and regeneration cycle shall allow uninterrupted QPS operation.

The 20 K adsorber system shall remove residual impurities (i.e. neon and hydrogen), and shall comply with the following requirements:

The adsorber shall operate at a temperature below 25 K.

The adsorber shall be sized to retain impurities corresponding to the full helium flow contaminated with ≤1 ppm by volume of hydrogen and ≤1 ppm by volume of neon for a duration of at least 200 hours.

The regeneration and subsequent cool-down shall take less than 12 hours.


# Filters
The QRB shall include, at minimum, the following filters:

A 10 µm wire mesh filter downstream of each adsorber.

A filter with a 10 µm retention rating shall be installed at the inlet of turbines.

A filter with a retention rating to be defined by the Contractor at the inlet of the cold compressors.

Filters installed in the QRB cold circuits shall be accessible from outside of the vacuum vessel for inspection, cleaning, or replacement.


# Dedicated insulation vacuum pumping system
The QRB shall be equipped with a dedicated vacuum pumping system for its insulation vacuum.

The pump-down of the QRB from atmospheric pressure to ≤10⁻⁵ mbar shall be fully automated and shall take less than one week.

The insulation vacuum shall be protected by a fast-acting isolation valve installed between the QRB vacuum vessel and the vacuum pumping system.

A dedicated connection point shall be provided between the turbo pump and the roughing pump for the connection of a helium leak detector.


# Process Instrumentation
The QRB shall include, at minimum, the process instrumentation defined in Table 15.

Table 15. Minimum Process Instrumentation for the QRB


# Warm Helium Storage (WSH)

# WSH Configuration
The Contractor shall supply the Warm Helium Storage (WSH) (Figure 9). The WSH shall be implemented in one of the following configurations:

WSH_FixedScope: fixed scope of supply, excluding the Helium gas storage vessels (Contingent Part #2).

WSH_FullScope: full scope of supply, including the Helium gas storage vessels (Contingent Part #2).

The configuration WSH_FixedScope shall be extendable to WSH_FullScope by means of adding Helium gas storage vessels only.

To this end, the WSH_FixedScope shall already include,

All predefined and physically implemented mechanical interfaces required for connection of the helium storage vessels

All predefined and physically implemented piping stubs, valves, and isolation provisions

All predefined and implemented electrical, control, and safety interfaces

All required space allocation and structural allowances for installation of the helium storage vessels

All implemented control and safety logic required for operation of the WSH_FullScope configuration

The transition from WSH_FixedScope to WSH_FullScope shall not require modification, rework, or interruption of already installed piping, equipment, structures, or control systems beyond planned installation and commissioning activities.

If WSH_FixedScope is implemented, the Contractor shall:

Specify the functional and technical requirements for the Helium storage vessels.

Specify the manufacturing requirements of the Helium storage vessels, such as surface cleaning, corrosion protection, inner-surface treatment (e.g., Rustol/Owatrol or equivalent), outer-surface coating, etc.

Figure 9. Warm Helium Storage (WSH), showing the Helium storage vessels covered under Contingent Part #2.


# WSH Requirements
The WSH shall fulfil, at minimum, the following functions:

Pressure balancing between the pressure sides of the WCS

Helium inventory management and buffering

Stabilisation of compressor suction pressure during transient events

Temporary storage of redistributed helium during cooldown, warm-up, and filling operations

Recovery and reintegration of helium discharged during abnormal events

Interface with helium purification, if applicable

Interface with external helium supply systems

The WSH shall include, at minimum:

Helium storage vessels (for configuration WSH_FullScope)

All associated instrumentation, valves, and control equipment

All necessary interfaces for external delivery of gaseous helium

The WSH shall be dimensioned to store the total helium inventory of the QPS and the QPS Users. This shall include at least the following Design Values:

The Helium inventory contained within the QPS, as specified by the Contractor

The Helium inventory contained within the LINAC in configuration LINAC_30, as specified in

Table 17

A Helium inventory of 50 kg for the External Dewar Users.

An additional contingency margin of ≥30 % on the total calculated inventory

The WSH shall consist of at least three (3) helium storage vessels.

The number of vessels shall be selected to ensure operational flexibility, maintainability, and robustness during cyclic operation and partial unavailability of vessels.

Each Helium storage vessel shall:

Be located within the designated outdoor Storage Area

Be oriented vertically

Include at least one inspection manhole for internal access during periodic inspection

Be provided with any ports required for purging, conditioning, and gas analysis

Each Helium storage vessel shall be equipped with:

A local pressure indicator

Instrumentation for measurement of temperature, pressure, moisture, and nitrogen contents, with remote read-out via the QPS:CIS

The WSH shall be equipped with:

Instrumentation for measurement of Helium pressure in the common vessel manifolds, with remote read-out via the QPS:CIS

Valves required for purging, conditioning, and gas analysis

The WSH design shall allow for controlled connection to the WCS lines. This shall include the capability for:

Automatic pressure regulation between compressor sides

Isolation of individual storage vessels

Selection and sequencing of storage vessels during operation

The WSH shall include a gas-management warm panel.

The panel shall allow local operation of valve switching, isolation, and vessel selection functions associated with the helium storage system.

The warm panel shall be integrated into the main control panel of the WCS.

The Contractor shall propose the final layout, volume, and positioning of the WSH during the Conceptual Design phase.

In the offer, Applicant shall describe the WSH implementation. At minimum, the offer shall include

The minimum total storage capacity

The minimum quantity of storage vessels

A conceptual layout of the WSH

A confirmation that the available space provisions at the outside Storage Area are sufficient for the proposed configuration


# Liquid Nitrogen Storage (QSN)
If LN2 Precooling is implemented (§4.2.5), the Contractor shall supply the Liquid Nitrogen Storage (QSN).

The Contractor shall size the QSN.

The storage capacity shall comply with §4.2.5.

The QSN shall include, at minimum:

liquid nitrogen storage tanks.

vaporizers and heaters, where required.

all interconnecting process lines and valves.

instrumentation and control equipment.

safety devices and pressure protection systems.

filling interfaces for LN₂ delivery.

all structural supports and ancillary equipment.


# Helium Inventory Management
The QPS shall minimize helium loss under all operating conditions, including failure modes.

In normal operation, the QPS shall lose no more than 1 Nm³ of helium per day.

The total instantaneous leak rate of the entire QPS shall be less than 1×10⁻⁵ mbar·L/s.

The Contractor shall implement a helium leak-detection and monitoring system in accordance with EN 13185:2001, Clause 6.2, or an equivalent methodology.

This shall include leak testing, leak monitoring, and automated isolation mechanisms where required.

The Contractor shall qualify the QPS for leak-tightness under operational and standby conditions.

The leak rates shall not exceed the values defined in Table 16. The values shall include all interconnecting piping, joints, and components operating at operating pressure and ambient temperature.

The QPLANT shall be dimensioned on the basis of the helium inventory required by the Cryogenic Users, as specified in

Table 17.

Table 16. He Leakage limits

Table 17. Helium Inventory at the Cryogenic Users (for LINAC_30)

In the offer, the Applicant shall quantify and substantiate:

The expected leak rates, expressed as annual helium loss percentage, per leak type and in total, including diffusive losses.

The helium leak-detection methods, pressure-hold test procedures, vacuum-decay or pressure-rise methodologies, and long-term monitoring techniques, including the corresponding acceptance criteria.

The post-installation and operational monitoring strategy, including thresholds and monitoring frequency.

The expected helium loss during conventional pump-down, purge, and conditioning operations for the QPS.


# LOOP
In case of LOOP, the QPS shall use the limited services (as defined in the respective sections) to avoid helium inventory loss while maintaining the safety of the installation.

In the offer, the Applicant shall provide an indicative design of the LOOP strategy, including:

The identification of the critical loads to be maintained under LOOP conditions.

The enveloping assumptions for the internal distribution logic, including switching, prioritization, and load-control schemes.

The configuration and internal routing of the limited utility supplies.


# Purging
The Contractor shall install all equipment and connections necessary to allow purging and conditioning of the QPS.


# Abnormal conditions
In case of QPS internal abnormal events, including those leading to abnormal conditions for the Cryogenic Users, no more than 1 % of the total helium inventory shall be lost.

The recovery concept shall cover all credible initiating events, including but not limited to LOOP, loss of vacuum, loss of instrument air, cooling-circuit trip, turbine trip, QRB trip, HP compressor trip, and PVPS trip.

Venting operations via safety valves shall discharge into line S.

Emergency transfer of inventory to WSH shall only be performed in accordance with approved safety procedures, with active monitoring and relief provisions in place.

In case of abnormal conditions at the Cryogenic Users, the QPS shall cope, without loss of inventory, with a helium flow returning through line QRB.S of:

≥200 g/s during normal operation of the QPS.

≥100 g/s during abnormal operation of the QPS, such as LOOP.

The QPS shall have a procedure to recover normal helium circulation once the initiated abnormal event is resolved.

In the offer, the Applicant shall present a high-level description of the helium recovery strategy including but not limited to

A Bill of Materials (BoM) of all recovery components (e.g. low-pressure gas balloon storage and/or high-pressure compressor-driven recovery and/or dedicated purification system).

The maximum flow that the QPS can accept from the S line.


# External Helium Withdrawal and Recovery
The QPS design shall include a Dewar Filling Station that allows External Dewar Users to (sporadically) withdraw LHe via dewars and to return GHe via a dedicated warm return line. To this end, the QPS shall include

All necessary infrastructure for the withdrawal of LHe to external dewars (the dewars themselves are not in scope of this Contract).

All necessary equipment and interfaces for the recovery of GHe via the dedicated line “G20” coming from the external WGR-MAC system.

The QPS shall serve the External Dewar Users using the installed cooling capacity as specified in §4.2.4.

No additional capacity shall be added solely to accommodate the needs of the External Dewar Users.

The QPS shall include all necessary equipment to protect its integrity, operational stability, and helium purity against disturbances originating from External LHe User systems.

The Dewar Filling Station and the interface to line G20 shall be located within the Coldbox Room.

The Contractor shall substantiate the design of the Dewar Filling Station in the Engineering File. At minimum, the substantiation shall include:

Mass and energy balance calculations

Quantification of LHe consumption associated to the Dewar filling operations, excluding the net liquid withdrawal delivered to the External Dewar Users

Assessment of the impact on overall QPS availability and operational stability, with particular emphasis on disturbances during 2K-OP.

Control logic and interlocks during Dewar filling operations, including Helium flow paths, pressure, and level control response.

Description of the control philosophy and interlocks during Dewar filling operations, including helium flow paths and pressure and level control response,

Definition and justification of acceptance criteria for operational parameters (e.g. pressure fluctuations), helium inventory impact, and helium purity.


# Dewar Filling Station
The Dewar Filling Station shall be designed to accommodate a mobile dewar with a nominal capacity of up to 500L.

Within the operational and boundary constraints defined in RTM-264, the Dewar Filling Station shall be designed to accommodate the following LHe filling requirements:

Filling demand during active Dewar User campaigns

Peak demand: A sporadic net withdrawal of up to 200 L of LHe at the start of Dewar User campaign

Nominal demand: An average net withdrawal of 50 L of LHe per day throughout the duration of a Dewar User campaign.

Net withdrawal definition

The net withdrawal shall correspond to the LHe delivered to the External Dewar User and shall exclude any additional liquid consumption associated to the filling operation (e.g. conditioning, cool-down, boil-off losses, or vapour recovery).

The Contractor shall quantify and substantiate the total helium demand associated with dewar filling activities, including all contributions arising from:

Interface conditioning and purge operations

Cool-down of associated filling equipment

Expected boil-off losses during transfer

Vapour recovery efficiency and return flow

Purging or conditioning steps where applicable

The Contractor shall demonstrate that the Dewar filling operations do not adversely affect the availability, operational stability, or reliability of the QPS. At minimum, the Contractor shall:

Substantiate compliance in the Engineering File

Demonstrate compliance during SAT

The Contractor shall assume that the dewar has no instrumentation.

In the offer, the Applicant shall indicate the maximum filling rate that QPS can provide for each of the two user configurations (LINAC_24 and LINAC_30). The values shall be specified for the operational scenarios 2K-OP, 2K-SB, and 4K-SB.


# Warm GHe Recovery from WGR-MAC
The QPLANT shall autonomously determine the acceptance or rejection of the GHe returning via line QRB.G20. To this end, the QPLANT shall include all instrumentation, control functions, and interlocks necessary to monitor the interface conditions and to execute acceptance or rejection decisions, without any reliance on the external system.

The QPLANT shall be designed for interfacing with line QRB.G20 under the following fluid conditions

Fluid: gaseous Helium

Nominal temperature: 300K

Nominal pressure: 1.1 bar(a) ± 0.02 bar(a)

Maximal pressure: 1.5 bar(a)

Nominal mass flow: 0.1 g/s

Maximal mass flow: 0.5 g/s

The Contractor shall specify the helium purity acceptance criteria for the GHe returning via line QRB.G20, such that acceptance of the returned helium does not require any additional purification or gas clean-up by the QPLANT. At minimum, the acceptance criteria shall specify:

maximum allowable O₂ content

maximum allowable N₂ content

maximum allowable dew point below –80 °C.

The QPLANT shall accept the returning helium only when the following conditions are simultaneously satisfied:

The interface fluid conditions at line QRB.G20 are in accordance with the specified interface conditions

The measured helium purity complies with the defined helium acceptance criteria

The QPLANT operation can be maintained without disturbance

Upon rejection, the QPLANT shall vent the returning helium to the atmosphere via an outdoor discharge point, located outside the Coldbox room.

Upon acceptance, the QPLANT shall continuously monitor the acceptance criteria and shall immediately reject the returning helium if the acceptance criteria are no longer met.

The QPLANT shall include at the interface with line QRB.G20, at minimum:

A non-return valve

An automated isolation valve

Removable end caps to allow blinding of the interface

Dedicated sampling points for impurity monitoring

A pressure transducer

A mass flow transducer

The QPLANT shall include manual vent and purge valves at the interface with line QRB.G20 to allow drying and conditioning, controlled depressurisation, and safe warm-up of the interface and connected user line.

In the offer, the Applicant shall define the helium purity acceptance criteria for the GHe returning via line QRB.G20.


# Interfaces with cryogenic infrastructure

# Cryogenic Distribution Backbone (QDB)
The QPS shall mechanically interface with the QDB at the QRB–QLM connection.

On the QPS side, the interfacing element shall be the QRB (cold box unit).

On the QDB side, the interfacing element shall be the QLM Spool.

The interface definition for the QRB–QLM connection shall be led by SCK CEN via the QDB Contractor.

The execution of the QRB–QLM connection (site connection works) shall be performed by SCK CEN via the QDB Contractor.

The Contractor shall support the definition of the QRB-QLM interface. To this end, the Contractor shall:

Define and provide the QRB-side interface constraints, including geometry, space envelope, accessibility, allowable loads, and other relevant parameters.

Define and provide the QRB-side boundary conditions, including the terminal points and the proposed connection principles.

Provide all information required by SCK CEN (and the QDB Contractor) to define and manufacture the QLM Spool and to prepare the connection work.

Comply with the agreed interface definition, provided that the QRB constraints are respected.

The QRB shall include a removable test cap on the QDB interface to allow operation of the QPS prior to the QDB connection (incl SAT). For the test cap, the Contractor shall:

Account for the spatial constraints introduced by the test cap in the QRB interface design, including envelope, access, and handling.

Design the test cap to be fully compatible with its later removal and with the final connection of the QLM Spool.

The QRB interface to the QLM Spool shall comply with the following requirements:

The interface design shall allow the following site activities to be performed without modification of the QRB’s cold box unit:

Removal of the QRB test cap,

Preparation of the QRB interface for connection,

Connection of the QLM spool to the QRB.

The interface design shall enable the physical completion of the connection, including:

Joining of the process pipes.

Continuity of the Thermal Shield and MLI across the connection.

Joining of the vacuum jackets.

The interface region shall provide sufficient accessibility and clearance to perform these activities, taking into account that the QRB will initially be installed with the test cap in place.

The QRB–QLM connection shall be defined and frozen as follows:

The arrangement shall be defined during the Conceptual Design phase.

The interfaces, including pipe sizes, shall be frozen no later than the end of the Detailed Design phase.

The preliminary arrangement of the QRB–QLM connection is illustrated in Figure 10.

Vacuum jacket: ~400 mm

Header A: ~30 mm

Header B: ~150 mm

Header D: ~50 mm

Header E: ~50 mm

Figure 10. Preliminary arrangement and indicative pipe sizes of the QLM at the QRB-QLM connection.


# Warm Piping System (WPS)
The QPS shall mechanically interface with the WPS at various QRB-WPS connections for the warm headers W, U and S.

On the WPS side, the interfacing elements shall be the terminal points of headers W, U, and S.

On the QPS side, the interfacing elements shall be the corresponding terminal points on the QRB.

The QRB-WPS connections shall be located in the Cold Box Room.

The Contractor shall define the interfaces of the QRB–WPS connections.

The execution of the QRB–WPS connections (site connection works) shall be performed by SCK CEN via the WPS Contractor.

The QRB-WPS connections shall be defined and frozen as follows:

The arrangement shall be defined during the Conceptual Design phase.

The interfaces, including pipe sizes and location, shall be frozen no later than the end of the Detailed Design phase.

The preliminary dimensions and mechanical interfaces of the WPS interfaces are as follows:

Line U: DN25 at user side, flange type CF40

Line W: DN40 at user side, flange type CF63

Line S: DN150 at user side, flange type CF160


# Specificities for Line U interface
The QRB.U shall support the following use cases:

Helium supply for purge/conditioning of the Cryogenic Users

Helium supply for replenishment of helium guards at the Cryogenic Users

The flow conditions at QRB.U shall be:

Nominal flow temperature: ambient temperature ± 5 K

Nominal supply pressure: ~1.5 bar

Protected maximum supply pressure: 1.6 bar

Helium mass flow rate:

≤20 g/s during conditioning of Cryogenic Users (~2 kg in ≤120 s)

During replenishment of helium guards: to be defined latest by the end of the Detailed Design phase

Helium quality: clean helium suitable for direct use, in accordance with the QPS helium cleanliness requirements

The QRB.U shall include, at minimum:

A manual shut-off valve, equipped with a limit switch to signal the closed position to the QPS:CIS

A pressure limiter with a setpoint configured to achieve the nominal supply pressure

Pressure protection devices sized and set such that the protected maximum supply pressure is not exceeded


# Specificities for Line S interface
The QRB.S shall support the following use case:

Helium return at room temperature from the Cryogenic Users

The flow conditions at QRB.S shall be:

Nominal flow temperature: ambient temperature ± 15 K

Nominal return pressure: 1.1 bar ±5 mbar

Minimum allowable pressure: 1.05 bar

Helium mass flow rate capabilities (use cases):

Residual/erratic return flow: ≤0.1 g/s continuous

Uncontrolled reheating at the Cryogenic Users: 100 g/s nominal with spikes to 150 g/s during 6-8 h

Sudden and total break of insulation vacuum at the Cryogenic Users (QVE): transient return flow spike up to 200 g/s for ~100 s.

Helium quality: clean helium suitable for direct use, in accordance with the QPS helium cleanliness requirements.

The QPS design and operating sequences shall not cause the pressure at the WPS.S side of the interface from dropping below the minimum allowable pressure specified in RTM-292.

The QRB.S shall include, at minimum:

A remotely controlled shut-off valve, equipped with a limit switch to signal the closed position to the QPS:CIS

A regulation valve to control the intake of return helium

A pressure sensor located upstream of the regulation valve

A temperature sensor located upstream of the regulation valve

Pressure protection devices sized and set to protect the QPS equipment against overpressure originating from the Cryogenic Users. User-side overpressure protection is outside the QPS scope.

Provisions to protect the QPS equipment against cold helium originating from the Cryogenic Users. The QPS may reject the flow intake.


# Specificities for Line W interface
The QRB.W shall support the following use case:

Helium return at room temperature from the Cryogenic Users

The flow conditions at QRB.W shall be:

Nominal flow temperature: ambient temperature ± 5 K

Nominal return pressure: 1.1 bar ±10 mbar

Helium mass flow rate:

For 4K-SB, 2K-SB and 2K-OP: 0-3 g/s with stability of ±0.1g/s peak-to-peak over τ=1 min

For TS-SB and RT-SB: no flow

Helium quality: clean helium suitable for direct use, in accordance with the QPS helium cleanliness requirements.

The QRB.W shall include, at minimum:

A remotely controlled shut-off valve, equipped with a limit switch to signal the closed position to the QPS:CIS

A regulation valve to control the intake of return helium

A pressure sensor located upstream of the shut-off valve

Pressure protection devices sized and set to protect the QPS equipment against overpressure originating from the Cryogenic Users. User-side overpressure protection is outside the QPS scope.


# Control and Interlock System (QPS:CIS)

# Overview
The QPS:CIS is the dedicated system for the control and interlock of the Contractors Equipment, ensuring all on-site cryogenic processes operate safely and efficiently. This implies that QPS needs to provide SCADA including archiving functionality for historical data.

To function within the wider facility, the QPS:CIS connects with the MCS, the MIT and the MIS. In a later stage, SCK CEN may decide to integrate the QPS:SCADA into MCS.

The connection to the MCS is designed to exchange all necessary data between the QPS:CIS and the QCELLs.

The integration with the MIT platform is designed to:

Connect to centralized networking infrastructure

Utilize centralized services like backups, and user authentication.

Within the overall machine safety framework, the QPS:CIS has a clearly defined role:

It manages the dedicated local protection of the QPS, executing immediate safety functions such as automated shutdowns in response to internal faults.

It defers to the MIS for all global safety functions, particularly when the QPLANT interacts with other facility systems


# QPS:CIS Reference Architecture
Figure 11 illustrates the reference architecture of the complete cryogenic control system, identifying the QPS:CIS as a key sub-system.

Figure 11. Reference Architecture of the Cryogenic Control System

Refer to §11.3.2 for detailed signal and interface mapping shown in Figure 11.


# General requirements
The Contractor shall design the QPS:CIS in accordance with the Controls, Interlocks, and IT Documentation specified in [AD_05].

The QPS:CIS shall include all components identified in green within Figure 11.

The QPS:CIS shall include any additional systems or subsystems required to meet overall QPS performance, functional, and safety objectives.

The QPS:CIS shall use a commercially available, industrial-grade control platform with documented lifecycle support and vendor independence.

It shall meet applicable safety, performance, and reliability standards and shall comply with all relevant regulatory frameworks.

The QPS:CIS shall enable autonomous operation of the QPS across all defined operational scenarios and transitions, without requiring operator intervention.

The QPS:CIS shall support real-time monitoring of instrument health (e.g.: drift, dropout, deviation from expected range) with alarms and diagnostic flags for early fault detection.

Where a Software Component can be upgraded, the QPS:CIS shall support an upgrade procedure which can be automated as script(s), without the need for an Internet connection. A list of required tools must be provided.

The Contractor shall follow the applicable sections from the General Software and Hardware Requirements for Contractors (GSHRC) containing quality and other requirements related to software, firmware, and interoperability as per [AD_04] and specific instruction table (see §11.3.1 Table 30. Instructions for GSHRC

Interlock thresholds shall not be writable through the remote-control interface and can only be performed by authorized personnel after formal approval.

The QPS:CIS should allow every actuator to be controlled manually in the event of a malfunction (for example a motor can have an automatic a manual override mode).

In maintenance mode, the QPS:CIS shall allow every sensor value to be set by the operator to be interpreted by the QPS:CIS as it is the real value coming from the sensor.

The QPS:CIS shall store historical records of all measured values, valve positions, operator actions, alarms, etc. and make it available for users via the SCADA.

The QPS:CIS shall include functionality to perform automated testing procedures to validate the correct functioning of the whole QPS e.g., during SAT.


# Network Integration

# Reference Architecture
The hierarchy and levels are as follows:

Enterprise Network (IT): Site-wide IT infrastructure providing shared physical connectivity and transport. OT integration does not rely on its internal VLANs or topology.

Technical Network (OT): Logical industrial network for control systems (PLCs/SCADA), implemented using an Industrial Underlay plus a VXLAN Overlay.

Aggregation Zone: Connection point for multiple cells into the overlay, enabling controlled connectivity to services and other domains.

Cell: Isolated subsystem network segment assigned to a specific security zone (e.g., QPLANT, LINAC, NFS).

Figure 12. MIT Reference Architecture


# General
The Contractor shall supply a detailed list of the network ports and protocols necessary for the correct functionality of their system and application as part of CIS Dossier.

The Contractor shall be responsible for configuring the necessary network elements based on the inventory of network ports, protocols, internal and external applications.

The Contractor shall use IP address ranges for the QPS:CIS as provided by SCK CEN. This includes Level 0 of the Perdue model. These ranges will be pre-assigned by MIT to ensure consistency with the overall network architecture and addressing schemes.

The Contractor is responsible for implementing the provided IP ranges without deviation, and any additional IP requirements shall be communicated to and approved by MIT prior to implementation.

The Contractor shall document the use of the assigned IP ranges (as part of CIS Dossier) for each device and submit this documentation to MIT upon completing the configuration. MIT reserves the right to audit the Contractor's implementation to ensure adherence to the assigned IP ranges and network configuration standards.


# MIT Services Integration
Where backup of a system is required, the Contractor shall define the QAP

a clear list of all folders, files, databases, ... that are to be included in a backup

a document describing the backup and restore process

any script(s) required to perform these backups and restore actions

Where the system has an operating system, the System shall support monitoring by at least one of the protocols mentioned in the MIT interface catalogue chapter "Monitoring" [AD_05.01].

Irrespective of whether a system has an operating system or not, the System shall support authorization by at least one of the protocols mentioned in the MIT interface catalogue chapter "Authorization and security" [AD_05.01].

The System shall support network addressing service and network naming service by at least one of the protocols mentioned in the MIT interface catalogue chapter "Network addressing service" [AD_05.01].

The Contractor shall implement a mechanism for automatic IP address assignment based on MAC addresses whenever possible, utilizing DHCP services to ensure efficient and consistent configuration. In scenarios where DHCP is not feasible, the Contractor shall configure static IP addresses in accordance with MIT's assigned IP ranges. All configurations shall align with MIT's network architecture standards to ensure seamless integration and avoid IP conflicts.

The Contractor shall provide a comprehensive list of all devices, including their respective MAC addresses, prior to configuring the network. This list is crucial for tracking and managing devices, especially when configuring static IP addresses or ensuring proper DHCP assignment.

If a device is DHCP-capable but not configured for DHCP, the Contractor shall provide a detailed procedure for enabling and configuring DHCP on the device. The procedure shall include all necessary steps for ensuring proper DHCP functionality, such as network settings, IP lease time configuration, and alignment with MIT’s DHCP service and network standards.


# Network Infrastructure
An aggregation network ensures high reliability and performance by implementing redundancy to minimize downtime and enable fast recovery during faults. Redundant connections ensure continuous backbone network availability by enabling quick failover during link failures, minimizing disruptions, and maintaining system stability.

The aggregation network shall use a redundant ring topology, with a dedicated redundancy manager and client switches. The network shall automatically reconfigure within 300 ms in case of interruptions. Redundant connections to the backbone shall be established using a master/slave configuration, ensuring failover times under 300 ms. All links within the aggregation network, including connections to the backbone and cell networks, shall support 1 Gbit/s bandwidth. The network design shall incorporate fault recovery mechanisms to reroute traffic in the event of failures, ensuring uninterrupted data flow.


# Security
The Contractor shall maintain an Information Security Management System (ISMS) in accordance with ISO 27001. In their offer the Applicant shall deliver, for this ISMS, either (1) an ISO 27001 certification issued by an accredited certification body and The Statement of Applicability and the applicable scope or, (2) a brief mapping statement explaining how equivalent assurances will be provided.

The Contractor shall comply with the SCK CEN cybersecurity policy framework which, for this procurement, is defined as the requirements, from the “CCB Cyber Fundamentals requirements” (CyFun) at assurance level IMPORTANT, which SCK CEN identifies as obligations for the Contractor.
The Contractor shall provide a completed SCK CEN CyFun Supplier Control Response Matrix (which will be provided by SCK CEN during the Contract execution) stating for each relevant control: (1) Compliance status (Compliant / Partially compliant / Not compliant / Not applicable), (2) Description of implementation and boundary conditions, (3) Any deviations/risks and proposed compensating controls.

In the offer, the Applicant shall indicate and substantiate their level of experience in providing such information.

Where the proposed delivered product and/or installed system is claimed to be certified to IEC 62443-3-3 Security Level (SL 2, 3 or 4 ), the Applicant shall provide with the offer (1) certification document(s) (certificate or assessment report) from a recognized scheme/provider, and (2) a version and configuration declaration confirming that any delivered version/configuration matches the IEC 62443-3-3 SL(2/3/4) certified scope or identification of deviations and their implications.

The Contractor shall document the system's security features and their alignment with the requested standards and framework or the Contractor’s proposed equivalent assurances. This documentation shall be provided to SCK CEN for review and approval before implementation at MINERVA site.
Any material gaps against mandatory scoped CyFun controls must be remediated prior to SAT (or within an agreed corrective action plan), subject to SCK CEN approval.

Where infrastructure or tools are required for, or related to, the security of the system, the Contractor shall work with the SCK CEN to integrate with SCK CEN’s existing infrastructure and tooling. This includes, but is not limited to, tools and infrastructure for: Network security, Endpoint security, Identity and access management, Monitoring and analysis, or Data security.

If the Contractor requires remote access to the plant, they shall utilize the standard solution provided by SCK CEN. Access will be granted with restricted permissions to ensure that only necessary functions are available, safeguarding the integrity and security of the plant's systems. The Applicant is responsible for adhering to the defined access protocols and ensuring compliance with SCK CEN’s security policies.

The Contractor shall identify all products with digital elements (as per the EU Cyber Resilience Act (CRA)), which are used in the system. For each of these the Contractor shall (1) verify that Commercial Off-The-Shelf (COTS) products have a valid CE marking, and (2) provide technical documentation and a Declaration of Conformity to show compliance with the CRA for custom-built products. For both the documentation shall be provided to SCK CEN for review and approval prior to SAT.


# MCS Integration
The QPS:CIS shall regulate the mass flow rate and supply temperature at the QRB-DIST interface ensuring that the temperature change rate (during cool-down and warm-up) for QCELL during transients remains within predefined limits and the operational window. The temperature change rate is defined as the maximum allowable rate of change of the internal QCELL temperature, expressed in K/h (e.g., 4 K/h).

The QPS:CIS shall allow the adjustment of these limits, the global cooling/heating rate during operation.

The QPS:CIS shall implement a Control and Monitoring interface with the Concentrator PLC (refer to Figure 11 and items 20 and 33), exchanging real-time operational and control signals at an update rate of 1 Hz. This will be used by Concentrator PLC, implemented within MCS, to actively control and enforce this temperature change rate by issuing setpoints to the QPLANT.

When the MCS is unavailable or a communication loss occurs, the QPS:CIS shall continue to operate as long as the system’s safety as well as personnel safety are guaranteed.

All the control parameters relevant for User Integration (QCELL’s) (e.g.: setpoints and thresholds), including calibration data shall be available to the control and monitoring interface with MCS.


# User and Maintenance Manuals
The User Manual and Maintenance Manual shall contain all necessary documentation to enable SCK CEN to independently operate and maintain the QPS with minimum reliance on the Contractor.

The manuals shall include, at minimum:

All information required for proper operation of the QPS by SCK CEN.

All information required for corrective and preventive maintenance of the QPS by SCK CEN.

In their offer, the Applicant shall include representative examples of a User Manual and a Maintenance Manual.


# Software development
The Contractor shall provide a list of all development tools, environments, and version compatibility requirements necessary to edit, build, deploy, and restore the delivered control software at the time of Plant Acceptance.

The Contractor shall identify all third-party or vendor software licenses required for modification or deployment of the control software.

The Contractor shall not rely on undisclosed, inaccessible, or in-house proprietary tools that prevent reasonable modification, maintenance, or restoration of the delivered system.

The Contractor may exclude from editable source-code delivery software components containing proprietary intellectual property, including software related to turboexpander control, cold compressor control, protection, interlocks, or performance optimization. Still all applicable clauses from the GSHRC (see [AD_04], e.g., ESCROW) remain valid. For each excluded software component, the Contractor shall:

Excluded components shall not prevent operation, monitoring, integration, or modification of the overall QPS:CIS and may be delivered in compiled or parameterized form only if their interfaces, configuration options, and integration points are fully documented and remain usable and configurable by SCK CEN within the QPLANT:CIS

The Contractor shall provide the following as part of Control System Dossier:

control philosophy, functional descriptions,

detailed documentation of the software architecture, covering all modules, functional blocks, and components, along with their inputs and outputs.

lists of alarms, protection functions, instruments, events, and parameters.

control cabinet hardware configuration and recommended spare parts.

In the offer, the Applicant shall provide sufficient detail deemed representative of the anticipated software development scope, including assumptions, planned methodologies, and architectural breakdown.

All PLCs shall be programmed in full compliance with the IEC 61131-3 standard.

The use of Instruction List (IL) is highly discouraged. Higher-level languages like Structured Text (ST) are highly recommended for better clarity, maintainability, and portability of PLC programs. Therefore, the Contractor is strongly advised to avoid new implementations in IL and to migrate any existing IL-based code to ST or other recommended IEC 61131-3 languages whenever possible.

In the offer, the Applicant shall:

Declare the programming languages to be used per functional block.

Justify any deviation from ST and including retained IL-based implementations.

Demonstrate software structuring practices that favour maintainability, reuse, and modular design.

Proposals will be evaluated with preference given to Applicants demonstrating disciplined use of structured IEC 61131-3 languages and long-term maintainability strategies.

When the Software Component includes human readable information (for example, but not limited to: HMI, logging, source code), it shall be in English.

The Contractor shall develop a functional analysis and a detailed description of all control scenarios including interfaces. The detailed description shall also include a program sequence plan (functions and procedures used in the program). For each software module, functional block, component, or data block, the Contractor shall provide a detailed description of the logical conditions and input states that govern the activation, value assignment, or change of each output parameter.

In the offer, the Applicant shall provide a preliminary functional analysis and indicative control sequence plan, representative of the anticipated implementation. This shall include key functions, procedural steps, and interface interactions necessary to support evaluation of scope, architecture complexity, and design maturity.

Each Software Component and Hardware Node shall include a unique version identifier that uniquely represents the build date and unique version identifier, automatically generated during the build process to ensure traceability; this identifier shall be retrievable in a consistent and read-only manner through the MCS control and monitoring interface.

Configuration files and parameter sets shall be provided with version identification, configuration records, and change history sufficient to establish traceability of the delivered baseline.

The Contractor shall provide a complete and final listing of all operational setpoints, control-loop tuning parameters, and mode-dependent configuration values used to achieve the specified QPLANT performance.

The information provided shall include deviations from vendor default settings and tuning applicable to all operating modes.

Operational setpoints, tuning parameters, and configuration values shall not be withheld on intellectual-property grounds.


# SCADA, HMI, and Data Historian Infrastructure
The Contractor shall provide local operator stations (HMI) to support local data visualization, reporting, and maintenance activities for QPS. At minimum, one station shall be installed in the Compressor Room and one in the Cold Box Room.

The Contractor shall supply, configure, and commission a System-Dedicated SCADA system (QPS:SCADA) and data historian (QPS:HIS) for QPS:CIS. The dedicated SCADA system shall be designed such that future integration with a Site-Wide MINERVA SCADA system is technically feasible and not precluded by architectural, licensing, protocol, or data-model constraints.

During standalone commissioning and SAT, integration with SCK CEN systems (MIT, MCS, MIS) may not be available; therefore, QPS:CIS shall be capable of independent operation until full site integration is realized.

The QPS:SCADA solution shall serve as a reference design for a potential future integration in the MINERVA SCADA system. The Contractor shall therefore provide sufficient technical and functional documentation to support reuse and alignment.

The Contractor shall optionally support later integration of QPS:CIS with the MINERVA SCADA System. This support shall include, at minimum:

operator screen design support

communication protocol provision

coordination for tag/alarm consistency

provision of all technical documentation

The Contractor shall ensure that all operator stations (HMI panels or industrial touch PCs) use industrial-grade hardware suitable for continuous operation under QPS environmental conditions, including temperature, dust, and vibration. Hardware shall comply with relevant industrial standards.

The SCADA platform, data historian, and HMI hardware/software shall be supported with software, firmware, and security updates for at least 20 years from commissioning. The Contractor shall provide manufacturer documentation confirming update availability.

In the offer, the Applicant shall explicitly address the obsolescence management strategy for the proposed PLC or control system platform, considering the anticipated forty (40) year operational lifetime of QPS. This shall include:

Manufacturer support lifecycle documentation

Spare part availability forecasts and migration plans

Platform evolution roadmap (e.g., upgrade compatibility or virtualization strategy)

Technical or commercial approach to sustaining software and hardware support beyond the guaranteed 20-year update period (e.g., stockpiling, long-term service contracts, emulation layers).

The HMI shall be designed to allow migration to newer hardware from the same manufacturer, ensuring compatibility of project files, software licenses, and configuration transfer procedures.

Where local control is provided, the HMI shall implement a three-state control selection mechanism: Local – Free – Remote.

Control may only be granted when the system is in the Free state. Read-only access shall always be permitted. Other internal state machines (e.g., regulation loops) shall remain active regardless of control mode.

A system reserved in a specific control mode shall automatically transition to the Free state after a configurable inactivity timeout (maximum 5 minutes).

The Operator Station HMI shall not host real-time or safety-critical control functions. It shall be limited to monitoring, visualization, and local interaction.

The Operator Station HMI shall store operational data (trends, alarms) only for short-term analysis. Local data shall not be backed up and may be overwritten after the configured retention period.

The Operator Station HMI shall provide real-time and short-term historical trend plotting of key process variables.

The Operator Station HMI shall include graphical process views for monitoring equipment states and process flows.

The Operator Station HMI shall display and log alarms and events for operator awareness. Alarm acknowledgement shall not be implemented at the Operator Station if no authentication of the user is possible.

The Contractor shall develop graphical process views in a participatory design approach with SCK CEN, incorporating user feedback to promote consistency, usability, and standardization across operator interfaces as part of CIS Dossier

All sensors and actuators shall be represented in the graphical views.

The Operator Station HMI software shall support a default data acquisition period of ≤2 s. For all time-critical data—including turbine data and any Contractor-defined sequence, event-driven, or diagnostic signals used for root-cause or sequence-of-events analysis—an acquisition rate of 100 ms shall be supported

The HMI software shall support at least two permission levels with distinct functional access.

The QPS:CIS shall support automatic calling or emailing of on-call staff through MIT

Graphical views shall be consistent with the Process & Instrumentation Diagrams to ensure intuitive operation.

The QPS:SCADA system shall be available for minimal two operator workstations ( equipped with large-format displays (≥24-inch) to support effective visualization during QPS operation.


# Software Change Management
Prior to deployment in the production environment, software updates shall be rigorously tested to avoid integration issues or breaking the production system.

In the offer, the Applicant shall detail how he shall implement the software change management.

The control software version delivered prior to SAT (L6) shall constitute the contractual software baseline.

The Contractor shall define all warranty limitations related to post-acceptance software modifications.

Minor modifications performed by or on behalf of SCK CEN shall not void the warranty unless the Contractor demonstrates a causal relationship between the modification and the claimed defect.


# Interfaces with (external) Control System

# Interfaces with MCS
The interface between QPS (Contractor) and Control System (ICS) shall comply to the Slow Fieldbus Control and Monitoring Interfaces type C as listed in MCS Interface Catalogue [AD_05.04].


# Interfaces with MIS
The interface between QPS (Contractor) and MIS (ICS) shall comply to the MIS interfaces listed in catalogue [AD_05.01] as hardwired slow interlock interface [AD_05.03].


# Interfaces with MIT
Where the system has an interface with MIT, the system shall comply with the MIT architecture, processes, and interfaces.

The interface between QPS (Contractor) and SCK CEN Information Technology shall comply to the MIT interfaces as listed in catalogue [AD_05.01].

The QPS shall be physically connected to the MIT network in a redundant, fault tolerant way. At minimum 2 physical links will be foreseen, each link routed via a separate pathway. The physical connections need to be distributed over at minimum 2 separate physical endpoints on the QPS side.

The QPS shall be connected to the MIT IP network using a single logical routed connection ("layer 3"). On both sides, a single gateway IP will be configured as destination IP for packet forwarding.

Where the QPS:CIS or one of its components supports system logging, the contractor shall provide system logs remotely through at least one of the protocols mentioned in the MIT interface catalogue chapter "System logging".

Where the QPS:CIS support application logging, the System shall log remotely either by using a protocol defined in section "Application logging" of document "MIT interface catalogue") or alternatively adhere to the following:

Logs are provided in a data and file format that is machine readable, text based and non-proprietary. Examples of this include but are not limited to: CSV (Comma Separated Values), JSON (JavaScript Object Notation), GELF (Graylog Extended Log Format) or “Common Log Format.”

The details of the log format(s) used are provided. This includes but is not limited to the message structure and the possible key/value pairs with their type, value, and description.

Logs can be encrypted during transport if the security classification of the data permits this, but in this case the decryption procedure and required secret(s) need to be provided.

The QPS:CIS shall support timing synchronization by at least one of the protocols mentioned in the MIT interface catalogue chapter "Timing synchronization".

Where the QPS:CIS requires remote access; Systems shall provide remote access through at least one of the protocols listed in the MIT interface catalogue chapter "Remote access".

The connection of the QPS:CIS with MIT shall terminate on a patch panel

The system naming and tagging structure shall be frozen at Concept Design (L1) and shall not be modified without formal configuration control approval.

The control architecture shall implement QPS:CIS as the parent control layer with subordinate subsystem and skid-level CIS integration, with naming consistent to the project namespace conventions.

Each skid-level CIS shall provide license-to-operate validation signals (permissives) prior to startup, supporting bottom-up readiness (utilities → subsystems → systems).


# Buildings and Utility Interfaces
The Contractor shall design the QPS in accordance with the building and utility provisions provided by SCK CEN, as specified in this section, [AD_01], and [AD_03].

The Contractor shall specify the relevant parameters and operating limits for each type of interface with SCK CEN.

This information shall be documented in a dedicated Interface Control Document for each interface type.

Each Interface Control Document shall be included in the Engineering File.


# Site environmental conditions
The QPS shall be designed to operate under the site environmental conditions specified in Table 18.

For the Cold Box Room, the specified ambient temperature range may be reduced for sensitive equipment upon the Contractor’s request, subject to justification and approval by SCK CEN.

In the offer, the Applicants shall indicate any required deviation from the specified Cold Box Room temperature range.

Table 18. Site Environmental Conditions

† Range may be reduced for sensitive hardware upon Contractor’s request.


# Building
The Contractor shall design the QPS in accordance with the building and areas provided by SCK CEN, as specified in [AD_01].

The Auxiliary Building (AUB), including the Cold-Box Room.

The Cryogenic Compressor Building (CCB), including the Compressor Room and the designated outdoor Storage Area.

The Contractor shall locate the QPS equipment in accordance with the following constraints:

WCS and QRB equipment

All associated equipment shall be installed within the Compressor Room and Cold Box Room.

Distribution of equipment between these two rooms shall be at the Contractor’s discretion, provided that spatial, operational, maintenance, and safety requirements are satisfied.

WSH and QSN equipment

All associated equipment shall be primarily located within the designated outdoor Storage Area.

Auxiliary equipment (e.g. control panels, instrumentation cabinets, local control units) may be located within the Compressor Room or Cold Box Room where technically justified.

During the Conceptual Design Phase, the Contractor shall assess and specify whether permanent lifting infrastructure (e.g., overhead crane, monorail, hoist system) is required in each room.

If lifting infrastructure is required in a room, the Contractor shall specify:

required lifting capacity.

hook height.

runway length and coverage.

structural load implications.

operational constraints.

For the Compressor Room, the Contractor shall comply with the following constraints:

The access door is 2.5 m wide and 3.5 m high.

For the Cold Box Room, the Contractor shall comply with the following constraints:

The access door is 3.0 m wide and 3.0 m high (expandable up to 4.5 m height in exceptional cases).

The height of the ceiling is ~6.5 m.

The available space between the facility perimeter and the building is 11 m wide.

There is a roof opening closed with a temporary cover allowing to install the Cold Box.

The maximum available roof opening is 4.5 m × 13 m, measured as clear structural opening.

Within this opening, a preferred installation envelope of 3.7 m × 12 m is available. This envelope may contain service routings that could be temporarily removed to facilitate installation. The removal of these service routings shall be carried out by SCK CEN. The Contractor shall coordinate the removal activities with SCK CEN as part of the installation planning.

The Contractor shall remove the temporary cover of the roof opening and put it back once the Cold Box is installed.

The weight of this temporary cover is less than the weight of the Cold Box.

No additional activities (e.g. for making watertight) are requested.

The Contractor shall define and accommodate all installation tolerances, lifting equipment clearances, and rigging requirements within the above constraints.

For the outdoor Storage Area, the Contractor shall comply with the following constraints:

The access gate is 5 m wide and 4.5 m high.

In the offer, the Applicant shall identify the relevant equipment and specify:

enveloping dimensions

lifting mass

clearances

floor loads

transportation loads (road loads)

the minimal size of the roof opening


# Electrical Interface
The QPS shall connect to the electrical interface provided by SCK CEN at the following terminal points as per Table 19 and Table 20.

Table 19 Compressor room (CCB) electrical supply and load constraints

Table 20 Cold Box Room (AUB) electrical supply & load constraints

The Contractor shall design and provide the complete Low Voltage (LV) distribution system for QPS, including e.g., LV cabinets, switchboards, and protection devices.

The Contractor shall route, install, and connect all electrical cabling, cable trays, and interfaces for the Compressor Room, Cold Box Room, and WSH area except for the terminal points provided by SCK CEN as stated above.

All electrical design files - including one-line diagrams, layout plans, and protection studies - shall be submitted for SCK CEN approval.

The Contractor shall ensure all QPS equipment is connected to the respective building earthing network (provided by SCK CEN), fully compliant with IEC 60364 and IEC 61000 EMC requirements.

EMC best practices shall apply as per as per IEC 62305-3.

All helium piping, water, air lines, and LV cabling entering each building shall pass through a single shared feedthrough and be connected to equipotential bonding systems.


# LOOP event
In the event of a Loss of Offsite Power (LOOP) to the MINERVA facility, the Contractor shall assume that up to 350 kW of back-up power (supplied by a diesel generator) is available after a an interruption of a few minutes.

The Contractor shall define the required UPS backup scope and loads (HMI, PLCs, network, digital I/O) to ensure that the QPS manages to handle the LOOP event.

In the Offer, the Applicant shall:

Provide the total and per-building load assessments (normal and peak demand).

Submit Single Line Diagram (One Line Diagrams) aligned to the ‘spatial split’ (2 rooms in 2 different buildings and terminal point logic described above.

Include a risk analysis and list safety functions to be served by a UPS backup.

Declare isolation strategies for embedded electronics in HV environments and list any required auxiliary supplies.


# Water-Cooling Interface

# General cooling water interfaces
The QPS design shall comply with the following water provisions supplied by SCK CEN:

One terminal point pair (supply/return) per room by cooling water type.

The Contractor shall use the drain infrastructure provided in the rooms.

Both rooms are equipped with a drainage pit for PCW.

The WCS room is also equipped with a PCW drainage pit.

The Contractor shall implement the complete internal distribution system from the building terminal points to the individual points of use.

This shall include all piping, supports, valves, sensors, and electrical/control cabling.

All internal distribution details, tagging, and symbology shall conform to ISO 10628 and ISA-5.1.

Relaxation may be evaluated for specific subcontractor package plants, provided they interface correctly with the Support System.

All internal distribution headers shall include manual vent and drain valves at all high and low points.

These shall be specifically routed to the provided drain infrastructure.

The system shall be capable of filling via the supply system.

No explicit provision for separate make-up terminal points is required as this is managed via the Support System.

The Contractor shall differentiate between two types of cooling water, both using softened water with biocides and inhibitors

RCW, recovery cooling water for the heat recovery of compressors

PCW, process cooling water for cooling of all other components with the following properties:

A 40 wt.% propylene glycol–water mixture.


# Process cooling water general
The QPS material compatibility for closed-loop operation (PCW and RCW) shall comply with the SCK CEN provided water per Table 21.

Table 21 Softened water quality parameters used for closed loop filling

The Contractor shall quantify the expected heat load and cooling water flow rates for all operational scenarios provide by the end of the Conceptual Design phase.

The Contractor shall assume the following features of the PCW:

A total heat sink capacity (across WCS and QRB) of 1300 kW at flow rate of 115 m3/h for a dT ~11°C.

An overpressure protection set at 6 bar on both supply and return headers.

Provisions to maintain constant flow to prevent fouling

The QPS shall implement specific turndown logic exclusively for the water-cooling consumption of the HP Compressors based on the active operational scenario and LINAC configuration.


# Water Heat exchangers
For the water cooling of the oil of the HP compressors, the QPS shall interface with the water-cooling system provided by SCK CEN trough two types of heat exchangers:

Process Heat Exchanger, for the main removal of the compressor oil heat

Heat-Recovery Heat Exchanger, for the recovery and utilization of compressor waste heat

The heat exchangers shall be counter current welded or semi-welded plate heat exchangers.

The design shall allow easy access for servicing without major disassembly of connected piping.

The water heat exchangers shall comply with the following water conditions:

Nominal supply water temperature

For the Heat-Recovery Heat Exchanger: 30°C with a tolerance of +15°C (45°C) and -10 °C (20°C)

For all other heat exchangers: 27 °C ±5°C

Exceptional supply water temperature

Lower than nominal conditions during the coldest outdoor conditions after a long shutdown
(SCK CEN will implement provision to prevent condensation).

The water heat exchangers shall comply with the following pressures on the water side:

Minimum design pressure: 0 bar

Maximum design pressure: 10 bar

Maximal allowed pressure drop between water terminal points (incl. heat exchanger, pipes, fittings, valves, and ancillaries in-between):

Heat-Recovery Heat Exchanger circuit: 0,7 bar

Process Heat Exchanger circuit: ≤ 2.0 bar.

Hydraulic test pressure: according to the ASME.

The design temperature of the heat exchanger shall be the maximum design temperature of the oil circuit.

At the cooling side, the design shall consider water with 40 wt.% glycol or water.

All wetter materials (e.g., seals, and gaskets) shall be specified by the Contractor and subject to SCK CEN approval.


# Heat-Recovery Heat Exchanger
The Heat-Recovery Heat Exchanger shall be sized to:

Transfer up to 850 kW of thermal power from the QPS to the SCK CEN building heating system.

The water flow through the Heat-Recovery Heat Exchanger shall be regulated by SCK CEN.

The water flow regulation shall be within the range 0- 490 L/min, depending on the demand of building heating system.

The Contractor shall provide the capability to bypass the Heat-Recovery Heat Exchanger.

The bypass function shall allow operation of the QPS without heat recovery during short and long periods (e.g. during summer periods with no heat-recovery demand).

The bypass function shall be remotely operable through the QPS:CIS

The QPS operation shall not be adversely affected by the operation of the Heat-Recovery Heat Exchanger.

The Contractor shall assume that water cooling conditions and availability are independent between the Heat-Recovery Heat Exchanger and the Process Heat Exchanger.

During commissioning or operational optimization phases, the supply water temperature may temporarily exceed the nominal operating range.

The return water shall meet the following conditions:

Nominal return temperature: 55 °C

Operation range:

Minimum: 53 °C

Maximum: 60 °C


# Process Heat Exchanger
The Process Heat Exchanger shall be sized to:

Remove the entire thermal load of the compressor oil

Remove the residual thermal load following partial precooling by the Heat-Recovery Heat Exchanger located upstream.

The Process Heat Exchanger shall allow a flow rate of the cooling water of up to 1800 L/min.

SCK CEN shall reduce the flow rate during partial load operations or during periods with heat recovery.

In the Offer, the Applicant shall specify the minimum cooling water flow required at the heat exchangers during normal, partial-load, and heat-recovery operating conditions.


# LOOP event
In the event of a Loss of Offsite Power (LOOP) to the MINERVA facility, the Contractor shall assume that:

A back-up cooling water capacity of up to 350 kW will be available after an interruption of a few minutes.

The back-up cooling-water header is hydraulically common with the normal WCS cooling-water header, and that it may operate at reduced total flow.


# Instrument Air Interfaces
The QPS design shall comply with the following instrument-air provisions supplied by SCK CEN:

One instrument-air outlet in the Compressor Room.

One instrument-air outlet in the Cold-Box Room.

The QPS shall be designed for the following instrument-air supply conditions:

Nominal supply pressure: approximately 9 bar.

Pressure dew point: lower than -40 °C.

Maximum flow rate: 50 Nm³/h for the entire QPS.

Air quality: Quality Class 2 for particles, water, and oil, in accordance with ISO 8573-1.

The Contractor shall distribute the instrument air from the supply points to the relevant QPS equipment.


# LOOP event
In the event of a Loss of Offsite Power (LOOP) to the MINERVA facility, the Contractor shall assume that:

No continuous instrument air shall be provided during the LOOP event.

The instrument-air header shall contain only sufficient air for the initial valve actuations following the LOOP event.

The QPS shall include a backup system capable of providing the instrument air required to support helium recovery operations during a LOOP event.

The pneumatic backup system shall provide an autonomy of ≥ 6 hours under full helium recovery load conditions.


# Interfaces with HVAC
The QPS design shall comply with the following HVAC provisions supplied by SCK CEN:

Ambient heat removal in the Compressor Room and in the Cold-Box Room.

Dedicated exhaust-air ducts connected to the top of each HP compressor.

No active equipment shall be assumed in the exhaust-air ducts for the purpose of heat removal. (e.g. any fans, dampers, or control devices)

The WCS shall comply with the following heat-rejection constraints:

The total heat dissipated by the WCS to the room air shall not exceed 120 kW under all steady-state operating conditions.

At least 50 % of the heat dissipated by the WCS to the room air shall be directly transferred to the exhaust-air ducts connected to the HP compressors.

In the offer, the Applicant shall provide all relevant information on:

The heat dissipated to the ambient air.

The interface of the ducts to the compressors, including at minimum the size, flow rate, and allowable pressure drop.


# LOOP event
In the event of a Loss of Offsite Power (LOOP) to the MINERVA facility, the Contractor shall assume that:

The exhaust-air ducts connected to the top of the HP compressors shall remain available without restriction.

No more than 15 kW may be dissipated to the ambient air in the compressor room.


# Design and Fabrication Requirements

# Drawings and CAD models
The Contractor shall:

Develop all 2D manufacturing drawings and the corresponding 3D CAD models;

Develop the as-built PIDs per Element in accordance with ISA 5.1;

Integrate all applicable Instrumentation into the 3D CAD model;

Supply the 2D manufacturing drawings;

Supply the corresponding 3D CAD model(s) in multiple Levels of Representation (LoR), in accordance with §4.8.1.1;

Supply the CAD source file(s) of the 3D model(s).

The 3D model(s) shall be submitted in the following formats:

STEP AP242 (ISO 10303-242) or STEP AP203 (ISO 10303 21), during the Conceptual Design;

STEP AP242 (ISO 10303-242), during the remainder of the Contract.

The file name(s) shall adhere to the naming convention specified in [AD_06].

SCK CEN shall provide the final version of [AD_06] during Conceptual Design.

The 2D drawings shall comply with the Geometrical Product Specifications (GPS) standards, including but not limited to:

ISO 1101:2017 - Geometrical tolerancing — Tolerances of form, orientation, location and run-out;

ISO 1:2022 - Standard reference temperature for the specification of geometrical and dimensional properties;

ISO 286:2010 - ISO code system for tolerances on linear sizes;

ISO 2768:1989 – General tolerances;

ISO 2692:2021 - Geometrical tolerancing — Maximum material requirement (MMR), least material requirement (LMR) and reciprocity requirement (RPR).

All 3D models and 2D layouts shall use a coherent coordinate system, axis orientation, and global origin.

The Contractor shall submit updated 3D CAD models at the following Contract stages:

Conceptual Design

Conceptual 3D model with a Level of Representation of at least LoR 30

The model shall include the location of all external interfaces

Detailed Design

Detailed 3D model with a Level of Representation of at least LoR 40

The model shall include, as applicable, metadata such as component identifiers, geometric data, material properties, kinematic information, assembly information

Prior to the SAT

As-built 3D model with a Level of Representation of LoR 99

The model shall include metadata such as component IDs, geometric data, material properties, kinematic information, assembly information


# Level of Representation of 3D Models
The following LoR levels shall be provided:

LoR 10 - Reference Lines:

Representation limited to basic reference geometry such as datum points, axes, and sketches.

LoR 20 – Envelope:

Simplified bounding boxes or envelopes representing the overall geometry and space claim of the Element or Instance.

LoR 30 - Space-Claim / Keep-Out Zones:

Envelopes including hard and soft keep-out volumes and functional boundaries required for integration and clash detection.

LoR 40 - Minimal Structural Representation:

Representation including the principal structural Parts and the relevant interfaces.

LoR 99 - Full-Detail Representation:

The complete and detailed model used for integration, reviews, documentation, and final verification.

The Contractor shall maintain all required LoR versions up-to-date throughout the Contract, ensuring that each LoR remains consistent with the current design baseline.


# CAD Models with Intellectual Property
Without prejudice to the provisions on IP, in case the CAD model would contain IP content that the Contractor does not wish to share with other parties than SCK CEN:

The Contractor shall provide an overview of said IP content;

The Contractor shall provide a redacted CAD model (removing said IP content) that may be shared by SCK CEN at its discretion. Nevertheless, the redacted CAD model shall contain sufficient detail to allow accomplishment of the purpose(s) for which SCK CEN needs to share the CAD model.

The Contractor shall exercise reasonable judgment in determining which IP content cannot be shared and provide appropriate justification thereto.


# 3D Model Management
The Contractor shall establish and maintain a 3D-model management platform (e.g. Autodesk BIM 360 Docs or an equivalent system approved by SCK CEN) for the controlled exchange, review, and version tracking of all 3D CAD models and related 2D drawings.

The platform shall:

Provide real-time access for SCK CEN to view, comment, and download the current model versions;

Feature version control and change-tracking;

Feature access-rights management;

Remain operational throughout the entire term of the Contract.

The Contractor should ensure that the 3D models and associated workflows are compatible with SCK CEN’s current digital engineering environment, which includes PTC Windchill, PTC Creo, Autodesk Revit, Autodesk Navisworks, and Autodesk Construction Cloud.

In the offer, the Applicant shall

indicate the 3D-model management platform they shall use

Provide a preliminary CAD model of the QPS with at least LoR 20 in format STEP AP242.


# Digital Process Model and Digital Twin
The Contractor shall supply all necessary parameters to enable SCK CEN to simulate the QPS using its own models and tools.

For components where the parametrization is subject to IP restrictions, the Contractor shall provide a simplified representation sufficient for system-level simulation.

The Contractor may supply a Digital Process Model, a Digital Twin, or both. If supplied, the Digital Process Model and/or Digital Twin shall:

Be representative of the as-built QPS

Be based on modelling tools that are certified, validated, or compliant with recognised standards

Be delivered with sufficient documentation to allow independent use by SCK CEN

In the Offer, the Applicant shall explicitly state whether a Digital Process Model and/or a Digital Twin will be supplied.

If supplied, the Offer shall include a description the proposed modelling approach and toolset

If not supplied, the Offer shall describe the approach to commissioning support, fault simulation, diagnostics, and operator training.


# Design, Materials

# Material Requirements
All materials shall be delivered with traceable certificates. This requirement applies, including but not limited to, the following:

Base materials of the MPHX (e.g. core, manifold, nozzles)

Aluminium-to-stainless steel transition joints

Filler materials and brazing alloys


# Cleaning and surface treatment
All Parts exposed to Insulation Vacuum shall be systematically protected from any substances that might impair the ability to establish and maintain the required vacuum.

All the components shall be cleaned and made free from any contamination, oxidation, welding spatters, grease, dust, traces of fingerprints, and hydrocarbons in accordance with EN 12300;

The cleanliness verification shall be performed in accordance with method A.5 of EN 12300;

Only cleaning products, appropriate for use for a high vacuum environment, shall be used;

The application of shot peening is strictly prohibited on all components operating in a vacuum.

All surfaces in contact with helium shall be systematically cleaned and protected from any substances that might contaminate the Helium.

All surfaces shall be cleaned and made free from any contamination, oxidation, welding spatters, grease, dust, traces of fingerprints, and hydrocarbons in accordance with EN 12300;

The final cleanliness level of all surfaces shall be compliant with ISO 23208:2017; oxygen-specific requirements do not apply.

All metallic surfaces in contact with He shall be cleaned, pickled, and passivated

Once cleaned and dried, the Contractor shall immediately protect the cleaned component (and its interior) from any subsequent contamination. Cleaned components shall be stored in a clean, dry location, free of dust.


# Welding

# Certification and Qualification
All welds shall be completed by welders who are:

qualified according to EN 287-1 (Qualification test of welders – Fusion welding - Part 1: steels); and

certified according to EN ISO 9606-1 and/or EN ISO 14732 (latest edition).

All operating modes for each type of welding shall be qualified according to EN ISO 15614-1. The Welding Process Qualification Record (WPQR) shall be included in the Manufacturing File.

The Contractor shall qualify the different welding procedures to the maximum extent possible.

In case qualification of a welding procedure is not reasonably possible, the Contractor shall implement and adhere to a welding procedure validation plan.

All certification and qualification information shall be made available to SCK CEN throughout the entire term of the Contract.


# Welding procedures
For any weld, the Contractor shall:

Ensure that the parts to be welded are clean and free from dust, any traces of cutting fluids, grease and other hydrocarbon contaminants;

Have the surfaces which are subjected to the welding operations, inspected by competent staff and ensure that these surfaces are free from any cracks and porosity;

Implement all necessary means to minimize heat transfer from the welding seams to the existing brazed/soldered sections to avoid damage;

Anticipate the effects of shrinkage after welding, and hence take into account sufficient material to compensate;

Carry out intermediate and final tests on all “seal welds” to validate tightness against leakage.

For the welding method, the Contractor shall adhere to the following requirements:

All welding for vacuum enclosures and He process piping shall be done using the TIG welding process.

All butt welds shall be carried out with full penetration and without any discontinuity;

No grinding, polishing, or other abrasive mechanical action is accepted on any finished weld exposed to vacuum. Brushing with a stainless-steel brush shall only be allowed as a last resort for welds that are difficult to access;

All welds exposed to vacuum shall be chemically cleaned from the oxidation layer at the HAZ (heat affected zone);

The welding procedures shall comply with EN 15614-1(/A1, and /A2).

All permanent junctions shall be welded.

Brazing may be permitted in exceptional cases prior to approval by SCK CEN.

All junctions separating helium and water circuits shall be welded with the weld located on the water side.


# Weld testing & inspections
The examination of welds shall comply with the following requirements:

Personnel performing the examination shall be qualified/certified in accordance with ISO 9712;

Radiographic inspections for bulk defects shall comply with EN 17636 and ISO 5817;

Acceptance criteria for weld imperfections shall comply with ISO 5817, quality level B;

All welds shall be free from defects such as inclusions or microcracks;

All welds shall demonstrate no degradation following a cool down, when applicable (e.g. after cooldown).

The Contractor shall perform, at least, the following inspections:

All welds shall be visually inspected.  All hidden welds shall be inspected with an endoscope;

For helium seal welds:

Radiographic inspection on 25% of circular welds. The sampling shall be evenly distributed per welder across the circular welds performed by this welder.

Welds shall undergo thermal shocking (e.g., liquid nitrogen spray) prior to final leak testing.

The Contractor shall:

Indicate in the Manufacturing File which circular welds will be radiographically inspected;

Treat any weld that fails the examination as a Non-Conformity. Weld rework for the purpose of passing the examination shall not be permitted;

Provide the results of welding inspections to SCK CEN no later than one week after their realization.


# General Electrical Requirements
All electrical components (including cables, cabinets, cable trays, and associated systems) shall comply with the applicable international electrical standards, including but not limited to IEC 61508 and IEC 61511 for lifecycle functional safety aspects.

The selection of cable sheathing materials shall explicitly consider and be validated against the environmental conditions to which they will be exposed, including moisture, oil, cable trenches, heat and freezing temperatures, and electromagnetic interference (EMI) effects.

Each electrical and instrumentation cabinet shall provide at least 25% of its internal volume as free space to accommodate future installation of equipment, cabling, or modifications without necessitating structural change.

The Contractor shall install harmonic filtering devices on all major variable frequency drives (VFDs) (e.g., LP and HP compressors), and the requirements of IEC 61800-3 for industrial electromagnetic environments.

The Contractor shall ensure that emission and immunity limits are met through appropriate use of input line filters, output dv/dt filters (where applicable), and proper shielding, earthing, and cable routing practices.

The Contractor shall ensure that all VFD-driven motors operate within the allowable continuous frequency range defined by IEC 60034 (Rotating Electrical Machines). Nominal VFD operation shall not exceed 60 Hz, unless the Contractor provides substantiated evidence demonstrating that:

The selected motor and compressor system are rated for sustained operation above 60 Hz.

The expected Mean Time Between Failures (MTBF) at the proposed operating frequency is documented and acceptable.

All required mitigations are in place (e.g., output filtering, derating, bearing protection, insulation class suitability).

Where high voltage (HV) or high-power systems exist, embedded controls shall be powered using a dedicated and segregated low-voltage AC feed. These feeds shall be galvanically isolated from the HV main circuits.


# Transportation and Logistics Requirements
The Contractor shall be responsible for the correct packaging prior to transport. This shall include, at minimum:

Filling and sealing of all process circuits with inert gas.

The installation of shock indicators and pressure gauges, where applicable.

A visual inspection of the packaged items prior to shipment.

The Contractor shall be responsible for the loading, transport, intermediate storage (if applicable) and unloading of all QPLANT components.

Upon arrival at the SCK CEN site, the Contractor shall perform at least the following incoming-inspection actions:

Inventory check.

Visual checks.

Comparison of pressure readings before and after transport.

Readout of shock and acceleration indicators.

Identification and documentation of any transport-related damage or deviation.


# Installation Requirements
Prior to installation at the SCK CEN site, the Contractor shall submit the QA/QC governance applicable to the installation activities.

This shall identify the responsibilities for installation quality control, the authority for approval of installation completion prior to testing, and the escalation path for deviations and non-conformities.

This governance shall be documented in the applicable QAP documentation and updated as necessary to provide granular details of the installation phase.

The Contractor shall perform the installation of all equipment within its scope.

The Contractor shall provide all tooling, machinery, temporary equipment, and other means required for the execution of the installation activities.

The Contractor shall not rely on SCK CEN for such means unless explicitly agreed otherwise in the Contract.

The Contractor shall perform, at minimum, the following installation-related activities and checks, and shall record the outcome in the Installation File:

Mechanical installation and conformity checks

Verification of interface geometry and mechanical placement.

Verification of conformity of the installed assembly with the P&IDs and 3D model.

Verification of labelling and weld inspections.

Pressure & leak Integrity activities

Performance of the required pressure tests and static leak tests on all applicable pressure-containing components in accordance with the applicable codes and standards.

Pressure tests on helium-service components shall be pneumatic, unless otherwise specified. (Note: not applicable to water systems)

Provision of the corresponding test certificates.

Electrical & Instrumentation activities

Performance of electrical continuity, insulation, and functional checks.

Calibration and verification of all applicable instruments, including sensors, valves, and gas analysers

Safety Logic verification

Checking safety interlocks and fail-safe functions to confirm correct behaviour under fault conditions.

Control System verification

Verification of the correct execution of the implemented control procedures.

Cleanliness, conditioning, and machinery activities

Conditioning of all gas circuits and verification that they are clean.

Performance of initial static vibration checks on the compressors.

Insulation vacuum activities

Verification that the insulation vacuum of the cold box is below 10E-5 mbar, unless a different acceptance value is justified.


# Commissioning Requirements
The Contractor shall perform the Standalone Commissioning of the QPS to achieve full operational readiness matching the stated requirements.

The Standalone Commissioning shall be without connection to the QLM.

For the Standalone Commissioning, the Contractor shall supply and deploy the temporary test equipment and arrangements required to close the cryogenic circuits and to emulate the representative user-side operating conditions during Standalone Commissioning.

This shall include, where applicable, test caps, temporary piping, valves, heaters, instrumentation, and any other means necessary to emulate the required thermal loads, mass-flow demands, and pressure-drop conditions.

The Contractor shall perform at least the following activities:

Pressure integrity testing

Control & interlock logic commissioning

Validation of correct Instrument calibration

Compressor Control Tuning to achieve stable suction and discharge pressures.

Adsorber Sequence Logic automation for regeneration and switching sequences for warm and cold adsorbers.

Turbine Optimization for rotational speed.

Tuning of labyrinth sealing parameters

The Contractor shall perform all required performance and capacity testing to validate full compliance with all guaranteed performance, capacity, and quality criteria defined in this Technical Specification.

The Contractor shall perform these tests as part of the Commissioning phase and thus before the SAT. This shall ensure that the subsequent SAT can be performed efficiently.

This shall include but is not limited to:

The helium inventory required to perform the SAT is available.

Long Duration Test: The compression station shall operate continuously for a minimum of 24 hours at specified conditions to demonstrate thermal stability and mechanical reliability.

Cycle Gas Purity: During long-duration operation, impurity levels (O₂, N₂, H₂O) shall remain equal to or lower than the guaranteed values.

Oil Removal Efficiency validation

Dryer Capacity validation (potentially by controlled water injection).

Vibration Spectral Analysis to identify potential vibration sources.

Validation of all interface control logic between QPS:CIS and: MCS, MIT and MIS


# Training Requirements

# Training and Competence Transfer
The Contractor shall train SCK CEN personnel to a level that enables them to autonomously operate, maintain, and troubleshoot the QPS.

This shall include theoretical instruction, supervised practical training, and simulation-based recovery exercises for abnormal events (e.g. LOOP).

The Contractor shall prepare and execute a training programme.

The training programme shall cover, at minimum, the following training modules:

Installation and commissioning training.

Operation and abnormal-event response training.

Maintenance and troubleshooting training.

Instrumentation and electrical-measurement training.

Helium logistics, consumables, waste handling, and special-tools training.

All training modules shall include participatory and hands-on elements.

The Contractor shall provide training records, attendance records, and training materials.

The installation and commissioning training shall include, at minimum:

Mechanical installation and hook-up activities associated with pressure-retaining joints, bolted connections, and support systems

Verification of pressure-retaining joints, bolted connections, and support systems.

Pressure testing procedures, leak-rate quantification, vacuum pumping, and purging sequences.

Specific installation procedures for safety-relief devices, including the correct use of torque tools and sealing methods.

The operation and abnormal-event response training shall include, at minimum:

Operator training on the local HMI, including signal interpretation, local patch-panel operations, alarm handling, and electrical-cabinet checks.

Functional training on start-up, shutdown, transients, and integrated QPS operation.

Training on helium management during abnormal events, including LOOP.

Simulation-based abnormal-event response and recovery exercises.

The maintenance and troubleshooting training shall include, at minimum:

Static troubleshooting, including process-pressure analysis, leak testing, vacuum-decay tests, and valve-seat leak verification.

Dynamic fault finding and fault resolution.

Maintenance procedures for major rotating machines, including HP compressor screw replacement and removal/replacement of a single PVPS vacuum pump.

Hands-on maintenance procedures for the oil-removal system (ORS), dryers, including desiccant and absorbent removal/replacement, multi-component samplers, and gas analysers.

The instrumentation and electrical-measurement training shall include, at minimum:

Sensor calibration, replacement, and signal verification.

Methods for testing and measuring electrical consumption on the relevant high-power equipment, including the HP compressors and the PVPS vacuum pumping systems.

Control-loop tuning of the relevant compressor pressure-regulation loops, including supervised tuning to achieve the required stability margins and response times.

The helium logistics, consumables, waste handling, and special-tools training shall include, at minimum:

Management of helium delivery by road tanker, including connection, disconnection, and transfer to the WSH.

Procedures for handling and disposal of the relevant consumables, solid waste, and hazardous fluids.

Procedures for absorbent and desiccant replacement.

Procedures for compressor and pump oil changes.

Procedures for glycol-water drainage at the relevant water interfaces.

Training in the correct use of all proprietary and special tools required for safety devices, rotating machinery, maintenance, installation, and skid positioning activities.

In the offer, the Applicant shall include:

The Training Plan, including the proposed training modules and their intended scope.

The total price for the Training.

The expected personnel profile, including the number, and minimum entry competencies of the SCK CEN personnel (operators and technicians) required to successfully fulfil their duties after completion of the training.


# Acceptance Test Requirements

# General Requirements
The Contractor shall be responsible for:

The preparation and submission of the acceptance test programme

The preparation of the acceptance test activities

The execution of the acceptance test activities

The analysis of the acceptance test results

The documentation of the results in the corresponding acceptance test reports

The acceptance tests shall be defined in dedicated programmes (FAT Programme and SAT Programme, respectively).

Each acceptance test programme shall be submitted to SCK CEN for approval before the corresponding acceptance test is performed.

The Contractor shall perform each acceptance test in accordance with the corresponding approved acceptance test programme.

Each acceptance test programme shall, at minimum, contain:

A general overview, including:

The purpose of the acceptance test.

A comprehensive list of the tests to be performed.

The participants required on site during the acceptance test.

A description of the communication strategy and logistical organization for conducting the tests.

General requirements, including:

The equipment, tools, instrumentation, and computing devices to be used.

The environmental conditions that must be in place.

The required consumables and utilities (e.g. process gas, electricity).

The qualifications of the personnel required to conduct the testing.

Safety requirements, including:

The safety conditions and precautions to be respected during the acceptance test.

The required personal protective equipment.

The applicable permits, authorisations, and access conditions.

The emergency arrangements and stop criteria applicable to the acceptance test.

The identification of the hazards relevant to the acceptance test and the corresponding mitigation measures.

The parameters to be measured, including:

Their target values and acceptance limits.

The measurement instruments used and their measurement accuracy.

The measurement methodology.

The calculation methods to be applied where direct measurement is not possible.

The test setups and methods, including:

A description of each test setup.

A description of each test method used to obtain representative and reliable results.

The reporting requirements, including:

How the acceptance tests shall be documented.

What the resulting documents shall contain.

To which organisations the resulting documents shall be transmitted.

The acceptance tests shall be documented in dedicated reports (the FAT Report and the SAT Report, respectively).

The reports shall clearly present the results of each individual test and explicitly state whether the corresponding test has been passed or failed.

The corresponding acceptance test report shall be annexed to the QCR and submitted to SCK CEN for approval.

The Contractor shall be responsible for providing and/or making available all testing equipment, tools, instrumentation, consumables, and utilities required for the proper execution of the acceptance tests.

Where required for the acceptance tests, the Contractor shall also provide additional test cryostats, valves, instrumentation, and other temporary test equipment.

In their offer, the Applicant shall provide a concise description of the inspections, FAT test and SAT tests that will be performed, including:

How each test shall be performed

Which equipment, tools, and instrumentation shall be used


# Factory Acceptance Test (FAT)
The Contractor shall perform a Factory Acceptance Test (FAT) to verify that the manufactured QPS and its functional Parts comply with the requirements set forth in the Contract.

The Contractor shall perform, at minimum, the FAT tests specified in this section.

The FAT shall include, at minimum, the functional verification of all functional Parts. This shall include, where applicable:

Full electrical inspections

Comprehensive checks for vacuum and/or gas leak tightness

Testing of the wiring for all Instrumentation hardware

The FAT shall include, at minimum, the following tests and activities:

Dimensional and geometrical controls.

Pressure and He leak tests.

Instrumentation and wiring tests incl. e.g. Insulation resistance, earthing continuity checks, visual inspection of cabling, labelling, and conformity to wiring diagrams.

Actuated Parts operability tests.

Hydraulic characterization.

Compressors & Motors tests, including flow rate, pressure, power consumption, efficiency, vibration, and noise.

Turbines & Cold Compressors tests, including verification of rotor stability and vibration levels at design rotation speed.

Validation of the local control and HMI for each individual system

Review of the QCR for conformity to the approved QAP.

Review of completeness of documentation included in the Contractor’s scope.


# Site Acceptance Tests (SAT)
The Contractor shall perform the Site Acceptance Tests (SAT) to demonstrate that the as-built QPS complies with the requirements set forth in the Contract under site conditions.

The Contractor shall perform, at minimum, the SAT demonstrations and tests specified in this section.

The SAT Programme shall define the SAT-specific aspects required for the execution of the SAT, including at minimum:

The site utilities, consumables, and external services required for the SAT.

Any temporary test equipment and arrangements required for the SAT demonstrations.

The SAT shall be performed in a logical sequence from prerequisite checks to functional demonstrations and performance demonstrations.

A test shall only be started once the prerequisites defined in the approved SAT Programme are fulfilled.

Each SAT demonstration shall be performed, at minimum, with the QPS operating at the QPLANT Design Point, unless specified otherwise in the applicable SAT requirement or in the approved SAT Programme.

Where specified, the SAT demonstration shall be performed with the QPS operating at QPLANT Predefined Test Points, which are defined as follows:

Each QPLANT Predefined Test Point shall correspond to a valid steady-state condition within the Operational Condition Ranges defined in §4.2.3.

All QPLANT Predefined Test Points shall be defined by SCK CEN and communicated during the SAT campaign.

The selected QPLANT Predefined Test Points shall be explicitly recorded in the SAT Report.

For each SAT demonstration, the Contractor shall continuously monitor and record the quantities relevant to the demonstrated function. This shall include, where applicable, at minimum:

Mass-flow rates.

Pressures and pressure drops.

Temperatures.

Liquid levels.

Storage pressures.

Cooling-water temperatures and flow rates.

Motor currents and voltages.

Applied heater powers.

For each SAT demonstration, the Contractor shall record the measured and derived quantities required to substantiate the test result.

The recorded data shall be sufficient to reconstruct the demonstrated operating condition, the applied determination method, and the resulting compliance assessment.

The reported values used to substantiate a SAT result or compliance assessment shall be reported with their associated expanded uncertainty.

The expanded uncertainty shall be reported at a confidence level of 95 %.

The expanded uncertainty shall include all contributions associated with the determination method of the respective value, including, where applicable, uncertainty arising from:

Measurement methods.

Direct or indirect determination methods.

Experimental or analytical simplifications.

Corrections, interpolations, or extrapolations.

For compliance assessment, the value used to verify compliance shall be the reported measurement value adjusted by the associated expanded uncertainty (as defined in RTM-506) in the direction unfavourable to compliance.

The Contractor shall provide and use the temporary test equipment and arrangements necessary to emulate the representative user-side operating conditions required for the SAT demonstrations. The temporary test equipment and arrangements shall:

Be based on the Cryogenic User Circuitry Model.

Include, where applicable, temporary heaters, valves, piping, test caps, and any other means necessary to emulate the required thermal loads, mass-flow demands, and pressure-drop conditions.

A demonstration performed prior to the formal SAT campaign may only be accepted as SAT evidence if:

It was performed in accordance with the approved SAT Programme

The corresponding records are available and acceptable to SCK CEN

No subsequent work, modification, or non-conformity may have affected its validity

SCK CEN explicitly agrees that repetition is not required


# Demonstration of functional behaviour and operability
The Contractor shall demonstrate the correct functional behaviour and operability of the QPS during the SAT.

The Contractor shall demonstrate the correct functioning of the QPS control sequences, alarms, protections, and interlocks. This shall include, at minimum:

The validation of the start-up and shutdown sequences of the QPS.

The validation of entry into, operation in, and exit from all Operational Scenarios, as defined in §4.2.2, including the transitions between them.

The validation of the relevant valve logic and automatic operating sequences.

The Contractor shall demonstrate the correct behaviour of the QPS under specified abnormal events by applying or triggering the relevant event conditions during the SAT. This shall include, at minimum:

Automatic switching to backup utility configurations

Helium recovery behaviour

Valve logic and interlock behaviour

Response behaviour to abnormal events (e.g. LOOP)

The Contractor shall perform stress tests under controlled SAT conditions to demonstrate the robustness of the QPS control and protection functions under perturbed operation.

The stress tests shall validate the control response, protection logic, and system stability under representative disturbances and off-normal but controlled operating conditions.

The stress tests shall include, at minimum:

Loss of electrical power.

Loss of cooling water.

Loss of instrument air.

Loss of vacuum.

Loss of control-system function or communication.

Degraded helium purity or impurity-related alarm/trip conditions.

The Contractor shall demonstrate the correct operational behaviour of the safety-related functions during the SAT.

Where applicable, this shall include the functional tests required to support the verification of the specified safety integrity requirements.


# Specific Functional demonstrations
For the WCS, the Contractor shall perform the following functional tests during the SAT:

Test conditions

The WCS shall be tested in stand-alone configuration

Tests execution

Checking the mechanical characteristics

Measurement of vibrations, noise, oil pressures, and oil temperatures.

Checking of the cooling-water system.

Testing of the control software and interlocks during operation and under simulated failures.

Measurement of the main process characteristics, including helium flow rates, pressures, and temperatures.

Acceptance criteria

No abnormal or unstable operation shall occur during the test.

The measured vibration and noise levels shall comply with the specified limits

All demonstrated characteristics shall comply with the corresponding requirements and specified limits.

For the QRB, the Contractor shall perform the following functional tests during the SAT:

Test conditions

After successful completion of all individual WCS tests.

Test execution

Checking of the mechanical characteristics.

Measurement of the vibrations of the rotating machines.

Checking of the control software and interlocks in accordance with the functional analysis.

Testing of the cold compressors at the design operating points (minimum and nominal) and at full speed.

Checking of the operation of all valves, instruments, heaters, and rotating machines in the QRB and associated warm panels for all defined operating modes.

Acceptance criteria

Checking of the control software and interlocks in accordance with the functional analysis.

Acceptance criteria

All demonstrated characteristics and functions shall comply with the corresponding requirements and specified limits.

For the QPS, the Contractor shall perform the following abnormal-event tests during the SAT:

Test conditions

The demonstrated operating point shall be:

POINT_A = QPLANT Design Point

The simulated abnormal events shall include, at minimum

Failure of the QPS:CIS

Partial or total loss of electrical power

Partial or total loss of cooling water

Partial or total loss of instrument air

Partial or total loss of insulation vacuum

Five (5) abnormal events selected by SCK CEN from a list proposed by the Contractor. For this purpose, the Contractor shall include in the SAT Programme a list of at least twenty (20) distinct credible, critical, and testable abnormal events relevant to the supplied system, affecting power supply, control signals, instrumentation, communication, auxiliary systems, or utilities

Test execution

Prior to the simulation of each abnormal event, the QPS shall be operating at POINT_A.

The Contractor shall simulate each abnormal event individually.

For each simulated abnormal event, the Contractor shall verify the QPS response, including alarms, interlocks, shutdown functions, and state transitions.

The Contractor shall verify the safe shutdown of the QPS following each simulated abnormal event.

After completion of each test run, the Contractor shall restore normal operating conditions before the next abnormal event is simulated.

The Contractor shall record the QPS response for each simulated abnormal event.

Acceptance criteria

The QPS shall respond to each simulated abnormal mode in accordance with the functional analysis, the defined fail-safe philosophy, and the recovery procedures.

No uncontrolled or undefined operating state shall occur during the test.

All alarms, interlocks, shutdown functions, and state transitions shall operate as specified.

All demonstrated characteristics and functions shall comply with the corresponding requirements and specified limits.


# Demonstration of performance and capacity
The Contractor shall demonstrate the performance and capacity of the QPS during the SAT.

The Contractor shall perform sustained runs where required by the applicable SAT demonstration

The sustained runs shall be of sufficient duration to demonstrate stable operation and performance under site conditions.

The minimum duration of each sustained run and the corresponding stability criteria shall be defined in the SAT Programme.

The Contractor shall demonstrate stable operation at the QPS for each operational scenario and for the relevant transitions between them. Where applicable, the Contractor shall demonstrate:

The achievement and sustainment of the required refrigeration power.

The available refrigeration power margin.

The mass-flow capability.

The stability of the relevant regulation loops.

The suction-pressure stability.

The ΔT stability.

The correct cold-box load balancing.

The response to representative step changes in applied heat load, operational configuration, and boundary conditions.

The short-term transient response and the longer-term steady-state stability.

The absence of any choke, surge, or other unstable operating modes.

The pressure-drop behaviour of the relevant circuits.

The Contractor shall, at minimum, continuously monitor and record the following quantities during the relevant SAT demonstrations, where applicable:

General

Individual electrical motor currents and voltages.

Heat power of the electrical heaters.

Cooling-water temperatures and mass-flow rates.

Mass-flow rates.

Pressures and pressure drops.

Temperatures.

For the QRB:

The flow conditions at headers A, B, D, E, and W.

The liquid levels of the LHe thermal baths.

For the WCS:

The flow conditions at headers VLP, LP, and HP.

For the WSH and, if applicable, the QSN:

The pressures in the storage tanks.

The mass-flow rates.

The liquid levels of LN2 in the QSN.


# Demonstration of the cooling capacity
For the TS-SB scenario, the Contractor shall perform the following cooling-capacity test during the SAT:

Test conditions

The demonstrated operating points shall be:

POINT_A = QPLANT Predefined Test Point, as defined in RTM-503, within the 4K-SB scenario

POINT_B = QPLANT Predefined Test Point, as defined in RTM-503, within the TS-SB scenario

The test run shall be performed without operation of the VLP compressors.

Test execution

The QPS shall start at the operating POINT_A.

The QPS shall transition from POINT_A to POINT_B.

The QPS shall operate for at least 24 h under steady-state conditions at POINT_B.

After completion of the run, the QPS shall return to POINT_A.

Acceptance criteria

No discontinuous operation shall occur during the full testing period.

The achieved values shall comply with the specified performance requirements.

For the 10K-SB scenario, the Contractor shall perform the following cooling-capacity test during the SAT:

Test conditions

The demonstrated operating points shall be:

POINT_A = QPLANT Predefined Test Point, as defined in RTM-503, within the 4K-SB scenario

POINT_B = QPLANT Predefined Test Point, as defined in RTM-503, within the 10K-SB scenario

POINT_C = QPLANT Predefined Test Point, as defined in RTM-503, within the 10K-SB scenario

The test run shall be performed without operation of the VLP compressors.

Test execution

The QPS shall start at the operating POINT_A.

The QPS shall transition from POINT_A to POINT_B.

The QPS shall operate for at least 12 h under steady-state conditions at POINT_B.

The QPS shall transition from POINT_B to POINT_C.

The QPS shall operate for at least 12 h under steady-state conditions at POINT_C.

After completion of the run, the QPS shall return to POINT_A.

Acceptance criteria

No discontinuous operation shall occur during the full testing period.

The achieved values shall comply with the specified performance requirements.

For the 4K-SB scenario, the Contractor shall perform the following cooling-capacity test during the SAT:

Test conditions

The demonstrated operating points shall be:

POINT_A = QPLANT Predefined Test Point, as defined in RTM-503, within the 4K-SB scenario

POINT_B = QPLANT Standby Point

All liquid-helium baths shall be filled to their minimum operating levels.

Test execution

The QPS shall run for at least 48 h at POINT_A.

The sub-atmospheric compressors shall not be running during the 48 h run.

After completion of the run, the QPS shall transition to POINT_B, including start-up of the sub-atmospheric compressors.

Acceptance criteria

No discontinuous operation shall occur during the full testing period.

The achieved values shall comply with the specified performance requirements.

For the 2K-OP and 2K-SB scenarios, the Contractor shall perform the following cooling-capacity tests during the SAT:

Test conditions

The demonstrated operating points shall be:

POINT_A = QPLANT Standby Point

POINT_B = QPLANT Predefined Test Point, as defined in RTM-503, within the 2K-OP scenario.

POINT_C = QPLANT Design Point

Test execution

Three (3) runs shall be performed back-to-back.

The 1st run shall be performed for at least 48 h at POINT_A.

The 2nd run shall be performed for at least 48 h at POINT_B.

The 3rd run shall be performed for at least 48 h at POINT_C.

Acceptance criteria

No discontinuous operation shall occur during the full testing period.

The VLP bath pressure stability shall remain within the specified limits during the full duration of each run.

The achieved values shall comply with the applicable performance requirements.


# Demonstration of the 2K-OP operating envelope
The Contractor shall demonstrate the robustness and controllability of the QPS within the 2K-OP operational envelope during the SAT. This demonstration shall be performed with the QPS operating at each of the following test points:

QPLANT Design Point

QPLANT Standby Point

Six (6) QPLANT Predefined Test Points, as defined in RTM-503, each corresponding to a condition within the 2K-OP scenario.

At each test point of the demonstration, the Contractor shall:

Demonstrate stable transition of the QPS from the preceding test point to the current test point.

Stabilise the QPS at the test point and record the relevant process values.

Apply a first step change ∆Q_step, as defined in RTM-528.

Demonstrate that the QPS remains controllable and reaches a stable operating condition following the applied step change ∆Q_step.

Apply a second independently selected step change ∆Q_step, as defined in RTM-528.

Demonstrate that the QPS remains controllable and reaches a stable operating condition following the applied step change ∆Q_step.

The Predefined Heat-Load Step Changes (∆Q_step) shall be defined as follows:

Each ∆Q_step shall have a value between -30 W and +30 W. All ΔQ_step values shall be selected independently of one another.

Each ∆Q_step shall be applied to the cavity heat loads Q_CAV, in accordance with the Cryogenic User Circuitry Model.

Each ∆Q_step value shall result in a valid heat load condition for the 2K-OP scenario within the Operational Condition Ranges defined in §4.2.3.

Each ∆Q_step value shall be defined by SCK CEN and communicated during the demonstration.

The demonstration shall be performed according to the following sequence:

The QPS shall start in 2K-SB

The QPS shall transition from 2K-SB to 2K-OP via the transient 2K-RAMP

The QPS shall stabilizes at the first test point

After completion of the demonstration at a given test point, the QPS shall transition to the subsequent test point.

The sequence shall be repeated until all test points have been demonstrated.

After completion of all test points, the QPS shall transition back to 2K-SB.


# Characterization of the QPLANT Maximal Point
The Contractor shall characterize the QPLANT Maximal Point during the SAT. To this end, the Contractor shall:

Determine the corresponding operating conditions.

Demonstrate stable operation of the QPS at that point.

Identify the limiting subsystem(s) or constraint(s).

Report the corresponding operating margins and stability limits.


# Demonstration of process subsystems and process integrity
The Contractor shall demonstrate that the QPS maintains the required leak-tightness and vacuum performance under operating conditions during the SAT. This shall include the verification that:

The relevant vacuum levels remain within the specified limits.

The measured leakage remains within the specified leak-rate limits.

No issues linked to leak-tightness or vacuum performance shall occur during the relevant SAT demonstrations and tests.

For the process helium, the Contractor shall demonstrate that the required purity is maintained during the SAT operating conditions.

This shall include the monitoring and assessment of at least oxygen, nitrogen, and water content in the processed helium, in accordance with the specified impurity limits.

This shall include the assessment of hydrocarbons and oil carry-over downstream of the oil-removal system.

The Contractor shall identify and use the relevant sampling and analysis points for the demonstrated helium circuits.

No purity-related deviation beyond the specified limits shall occur during all relevant SAT demonstrations and tests.

The Contractor shall demonstrate during the SAT the correct functional behaviour of lines QRB.U, QRB.S, and QRB.W under the relevant operating conditions. This shall include, where applicable, at minimum, the verification of:

For all 3 lines

The corresponding temperatures, pressures, mass-flow capabilities, and helium quality at the relevant interface.

The correct behaviour of the associated shut-off valves, regulation valves, instrumentation, and protection devices.

The operation through the relevant line does not cause unacceptable degradation of QPS performance, process stability, equipment protection, or compression-system behaviour.

For lines QRB.S and QRB.W

The flow through the lines is correctly received and processed by the QPS.

For line QRB.S

The QPS design and operating sequences do not cause the pressure at the WPS.S side of the interface to fall below the specified minimum allowable pressure.

The correct behaviour of the associated cold-helium protection provisions.


# Demonstration of rotating and compression equipment
For the cold compressors, the Contractor shall demonstrate the operating envelope and stability margins during the SAT. This shall include, at minimum:

The verification of the operating envelope of the cold compressors.

The provision and verification of the reference performance maps and stability limits used to define that operating envelope.

The verification of the choke and surge margins at the demonstrated operating points.

For each warm compressor unit, the Contractor shall demonstrate the relevant performance and operating characteristics during the SAT. This shall include, at minimum:

The mass-flow capability.

The noise, vibration, and flow stability.

The load/unload logic and turndown control behaviour.

The verification of operation at the QPLANT Design Point

The verification of operation at the QPLANT Standby Point

The verification of compliance with specified noise/vibration limits

For each warm compressor system, the Contractor shall demonstrate the relevant auxiliary-process performance during the SAT. This shall include, at minimum:

The oil-removal efficiency.

The dryer performance.

The verification of the relevant impurity-removal performance of the auxiliary-process systems.

The verification of the relevant downstream oil concentration limits.

The verification of the regeneration procedure, regeneration duration, and regeneration-gas consumption.

For the WCS, the Contractor shall perform the following capacity test during the SAT:

Test conditions

The QPS may be at room temperature

The WCS shall operate over 48 h under steady-state conditions corresponding to the maximum mass-flow rate for each compression stage and the maximum pressure ratio.

All compressors shall operate at full charge during the full duration of the test.

Test execution

The following quantities shall be continuously monitored and recorded during the full test period:

Mass-flow rates delivered by the compressors.

Pressures at VLP, LP, and HP.

Helium temperatures.

Cooling-water temperatures.

The performance of the oil-removal system, including the hydrocarbon level downstream of the ORS.

The performance of the dryer.

Individual electrical motor currents and voltages.

Acceptance criteria

No discontinuous operation shall occur during the full testing period.

The cooling-water temperatures shall remain within the specified limits.

The compressor stability shall remain within the following limits: LP: ±3 %; HP: ±2 %.

For the expansion turbines, the Contractor shall demonstrate the performance and stable operation during the SAT. This shall include, at minimum:

The verification of the relevant operating range.

The verification of stable rotational behaviour.

The verification of the relevant inlet and outlet process conditions.

The verification of the turbine control behaviour.

The verification of the turbine start-up, shutdown, and response to operating-point changes.


# Demonstration of storage and withdrawal systems
For the WSH, the Contractor shall demonstrate the performance during the SAT. This shall include, at minimum:

The verification of the usable helium storage capacity.

The verification of the fill and withdrawal capability.

The verification of the pressure stability and pressure control behaviour.

The verification of the correct functioning of the associated instrumentation, valves, and protections.

If the QSN is supplied, the Contractor shall demonstrate the performance of the QSN during the SAT. This shall include, at minimum:

The verification of the boil-off rate.

The verification of the usable LN2 storage capacity.

The verification of the fill and withdrawal capability under representative demand.

The verification of the pressure stability and pressure control behaviour.

The verification of the correct functioning of the associated instrumentation, valves, and protections.

For the filling station, the Contractor shall demonstrate the filling of a dewar while the QPS is operating at the QPLANT Design Point. This shall include, at minimum:

The verification of the correct filling operation under the relevant operating conditions.

The verification of the correct functioning of the associated instrumentation, valves, and protections.

The verification that impure helium is automatically rejected in accordance with the specified acceptance criteria.


# Energy-Efficiency demonstration
The Contractor shall demonstrate compliance with invCOP_contract in accordance with §4.3.4. To this end, the Contractor shall:

Define and document the methodology used to determine invCOP_SAT.

Perform the measurements required by that methodology.

Determine invCOP_SAT and the associated expanded uncertainty U_invCOP_SAT.

Document and substantiate the SAT results.

The methodology used to determine invCOP_SAT shall be defined in advance and shall specify at least:

The required instrumentation.

The electrical measurement boundary.

The measured and derived quantities used in the determination.

Any correction, interpolation, or extrapolation applied to determine invCOP_SAT at the QPLANT Design Point.

The Contractor shall provide SCK CEN with reasonable access to electrical measurement points to independently measure the energy consumption of the QPS and validate the claimed energy figures.

In the offer, the Applicant shall

Describe the electrical power measurement method they will apply within the QPS, including the electrical boundary (e.g. total plant consumption including auxiliaries, compressors, and control systems) and the associated measurement uncertainty.

Explicitly state whether any SCK CEN measurements are assumed.


# Demonstration of operating procedures
The Contractor shall demonstrate during the SAT the operational procedures of the QPS that are relevant to operation, maintenance, regeneration, and special site-test conditions.

The Contractor shall demonstrate the execution of the operational procedures required for normal operation of the QPS. This shall include, at minimum:

Start-up procedures.

Shutdown procedures.

Entry into and exit from maintenance or regeneration states.

Recovery to the intended operating state after completion of the procedure.

For the gas-treatment systems, the Contractor shall demonstrate the relevant switching, regeneration, and recovery procedures during the SAT. This shall include, where applicable, at minimum:

Dryer switching and regeneration.

Cold adsorber switching and regeneration.

The demonstration that these procedures can be performed without unacceptable disturbance to the QPS operating at the QPLANT Design Point, or at another relevant operating point specified in the SAT Programme.


# Demonstration of control system behaviour
The Contractor shall demonstrate during the SAT that the QPS:CIS behaves correctly and complies with the specified control, communication, and data-handling requirements.

The Contractor shall demonstrate the continuity and failover behaviour of the QPS:CIS, where applicable. This shall include, at minimum:

The behaviour of the PLC and SCADA during failover, restart, and recovery conditions.

The correct restoration of the relevant control-system functions after failover or restart.

The preservation or orderly recovery of the relevant control states, alarms, and operator functions.

The Contractor shall demonstrate the behaviour of the QPS:CIS communication infrastructure during the SAT. This shall include, at minimum:

The verification of the relevant network communication paths.

The behaviour under communication loss and restoration, where applicable.

The verification of network redundancy functions, where applicable.

The verification that the QPS can remain in a safe and operable state if external communication links are unavailable, where applicable.

The Contractor shall demonstrate the correct continuity and functionality of the control cabinets and I/O chains during the SAT. This shall include, at minimum:

The continuity between FAT-validated and SAT-validated cabinet functions, where applicable.

The validation of the relevant I/O signals, command paths, status indications, and permissives.

The validation of the relevant sequence execution from the QPS:CIS perspective.

The demonstration of the relevant manual, maintenance, and degraded operating modes, where applicable.

The Contractor shall demonstrate the correct behavior of the QPS:CIS protection and interlock mechanisms during the SAT. This shall include, at minimum:

The verification that all relevant interlocks prevent unsafe commands or sequences.

The verification of trip propagation and latching behavior.

The verification of reset procedures for trips and interlocks.

The verification of permissive chains required for equipment start or operation.

The verification of safe-state transitions when protection signals are activated.

The verification of safe-state behaviour in case of loss of power, where applicable.

The Contractor shall demonstrate the correct behavior of the field devices controlled or monitored by the QPS:CIS during the SAT. This shall include, at minimum:

The verification of the correct operation of sensors, transmitters, and switches connected to the system.

The verification of the correct operation of actuators such as valves, drives, heaters, and compressors where applicable.

The verification that field-device feedback signals correspond correctly with issued commands.

The verification of device fail-safe positions and behavior.

The Contractor shall demonstrate the capability of the QPS:CIS to recover from a loss of power and to support black-start procedures.

This shall include the verification of the correct restoration of the relevant control-system functions, sequences, and operator functions following power restoration.

The Contractor shall demonstrate the correct behaviour of the QPS:CIS data-handling functions during the SAT. This shall include, at minimum:

The alarm management behaviour.

The historian and data logging behaviour.

The time-synchronisation behaviour, where applicable.

The Contractor shall demonstrate the readiness of the external interfaces of the QPS:CIS during the SAT. This shall include, at minimum:

The readiness of the interface towards MIT services, where applicable.

The readiness of the interface towards the MCS.

The readiness and correct behaviour of the interlock interfaces towards the MIS.

Where the actual external system is not available during the SAT, the Contractor shall demonstrate the interface by means of an agreed simulation, emulation, or equivalent test method.


# Other deliverables

# Fluid Inventory
The Contractor shall provide all the Helium inventory required by the QPS itself during performance of the Contract, including any replenishment required during this period.

If LN2 Precooling is implemented (§4.2.5), the Contractor shall provide all the LN2 inventory required by the QPS itself during performance of the Contract, including any replenishment required during this period.


# Special tooling
The Contractor shall identify, document, and supply all proprietary, special, and operational tools and equipment required for operation, installation, commissioning, and maintenance.


# Spare Parts
If Contingent Part 1 is activated, the Contractor shall supply strategic spare parts required to support the first five (5) years of operation.

The spare parts shall include, at minimum, spare parts for operationally critical components with long procurement lead times, including but not limited to:

Turbines

Cold compressors

Warm compressors

All spare parts shall

be fully traceable to qualified manufacturers

be fully compatible with the original design, performance, and safety requirements of the QPS.

In their Offer, the Applicant shall provide the following lists:

Strategic Spare Parts List, indicating all spare parts included in Contingent Part 1, and specifying for each item:

unit price

procurement lead time.

Critical Components List, specifying the unit price, procurement lead time, and shelf life for all cost-relevant and/or operationally critical items that meet any of the following criteria:

a mean time between failures (MTBF) of less than ten (10) years, or

a projected replacement rate of two (2) or more times within the QPSs lifetime (RTM-055).


# After-Sales Services
The Contractor shall provide After-Sales Services for the full Lifetime of the QPS. The After-Sales service shall include at least (but not be limited to) the services stated below:

Helpdesk offers remote technical support, available on Business Days during normal working hours (from 7:00 am until 19:00 CE(S)T) via telephone, MS® Teams, or other commonly available communication tools.

Technical field service, available to provide technical support at the MINERVA site.

The technical support shall provide fault identification/analysis and troubleshooting, as well as universal support, for all and any aspects of the QPSs, including but not limited to maintenance, technical assistance during integrated user commissioning, software & firmware, etc.

Following a request for support from SCK CEN, the actions and respective response times in case of a fault shall be:

Complete the fault identification and analysis, and establish the strategy to realize the solution, including a preliminary cost and time estimate:

Maximum 3 Business Days after SCK CEN’s request for support in case presence at the MINERVA site by the Contractor is not required for fault identification/analysis.

Maximum 5 Business Days after SCK CEN’s request for support in case presence at the MINERVA site by the Contractor is required for fault identification/analysis.

The Contractor shall propose a solution which implies as little downtime as reasonably possible for the operation of the LINAC.

Submit a formal quote for the solution:

Maximum 3 Business Days after completion of the previous step (fault identification/analysis completed; strategy for solution established).

This quote shall clearly state (i) technical description of the proposed solution; (ii) price for the realization of the proposed solution; and (iii) the lead time for the realization of the proposed solution.

Notwithstanding these stipulations, the Contractor shall at all times provide the solution without undue delay.

In the offer, the Applicant shall provide the following information as regards the after-sales service:

Organization of the after-sales service – at least a concise description of the approach to handling customers’ requests and an overview of the available staff must be given.

Procedure to be followed for requesting after-sales service – at least a comprehensive description of how the helpdesk can be contacted (including all relevant information such as contact data (telephone, email or equivalent) and availability) must be given.

Pricing of the after-sales service – at least the labour costs (hourly rates) must be clearly stated; any spare parts or Components needed in view of the after-sales service shall be remunerated according to the price list for spare parts.

The hourly rates shall be declared per discipline, including at minimum:

process / cryogenic engineering,

control and automation systems,

electrical engineering,

mechanical engineering,

software and firmware support.

In the offer, the Application shall provide estimates of typical expected hours for typical maintenance activities.


# Technical Documentation
The Contractor shall supply all documentation related to this Contract. To this end, the Contractor shall produce technical “Files”.

Files shall function as structured repositories for documentation and substantiating evidence.

Where a requirement specifies substantiation, demonstration, or verification, the corresponding documentation shall be included in the relevant File.

The Contractor shall, as a minimum, produce the Files specified in this section (§4.16).

For each File, the Contractor shall:

Define the File structure and level of breakdown based on its own expertise and established engineering practices.

Define internal grouping of documentation within a File (e.g. thematic sections or substantiation packages) to facilitate traceability and review.

Communicate the preliminary File structure to SCK CEN at an early state for iteration and feedback.

The Contractor shall submit each File for review and approval to SCK CEN.

Activities may only commence once the respective File has been approved by SCK CEN.

Throughout the performance of the Contract, the Contractor shall update the different Files based on the return of experience gained as the Contract progresses.

Each update shall be (re-)submitted to SCK CEN for approval.

Each change shall result in an updated version number.

For each component, it shall be fully traceable which version of the File was applied for each (sub-)step of the Contractual Phases.

Each File shall include, at minimum:

An overview of all documents (including version) which are included in the respective File.

The Unique Identifier of the Element or Instance, whenever applicable.


# Engineering File
The Contractor shall produce an Engineering File.

The Engineering File shall include all documents describing the engineering basis, design choices, calculations, analyses, models, and integration results applicable to the QPS.

The Engineering File shall cover, at least, the following aspects:

Design decisions for the key Parts and Elements of the QPS, including their technical justification.

Sizing results for the relevant process and hydraulic Parts, including the supporting calculations.

Design verification results, including the associated substantiating documentation, such as calculation notes, simulation results, and analysis reports.

Building-integration results, including the relevant 3D CAD models and layout documentation.

Integration results at Element level and at QPS level with the interfacing systems and Parts, including the associated substantiating documentation.

Availability and reliability assessments, including the treatment of LOOP events.

Technical risk assessment results, including:

The assessment of process, human, and environmental safety risks.

The description of the protective measures implemented to eliminate or mitigate the identified risks.

As part of the Engineering File, the Contractor shall provide the technical data and design datasheets of the critical components required to enable SCK CEN to model the complete cryogenic system, including the cryogenic plant, in simulations.

This shall include, at minimum, the relevant data for heat exchangers, piping, rotating machines, and valves.

The level of detail provided shall be sufficient to support system-level simulation by SCK CEN.

Where the detailed data is subject to intellectual-property restrictions, the Contractor shall provide a simplified representation with sufficient fidelity for the intended simulation use by SCK CEN.


# Manufacturing File
The Contractor shall produce a Manufacturing File.

The Manufacturing File shall include all documents describing the processes, procedures, plans, drawings, and technical data applicable to the manufacturing, assembly, testing, handling, packaging, and transportation of the QPS.

The Manufacturing File shall cover, at least, the following aspects:

3D CAD models, 2D drawings, and corresponding Bills of Materials (BOMs), including:

the details of the electrical wiring, cryogenic circuitry, and Instrumentation.

P&IDs.

Procedures for each manufacturing and assembly step of the Elements, and for any associated process, such as cleaning, spatial referencing, and wiring or mounting of the Instrumentation, specified to an appropriate level of detail to ensure correct execution.

Technical documentation of all Parts, including data sheets, certificates, calibration reports, and equivalent technical records.

All documentation received from the Original Equipment Manufacturer (OEM) for Commercial Off-The-Shelf (COTS) equipment.

Where the original documentation is not in English, the Contractor shall provide an accurate English translation together with the original.

Design documentation for custom tools or equipment intended for installation or maintenance, including at minimum CAD models, drawings, and production plans, with sufficient detail to allow SCK CEN to have such tools or equipment built-to-print.

Protocols for all QA/QC activities during manufacturing and assembly, specified to an appropriate level of detail to ensure correct execution.

The FAT Programme.

Procedures for handling, packaging, and transportation.

The FMECA in accordance with IEC 60812:2018, covering at minimum manufacturing, assembly, storage, packaging, and transportation.

The technical data and design datasheets of critical components, including heat exchangers, piping, rotating machines, and valves, with sufficient detail to allow SCK CEN to model the complete cryogenic system, including the cryogenic plant, in simulations.


# Installation File
The Contractor shall produce an Installation File. The File shall differentiate between,

Installation activities specific to each physical location (e.g. Coldbox Room)

Installation activities related to the QPS, including its integration into the MINERVA facility (buildings and infrastructure).

The Installation File shall contain all information that is required to correctly position, install, and test each Element. It shall cover, at least, the following aspects:

3D CAD models and 2D layouts of the final building and system integration.

Installation procedures (i.e. placement of an Instance, Internal Interface connections, External Interface connections).

Protocols for all QA/QC activities during the Installation.

SAT Programme.

The Contractor shall add their “Health, Safety and Environmental Plan” to the Installation File.

Said plan shall describe all (safety) measures, specified to an appropriate level of detail to ensure their proper implementation, that the Contractor shall implement and adhere to during their presence on the MINERVA site. The Contractor’s Health, Safety and Environmental Plan shall comply with the MINERVA Health, Safety and Environmental Plan


# Quality Control Report
The Contractor shall produce a Quality Control Report (QCR)

The QCR shall include the quality-control records, traceability information, and deviation records applicable to the QPS.

The Quality Control Report shall include, at minimum:

All results and records of all conducted QC activities, including tests, measurements, and inspections.

A complete report of all identified deviations arising during the Contractual Phases, including the related processes and their resolution status.

For the purpose of the QCR, the term installation shall also include the establishment of all Internal and External Interfaces of the Instance. For Internal Interfaces, the corresponding information shall be included in the QCR of both affected Instances.

The Quality Control Report shall include, at least, the following aspects:

The Manufacturing File version(s) applied for each manufacturing step.

The Installation File version(s) applied for each installation step.

The identification, such as batch numbers or serial numbers, of all Parts used to manufacture and install the Instance, to ensure full traceability.

The complete QC documentation for all Parts and materials used to manufacture and install the Instance.

Where applicable, the material certificates in accordance with EN 10204, including especially type 3.1 and type 3.2 certificates.

A detailed log of each manufacturing, packaging, transportation, and installation step, including the relevant process parameters.

For packaging and transportation, a log of any loads or events that may affect the functionality of the Instance. At minimum, the state of the transportation-monitoring equipment shall be documented before and after transportation.

A photographic log of the Instrumentation located within the insulation vacuum environment, in accordance with §RTM-095

The Spatial Referencing information.

The QC results and records, in accordance with §8..

The reporting of deviations, including an overview of all Non-Conformity Reports (NCRs).

SCK CEN shall have the right to access the QCR at any time during Contract performance.

The results of each QC activity shall be uploaded to SCK CEN’s designated document-management system within 5 Business Days after performance of the activity.


# FAT Report
The FAT Report shall document the execution and results of each individual test stipulated in the applicable FAT Program and shall state whether the Instance has passed or failed the FAT.

The FAT Report shall include, at minimum:

The Manufacturing File version(s) according to which each FAT test has been performed.

The results and records of each individual test.


# SAT Report
The SAT Report shall document the execution and results of each individual test stipulated in the applicable SAT Program.

The SAT Report shall include, at minimum:

The Installation File version(s) according to which each SAT test has been performed.

The SAT Programme

The results and records of each individual test, including but not limited to, the executed procedures, test conditions, measured data, derived results, deviations, non-conformities, and compliance assessment.


# Commissioning Plan
The Commissioning Plan shall contain all information required to duly perform the commissioning of each individual Instance, each sub-system, and of the combined total system (QPS including QPS/CIS).

The Commissioning Plan shall cover, at minimum:

An overview of all tests to be performed during commissioning.

For each test, the test procedure specified to an appropriate level of detail to ensure proper execution.

A matrix of roles and responsibilities for commissioning and acceptance, identifying at least the Commissioning Manager, QA, and any third-party bodies.


# Commissioning Report
The Commissioning Report shall document the execution and results of each individual test stipulated in the applicable Commissioning Plan.

The Commissioning Report shall include, at minimum:

The Commissioning Plan version(s) according to which each commissioning test has been performed.

The results and records of each individual test.


# As-built File
The As-Built File shall consolidate the complete final “as-is” implementation of the QPS at the MINERVA site and shall form part of the SAT deliverables.

The As-Built File shall contain all technical documentation reflecting the final installed configuration and shall include, at minimum:

3D CAD models and 2D drawings of the final implementation.

The implemented physical details of electrical wiring, cryogenic circuitry, instrumentation, and all other information required for operation, maintenance, and repair.

Per Instance, a list of deviations from the original design that occurred during manufacturing, installation, and/or commissioning.

The Contractor shall submit the As-built File as part of the SAT.


# Technical File
The Contractor shall provide Technical Files in accordance with §9.1.

The File shall be delivered as a dedicated, self-contained documentation package compiled explicitly for that purpose.


# VLAREM Technical File
The Contractor shall provide the VLAREM Technical File in accordance with VLAREM II (§9.1).

The File shall be delivered as a dedicated, self-contained documentation package compiled explicitly for that purpose.

The File shall be delivered ready for successful submission to the respective authorities.


# Safety and Protection Requirements

# Machine Protection
The QPS shall be designed to prevent, detect, and mitigate conditions that could damage the QPS, so far as reasonably practicable.

The Contractor shall perform a risk analysis (e.g. HAZOP, FMECA, or an equivalent methodology) and shall implement the required mitigation measures.

The corresponding report shall be submitted as part of the Conceptual Design Report and, where necessary, updated in the Detailed Design Report.

The risk analysis shall include, at minimum:

QPS external interfaces

Loss of utility (e.g. electricity, water, compressed air, …)

MIS Interlock Interface failure

Operation outside the nominal interface parameters and defined operational window

Operator error

Any QPS internal failure, such as loss of insulation vacuum or a QPLANT trip

The Contractor shall design, implement, and validate fail-safe hard-wired interlock circuits to prevent damage to the QPS.

These interlock circuits shall remain functional in the event of relevant control-system failures and loss-of-utility events.

The QPS shall not rely on the MIS for internal QPS interlock processing, but only for interlock connections to systems outside the QPS.

The QPS:CIS shall expose the interlock status of the QPS to the MCS control interface.

Electrical contacts associated with the hard-wired interlock sensors (flow, pressure, temperature, level, valve-end switches, etc.) shall be wired “positive-logic” (open = abnormal/trip) so that any loss of signal, power, or cable integrity forces the affected component to a safe state.

The QPS shall include redundant measurement channels and stand-by heaters for all inaccessible components and for components whose failure would jeopardize machine integrity.


# Personnel Safety
The Contractor shall comply with the following boundary conditions:

The QCELLs have a dedicated bursting disk venting system that is not connected to the QPS and not within the scope of this Contract.

SCK CEN shall be responsible for the fire detection and fighting equipment in all the QPS related rooms/areas.

SCK CEN shall be responsible for the access control system to all the QPS rooms/areas

The treatment of safety aspects shall make a clear distinction between

hazards (detectable physical conditions),

consequences (physiological or mechanical outcomes)

mitigation layers (engineering, organizational, and procedural).

The Contractor shall design, implement, supply and document all safety measures, including engineered safety devices, personal protective equipment (PPE), and operational procedures, to eliminate, reduce, or mitigate safety hazards, including but not limited to the cryogenic ones:

Oxygen-Deficiency Hazard (ODH) with Asphyxiation / anoxia as the ultimate physiological consequence of unmitigated ODH.

Cold burn (cryogenic frostbite).

The Contractor shall document the hazard analysis, selected mitigation measures, detection and protection devices, PPE requirements, and associated procedures.

The Contractor shall be responsible for any required 3rd party for inspection or certification (e.g. PED auditor).

Any Cold helium volume shall be protected by safety devices in accordance with EN 17527 (supplemented, where applicable, by API 520/521/580 for warm service).

Any cold volume that can be isolated by valves and all insulation vacuum volumes shall have dedicated safety devices.

The Contractor shall submit a project-specific safety file for review and approval prior to start of site activities. The safety file shall include, as a minimum:

PIF (Post Installation File) inputs and residual risk records for handover.

No installation, construction, testing, or commissioning activities shall start until the Safety File has been reviewed and accepted by SCK-CEN and the appointed Safety Coordinator.

Annex 12 – Safety Charter, which shall be issued by SCK-CEN and signed by all participating Contractors and subcontractors.


# Oxygen-Deficiency Hazard
The Contractor shall supply a substantiated proposal for the locations of Oxygen-Deficiency Hazard (ODH) monitors on all rooms housing the QPS equipment. The proposal shall be based on the following boundary conditions:

The ODH monitors will be installed by SCK CEN

The ODH monitors will be fixed, compliant with EN 50104:2019, and rated to performance class SIL-2

The ODH monitors will be integrated by SCK CEN into the MINERVA wide site alarm and access control system

The Contractor shall provide all technical input related to the QPS required for SCK CEN to complete the ODH system certification.

The Contractor shall integrate the ODH monitor signal(s) into the QPS:CIS to perform mitigating actions.

The Contractor shall define the interface location where SCK CEN shall provide the ODH monitor signals to the QPS. The interface shall be either at:

each monitor (signal splitters scope of SCK CEN)

a centralized location of a SCK CEN safety-interlock aggregator.

The Contractor shall perform all the required functional testing of this integration during standalone commissioning and demonstrate it during the SAT.

Evidence of such verification shall be included in the Commissioning File and Acceptance Test File.


# Schedule

# Contract Phases
Contractual performance shall proceed in phases. A phase will only be considered as completed when all associated deliverables (including documentation) are approved by SCK CEN.


# Conceptual Design (L1)
In this phase, the Contractor shall, at least, perform the following activities:

Establish the project management baseline (Management Dashboard & underlying processes, Quality Assurance Program and Risk Management Plan).

Develop the conceptual design, verifying/ validating conformance with technical specifications, define specific requirements for buildings and utilities.

Prepare the Conceptual Design File.


# Detailed Design (L2)
In this phase, the Contractor shall, at least, perform the following activities:

Develop the detailed design, verifying/ validating conformance with technical specifications, define the list of components (incl. procurement specifications, manufacturing drawings), setting final requirements for buildings and utilities, developing plans and procedures for the next phases (e.g.: MIP, packaging and transportation plan, installation plan).

Prepare the Detailed Design File.


# Construction (L3)
In this phase, the Contractor shall, at least, perform the following activities:

Perform the procurement, assembly, and manufacturing of all components and services necessary for performing the Contract

Prepare final plans and procedures for Phases L3 to L6

Execute tests and inspections,

Execute the FAT


# Installation (L4)
In this phase, the Contractor shall, at least, perform the following activities:

Transportation to SCK CEN

Incoming inspections

Installation of the QPS


# Standalone Commissioning (L5)
In this phase, the Contractor shall, at least, perform the following activities:

Stand-alone commissioning of the QPS

Training of SCK CEN staff


# Site Acceptance testing (L6)
In this phase, the Contractor shall, at least, perform the following activities:

Execute the SAT


# Provisional Schedule
In their x, the Applicant shall submit a detailed schedule following these phases according to its own expertise and experience and propose. In doing so, the Applicant shall take into consideration the preliminary schedule in Table 22. The Applicant may add (to a reasonable extent) additional milestones as they think appropriate.

Table 22 Provisional contract execution milestones.

“ED” = Earliest Date, “LD” = Latest Possible Date, “M” = months, “wks” = weeks, 
“BD” = Business Days, “CD” = Calendar Days.


# Hold and Witness Points (HP / WP)
To ensure quality control, specific verification points are mandatory. Work shall not proceed beyond a Hold Point without written approval from SCK CEN.

Upon receiving the Contractor’s finalized project schedule and Manufacturing and Inspection Plan, SCK CEN will define HP(s)/WP(s) and will duly notify the Contractor of such decisions. This will include at least the following:

The end of each Contract Phase is a mandatory Hold point

The FAT approval in view of Installation (per Component)

SCK CEN has at its disposal a maximum of 30 Calendar Days (60 Calendar Days when involving (an) external partner(s)) to complete all formalities) concerning approval of a certain Hold Points. Nonetheless, SCK CEN shall always aim to give feedback to the Contractor concerning the HPs without undue delay. The envisaged lead time is 10 Business Days (to be determined considering SCK CEN’s and/or its collaboration partner’s days of closure)


# Contract Performance

# General Organization
The Contractor shall assign a member of its staff to be responsible for the follow-up of the Contract (further referred to as “Project Manager”). The Project Manager shall be responsible for planning, organizing, monitoring, and controlling, and directing the performance of the Contract, to ensure that the Contract is accomplished on time, within budget, and compliant to the requirements laid down in the Contract.

The Contractor shall notify SCK CEN in writing in case a different Project Manager is appointed. Replacement of the Project Manager is subject to prior written approval by SCK CEN. In case of replacement, the substitute shall always have a level of education, skills, and experience equivalent to or better than the original resource proposed for this role.

At the conclusion of the Contract, SCK CEN shall designate the Leading Officer for the Contract and inform the Contractor. The Contractor shall be notified of any change in writing.

Regarding the practical follow-up of the Contract, SCK CEN reserves the right to have itself represented by a third party of its choice, acting on its behalf (further referred to as “Representative(s)”).In this respect, SCK CEN grants to the Representative(s) the same rights as SCK CEN have accrued under the present Contract and the Contractor shall give effect thereto. The Contractor shall grant the Representatives the same access rights (physical access, document access, ...) as have been contractually instated for SCK CEN. Notwithstanding the foregoing, SCK CEN will remain the sole principal to the Contract and therefore:

any approval/acceptance/equivalent step which has been contractually set, shall only be approved, respectively accepted, if and to the extent that SCK CEN has confirmed its approval, respectively acceptance, of such step in writing.

any decision to deviate from the terms and conditions as have been contractually agreed upon, may only be implemented after having obtained approval thereto from SCK CEN in writing.


# Communication
All communication, including - but not limited to - tender documents, offers, technical documentation, any correspondence, and all meetings, related to the Contract, shall be in English.

Any information that a Party considers significant enough to bring to the attention of the other Party, shall be deemed correctly communicated if exchanged in writing (e-mail suffices) between the designated persons in charge of the general organization of the Contract.

Any contract-related request – of technical or any other nature – directed by SCK CEN to the Contractor shall be adequately responded to within five Business Days. If such request cannot be answered within this lead time, e.g., due to a technical question requiring additional time to be answered, the Contractor shall at least communicate (within this lead time) when SCK CEN will receive the answer.

If the Contractor anticipates any delays or difficulties in meeting the schedule, planned deliveries or any other milestone within its offer, it shall promptly notify SCK CEN.


# Document Management
All project-related documents shall be uploaded to the Coreshare platform managed by SCK CEN..

Where applicable, documentation shall be provided in one of the following formats: MS Word, MS Excel, PDF, STEP, DXF, or EPLAN.

All documents shall follow the specified file-naming conventions and metadata requirements to ensure clear identification, version control, and lifecycle management.

The Contractor shall maintain version control of the documents received from SCK CEN.

When an updated version of a document is received, the previous version shall be removed from circulation as soon as reasonably possible.

These documents shall be made accessible to the Contractor’s personnel and subcontractors only on a need-to-know basis, for the purpose of the Contract, and only for as long as required.


# Contract Management

# Progress Dashboard
The Contractor shall implement a digital dashboard giving SCK CEN a snapshot up-to-date information on the status and progress of the Contract. The information shall be continuously (at least monthly) updated with the latest information. The Contractor shall produce and submit monthly progress reports to SCK CEN at least three Business Days prior to the monthly progress meeting. If comments or revisions arise during the progress meeting, the Contractor shall issue an updated version five business days after the meeting. The dashboard shall, as a minimum, include the following:

A concise summary of the Contract progress

Updated open-action-register.

Work completed since the last update of the dashboard including encountered difficulties and improvement proposal.

Work scheduled until the next update of the dashboard

Monitoring of the schedule

Updated issue register, and any other points-of-attention identified during the performance of the Contract

Updated Change register

Updated non-conformity register

Updated Risk register

In the offer, the Applicant shall include a concise description of the dashboard as well as the underlying management processes. This description shall include sufficient detail to demonstrate compliance with the requirements.


# Meetings
Meetings shall take place at either of below locations:

The Contractor’s premises.

SCK CEN: Boeretang 200, 2400 Mol, Belgium or Avenue Hermann-Debroux 40, 1160 Brussels, Belgium.

Any other location mutually agreed upon by the Contractor and SCK CEN, such as the premises of the deliverable’s component Contractors.

In audio or video conferencing.

The Contractor shall ensure that all relevant information for these meeting is made available to SCK CEN at least three Business Days in advance including, but not limited to, meeting agenda, reports, and presentations. The Contractor shall draft the minutes of these meetings and submit them to SCK CEN for review and approval within 5 Business Days following the meeting.

Travel expenses shall be paid by the party who travels.


# Progress Meetings
The Contractor shall organize at least monthly Progress meetings between the Contractor and SCK CEN.


# Milestone Meetings
The Contractor shall organize at least the following Milestone Meetings:

Kick-Off meeting (M11)

This meeting is a “face-to-face” meeting to be held at SCK CEN in Mol.

At the end of each Contract Phase

SAT completion.

This meeting is a “face-to-face” meeting to be held at SCK CEN in Mol.


# Technical Review Meetings
The Contractor shall organize Technical Review Meetings with the necessary stakeholders to define the technical baseline and identify any evolutions between reviews.


# Risk Assessment & Management Plan
In the offer, the Applicant shall submit a preliminary Risk Assessment & Management Plan. It shall contain all risks with a severity that are bound to compromise the successful completion of the Contract either in terms of schedule, budget, or technical requirements, irrespective of probability. It shall present a top-level view of the mitigation strategy that the Applicant shall implement during contract execution, for all the risks that have been identified as unacceptable.

During contract execution, the Contractor shall detail, complete, and continuously maintain the Risk Assessment & Management Plan. The Contractor shall continuously monitor, identify, and document any new risks that might threaten the successful completion of the Contract in any way. The Contractor shall duly implement the mitigation strategy in accordance with this plan.


# Factory Access
During the performance of the Contract, SCK CEN and/or its representatives shall have access during normal working hours to (all) the location(s) where (part of) the Contract is being performed (including Contractor’s and Subcontractors' premises). The Contractor shall be notified of any site visit at least five Business Days in advance.


# General Quality Assurance and Control
Prior to beginning any other work, the Contractor shall submit a detailed Quality Assurance & Control Program (QAP) to SCK for approval, demonstrating compliance with the QA/QC requirements set out in this document. Any required change to the QAP during Contract execution shall be requested from SCK CEN via a Change Request. The QAP shall include e.g. Manufacturing and Inspection Plan / Inspection and Test Plan, Responsibility Matrix, Change Register, Non-Conformity Register, audit reports, FAT reports, SAT reports, commissioning reports, and installation dossiers

In the offer, the Applicant shall:

submit a preliminary version of the QAP outlining the quality control process that will be implemented during Contract execution.


# Quality Assurance

# General requirements
The Contractor shall implement and maintain a Quality Management System compliant with ISO 9001 for all activities under this Contract.

During the warranty and after-sales period, the Contractor shall maintain application of its ISO 9001 Quality Management System to all services provided under this Contract, including maintenance, repairs, modifications, and upgrades. Non-conformities, changes, and configuration updates during the warranty period shall be managed according to the same Non-Conformity and Change Management processes as applied during the project phases.

The Contractor shall demonstrate how its existing ISO 9001:2015 Quality Management System is applied to this specific QPS project.


# Quality Management System
Any Subcontractor shall also be ISO 9001 certified for their scope of work by a nationally accredited body. In absence of an ISO 9001 certified QMS, an equivalent system may be accepted after written approval from SCK CEN. If deemed necessary, SCK CEN may request an audit.

The Contractor shall inform SCK CEN of any change in certification during execution of the Contact.


# Quality Assurance Program
Quality assurance and control activities, including QAP, MIP, inspections, and requirements fulfilment and conformity assessment, shall be implemented.

The inspections, measurements, and testing activities described in the Contract are mandatory but comprise only the minimum required. These activities are not intended to supplant any control, measurement, examination, inspection, or test usually performed by the Contractor to ensure the quality of the product.

The Quality Assurance Program (QAP) shall include User Training and Competence Transfer as controlled activities, with defined inputs, outputs, responsibilities, and records.


# Quality Assurance Plan (QAP)
Prior to beginning its work, the Contractor shall submit a QAP for review and approval by SCK CEN demonstrating compliance with the requirements set out in the Contract. It shall cover at minimum the following topics:

Requirement traceability Matrix.

Test Plans & Reports.

Functional safety lifecycle management.

Certificate management.

Change and non-conformance management.

Document management.

In their offer, the Applicant shall include a preliminary version of this QAP.

The Contractor must adhere to the QAP and shall apply the mandatory QA/QC measures throughout the performance of the Contract. In case a deviation is required from one or another condition set out in the Contract, such request shall be clearly stated in the QAP.

Contractors who subcontract work to a subcontractor must take appropriate measures to ensure that the subcontractor complies with the QAP.


# Qualification of personnel
The Contractor shall ensure that all personnel involved in the performance of the Contract is qualified and trained to the required competencies to deliver results complying with SCK CEN requirements and specifications. Special training and qualifications are specifically required for personnel responsible for welding and any on site rigging activities.

The Contractor shall keep records of personnel qualification and make them available to SCK CEN free of charge upon simple request.

The Contractor shall ensure that all personnel who have direct contact with SCK CEN can understand as well as express themselves fluently in English, both orally and in writing.

Training activities contributing to operational handover shall be performed by qualified Contractor personnel and shall result in demonstrable qualification of SCK CEN personnel for defined operational and maintenance roles.

While §7.1.4 mandates qualification of Contractor staff, the Contractor shall also define the competency matrix required for SCK CEN staff. The Contractor shall issue Certificates of Competence to SCK CEN personnel upon successful completion of the training modules, validating their ability to take over operations.

All User Training, competence transfer, and operational handover activities shall be implemented in alignment with the Quality Assurance framework.


# Document Retention and Submission Requirements
The Contractor shall retain all documents created under the Contract for a minimum period of ten (10) years, or for the duration required by applicable law, whichever is longer.

All documents submitted to SCK CEN shall:

be identified by a unique document code, version number, and document title.

include a reference to the Contract unless the document was created independently of the Contract.

be version-controlled and include a change log listing the modifications applied in each revision.

be reviewed and approved by competent and authorized personnel prior to submission to SCK CEN.

be submitted in digital format, compatible with commonly available application software for Microsoft Windows OS and suitable for transmission via the internet.


# Change Management
Proposals for change to the project, its scope of work and/or previously approved deliverables, either initiated by the Contractor or by SCK CEN, shall be analysed and documented (in a “Change Request”) by the Contractor and submitted for approval to SCK CEN.

A Change Request shall at least contain following information:

the initiator of the change

the justification for the change

the impact of the change (on product and/or (related) service(s),

safety,

risks,

contract price and schedule),

the description of the change and the plan of implementation.

The Contractor shall include the Change Request template in annex to the QAP.

Only Change Requests approved by SCK CEN may and shall be implemented.

The Contractor shall create and maintain a Change Register, accessible to SCK CEN, in which all Change Requests shall be logged, including at least:

a unique identifier, title, date of issuance,

monetary impact (if any),

impact on the Contract schedule (if any)

information about the status of the decision (proposed, on hold, rejected, approved, withdrawn).


# Non-Conformity Management
A Non-Conformity is defined as any non-compliance with, or deviation from, any of the requirements and/or conformity criteria set forth in the Contract or approved Change Requests.

Deviations from the specifications defined in the Contract, that were not explicitly authorized by SCK CEN in advance in writing, shall be treated as Non-Conformities.

The Contractor shall have a process in place for managing Non-Conformities that arise during the performance of the Contract, including receiving and processing notifications of Non-Conformities from SCK CEN and/or third parties (such as its Contractors or Subcontractors).

In case of a Non-Conformity, the Contractor may not ship, or shall recall at its own risk and expense, the impacted supply. Any steps of the Contract execution, which are (potentially) affected by the Non-conformity, shall be put on hold.-Conformity, shall be put on hold.

The Contractor shall notify SCK CEN in writing of any such Non-Conformities by means of a Non-Conformity Report (NCR). An NCR shall be submitted to SCK CEN as soon as reasonably possible after a Non-Conformity is identified.

An NCR shall cover at least the following aspects:

Detailed description of the Non-Conformity.

Identification of all potentially affected deliverables.

Identified (root) cause(s) including verification thereof.

Proposed corrective actions including their anticipated effectiveness.

Proposed reoccurrence prevention plan (if applicable).

The Contractor shall include the NCR template in annex to the QAP.

Each NCR shall be submitted to SCK CEN for approval. SCK CEN shall be entitled to reject the solution(s) proposed by the Contractor in case SCK CEN deems the solution not useable given the circumstances.

The Contractor shall perform all necessary actions to correct the Non-Conformity (in accordance with the SCK CEN approved NCR) at its own risk and expense. Said necessary actions shall not only concern redoing (parts of) the manufacturing and/or its related processes (assembly, packaging, delivery, …) but shall also entail redoing all QA/QC activities associated therewith. Next to that, if so, requested by SCK CEN, the Contractor shall moreover reimburse SCK CEN for the costs incurred by SCK CEN to have the FAT/SAT of the impacted items redone.

The Contractor shall keep SCK CEN duly informed about the progress of the implementation of the actions identified in the NCR and, if applicable, shall provide a revised schedule identifying the time impact of the implementation of said actions; the Contractor shall minimize the consequences on the schedule in any case.

At the specific request of SCK CEN, to avoid repetition of possible recurring Non-Conformities during the execution of the Contract, or when imposed by the Contractor's quality management system or the QAP, the Contractor shall conduct a root cause analysis of the Non-Conformity. Such an analysis shall:

be documented and submitted for approval to SCK CEN.

include the identified Non-Conformity cause(s).

propose an action plan to minimize the probability of a recurrence.

For actions taking more than 1 month, the Contractor shall provide a regular status report describing the result of implementation according to the due dates in the action plan.

Performing the root cause analysis and implementing any preventive/corrective actions arising therefrom, shall not give rise to any additional compensation for the Contractor.

Any Non-Conformities identified and reported by SCK CEN to the Contractor, as well as any other complaints received by the Contractor from SCK CEN, shall be treated as Non-Conformities and duly documented, investigated, and resolved according to the stipulations under this clause.

Neither the implementation of the procedure on Non-Conformity management, nor the approval by SCK CEN of a Non-Conformity Report, shall waive or reduce the Contractor’s responsibility, according to the relevant stipulations of the Contract, to indemnify and hold SCK CEN harmless against all losses, damages, and costs (e.g. due to delay on the schedule) arising from such Non-Conformity.


# Audits
SCK CEN shall be entitled to conduct, or to have carried out by a third party on its behalf (procured at SCK CEN’s own cost), an audit of Contractor/its Subcontractor’s premises, equipment, procedures to assess the ability of Contractor/Subcontractor to comply with the requirements of this document and the Contract. SCK CEN may request such audit when at least one of the following conditions is met:

to qualify a Contractor/Subcontractor which is not ISO 9001 certified.

to address performance issues.

SCK CEN shall inform the Contractor in advance of the audit and shall take all necessary steps not to unduly interfere with the performance of Contractor’s business operations. SCK CEN shall provide an audit report within two weeks of completing the audit. The Contractor shall respond within two weeks with an action plan to address the identified Non-Conformities.


# Quality Control

# General requirements
The Contractor shall perform quality control in accordance with recognized best practices.

The Contractor shall assume full responsibility for the quality of all deliverables and documentation, as well as all procured components, materials, and services. The Contractor shall ensure that the Contract is performed in accordance with all applicable regional, national, and international laws, regulations, industrial codes, standards, and Good Industry Practices.

Additionally, to ensure compliance with the requirements outlined in this document, the Quality Assurance Program (QAP) shall, at a minimum, include the qualification and validation requirements specified herein.

All measurement and testing instrumentation used during the performance of the Contract shall have the appropriate certification and shall be regularly calibrated to ensure appropriate accuracy and precision. SCK CEN reserves the right to request a measurement system analysis and/or proof of calibration.


# Declaration of conformity with all requirements
Together with the delivery, the Contractor shall submit to SCK CEN a Declaration of Conformity certifying that all the requirements have been met. Such declaration shall include at least the following information:

Identification of the deliverable, including the purchase order reference no. and Contract reference.

A list of approved changes, waivers, or deviations from the specifications.

Such declaration shall be dated and signed by a duly authorized representative of the Contractor responsible for quality assurance as shown in the approved QAP.


# Applicable legislation, Codes and Standards
The legislation, codes and standards listed below define both technical compliance obligations and competence and verification expectations.

Compliance with a listed standard shall not be limited to design calculations or certificates but shall, where applicable, be reflected in:

installation practices,

commissioning and acceptance testing,

training material and competence transfer,

maintenance strategy.

The Contractor shall organise the applicable codes and standards in a hierarchical manner where management-system standards (e.g. ISO 9001) act as parents to project-level requirements and technical standards (e.g. PED, EN 13480, EN 13445, IEC functional-safety standards).

In the offer, the Applicant shall include a list of the applied codes, rules and standard for the design, manufacturing, and testing of the QPS.


# Applicable legislation
The Contractor shall provide an EU declaration of conformity for the QPS and CE mark all QPS components.

The Contractor shall identify all EU directives applicable to the QPS and ensure compliance with said EU directives. The directives listed below are identified by SCK CEN as a minimum requirement but does not exclude other directives from being applicable:

Low Voltage Directive 2014/35/EU

Machinery Directive 2006/42/EC

EMC Directive 2014/30/EU

Pressure Equipment Directive (2014/68/EU)

EU Eco-design Directive 2009/125/EC

For pressure equipment and associated piping, the Contractor shall assume the role of Manufacturer (or equivalent designation under the applicable pressure equipment legislation and standards) and shall be responsible for design, manufacturing, conformity assessment, marking, and documentation in accordance with Pressure Equipment Directive (2014/68/EU). These responsibilities shall be clearly reflected in the Responsibility Matrix and the Codes and Standards Register which form part of the continuously updated QAP.

The Contractor shall identify and apply all applicable norms and directives.

To demonstrate conformity with the applicable EU directives, the Contractor shall submit the Technical File well before the shipment of the first QPS parts. The Technical File shall include at least:

A general description of the QPS

An overall drawing of the product, as well as other drawings to cover specific aspects of the product, such as circuit diagrams. The drawings shall, where appropriate, be accompanied by descriptions and explanations to understand the product.

The description of the protective measures implemented to eliminate identified hazards or to reduce risks and, when appropriate, the indication of the residual risks associated with the QPS.

The list of standards and other technical specifications used to show compliance with the essential requirements outlined in the EU directive(s).

Instructions and other information for the safe use of the product covering at least, but not limited to, handling, shipping, installation, integration, operation, maintenance, de-commissioning, disposal, in English, and Dutch

Where appropriate, copies of the EU declaration of conformity of components incorporated into the assembly.

A copy of the QPS EU declaration of conformity in the original language, in English, and Dutch.

A copy of the nameplate(s) with CE mark.

The Contractor shall identify and document the applicable Belgian and Flemish environmental regulatory requirements and proof or demonstration with compliance for associated with the QPS installation. This shall include, but is not limited to, requirements imposed by local environmental laws specific VLAREM II (Environmental Permit Regulation).

According to VLAREM II, e.g. a helium inventory of >300 kg triggers an environmental classification. At least, the following studies are required: acoustic study, energy study.

If requested by SCK CEN, the Contractor shall submit an updated version of the Technical File including more detail on specific section to demonstrate conformity with the directive(s) in more detail. This may require adding e.g.:

Full detailed drawings.

Calculation notes,

Test reports, certificates, ...

The Contractor’s Health, Safety and Environmental Plan shall comply with the MINERVA Health, Safety and Environmental Plan [AD_02].


# Asset Management and Maintenance Standards
The Contractor shall apply at least the standards listed in Table 23

Table 23. Asset Management and RCM standards


# Electromagnetic interference
The Contractor shall propose a solution, subject to approval by SCK CEN, to minimize the effects of electromagnetic interference (EMI). The solution shall address shielding, cabling, signal routing, voltage level separation, and earthing strategy.

The EMI mitigation design shall ensure that all instrumentation and control signals operate within their specified accuracy limits under defined electromagnetic environments.

The proposed solution shall comply with the relevant sections of EN 61000-6-2 (Immunity for industrial environments) and EN 61000-6-4 (Emission for industrial environments), or an equivalent standard approved by SCK CEN. The Contractor shall verify correct implementation by at least:

A design dossier including EMI layout drawings and shielding measures,

A wiring and installation checklist verified during site inspection,

And, where applicable, EMC type tests or certificates for sensitive components (e.g., sensors, analysers, PLCs).

To ease diagnostic and checking of measurement chains, knife-switch type terminal blocks or similar cabling interface shall be fitted for input and output signals connections with the QPS:CIS.


# Pressure Equipment & Safety
The Contractor shall comply at least with the standards specified in Table 24.

Table 24. Pressure Equipment and Safety Standards


# Functional Safety & Control
The Contractor shall comply at least with the standards specified in Table 25.

Any system involved in personnel protection shall be designed according to standards IEC 61508 (Functional Safety) or one of the sector-specific derived standards (IEC 62061, IEC 61511) or alternative (e.g. ISO 13849-1).

Table 25. Functional Safety & Control Standards


# Cleanliness & Purity
The Contractor shall comply at least with the standards specified in Table 26.

Table 26. Cleanliness and Purity


# Acceptance and Warranty

# Provisional Acceptance
A Provisional Acceptance Certificate shall be issued by SCK CEN for each deliverable (together with the required documentation), provided that no shortcomings are identified during the provisional acceptance.

The provisional acceptance shall be subject to:

the successful completion of the SAT and

all identified Non-Conformities (e.g., missing, or incomplete documentation) having been duly corrected by the Contractor.


# Warranty Period
The warranty period (the “Warranty Period”) shall start on the date of issuance of the provisional acceptance report and shall end on the date of final acceptance. The Warranty Period shall be at least 3 years.

In-warranty repairs and/or replacement parts shall be warranted for at least one (1) year after execution, or for the unexpired portion of the original Warranty Period of the CRYOPLANT, whichever is longest. Notwithstanding the foregoing, the Warranty Period is suspended for the duration between formal notice by the Contracting Authority to the Contractor on the defect and resolving of said defect by the Contractor.

If the Contractor fails to fulfil its obligations under the warranty, so that final acceptance cannot take place at the scheduled time, the Warranty Period shall be automatically extended, without any right to compensation for the Contractor, until final acceptance takes place.

In the offer, the Applicant shall put forward the price per year to extend the Warranty Period with (an) extra year(s) beyond this minimum of 3 years up to a maximum of 6 years in aggregate (initial Warranty Period + extensions). SCK CEN shall be entitled to impose such additional Warranty Period by issuing a separate purchase order to that extent.


# Warranty Conditions
During the warranty period, the Contractor shall at its own risk and expense remedy any outstanding issues, as well as any shortcomings and defects that were not visible during the acceptance tests.

The Contractor’s methods of solving a warranty issue shall always need to be approved in advance by SCK CEN. SCK CEN reserves the right, at its sole discretion, to not allow for repair and to demand replacement of a defective item.

In case the warranty work needs to be performed at SCK CEN, the Contractor shall consider and comply with SCK CEN’s instructions relating to working hours, access, ..., without being entitled to any additional compensation.

The Contractor’s warranty obligation shall not apply:

to normal wear and tear of the QPS, as well as any associated consumables.

to defects of which the Contractor is notified after the Warranty period, unless SCK CEN can demonstrate that such defect has arisen before the end of the Warranty period in which case such defect shall fall under the warranty obligation.

to failures or defects which the Contractor can substantiate are due to alteration, misapplication, inappropriate use in view of the conditions of use as outlined by the Contractor (if any are provided), and/or maintenance not carried out according to the Contractor’s nominal conditions as set forth by the Contractor, lack of trained maintenance personnel (other than the Contractor’s personnel), operation above rated capacities either intentional or otherwise, or physical damage caused by persons other than the Contractor’s personnel.

During the warranty period, the Contractor shall execute repairs and/or replacements without undue delay at the Contractor’s risk and expense. SCK CEN may request warranty service during non-normal working hours or for services excluded from the warranty coverage as defined herein, provided that SCK CEN shall pay the reasonable overtime premium portion of the non-normal hours worked or the normal service charge, respectively.

In-warranty repairs and/or replacement parts shall be warranted for at least one year after execution, or for the unexpired portion of the original warranty period of the deliverable, whichever is longest.

Notwithstanding the foregoing, the warranty period is suspended for the duration between formal notice by SCK CEN to the Contractor on the defect and resolving of said defect by the Contractor.

If the Contractor fails to fulfil its obligations under the warranty, so that final acceptance cannot take place at the scheduled time, the warranty period shall be automatically extended, without any right to compensation and/or remuneration for the Contractor, until final acceptance takes place.

The Contractor shall keep a register of all interventions that the Contractor performs during the warranty period which can be always consulted by SCK CEN. If SCK CEN can demonstrate a trend of failure occurring during the warranty period, which is not attributable to any inappropriate use of the equipment, this will be considered as a deficiency, and the Contractor shall be liable to replace at his own risk and expense the affected item

In addition to the above rights, SCK CEN shall be entitled to full compensation for all damages incurred in view of these outstanding issues, shortcomings, and/or defects according to the stipulations of the contract.

The warranty as described in this section shall in no way constitute a restriction on the applicable Belgian statutory regulations on hidden defects.

The warranty stipulations regarding warranty shall apply mutatis mutandis to any spare parts supplied under header of this contract.


# Final Acceptance
Initial acceptance occurs after the successful completion of the Warranty Period, at the written request of the Contractor, on the condition that all defects, attributable to the Contractor, regardless of whether they have been identified in the Provisional Acceptance Certificate or during the Warranty Period, have been duly resolved by the Contractor. If the conditions are met, a Final Acceptance Certificate will be issued by SCK CEN within 10 Business Days after receipt of the Contractor’s written request in this respect.


# Appendix

# Cryogenic User Circuitry Model – Boundary conditions
This section defines the boundary conditions required for the implementation of the Cryogenic User Circuitry Model referenced in §4.2.1.1.

The boundary conditions define the assumed thermodynamic states and modelling simplifications at the Cryogenic User interfaces for the steady-state operational scenarios.

The boundary conditions are defined per operational scenario as follows:

For 2K-OP and 2K-SB

CAV Bath

Bath temperature: 2 K (saturated LHe)

vapour quality at inlet (xXM): 17 % (two-phase Helium) (fixed value; model simplification)

vapour quality at outlet: 100 % (saturated GHe)

Heat exchanger

Temperature of returning GHe at HX outlet (TXB): 3.5 K (fixed value; model simplification)

For 4K-SB

CAV Bath

Bath temperature: 4.45 K (saturated LHe)

vapour quality at inlet (xXM): 7.8 % (two-phase Helium) (fixed value; model simplification)

vapour quality at outlet: 100 % (saturated GHe)

Heat exchanger

Temperature of returning GHe at HX outlet (TXB): 4.6 K (fixed value; model simplification)

For 10K-SB

CAV Bath

Supply flows via the filling valve, bypassing the heat exchanger (HX) and JT valve

Supply temperature (before filling valve): 10 K (superheated GHe)


# Cryogenic User Transient Model – Input Data and Thermal Parameters
This section defines the thermo-physical input data required for the implementation of the Cryogenic User Transient Model referenced in §4.2.1.1.

The model represents the user cold masses as two lumped thermal capacities, each including all structural and functional components thermally anchored to the respective circuit:

“Cold Mass,” for all components thermally anchored to the CAV Circuit.

“TS Mass,” for all components thermally anchored to the TS Circuit.

The model accounts for:

Temperature-dependent heat capacity, implemented via tabulated enthalpy values.

Temperature-dependent heat transfer between stages and from ambient. The heat transfer is differentiated into radiative and conductive heat loads.

The thermo-physical input data is provided in the following tables:

Table 27, for the material breakdown of each lumped mass. The values represent the total installed mass per material contributing to the respective thermal capacity.

Table 28, for the temperature-dependent static heat loads.

Table 29, for the temperature-dependent specific enthalpy of the Cold Mass and TS Mass.

Table 27. Lumped cold mass composition for the Cryogenic User Transient Model.

Table 28. Static heat loads for the Cryogenic User Transient Model

- The term  corresponds to the temperature-dependent thermal conductivity of “AISI 304 (UNS S30400)” stainless steel, according to NIST data.

- All temperatures are expressed in Kelvin. All heat loads are expressed in Watts.

Table 29. Specific enthalpy (weighted average) of the lumped masses 
for the 1 K to 300 K.


# Control Systems

# Instructions for GSHRC
Table 30. Instructions for GSHRC [AD_04].


# Control Architecture details
The following table expands on details as per Figure 11.

Table 31. Control Architecture details


---
## Extracted Tables

### Table TBL-001 (81×2)
| AD | Applicable Documents |
| --- | --- |
| AH | Atmospheric Heat exchanger |
| BSL | Baseline |
| CAV | Cavity |
| CCB | Cryogenic Compressor Building |
| CIS | Control and Interlock system |
*... 75 more rows*

### Table TBL-002 (2×2)
| Piping | For process lines interfacing two or mor |
| --- | --- |
| Control & Interlock System | The Control and Interlock System of a su |

### Table TBL-003 (19×2)
| CoreShare | SCK CEN’s collaboration platform to shar |
| --- | --- |
| Design Phase | A self-contained phase within the engine |
| Digital Process Model | A mathematical or logical representation |
| Digital Twin | A full-scope digital representation of a |
| Element | Collective term for any major, self-cont |
| Heat Load | Dynamic Heat Load: The heat input to a c |
*... 13 more rows*

### Table TBL-004 (13×4)
| Family | Line ID | Line Name | Main Function |
| --- | --- | --- | --- |
| Main 
cryogenics
headers | A * | SHe Supply Line | Supplies user with SHe for main cryogeni |
| Main 
cryogenics
headers | B * | VLP Return Line | Returns from user (very-)low pressure GH |
| Main 
cryogenics
headers | D * | TS Supply Line | Supplies user with high-pressure GHe for |
| Main 
cryogenics
headers | E * | TS Return Line | Returns from user high-pressure GHe from |
| Warm 
distribution lines | U | Warm Supply Line | Supplies user with warm GHe for purging  |
*... 7 more rows*

### Table TBL-005 (33×3)
| ID | Document name | Reference |
| --- | --- | --- |
|  | Auxiliary Building (ZIP file, including  | SCK CEN/98684417 |
|  | MINERVA_Views | SCK CEN/83474410 |
|  | Masterplan | SCK CEN/84582975 |
|  | AUB_Fire Escape | SCK CEN/81503842 |
|  | CCB_Fire Escape | SCK CEN/81506385 |
*... 27 more rows*

### Table TBL-006 (8×3)
| ID | Operational 
Scenario | Description |
| --- | --- | --- |
| WSTOP | Warm Stop | QPS is offline. |
| RT-SB | Room Temperature Standby | QPS and QCELLs are at ambient temperatur |
| TS-SB | Thermal Shield Standby | QCELLs are cooled non-isothermally at th |
| 10K-SB | 10 K Standby | QCELLs are cooled non-isothermally at ~1 |
| 4K-SB | 4 K Standby | QCELLs are cooled isothermally at ~4.5 K |
*... 2 more rows*

### Table TBL-007 (10×3)
| ID | Operational Scenario | Description |
| --- | --- | --- |
| CD-TS | Cool-down to TS-SB | Controlled cool-down to TS Standby condi |
| CD-4K | Cool-down to 4K-SB | Controlled cool-down to 4 K Standby cond |
| CD-10K | Cool-down to 10K-SB | Controlled cool-down to 10 K Standby con |
| CD-2K | Cool-down to 2K-SB | Controlled cool-down to 2 K Standby cond |
| 2K-RAMP | Ramping at 2K | Controlled adjustment of the 2 K heat lo |
*... 4 more rows*

### Table TBL-008 (5×4)
| Scenario | Parameter | LINAC_24 | LINAC_30 |
| --- | --- | --- | --- |
| LHe Filling | Filling rate | ~19 g/s † | ~ 24 g/s † |
| LHe Filling | Filling capacity | ~ 1700 L | ~ 2100 L |
| LHe Emptying | Emptying rate | 12-16 g/s | 15-20 g/s |
| LHe Emptying | Emptying capacity | ~ 1700 L | ~ 2100 L |

### Table TBL-009 (6×5)
| Operational Scenario | QCAV (W) | QTS (W) | mCPLR (g/s) | QB (W) |
| --- | --- | --- | --- | --- |
| 2 K Operation (2K-OP) | 380-770 | 4800-8200 | 1.2-2.3 | 49-81 |
| 2 K Standby (2K-SB) | 250-460 | 4800-8200 | 0-1.8 | 49-81 |
| 4 K Standby (4K-SB) | 250-460 | 4800-8200 | 0-1.8 | 49-81 |
| 10 K Standby (10K-SB) | 250-460 | 4800-8200 | 0-1.8 | 49-81 |
| TS Standby (TS-SB) | - | 4800-8200 | - | - |

### Table TBL-010 (11×7)
| Scenario | Line ID | A | B | D | E | W |
| --- | --- | --- | --- | --- | --- | --- |
| 2K-OP | p (bar)
[range | stability] | 3.0 | ±0.015 |  | ~14 ‡ | ±0.025 | ~13 ‡ | ±0.025 | 1.1 | ±0.010 |
| 2K-OP | T (K)
[range | stability] | 4.5 | ±0.05 | 3.0-4.0 | ±0.25 | ~40 ‡ | ±1.5 | ~60 ‡ | ±5 | 300 † |
| 2K-SB | p (bar)
[range | stability] | 3.0 | ±0.050 |  | ~14 ‡ | ±0.050 | ~13 ‡ | ±0.050 | 1.1 | ±0.015 |
| 2K-SB | T (K)
[range | stability] | 4.5 | ±0.15 | 3.0-4.5 | ±0.25 | ~40 ‡ | ±2.5 | ~60 ‡ | ±5 | 300 † |
| 4K-SB | p (bar)
[range | stability] | Same as in
2K-SB |  | Same as in 
2K-SB | Same as in 
2K-SB | Same as in 
2K-SB |
*... 5 more rows*

### Table TBL-011 (3×6)
| Condition type | Operational Scenario | QCAV (W) | QTS (W) | mCPLR (g/s) | QB (W) |
| --- | --- | --- | --- | --- | --- |
| QPLANT Design Point | 2K-OP (2 K Operation) | 770 | 8200 | 2.3 | 81 |
| QPLANT Standby Point | 2K-SB (2 K Standby) | 250 | 4800 | 0 | 49 |

### Table TBL-012 (7×8)
| Condition type | Operational Scenario | Line ID | A | B | D | E | W |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QPLANT 
Design Point | 2K-OP 
(2 K Operation) | Pressure (bar) | ≥ 3.0 | ≤ 0.026 | ~14 ‡ | ~13 ‡ | ≤ 1.1 |
| QPLANT 
Design Point | 2K-OP 
(2 K Operation) | Temperature (K) | ≤ 4.5 | ≥ 3.5 | ~40 ‡ | ~60 ‡ | 300 † |
| QPLANT 
Design Point | 2K-OP 
(2 K Operation) | Mass Flow Rate (g/s) | ≥ 42 | ≥ 39 | ~77 ‡ | ~77 ‡ | ≥ 2.3 |
| QPLANT 
Standby Point | 2K-SB 
(2 K Standby) | Pressure (bar) | ≥ 3.0 | ≤ 0.029 | ~14 ‡ | ~13 ‡ | ≤ 1.1 |
| QPLANT 
Standby Point | 2K-SB 
(2 K Standby) | Temperature (K) | ≤ 4.5 | ≥ 4.2 | ~40 ‡ | ~60 ‡ | 300 † |
*... 1 more rows*

### Table TBL-013 (4×3)
| Failure Class | Maximum allowable events | Reference period |
| --- | --- | --- |
| Class A | ≤1 | 1 year |
| Class B | ≤5 | 5 year |
| Class C | ≤2 | 10 year |

### Table TBL-014 (6×3)
| Maintenance interval | Maintenance window | Operational state during maintenance |
| --- | --- | --- |
| Not limited | Not limited | 2K-OP |
| ≥6 months | 10 days | 2K-SB |
| ≥1 year | 20 days | 4K-SB |
| ≥2.5 years | 60 days | WSTOP |
| ≥10 years | 120 days | WSTOP |

### Table TBL-015 (4×4)
| Nominal Temperature | < 30 K | 30 K to 120 K | > 120 K |
| --- | --- | --- | --- |
| Accuracy class: “standard” | ≤ ±100 mK | ≤ ±500 mK | ≤ ±1 K |
| Accuracy class: “high” | ≤ ±50 mK | ≤ ±300 mK | not applicable |
| Long term drift (of the whole scale) | ≤ ±10 mK per year | ≤ ±50 mK per year | ≤ ±100 mK per year |

### Table TBL-016 (14×2)
| Tag | Description |
| --- | --- |
| TT | Temperature transmitter measuring the te |
| PT | Pressure transmitter measuring the press |
| FT | Flow transmitter measuring the flow rate |
| LT | Level transmitter measuring the cryogeni |
| LS | Limit switch providing a discrete positi |
*... 8 more rows*

### Table TBL-017 (18×2)
| Parameter | Measurement Location(s) |
| --- | --- |
| Helium Mass Flow Rate | - WCS.VLP 
- WCS.LP
- WCS.HP |
| Helium Temperatures | - WCS.VLP 
- WCS.LP
- WCS.HP |
| Helium Mass flow rate | - WCS.VLP 
- WCS.LP
- WCS.HP |
| Helium Pressure | - Suction of each compressor (including  |
| Differential Pressure | - Across each oil filter
- Across the ch |
*... 12 more rows*

### Table TBL-018 (11×2)
| Parameter | Measurement Location(s) |
| --- | --- |
| Helium mass flow rate | - Inlet HP stream of the QRB
- Supply SH |
| Temperatures | - Inlets and outlets of the QRB
- Inlet  |
| Pressure | - Inlets and outlets of the QRB
- Inlet  |
| Differential pressure | - Across each filter or set of parallel  |
| Level measurements | - In liquid helium phase separate (2K an |
*... 5 more rows*

### Table TBL-019 (11×2)
| Type of Leak | Maximal leak rates |
| --- | --- |
| To vacuum, per helium circuits | 1×10⁻⁸ mbar·L/s |
| To the water circuits, per helium or hel | 1×10⁻⁸ mbar·L/s |
| To helium circuits, per LN2 circuit | 1×10⁻⁸ mbar·L/s |
| To sub-atmospheric circuits, per helium  | 1×10⁻⁵ mbar·L/s |
| To atmosphere, per from helium and oil c | 1×10⁻⁵ mbar·L/s |
*... 5 more rows*

### Table TBL-020 (4×3)
| Component | Helium inventory data | Helium Mass (kg) |
| --- | --- | --- |
| Cryomodules (QM) | QM ~ 12 kg each | 360 kg |
| Cryogenic Distribution Backbone (QDB) | QVBs ~ 0.4 kg each
QVE ~ 22 kg
QLM ~ 9 k | 45 kg |
| Warm Pipping System (WPS) | WPS ~ 30 kg | 30 kg |

### Table TBL-021 (10×2)
| Parameter | Value |
| --- | --- |
| Elevation | 27 m |
| Location Coordinates | 51° 13' 50" N, 5° 05' 24" E |
| Outside Winter Conditions
– Dry-bulb Tem | -9.1 °C
90 % |
| Outside Summer Conditions
– Dry-bulb Tem | 33.4 °C
39 % |
| Wind Speed 
(3 s. gust at 25 m height, N | 49 m/s 
(~176 km/h) |
*... 4 more rows*

### Table TBL-022 (10×5)
| Equipment Description | Supply Voltage (V) | Phases & 
Earthing | Rated Active Power (kW) | Load Type |
| --- | --- | --- | --- | --- |
| HP Compressor 1 | 400 | 3PH + N + PE | 356 | Motor (VFD) |
| HP Compressor 2 | 400 | 3PH + N + PE | 356 | Motor (VFD) |
| HP Compressor 3 | 400 | 3PH + N + PE | 356 | Motor (VFD) |
| HP Compressor 4 | 400 | 3PH + N + PE | 356 | Motor (VFD) |
| PVPS pumping skid | 400 | 3PH + N + PE | 150 | Feeder |
*... 4 more rows*

### Table TBL-023 (6×5)
| Equipment Description | Supply Voltage (V | Phases & Earthing | Rated Active Power (kW) | Load Type |
| --- | --- | --- | --- | --- |
| Cold Compressor 1 | 400 V | 3PH + N + PE | 42 | Motor (DOL) |
| Cold Compressor 2 | 400 V | 3PH + N + PE | 42 | Motor (DOL) |
| Cold Compressor 3 | 400 V | 3PH + N + PE | 42 | Motor (DOL) |
| Other | 400 V | 3PH + N + PE | 65 | Feeder |
| Control systems supply | 230 V | 1PH + N + PE | 3 | Varia |

### Table TBL-024 (14×3)
| Parameter | Unit | Value or Range |
| --- | --- | --- |
| Conductivity | µS/cm | 150 – 500 |
| TSS | mg/L | < 25 |
| pH | – | 7 – 8.5 |
| TDS | mg/L | < 1000 |
| Total hardness | mg/L | < 60 |
*... 8 more rows*

### Table TBL-025 (19×4)
| ID | Description | Responsible | Dates (Earliest/Latest) |
| --- | --- | --- | --- |
| T0 | Contract Conclusion | SCK CEN | Oct 2026 |
| Conceptual Design (L1) | Conceptual Design (L1) | Conceptual Design (L1) | Conceptual Design (L1) |
|  | Kick-Off Meeting | SCK CEN | T0 + 15 Business Days |
|  | Conceptual Design File Approval | Contractor | To be defined by Contractor |
| Detailed Design (L2) | Detailed Design (L2) | Detailed Design (L2) | Detailed Design (L2) |
*... 13 more rows*

### Table TBL-026 (7×2)
| Standard | Role in Training & Handover |
| --- | --- |
| IEC 60300-3-3
(Reliability-Centered Main | Defines RCM logic that operators and tec |
| ISO 20815 | Production assurance and availability ma |
| IEC 60300-3-11 | Reliability-Centred Maintenance (RCM) |
| IEC 60300-3-12
(Life-cycle costing) | CAPEX/OPEX modelling |
| ISO 55000 / 55001 / 55002
(Asset Managem | Training shall support asset lifecycle t |
*... 1 more rows*

### Table TBL-027 (7×3)
| Ref | Standard | Scope |
| --- | --- | --- |
| PED | 2014/68/EU | EU Pressure Equipment Directive |
| ASME VIII‐1 | Unfired pressure vessels | Design / certification |
| EN 13445 | Unfired pressure vessels | EU compliance |
| API 520/521 | Pressure relief sizing & selection | PSVs / BD |
| EN ISO 4126 | Safety valves & RD devices | Proof-test ≤ 5 y |
*... 1 more rows*

### Table TBL-028 (5×3)
| Ref | Standard | Scope |
| --- | --- | --- |
| IEC 61508 | Functional safety (E/E/PE systems) | SIL assignment |
| IEC 61511 | SIS for process industry | SIS lifecycle |
| IEC 60204-1 / 61439 | Electrical equipment & switchgear | Control cabinet |
| IEC 60300-3-3 | RCM assessment | Links to DMAIC Control |

### Table TBL-029 (3×3)
| Ref | Standard | Scope |
| --- | --- | --- |
| ISO 8573-1 Class 0 | Oil-free compressor classification | Compressors |
| ASTM D5464 | Helium purity test | Getter skid validation |

### Table TBL-030 (3×3)
| LINAC Configuration | Cold Mass | TS Mass |
| --- | --- | --- |
| LINAC_24 | 9 885 kg | 8 602 |
| LINAC_30 | 12 356 kg | 10 753 kg |

### Table TBL-031 (5×5)
| Heat load direction | Heat load type | Heat load equation (W) | LINAC_24 | LINAC_30 |
| --- | --- | --- | --- | --- |
| From the TS Mass 
to the Cold Mass | Conduction |  | = -2.93 | = -3.60 |
| From the TS Mass 
to the Cold Mass | Radiation |  | = 1.82 E-05 | = 2.24 E-05 |
| From ambient 
to the TS Mass | Conduction |  | = -1.13 | = -1.38 |
| From ambient 
to the TS Mass | Radiation |  | = 5.40 E-07 | = 6.58 E-07 |

### Table TBL-032 (31×3)
| Temperature (K) | Cold Mass Enthalpy (J/kg) | TS Mass Enthalpy (J/kg) |
| --- | --- | --- |
| 1 | 0.0 | 0.0 |
| 2 | 0.6 | 0.1 |
| 3 | 1.2 | 0.2 |
| 4 | 2.2 | 0.4 |
| 6 | 4.9 | 0.9 |
*... 25 more rows*

### Table TBL-033 (42×2)
| Req. | Specific instruction |
| --- | --- |
| GSHRC-1 | Applicable. Software hardware and firmwa |
| GSHRC-2 | Applicable. Final Software Architecture  |
| GSHRC-3 | Applicable. Final System Interlock Diagr |
| GSHRC-4 | Applicable. Final Interface Design Descr |
| GSHRC-5 | Applicable. Datasheets shall be delivere |
*... 36 more rows*

### Table TBL-034 (47×3)
| WNo. | Name | Description |
| --- | --- | --- |
| 11–19: Local Engineering and Control Sta | 11–19: Local Engineering and Control Sta | 11–19: Local Engineering and Control Sta |
| 11 | Engineering Station | A dedicated workstation for running the  |
| 111 | Engineering Tool | A dedicated engineering software for con |
| 12 | Local Operator Station (HMI) | A touchscreen placed near the cryogenic  |
| 121 | QPS HMI | Local HMI |
*... 41 more rows*
