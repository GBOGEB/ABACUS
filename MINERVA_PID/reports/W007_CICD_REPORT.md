# W007 — CI/CD Pipeline Report

**Wave:** W007 &nbsp;|&nbsp; **Status:** ✅ Prepared (staged, awaiting maintainer activation)
**Plan:** `docs/W007_CICD_PLAN.md` &nbsp;|&nbsp; **Setup guide:** `docs/W007_MANUAL_SETUP.md`

---

## Summary

A complete, syntactically validated GitHub Actions workflow for the MINERVA
P&ID pipeline has been authored and staged at **`ci/minerva-pid-test.yml`**.
On every push/PR/manual dispatch it runs a **Python 3.10 / 3.11 / 3.12** matrix
on `ubuntu-latest` that installs system + Python dependencies, regenerates every
derived artifact via `./make.sh` (reproducibility gate), runs the full standalone
test battery (50 assertions), produces optional coverage, enforces a semantic
golden-file gate, and uploads build artifacts.

It is **staged** rather than active because the connected Abacus GitHub App lacks
the `workflows` permission and cannot write under `.github/workflows/`. Activation
is a one-time maintainer step documented in `docs/W007_MANUAL_SETUP.md`.

---

## Deliverables produced

| File | Purpose |
|---|---|
| `ci/minerva-pid-test.yml` | The full GitHub Actions workflow (staged). |
| `ci/golden_gate.py` | Semantic golden-file gate over `reports/*_statistics.json`. |
| `docs/W007_MANUAL_SETUP.md` | Maintainer activation, permissions, expected behavior, troubleshooting. |
| `reports/W007_CICD_REPORT.md` | This report. |
| `reports/wave_status.json` | Updated with the W007 entry (`pass: true`). |

---

## Pipeline stages (as implemented)

```
checkout → setup-python (3.10/3.11/3.12, pip cache)
   → apt: poppler-utils, libcairo2-dev
   → pip install -r requirements.txt
   → ./make.sh --clean && ./make.sh         # reproducibility (7-stage build, exit 0)
   → run every tests/test_*.py              # 50 assertions, fail on any non-zero
   → optional pytest + coverage (coverage.xml, continue-on-error)
   → ci/golden_gate.py                       # semantic stats diff, XLSX jitter ignored
   → upload-artifact (html, md, stats json, crossmap json, coverage)
```

### Matrix & environment
| Axis | Values |
|---|---|
| Python | 3.10, 3.11, 3.12 |
| OS | ubuntu-latest |
| System packages | `poppler-utils`, `libcairo2-dev` |
| Token permissions | `contents: read` (no write-back, no auto-merge) |
| Secrets | none |

### Test battery covered (standalone runners, no pytest required)
`test_colour_model`, `test_integration_pipeline`, `test_w003_w004`,
`test_w005_reconciliation`, `test_w006_crossmap`, `test_w008_viewer` — **50
assertions total**. Each is invoked as `PYTHONPATH=src python3 <file>`; the job
fails if any returns non-zero. Data-dependent suites self-skip if artifacts are
absent, but in CI `make.sh` always builds them first.

### Golden-file gate
`ci/golden_gate.py` flattens and diffs the regenerated
`reports/W005_coverage_statistics.json` and
`reports/W006_crossmap_statistics.json` against their committed (HEAD) versions.
It **fails on count drift** and **ignores** the documented ~1-byte XLSX zip
jitter (XLSX files are excluded from the gate entirely, per plan §4 strategy 1).

---

## Local validation performed

| Check | Result |
|---|---|
| `yaml.safe_load(ci/minerva-pid-test.yml)` | ✅ valid YAML |
| `py_compile ci/golden_gate.py` | ✅ compiles |
| `python3 ci/golden_gate.py` (against committed snapshots) | ✅ PASS — 0 drift entries |
| `wave_status.json` parse after update | ✅ valid JSON, W007 present, `pass: true` |

> Full matrix execution on GitHub-hosted runners cannot be verified from here —
> it requires the workflow to be landed under `.github/workflows/` first.

---

## Activation (maintainer — see docs/W007_MANUAL_SETUP.md)

1. **Resolve the `workflows` blocker** — either grant the Abacus GitHub App the
   *Workflows: read & write* permission, **or** manually:
   ```bash
   git mv MINERVA_PID/ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml
   git commit -m "ci: activate MINERVA P&ID workflow" && git push
   ```
   (Keep `ci/golden_gate.py` in place — the workflow calls it from `ci/`.)
2. Open a throwaway PR and confirm the matrix is green.
3. Add the status badge to the README.

---

## Definition-of-done status

| # | Plan requirement | Status |
|---|---|---|
| 1 | Workflow active on `main` | ⏳ Staged — needs maintainer activation |
| 2 | Matrix green on 3.10–3.12 | ⏳ Pending real run |
| 3 | `./make.sh` exits 0 in CI | ✅ Implemented (reproducibility step) |
| 4 | All `tests/test_*.py` pass | ✅ Implemented (50 assertions, fail-on-nonzero) |
| 5 | Golden-file gate, XLSX-tolerant | ✅ Implemented & locally verified |
| 6 | Artifacts uploaded per run | ✅ Implemented |
| 7 | README status badge | ⏳ After activation |

**Wave outcome:** Pipeline fully prepared and self-validated; remaining items
are the maintainer-only activation steps that are blocked by the GitHub App
permission scope (documented).
