# Ubuntu MCP Task Sequences

> **Complete command sequences with expected outputs, validation checkpoints, and error recovery**
> **Environment:** Ubuntu (Abacus AI Agent VM) · Python 3.11 · Git 2.x
> **Working Directory:** `/home/ubuntu`

---

## 1. Task Group: REPO_INIT — Repository Setup

### 1.1 — Clone All GBOGEB Repositories

```bash
# ── Sequence: REPO_INIT_CLONE ──
mkdir -p /home/ubuntu/github_repos
cd /home/ubuntu/github_repos

# Clone cryogenic-accelerator-workspace
git clone --depth=50 https://github.com/GBOGEB/cryogenic-accelerator-workspace.git
# Expected: Cloning into 'cryogenic-accelerator-workspace'... done.

# Clone GBA (ABACUS) — if not already at /home/ubuntu/gbogeb_abacus
test -d /home/ubuntu/gbogeb_abacus || \
  git clone --depth=50 https://github.com/GBOGEB/ABACUS.git /home/ubuntu/gbogeb_abacus
# Expected: Already exists OR Cloning into '/home/ubuntu/gbogeb_abacus'...

# Clone GBC (CODEX)
test -d /home/ubuntu/gbogeb_codex || \
  git clone --depth=50 https://github.com/GBOGEB/CODEX.git /home/ubuntu/gbogeb_codex
# Expected: Already exists OR Cloning into '/home/ubuntu/gbogeb_codex'...

# Clone MCP Server
test -d /home/ubuntu/gbogeb_mcp_server || \
  git clone --depth=50 https://github.com/GBOGEB/gbogeb-mcp-server.git /home/ubuntu/gbogeb_mcp_server
# Expected: Already exists OR Cloning...

# Validation checkpoint
echo "=== REPO_INIT_CLONE validation ==="
for d in /home/ubuntu/gbogeb_abacus /home/ubuntu/gbogeb_codex /home/ubuntu/gbogeb_mcp_server \
         /home/ubuntu/github_repos/cryogenic-accelerator-workspace; do
  if [ -d "$d/.git" ]; then
    echo "  ✅ $d ($(git -C $d log --oneline -1))"
  else
    echo "  ❌ $d — NOT A GIT REPO"
  fi
done
```

### 1.2 — Configure Git Identity

```bash
# ── Sequence: REPO_INIT_CONFIG ──
git config --global user.name "GBOGEB"
git config --global user.email "gbogeb@users.noreply.github.com"

# Validation
git config --global user.name   # Expected: GBOGEB
git config --global user.email  # Expected: gbogeb@users.noreply.github.com
```

---

## 2. Task Group: CONFIG_VALIDATE — Configuration Checks

### 2.1 — Validate All YAML Configs

```bash
# ── Sequence: CONFIG_VALIDATE_YAML ──
cd /home/ubuntu/gbogeb_abacus
pip install pyyaml -q

python3 << 'EOF'
import yaml, glob, sys
errors = 0
for pattern in ['config/*.yaml', 'config/*.yml', 'engines/*.yaml']:
    for f in glob.glob(pattern):
        try:
            with open(f) as fh:
                yaml.safe_load(fh)
            print(f"  ✅ {f}")
        except yaml.YAMLError as e:
            print(f"  ❌ {f}: {e}")
            errors += 1
print(f"\n{'✅' if errors==0 else '❌'} {errors} errors found")
sys.exit(1 if errors else 0)
EOF
# Expected: All ✅, 0 errors
```

### 2.2 — Validate All JSON Configs

```bash
# ── Sequence: CONFIG_VALIDATE_JSON ──
cd /home/ubuntu/gbogeb_abacus

python3 << 'EOF'
import json, glob, sys
errors = 0
for f in glob.glob('config/*.json') + glob.glob('_data/*.json'):
    try:
        with open(f) as fh:
            json.load(fh)
        print(f"  ✅ {f}")
    except json.JSONDecodeError as e:
        print(f"  ❌ {f}: {e}")
        errors += 1
print(f"\n{'✅' if errors==0 else '❌'} {errors} errors found")
sys.exit(1 if errors else 0)
EOF
# Expected: All ✅
```

### 2.3 — Validate Knowledge Topology

```bash
# ── Sequence: CONFIG_VALIDATE_TOPOLOGY ──
cd /home/ubuntu/gbogeb_abacus

python3 << 'EOF'
import json
with open('config/knowledge_topology.json') as f:
    data = json.load(f)
nodes = data if isinstance(data, list) else data.get('nodes', [])
print(f"Topology: {len(nodes)} nodes")
for n in nodes:
    if isinstance(n, dict):
        nid = n.get('id', 'unknown')
        repo = n.get('repo', 'unknown')
        label = n.get('label', 'unknown')
        print(f"  {nid:20s} [{repo:4s}] {label}")
print(f"\n✅ Topology validated: {len(nodes)} nodes")
EOF
# Expected: 20+ nodes listed
```

---

## 3. Task Group: TEST_EXEC — Test Execution

### 3.1 — GBA Test Suite (79 tests)

```bash
# ── Sequence: TEST_EXEC_GBA ──
cd /home/ubuntu/gbogeb_abacus
pip install pyyaml pytest pytest-cov -q

python3 -m pytest tests/ -v --tb=short --cov=engines --cov-report=term-missing
# Expected:
#   tests/test_render_linter.py ........ 22 passed
#   tests/test_wcag_contrast.py ........ 19 passed
#   tests/test_slide_id_enforcer.py .... 19 passed
#   tests/test_verification_hook.py .... 19 passed
#   ========= 79 passed =========

# Validation checkpoint
python3 -m pytest tests/ -q 2>&1 | tail -1
# Expected: 79 passed
```

### 3.2 — GBC Test Suite (68 tests)

```bash
# ── Sequence: TEST_EXEC_GBC ──
cd /home/ubuntu/gbogeb_codex
pip install pyyaml pytest pytest-cov -q

python3 -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
# Expected:
#   tests/test_asset_validator.py ...... 25 passed
#   tests/test_svg_cleaner.py ......... 24 passed
#   tests/test_lineage_tracker.py ..... 19 passed
#   ========= 68 passed =========

# Validation checkpoint
python3 -m pytest tests/ -q 2>&1 | tail -1
# Expected: 68 passed
```

### 3.3 — MCP Server Test Suite (51 tests)

```bash
# ── Sequence: TEST_EXEC_MCP ──
cd /home/ubuntu/gbogeb_mcp_server
pip install -e ".[dev]" -q 2>/dev/null || pip install pyyaml pytest -q

python3 -m pytest tests/ -v --tb=short
# Expected: 51 passed

# Validation checkpoint
python3 -m pytest tests/ -q 2>&1 | tail -1
# Expected: 51 passed
```

### 3.4 — Cryogenic Workspace Validation

```bash
# ── Sequence: TEST_EXEC_CRYO ──
cd /home/ubuntu/github_repos/cryogenic-accelerator-workspace
pip install numpy pyyaml -q

# Physics validation
python3 -c "
import yaml, sys
sys.path.insert(0, 'src')
from physics_validator import verify_mass_balance
with open('config/engineering_data.yaml') as f:
    config = yaml.safe_load(f)
r = verify_mass_balance(config)
print(f'  ṁ = {r[\"calculated_mass_flow_kg_s\"]} kg/s')
print(f'  Status: {r[\"system_verification_status\"]}')
assert r['system_verification_status'] in ('PASS', 'WARN_LIMIT')
print('✅ Physics validation passed')
"
# Expected:
#   ṁ = 0.47274 kg/s
#   Status: WARN_LIMIT
#   ✅ Physics validation passed

# Workspace build
python3 workspace_build.py
# Expected: ✔ Successful Execution
test -f web/workspace_bundle.tar.gz && echo "✅ Bundle exists" || echo "❌ Bundle missing"
```

---

## 4. Task Group: GOVERNANCE — Render Validation

### 4.1 — Run Render Linter

```bash
# ── Sequence: GOVERNANCE_LINT ──
cd /home/ubuntu/gbogeb_abacus

python3 engines/RENDER_LINTER.py docs/ --format json 2>/dev/null || \
  python3 -c "
import sys; sys.path.insert(0, '.'); 
from engines.RENDER_LINTER import lint_file
import glob
for f in glob.glob('docs/*.md'):
    result = lint_file(f)
    print(f'  {f}: {result}')
"
# Expected: Lint results for each doc file
```

### 4.2 — Run WCAG Contrast Checker

```bash
# ── Sequence: GOVERNANCE_CONTRAST ──
cd /home/ubuntu/gbogeb_abacus

python3 engines/WCAG_CONTRAST_CHECKER.py engines/SEMANTIC_THEME.yaml --format json 2>/dev/null || \
  python3 -c "
import sys; sys.path.insert(0, '.');
from engines.WCAG_CONTRAST_CHECKER import check_theme_file
result = check_theme_file('engines/SEMANTIC_THEME.yaml')
print(f'Contrast check: {result}')
"
# Expected: WCAG AA compliance results
```

---

## 5. Task Group: DEPLOY — Deployment Operations

### 5.1 — CI/CD Workflow Activation

```bash
# ── Sequence: DEPLOY_ACTIVATE_WORKFLOWS ──
cd /home/ubuntu
# NOTE: Requires user PAT with workflow scope (App token cannot push to .github/workflows/)

# Copy workflows from reference
bash docs/ci-workflows/apply.sh
# Expected: 6 workflows copied

# Stage and commit
git add .github/workflows/
git commit -m "ci: activate 6-workflow CI/CD suite"

# Push (requires workflow-scope token)
git push origin main
# Expected: Triggers ci-test, ci-build, ci-deploy on GitHub Actions
```

### 5.2 — GitHub Pages Verification

```bash
# ── Sequence: DEPLOY_VERIFY_PAGES ──
# Check each repo's Pages deployment
for repo in ABACUS CODEX cryogenic-accelerator-workspace; do
  URL="https://gbogeb.github.io/$repo/"
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
  echo "  $repo: HTTP $STATUS ($URL)"
done
# Expected: HTTP 200 for each (if Pages enabled)
```

---

## 6. Error Recovery Procedures

### E001 — Git Clone Failure

```bash
# Diagnosis
git clone https://github.com/GBOGEB/REPO.git 2>&1
# If "remote: Repository not found" → Check repo name/access
# If "fatal: unable to access" → Check network/token

# Recovery
# 1. Verify repo exists
curl -s "https://api.github.com/repos/GBOGEB/REPO" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('full_name','NOT FOUND'))"
# 2. Refresh token
# Use Git_Tool get_github_access_token and store it in GITHUB_TOKEN
# 3. Authenticate without embedding the token in the clone URL
printf '%s' "$GITHUB_TOKEN" | gh auth login --with-token
# 4. Retry clone with the normal HTTPS URL
git clone https://github.com/GBOGEB/REPO.git
```

### E002 — Git Push Rejected (Workflows)

```bash
# Diagnosis: "refusing to allow a GitHub App to create or update workflow"
# This is a platform restriction — App tokens CANNOT push to .github/workflows/

# Recovery:
# Option A: User pushes from local machine with PAT (workflow scope)
# Option B: User edits workflow files via GitHub web UI
# Option C: Use docs/ci-workflows/apply.sh after cloning locally
echo "❌ App token cannot push workflows — user intervention required"
```

### E003 — Test Failures

```bash
# Diagnosis
python3 -m pytest tests/ -v --tb=long 2>&1 | grep FAILED
# Show specific failure details

# Recovery
# 1. Check if it's a dependency issue
pip install -r requirements.txt 2>/dev/null || pip install pyyaml pytest numpy
# 2. Run individual failing test with full trace
python3 -m pytest tests/test_specific.py::TestClass::test_method -v --tb=long
# 3. Check for missing fixture files
ls tests/fixtures/
```

### E004 — Config Validation Failure

```bash
# Diagnosis
python3 -c "import yaml; yaml.safe_load(open('config/FILE.yaml'))" 2>&1
# Shows exact YAML parsing error

# Recovery
# 1. Check file encoding
file config/FILE.yaml  # Should be: UTF-8 Unicode text
# 2. Validate online: https://yamlchecker.com/
# 3. Fix indentation (most common issue)
```

### E005 — Physics Engine Assertion

```bash
# Diagnosis
python3 -c "
import yaml, sys
sys.path.insert(0, 'src')
from physics_validator import verify_mass_balance, HeliumPropertyEngine
e = HeliumPropertyEngine()
print(f'h(4.2K): {e.get_enthalpy(4.2, 1.0)}')
print(f'h(4.5K): {e.get_enthalpy(4.5, 1.0)}')
config = yaml.safe_load(open('config/engineering_data.yaml'))
r = verify_mass_balance(config)
print(f'Result: {r}')
"

# Recovery: Check config values
python3 -c "import yaml; d=yaml.safe_load(open('config/engineering_data.yaml')); print(d['engineering_metrics']['heat_loads'])"
# Verify: static_loss > 0 and dynamic_rf_load > 0
```

### E006 — Topology Broken Link

```bash
# Diagnosis
python3 -c "
import json
with open('config/knowledge_topology.json') as f:
    data = json.load(f)
nodes = data if isinstance(data, list) else data.get('nodes', [])
all_ids = {n.get('id') for n in nodes if isinstance(n, dict)}
for n in nodes:
    if isinstance(n, dict):
        for out in n.get('outputs', []):
            if out not in all_ids:
                print(f'  ❌ {n[\"id\"]} → {out} (broken)')
"

# Recovery: Fix the broken output reference
```

### E007 — Bundle Generation Failure

```bash
# Diagnosis
python3 workspace_build.py 2>&1
# Check which step fails

# Recovery
# 1. Ensure all source files exist
for f in config/engineering_data.yaml config/knowledge_topology.json src/physics_validator.py web/index.html web/app.html; do
  test -f "$f" && echo "✅ $f" || echo "❌ $f MISSING"
done
# 2. Re-run workspace generator
python3 workspace_build.py
```

### E008 — PR Creation Failure

```bash
# Recovery: Refresh GitHub token
# Use Git_Tool get_github_access_token
# Then retry PR creation
```

### E009 — Jekyll Build Failure

```bash
# Diagnosis
cd /home/ubuntu/gbogeb_abacus
bundle install 2>&1 | tail -5
bundle exec jekyll build 2>&1

# Recovery
# 1. Check Ruby/Bundler versions
ruby --version
gem --version
# 2. Install missing gems
bundle install
# 3. Check _config.yml syntax
ruby -e "require 'yaml'; YAML.load_file('_config.yml')"
```

### E010 — Cross-Repo Sync Failure

```bash
# Diagnosis
# Check both repo states
git -C /home/ubuntu/gbogeb_codex status
git -C /home/ubuntu/gbogeb_abacus status

# Recovery
# 1. Ensure both repos are clean
git -C /home/ubuntu/gbogeb_codex stash
git -C /home/ubuntu/gbogeb_abacus stash
# 2. Pull latest
git -C /home/ubuntu/gbogeb_codex pull
git -C /home/ubuntu/gbogeb_abacus pull
# 3. Retry sync
```

---

## 7. Parallel Execution Opportunities

### 7.1 — Independent Test Suites (can run simultaneously)

```bash
# These can execute in parallel (different repos, no shared state)
python3 -m pytest /home/ubuntu/gbogeb_abacus/tests/ -q &
python3 -m pytest /home/ubuntu/gbogeb_codex/tests/ -q &
python3 -m pytest /home/ubuntu/gbogeb_mcp_server/tests/ -q &
wait
echo "All test suites completed"
```

### 7.2 — Independent Config Validations

```bash
# YAML + JSON validation can run in parallel
python3 -c "import yaml; yaml.safe_load(open('/home/ubuntu/gbogeb_abacus/config/governance_tuning.yaml'))" &
python3 -c "import json; json.load(open('/home/ubuntu/gbogeb_abacus/config/knowledge_topology.json'))" &
python3 -c "import yaml; yaml.safe_load(open('/home/ubuntu/gbogeb_codex/config/visual_data.yaml'))" &
wait
echo "All configs validated"
```

### 7.3 — Async Task Groups

```
PARALLEL_GROUP_A (independent):
  ├── GBA test suite
  ├── GBC test suite
  └── MCP test suite

PARALLEL_GROUP_B (after GROUP_A):
  ├── GBA governance validation
  └── GBC asset validation

SERIAL (after GROUP_B):
  ├── Cross-repo sync
  ├── Topology update
  └── Deployment
```

---

## 8. Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│  UBUNTU MCP SEQUENCES — QUICK REFERENCE                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  TASK GROUPS:                                            │
│    §1 REPO_INIT     Clone, configure                     │
│    §2 CONFIG_VALID  YAML, JSON, topology                 │
│    §3 TEST_EXEC     GBA(79) + GBC(68) + MCP(51) + Cryo  │
│    §4 GOVERNANCE    Lint, contrast, WCAG                 │
│    §5 DEPLOY        Workflows, Pages                     │
│                                                          │
│  ERRORS: E001-E010 (clone, push, test, config, physics,  │
│          topology, bundle, PR, jekyll, cross-sync)       │
│                                                          │
│  PARALLEL: Test suites (3 repos) · Config validations    │
│  SERIAL: Cross-repo sync → Topology → Deploy             │
│                                                          │
│  TOTAL TESTS: 79 + 68 + 51 = 198                        │
└──────────────────────────────────────────────────────────┘
```
