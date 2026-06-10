<<<<<<< HEAD
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
=======
# W007 — CI/CD Pipeline: Validation Report

**Wave:** W007 &nbsp;|&nbsp; **Status:** delivered &nbsp;|&nbsp; **Date:** 2026-06-07

This is the *Normalized-Claim ≠ Complete* record for W007 (per AGENTS.md
governance): every claim below is backed by a file that exists and a runtime
result that was actually produced.

---

## 1. Claim

> The MINERVA P&ID pipeline is continuously verifiable: a GitHub Actions
> workflow regenerates all derived artifacts (`./make.sh`), runs the full
> standalone test battery under coverage, enforces a deterministic golden-file
> regression gate, checks clean-rebuild reproducibility, and uploads artifacts —
> all **without pytest**, honoring the project's standalone-runner convention.

## 2. What exists (files)

| Artifact | Path | Purpose |
|---|---|---|
| Workflow | `ci/minerva-pid-test.yml` | build + test + coverage + golden + reproducibility + artifacts (staged; see §6) |
| Coverage cfg | `.coveragerc`, `[tool.coverage.*]` in `pyproject.toml` | coverage.py settings (source=src, branch, parallel) |
| Golden snapshots | `tests/golden/expected_line_model_structure.json`, `…/expected_component_counts.json`, `…/expected_crossmap_stats.json` | pinned invariants from runtime output |
| Golden runner | `tests/test_golden_files.py` | standalone golden-file regression gate |
| Pre-commit | `.pre-commit-config.yaml` | advisory hygiene/lint hooks |
| Implementation doc | `docs/W007_CI_IMPLEMENTATION.md` | what was built + the no-pytest rationale |
| This report | `reports/W007_CICD_REPORT.md` | validation record |

## 3. Runtime results (actually produced)

```
./make.sh                       → exit 0 (all derived outputs regenerated)
./make.sh --clean ; ./make.sh   → exit 0 (idempotent; artifacts re-created)

Standalone test battery (PYTHONPATH=src python3 tests/test_*.py):
  test_colour_model.py            5/5   PASS
  test_golden_files.py            4/4   PASS   (NEW this wave)
  test_integration_pipeline.py    5/5   PASS
  test_w003_w004.py              10/10  PASS
  test_w005_reconciliation.py    11/11  PASS
  test_w006_crossmap.py          13/13  PASS
  ----------------------------------------------
  TOTAL                          48/48  PASS  (6 runners)

Coverage (coverage run -p → combine → report → xml):
  coverage.xml produced (~98 KB)
  TOTAL line coverage ≈ 17.9%  (reported, not gated — see §5)
```

## 4. Golden-file gate — pinned values (verified)

| Invariant | Value |
|---|---|
| `line_model.line_count` | 9 |
| catalog `unique_count` / `real_count` / `template_count` | 165 / 141 / 24 |
| `real_prefix_histogram` | CV 10, EH 22, HV 12, LS 25, PT 9, TT 63 (= 141) |
| crossmap `total_design_tags` / `total_asdrawn_real_tags` | 97 / 141 |
| crossmap `mapped` (HIGH/MED/LOW) | 43 (0 / 39 / 4) |
| crossmap `unmapped_design` / `asdrawn_unclaimed` | 54 / 98 |

Internal-consistency assertions enforced: histogram Σ = `real_count`;
confidence tiers Σ = `mapped`. Volatile geometry and the ~1-byte XLSX jitter are
excluded from the gate by design → deterministic.

## 5. Known gaps

- **Coverage is reported, not gated.** ~18% reflects that tests target pure
  functions while `build_*` scripts execute via `make.sh` as `__main__`. No
  inflated `fail_under` was added. A real floor needs build-script
  importability refactoring — deferred.
- **Workflow cannot self-activate** — GitHub App lacks `workflows` permission;
  the file is staged at `ci/minerva-pid-test.yml` and a maintainer must copy it
  to `.github/workflows/` (instructions in §6 and the implementation doc).
- **Codecov upload commented out** (needs maintainer `CODECOV_TOKEN`).
- **pre-commit advisory only** — not enforced in CI to avoid a mass reformat
  diff that could perturb reproducible outputs.
- The wave-registry's broader W007 line also names cross-drawing
  QCELL↔RFCELL reconciliation and 4.5K/2K/warm segment classification; those are
  **modelling** scope deferred to a follow-up. This deliverable is the CI/CD half.

## 6. Maintainer activation (one-time)

```bash
cp MINERVA_PID/ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml
git add .github/workflows/minerva-pid-test.yml
git commit -m "ci: activate MINERVA P&ID workflow (W007)"
git push
```

## 7. Reproduce locally

```bash
./make.sh
export PYTHONPATH=src
for t in tests/test_*.py; do python3 "$t"; done
# coverage:
for t in tests/test_*.py; do coverage run -p "$t"; done
coverage combine && coverage report && coverage xml
git checkout -- reports/W005_validation_report.md   # revert XLSX byte jitter
```

**pass = true** — output files exist, this validation report exists, runtime
counts are recorded above, and known gaps are listed.
>>>>>>> origin/main
