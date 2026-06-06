# Follow-up PR #547 — Summary Report

**Repo:** `GBOGEB/ABACUS` · **Follow-up PR:** [#547](https://github.com/GBOGEB/ABACUS/pull/547) (open) ·
**Parent PR:** [#546](https://github.com/GBOGEB/ABACUS/pull/546) (merged 2026-06-05) ·
**Branch:** `minerva-pid-improvements` → `main`

---

## 1. The problem — snapshot warning

GitHub reported on PR #546:

> *"No snapshots were found for the head SHA `dd35898`."*

**Root cause:** GitHub's dependency graph builds a *dependency snapshot* by scanning a
commit for package manifests (`requirements.txt`, `pyproject.toml`, `package.json`, …).
The `MINERVA_PID/` subproject shipped **none** — so GitHub had nothing to record, hence
*no snapshot* and the warning. It is **not** a build or security failure; it just means the
subproject was invisible to the dependency graph and to Dependabot.

**Fix:** add manifests GitHub can detect under `MINERVA_PID/`, and register the directory
with Dependabot. Done in this PR.

---

## 2. Honest dependency audit (the important part)

The original task template suggested a large `requirements.txt` (pandas, numpy, scipy,
lxml, svgwrite, markdown, jinja2, pytest, pytest-cov, …). **An import audit of every
`.py` file proved most of those are never used.** Declaring them would have created fake
dependencies and a false vulnerability surface — the opposite of this project's
stdlib-first, "Claim ≠ Complete" discipline.

**Actual third-party imports across the entire source tree = exactly 5 packages:**

| Package | Pinned | Imported as | Role | Tier |
|---------|--------|-------------|------|------|
| `openpyxl` | `3.1.5` | `openpyxl` | XLSX catalog + W005 register | **core** (`make.sh`) |
| `PyYAML` | `6.0.2` | `yaml` | YAML colour/layer model | **core** (`make.sh`) |
| `cairosvg` | `2.9.0` | `cairosvg` | SVG → PNG/PDF rasterisation | **core** (`make.sh`) |
| `Pillow` | `10.4.0` | `PIL` | preview raster compositing | optional (`generator/`) |
| `python-pptx` | `1.0.2` | `pptx` | dissection slide-deck | optional (`generator/`) |

Everything else is the **Python standard library** (`csv, json, xml, html, re, math,
datetime, glob, os, sys, collections, tempfile, __future__`). Tests use **no pytest** —
they are standalone `__main__` runners.

---

## 3. What was delivered

### Pushed in PR #547 (7 files)

| File | Status | Purpose |
|------|--------|---------|
| `MINERVA_PID/requirements.txt` | added | exact reproducible pins (5 packages) |
| `MINERVA_PID/pyproject.toml` | added | PEP 621 metadata; core deps + optional `[deck]` extra |
| `MINERVA_PID/SYSTEM_DEPENDENCIES.md` | added | native `libcairo2` requirement for CairoSVG |
| `MINERVA_PID/docs/INSTALLATION.md` | added | step-by-step install / regenerate / test |
| `MINERVA_PID/README.md` | modified | new "Setup & dependencies" section |
| `MINERVA_PID/make.sh` | modified | corrected stale `pytest` hint → standalone runner |
| `.github/dependabot.yml` | modified | new `pip` entry for `/MINERVA_PID` (weekly) |

### Source-of-record (standalone `pr1-w001-w005` branch / `pid_project`)

The same manifests + docs were authored and committed here first, with conventional
commits:
- `chore(deps): add dependency manifests and system requirements (W001-W005)`
- `docs: add project README and installation guide`
- `fix(make): correct test-run hint to standalone runners (no pytest)`

---

## 4. Validation

```text
./make.sh                                  → exit 0 (6 stages)
PYTHONPATH=src python3 tests/test_colour_model.py          → 5 passed
PYTHONPATH=src python3 tests/test_integration_pipeline.py  → 5/5
PYTHONPATH=src python3 tests/test_w003_w004.py             → 10/10
PYTHONPATH=src python3 tests/test_w005_reconciliation.py   → 11/11
                                                    TOTAL = 31/31 ✅
```

YAML linted: `.github/dependabot.yml` and the CI workflow both parse cleanly.

---

## 5. ⚠️ One manual step — CI workflow (action required by a maintainer)

A paths-scoped CI workflow was prepared but **could not be pushed via the GitHub App**:
the app token lacks the `workflows` permission (GitHub rejects workflow file creation
without it). Everything else in PR #547 is unaffected.

**To add it**, a maintainer with `workflows` permission creates
`.github/workflows/minerva-pid-test.yml` with the content below (also saved in this repo
at `ci/minerva-pid-test.yml`):

- Triggers only on changes under `MINERVA_PID/**` (no interference with the ~30 other
  workflows).
- Installs `libcairo2`, installs the pinned deps, runs `make.sh`, then runs the
  **standalone** test files (no pytest) across Python 3.8 → 3.11.

> Alternatively, grant the Abacus GitHub App the **Workflows** permission and re-push.

---

## 6. Governance notes

- **No auto-merge.** PR #547 is left open for engineering review.
- **No fabricated dependencies.** The dependency list was corrected down to the 5 truly
  imported packages — reported transparently rather than matching the (inaccurate) template.
- **Reproducibility preserved.** Derived artifacts remain git-ignored; everything
  regenerates from tracked source via `./make.sh`.

---

## 7. Prepare for next wave (W006 suggestion)

The W005 headline finding — design register (`CV001`/`TT100`…) vs as-drawn catalog
(`CV560`/`TT514`…) are **orthogonal numbering schemes → 0 exact overlap** — points to the
clear next deliverable:

> **W006 — design ↔ as-drawn tag cross-map.** Build an explicit crosswalk table that
> links each design tag to its as-drawn instance(s) by TYPE + topology/position, so
> coverage can be reported as true matches rather than per-TYPE deltas. This is the #1
> recommendation already flagged in the W005 report.
