# MINERVA CryoCell — P&ID v2 Drawing Set Index

**Project:** MINERVA CryoCell — SCK CEN
**Drawing No.:** SCK CEN/84836013
**Sheet size:** A3 landscape (420 × 297 mm)
**Standards basis:** ANSI/ISA-5.1-2022, ISO 10628, IEC 60617, SCK CEN tag scheme `W-X:Y-Z-1`

---

## 1. Drawing split

The two original source drawings were each split into **two focused sheets** to
improve readability. Each sheet is delivered in **two style versions**.

| Source | Sheet | Focus |
|--------|-------|-------|
| QCELL / LB | Sheet 1 — Cryogenic | 40 K / 4.5 K / 2 K circuits + heat exchangers, vessels, valves |
| QCELL / LB | Sheet 2 — Instrumentation | Sensors, control loops, DIS interlock, signals |
| RFCELL (seen by ACR) | Sheet 1 — Process | DI-water / coupler process flow |
| RFCELL (seen by ACR) | Sheet 2 — Instrumentation | Sensors, control loops, DIS interlock, signals |

## 2. Style versions

| Version | Filename suffix | Description |
|---------|-----------------|-------------|
| **B — Standard** | `_STANDARD` | Balanced, full colour. Process lines primary (1.0 mm), equipment secondary (0.7 mm), bubbles 2 mm, signals 0.25 mm, tags 2.5 mm. |
| **A — Control-Centric** | `_CONTROL-CENTRIC` | Signals emphasised. Process de-emphasised to grayscale (0.5 mm), equipment background (0.35 mm), bubbles 3 mm, signals colour 0.5 mm, tags 3.5 mm. |

> Bubble diameters were scaled up from the 2 mm / 3 mm nominal to keep two-line
> ISA tags legible at the drawing's information density, while preserving the
> A > B emphasis relationship exactly.

## 3. File manifest (8 SVG + 8 PDF = 16 files)

### output_v2/QCELL/
- `QCELL-Sheet1-Cryogenic_STANDARD.svg` / `.pdf`
- `QCELL-Sheet1-Cryogenic_CONTROL-CENTRIC.svg` / `.pdf`
- `QCELL-Sheet2-Instrumentation_STANDARD.svg` / `.pdf`
- `QCELL-Sheet2-Instrumentation_CONTROL-CENTRIC.svg` / `.pdf`

### output_v2/RFCELL/
- `RFCELL-Sheet1-Process_STANDARD.svg` / `.pdf`
- `RFCELL-Sheet1-Process_CONTROL-CENTRIC.svg` / `.pdf`
- `RFCELL-Sheet2-Instrumentation_STANDARD.svg` / `.pdf`
- `RFCELL-Sheet2-Instrumentation_CONTROL-CENTRIC.svg` / `.pdf`

## 4. Companion documentation
- `01_LAYER_STRUCTURE_GUIDE.md` — the 14-layer toggleable hierarchy.
- `02_SENSOR_REALLOCATION.md` — sensor re-allocation mapping.
- `03_SCOPE_BOUNDARY_REFERENCE.md` — TPXYYYY scope-boundary reference table.
- `_build_meta.json` — machine-readable build metadata (re-allocations, scope codes).

## 5. Regeneration
```
cd generator && python3 build_pid_v2.py          # writes the 8 SVGs
python3 -c "import cairosvg,glob; [cairosvg.svg2pdf(url=f,write_to=f[:-4]+'.pdf') for f in glob.glob('../output_v2/*/*.svg')]"
```
All geometry is reproduced from the structured segmentation data and the
extracted symbol library; nothing is hand-placed bitmap.
