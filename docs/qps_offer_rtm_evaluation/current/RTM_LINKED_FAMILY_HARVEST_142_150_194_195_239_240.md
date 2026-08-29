# QPS Wave 2C — next set, backlog and linked-family harvest

Status: **GOVERNED INDIVIDUAL DISPOSITION + LINKED BACKLOG — NO REQUIREMENT CLOSURE**

## Why this set

Wave 2B converted the most material returned evidence and advanced the exact-v24 frontier to RTM-197 / R75. This pass takes the next lowest-cost explicit returned-evidence backlog and keeps every item attached to its canonical OFFER family, so manual review propagates across the linked neighbourhood rather than stopping at six rows.

## New individual dispositions

| RTM | OFFER family | Returned position | Owner state | Owner disposition |
|---|---|---|---|---|
| RTM-142 | OFFER-15 | ALAT proposes deleting **at minimum** from the WCS compression-equipment floor; LKT exception register is silent. | **D_CL** | Preserve the minimum equipment/function floor. Require positive configuration evidence against every listed subsystem; LKT silence is not compliance. |
| RTM-150 | OFFER-16 | ALAT says compressor oil-retention provision will follow vendor standard; LKT carries family-level compressor scope/turndown clarification/deviation. | **D_CL_EQ_CANDIDATE** | Vendor standard is acceptable only if the complete contractual oil-containment function/capacity is demonstrated. Keep unrelated LKT turndown deviation attached to its own requirement; do not let family-level evidence overwrite RTM-150. |
| RTM-194 | OFFER-17 | ALAT proposes deleting **at minimum** from the QRB subsystem list; LKT exception register is silent. | **D_CL** | Preserve the minimum QRB subsystem floor and require subsystem-by-subsystem positive evidence. |
| RTM-195 | OFFER-17 | ALAT proposes deleting **at minimum** from the cold-box internal-component list; LKT exception register is silent. | **D_CL** | Preserve the minimum internal-component floor; alternative architecture requires explicit functional equivalence per affected component/function. |
| RTM-239 | OFFER-19 | ALAT proposes deleting **at minimum** from the required WSH functions; LKT exception register is silent. | **D_CL** | Preserve the minimum WSH functional floor and demonstrate each function in design/evidence. |
| RTM-240 | OFFER-19 | ALAT proposes deleting **at minimum** from required WSH contents and defers interface number/location to detailed design; LKT exception register is silent. | **D_CL** | Preserve the minimum content/interface floor. Detailed-design refinement may set final locations but may not silently remove required interfaces/functions. |

## Linked family matrix

| OFFER | Canonical linked RTMs in this neighbourhood | Individually governed after this pass | Linked backlog still pending individual disposition |
|---|---|---|---|
| OFFER-15 — compressor noise emission | RTM-141..147 | 142, 146, 147 | 141, 143, 144, 145 |
| OFFER-16 — compressor configuration & operating limits | RTM-148..152 | 148, 149, 150, 152 | 151 |
| OFFER-17 — preliminary 3D / QRB layout family | RTM-193..197 | 194, 195, 197 | 193, 196 |
| OFFER-19 — WSH design & layout | RTM-239..248 | 239, 240, 247 | 241, 242, 243, 244, 245, 246, 248 |
| OFFER-20 — helium leak detection & loss management | RTM-252..257 | 252, 253, 254, 255 | 256, 257 |

The five linked families contain **33 RTMs**. Seventeen are now individually governed in the graph-harvest programme. The remaining **16 family-linked RTMs** are not closed or assumed compliant: they are the next positive-evidence / no-exception backlog to be converted into explicit Owner acceptance matrices.

## Backlog order

### B1 — linked positive-evidence conversion

Review the 16 family-linked pending RTMs as five family matrices, not sixteen isolated passes:

- OFFER-15: RTM-141, 143, 144, 145
- OFFER-16: RTM-151
- OFFER-17: RTM-193, 196
- OFFER-19: RTM-241..246, 248
- OFFER-20: RTM-256, 257

For each, record: Owner baseline -> ALAT positive evidence -> LKT positive evidence or explicit `NO_EXCEPTION_ON_FILE` -> evidence gap -> verification route -> Owner disposition.

### B2 — evidence-recovery nodes

Only after B1, spend retrieval effort on the **11 graph nodes without narrow-family evidence** already identified by the RTM-197 depth-2 graph. This keeps retrieval cost behind evidence already available.

### B3 — next exact-v24 ranked seed

After linked-family conversion, enter the next exact-v24 unresolved ranked seed and repeat:

`ranked seed -> OFFER neighbours -> RTM family -> derived dependencies -> both Contractor evidence lanes -> individual Owner disposition`.

The scalar rank chooses the entry point; it does not limit review to the next five rows.

## Coverage effect

- graph depth-2 reach: **49 RTMs**
- evidence-bearing graph nodes: **38**
- individually governed graph-harvest nodes: **11 -> 17**
- governed share of evidence-bearing graph: **28.9% -> 44.7%**
- evidence-present / review-pending graph nodes: **27 -> 21**
- linked family union explicitly controlled here: **33 RTMs**
- family-linked pending individual dispositions: **16**
- evidence-recovery backlog remains: **11**
- exact-v24 frontier remains **R75** until the next ranked seed is individually governed.

## Control

Contract/Addendum II and the canonical 722/50 projection remain authoritative. OFFER is an evidence interface. `NO_EXCEPTION_ON_FILE` is never rendered as compliance. Removing words such as **at minimum** is treated as a requirement-floor change unless governed equivalence is accepted. Graph coverage is not closure. No requirement is closed by this pass. Accepted-release HOLD remains unchanged and independent.
