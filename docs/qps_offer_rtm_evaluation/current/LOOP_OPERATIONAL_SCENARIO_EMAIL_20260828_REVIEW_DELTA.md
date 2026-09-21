# QPS LOOP operational scenario — RTM/OFFER review delta

Status: **SOURCE-SUPPORTED INTERFACE EVIDENCE — NO REQUIREMENT CLOSURE / NO SCORE CHANGE**

## Source provenance

- Source: Outlook email `QPS LOOP event - operational scenario`
- Sender: Daniel Berkowitz, SCK CEN
- Date: 2026-08-28
- Referenced historical source: DSBT DEL2.1
- Evidence class: email operational statements = **SOURCE-SUPPORTED**; historical curves = **SUPPORTING ENGINEERING / ORDER-OF-MAGNITUDE**
- Authority rule: Contract/Addendum II and the governed RTM remain **CONTROLLED**

The email explicitly states that the DEL2.1 curves are already outdated and are retained only to indicate orders of magnitude. They are not selected-design acceptance values.

## Operational sequence captured by the email

1. Loss of normal power initiates diesel-generator backup service.
2. NA.ES02 can energise **one QPS HP compressor after 30 min**, with **15 min preferred**.
3. Transfer from normal to backup power is **automatic** following power loss.
4. Return from backup to normal power is **manual**, triggered by operators after normal power is restored.
5. Maximum backup-power demand is expected for approximately **1–2 h**, after which demand drops significantly.
6. NA.ES02 design must be capable of the required sequence and load.
7. The QPS Contractor must explicitly confirm compatibility with this interface.
8. The mass-flow capability of one HP compressor is capped at approximately **100 g/s** for this interface scenario.

These statements define a review/acceptance interface. They do not themselves prove the QPS or either bidder design compliant.

## Governed RTM/OFFER impact matrix

| Anchor | Evidence effect | Review disposition |
|---|---|---|
| RTM-051 | Refines the electrical abnormal-event sequence with actual transfer, restart-delay, load-duration and restoration assumptions. | OPEN / REVIEW; no canonical OFFER back-fill. |
| RTM-258 / OFFER-21 | Converts “critical load management” into a time-sequenced interface: one HP, 15/30 min start, automatic backup transfer, manual normal retransfer, ~1–2 h peak load. | OPEN; Contractor confirmation required. |
| RTM-260 / OFFER-22 | ≤1% abnormal-event loss must be proven through the pre-HP delay and active-recovery phases. | OPEN; buffer/WSH/Line-S/relief chain required. |
| RTM-261 / OFFER-22 | Contract requirement remains ≥100 g/s abnormal/LOOP without inventory loss. Approximate one-HP site cap is ~100 g/s. | OPEN; bidder values >100 g/s are not automatically creditable on LOOP. |
| RTM-262 / OFFER-22 | Recovery procedure must include operator-triggered normal-power retransfer and restoration of normal helium circulation. | OPEN. |
| RTM-428 | Existing backup cooling-water availability must be reconciled with the HP start delay, one-HP load, auxiliaries and continuous duty. | OPEN; no inference that 350 kW alone proves recovery. |
| RTM-436 | Emergency one-HP operation remains subject to exhaust-duct availability and the compressor-room ambient heat-release boundary. | OPEN. |
| RTM-433 | Email adds no instrument-air evidence. | UNCHANGED / OPEN. |

## Bidder-specific review effect

### LKT

Current source-bound offer evidence describes about 110 g/s LOOP recovery with one emergency-powered HP compressor. The new SCK CEN interface evidence prevents that 110 g/s claim from being used unqualified as the site LOOP point: NA.ES02 currently caps the one-HP interface at approximately 100 g/s and does not energise the compressor until 15–30 min after normal-power loss.

Therefore:

- any argument that an approximately 110–112 g/s HP compressor satisfies the LOOP case **provided suction is running at event onset** is not a LOOP closure argument;
- LKT must demonstrate the 15–30 min bridge using selected Line-S/WSH inventory, initial pressure, relief margin and controls;
- any credit above ~100 g/s requires explicit NA.ES02 electrical/load confirmation;
- the existing lack of a guaranteed ≤1% inventory-loss result remains open.

### ALAT

Current source-bound offer evidence gives a nominal LOOP recovery point of about 80 g/s at 275 kW and an expected, not guaranteed, point near 100 g/s at about 340 kW, with cooling-water and backup-power dependencies.

Therefore:

- 80 g/s remains below the RTM-261 abnormal/LOOP flow requirement;
- the expected ~100 g/s point is directionally aligned with the approximate site one-HP cap but remains unguaranteed;
- the 15–30 min pre-start interval and associated buffer/pressure/helium-loss proof remain open;
- available backup power, cooling water, controls and instrument air remain acceptance dependencies.

## Required clarification / acceptance package

The next evidence return from each Applicant should provide one integrated LOOP sequence rather than isolated equipment claims:

1. A time-sequenced load/state table covering **0–15 min**, **15–30 min**, **30–120 min** and **>120 min**, including HP motor/VFD starting demand, continuous electrical demand, controls, actuators, auxiliaries, cooling water, instrument air and heat rejection.
2. Confirmation that the offered QPS is compatible with automatic transfer to backup power and manual operator-triggered return to normal power.
3. Selected-design proof of Line-S/WSH pressure and inventory behaviour over the 15–30 min period before one HP compressor becomes available.
4. Demonstration of RTM-260 / RTM-261 helium-loss and flow requirements for the selected initial pressure/state, including relief margin and the disposition of the 150 g/s / 200 g/s transient envelope.
5. Explicit confirmation of the accepted one-HP emergency-power flow point and electrical/cooling duty at that point.
6. A verified post-LOOP restoration sequence satisfying RTM-262.
7. FAT/SAT or equivalent verification hooks for transfer logic, compressor start timing, limited-service load shedding, sustained emergency operation and restoration.

## Control / anti-overclaim rules

- No RTM wording is changed by this email.
- No v24 rank/tier, BT/PCA value, OFFER score or bidder compliance credit is changed by this review delta.
- The approximate 100 g/s one-HP cap remains source-supported interface evidence until controlled NA.ES02 design data is issued.
- The historical DEL2.1 curves are not selected-design or contractual values.
- The ~1–2 h peak backup-power window does **not** replace the controlled LOOP duration tiers or any longer-duration recovery/inventory requirement.
- A diesel-generator rating, cooling-water rating or compressor nameplate value alone does not prove the end-to-end LOOP function.
