# Installation & Quick Start

This guide gets the ABACUS SVG P&ID pipeline (MINERVA QCELL/RFCELL, W001–W005)
running from a clean checkout and reproduces every quoted deliverable number.

> **Design philosophy:** the pipeline is *stdlib-first*. Only three packages are
> required for the core regeneration (`./make.sh`); two more are optional and
> only used by the slide-deck / preview generators. See
> [`SYSTEM_DEPENDENCIES.md`](../SYSTEM_DEPENDENCIES.md) for native libraries.

---

## 1. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python      | **3.8+** (validated on 3.11) | `python3 --version` |
| Cairo       | `libcairo2` | Native lib for CairoSVG — see below |
| pip         | recent  | `python3 -m pip --upgrade pip` |

Install the one native library (Debian/Ubuntu):

```bash
sudo apt-get update && sudo apt-get install -y libcairo2 libcairo2-dev
```

(See [`SYSTEM_DEPENDENCIES.md`](../SYSTEM_DEPENDENCIES.md) for macOS / Fedora / Windows.)

---

## 2. Create a virtual environment & install Python deps

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Exact, reproducible pins used for the W001–W005 deliverables:
pip install -r requirements.txt

# — or — install as a package (core deps only):
pip install .
# with the optional slide-deck / preview tooling:
pip install ".[deck]"
```

Verify the native binding:

```bash
python3 -c "import cairosvg; print('cairosvg OK', cairosvg.__version__)"
```

---

## 3. Regenerate all derived outputs

Derived artifacts (`output_v6/`, `data/model/`, `data/pemo/`, `data/excel/`,
`publish/`, `reports/*.xlsx`) are **git-ignored** — you regenerate them from the
tracked source (`src/`, `segmentation/data/*.json`, `configs/`, `data/svg/`):

```bash
./make.sh            # full regeneration
./make.sh --clean    # wipe derived outputs first, then regenerate
```

The pipeline runs six stages in order:

1. `cli.py` — W001/W002 colour-line model (**must run first**)
2. `build_w003_w004` — layer hierarchy + geometry/arrow tracing + PEMO
3. `build_catalog` — component catalog (XLSX + HTML)
4. `build_w005` — tag & instrument register reconciliation
5. `build_atlas_v6` — layered 13-layer atlas (SVG/PDF/HTML)
6. `render_collage` — colour-line collage (W002 publish deliverable)

---

## 4. Run the tests

The test suite uses **plain standalone runners** (no pytest dependency). Each
file self-reports `N/N assertions passed`:

```bash
export PYTHONPATH=src
python3 tests/test_colour_model.py
python3 tests/test_integration_pipeline.py
python3 tests/test_w003_w004.py
python3 tests/test_w005_reconciliation.py
```

> **Note:** the data-dependent suites (`test_colour_model`, `test_w003_w004`,
> `test_w005_reconciliation`) auto-**SKIP** their data-backed assertions if you
> have not yet run `./make.sh`. Run `./make.sh` first for the full 31/31 pass.

Run them all in one line:

```bash
export PYTHONPATH=src
for t in tests/test_*.py; do echo "== $t =="; python3 "$t" || exit 1; done
```

---

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `OSError: no library called "cairo-2"` | Install `libcairo2` (step 1). |
| `ERROR: expected >= 2 source SVGs` | Ensure `data/svg/QCELL.svg` and `RFCELL.svg` exist before `./make.sh`. |
| Tests print `SKIP … data not built` | Run `./make.sh` first to generate `data/model/`, `data/excel/`. |
| `ModuleNotFoundError: abacus_svg_pid` | Set `export PYTHONPATH=src` (or `pip install .`). |
