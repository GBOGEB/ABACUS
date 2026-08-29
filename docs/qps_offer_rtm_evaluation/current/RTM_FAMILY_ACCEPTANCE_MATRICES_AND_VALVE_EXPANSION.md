# QPS Wave 2D — linked family acceptance matrices + WCS valve/control expansion

Status: **FAMILY-LEVEL OWNER ACCEPTANCE CONTROL + INDIVIDUAL HIGH-VALUE DISPOSITIONS — NO REQUIREMENT CLOSURE**

## Scope

Wave 2C left 16 RTMs pending inside five canonical OFFER families. This wave converts all 16 from generic linked backlog into explicit Owner acceptance-matrix states, then expands to the adjacent WCS valve/control/cooler chain RTM-153..157 because returned evidence already shows material configuration changes.

The distinction is important:

- the five OFFER families below are **canonical OFFER↔RTM relationships**;
- RTM-153..157 are an **adjacent engineering continuation** from the WCS compressor family and are not assigned a new canonical OFFER edge here unless the governed crosswalk explicitly provides one;
- family-level Contractor comments are never copied blindly into a row-specific disposition.

## Family matrix A — OFFER-15 / compressor noise & rotating-equipment envelope

| RTM | Owner baseline | Returned evidence state | Owner disposition |
|---|---|---|---|
| RTM-141 | WCS provides VLP, LP and HP compression levels. | ALAT explicitly compliant; LKT exception-only lane silent. | **PE / POSITIVE EVIDENCE BINDING.** Bind compressor/PVPS architecture and pressure-level evidence; LKT silence is not compliance. |
| RTM-143 | Each compression stage has at least three compressors; same-stage machines identical. | ALAT compliant; LKT silent. | **PE.** Bind compressor count, stage allocation and identical-unit BOM/model evidence. |
| RTM-144 | Each compressor motor has a full-load-rated VFD. | ALAT compliant but clarifies no VFD on PVPS. | **CL / SCOPE BINDING.** Confirm whether canonical wording applies to HP compressors only or also PVPS; do not infer scope from ALAT clarification. Bind VFD ratings to each applicable motor. |
| RTM-145 | Motor/VFD efficiency complies with EU 2019/1781. | ALAT compliant; LKT silent. | **PE.** Require manufacturer efficiency class/declaration for each applicable motor/VFD. |

Together with already-governed RTM-142/146/147, OFFER-15 is now **7/7 individually dispositioned**.

## Family matrix B — OFFER-16 / compressor configuration & limits

| RTM | Owner baseline | Returned evidence state | Owner disposition |
|---|---|---|---|
| RTM-151 | Helium oil concentration downstream of bulk oil separator <=100 ppm(w). | ALAT explicitly compliant. LKT row carries the family compressor-scope/turndown block, not a specific oil-concentration rejection. | **PE / REQUIREMENT-SPECIFIC EVIDENCE.** Require guaranteed oil concentration, measurement location/method, operating envelope and FAT/SAT evidence. Do **not** misclassify the inherited LKT family comment as a row-specific deviation. |

Together with RTM-148/149/150/152, OFFER-16 is now **5/5 individually dispositioned**.

## Family matrix C — OFFER-17 / QRB general layout/interface

| RTM | Owner baseline | Returned evidence state | Owner disposition |
|---|---|---|---|
| RTM-193 | QPS includes QRB producing required cooling power and distributing cryogenic flows to QDB. | ALAT compliant; LKT silent. | **PE.** Bind QRB functional architecture, process-flow mapping and design-point capacity evidence. |
| RTM-196 | Contractor defines cold-box arrangement and orientation. | ALAT compliant/information; LKT silent. | **PE / DESIGN DELIVERABLE.** Require controlled layout/orientation deliverable tied to interfaces, maintainability and installation envelopes. |

Together with RTM-194/195/197, OFFER-17 is now **5/5 individually dispositioned**.

## Family matrix D — OFFER-19 / WSH design & layout

| RTM | Owner baseline | Returned evidence state | Owner disposition |
|---|---|---|---|
| RTM-241 | WSH stores total helium inventory of QPS and users to contractual design values. | ALAT compliant; LKT silent. | **PE.** Require inventory calculation, usable volume, pressure/temperature basis and margin. |
| RTM-242 | WSH has at least three helium storage vessels. | ALAT compliant; LKT silent. | **PE.** Bind vessel count, individual volume and arrangement. |
| RTM-243 | Each storage vessel meets listed vessel requirements. | ALAT compliant; LKT silent. | **PE.** Use vessel-by-vessel compliance/evidence matrix. |
| RTM-244 | Each vessel includes required instrumentation/equipment. | ALAT compliant; LKT silent. | **PE.** Bind instrument/equipment tags and datasheets per vessel. |
| RTM-245 | WSH includes the required common equipment/functions. | ALAT compliant; LKT silent. | **PE.** Bind common-system equipment to P&ID/BOM and control functions. |
| RTM-246 | WSH allows controlled connection to WCS lines with required capabilities. | ALAT compliant; LKT silent. | **PE.** Require interface/control matrix for connection, isolation, transfer and recovery modes. |
| RTM-248 | Contractor proposes final WSH layout, volume and positioning during Conceptual Design. | ALAT compliant; LKT silent. | **PE / DESIGN DELIVERABLE.** Bind final layout to building interfaces, access, maintainability and vessel-capacity evidence. |

Together with RTM-239/240/247, OFFER-19 is now **10/10 individually dispositioned**.

## Family matrix E — OFFER-20 / helium inventory and leak management

| RTM | Owner baseline | Returned evidence state | Owner disposition |
|---|---|---|---|
| RTM-256 | QPLANT dimensioning is based on required Cryogenic User helium inventory. | ALAT compliant. LKT comparison repeats OFFER-20 family deviations but does not establish a row-specific rejection of the inventory-dimensioning obligation. | **PE / SEPARATE FAMILY FROM ROW EVIDENCE.** Require inventory basis, design margin and traceable user-inventory inputs. Do not inherit unrelated leak-rate deviation automatically. |
| RTM-257 | Table 17 requirement. | ALAT has **no matched row**; LKT comparison repeats the OFFER-20 family deviation block. | **NE / ROW-SPECIFIC EVIDENCE RECOVERY REQUIRED.** Recover canonical Table 17 content and bidder-specific response before disposition. Family-level LKT text is insufficient to determine row compliance. |

Together with RTM-252..255, OFFER-20 is now **6/6 individually triaged**, but RTM-257 remains evidence-incomplete rather than compliant.

## Linked-family result

All **33 RTMs** in OFFER-15/16/17/19/20 now have an individual Owner-controlled state:

- 33 / 33 individually dispositioned or triaged;
- 0 remain generic `linked pending individual disposition`;
- positive/compliant bidder statements remain **PE**, not closure;
- RTM-257 is explicitly **NE** because row-specific evidence is missing;
- inherited family comments are separated from row-specific evidence.

This completes the B1 linked-family conversion without spending retrieval effort on the separate 11 evidence-poor graph nodes.

# Adjacent high-value expansion — RTM-153..157

These requirements are adjacent to the WCS compressor family and already contain returned evidence with direct design consequences. They are therefore advanced before lower-value generic recovery work.

| RTM | Owner baseline | ALAT returned position | Owner state / disposition |
|---|---|---|---|
| RTM-153 | WCS includes bypass valves HP→LP and LP→VLP; bypass sizing satisfies the contractual full-flow/worst-dP requirement. | ALAT states no LP→VLP bypass will be installed; only PVPS recirculation is foreseen. It also proposes one bypass for full flow and another for pressure control. | **D_MATERIAL.** Preserve both required pressure-header bypass functions and sizing. Require stage/header flow-control architecture and transient/recovery justification for any replacement topology. |
| RTM-154 | Control valves are installed in each listed storage/header connection. | ALAT marks the listed connections compliant. | **PE.** Bind each required connection to P&ID valve tag, Cv/rangeability, fail position and control function. |
| RTM-155 | Each WCS↔QRB helium connection includes a control valve in the WCS building. | ALAT explicitly says no additional control valves will be installed and offers ON/OFF valves at QRB inlet/outlet instead. | **D_MATERIAL / FUNCTIONAL_EQ_CANDIDATE.** ON/OFF isolation is not automatically equivalent to a control valve. Require control-function/rangeability/transient analysis; retain Owner baseline unless equal-or-better function is demonstrated and approved. |
| RTM-156 | Each compressor-stage suction/discharge has automatic non-return valves closing when the compressor stops. | ALAT does not consider NRVs relevant on compressors and proposes automatic non-return only for PVPS. | **D_MATERIAL.** Require reverse-flow/backspin/surge/transient protection analysis per stage and demonstrate equivalent automatic isolation if physical NRVs are omitted. |
| RTM-157 | Each cooler gas circuit includes the required gas-side items, including purge valves for draining/purging/rinse-out. | ALAT accepts the cooler requirement but leaves purge-valve number/location to vendor standard. | **D_CL / DESIGN EVIDENCE.** Vendor standard may set implementation only if all required purge/drain/rinse functions are preserved. Bind valve count/location to purge-volume, dead-leg and maintainability analysis. |

## Immediate next linked expansion

The evidence visible beside this chain already flags RTM-158 and later WCS equipment rows. After this PR, continue by engineering family rather than scalar rank:

1. RTM-158 onward — cooler water circuit and adjacent WCS equipment requirements;
2. RTM-153..157 dependencies back into WCS control philosophy, compressor trip/recovery and SAT/FAT acceptance;
3. then the 11 evidence-poor nodes from the RTM-197 graph;
4. then enter the next exact-v24 ranked seed and repeat bidirectional expansion.

## Control

Contract/Addendum II and canonical RTM remain authoritative. Canonical OFFER edges are not invented. Derived adjacency/dependency is labelled as such. Bidder `Compliant` is evidence to verify, not Owner closure. Family-level comments cannot automatically become row-specific deviations. No requirement is closed by this file. Accepted-release HOLD remains unchanged and independent.
