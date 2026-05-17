# Phase 1 Control Checklist — Ongoing Maintenance

> **Purpose:** Prevent regression of Phase 1 improvements through systematic checks  
> **Frequency:** Before each release / after each significant change  
> **Project:** MYRRHA QPLANT Cryogenic Dashboard v4.0.0+  
> **Created:** 2026-05-12  

---

## Pre-Build Checks

- [ ] **C-01** — `data/config.yaml` is the only place engineering parameters are defined
- [ ] **C-02** — `VERSION.json` version matches `config.yaml` version field
- [ ] **C-03** — No hardcoded compressor count, motor power, or CAPEX in Python generators
  - Verify: `grep -rn "400 kW\|4×\|€820" src/*.py` returns zero results
- [ ] **C-04** — All Python generators import from `config_loader.py` for key parameters
- [ ] **C-05** — Virtual environment is active and `requirements.txt` packages installed

## Build Execution Checks

- [ ] **C-06** — Run `./build_all.sh` (not individual scripts) for full builds
- [ ] **C-07** — All 9 build steps pass (check `dist/build_all.log`)
- [ ] **C-08** — No warnings or errors in build log
- [ ] **C-09** — Build completes in <30 seconds (flag performance regressions)

## Post-Build Validation

- [ ] **C-10** — 22/22 tests passing: `python -m pytest tests/ -v`
- [ ] **C-11** — Triage compliance ≥9.0/10.0
- [ ] **C-12** — Version consistency check:
  ```bash
  grep -r "v3.1.0\|v2.1.0" docs/*.html docs/heroes/*.html | grep -v "index_v3" | wc -l
  # Expected: 0
  ```
- [ ] **C-13** — Config alignment spot-check:
  ```bash
  grep -c "315 kW" docs/compressors/HP_Redundancy_Analysis.html
  # Expected: ≥1
  grep -c "3× FSD575\|3 active" docs/index_v4_0.html
  # Expected: ≥1
  ```
- [ ] **C-14** — Manifest hashes are fresh (check `docs/manifest.json` timestamp)

## Documentation Checks

- [ ] **C-15** — `CHANGELOG.md` updated for new version
- [ ] **C-16** — `BUILD_GUIDE.md` reflects any pipeline changes
- [ ] **C-17** — `phase1_consolidated_todos.md` updated with completed/new items
- [ ] **C-18** — All new HTML pages include version badge and SSoT reference footer

## Configuration Drift Detection

- [ ] **C-19** — Run config drift check:
  ```bash
  python3 -c "
  from src.config_loader import cfg
  assert cfg.get('compressor_specifications.hp_compressors.count') == 3
  assert cfg.get('compressor_specifications.fsd575.motor_power_kW') == 315
  assert cfg.get('financial.compressor_capex.total_3_units_eur') == 600000
  print('✅ Config drift check passed')
  "
  ```
- [ ] **C-20** — No new hardcoded engineering values introduced:
  ```bash
  git diff --cached src/*.py | grep -E "^\+" | grep -E "[0-9]{3,} kW|€[0-9]" | wc -l
  # Expected: 0 (flag any new hardcoded values)
  ```

## Regression Prevention

- [ ] **C-21** — No files manually edited in `docs/` (all should be generated)
- [ ] **C-22** — `build_all.sh` has `set -euo pipefail` (fail-fast behavior)
- [ ] **C-23** — Test suite covers all critical calculations (leak rate, Monte Carlo, reliability)
- [ ] **C-24** — Git commit includes descriptive message with affected areas

## Periodic Review (Monthly)

- [ ] **C-25** — Review remaining TODO items (target: reduce by ≥3 per month)
- [ ] **C-26** — Check for new Python/library security updates
- [ ] **C-27** — Verify SSoT parameters against latest vendor documentation
- [ ] **C-28** — Review build performance trends
- [ ] **C-29** — Update this checklist based on new learnings

---

## Quick Validation Script

```bash
#!/usr/bin/env bash
# Run this after any change to verify Phase 1 controls
cd /home/ubuntu/handover_dashboard

echo "=== Phase 1 Control Validation ==="

# C-02: Version match
CONFIG_VER=$(python3 -c "import yaml; print(yaml.safe_load(open('data/config.yaml'))['version'])")
JSON_VER=$(python3 -c "import json; print(json.load(open('VERSION.json'))['version'])")
[ "$CONFIG_VER" = "$JSON_VER" ] && echo "✅ C-02: Version match ($CONFIG_VER)" || echo "❌ C-02: Version mismatch ($CONFIG_VER vs $JSON_VER)"

# C-03: No stale values
STALE=$(grep -rn "400 kW\|4× with VFD\|€820" src/*.py 2>/dev/null | wc -l)
[ "$STALE" -eq 0 ] && echo "✅ C-03: No stale config values" || echo "❌ C-03: $STALE stale values found"

# C-10: Tests
python3 -m pytest tests/ -q 2>&1 | tail -1

# C-12: Version labels
STALE_LABELS=$(grep -r "v3.1.0\|v2.1.0" docs/*.html docs/heroes/*.html 2>/dev/null | grep -v "index_v3" | wc -l)
[ "$STALE_LABELS" -eq 0 ] && echo "✅ C-12: No stale version labels" || echo "❌ C-12: $STALE_LABELS stale labels found"

echo "=== Validation Complete ==="
```

---

*Control checklist for QPLANT Phase 1 maintenance — Generated 2026-05-12*

---

## Phase 2 Retrospective Additions

> **Added:** 2026-05-12 — Items discovered during Phase 2 execution that should have been in Phase 1 controls.

### API Readiness Controls (New)

- [ ] **C-20** — Python modules are importable without `sys.path` manipulation
  - Verify: No `sys.path.insert` in any `api/` files
- [ ] **C-21** — All calculation functions return structured data (dict/dataclass), not HTML strings
  - Verify: `grep -rn "return.*<" src/*.py` should return 0 non-HTML-generator results
- [ ] **C-22** — `config_loader.py` works with absolute and relative paths
  - Verify: Import from project root and from subdirectory both succeed

### Integration Readiness Controls (New)

- [ ] **C-23** — CORS requirements documented if any web consumers exist
  - Verify: Check for `localhost:3000` or other origins in middleware config
- [ ] **C-24** — All configuration values are accessible via programmatic API (not just file read)
  - Verify: `/api/v1/config` returns complete config sections
- [ ] **C-25** — Integration test suite exists alongside unit tests
  - Verify: `ls tests/test_api.py tests/test_integration*.py`

### Monitoring Readiness Controls (New)

- [ ] **C-26** — Build pipeline produces machine-readable output (JSON log)
  - Verify: `dist/build_all.log` or equivalent exists
- [ ] **C-27** — Config drift detection baseline is maintained
  - Verify: `monitoring_dashboard/collect_metrics.py --check` exits 0
- [ ] **C-28** — Version consistency checked across all systems (config.yaml, VERSION.json, API, dashboard)
  - Verify: Run version consistency script

### Traceability Controls (New)

- [ ] **C-29** — All new source files added to cross-link registry within 24h
  - Verify: `python validate_cross_links.py` shows 0 missing paths
- [ ] **C-30** — Dependency edges updated when imports/references change
  - Verify: Edge count matches actual import graph
- [ ] **C-31** — No orphaned artifacts in the registry
  - Verify: `validate_cross_links.py` orphan count = 0

---

**Total Controls:** 31 items (original 19 + 12 new from Phase 2 retrospective)  
**Review Cadence:** Weekly (automated), Monthly (manual review)
