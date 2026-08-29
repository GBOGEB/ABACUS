# QPS Wave 2F — WCS cleanliness, ORS/GMP, dryer and instrumentation chain RTM-169..192

Status: **OWNER-CONTROLLED ENGINEERING-FAMILY DISPOSITION — NO REQUIREMENT CLOSURE**

## Scope and selection

This wave continues directly from merged Wave 2E (RTM-158..168). It reviews RTM-169..192 as one physical verification chain:

**oil filter isolation → oil purge/fill → ORS/GMP → coalescers → charcoal adsorber → helium dryer → final filters → WCS process instrumentation → FAT/commissioning/SAT evidence.**

The chain contains exact-v24 RTM-186 (previously identified at R77), but scalar rank is not used as the scope boundary. The contiguous rank frontier remains R75 until unresolved R76 is governed.

## Individual Owner dispositions

| RTM | Owner baseline | Returned Contractor evidence | Owner state / disposition |
|---|---|---|---|
| RTM-169 | Each oil filter has the required maintenance/isolation and blockage-monitoring provisions. | ALAT leaves manual isolation-valve number/location to vendor standard but accepts differential-pressure indication. LKT exception-only lane silent. | **D_CL / PE.** Preserve maintainable isolation of each filter; bind valve arrangement and DP indication to P&ID and maintenance method. |
| RTM-170 | Relevant compressor oil piping can be fully isolated for maintenance. | ALAT compliant; LKT silent. | **PE.** Bind all isolation points to P&ID and maintenance isolation boundary. |
| RTM-171 | Oil piping/purge arrangement has >1% slope to designated oil traps to prevent migration into oil-free regions. | ALAT defers arrangement to vendor standard. | **D_CL / DESIGN_EQ.** Vendor standard is acceptable only if slope/drainage/oil-migration objective is demonstrated on controlled layout/isometrics. |
| RTM-172 | WCS includes ORS/GMP and residual oil at QRB interface is <=10 ppb(w) under all operating conditions including start-up/recovery. | ALAT states compliant. LKT raises measurement/monitoring limitations in the ORS family. | **PE_DEPENDENT.** Preserve <=10 ppb(w); require a measurable, traceable acceptance method and operating-condition coverage. Family limitations cannot be ignored. |
| RTM-173 | ORS/GMP contains at minimum the specified coalescer, charcoal and diagnostics architecture. | ALAT deletes `at minimum`; LKT reports oil-concentration measurement and remote-monitoring limitations. | **D_CL_MATERIAL.** Preserve minimum architecture/function floor. Require component/function/evidence matrix; inherited LKT family issues must be mapped requirement-by-requirement. |
| RTM-174 | Diagnostics and validated procedures verify oil concentration at all specified locations. | ALAT states no particular test/procedure will be provided and has no sampling point downstream of bulk separator. LKT likewise states concentration cannot be measured at one required location and reports limited remote monitoring. | **D_MATERIAL_VERIFICATION_GAP.** Owner baseline requires all measurement locations and validated procedures. Require sampling/analyser architecture, calibration, method uncertainty and test procedure for each location. |
| RTM-175 | Coalescer architecture satisfies location and minimum-stage requirements. | ALAT compliant; LKT silent. | **PE.** Bind stage count/order, vessel/filter IDs and P&ID evidence. |
| RTM-176 | Coalescer performance includes required gas-velocity margin and downstream oil <=0.5 ppm(w). | ALAT will not guarantee 0.5 ppm(w), only expects it. | **D_MATERIAL.** Preserve quantitative 0.5 ppm(w) acceptance criterion; require guarantee/test method or formal Owner-approved deviation/equivalence. |
| RTM-177 | Coalescer assembly withstands compressor vibration without fatigue/seal/fastener failure. | ALAT compliant; LKT silent. | **PE.** Bind vibration qualification/design evidence to the already-governed compressor vibration chain. |
| RTM-178 | Every coalescing stage has local and remote level measurement. | ALAT proposes remote level switches on each stage but local sightglass only on third stage, explicitly for cost reasons. | **D_MATERIAL.** Preserve both local and remote monitoring for each stage unless a formal functional-equivalence case is approved. |
| RTM-179 | Last coalescing stage is a guard stage, not automatically drained, with oil detection integrated into station shutdown; oil detection triggers shutdown. | ALAT compliant. LKT separately questions/clarifies shutdown implementation in the family. | **PE_CL.** Bind guard-stage detector, alarm/trip setpoints, shutdown logic and cause/effect; reconcile LKT clarification without weakening Owner shutdown requirement. |
| RTM-180 | Upstream-stage oil is automatically returned to compressor suction via motorized drain valves controlled by level instrumentation. | ALAT compliant; LKT silent. | **PE.** Bind drain-valve tags, permissives/interlocks and failure states. |
| RTM-181 | Charcoal adsorber architecture includes required placement, vessel(s), downstream fine dust filter and flow direction. | ALAT compliant; LKT silent. | **PE.** Bind P&ID/BOM and adsorber/dust-filter design. |
| RTM-182 | Charcoal adsorber meets required performance conditions. | ALAT compliant; LKT silent. | **PE.** Bind sizing, capacity, pressure drop and oil-removal performance evidence. |
| RTM-183 | Adsorber is filled only with cleaned/dried smooth charcoal pellets to specified quality. | ALAT compliant; LKT silent. | **PE.** Require adsorbent specification, QA certificate and loading procedure. |
| RTM-184 | Adsorbent movement and dust carry-over are prevented and demonstrated. | ALAT compliant; LKT silent. | **PE.** Require retention/dust-control design plus inspection/test evidence. |
| RTM-185 | Required charcoal drying/heating equipment is supplied. | ALAT proposes use of the helium-dryer heating unit for charcoal drying. | **CL_EQ_CANDIDATE.** Shared heater may be acceptable only if capacity, availability, operating sequence and simultaneous-maintenance constraints preserve both functions. |
| RTM-186 | Helium dryer meets contractual architecture, including redundancy/availability provisions. | ALAT proposes only one full-flow dryer and a non-redundant bypass for cost reasons. | **D_MATERIAL — exact-v24 R77 hit.** Preserve contractual architecture/redundancy unless a quantified RAM/availability equivalence is formally approved. Cost alone is not equivalence. |
| RTM-187 | Helium dryer meets specified performance requirements. | ALAT compliant; LKT silent. | **PE.** Bind outlet dew-point/water performance, capacity, pressure drop and test method. |
| RTM-188 | Dryer regeneration meets required regeneration conditions/timing. | ALAT will not guarantee 12 h; only expects it. | **D_MATERIAL.** Preserve the contractual regeneration-time criterion; require guaranteed cycle evidence or governed deviation/equivalence. |
| RTM-189 | Each helium dryer includes required equipment/instrumentation. | ALAT compliant; LKT silent. | **PE.** Bind per-dryer equipment list, instrumentation and control logic. |
| RTM-190 | WCS includes at minimum the specified filters. | ALAT deletes `at minimum`; LKT states a typical 50 micrometre compressor-suction filter. | **D_CL / REQUIREMENT-SPECIFIC REVIEW.** Preserve minimum filter floor and required ratings; supplier-typical filter size is evidence, not baseline replacement. |
| RTM-191 | Each filter has manual isolation valves on both sides to minimise air contact during maintenance/replacement. | ALAT says valves will not necessarily be directly at each filter for cost reasons. LKT carries the family filter-size deviation. | **D_MATERIAL.** Preserve isolation/air-ingress-control function at each maintenance boundary; require P&ID evidence or formal functional equivalence. |
| RTM-192 | WCS includes at minimum the process instrumentation defined in Table 14. | ALAT removes `at minimum` and refers to proposal instrumentation. LKT states no flow measurement in LP/VLP WCS lines and carries further instrumentation deviations/clarifications. | **D_MATERIAL / INSTRUMENTATION GAP.** Preserve Table-14 measurement functions and minimum floor. Require tag-by-tag instrumentation crosswalk, range/accuracy, location, control use and data-logging path. |

## Dependency propagation

This chain creates several important derived engineering dependencies which are controlled separately from canonical OFFER edges:

1. **RTM-166 + RTM-174 → RTM-151/167/172/176:** oil concentration limits are not acceptance-ready unless sampling/analyser locations and validated procedures exist.
2. **RTM-178/179/180 → compressor protection / cause-and-effect:** level monitoring, guard-stage detection and drain control must appear in CIS logic, alarm/trip matrices and SAT abnormal-event evidence.
3. **RTM-185/186/188 → availability/RAM:** shared heater, single dryer and regeneration duration directly affect availability, maintenance bypass and recovery capability.
4. **RTM-190/191/192 → cleanliness + operability:** filter architecture, isolation and process instrumentation jointly control contamination risk, maintainability and measurable process performance.
5. **RTM-169..192 → RTM-161 O&M:** every maintenance, oil-quality, sampling, regeneration and filter-replacement method must be represented in controlled O&M documentation.
6. **RTM-169..192 → FAT / Commissioning / WCS SAT:** positive bidder compliance becomes testable only when each quantitative criterion has a measurement method, instrument, acceptance tolerance and retained evidence path.

## Backlog effect

This wave converts **24 adjacent WCS cleanliness RTMs** into explicit Owner states in one engineering-family pass. It also captures the earlier high-priority RTM-186 without waiting for a scalar-only review sequence.

The next action is **not** another generic infrastructure layer. After merge:

- reconcile these 24 rows into the live HTML state;
- issue a consolidated WCS cleanliness / oil / dryer evidence matrix for both Contractors;
- then return to the unresolved exact-v24 R76 seed and graph-expand it;
- in parallel recover the 11 evidence-poor nodes from the RTM-197 neighbourhood where cheap evidence retrieval is possible.

## Control

Contract/Addendum II and canonical RTM remain authoritative. OFFER evidence is downstream. `Compliant` is returned evidence, not closure. `N/A`, vendor-standard substitutions, shared equipment and reduced redundancy require explicit Owner applicability/equivalence decisions. No requirement is closed by this file. Accepted-release HOLD remains unchanged and independent.
