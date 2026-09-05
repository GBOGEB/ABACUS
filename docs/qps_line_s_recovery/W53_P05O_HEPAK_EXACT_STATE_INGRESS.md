# W53-P05O — exact HEPAK state ingress

## Purpose

Close the only remaining independent-property blocker for the corrected QPLANT A→B residual without substituting CoolProp, interpolation, or a nearby NIST pressure row for the required exact state.

## Governed states

| State | T [K] | P [Pa] | Required outputs |
|---|---:|---:|---|
| A | 4.5 | 300000 | density_kg_m3, enthalpy_J_kg |
| B | 3.6 | 2200 | density_kg_m3, enthalpy_J_kg |

Run these two points in **licensed HEPAK v3.4** using temperature + absolute pressure as independent variables. Record the HEPAK version/build, execution date, engineer, and export method. Do not use CoolProp to populate the reference file.

## Export

1. Copy `he_reference_hepak_TEMPLATE.csv` to `he_reference_hepak.csv`.
2. Populate only the two density and enthalpy values produced by HEPAK plus provenance columns.
3. Keep SI units exactly as defined by the existing loader: K, Pa, kg/m3, J/kg.
4. Commit the frozen CSV. The licensed HEPAK executable/workbook itself must not be committed.

The existing `models/helium_properties/hepak_reference.py` loader remains the acceptance ingress. Missing file or missing required columns is `UNVALIDATED`, never PASS.

## Automatic calculation after the two rows exist

Use:

- `delta_h = h_B - h_A`
- `m_B = 890 / delta_h` kg/s
- convert `m_B` to g/s.

Acceptance gates:

1. exact A and B states are present with independent HEPAK provenance;
2. `m_B >= 39.0 g/s` because Table 9 is a lower-bound capability requirement;
3. the same-boundary 890 W calculation is within the governed ±1% numerical tolerance when evaluated at the selected source-bound flow;
4. the child receipt explicitly records ACCEPT or FAIL.

For orientation only, the maximum independent `delta_h` compatible with the 39 g/s lower bound is `890 / 0.039 = 22820.5128 J/kg`. This threshold is a gate, not a property estimate.

## Independent corroboration already frozen

NIST TN1334 provides an exact A row at 4.5 K / 300 kPa. The available 3.6 K / 10 kPa B-side row gives an independent pressure-bracket calculation of 41.280 g/s. That is supporting evidence only; it does not replace the exact 3.6 K / 2.2 kPa HEPAK row.

The historic ALAT pre-study explicitly records its process stack as Aspen HYSYS v10.0 + MBWR with **Helium properties HEPAK v3.4**, establishing HEPAK v3.4 as project-era independent methodology. It does not publish the exact required enthalpy pair and therefore cannot itself close the gate.

## Stop rule

No further property-model architecture, dashboard, or proxy interpolation earns credit. The next state transition is only:

`HEPAK two-row export -> frozen CSV -> loader receipt -> delta-h -> B-flow -> 890 W gate -> child ACCEPT/FAIL`.
