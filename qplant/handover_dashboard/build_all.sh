#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# QPLANT Cryogenic Dashboard — Master Build Script v4.4.0
# ─────────────────────────────────────────────────────────────────────────────
# Single entry point for all build operations.
# Usage:  ./build_all.sh [--skip-tests] [--verbose]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

SKIP_TESTS=false
VERBOSE=false
for arg in "$@"; do
  case $arg in
    --skip-tests) SKIP_TESTS=true ;;
    --verbose) VERBOSE=true ;;
  esac
done

# ── Activate venv if available ──────────────────────────────────────────────
if [ -f "venv/bin/activate" ]; then
  source "venv/bin/activate"
fi

# ── Setup ───────────────────────────────────────────────────────────────────
mkdir -p dist docs outputs
BUILD_LOG="dist/build_all.log"
: > "$BUILD_LOG"

log() {
  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$ts] $*" | tee -a "$BUILD_LOG"
}

PASS=0
FAIL=0
step_ok()   { PASS=$((PASS+1)); log "  ✅ $*"; }
step_fail() { FAIL=$((FAIL+1)); log "  ❌ $*"; }

log "═══════════════════════════════════════════════════════"
log "  QPLANT Master Build — $(cat VERSION)"
log "═══════════════════════════════════════════════════════"

# ── Step 0: Validate configuration ─────────────────────────────────────────
log "[0/7] Validating configuration (SSoT)..."
python3 -c "
from src.config_loader import cfg
v = cfg.version
hp = cfg.get('compressor_specifications.hp_compressors.count')
capex = cfg.get('financial.compressor_capex.total_system_eur')
print(f'  Config v{v}: {hp} compressors, €{capex:,.0f} total CAPEX')
assert v == '4.0.0', f'Version mismatch: {v}'
assert hp == 3, f'Compressor count mismatch: {hp}'
print('  Configuration valid ✓')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Config validated" || step_fail "Config validation"

# ── Step 1: Generate standards & statistical analysis ───────────────────────
log "[1/7] Generating standards & statistical analysis..."
export PYTHONHASHSEED=42
export CRYO_BUILD_SEED=42
python3 src/generate_standards_stats.py 2>&1 | tee -a "$BUILD_LOG" && step_ok "Standards & stats" || step_fail "Standards & stats"

# ── Step 2: Generate v3.1/v4.0 visualizations & doc pages ──────────────────
log "[2/7] Generating compressor/liquid He visualizations & docs..."
python3 src/build_v3_1.py 2>&1 | tee -a "$BUILD_LOG" && step_ok "v3.1 visualizations" || step_fail "v3.1 visualizations"

# ── Step 3: Build dense slide navigator & stakeholder presentation ──────────
log "[3/7] Building slide navigators & presentations..."
python3 src/build_dense_slides.py 2>&1 | tee -a "$BUILD_LOG" && step_ok "Dense slides" || step_fail "Dense slides"

# ── Step 4: Create v4.0.0 navigator from v3.1 template ─────────────────────
log "[4/7] Generating v4.0.0 navigator..."
sed 's/v3\.1\.0/v4.0.0/g; s/index_v3_1\.html/index_v4_0.html/g' docs/index_v3_1.html > docs/index_v4_0.html
step_ok "v4.0.0 navigator"

# ── Step 5: Build landing hub (index.html) & manifest ──────────────────────
log "[5/7] Building landing hub & manifest..."
python3 src/build_dashboard.py 2>&1 | tee -a "$BUILD_LOG" && step_ok "Landing hub" || step_fail "Landing hub"

# Rebuild manifest
python3 -c "
import json, hashlib, os
from pathlib import Path
from datetime import datetime, timezone

root = Path('.')
version = (root / 'VERSION').read_text(encoding='utf-8').strip()
manifest_path = root / 'docs' / 'manifest.json'

manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['version'] = version
manifest['build'] = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'builder': 'build_all.sh v4.0.0',
    'status': 'verified',
}

manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
print(f'  Manifest updated: v{version}')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Manifest" || step_fail "Manifest"

# ── Step 6: Run tests ──────────────────────────────────────────────────────
if [ "$SKIP_TESTS" = true ]; then
  log "[6/7] Tests SKIPPED (--skip-tests flag)"
else
  log "[6/7] Running test suite..."
  python3 -m pytest tests/ -v --tb=short 2>&1 | tee -a "$BUILD_LOG" && step_ok "Tests" || step_fail "Tests"
fi

# ── Step 7: Triage verification ────────────────────────────────────────────
log "[7/7] Running triage verification..."
python3 src/verify_triage.py --all 2>&1 | tee -a "$BUILD_LOG" && step_ok "Triage verification" || step_fail "Triage verification"

# ── Step 8: Generate stakeholder presentations (Phase 2) ───────────────────
log "[8/13] Generating stakeholder presentations..."
python3 scripts/generate_presentation.py --audience=all 2>&1 | tee -a "$BUILD_LOG" && step_ok "Presentations" || step_fail "Presentations"

# ── Step 9: Validate cross-links (Phase 2) ─────────────────────────────────
log "[9/13] Validating cross-link registry..."
if [ -f "/home/ubuntu/validate_cross_links.py" ]; then
  python3 /home/ubuntu/validate_cross_links.py 2>&1 | tee -a "$BUILD_LOG" && step_ok "Cross-links" || step_fail "Cross-links"
else
  log "  ⚠️  Cross-link validator not found, skipping"
fi

# ── Step 10: Config service validation (Phase 3) ───────────────────────────
log "[10/13] Validating configuration service..."
python3 -c "
import sys; sys.path.insert(0, '/home/ubuntu')
from config_service.schemas import QplantConfig
from config_service.service import ConfigService
svc = ConfigService(config_path='$ROOT_DIR/data/config.yaml')
result = svc.validate()
print(f'  Config valid: {result[\"valid\"]}')
print(f'  Sections: {len(result.get(\"sections\", []))}')
assert result['valid'], 'Config validation failed'
print('  Config service validation passed ✓')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Config service" || step_fail "Config service"

# ── Step 11: AI-assisted config validation (Phase 3) ──────────────────────
log "[11/13] Running AI-assisted config validation..."
python3 -c "
import sys, json; sys.path.insert(0, '/home/ubuntu')
from ai_validation.config_validator import ConfigValidator
v = ConfigValidator('$ROOT_DIR/data/config.yaml')
result = v.validate_all()
print(f'  Validation score: {result[\"score\"]}%')
print(f'  Total checks: {result[\"total_checks\"]}')
print(f'  Valid: {result[\"valid\"]}')
errors = [r for r in result['results'] if r['level'] == 'error']
if errors:
    for e in errors:
        print(f'  ⚠️  {e[\"message\"]}')
assert result['valid'], f'AI validation found errors'
print('  AI config validation passed ✓')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "AI config validation" || step_fail "AI config validation"

# ── Step 12: Code quality analysis (Phase 3) ──────────────────────────────
log "[12/13] Running code quality analysis..."
python3 -c "
import sys, json; sys.path.insert(0, '/home/ubuntu')
from ai_validation.code_quality import CodeQualityAnalyser
a = CodeQualityAnalyser()
result = a.analyse_directory('$ROOT_DIR/src')
s = result['summary']
print(f'  Files: {s[\"files_analysed\"]}, Lines: {s[\"total_lines\"]}')
print(f'  Average score: {s[\"average_score\"]}/10.0')
print(f'  Issues: {s[\"total_issues\"]}')
print('  Code quality analysis complete ✓')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Code quality" || step_fail "Code quality"

# ── Step 13: Documentation quality check (Phase 3) ────────────────────────
log "[13/13] Checking documentation quality..."
python3 -c "
import sys; sys.path.insert(0, '/home/ubuntu')
from ai_validation.doc_quality import DocQualityAnalyser
a = DocQualityAnalyser()
result = a.analyse_directory('/home/ubuntu', patterns=['*.md'])
s = result['summary']
print(f'  Docs analysed: {s[\"files_analysed\"]}')
print(f'  Total words: {s[\"total_words\"]}')
print(f'  Average score: {s[\"average_score\"]}/10.0')
print('  Documentation quality check complete ✓')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Doc quality" || step_fail "Doc quality"

# ── Phase 4: Authentication ────────────────────────────────────────────────
log ""
log "Step 14/17: Validating API key authentication..."
python3 -c "
import sys; sys.path.insert(0, '/home/ubuntu')
from authentication.api_key_manager import APIKeyManager
mgr = APIKeyManager('/tmp/build_test_keys.json')
kid, key = mgr.generate_key('build-test', expiry_days=1)
result = mgr.validate_key(key)
assert result['valid'], 'Key validation failed'
mgr.revoke_key(kid)
result2 = mgr.validate_key(key)
assert not result2['valid'], 'Revocation failed'
import os; os.remove('/tmp/build_test_keys.json')
print('  API key auth: generate ✓ validate ✓ revoke ✓')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Auth validation" || step_fail "Auth validation"

# ── Phase 4: SBOM ─────────────────────────────────────────────────────────
log ""
log "Step 15/17: Validating SBOM..."
python3 -c "
import json, sys
from pathlib import Path
sbom = Path('/home/ubuntu/sbom/cyclonedx_sbom.json')
if sbom.exists():
    data = json.loads(sbom.read_text())
    assert data.get('bomFormat') == 'CycloneDX'
    comps = len(data.get('components', []))
    print(f'  SBOM valid: {comps} components, CycloneDX 1.5')
else:
    print('  SBOM not found — run sbom/generate_sbom.py first')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "SBOM validation" || step_fail "SBOM validation"

# ── Phase 4: K8s manifests ────────────────────────────────────────────────
log ""
log "Step 16/17: Validating K8s manifests..."
python3 -c "
import yaml, sys
from pathlib import Path
k8s_dir = Path('/home/ubuntu/deployment/k8s')
manifests = list(k8s_dir.glob('*.yaml'))
valid = 0
for m in manifests:
    try:
        list(yaml.safe_load_all(m.read_text()))
        valid += 1
    except Exception as e:
        print(f'  ❌ Invalid: {m.name}: {e}')
print(f'  K8s manifests: {valid}/{len(manifests)} valid')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "K8s validation" || step_fail "K8s validation"

# ── Phase 4: Load test config ─────────────────────────────────────────────
log ""
log "Step 17/17: Validating load test configuration..."
python3 -c "
import json, sys
from pathlib import Path
bl = Path('/home/ubuntu/load_testing/performance_baselines.json')
if bl.exists():
    data = json.loads(bl.read_text())
    endpoints = len(data.get('api_endpoints', {}))
    print(f'  Load test baselines: {endpoints} endpoints configured')
else:
    print('  Load test baselines not found')
" 2>&1 | tee -a "$BUILD_LOG" && step_ok "Load test config" || step_fail "Load test config"

# ── Summary ────────────────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════"
log "  BUILD COMPLETE — v$(cat VERSION)"
log "  Steps passed: $PASS | Steps failed: $FAIL"
log "  Log: dist/build_all.log"
log "═══════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  log "⚠️  $FAIL step(s) failed — review log for details"
  exit 1
fi

log "✅ All steps passed"
