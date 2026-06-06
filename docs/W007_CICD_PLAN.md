# W007 — CI/CD Pipeline Plan

**Wave:** W007
**Status:** Planned. A ready-to-use workflow file already exists in the repo as **`ci/minerva-pid-test.yml`** because the connected GitHub App currently lacks the `workflows` permission and therefore cannot push files under `.github/workflows/`. W007's first job is to land that workflow properly.
**Goal:** make the MINERVA P&ID pipeline continuously verifiable — every push/PR regenerates derived artifacts and runs the full standalone test battery, with deterministic, reviewable results.

---

## 1. Constraints carried from earlier waves

These are non-negotiable and shape every CI decision:

- **No pytest.** Tests are standalone runners (`_run_all()` + `if __name__ == "__main__"`), with `_data_available()` skip-guards for data-dependent suites. CI must invoke each `tests/test_*.py` directly.
- **Stdlib-first.** Runtime deps are minimal; `cairosvg` (PDF render) needs system `libcairo2`. CI must install that OS package.
- **Reproducibility via `./make.sh`.** CI regenerates everything from sources in `data/svg/` and then runs the tests — it must not rely on committed derived artifacts.
- **Known nondeterminism.** `reports/COMPONENT_CATALOG_v2.xlsx` differs by ~1 byte between runs (zip timestamp/ordering), which cascades into `reports/W005_validation_report.md` size. CI must tolerate or normalize this (see §4).
- **No auto-merge.** CI reports status; humans merge.

---

## 2. Pipeline stages

```
checkout → setup matrix (Python) → apt: libcairo2 → pip: requirements
   → ./make.sh (regenerate all derived outputs)
   → run every tests/test_*.py (aggregate pass/fail)
   → golden-file diff gate (statistics JSONs)
   → upload artifacts (publish/*.html, reports/*.md, data/crossmap/*.json)
```

### 2.1 Build/regenerate
- Run `./make.sh` end-to-end. It must exit 0. This is itself a strong integration test (7 steps: model → W003/W004 → catalog → W005 → **W006 crossmap** → atlas v6 → collage → **W006 viewer**).

### 2.2 Test
- Loop over `tests/test_*.py`, run each with `PYTHONPATH=src python3 <file>`, capture exit codes, fail the job if any returns non-zero.
- Current battery (44 assertions): `test_colour_model` (5), `test_integration_pipeline` (5), `test_w003_w004` (10), `test_w005_reconciliation` (11), `test_w006_crossmap` (13).

### 2.3 Golden-file gate *(cross-pollinated pattern)*
- Treat the committed `reports/*_statistics.json` as golden snapshots. After `make.sh`, diff regenerated stats against committed ones; **fail on semantic drift** (counts changing) but **ignore** the known XLSX byte jitter.
- This is the same golden-file discipline used in the test suites, lifted to CI level.

---

## 3. Matrix & environment

| Axis | Values | Rationale |
|---|---|---|
| Python | 3.10, 3.11, 3.12 | repo targets stdlib that is stable across these; catches version drift |
| OS | ubuntu-latest | `libcairo2` available via apt |

System setup step:
```bash
sudo apt-get update && sudo apt-get install -y libcairo2
python -m pip install --upgrade pip
pip install -r requirements.txt   # cairosvg, openpyxl, pyyaml (if pinned)
```

---

## 4. Handling the known nondeterminism

Two viable strategies (pick one in implementation):

1. **Normalize before diff (preferred):** strip the file-size column from `W005_validation_report.md` and exclude `*.xlsx` from the golden gate, comparing only semantic JSON stats.
2. **Tolerance gate:** allow `±2 bytes` on the single XLSX/size line, fail on anything larger.

CI must **never** commit regenerated artifacts back (no write-back), avoiding noisy diffs.

---

## 5. The `workflows` permission blocker (must resolve first)

- The Abacus GitHub App connection used for pushes **cannot write `.github/workflows/*.yml`** (missing `workflows` scope). PR #547 worked around this by committing the workflow as **`ci/minerva-pid-test.yml`** plus documentation.
- **W007 action items:**
  1. Ask the maintainer to grant the `workflows` permission to the [Abacus GitHub App](https://github.com/apps/abacusai/installations/select_target), **or** have a maintainer manually `git mv ci/minerva-pid-test.yml .github/workflows/minerva-pid-test.yml` and push.
  2. Once landed, verify the Actions run is green on a throwaway PR.
  3. Add a status badge to the MINERVA P&ID README.

---

## 6. Deliverables / Definition of done
1. `.github/workflows/minerva-pid-test.yml` active on `main` (resolves §5).
2. Matrix build green on Python 3.10–3.12.
3. `./make.sh` runs in CI and exits 0.
4. All `tests/test_*.py` pass in CI (44+ assertions).
5. Golden-file gate active and tolerant of the documented XLSX jitter.
6. Build artifacts (viewer HTML, reports, crossmap JSON) uploaded per run.
7. Status badge in README.

---

## 7. Future (post-W007)
- Cache pip + apt to speed runs.
- Optional: publish `publish/*.html` to GitHub Pages for always-fresh interactive viewer + atlas.
- Optional: scheduled (nightly) run to catch environment drift.
