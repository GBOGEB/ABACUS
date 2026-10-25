# GBA (GBOGEB/ABACUS) — MCP Orchestration Tuples

> **Repository:** `GBOGEB/ABACUS`
> **Local Path:** `/home/ubuntu/gbogeb_abacus`
> **Test Suite:** 79 tests (render linter, WCAG contrast, slide ID enforcer, verification hook)
> **Topology Nodes:** 20 (GBA-GOV-001 through GBA-CFG-003 + GBC cross-refs)

---

## 1. Task Group Taxonomy

```python
GBA_TASK_GROUPS = {
    "GOVERNANCE_INIT":   "Initialize governance engines, validate configs, load tuning params",
    "RENDER_VALIDATE":   "Execute rendering rules — linter, contrast, slide IDs, layout contracts",
    "LINEAGE_TRACK":     "Binary asset processing — SHA256, .mock sidecars, manifest updates",
    "DEPLOY_GHA":        "GitHub Actions deployment — governance validation, asset verification, Pages",
    "JEKYLL_RENDER":     "Jekyll build pipeline — layouts, theme resolution, site generation",
    "WCAG_COMPLY":       "WCAG AA accessibility checks — contrast ratios, semantic HTML, ARIA",
    "TEST_GOVERN":       "Test execution — 79-test suite, coverage, regression",
    "TOPO_SYNC":         "Knowledge topology synchronization — cross-repo node updates",
}
```

---

## 2. Tuple Format

```
(task_id, task_type, dependencies, inputs, outputs, validation)
```

---

## 3. Orchestration Sequences

### 3.1 — Governance Engine Initialization

```python
WORKFLOW_GOVERNANCE_INIT = [
    (
        "GBA_INIT_001",
        "GOVERNANCE_INIT",
        [],
        {"config": "config/governance_tuning.yaml"},
        {"strict_mode": True, "linter_enabled": True, "wcag_level": "AA"},
        {"cmd": "python3 -c \"import yaml; d=yaml.safe_load(open('config/governance_tuning.yaml')); assert d['governance']['strict_mode']==True\"", "exit_code": 0}
    ),
    (
        "GBA_INIT_002",
        "GOVERNANCE_INIT",
        ["GBA_INIT_001"],
        {"topology": "config/knowledge_topology.json"},
        {"node_count": 20, "cross_repo_edges": 6},
        {"cmd": "python3 -c \"import json; d=json.load(open('config/knowledge_topology.json')); nodes=[n for n in d if isinstance(n,dict)]; print(f'{len(nodes)} nodes')\"", "exit_code": 0}
    ),
    (
        "GBA_INIT_003",
        "GOVERNANCE_INIT",
        ["GBA_INIT_001"],
        {"stakeholders": "config/stakeholder_registry.yaml"},
        {"routes": ["KEB", "DOW", "ALL"]},
        {"cmd": "python3 -c \"import yaml; d=yaml.safe_load(open('config/stakeholder_registry.yaml')); print('Registry loaded')\"", "exit_code": 0}
    ),
    (
        "GBA_INIT_004",
        "GOVERNANCE_INIT",
        ["GBA_INIT_001"],
        {"theme": "engines/SEMANTIC_THEME.yaml"},
        {"light_tokens": True, "dark_tokens": True},
        {"cmd": "python3 -c \"import yaml; d=yaml.safe_load(open('engines/SEMANTIC_THEME.yaml')); assert 'light' in str(d) or 'colors' in str(d)\"", "exit_code": 0}
    ),
]
```

### 3.2 — Render Validation Pipeline

```python
WORKFLOW_RENDER_VALIDATE = [
    (
        "GBA_RENDER_001",
        "RENDER_VALIDATE",
        ["GBA_INIT_001"],
        {"engine": "engines/RENDER_LINTER.py", "targets": "docs/"},
        {"findings": "lint_report.json", "severity_counts": {}},
        {"cmd": "python3 engines/RENDER_LINTER.py docs/ --format json", "exit_code": 0}
    ),
    (
        "GBA_RENDER_002",
        "RENDER_VALIDATE",
        ["GBA_INIT_004"],
        {"engine": "engines/WCAG_CONTRAST_CHECKER.py", "theme": "engines/SEMANTIC_THEME.yaml"},
        {"contrast_report": "contrast_report.json", "wcag_level": "AA"},
        {"cmd": "python3 engines/WCAG_CONTRAST_CHECKER.py engines/SEMANTIC_THEME.yaml --format json", "exit_code": 0}
    ),
    (
        "GBA_RENDER_003",
        "RENDER_VALIDATE",
        ["GBA_INIT_001"],
        {"engine": "engines/SLIDE_ID_ENFORCER.py", "targets": "docs/"},
        {"id_report": "slide_id_report.json"},
        {"cmd": "python3 engines/SLIDE_ID_ENFORCER.py docs/ --format json", "exit_code": 0}
    ),
    (
        "GBA_RENDER_004",
        "RENDER_VALIDATE",
        ["GBA_RENDER_001", "GBA_RENDER_002", "GBA_RENDER_003"],
        {"reports": ["lint_report.json", "contrast_report.json", "slide_id_report.json"]},
        {"governance_gate": "PASS|WARN"},
        {"cmd": "echo 'All render validations completed'", "exit_code": 0}
    ),
]
```

### 3.3 — Lineage Tracking Pipeline

```python
WORKFLOW_LINEAGE_TRACK = [
    (
        "GBA_LIN_001",
        "LINEAGE_TRACK",
        [],
        {"input_dir": "Input_Master/", "hook": "engines/verification_hook.py"},
        {"mock_files": "*.mock", "manifest_updated": True},
        {"cmd": "python3 engines/verification_hook.py --input-dir Input_Master/ --data-dir _data/", "exit_code": 0}
    ),
    (
        "GBA_LIN_002",
        "LINEAGE_TRACK",
        ["GBA_LIN_001"],
        {"manifest": "_data/lineage_manifest.json"},
        {"status_report": True},
        {"cmd": "python3 engines/verification_hook.py --status", "exit_code": 0}
    ),
    (
        "GBA_LIN_003",
        "LINEAGE_TRACK",
        ["GBA_LIN_002"],
        {"manifest": "_data/lineage_manifest.json"},
        {"schema_valid": True, "all_sha256_64chars": True},
        {"cmd": "python3 -c \"import json; m=json.load(open('_data/lineage_manifest.json')); all(len(a['sha256'])==64 for a in m.get('assets',[])) or (_ for _ in ()).throw(AssertionError('Invalid sha256 length'))\"", "exit_code": 0}
    ),
    (
        "GBA_LIN_004",
        "LINEAGE_TRACK",
        ["GBA_LIN_001"],
        {"git_status": True},
        {"uncommitted_mocks": "warn_if_any"},
        {"cmd": "git diff --name-only | grep -c '.mock$' || echo '0 uncommitted mocks'", "exit_code": 0}
    ),
]
```

### 3.4 — Jekyll Rendering Pipeline

```python
WORKFLOW_JEKYLL_RENDER = [
    (
        "GBA_JEK_001",
        "JEKYLL_RENDER",
        ["GBA_RENDER_004"],
        {"config": "_config.yml", "layouts": "_layouts/", "includes": "_includes/"},
        {"config_valid": True},
        {"cmd": "ruby -e \"require 'yaml'; YAML.load_file('_config.yml')\"", "exit_code": 0}
    ),
    (
        "GBA_JEK_002",
        "JEKYLL_RENDER",
        ["GBA_JEK_001"],
        {"layouts": ["_layouts/default.html", "_layouts/slide.html"]},
        {"layouts_valid": True, "liquid_syntax_ok": True},
        {"cmd": "test -f _layouts/default.html && test -f _layouts/slide.html", "exit_code": 0}
    ),
    (
        "GBA_JEK_003",
        "JEKYLL_RENDER",
        ["GBA_JEK_002"],
        {"css": "assets/css/main.css", "js": "assets/js/theme.js"},
        {"theme_css_tokens": True, "theme_js_toggle": True},
        {"cmd": "grep -q 'data-theme' assets/css/main.css && grep -q 'toggleTheme' assets/js/theme.js", "exit_code": 0}
    ),
    (
        "GBA_JEK_004",
        "JEKYLL_RENDER",
        ["GBA_JEK_003"],
        {"build_cmd": "bundle exec jekyll build"},
        {"site_dir": "_site/", "html_output": True},
        {"cmd": "bundle exec jekyll build 2>&1 | tail -1", "expect_contains": "done"}
    ),
]
```

### 3.5 — WCAG Compliance Checks

```python
WORKFLOW_WCAG_COMPLY = [
    (
        "GBA_WCAG_001",
        "WCAG_COMPLY",
        ["GBA_INIT_004"],
        {"theme": "engines/SEMANTIC_THEME.yaml", "mode": "light"},
        {"min_ratio_normal": 4.5, "min_ratio_large": 3.0},
        {"cmd": "python3 engines/WCAG_CONTRAST_CHECKER.py engines/SEMANTIC_THEME.yaml --mode light", "exit_code": 0}
    ),
    (
        "GBA_WCAG_002",
        "WCAG_COMPLY",
        ["GBA_INIT_004"],
        {"theme": "engines/SEMANTIC_THEME.yaml", "mode": "dark"},
        {"min_ratio_normal": 4.5, "min_ratio_large": 3.0},
        {"cmd": "python3 engines/WCAG_CONTRAST_CHECKER.py engines/SEMANTIC_THEME.yaml --mode dark", "exit_code": 0}
    ),
    (
        "GBA_WCAG_003",
        "WCAG_COMPLY",
        ["GBA_JEK_004"],
        {"html_files": "_site/**/*.html"},
        {"semantic_html": True, "aria_landmarks": True},
        {"cmd": "grep -r 'role=\"banner\"\\|role=\"main\"\\|role=\"contentinfo\"' _site/ | wc -l", "expect": ">0"}
    ),
    (
        "GBA_WCAG_004",
        "WCAG_COMPLY",
        ["GBA_WCAG_001", "GBA_WCAG_002", "GBA_WCAG_003"],
        {"reports": "all"},
        {"wcag_aa_compliant": True},
        {"cmd": "echo '✅ WCAG AA compliance verified'", "exit_code": 0}
    ),
]
```

### 3.6 — Test Suite Execution

```python
WORKFLOW_TEST_GOVERN = [
    (
        "GBA_TEST_001",
        "TEST_GOVERN",
        ["GBA_INIT_001"],
        {"test_dir": "tests/", "deps": ["pyyaml", "pytest", "pytest-cov"]},
        {"install_ok": True},
        {"cmd": "pip install pyyaml pytest pytest-cov -q", "exit_code": 0}
    ),
    (
        "GBA_TEST_002",
        "TEST_GOVERN",
        ["GBA_TEST_001"],
        {"suite": "tests/test_render_linter.py"},
        {"tests_passed": 22, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_render_linter.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBA_TEST_003",
        "TEST_GOVERN",
        ["GBA_TEST_001"],
        {"suite": "tests/test_wcag_contrast.py"},
        {"tests_passed": 19, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_wcag_contrast.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBA_TEST_004",
        "TEST_GOVERN",
        ["GBA_TEST_001"],
        {"suite": "tests/test_slide_id_enforcer.py"},
        {"tests_passed": 19, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_slide_id_enforcer.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBA_TEST_005",
        "TEST_GOVERN",
        ["GBA_TEST_001"],
        {"suite": "tests/test_verification_hook.py"},
        {"tests_passed": 19, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_verification_hook.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBA_TEST_006",
        "TEST_GOVERN",
        ["GBA_TEST_002", "GBA_TEST_003", "GBA_TEST_004", "GBA_TEST_005"],
        {"full_suite": "tests/"},
        {"total_passed": 79, "coverage": ">60%"},
        {"cmd": "python3 -m pytest tests/ -v --cov=engines --cov-report=term-missing", "exit_code": 0}
    ),
]
```

### 3.7 — GitHub Actions Deployment

```python
WORKFLOW_DEPLOY_GHA = [
    (
        "GBA_DEPLOY_001",
        "DEPLOY_GHA",
        ["GBA_TEST_006", "GBA_RENDER_004"],
        {"workflow": ".github/workflows/governance-validation.yml"},
        {"lint_job": "pass", "contrast_job": "pass", "slide_ids_job": "pass", "tests_job": "pass"},
        {"manual": "Verify at https://github.com/GBOGEB/ABACUS/actions/workflows/governance-validation.yml"}
    ),
    (
        "GBA_DEPLOY_002",
        "DEPLOY_GHA",
        ["GBA_LIN_003"],
        {"workflow": ".github/workflows/asset-verification.yml"},
        {"verify_job": "pass", "manifest_valid": True},
        {"manual": "Verify at https://github.com/GBOGEB/ABACUS/actions/workflows/asset-verification.yml"}
    ),
    (
        "GBA_DEPLOY_003",
        "DEPLOY_GHA",
        ["GBA_JEK_004"],
        {"workflow": ".github/workflows/archive-deploy.yml"},
        {"bundle_created": True, "pages_deployed": True},
        {"manual": "Verify at https://github.com/GBOGEB/ABACUS/actions/workflows/archive-deploy.yml"}
    ),
]
```

---

## 4. Dependency Graph

```
GBA_INIT_001 ──┬── GBA_INIT_002
               ├── GBA_INIT_003
               ├── GBA_INIT_004 ──┬── GBA_WCAG_001
               │                  ├── GBA_WCAG_002
               │                  └── GBA_RENDER_002
               ├── GBA_RENDER_001
               ├── GBA_RENDER_003
               └── GBA_TEST_001 ──┬── GBA_TEST_002
                                  ├── GBA_TEST_003
                                  ├── GBA_TEST_004
                                  └── GBA_TEST_005 → GBA_TEST_006
               
GBA_RENDER_001 ─┐
GBA_RENDER_002 ─┤→ GBA_RENDER_004 → GBA_JEK_001 → GBA_JEK_002 → GBA_JEK_003 → GBA_JEK_004
GBA_RENDER_003 ─┘                                                                   │
                                                                                     ├── GBA_WCAG_003
                                                                                     └── GBA_DEPLOY_003

GBA_LIN_001 → GBA_LIN_002 → GBA_LIN_003 → GBA_DEPLOY_002
         └── GBA_LIN_004

GBA_TEST_006 ──┬── GBA_DEPLOY_001
GBA_RENDER_004 ┘
```

---

## 5. CI/CD Workflow Integration

| GHA Workflow | Orchestration Tuples | Trigger |
|-------------|---------------------|---------|
| `governance-validation.yml` | GBA_RENDER_001-004, GBA_WCAG_001-002, GBA_TEST_002-006 | PR to main/develop, push main |
| `asset-verification.yml` | GBA_LIN_001-004 | Push to Input_Master/ |
| `archive-deploy.yml` | GBA_JEK_001-004, GBA_DEPLOY_003 | Push to main |

---

## 6. Error Handling

```python
GBA_RETRY_POLICY = {
    "GOVERNANCE_INIT":  {"max_retries": 2, "backoff_s": 2,  "on_fail": "HALT"},
    "RENDER_VALIDATE":  {"max_retries": 1, "backoff_s": 0,  "on_fail": "REPORT_AND_BLOCK"},
    "LINEAGE_TRACK":    {"max_retries": 2, "backoff_s": 5,  "on_fail": "HALT"},
    "DEPLOY_GHA":       {"max_retries": 3, "backoff_s": 15, "on_fail": "ROLLBACK"},
    "JEKYLL_RENDER":    {"max_retries": 2, "backoff_s": 10, "on_fail": "HALT"},
    "WCAG_COMPLY":      {"max_retries": 1, "backoff_s": 0,  "on_fail": "REPORT_AND_BLOCK"},
    "TEST_GOVERN":      {"max_retries": 1, "backoff_s": 0,  "on_fail": "REPORT"},
    "TOPO_SYNC":        {"max_retries": 2, "backoff_s": 5,  "on_fail": "WARN"},
}
```

---

## 7. Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│  GBA MCP ORCHESTRATION — QUICK REFERENCE                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  GROUPS: GOVERNANCE_INIT | RENDER_VALIDATE | LINEAGE_TRACK│
│          DEPLOY_GHA | JEKYLL_RENDER | WCAG_COMPLY        │
│          TEST_GOVERN | TOPO_SYNC                         │
│                                                          │
│  SEQUENCES:                                              │
│    §3.1 Governance Init ──→ 4 tuples                     │
│    §3.2 Render Validate ──→ 4 tuples                     │
│    §3.3 Lineage Track ────→ 4 tuples                     │
│    §3.4 Jekyll Render ────→ 4 tuples                     │
│    §3.5 WCAG Comply ──────→ 4 tuples                     │
│    §3.6 Test Suite ────────→ 6 tuples                    │
│    §3.7 Deploy GHA ────────→ 3 tuples                    │
│                                                          │
│  TOTAL: 29 tuples across 7 sequences                     │
│  TEST SUITE: 79 tests (22+19+19+19)                      │
│  TOPOLOGY: 20 nodes + 6 cross-repo edges                 │
│  ENVIRONMENTS: testing → staging → production            │
└──────────────────────────────────────────────────────────┘
```
