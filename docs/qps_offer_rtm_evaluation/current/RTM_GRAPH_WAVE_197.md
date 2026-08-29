# QPS RTM graph-expanded evidence wave — RTM-197 seed

## Control basis

- Exact-v24 ranked seed: **RTM-197**, next unresolved frontier after governed R74 wave.
- BT/PCA chooses the entry point only; it does not define applicability or closure.
- Expansion is depth-controlled: seed RTM -> first-hop canonical OFFERs -> all RTMs linked to those OFFERs -> second-hop canonical OFFERs -> newly reached RTMs.
- Canonical direct/supporting edges remain distinct from derived engineering dependencies.
- Every RTM remains individually dispositioned before any closure claim.

## PCA / BT seed character

RTM-197 is in the Quality / Verifiability / Performance PCA cluster. Its score vector is L=0, R=2, P=2, F=2, Q=3, C=3. This makes it a strong cross-cutting seed: quality/verifiability is high while reliability, performance and functional content are all material.

## First-hop canonical neighbourhood

### OFFER-17 — Preliminary 3D Plant Layout Model

Direct canonical scope: **RTM-193..RTM-197**.

This is the tight primary neighbourhood for RTM-197. Review as one layout/integration evidence package while retaining individual RTM dispositions.

### OFFER-13 — Main Equipment Technical Specifications

Broad/contextual canonical scope:

- RTM-141..RTM-152 — compressor/main-equipment requirements;
- RTM-193..RTM-197 — layout/integration family;
- RTM-236..RTM-257 — storage/inventory/equipment family;
- RTM-263..RTM-267 — external helium withdrawal/recovery family.

OFFER-13 is deliberately marked `Review breadth` in the canonical crosswalk. It is therefore a graph expansion node, not evidence of compliance for every connected RTM.

## Second-hop OFFER nodes reached

The first-hop RTMs connect to narrower canonical OFFERs which should be used to structure manual review:

- **OFFER-15** — RTM-141..147 compressor noise/emission family.
- **OFFER-16** — RTM-148..152 compressor configuration/operating limits.
- **OFFER-19** — RTM-239..248 warm storage heater design/layout.
- **OFFER-20** — RTM-252..257 direct helium leak/loss management plus RTM-258..262 supporting/contextual child requirements.
- OFFER-17 itself remains the direct RTM-193..197 layout package.

The second hop therefore deliberately pulls RTM-258..262 into the neighbourhood even though they were not part of OFFER-13's first-hop range. This is the intended coverage multiplication from bidirectional propagation.

## Manual-review work packages

| Package | RTM scope | Evidence question | Priority treatment |
|---|---|---|---|
| A — layout/integration | RTM-193..197 | Does returned 3D/layout evidence demonstrate the contractual equipment, access, maintainability and integration basis? | Seed package; review first |
| B — compressor equipment | RTM-141..152 | Do technical specifications substantiate noise, configuration, operating limits and associated equipment obligations? | Review with OFFER-15/16 evidence |
| C — storage/inventory | RTM-236..262 | Do equipment, WSH, leak/loss and abnormal-condition evidence form one coherent helium-inventory design? | Review with OFFER-19/20; preserve direct vs supporting edges |
| D — external withdrawal/recovery | RTM-263..267 | Does external-user withdrawal/recovery equipment preserve inventory, interfaces and operational constraints? | Review as connected subsystem family |

## Coverage semantics

Each reached RTM receives one of the following states:

- `GOVERNED_INDIVIDUAL` — Owner baseline and Contractor position have been individually dispositioned.
- `DEPENDENCY_COVERED_PENDING_DISPOSITION` — reached through canonical graph and included in the engineering review package, but no individual disposition yet.
- `EVIDENCE_COMPLETE` — positive returned evidence covers the Owner acceptance definition with deviations resolved.
- `CLOSURE_READY` — evidence complete plus verification route and residual actions controlled.
- `CLOSED` — only after governed Owner closure authority is exercised.

Graph reach must never be reported as compliance or closure.

## DMAIC improvement over earlier waves

**Define:** review unit is a technical neighbourhood, not five arbitrary ranked rows.

**Measure:** one ranked seed reaches four coherent engineering packages and >40 canonical RTMs before individual evidence disposition.

**Analyse:** OFFER-13's intentional breadth makes RTM-197 a high-leverage seed; narrower OFFER-15/16/17/19/20 decompose the broad neighbourhood into reviewable technical packages.

**Improve:** perform manual review by package, reusing evidence across connected RTMs without deleting any requirement.

**Control:** depth limit, edge classes, individual disposition states and closure guardrails prevent uncontrolled graph expansion or false compliance.

## Next evidence action

Recover both Contractor evidence lanes for Package A first (RTM-193..197), then process Packages B-D. Findings from each package propagate back to all connected OFFER nodes and RTMs. Positive evidence is explicitly required where the current state is only no-exception / clarification / proposal reference.

No requirement closure is claimed. Accepted-release HOLD remains independent and unchanged.
