# Sensor Re-allocation Mapping

Derived from the QSYS instrumentation-location study (LB / LBI) and the
QM instrumentation & controls brainstorming. The goal is to monitor the Piezo
(PZ) tuner thermal gradient and the MAG / coupler thermalisation points with the
correct cryogenic sensor technology.

## 1. Sensor technologies

| Sensor type | Technology | Best for |
|-------------|-----------|----------|
| **TT-CX** | Cernox® resistance thermometer | Coldest points (≤ 4 K range), high sensitivity at low T |
| **TT-PT100** | Pt-100 RTD | Warmest points (> 40 K range), stable at higher T |

## 2. Primary re-allocations (PZ — Piezo tuner)

| Original tag | New tag | Sensor type | Position | In source geometry |
|--------------|---------|-------------|----------|--------------------|
| **TT535** | PZ535 | **TT-CX** | Coldest part of the Piezo (PZ) | ✅ yes — re-tagged & ring-highlighted on drawing |
| **TT525** | PZ525 | **TT-PT100** | Warmest part of the Piezo (PZ) | ⚠ design re-allocation — tag not present in current source extract; applied automatically if/when present |

> On the drawings, a re-allocated sensor is shown as a normal ISA bubble with a
> dashed **red highlight ring** and a red sensor-type label (`TT-CX` / `TT-PT100`).

## 3. MAG & coupler-port redistribution

TT-CX and TT-PT100 sensors are redistributed to monitor the MAG component and
the coupler thermalisation ports:

| Sensor type | Location | Purpose |
|-------------|----------|---------|
| TT-CX | MAG cold port | Cold-end temperature of the MAG |
| TT-PT100 | MAG warm port | Warm-end temperature of the MAG |
| TT-CX | Coupler port (cold) | Coupler thermalisation, cold side |
| TT-PT100 | Coupler port (warm) | Coupler thermalisation, warm side |

## 4. PZ monitoring strategy (summary)

- **TT-CX → coldest part of the Piezo** (maximum sensitivity in the 2–4 K band).
- **TT-PT100 → warmest part of the Piezo** (stable readout in the 40–300 K band).
- The pair brackets the PZ thermal gradient so the control system can verify
  that the actuator stays within its allowable temperature window.

## 5. Where to see it
- Re-allocated PZ sensors appear on the **Instrumentation sheets** (Sheet 2)
  of both QCELL and RFCELL, on **Layer 9 — Instruments** (bubble) with the
  red highlight, and the sensor-type callout on **Layer 12 — Tags**.
- The machine-readable record is in `_build_meta.json` under `realloc` /
  `mag_coupler`.
