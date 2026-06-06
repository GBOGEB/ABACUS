# ABACUS SVG P&ID — MINERVA QCELL / RFCELL

SVG-driven Piping & Instrumentation Diagram (P&ID) tooling for the MINERVA
QCELL and RFCELL drawings. Produces a colour-line model, a layered 13-layer
atlas, a component catalog, and a tag/instrument register reconciliation —
covering work packages **W001 → W005**.

> 📋 **Pull request:** [GBOGEB/ABACUS #546](https://github.com/GBOGEB/ABACUS/pull/546)

---

## Highlights

- **Stdlib-first.** The Python standard library does all parsing, geometry,
  CSV/JSON/HTML emission and reconciliation. Only **3** third-party packages are
  required for the core pipeline (`openpyxl`, `PyYAML`, `cairosvg`).
- **Fully reproducible.** Every quoted number is regenerated from tracked source
  by a single `./make.sh`; derived artifacts are git-ignored.
- **Honest reconciliation (W005).** The design tag scheme (circuit-sequence,
  e.g. `CV001`/`TT100`) and the as-drawn SVG-instance scheme (e.g.
  `CV560`/`TT514`) are *orthogonal* → **0 exact overlap**, reported per-TYPE:
  97 design tags vs 141 real as-drawn tags (+24 template placeholders).

## Work packages

| Wave | Deliverable |
|------|-------------|
| W001/W002 | Colour-line model + collage (`cli.py`, `render_collage`) |
| W003/W004 | Layer hierarchy, geometry/arrow tracing, PEMO (`build_w003_w004`) |
| W005 | Tag & instrument register reconciliation (`build_w005`) |
| — | Layered 13-layer atlas v6 (`build_atlas_v6`), component catalog (`build_catalog`) |

## Quick start

```bash
sudo apt-get install -y libcairo2           # native dep for CairoSVG
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt             # exact reproducible pins
./make.sh                                   # regenerate all derived outputs
PYTHONPATH=src python3 tests/test_integration_pipeline.py
```

Full instructions: **[docs/INSTALLATION.md](docs/INSTALLATION.md)** ·
Native libraries: **[SYSTEM_DEPENDENCIES.md](SYSTEM_DEPENDENCIES.md)**

## Repository layout

```
src/abacus_svg_pid/   core pipeline (cli, build_*, render_collage)
generator/            auxiliary slide-deck / HTML-viewer tooling (optional deps)
standards/            legend/library builders
segmentation/         segmentation data + helpers
configs/              YAML colour-line & layer models
data/svg/             tracked source SVGs (QCELL, RFCELL)
tests/                standalone test runners (no pytest)
docs/                 plans, manifests, installation guide
make.sh               one-command reproducible regeneration
```

## Dependencies

| Package | Role | Required by |
|---------|------|-------------|
| `openpyxl` | XLSX catalog + W005 register | core (`make.sh`) |
| `PyYAML` | YAML colour/layer model | core (`make.sh`) |
| `cairosvg` | SVG → PNG/PDF rasterisation | core (`make.sh`) |
| `Pillow` | preview raster compositing | optional (`generator/`) |
| `python-pptx` | dissection slide-deck | optional (`generator/`) |

See [`requirements.txt`](requirements.txt) for exact pins and
[`pyproject.toml`](pyproject.toml) for packaging metadata.
