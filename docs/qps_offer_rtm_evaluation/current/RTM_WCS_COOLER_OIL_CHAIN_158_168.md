# QPS Wave 2D continuation — WCS cooler and oil chain RTM-158..168

Status: **INDIVIDUAL OWNER DISPOSITION — DERIVED ENGINEERING FAMILY EXPANSION — NO REQUIREMENT CLOSURE**

## Why this family is reviewed together

RTM-158..168 form a physically connected WCS reliability chain: cooling-water control affects compressor thermal state; oil management affects lubrication and oil carry-over; auxiliary-oil applicability affects start/stop/coast-down protection; separator instrumentation and sampling affect the ability to prove the contractual oil limit; filter architecture protects bearings/seals and downstream oil-removal equipment.

This is a derived engineering dependency family. No new canonical OFFER edge is asserted by this file.

| RTM | Canonical Owner baseline | Returned position | Owner disposition |
|---|---|---|---|
| RTM-158 | Each cooler water circuit includes purge/drain capability, cooling-water flow regulation and manual inlet isolation. | ALAT leaves purge/drain, control-valve and manual shut-off valve number/location to Kaeser vendor standard. LKT exception-only lane is silent. | **D_CL / DESIGN_EQ_REQUIRED.** Vendor standard may determine implementation only if every required purge, drain, regulation and isolation function remains demonstrable. Require cooler-by-cooler P&ID/tag/Cv/fail-state and drainability evidence. |
| RTM-159 | WCS oil-management system provides at minimum the listed bulk separation, storage/thermal conditioning/controlled supply and oil-retention functions. | ALAT proposes deleting `at minimum` while marking listed functions compliant. | **D_CL / PE.** Preserve the minimum functional floor. Bind each listed function to equipment, instrumentation and operating/control evidence. |
| RTM-160 | Contractor supplies initial compressor oil; oil is qualified for helium-compressor service or approved equivalent and meets specified quality limits. | ALAT proposes proprietary oil used on its 2 K applications; particle-size requirement is treated as a suggestion while other properties are marked compliant. | **EQ_CANDIDATE / D_CL.** Prior service history supports but does not prove equivalence. Require oil specification, compressor-OEM approval, particle/water/acid properties, compatibility and acceptance certificate against every Owner criterion. |
| RTM-162 | Each compressor has an automatically controlled auxiliary oil-pump unit maintaining minimum bearing-lubrication pressure during start-up, shutdown and coast-down. | ALAT marks N/A because Kaeser compressors use no oil pump. | **FUNCTIONAL_EQ_REQUIRED.** `N/A` is acceptable only if compressor architecture demonstrably provides equal-or-better lubrication protection through all start/stop/coast-down states without the specified auxiliary pump. Require lubrication schematic, pressure envelope, trip logic and OEM evidence. |
| RTM-163 | Each auxiliary oil-pump unit includes the specified pressure transmitters and protection-system flow switch. | ALAT marks all N/A because no oil pump is used. | **CONDITIONAL_NA.** Disposition follows RTM-162. If Owner accepts a pump-less equivalent architecture, these component requirements may become genuinely non-applicable; otherwise baseline remains. Record the dependency explicitly rather than closing RTM-163 independently. |
| RTM-164 | Each bulk oil separator has differential-pressure indication across separation elements for fouling/performance monitoring. | ALAT explicitly deviates: standard Kaeser equipment has no DP indicator. | **D_MATERIAL.** Loss of DP monitoring removes direct separator-health evidence. Require either contractual DP indication or an Owner-approved equivalent fouling/performance-monitoring method with alarm/maintenance thresholds and verification. |
| RTM-165 | Where separator also provides oil retention/reservoir function, electric heating preheats retained oil before compressor start. | ALAT explicitly deviates: no electrical preheater. | **D_MATERIAL / FUNCTIONAL_EQ_CANDIDATE.** Demonstrate oil viscosity/temperature and lubrication readiness at worst-case start conditions. Absence of heater is acceptable only if no preheat function is needed and the full startup envelope is substantiated. |
| RTM-166 | Suitable sampling points and agreed procedures at each bulk-oil-separator helium outlet allow oil carry-over verification during performance tests and long-term operation. | ALAT explicitly deviates: no sampling point for oil carry-over measurement. | **D_MATERIAL / VERIFICATION_GAP.** This directly removes the means to verify RTM-151/167. Require physical sampling or an Owner-approved measurement method providing equivalent location-specific verification during acceptance and operation. |
| RTM-167 | Helium at each bulk-oil-separator outlet is <=100 ppm(w) oil under all normal operation; this is maximum ORS inlet concentration. | ALAT marks compliant; LKT exception-only lane silent. | **PE / ACCEPTANCE_LINK.** Require guaranteed value plus test method, operating envelope and measurement evidence. Closure cannot occur while RTM-166 leaves the verification method unresolved. |
| RTM-168 | Compressor oil-filter system includes at minimum the specified duplex pump-inlet filter and fine injection filter architecture. | ALAT proposes deleting `at minimum`; marks pump-inlet filter N/A because no oil pump exists; leaves fine-filter number/location to vendor standard. | **D_CL / CONDITIONAL_EQ.** Preserve filtration performance and maintainability objectives. Pump-inlet element depends on RTM-162 architecture; fine filtration requires micron rating, location, bypass/changeover/maintenance evidence and protection of bearings/seals. |

## Cross-requirement acceptance dependencies

1. **RTM-162 → RTM-163 → compressor start/stop/trip acceptance.** Pump-less architecture requires functional-equivalence evidence for lubrication protection through transient states.
2. **RTM-164 + RTM-166 → RTM-151/167.** Claimed <=100 ppm(w) oil concentration is not independently verifiable if separator condition and outlet sampling/measurement are removed.
3. **RTM-157/158 → cooling-water performance → compressor thermal stability.** Vendor-standard valve layout must still prove drainability, controllability, isolation and stable temperatures.
4. **RTM-159/160/165/168 → oil quality/readiness → long-term compressor reliability.** Proprietary/vendor-standard solutions require quantitative equivalence evidence.

## FAT / SAT / commissioning propagation

- FAT/commissioning: verify oil specification/certificates, filtration architecture, lubrication protection logic, separator-health monitoring and cooler valve functionality where practicable.
- WCS SAT: demonstrate cooling-water regulation, stable oil pressure/temperature, compressor start/stop/coast-down behaviour, protection logic and oil carry-over acceptance method.
- long-term/maintenance evidence: define separator fouling indication or equivalent, oil sampling/analysis, filter service criteria and traceable oil-carry-over verification.

This propagation is **derived engineering evidence routing**, not a change to contractual authority or OFFER crosswalk.

## Result

RTM-158..168 reviewed in this continuation, excluding RTM-161 because it was already individually governed at exact-v24 rank R50.

Newly dispositioned here: **10 RTMs** — 158, 159, 160, 162, 163, 164, 165, 166, 167, 168.

High-value issues now exposed: RTM-164 separator DP monitoring omitted; RTM-165 oil preheating omitted; RTM-166 oil carry-over sampling/verification omitted; RTM-162/163 require governed functional-equivalence determination; RTM-167 claimed compliance is acceptance-dependent on resolving RTM-166.

## Next engineering set

Continue with RTM-169 onward through oil-filter isolation, oil purge/fill, downstream oil-removal/dryer equipment and associated instrumentation until the WCS oil/cleanliness chain reaches a natural system boundary. Then reconcile that chain against RTM-161 O&M requirements and the WCS FAT/SAT items already governed.

No requirement is closed here. `Compliant` remains returned evidence, `N/A` requires Owner applicability/equivalence disposition, and LKT exception silence remains non-compliance-neutral. Accepted-release HOLD unchanged and independent.
