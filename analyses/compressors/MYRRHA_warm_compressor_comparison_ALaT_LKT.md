# MYRRHA Warm-Compressor Comparison: ALaT FSD 575 SFC vs LKT FSD 475 SFC

I went through both applicant pre-studies and the uploaded compressor sheets.

## Bottom line

- ALaT documents a Kaeser **FSD 575 SFC at 72 Hz** as an option for MYRRHA, with a confirmed per-skid full-flow point of **112.54 g/s**.
- LKT documents a Kaeser **FSD 475 SFC** as the selected warm compressor skid, with:
  - actual design nominal total flow = **264 g/s for 3 units**, i.e. **88 g/s per skid**
  - documented max per-skid flow = **96.1 g/s at 62 Hz**

So for your requested target totals:

- **350, 344** are above 3-skid capacity even for the ALaT 575 @ 72 Hz
- **336** is basically right at the limit of 3 × 575
- **304** is above 3 × 475 max
- **200, 250, 275** are feasible for both concepts, depending on operating frequency

## Interactive mass-flow view

The interactive mass-flow explorer (capacity bars, per-skid frequency estimates, and a live status table) is published as a **standalone HTML page**, because GitHub strips `<script>` and `<style>` tags — and inline `style=` attributes — when it renders Markdown, so an embedded version would not run or be styled here.

▶ **[Open the interactive mass-flow comparison](./visualizations/compressor_mass_flow_comparison.html)**

A static snapshot of the same numbers is captured in the [Requested total-flow checks](#requested-total-flows-first-pass-equal-load-check) tables further down, so the analysis is fully readable directly on GitHub.

## Confirmed reference trail

### ALaT pre-study

- **§3.1.1 Warm compressor, p. 15/56** — states standard helium compressors were considered and layout was based on 3 × ESD 445 SFC
- **§4.6 2K nominal mode Summary, p. 30/56** — lists possible compressor solutions, including 2 FSD 575 SFC operating at 72 Hz : ~220 g/s
- **Annex warm compressor datasheet, pp. 67–69/73** — detailed Kaeser data for ESD 445, ESD 445 SFC, FSD 575 SFC (this is also what the uploaded `image.png` and `image (2).png` show)
- **Utilities note C1393-TN-020(1)** — §3.2 Cooling water characteristics, p. 5/8; §8 Power Supply, p. 8/8

### LKT pre-study

- **§6.1.1.1 Refrigerant Compressors, p. 11/50** — says the concept foresees 3 pcs. KAESER FSD475 SFC water cooled
- **§10.2.1 Helium Refrigerant Compressor Unit, Table 16, p. 35/50** — gives the selected compressor spec: 3 × FSD475 SFC, design flow 264 g/s total, max flow 288 g/s total
- **Attachment 04_Main Equipment / 01b_Refrigerant Compressor DataSheet** — detailed FSD 475 SFC utility sheet (same content is visible in the uploaded `image (4).png`)
- **Preliminary Utility List** — §1.3 Cooling Water, p. 4/6; §1.4 Instrument Air, p. 4/6; §1.5 Cooling Air, p. 5/6
- **Indicative Price Proposal, §4 UTILITIES, pp. 10–11/16** — electrical, cooling water, LN2, and instrument-air battery-limit values

## Confirmed utilities per skid

| Item | ALaT FSD 575 SFC | LKT FSD 475 SFC | Source |
|---|---|---|---|
| Confirmed full / nominal basis point | 112.54 g/s @ 72 Hz | 88 g/s actual design nominal (264/3), and 96.1 g/s documented max | ALaT annex pp. 67–69/73; LKT Table 16 p. 35/50 + image (4).png |
| Motor rated power | 315 kW | 250 kW | same |
| Compressor/package input power | 314.05 kW shaft, 348.54 kW package water-cooled | 266 kW nominal w/o LN2, 289 kW documented max | same |
| Cooling water flow | 18.2 m³/h | 15.5 m³/h machine sheet | same |
| Heat rejection to cooling water | 323.9 kW | 230.9 kW | same |
| Cooling air for enclosure | 5,000 m³/h | 5,000 m³/h | same |
| Cooling air for VFD | 4,200 m³/h | 4,200 m³/h | same |
| Heat dissipation by cooling air | 17.4 kW | 13.1 kW | same |
| Waste heat to ambient | 14.2 kW | 5.1 kW | same |
| Noise @ 1 m | 75 dB(A) | 74 dB(A) | same |
| Dimensions | 3240 × 2145 × 2360 mm | 3240 × 2145 × 2360 mm | same |
| Weight | 6770 kg | ~6400 kg | same |
| Oil charge | 173 L | 180 L | same |

## Useful 3-skid totals

| 3-skid total | ALaT 3 × FSD575 | LKT 3 × FSD475 |
|---|---|---|
| Max total mass flow from confirmed basis point | 337.62 g/s | 264 g/s actual nominal, 288.3 g/s documented max |
| Package power | 1045.62 kW | 798 kW nominal, 867 kW max |
| Cooling water flow | 54.6 m³/h | 46.5 m³/h |
| Heat rejection to cooling water | 971.7 kW | 692.7 kW |
| Cooling air, enclosure only | 15,000 m³/h | 15,000 m³/h |
| Cooling air, VFD only | 12,600 m³/h | 12,600 m³/h |

### Important note on LKT utility allowances

LKT has two different levels of cooling-water numbers in the package:

- machine datasheet: **15.5 m³/h per FSD475**
- plant utility / battery-limit allowance:
  - Preliminary Utility List: **60 m³/h total** for KAESER compressors
  - Indicative Price Proposal: **3 × 20 m³/h**

So for LKT, I would read it as:

- equipment-sheet value: **15.5 m³/h per skid**
- site utility allowance / design margin: **~20 m³/h per skid**

## Requested total flows: first-pass equal-load check

### Using ALaT FSD575 full point (112.54 g/s/skid @ 72 Hz)

| Total target | Per skid | Estimated equal-load Hz | Status |
|---|---|---|---|
| 350 | 116.67 g/s | 74.64 Hz | above 3-skid capacity |
| 344 | 114.67 g/s | 73.36 Hz | above 3-skid capacity |
| 336 | 112.00 g/s | 71.65 Hz | OK |
| 304 | 101.33 g/s | 64.83 Hz | OK |
| 275 | 91.67 g/s | 58.65 Hz | OK |
| 250 | 83.33 g/s | 53.31 Hz | OK |
| 200 | 66.67 g/s | 42.65 Hz | OK |

### Using LKT FSD475 actual nominal (88 g/s/skid @ ~57 Hz)

| Total target | Per skid | Estimated equal-load Hz | Status |
|---|---|---|---|
| 350 | 116.67 g/s | 75.57 Hz | above 3-skid capacity |
| 344 | 114.67 g/s | 74.27 Hz | above 3-skid capacity |
| 336 | 112.00 g/s | 72.55 Hz | above 3-skid capacity |
| 304 | 101.33 g/s | 65.64 Hz | above 3-skid capacity |
| 275 | 91.67 g/s | 59.38 Hz | above 3-skid capacity |
| 250 | 83.33 g/s | 53.98 Hz | OK |
| 200 | 66.67 g/s | 43.18 Hz | OK |

### Using LKT FSD475 documented max (96.1 g/s/skid @ 62 Hz)

| Total target | Per skid | Estimated equal-load Hz | Status |
|---|---|---|---|
| 350 | 116.67 g/s | 75.27 Hz | above 3-skid capacity |
| 344 | 114.67 g/s | 73.98 Hz | above 3-skid capacity |
| 336 | 112.00 g/s | 72.26 Hz | above 3-skid capacity |
| 304 | 101.33 g/s | 65.38 Hz | above 3-skid capacity |
| 275 | 91.67 g/s | 59.14 Hz | OK |
| 250 | 83.33 g/s | 53.76 Hz | OK |
| 200 | 66.67 g/s | 43.01 Hz | OK |

> Frequency values are first-pass equal-load estimates using proportional flow-vs-speed scaling from the documented basis point.

## Interpretation against your requested numbers

- **350 g/s design default**
  - not achievable with 3 × FSD575 @ documented 72 Hz
  - definitely not achievable with 3 × FSD475
- **344 g/s**
  - also above documented 3 × FSD575 @ 72 Hz
- **336 g/s**
  - basically the top end of 3 × FSD575
- **304 g/s**
  - comfortably inside 3 × FSD575
  - above 3 × FSD475 max
- **275 g/s**
  - okay for 3 × FSD575
  - okay for 3 × FSD475 max
  - above LKT's actual nominal 264 g/s design point
- **250 g/s, 200 g/s**
  - feasible for both concepts

## Small source previews

- ALaT Kaeser warm compressor datasheet
- LKT compressor specification and FSD475 datasheet

## One caution

I did not fabricate a 72 Hz point for FSD475 because the LKT material only documents:

- actual nominal around **57 Hz / 88 g/s per skid**
- documented max around **62 Hz / 96.1 g/s per skid**

So wherever you asked for "full 72 Hz", that is directly supported for the FSD575, but **not** directly supported for the FSD475 in the supplied documents.

If you want, I can next turn this into either:

- a clean comparison matrix for all requested flow cases, or
- a CSV/XLSX-ready table with all per-skid and total utilities.
