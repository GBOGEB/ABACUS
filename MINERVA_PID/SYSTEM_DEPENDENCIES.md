# System Dependencies

The ABACUS SVG P&ID pipeline is **Python-stdlib-first**. The only non-Python
system requirement comes from one package: **CairoSVG**, which binds to the
native Cairo graphics library for SVG → PNG/PDF rasterisation. Everything else
(`openpyxl`, `PyYAML`, `python-pptx`) is pure Python, and `Pillow` ships
self-contained binary wheels on all mainstream platforms.

| Capability                         | Python package | Native system library         |
|------------------------------------|----------------|-------------------------------|
| SVG → PNG/PDF (atlas v6, collage)  | `cairosvg`     | **Cairo** (`libcairo2`)       |
| XLSX catalog / W005 register       | `openpyxl`     | none (pure Python)            |
| YAML colour/layer model            | `PyYAML`       | none (wheel-bundled libyaml)  |
| Raster compositing (previews)      | `Pillow`       | none (binary wheel)           |
| Dissection slide-deck (.pptx)      | `python-pptx`  | none (pure Python)            |

## Install the native Cairo library

### Debian / Ubuntu
```bash
sudo apt-get update
sudo apt-get install -y libcairo2 libcairo2-dev
```

### Fedora / RHEL / CentOS
```bash
sudo dnf install -y cairo cairo-devel
```

### macOS (Homebrew)
```bash
brew install cairo
```

### Windows
CairoSVG bundles the required Cairo DLLs in its wheel on Windows, so no
separate install is normally needed. If you hit a `cairocffi`/`OSError`, install
GTK runtime (which provides `libcairo-2.dll`) and ensure it is on `PATH`.

## Verifying

```bash
python3 -c "import cairosvg; print('cairosvg OK', cairosvg.__version__)"
```

If this prints a version without an `OSError`, the native Cairo library is
correctly installed and the full `./make.sh` pipeline can run.

## Notes

- **No system database, browser, or headless-Chrome dependency.** HTML
  deliverables are emitted as static files; nothing needs to be rendered by a
  browser engine.
- The CI workflow (`.github/workflows/minerva-pid-test.yml`) installs
  `libcairo2` on the Ubuntu runner before running the test suite.
- Python **3.8+** is required (see `pyproject.toml`); the deliverables were
  produced and validated on Python 3.11.
