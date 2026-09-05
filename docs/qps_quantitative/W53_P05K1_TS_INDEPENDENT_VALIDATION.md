# W53/P05K1 — First strict thermal-shield residual closure

## 1. Purpose

Convert the strongest P05J diagnostic result into a governed strict residual candidate using the **exact current ALAT thermal-shield state**, an independent contract mass-flow anchor, and at least one independent helium-property calculation.

This wave is intentionally narrow. It does not add architecture. It either earns the first strict numerical residual or records the precise evidence/property reason why it remains deferred.

## 2. Source hierarchy

### 2.1 Contract anchors

- Table 8, 2K-OP: `QTS = 8200 W`.
- Table 9, 2K-OP: `D ≈ 77 g/s`, `E ≈ 77 g/s`.
- Contract `≈77 g/s` is a design-flow semantic, not an exact metrology value. Any strict acceptance must state and govern the tolerance used for that approximation.

### 2.2 Current ALAT offer — exact non-binding thermodynamic example

Source: `C1462-TN-001_0_SCK_CEN_MYRRHA_Phase_1_Technical_Proposal`.

Controlled locators already recovered in the child SSOT:

- guaranteed performance: page 55/81 section 3;
- guaranteed conditions: page 56/81;
- non-binding thermodynamic example inputs: page 59/81;
- non-binding thermodynamic example outputs: page 60/81.

Exact TS example:

| Variable | D inlet | E outlet |
|---|---:|---:|
| Pressure | 14.12 bara | 13.12 bara |
| Temperature | 35 K | 55 K |
| Bidder enthalpy | 196438 J/kg | 302915 J/kg |
| Bidder entropy | 14861 J/kg/K | 17428 J/kg/K |

Additional source values:

- `QTS = 8200 W`;
- bidder example label = `example and non-binding`;
- reconstructed flow from bidder values = `77.01 g/s`.

The bidder reconstructed flow is **not independent** of bidder duty/enthalpy and therefore cannot by itself earn a strict residual PASS.

## 3. Strict-residual definitions

### 3.1 Primary cross-source residual candidate

Use:

- current ALAT exact D/E state from pages 59–60;
- **contract independent design-flow anchor ≈77 g/s**;
- independent governed helium properties.

Calculate:

`Q_pred = mdot_contract * [h(P_E,T_E) - h(P_D,T_D)]`

Residuals:

- `R_Q_W = Q_pred - 8200 W`;
- `R_Q_pct = R_Q_W / 8200 * 100`.

Also calculate inverse flow:

`mdot_pred = 8200 / Δh`

and compare to contract `≈77 g/s`.

### 3.2 Bidder internal-consistency receipt

Separately calculate:

`Q_bidder = 0.07701 * (302915 - 196438)`.

This checks transcription/internal consistency only. It is explicitly `NON_INDEPENDENT_SOURCE_CONSISTENCY` and cannot count as the strict residual.

### 3.3 Property-reference cross-check

Run exact D/E state against:

1. governed CoolProp 7.2.0 normal-fluid provider;
2. a genuinely independent reference where recoverable: HEPAK, MBWR/Aspen-HYSYS, REFPROP-equivalent governed source, or a source table with exact state enthalpies.

Historical ALAT pre-study establishes method lineage (`Aspen HYSYS v10 / MBWR / HEPAK v3.4`) but does **not** automatically provide exact current-state property values. Historical method similarity therefore cannot silently satisfy the independent-reference gate.

If an exact independent reference cannot be recovered, disposition is `DEFER_INDEPENDENT_PROPERTY_REFERENCE` even if CoolProp residual is numerically excellent.

## 4. Tolerance semantics

The contract uses approximately `77 g/s`. P05K1 shall therefore report sensitivity at minimum for:

- 76.5 g/s;
- 77.0 g/s;
- 77.5 g/s;

and, if justified by the controlled contract interpretation, a broader envelope such as ±1 g/s.

No tolerance may be invented after seeing the residual. The child acceptance record must state the adopted tolerance semantics before scoring PASS.

## 5. Required quantitative outputs

- exact source locator and source SHA;
- D/E P/T values;
- provider IDs and versions;
- `h_D`, `h_E`, `Δh` for each provider;
- `Q_pred` at each governed flow point;
- absolute and relative duty residual;
- inverse predicted flow for 8200 W;
- flow residual against 77 g/s;
- provider-to-provider `Δh` disagreement %;
- bidder-table internal consistency residual;
- tolerance sensitivity table;
- uncertainty statement;
- final candidate disposition.

## 6. Negative tests / fail-closed rules

Reject or defer if any of the following occurs:

- reconstructed ALAT 77.01 g/s is represented as an independent source;
- current non-binding D/E state is represented as a guaranteed fixed BOP;
- rounded 14/40→13/60 state substitutes for the exact ALAT 14.12/35→13.12/55 state;
- `A=B+W` or any other topology identity is scored as an independent residual;
- CoolProp is treated as an independent reference to itself;
- historic pre-study data overwrite the current offer;
- missing property evidence is imputed;
- tolerance is selected post hoc to create PASS;
- parent runtime self-promotes child compliance.

## 7. DoV metrics

Record separately:

- `strict_residual_count_pass/defer/fail`;
- `same_boundary_source_completeness_pct`;
- `independent_reference_coverage_pct`;
- `provider_agreement_pct`;
- `residual_abs_W`;
- `residual_pct`;
- `flow_residual_g_s`;
- `source_bound_fraction`;
- `provenance_completeness_pct`;
- `formal_credit_delta`;
- `diagnostic_DoV_delta`.

A diagnostic numerical result may raise model/evidence DoV but formal engineering score changes only after child acceptance against a governed obligation.

## 8. PCA / Bradley–Terry integration

P05K1 contributes observed quantitative features to the next PCA population:

- thermo residual %;
- property-provider disagreement %;
- independent-reference coverage;
- source-bound fraction;
- provenance completeness;
- uncertainty width;
- execution/retry count.

For Bradley–Terry planning, compare at least:

- `K1_TS_INDEPENDENT_REFERENCE`;
- `K2_LINES_TRANSIENT_REPAIR`;
- `K3_VLP_FLOW_KCV_SOURCE_BINDING`;
- `HEPAK_LOW_T_REFERENCE`;
- `LOCAL_WORKER_BUILDOUT`.

Priority is diagnostic only and never compliance authority.

## 9. Definition of Done

P05K1 is done when one of two outcomes is source-proven:

### Outcome A — strict PASS candidate

- exact ALAT D/E state bound;
- independent contract ≈77 g/s semantics governed;
- CoolProp receipt generated;
- independent property reference generated;
- residual within predeclared governed tolerance;
- CODEX semantic/provenance validation PASS;
- child records `ACCEPT` for the strict residual.

### Outcome B — precise DEFER

All numerical work is complete, but the exact missing blocker is named, normally independent exact-state property validation or governed tolerance semantics.

## 10. Victory condition

**First genuine QPLANT strict numerical residual = 1/5**, without source circularity, post-hoc tolerance, or parent self-promotion.
