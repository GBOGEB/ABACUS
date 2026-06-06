# MINERVA QCELL/RFCELL P&ID — Colour-Line Engineering Process Model (W001–W005)

> Subproject of the `ABACUS` repository. Programme: Mott MacDonald / SCK CEN — MYRRHA-MINERVA Phase 1.

Decomposes the real QCELL/RFCELL P&ID SVGs into colour-defined process lines, a layer
hierarchy, geometric flow tracing, a component catalog, and an XLSX tag/instrument register
reconciliation — across five delivered waves (W001–W005).

## Quick start (full reproducibility)

Derived outputs (`data/model/`, `data/pemo/`, `data/excel/`, `output_v6/`, `publish/`,
`reports/*.xlsx`) are **git-ignored** — regenerable, not source of record.

```bash
cd MINERVA_PID
./make.sh                                                   # regenerate ALL derived outputs

PYTHONPATH=src python3 tests/test_integration_pipeline.py   # source-only smoke test (no data needed)
PYTHONPATH=src python3 tests/test_colour_model.py           # W002 (after make.sh)
PYTHONPATH=src python3 tests/test_w003_w004.py              # W003/W004 (after make.sh)
PYTHONPATH=src python3 tests/test_w005_reconciliation.py    # W005 (after make.sh)
```

Verified: fresh `make.sh` exit 0 → **31/31 tests pass**.

## Setup & dependencies

The pipeline is **stdlib-first** — only three packages are required for the core
`make.sh` regeneration (`openpyxl`, `PyYAML`, `cairosvg`), plus two optional ones
for the slide-deck / preview tooling (`Pillow`, `python-pptx`).

```bash
sudo apt-get install -y libcairo2   # native dep for CairoSVG (see SYSTEM_DEPENDENCIES.md)
pip install -r requirements.txt     # exact reproducible pins
```

- **Exact pins:** [`requirements.txt`](requirements.txt)
- **Packaging metadata / optional extras:** [`pyproject.toml`](pyproject.toml)
- **Native system libraries:** [`SYSTEM_DEPENDENCIES.md`](SYSTEM_DEPENDENCIES.md)
- **Step-by-step guide:** [`docs/INSTALLATION.md`](docs/INSTALLATION.md)

These manifests also feed GitHub's dependency graph / Dependabot
(`/MINERVA_PID` pip ecosystem) so the subproject is tracked for security updates.

## Waves delivered

| Wave | Scope |
| --- | --- |
| W001 | Source ingestion & style extraction (inline-style colour precedence) |
| W002 | Colour-line decomposition into canonical process lines + validation |
| W003 | 13 top-level layers (21 named sub-layers); per-element assignment |
| W004 | Geometric arrow/flow tracing, element pairing, 297-component catalog, PEMO SSOT |
| W005 | XLSX tag & instrument register reconciliation (coverage delta + canonical SSOT) |

## Key documents

- **Full PR description:** `docs/PR1_DESCRIPTION_COMBINED.md`
- **Capability matrix (honest "Claim ≠ Complete"):** `docs/CAPABILITY_MATRIX.md`
- **W005 reconciliation report:** `reports/W005_XLSX_RECONCILIATION_REPORT.md`
- **Governance / wave status:** `reports/wave_status.json`, `configs/wave_registry.json`

## W005 headline finding

The design nomenclature register (circuit-sequential `CV001`/`TT100`…) and the as-drawn catalog
(SVG-instance `CV560`/`TT514`…) use **orthogonal numbering schemes** → **exact tag overlap = 0**.
This is a genuine engineering finding (not a defect); coverage is reported **per instrument TYPE**,
and the recommended next deliverable is a **design ↔ as-drawn cross-map**.
